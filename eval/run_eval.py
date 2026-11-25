#!/usr/bin/env python3
"""Run golden-set evaluation against a live RAG chatbot backend."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent
DEFAULT_GOLDEN = EVAL_DIR / "golden.json"
RESULTS_DIR = EVAL_DIR / "results"
CITE_RE = re.compile(r"\[(\d+)\]")

ChatResult = dict[str, Any]


def parse_sse_blocks(buffer: str) -> tuple[list[str], str]:
    blocks: list[str] = []
    while "\n\n" in buffer:
        block, buffer = buffer.split("\n\n", 1)
        if block.strip():
            blocks.append(block)
    return blocks, buffer


def ask(client: httpx.Client, base_url: str, message: str, conversation_id: str | None = None) -> ChatResult:
    t0 = time.perf_counter()
    tokens: list[str] = []
    sources: list[dict] = []
    conv_id: str | None = conversation_id
    error: str | None = None
    ttft: float | None = None

    payload = {"message": message, "conversation_id": conversation_id, "use_documents": True}
    buffer = ""
    try:
        with client.stream("POST", f"{base_url}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_text():
                buffer += chunk
                blocks, buffer = parse_sse_blocks(buffer)
                for block in blocks:
                    for line in block.splitlines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            continue
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if "conversation_id" in event:
                            conv_id = event["conversation_id"]
                        elif "token" in event:
                            if ttft is None:
                                ttft = time.perf_counter() - t0
                            tokens.append(event["token"])
                        elif "sources" in event:
                            sources = event["sources"] or []
                        elif "error" in event:
                            error = event["error"]
    except httpx.HTTPError as exc:
        error = str(exc)

    latency = time.perf_counter() - t0
    return {
        "conversation_id": conv_id,
        "answer": "".join(tokens),
        "sources": sources,
        "ttft": ttft,
        "latency": latency,
        "error": error,
    }


def top_score(sources: list[dict]) -> float | None:
    if not sources:
        return None
    return max(float(s["score"]) for s in sources)


def retrieval_hit(sources: list[dict], expected_page: int) -> bool:
    return expected_page in [s.get("page") for s in sources]


def cited_correct_page(answer: str, sources: list[dict], expected_page: int) -> bool:
    by_n = {int(s["n"]): s.get("page") for s in sources}
    return any(by_n.get(int(m.group(1))) == expected_page for m in CITE_RE.finditer(answer))


def keywords_ok(answer: str, keywords: list[str]) -> bool:
    lower = answer.lower()
    return all(k in lower for k in keywords)


def not_found_ok(answer: str, sources: list[dict]) -> bool:
    lower = answer.lower()
    return ("couldn't find" in lower or "could not find" in lower) and not sources


def wrong_refusal(answer: str) -> bool:
    lower = answer.lower()
    return "couldn't find" in lower or "could not find" in lower


def injection_ok(answer: str, forbidden: str) -> bool:
    return forbidden.lower() not in answer.lower()


def ensure_pdf_indexed(client: httpx.Client, base_url: str, pdf_path: Path) -> None:
    name = pdf_path.name
    docs = client.get(f"{base_url}/api/documents").raise_for_status().json()
    if any(d.get("filename") == name for d in docs):
        return
    with pdf_path.open("rb") as fh:
        client.post(f"{base_url}/api/documents", files={"file": (name, fh)}).raise_for_status()


def upload_doc(client: httpx.Client, base_url: str, path: Path) -> str:
    with path.open("rb") as fh:
        client.post(f"{base_url}/api/documents", files={"file": (path.name, fh)}).raise_for_status()
    for d in client.get(f"{base_url}/api/documents").raise_for_status().json():
        if d.get("filename") == path.name:
            return d["id"]
    raise RuntimeError(f"Uploaded {path.name} but it does not appear in /api/documents")


def delete_doc(client: httpx.Client, base_url: str, doc_id: str) -> None:
    client.delete(f"{base_url}/api/documents/{doc_id}").raise_for_status()


def yn(val: bool | None) -> str:
    return "-" if val is None else ("Y" if val else "N")


def failed(entry: dict[str, Any], metrics: dict[str, Any]) -> bool:
    if metrics.get("error"):
        return True
    group = entry["group"]
    if group in ("answerable", "followup"):
        return not (metrics["retrieval_hit"] and metrics["cited_correct_page"] and metrics["keywords_ok"])
    if group == "unanswerable":
        return not metrics["not_found_ok"]
    if group == "injection":
        return not metrics["injection_ok"]
    return True


def score_metrics(entry: dict[str, Any], result: ChatResult) -> dict[str, Any]:
    sources = result["sources"]
    metrics: dict[str, Any] = {
        "top_score": top_score(sources),
        "ttft": result["ttft"],
        "latency": result["latency"],
        "error": result["error"],
        "retrieval_hit": None,
        "cited_correct_page": None,
        "keywords_ok": None,
        "not_found_ok": None,
        "wrong_refusal": None,
        "injection_ok": None,
    }
    if result["error"]:
        return metrics

    group = entry["group"]
    if group in ("answerable", "followup"):
        page = entry["expected_page"]
        metrics["retrieval_hit"] = retrieval_hit(sources, page)
        metrics["cited_correct_page"] = cited_correct_page(result["answer"], sources, page)
        metrics["keywords_ok"] = keywords_ok(result["answer"], entry["expected_keywords"])
        metrics["wrong_refusal"] = wrong_refusal(result["answer"])
    elif group == "unanswerable":
        metrics["not_found_ok"] = not_found_ok(result["answer"], sources)
    elif group == "injection":
        metrics["injection_ok"] = injection_ok(result["answer"], entry["must_not_contain"])
    return metrics


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ans_fu = [r for r in rows if r["entry"]["group"] in ("answerable", "followup")]
    unans = [r for r in rows if r["entry"]["group"] == "unanswerable"]
    inj = [r for r in rows if r["entry"]["group"] == "injection"]

    def rate(items: list[dict], key: str) -> tuple[int, int]:
        return sum(1 for r in items if r["metrics"].get(key)), len(items)

    def pct(ok: int, total: int) -> str:
        return f"{ok}/{total} ({100 * ok / total:.0f}%)" if total else "0/0 (0%)"

    h_ok, h_tot = rate(ans_fu, "retrieval_hit")
    c_ok, _ = rate(ans_fu, "cited_correct_page")
    nf_ok, nf_tot = rate(unans, "not_found_ok")
    wr_ok = sum(1 for r in ans_fu if r["metrics"].get("wrong_refusal"))
    inj_pass = bool(inj and inj[0]["metrics"].get("injection_ok"))

    lats = [r["metrics"]["latency"] for r in rows]
    ttfts = [r["metrics"]["ttft"] for r in rows if r["metrics"]["ttft"] is not None]

    return {
        "retrieval_hit": pct(h_ok, h_tot),
        "citation_correct": pct(c_ok, h_tot),
        "not_found_accuracy": pct(nf_ok, nf_tot),
        "wrong_refusals": f"{wr_ok}/{len(ans_fu)}",
        "injection": "PASS" if inj_pass else "FAIL",
        "avg_latency_s": round(sum(lats) / len(lats), 2) if lats else None,
        "avg_ttft_s": round(sum(ttfts) / len(ttfts), 2) if ttfts else None,
    }


def print_progress(entry: dict[str, Any], metrics: dict[str, Any]) -> None:
    eid, group = entry["id"], entry["group"]
    lat = metrics["latency"]
    top = metrics["top_score"]
    top_s = f"{top:.2f}" if top is not None else "-"
    if group in ("answerable", "followup"):
        print(
            f"{eid}  {group}  hit={yn(metrics['retrieval_hit'])}  "
            f"cite={yn(metrics['cited_correct_page'])}  kw={yn(metrics['keywords_ok'])}  "
            f"wr={yn(not metrics.get('wrong_refusal'))}  top={top_s}  {lat:.1f}s"
        )
    elif group == "unanswerable":
        print(f"{eid}  {group}  nf={yn(metrics['not_found_ok'])}  top={top_s}  {lat:.1f}s")
    else:
        print(f"{eid}  {group}  ok={yn(metrics['injection_ok'])}  top={top_s}  {lat:.1f}s")


def summarize(rows: list[dict[str, Any]]) -> None:
    stats = summarize_rows(rows)
    fails = [r for r in rows if failed(r["entry"], r["metrics"])]

    print("\n--- Summary ---")
    print(f"Retrieval hit rate (answerable + followup): {stats['retrieval_hit']}")
    print(f"Cited correct page: {stats['citation_correct']}")
    print(f"Not-found accuracy (unanswerable): {stats['not_found_accuracy']}")
    print(f"Wrong refusals (answerable + followup): {stats['wrong_refusals']}")
    print(f"Injection resisted: {stats['injection']}")
    if stats["avg_latency_s"] is not None:
        print(f"Average latency: {stats['avg_latency_s']}s")
    if stats["avg_ttft_s"] is not None:
        print(f"Average time to first token: {stats['avg_ttft_s']}s")

    print("\n--- Failures ---")
    if not fails:
        print("(none)")
    for r in fails:
        print(f"  {r['entry']['id']}: {r['entry']['question']}")


def run_entry(client: httpx.Client, base_url: str, entry: dict[str, Any]) -> dict[str, Any]:
    group = entry["group"]
    if group == "followup":
        first_user = next(m["content"] for m in entry["history"] if m["role"] == "user")
        warmup = ask(client, base_url, first_user)
        result = ask(client, base_url, entry["question"], warmup.get("conversation_id"))
    elif group == "injection":
        doc_id = upload_doc(client, base_url, REPO_ROOT / entry["fixture_file"])
        try:
            result = ask(client, base_url, entry["question"])
        finally:
            delete_doc(client, base_url, doc_id)
    else:
        result = ask(client, base_url, entry["question"])

    metrics = score_metrics(entry, result)
    print_progress(entry, metrics)
    return {
        "id": entry["id"],
        "group": group,
        "question": entry["question"],
        "answer": result["answer"],
        "sources": result["sources"],
        "conversation_id": result["conversation_id"],
        "metrics": metrics,
        "entry": entry,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RAG golden-set evaluation")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--pdf", type=Path, default=None, help="Knowledge-base PDF to ensure is indexed")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON path (default: eval/results/<timestamp>-<label>.json)",
    )
    parser.add_argument("--label", default="baseline", help="Run label for results filename")
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    args = parser.parse_args()

    if args.pdf is None:
        print("Error: --pdf is required (path to python_basics_knowledge_base.pdf).", file=sys.stderr)
        return 1
    if not args.pdf.is_file():
        print(f"Error: PDF not found: {args.pdf}", file=sys.stderr)
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = args.out or (RESULTS_DIR / f"{ts}-{args.label}.json")

    print(
        "Note: start the backend with CHAT_TEMPERATURE=0 for comparable eval runs.",
        file=sys.stderr,
    )

    golden = json.loads(args.golden.read_text())
    base_url = args.base_url.rstrip("/")

    with httpx.Client(timeout=120.0) as client:
        try:
            client.get(f"{base_url}/api/documents").raise_for_status()
        except httpx.HTTPError as exc:
            print(f"Error: backend not reachable at {base_url}: {exc}", file=sys.stderr)
            return 1
        ensure_pdf_indexed(client, base_url, args.pdf.resolve())

        rows: list[dict[str, Any]] = []
        for entry in golden:
            rows.append(run_entry(client, base_url, entry))

    stats = summarize_rows(rows)
    out_rows = [{k: v for k, v in r.items() if k != "entry"} for r in rows]
    payload = {
        "label": args.label,
        "timestamp": ts,
        "temperature_note": "Set CHAT_TEMPERATURE=0 on the server before running.",
        "summary": stats,
        "rows": out_rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nWrote {out_path}")
    summarize(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
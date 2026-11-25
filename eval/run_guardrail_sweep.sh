#!/usr/bin/env bash
# Restart the backend between runs so builder.py picks up flag changes.
set -euo pipefail
PDF="${1:?Usage: $0 /path/to/python_basics_knowledge_base.pdf}"
BASE="${2:-http://localhost:8000}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

run_one() {
  local label="$1"
  shift
  export CHAT_TEMPERATURE=0 "$@"
  python3 "$ROOT/eval/run_eval.py" --pdf "$PDF" --base-url "$BASE" --label "$label"
}

run_one baseline \
  ENABLE_INPUT_GUARD=false ENABLE_RELEVANCE_GRADING=false \
  ENABLE_OUTPUT_CHECK=false ENABLE_PROMPT_REORDER=false

run_one +prompt_reorder \
  ENABLE_PROMPT_REORDER=true

run_one +input_guard \
  ENABLE_INPUT_GUARD=true

run_one +relevance_grading \
  ENABLE_RELEVANCE_GRADING=true

run_one +output_check \
  ENABLE_OUTPUT_CHECK=true

run_one all_on \
  ENABLE_INPUT_GUARD=true ENABLE_RELEVANCE_GRADING=true \
  ENABLE_OUTPUT_CHECK=true ENABLE_PROMPT_REORDER=true

echo "Compare with:"
echo "  python3 eval/compare_runs.py eval/results/*-<label>.json"
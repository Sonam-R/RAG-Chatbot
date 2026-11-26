"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";

const STORAGE_KEY = "theme-preference";

export type ThemeMode = "light" | "dark" | "system";

function readStoredMode(): ThemeMode {
  if (typeof window === "undefined") return "system";
  return (localStorage.getItem(STORAGE_KEY) as ThemeMode | null) ?? "system";
}

function systemPrefersDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function useTheme() {
  const [mode, setModeState] = useState<ThemeMode>(readStoredMode);
  const [systemDark, setSystemDark] = useState(systemPrefersDark);

  const resolvedDark = useMemo(
    () => (mode === "dark" ? true : mode === "light" ? false : systemDark),
    [mode, systemDark],
  );

  useLayoutEffect(() => {
    document.documentElement.classList.toggle("dark", resolvedDark);
    document.documentElement.dataset.theme = resolvedDark ? "dark" : "light";
  }, [resolvedDark]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setSystemDark(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const setMode = useCallback((m: ThemeMode) => {
    localStorage.setItem(STORAGE_KEY, m);
    setModeState(m);
  }, []);

  const toggle = useCallback(() => {
    setMode(resolvedDark ? "light" : "dark");
  }, [resolvedDark, setMode]);

  return { mode, resolvedDark, setMode, toggle };
}
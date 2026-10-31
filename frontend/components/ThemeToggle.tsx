"use client";
import { useEffect, useState } from "react";

type Theme = "light" | "dark";

export function applyTheme(t: Theme) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem("applypilot_theme", t); } catch {}
}

export function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem("applypilot_theme");
    if (saved === "dark" || saved === "light") return saved;
  } catch {}
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  useEffect(() => { const t = initialTheme(); setTheme(t); applyTheme(t); }, []);
  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      className="theme-toggle"
      aria-label={`Switch to ${next} mode`}
      aria-pressed={theme === "dark"}
      title={`Switch to ${next} mode`}
      onClick={() => { setTheme(next); applyTheme(next); }}
    >
      {theme === "dark" ? "\u2600\uFE0F Light" : "\uD83C\uDF19 Dark"}
    </button>
  );
}

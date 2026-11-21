import { useCallback, useEffect, useState } from "react";
import { readStored, writeStored } from "./format";

export type Theme = "light" | "dark";

const KEY = "fs-theme";

function systemTheme(): Theme {
  // Light is the default; dark only when the user picks it.
  return "light";
}

function currentTheme(): Theme {
  const attr = document.documentElement.getAttribute("data-theme");
  return attr === "light" || attr === "dark" ? attr : systemTheme();
}

export function useTheme(): { theme: Theme; toggle: () => void; setTheme: (t: Theme) => void } {
  const [theme, setThemeState] = useState<Theme>(currentTheme);

  const setTheme = useCallback((t: Theme) => {
    document.documentElement.setAttribute("data-theme", t);
    writeStored(KEY, t);
    setThemeState(t);
  }, []);

  const toggle = useCallback(() => setTheme(currentTheme() === "dark" ? "light" : "dark"), [setTheme]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (): void => {
      if (!readStored(KEY)) setThemeState(systemTheme());
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return { theme, toggle, setTheme };
}

/** The ASHA view starts in the light theme (bright ambient light) unless she has chosen otherwise. */
export function applyAshaDefaultTheme(): void {
  if (!readStored(KEY)) document.documentElement.setAttribute("data-theme", "light");
}

export function releaseAshaDefaultTheme(): void {
  if (!readStored(KEY)) document.documentElement.removeAttribute("data-theme");
}

import { useEffect, useRef, useState } from "react";
import { confidenceWord, cx, pct } from "../../lib/format";

function tone(c: number): { bar: string; text: string } {
  if (c >= 0.75) return { bar: "bg-confHigh", text: "text-confHigh" };
  if (c >= 0.45) return { bar: "bg-confUnc", text: "text-confUnc" };
  return { bar: "bg-confUnk", text: "text-confUnk" };
}

interface MeterProps {
  value: number;
  label?: string;
  width?: string;
  showWord?: boolean;
  /** Animate from this value to `value` (600 ms, ease-out). Used once after an ASHA report. */
  animateFrom?: number;
  className?: string;
}

export function ConfidenceMeter({ value, label = "Confidence", width = "w-28", showWord = true, animateFrom, className }: MeterProps) {
  const v = Math.min(1, Math.max(0, value));
  const [shown, setShown] = useState(animateFrom ?? v);
  const raf = useRef(0);

  useEffect(() => {
    if (animateFrom === undefined) {
      setShown(v);
      return;
    }
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setShown(v);
      return;
    }
    const start = performance.now();
    const from = animateFrom;
    const step = (now: number): void => {
      const t = Math.min(1, (now - start) / 600);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(from + (v - from) * eased);
      if (t < 1) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [v, animateFrom]);

  const word = confidenceWord(v);
  const t = tone(shown);
  return (
    <div className={cx("inline-flex items-center gap-2", className)}>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(v * 100)}
        aria-valuetext={`${Math.round(v * 100)} percent, ${word.toLowerCase()}`}
        className={cx("h-2 overflow-hidden rounded-full bg-sunken", width)}
      >
        <div className={cx("h-2 rounded-full", t.bar)} style={{ width: `${shown * 100}%` }} />
      </div>
      <span className={cx("mono text-sm", t.text)}>{pct(shown)}</span>
      {showWord && <span className={cx("text-sm font-semibold", t.text)}>{word}</span>}
    </div>
  );
}

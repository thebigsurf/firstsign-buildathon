import { Mic, RotateCcw, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { cx } from "../../lib/format";
import { PulseLine } from "./Pulse";

export type RecorderStatus = "idle" | "recording" | "recorded" | "denied" | "unsupported";

export interface RecordedAudio {
  blob: Blob;
  fileName: string;
  seconds: number;
}

const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];

function pickMime(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return MIME_CANDIDATES.find((m) => MediaRecorder.isTypeSupported(m));
}

function extFor(mime: string): string {
  if (mime.includes("webm")) return "webm";
  if (mime.includes("mp4")) return "m4a";
  if (mime.includes("ogg")) return "ogg";
  return "audio";
}

function canRecord(): boolean {
  return Boolean(pickMime()) && typeof navigator.mediaDevices?.getUserMedia === "function";
}

export const mmss = (s: number): string => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

interface UseRecorder {
  status: RecorderStatus;
  seconds: number;
  analyser: AnalyserNode | null;
  announcement: string;
  start: () => Promise<void>;
  stop: () => void;
  reset: () => void;
}

/** MediaRecorder wrapper: tap to start, tap to stop, auto-stop at `maxSeconds`, audio is kept for playback. */
export function useRecorder(maxSeconds: number, onRecorded: (audio: RecordedAudio | null) => void, haptic = false): UseRecorder {
  const [status, setStatus] = useState<RecorderStatus>(() => (canRecord() ? "idle" : "unsupported"));
  const [seconds, setSeconds] = useState(0);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
  const [announcement, setAnnouncement] = useState("");

  const recRef = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const timerRef = useRef(0);
  const startedAt = useRef(0);
  const cb = useRef(onRecorded);
  cb.current = onRecorded;

  const cleanup = useCallback(() => {
    window.clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    void ctxRef.current?.close().catch(() => undefined);
    ctxRef.current = null;
    setAnalyser(null);
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const buzz = useCallback(() => {
    if (haptic && "vibrate" in navigator) navigator.vibrate(30);
  }, [haptic]);

  const stop = useCallback(() => {
    const rec = recRef.current;
    if (rec && rec.state !== "inactive") rec.stop();
  }, []);

  const start = useCallback(async () => {
    const mime = pickMime();
    if (!mime || !canRecord()) {
      setStatus("unsupported");
      return;
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      const name = err instanceof DOMException ? err.name : "";
      setStatus(name === "NotFoundError" || name === "OverconstrainedError" ? "unsupported" : "denied");
      return;
    }
    streamRef.current = stream;
    chunks.current = [];
    const rec = new MediaRecorder(stream, { mimeType: mime });
    recRef.current = rec;

    const AudioCtx = window.AudioContext;
    const ctx = new AudioCtx();
    ctxRef.current = ctx;
    const node = ctx.createAnalyser();
    node.fftSize = 256;
    ctx.createMediaStreamSource(stream).connect(node);
    setAnalyser(node);

    rec.ondataavailable = (e: BlobEvent): void => {
      if (e.data.size > 0) chunks.current.push(e.data);
    };
    rec.onstop = (): void => {
      const elapsed = Math.max(1, Math.round((Date.now() - startedAt.current) / 1000));
      const blob = new Blob(chunks.current, { type: mime });
      cleanup();
      buzz();
      setSeconds(elapsed);
      setStatus("recorded");
      setAnnouncement(`Recording stopped, ${elapsed} seconds`);
      cb.current({ blob, fileName: `recording.${extFor(mime)}`, seconds: elapsed });
    };

    startedAt.current = Date.now();
    rec.start(250);
    buzz();
    setSeconds(0);
    setStatus("recording");
    setAnnouncement("Recording started");
    timerRef.current = window.setInterval(() => {
      const s = Math.round((Date.now() - startedAt.current) / 1000);
      setSeconds(s);
      if ([30, 60, 80].includes(s)) setAnnouncement(`${s} seconds`);
      if (s >= maxSeconds) stop();
    }, 500);
  }, [buzz, cleanup, maxSeconds, stop]);

  const reset = useCallback(() => {
    const rec = recRef.current;
    if (rec && rec.state !== "inactive") {
      rec.onstop = null;
      rec.stop();
    }
    cleanup();
    setSeconds(0);
    setStatus(canRecord() ? "idle" : "unsupported");
    cb.current(null);
  }, [cleanup]);

  return { status, seconds, analyser, announcement, start, stop, reset };
}

function Waveform({ analyser, active }: { analyser: AnalyserNode | null; active: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx2d = canvas.getContext("2d");
    if (!ctx2d) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx2d.scale(dpr, dpr);
    const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#0B5C7A";
    const bars = Math.floor(w / 5);
    const data = new Uint8Array(analyser?.frequencyBinCount ?? 0);
    let raf = 0;

    const draw = (): void => {
      ctx2d.clearRect(0, 0, w, h);
      ctx2d.fillStyle = accent;
      if (analyser && active) analyser.getByteFrequencyData(data);
      for (let i = 0; i < bars; i++) {
        const v = analyser && active ? data[Math.floor((i / bars) * data.length * 0.7)] / 255 : 0;
        const bh = Math.max(3, v * h);
        ctx2d.fillRect(i * 5, (h - bh) / 2, 3, bh);
      }
      if (analyser && active) raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [analyser, active]);

  return <canvas ref={ref} aria-hidden="true" className="h-[72px] w-full rounded-xl bg-sunken" />;
}

interface RecorderProps {
  maxSeconds?: number;
  big?: boolean;
  haptic?: boolean;
  startLabel: ReactNode;
  stopLabel: ReactNode;
  recordingLabel: ReactNode;
  againLabel: ReactNode;
  deniedMessage: ReactNode;
  unsupportedMessage: ReactNode;
  onRecorded: (audio: RecordedAudio | null) => void;
  disabled?: boolean;
  lang?: string;
}

export function Recorder({
  maxSeconds = 90,
  big = false,
  haptic = false,
  startLabel,
  stopLabel,
  recordingLabel,
  againLabel,
  deniedMessage,
  unsupportedMessage,
  onRecorded,
  disabled,
  lang,
}: RecorderProps) {
  const [url, setUrl] = useState<string | null>(null);
  const urlRef = useRef<string | null>(null);

  const handle = useCallback(
    (audio: RecordedAudio | null) => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      urlRef.current = audio ? URL.createObjectURL(audio.blob) : null;
      setUrl(urlRef.current);
      onRecorded(audio);
    },
    [onRecorded],
  );
  const inner = useRecorder(maxSeconds, handle, haptic);
  useEffect(
    () => () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    },
    [],
  );

  const { status, seconds } = inner;
  const live = status === "recording";
  const size = big ? "h-[120px] w-[120px] [@media(max-height:700px)]:h-24 [@media(max-height:700px)]:w-24" : "h-16 w-16";
  const remaining = maxSeconds - seconds;

  if (status === "denied" || status === "unsupported") {
    return (
      <div role="alert" className="panel-warn" lang={lang}>
        {status === "denied" ? deniedMessage : unsupportedMessage}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4">
      {status !== "recorded" && (
        <>
          <button
            type="button"
            onClick={live ? inner.stop : () => void inner.start()}
            disabled={disabled}
            aria-label={live ? "Stop recording" : "Start recording"}
            aria-pressed={live}
            className={cx(
              "flex items-center justify-center rounded-full shadow-2 focus-visible:outline-offset-4 disabled:opacity-60",
              size,
              live ? "bg-alert text-onAlert ring-4 ring-alert/30 animate-ring motion-reduce:animate-none" : "bg-accent text-accentFg",
            )}
          >
            {live ? <Square size={big ? 44 : 26} fill="currentColor" aria-hidden="true" /> : <Mic size={big ? 48 : 28} aria-hidden="true" />}
          </button>
          <div className="text-center" lang={lang}>
            {live ? stopLabel : startLabel}
          </div>
        </>
      )}

      {status === "idle" && (
        <div className="flex h-[72px] w-full items-center justify-center rounded-xl bg-sunken">
          <PulseLine width={96} />
        </div>
      )}
      {live && (
        <div className="w-full space-y-3">
          <Waveform analyser={inner.analyser} active />
          <div className="flex items-center justify-center gap-3">
            <span aria-hidden="true" className="h-3 w-3 rounded-full bg-alert" />
            <span lang={lang} className="font-semibold">
              {recordingLabel}
            </span>
            <span className="mono text-num-lg tabular-nums" aria-hidden="true">
              {mmss(seconds)}
            </span>
          </div>
          {remaining <= 10 && (
            <p className="text-center text-sm text-watch" aria-hidden="true">
              {remaining}s left
            </p>
          )}
        </div>
      )}
      {status === "recorded" && url && (
        <div className="w-full space-y-3">
          <p className="mono text-center">{mmss(seconds)}</p>
          <audio controls src={url} className="w-full" aria-label="Play back your recording" />
          <button
            type="button"
            onClick={inner.reset}
            className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-borderStrong bg-surface font-semibold hover:bg-sunken"
          >
            <RotateCcw size={18} aria-hidden="true" />
            <span lang={lang}>{againLabel}</span>
          </button>
        </div>
      )}
      <div className="sr-only" aria-live="polite" role="status">
        {inner.announcement}
      </div>
    </div>
  );
}

import { CheckCheck, Image as ImageIcon, Mic, Send, Square, TriangleAlert, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../lib/AuthContext";
import { Button } from "../components/ui/Button";
import { mmss, useRecorder, type RecordedAudio } from "../components/ui/Recorder";
import { useToast } from "../components/ui/Toast";
import { baseName, pickSamples, type Sample } from "../lib/chemistSamples";
import { cx, fmtTime, langName, readStored, writeStored } from "../lib/format";
import { toApiError, useAsync, useDocumentTitle } from "../lib/hooks";
import { useRefData } from "../lib/refdata";

const CHEMIST_KEY = "firstsign.chemist";

type Draft =
  | { kind: "audio"; blob: Blob; name: string; seconds: number; url: string }
  | { kind: "image"; blob: Blob; name: string; url: string };

interface Bubble {
  key: string;
  kind: "text" | "audio" | "image";
  text?: string;
  url?: string;
  at: string;
  state: "sending" | "sent" | "failed";
  messageId?: string;
  retry?: () => void;
}

interface Payload {
  chemistId: string;
  file?: Blob;
  fileName?: string;
  text?: string;
}

function BubbleView({ b }: { b: Bubble }) {
  return (
    <li className="flex justify-end">
      <div className="max-w-[85%] rounded-lg rounded-tr-none bg-accentSoft p-2 text-sm text-text shadow-1">
        {b.kind === "text" && <p className="m-0 whitespace-pre-wrap break-words">{b.text}</p>}
        {b.kind === "audio" && b.url && <audio controls src={b.url} className="h-10 w-56 max-w-full" aria-label="Your voice note" />}
        {b.kind === "image" && b.url && <img src={b.url} alt="Photo of your handwritten list" className="max-h-48 rounded-md" />}
        <p className="m-0 mt-1 flex items-center justify-end gap-1 text-xs text-muted">
          {fmtTime(b.at)}
          {b.state === "sent" && (
            <>
              <CheckCheck size={14} aria-hidden="true" className="text-accentText" />
              <span className="sr-only">Delivered</span>
            </>
          )}
          {b.state === "sending" && <span>Sending...</span>}
          {b.state === "failed" && (
            <span className="inline-flex items-center gap-1 font-semibold text-alert">
              <TriangleAlert size={14} aria-hidden="true" /> Not sent
              {b.retry && (
                <button type="button" onClick={b.retry} className="ml-1 min-h-8 underline">
                  Try again
                </button>
              )}
            </span>
          )}
        </p>
      </div>
    </li>
  );
}

const STEPS = [
  "It appears in the distributor's inbox as a new message.",
  "Gemini reads it. Any line it is unsure about is flagged for a clerk.",
  "A clerk approves, and the order is logged and ready to bill.",
];

export function Chemist() {
  useDocumentTitle("Chemist");
  const { chemists, distributor, areaOf, chemistById } = useRefData();
  const toast = useToast();
  const navigate = useNavigate();
  const { user } = useAuth();
  const fixedChemist = user?.roleId === "chemist" ? user.chemistId : undefined;
  const [chemistId, setChemistId] = useState<string>(() => fixedChemist ?? readStored(CHEMIST_KEY) ?? "");
  const [text, setText] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [busy, setBusy] = useState(false);
  const urls = useRef<string[]>([]);
  const logRef = useRef<HTMLUListElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const chemist = chemistById(chemistId) ?? chemists[0];
  const effectiveId = chemist?.chemist_id ?? "";
  const distName = distributor?.name?.replace(/ Distributors$/, "") ?? "Sai Krupa Pharma";

  const inbox = useAsync((s) => api.inbox(s), []);
  const samples = useMemo(
    () => pickSamples(inbox.data ?? [], (id) => chemistById(id)?.shop_name ?? id),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [inbox.data, chemists],
  );

  useEffect(
    () => () => {
      urls.current.forEach((u) => URL.revokeObjectURL(u));
    },
    [],
  );
  useEffect(() => {
    logRef.current?.lastElementChild?.scrollIntoView({ block: "nearest" });
  }, [bubbles]);

  const makeUrl = (blob: Blob): string => {
    const u = URL.createObjectURL(blob);
    urls.current.push(u);
    return u;
  };

  const onRecorded = useCallback((a: RecordedAudio | null) => {
    if (!a) {
      setDraft(null);
      return;
    }
    const u = URL.createObjectURL(a.blob);
    urls.current.push(u);
    setDraft({ kind: "audio", blob: a.blob, name: a.fileName, seconds: a.seconds, url: u });
  }, []);
  const rec = useRecorder(60, onRecorded);

  const choose = (id: string): void => {
    setChemistId(id);
    writeStored(CHEMIST_KEY, id);
  };

  const deliver = useCallback(
    async (key: string, payload: Payload): Promise<void> => {
      setBubbles((cur) => cur.map((b) => (b.key === key ? { ...b, state: "sending", retry: undefined } : b)));
      try {
        const res = await api.chemistSend({ chemistId: payload.chemistId, file: payload.file, fileName: payload.fileName, text: payload.text });
        setBubbles((cur) => cur.map((b) => (b.key === key ? { ...b, state: "sent", messageId: res.message_id, retry: undefined } : b)));
        toast.show("success", "Sent. It is now in the distributor's inbox.", {
          label: "Open the inbox",
          onClick: () => navigate(`/distributor/inbox?msg=${encodeURIComponent(res.message_id)}`),
        });
      } catch (err) {
        const retry = (): void => void deliver(key, payload);
        setBubbles((cur) => cur.map((b) => (b.key === key ? { ...b, state: "failed", retry } : b)));
        toast.show("error", `Could not send. ${toApiError(err).message}`);
      }
    },
    [navigate, toast],
  );

  const send = async (kind: Bubble["kind"], payload: Payload, url?: string): Promise<void> => {
    const key = `b${Date.now()}${Math.random().toString(36).slice(2, 6)}`;
    setBubbles((cur) => [...cur, { key, kind, text: payload.text, url, at: new Date().toISOString(), state: "sending" }]);
    setBusy(true);
    await deliver(key, payload);
    setBusy(false);
  };

  const submit = async (): Promise<void> => {
    if (!effectiveId || busy) return;
    if (draft) {
      const d = draft;
      setDraft(null);
      rec.reset();
      await send(d.kind, { chemistId: effectiveId, file: d.blob, fileName: d.name }, d.url);
    } else if (text.trim()) {
      const t = text.trim();
      setText("");
      await send("text", { chemistId: effectiveId, text: t });
    }
  };

  const onPhoto = (file: File | undefined): void => {
    if (!file) return;
    rec.reset();
    setDraft({ kind: "image", blob: file, name: file.name, url: makeUrl(file) });
  };

  const sendSample = async (s: Sample): Promise<void> => {
    if (busy) return;
    setBusy(true);
    try {
      const res = await fetch(s.url);
      if (!res.ok) throw new Error("sample missing");
      const blob = await res.blob();
      choose(s.chemistId);
      setBusy(false);
      await send(s.kind, { chemistId: s.chemistId, file: blob, fileName: baseName(s.media) }, makeUrl(blob));
    } catch {
      toast.show("error", "Could not load that sample. Check the server is running.");
      setBusy(false);
    }
  };

  const recording = rec.status === "recording";
  const hasContent = Boolean(draft) || text.trim().length > 0;
  const micUnavailable = rec.status === "unsupported" || rec.status === "denied";

  return (
    <div className="mx-auto max-w-[1100px] px-4 py-6 md:px-6 xl:px-8">
      <header className="mb-6 space-y-1">
        <h1 className="text-h1">
          <span lang="hi">अपना ऑर्डर भेजें</span> <span className="text-muted">/ Send your order</span>
        </h1>
        <p className="m-0 max-w-2xl text-muted">
          <span lang="hi">आप जैसे रोज़ WhatsApp पर ऑर्डर भेजते हैं, वैसे ही भेजिए: बोलकर, पर्ची की फ़ोटो, या लिखकर।</span> Send it the way you
          always do. It lands in the distributor&apos;s inbox, ready to check and bill.
        </p>
      </header>

      <div className="grid items-start gap-8 lg:grid-cols-2">
        <section aria-label="Chemist phone, simulated chat" className="mx-auto w-full max-w-[380px]">
          <div className="overflow-hidden rounded-[2rem] border-4 border-borderStrong bg-surface shadow-3">
            <div className="flex items-center gap-3 border-b border-border bg-accent px-4 py-3 text-accentFg">
              <span
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accentFg font-display font-bold text-accent"
                aria-hidden="true"
              >
                SK
              </span>
              <div className="min-w-0">
                <p className="m-0 truncate font-semibold">{distName}</p>
                <p className="m-0 text-xs opacity-90">
                  <span lang="hi">वितरक</span> · Distributor
                </p>
              </div>
            </div>

            <div className="flex h-[380px] flex-col bg-sunken">
              <p className="m-0 px-3 pt-2 text-center text-xs text-muted">Simulated chat. No real WhatsApp message is sent.</p>
              <div role="log" aria-live="polite" aria-label="Messages you sent" className="flex-1 overflow-y-auto p-3" tabIndex={0}>
                {bubbles.length === 0 && (
                  <p className="m-0 mt-8 text-center text-sm text-muted">
                    <span lang="hi">यहाँ से ऑर्डर भेजिए।</span>
                    <br />
                    Nothing sent yet.
                  </p>
                )}
                {bubbles.length > 0 && (
                  <ul ref={logRef} className="m-0 list-none space-y-2 p-0">
                    {bubbles.map((b) => (
                      <BubbleView key={b.key} b={b} />
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {recording && (
              <div className="flex items-center gap-3 border-t border-border bg-alertBg px-4 py-2 text-alert" role="status">
                <span aria-hidden="true" className="h-3 w-3 animate-pulse rounded-full bg-alert motion-reduce:animate-none" />
                <span lang="hi" className="font-semibold">
                  रिकॉर्डिंग चल रही है
                </span>
                <span className="mono ml-auto tabular-nums">{mmss(rec.seconds)}</span>
              </div>
            )}
            {draft && (
              <div className="flex items-center gap-2 border-t border-border bg-surface px-3 py-2">
                {draft.kind === "audio" ? (
                  <audio controls src={draft.url} className="h-10 min-w-0 flex-1" aria-label="Play back your voice note before sending" />
                ) : (
                  <img src={draft.url} alt="Photo ready to send" className="h-12 w-12 rounded-md object-cover" />
                )}
                <button
                  type="button"
                  aria-label="Remove this attachment"
                  onClick={() => {
                    setDraft(null);
                    rec.reset();
                  }}
                  className="flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-sunken"
                >
                  <X size={18} aria-hidden="true" />
                </button>
              </div>
            )}

            <form
              className="flex items-center gap-2 border-t border-border bg-surface p-2"
              onSubmit={(e) => {
                e.preventDefault();
                void submit();
              }}
            >
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                tabIndex={-1}
                aria-label="Choose a photo of your list"
                onChange={(e) => onPhoto(e.target.files?.[0])}
              />
              <button
                type="button"
                aria-label="Attach a photo of your list"
                onClick={() => fileRef.current?.click()}
                className="flex min-h-11 min-w-11 items-center justify-center rounded-full hover:bg-sunken"
              >
                <ImageIcon size={22} strokeWidth={1.75} aria-hidden="true" />
              </button>
              <label className="min-w-0 flex-1">
                <span className="sr-only">Type your order</span>
                <input
                  className="input w-full"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="ऑर्डर लिखें / Type your order"
                  disabled={recording}
                  autoComplete="off"
                />
              </label>
              {hasContent ? (
                <button
                  type="submit"
                  disabled={busy || !effectiveId}
                  aria-label="Send"
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent text-accentFg disabled:opacity-60"
                >
                  <Send size={20} strokeWidth={1.75} aria-hidden="true" />
                </button>
              ) : (
                <button
                  type="button"
                  disabled={micUnavailable || busy}
                  aria-label={recording ? "Stop recording" : "Record a voice note"}
                  aria-pressed={recording}
                  onClick={recording ? rec.stop : () => void rec.start()}
                  className={cx(
                    "flex h-11 w-11 shrink-0 items-center justify-center rounded-full disabled:opacity-60",
                    recording ? "bg-alert text-onAlert" : "bg-accent text-accentFg",
                  )}
                >
                  {recording ? <Square size={18} fill="currentColor" aria-hidden="true" /> : <Mic size={22} strokeWidth={1.75} aria-hidden="true" />}
                </button>
              )}
            </form>
            {micUnavailable && (
              <p className="m-0 border-t border-border bg-watchBg px-3 py-2 text-sm text-watch" role="status">
                <span lang="hi">माइक्रोफ़ोन नहीं चल रहा। नीचे से नमूना चुनें या लिखें।</span> Microphone is not available. Pick a sample or type.
              </p>
            )}
          </div>
        </section>

        <div className="space-y-6">
          <section aria-labelledby="who-h" className="card space-y-3">
            <h2 id="who-h" className="text-h3">
              {fixedChemist ? (
                "Your shop"
              ) : (
                <>
                  <span lang="hi">आप कौन हैं?</span> <span className="text-muted">/ Which chemist are you?</span>
                </>
              )}
            </h2>
            {fixedChemist && chemist && (
              <p className="m-0 font-medium">
                {chemist.shop_name}, {areaOf(chemist.pin)} ({chemist.pin})
              </p>
            )}
            <label className={cx("block text-sm font-medium", fixedChemist && "hidden")}>
              Chemist
              <select className="input mt-1 w-full" value={effectiveId} onChange={(e) => choose(e.target.value)} disabled={chemists.length === 0}>
                {chemists.map((c) => (
                  <option key={c.chemist_id} value={c.chemist_id}>
                    {c.shop_name}, {areaOf(c.pin)} ({c.pin})
                  </option>
                ))}
              </select>
            </label>
            {chemist && (
              <p className="m-0 text-sm text-muted">
                {chemist.owner_first_name} · speaks <span lang={chemist.language}>{langName(chemist.language)}</span>. Simulated shop.
              </p>
            )}
          </section>

          <section aria-labelledby="sample-h" className="card space-y-3">
            <h2 id="sample-h" className="text-h3">
              <span lang="hi">या नमूना आज़माएँ</span> <span className="text-muted">/ Or try a sample</span>
            </h2>
            <p className="m-0 text-sm text-muted">Bundled demo voice notes and handwritten lists. Each one is sent as the chemist it came from.</p>
            {inbox.loading && !inbox.data ? (
              <p className="m-0 text-sm text-muted">Loading samples...</p>
            ) : samples.length === 0 ? (
              <p className="m-0 text-sm text-muted">No samples found. Record a voice note, attach a photo or type an order.</p>
            ) : (
              <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                {samples.map((s) => (
                  <li key={s.id}>
                    <Button
                      variant="secondary"
                      disabled={busy}
                      onClick={() => void sendSample(s)}
                      icon={s.kind === "audio" ? <Mic size={16} aria-hidden="true" /> : <ImageIcon size={16} aria-hidden="true" />}
                    >
                      {s.label}
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="next-h" className="space-y-3">
            <h2 id="next-h" className="text-h3">
              What happens next
            </h2>
            <ol className="m-0 list-none space-y-2 p-0 text-sm">
              {STEPS.map((t, i) => (
                <li key={t} className="flex gap-3">
                  <span className="mono flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent text-accentFg" aria-hidden="true">
                    {i + 1}
                  </span>
                  {t}
                </li>
              ))}
            </ol>
            <Button variant="ghost" onClick={() => navigate("/distributor/inbox")}>
              Open the distributor inbox
            </Button>
          </section>
        </div>
      </div>
    </div>
  );
}

import { Check, FileUp, Keyboard, Minus, Plus, RefreshCw, TriangleAlert, WifiOff } from "lucide-react";
import { useCallback, useEffect, useId, useMemo, useState, type ReactNode } from "react";
import { api } from "../api";
import { useAuth } from "../lib/AuthContext";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ConfidenceMeter } from "../components/ui/ConfidenceMeter";
import { AshaRecentTable } from "../components/officer/ExtendedPanels";
import { MiniChart } from "../components/ui/MiniChart";
import { Modal } from "../components/ui/Modal";
import { Recorder, type RecordedAudio } from "../components/ui/Recorder";
import { Skeleton } from "../components/ui/States";
import { cx, readStored, writeStored } from "../lib/format";
import { ashaSeries, lastDays } from "../lib/extended";
import { toApiError, useAsync, useDocumentTitle } from "../lib/hooks";
import { useRefData } from "../lib/refdata";
import { applyAshaDefaultTheme, releaseAshaDefaultTheme } from "../lib/theme";
import { tr, type AshaKey, type AshaLang } from "../strings";
import type { Asha, AshaReportResult, AshaVisit } from "../types";

type Step = "list" | "record" | "confirm" | "done";
const STEP_NO: Record<Step, number> = { list: 1, record: 2, confirm: 3, done: 4 };
const ASHA_KEY = "fs-asha";

/** Hindi (or Marathi) first, English beneath. */
function Bi({ k, lang, onAccent = false, inline = false }: { k: AshaKey; lang: AshaLang; onAccent?: boolean; inline?: boolean }) {
  const t = tr(k, lang);
  return (
    <>
      <span lang={t.lang}>{t.primary}</span>
      {inline ? " " : null}
      <span className={cx(inline ? "text-sm" : "block text-sm font-normal", onAccent ? "opacity-90" : "text-muted")}>{inline ? `/ ${t.secondary}` : t.secondary}</span>
    </>
  );
}

function BottomBar({ children }: { children: ReactNode }) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 shadow-3">
      <div className="mx-auto flex max-w-xl flex-col gap-2">{children}</div>
    </div>
  );
}

const PRIORITY: Record<number, "High" | "Medium" | "Low"> = { 1: "High", 2: "High", 3: "Medium", 4: "Medium" };

function Progress({ step, lang }: { step: Step; lang: AshaLang }) {
  const n = STEP_NO[step];
  return (
    <div className="flex items-center justify-between gap-3">
      <div aria-hidden="true" className="flex gap-1.5">
        {[1, 2, 3, 4].map((i) => (
          <span key={i} className={cx("h-2.5 w-7 rounded-full", i <= n ? "bg-accent" : "bg-sunken")} />
        ))}
      </div>
      <p className="m-0 text-sm text-muted">
        <span lang={lang === "mr" ? "mr" : "hi"}>चरण {n} / 4</span> · Step {n} of 4
      </p>
    </div>
  );
}

// ------------------------------------------------------------------ who am I

function ChooseAsha({ ashas, onChoose }: { ashas: Asha[]; onChoose: (id: string) => void }) {
  return (
    <div className="space-y-4">
      <h1 className="text-asha-h">
        <span lang="hi">अपना नाम चुनें</span>
        <span className="block text-sm font-normal text-muted">Choose your name</span>
      </h1>
      {ashas.length === 0 ? (
        <div className="space-y-3">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : (
        <ul className="m-0 list-none space-y-3 p-0">
          {ashas.map((a) => (
            <li key={a.asha_id}>
              <button
                type="button"
                onClick={() => onChoose(a.asha_id)}
                className="flex min-h-14 w-full items-center justify-between gap-3 rounded-xl border border-borderStrong bg-surface px-4 text-left text-asha hover:bg-sunken"
              >
                <span>{a.first_name}</span>
                <span className="mono text-sm text-muted">{a.pin}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="text-sm text-muted">Names are simulated for this demo.</p>
    </div>
  );
}

// ------------------------------------------------------------------ step 1: visit list

/** Fallback when no officer list is approved yet: she can still report on any locality in her own pin code. */
function OwnPinLocalities({ asha, lang, onRecord }: { asha: Asha; lang: AshaLang; onRecord: (v: AshaVisit) => void }) {
  const places = useAsync((s) => api.localities(asha.pin, s), [asha.pin]);
  const list = places.data ?? [];
  if (list.length === 0) return null;
  const t = tr("reportWithoutList", lang);
  return (
    <section aria-labelledby="own-pin-h" className="space-y-3">
      <h2 id="own-pin-h" className="text-asha font-semibold">
        <span lang={t.lang}>{t.primary}</span>
        <span className="block text-sm font-normal text-muted">{t.secondary}</span>
      </h2>
      <ul className="m-0 list-none space-y-2 p-0">
        {list.map((l) => (
          <li key={l.locality_id}>
            <Button variant="secondary" size="asha" onClick={() => onRecord({ locality_id: l.locality_id, name: l.name, landmark: l.landmark, priority: 0, reason: "" })}>
              <span className="text-left">
                {l.name}
                <span className="block text-sm font-normal text-muted">{l.landmark}</span>
              </span>
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function RecentReports({ asha, lang }: { asha: Asha; lang: AshaLang }) {
  const q = useAsync((s) => api.ashaHistory(asha.pin, 14, s), [asha.pin]);
  const rows = lastDays(q.data ?? [], 14).reverse();
  const t = tr("lastDays", lang);
  const series = ashaSeries(rows);
  if (q.loading && !q.data) return <Skeleton className="h-32 w-full" />;
  return (
    <section aria-labelledby="recent-h" className="space-y-3">
      <h2 id="recent-h" className="text-asha font-semibold">
        <span lang={t.lang}>{t.primary}</span>
        <span className="block text-sm font-normal text-muted">{t.secondary} (simulated)</span>
      </h2>
      {rows.length === 0 ? (
        <p className="m-0 text-base text-muted">
          <Bi k="noHistory" lang={lang} inline />
        </p>
      ) : (
        <div className="card space-y-3 p-4">
          <MiniChart dates={series.dates} series={series.series} label={`Your reports, last 14 days: households with fever, diarrhoea and cough.`} />
          <AshaRecentTable
            rows={rows}
            headers={{ day: tr("dayCol", lang).primary, homes: tr("homes", lang).primary, fever: tr("fever", lang).primary, diarrhoea: tr("diarrhoea", lang).primary, cough: tr("cough", lang).primary }}
          />
        </div>
      )}
    </section>
  );
}

function VisitList({ asha, lang, onRecord }: { asha: Asha; lang: AshaLang; onRecord: (v: AshaVisit) => void }) {
  const visits = useAsync((s) => api.ashaVisits(asha.asha_id, s), [asha.asha_id]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-asha-h">
          <Bi k="todaysVisits" lang={lang} />
        </h1>
        <p className="m-0 mt-1 text-asha">
          {asha.first_name} · <span className="mono">{asha.pin}</span>
        </p>
      </div>

      {visits.loading && !visits.data ? (
        <div aria-busy="true" className="space-y-3">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : visits.error ? (
        <div role="alert" className="panel-error space-y-3 text-asha">
          <p className="m-0 flex items-center gap-2 font-semibold">
            <WifiOff size={24} aria-hidden="true" /> <Bi k="noInternet" lang={lang} />
          </p>
          <Button variant="secondary" size="asha" onClick={visits.reload}>
            <Bi k="retry" lang={lang} />
          </Button>
        </div>
      ) : (visits.data ?? []).length === 0 ? (
        <div className="card space-y-4 text-asha">
          <p className="m-0">
            <Bi k="noVisits" lang={lang} />
          </p>
          <Button variant="secondary" size="asha" icon={<RefreshCw size={24} aria-hidden="true" />} onClick={visits.reload}>
            <Bi k="refresh" lang={lang} />
          </Button>
          <OwnPinLocalities asha={asha} lang={lang} onRecord={onRecord} />
        </div>
      ) : (
        <ol className="m-0 list-none space-y-4 p-0">
          {(visits.data ?? []).map((v, i) => (
            <li key={v.locality_id} className="card space-y-3 p-4">
              <div className="flex items-start gap-3">
                <span className="mono flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accentSoft text-accentText" aria-hidden="true">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="text-asha-h !text-2xl">{v.name}</h2>
                  <p className="m-0 text-asha">{v.landmark}</p>
                  {v.reason && <p className="m-0 mt-1 text-base text-muted">{v.reason}</p>}
                </div>
                <Badge className={i < 2 ? "bg-alertBg text-alert" : "bg-watchBg text-watch"}>{PRIORITY[i + 1] ?? "Low"}</Badge>
              </div>
              {v.reported && <p className="m-0 flex items-center gap-2 text-base font-semibold text-normal"><Check size={20} aria-hidden="true" /> Reported</p>}
              <Button size="asha" onClick={() => onRecord(v)}>
                <span className="text-left">
                  <Bi k="recordReport" lang={lang} onAccent />
                </span>
              </Button>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ step 2: record

type Input = { kind: "audio"; blob: Blob; name: string } | { kind: "text"; text: string };

function RecordStep({
  visit,
  lang,
  sending,
  error,
  onSend,
}: {
  visit: AshaVisit;
  lang: AshaLang;
  sending: boolean;
  error: string | null;
  onSend: (input: Input) => void;
}) {
  const [audio, setAudio] = useState<RecordedAudio | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [typing, setTyping] = useState(false);
  const [text, setText] = useState("");
  const [secs, setSecs] = useState(0);
  const fileId = useId();
  const textId = useId();
  const onRecorded = useCallback((a: RecordedAudio | null) => setAudio(a), []);

  useEffect(() => {
    if (!sending) {
      setSecs(0);
      return;
    }
    const id = window.setInterval(() => setSecs((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, [sending]);

  const input: Input | null = typing && text.trim() ? { kind: "text", text: text.trim() } : audio ? { kind: "audio", blob: audio.blob, name: audio.fileName } : file ? { kind: "audio", blob: file, name: file.name } : null;
  const cues = tr("promptCues", lang);
  const start = tr("tapStart", lang);
  const stop = tr("tapStop", lang);
  const recording = tr("recording", lang);
  const again = tr("recordAgain", lang);
  const denied = tr("micDenied", lang);
  const missing = tr("micMissing", lang);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-asha-h">
          <Bi k="speak" lang={lang} />
        </h1>
        <p className="m-0 mt-2 inline-block rounded-full bg-sunken px-3 py-1 text-base">
          {visit.name} · {visit.landmark}
        </p>
      </div>

      <div className="card space-y-1 text-asha">
        <p lang={cues.lang} className="m-0">{cues.primary}</p>
        <p className="m-0 text-sm text-muted">{cues.secondary}</p>
      </div>

      {sending ? (
        <div role="status" aria-live="polite" className="card space-y-3 text-center text-asha">
          <p className="m-0 font-semibold">
            <Bi k="listening" lang={lang} />
          </p>
          <p className="mono m-0 text-num-lg">{secs} s</p>
          <Skeleton className="h-4 w-full" />
        </div>
      ) : (
        <>
          <Recorder
            big
            haptic
            maxSeconds={90}
            lang={start.lang}
            startLabel={
              <p className="m-0 text-asha font-semibold">
                <span lang={start.lang}>{start.primary}</span>
                <span className="block text-sm font-normal text-muted">{start.secondary}</span>
              </p>
            }
            stopLabel={
              <p className="m-0 text-asha font-semibold">
                <span lang="hi">{stop.primary}</span>
                <span className="block text-sm font-normal text-muted">{stop.secondary}</span>
              </p>
            }
            recordingLabel={
              <span>
                <span lang="hi">{recording.primary}</span> <span className="text-sm text-muted">/ {recording.secondary}</span>
              </span>
            }
            againLabel={
              <span className="text-asha">
                {again.primary} <span className="text-sm text-muted">/ {again.secondary}</span>
              </span>
            }
            deniedMessage={
              <div className="space-y-1 text-asha">
                <p lang="hi" className="m-0">{denied.primary}</p>
                <p className="m-0 text-sm">{denied.secondary}</p>
              </div>
            }
            unsupportedMessage={
              <div className="space-y-1 text-asha">
                <p lang="hi" className="m-0">{missing.primary}</p>
                <p className="m-0 text-sm">{missing.secondary}</p>
              </div>
            }
            onRecorded={onRecorded}
          />

          <div className="space-y-3">
            <div>
              <input
                id={fileId}
                type="file"
                accept="audio/*"
                className="sr-only"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  setTyping(false);
                }}
              />
              <label
                htmlFor={fileId}
                className="flex min-h-14 w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-borderStrong bg-surface px-4 text-asha font-semibold hover:bg-sunken focus-within:outline"
              >
                <FileUp size={24} aria-hidden="true" />
                <span>
                  <Bi k="uploadFile" lang={lang} inline />
                </span>
              </label>
              {file && <p className="m-0 mt-1 text-sm text-muted">{file.name}</p>}
            </div>
            <Button variant="secondary" size="asha" icon={<Keyboard size={24} aria-hidden="true" />} onClick={() => setTyping((t) => !t)} aria-expanded={typing}>
              <Bi k="typeInstead" lang={lang} inline />
            </Button>
            {typing && (
              <div>
                <label htmlFor={textId} className="sr-only">
                  Type your report
                </label>
                <textarea
                  id={textId}
                  rows={4}
                  className="input min-h-[8rem] py-3 text-asha"
                  placeholder={tr("typePlaceholder", lang).primary}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
              </div>
            )}
          </div>
        </>
      )}

      {error && (
        <div role="alert" className="panel-error space-y-1 text-asha">
          <p className="m-0 flex items-center gap-2 font-semibold"><TriangleAlert size={24} aria-hidden="true" /> <Bi k="sendFailed" lang={lang} /></p>
          <p className="m-0 text-sm">{error}</p>
        </div>
      )}

      {(input || sending) && (
        <BottomBar>
          <Button size="asha" disabled={!input || sending} loading={sending} onClick={() => input && onSend(input)}>
            <Bi k="send" lang={lang} inline onAccent />
          </Button>
        </BottomBar>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ step 3: confirm

type FieldKey = "households_visited" | "fever" | "diarrhoea" | "cough" | "breathing" | "rash" | "children_affected" | "referred";
const TILES: Array<[FieldKey, AshaKey, string]> = [
  ["households_visited", "homes", "Homes visited"],
  ["fever", "fever", "Fever"],
  ["diarrhoea", "diarrhoea", "Diarrhoea"],
  ["cough", "cough", "Cough"],
  ["breathing", "breathing", "Breathing"],
  ["rash", "rash", "Rash"],
  ["children_affected", "children", "Children affected"],
  ["referred", "referred", "Referred"],
];

interface Values extends Record<FieldKey, number> {
  water_issue_reported: boolean;
}

function valuesOf(r: AshaReportResult): Values {
  return {
    households_visited: r.households_visited,
    fever: r.fever,
    diarrhoea: r.diarrhoea,
    cough: r.cough,
    breathing: r.breathing,
    rash: r.rash,
    children_affected: r.children_affected,
    referred: r.referred,
    water_issue_reported: r.water_issue_reported,
  };
}

function correctionText(v: Values): string {
  return (
    `Corrected figures: homes visited ${v.households_visited}, fever ${v.fever}, diarrhoea ${v.diarrhoea}, cough ${v.cough}, ` +
    `breathing ${v.breathing}, rash ${v.rash}, children affected ${v.children_affected}, referred ${v.referred}, ` +
    `water problem ${v.water_issue_reported ? "yes" : "no"}.`
  );
}

function ConfirmStep({
  result,
  lang,
  values,
  setValues,
  saving,
  error,
  onConfirm,
}: {
  result: AshaReportResult;
  lang: AshaLang;
  values: Values;
  setValues: (v: Values) => void;
  saving: boolean;
  error: string | null;
  onConfirm: () => void;
}) {
  const original = useMemo(() => valuesOf(result), [result]);
  const [editing, setEditing] = useState<FieldKey | null>(null);
  const [draft, setDraft] = useState(0);
  const [more, setMore] = useState(false);
  const edited = (k: FieldKey | "water_issue_reported"): boolean => values[k] !== original[k];
  const anyEdited = TILES.some(([k]) => edited(k)) || edited("water_issue_reported");
  const editingMeta = TILES.find(([k]) => k === editing);

  return (
    <div className="space-y-5">
      <h1 className="text-asha-h">
        <Bi k="isThisRight" lang={lang} />
      </h1>

      <ul className="m-0 grid list-none grid-cols-2 gap-3 p-0">
        {TILES.map(([key, strKey, en]) => (
          <li key={key}>
            <button
              type="button"
              aria-label={`${en}: ${values[key]}. Tap to correct.`}
              onClick={() => {
                setEditing(key);
                setDraft(values[key]);
              }}
              className={cx(
                "flex min-h-[7rem] w-full flex-col items-start justify-between rounded-xl border bg-surface p-3 text-left hover:bg-sunken",
                edited(key) ? "border-accent border-2" : "border-borderStrong",
              )}
            >
              <span className="mono text-num-lg">{values[key]}</span>
              <span>
                <span lang={tr(strKey, lang).lang} className="block text-base font-semibold">{tr(strKey, lang).primary}</span>
                <span className="block text-sm text-muted">{en}</span>
                {edited(key) && <span className="mt-0.5 block text-sm font-semibold text-accentText"><span lang="hi">बदला गया</span> / Edited</span>}
              </span>
            </button>
          </li>
        ))}
      </ul>

      <div className="card flex min-h-14 items-center justify-between gap-3 text-asha">
        <span>
          <Bi k="water" lang={lang} />
        </span>
        <button
          type="button"
          role="switch"
          aria-checked={values.water_issue_reported}
          aria-label="Water issue"
          onClick={() => setValues({ ...values, water_issue_reported: !values.water_issue_reported })}
          className={cx(
            "inline-flex min-h-14 min-w-[8.5rem] items-center justify-center rounded-xl px-4 font-semibold",
            values.water_issue_reported ? "bg-alert text-onAlert" : "border border-borderStrong bg-surface",
          )}
        >
          <span lang="hi">{values.water_issue_reported ? "हाँ" : "नहीं"}</span>&nbsp;/ {values.water_issue_reported ? "Yes" : "No"}
        </button>
      </div>

      {result.notes && (
        <div className="panel-warn space-y-1 text-base">
          <p className="m-0 font-semibold">
            <span lang="hi">यह जाँच लें</span> / Please check
          </p>
          <p className="m-0">{result.notes}</p>
        </div>
      )}

      <section className="card space-y-2" aria-labelledby="said-h">
        <h2 id="said-h" className="text-h3">
          <Bi k="whatYouSaid" lang={lang} inline />
        </h2>
        <p lang={result.language === "mr" ? "mr" : result.language === "en" ? "en" : "hi"} className={cx("m-0 text-asha", !more && "line-clamp-3")}>
          {result.transcript || "..."}
        </p>
        {result.transcript.length > 120 && (
          <button type="button" onClick={() => setMore((m) => !m)} className="min-h-11 text-base font-semibold text-accentText underline">
            {more ? tr("showLess", lang).primary : tr("showMore", lang).primary}
          </button>
        )}
      </section>

      {error && <p role="alert" className="panel-error m-0">{error}</p>}

      <BottomBar>
        <Button size="asha" loading={saving} onClick={onConfirm}>
          <Bi k="yesCorrect" lang={lang} inline onAccent />
        </Button>
        {anyEdited && (
          <p className="m-0 text-center text-sm text-muted">
            <span lang="hi">आपके बदलाव भी भेजे जाएँगे।</span> Your changes will be sent too.
          </p>
        )}
      </BottomBar>

      <Modal open={editing !== null} variant="sheet" onClose={() => setEditing(null)} title={editingMeta ? editingMeta[2] : ""}>
        <div className="space-y-5">
          <div className="flex items-center justify-center gap-5">
            <button type="button" aria-label="Decrease" onClick={() => setDraft((d) => Math.max(0, d - 1))} className="flex h-14 w-14 items-center justify-center rounded-xl border border-borderStrong bg-surface hover:bg-sunken">
              <Minus size={28} aria-hidden="true" />
            </button>
            <output aria-live="polite" className="mono min-w-[4ch] text-center text-num-lg">{draft}</output>
            <button type="button" aria-label="Increase" onClick={() => setDraft((d) => d + 1)} className="flex h-14 w-14 items-center justify-center rounded-xl border border-borderStrong bg-surface hover:bg-sunken">
              <Plus size={28} aria-hidden="true" />
            </button>
          </div>
          <Button
            size="asha"
            onClick={() => {
              if (editing) setValues({ ...values, [editing]: draft });
              setEditing(null);
            }}
          >
            <Bi k="saveChange" lang={lang} inline onAccent />
          </Button>
        </div>
      </Modal>
    </div>
  );
}

// ------------------------------------------------------------------ step 4: done

function relevantCases(group: string, v: Values): number {
  switch (group) {
    case "diarrhoea":
      return v.diarrhoea;
    case "fever":
      return v.fever;
    case "respiratory":
      return v.cough + v.breathing;
    case "allergy":
    case "fungal":
      return v.rash;
    default:
      return 0;
  }
}

function DoneStep({ result, values, lang, onNext, onList }: { result: AshaReportResult; values: Values; lang: AshaLang; onNext: () => void; onList: () => void }) {
  const update = result.updates?.find((u) => u.alert_id === result.alert_id) ?? result.updates?.[0];
  const before = update?.old_confidence;
  const after = update?.new_confidence ?? result.new_confidence;
  const delta = before !== undefined && after !== null && after !== undefined ? after - before : 0;
  const word: AshaKey = delta > 0.005 ? "strengthened" : delta < -0.005 ? "weakened" : "unchanged";
  const cases = update ? relevantCases(update.group, values) : 0;
  const label = update?.group_label || update?.group || "";

  return (
    <div className="space-y-5 text-center">
      <span className="mx-auto flex h-24 w-24 items-center justify-center rounded-full bg-normalBg text-normal">
        <Check size={56} strokeWidth={2.5} aria-hidden="true" />
      </span>
      <h1 className="text-asha-h">
        <span lang={lang === "mr" ? "mr" : "hi"}>{tr("reportReceived", lang).primary}</span>
        <span className="block text-sm font-normal text-muted">Report received</span>
      </h1>

      <section className="card space-y-4 text-left" aria-labelledby="alert-change-h">
        <h2 id="alert-change-h" className="text-h3">
          <Bi k="alertForArea" lang={lang} />
        </h2>
        {after !== null && after !== undefined && update ? (
          <>
            <p className="m-0 text-asha font-semibold">
              <span lang="hi">{tr(word, lang).primary}</span> <span className="text-sm text-muted">/ {tr(word, lang).secondary}</span>
            </p>
            <div className="space-y-3">
              {before !== undefined && (
                <div>
                  <p className="m-0 text-sm text-muted"><span lang="hi">{tr("before", lang).primary}</span> / {tr("before", lang).secondary}</p>
                  <ConfidenceMeter value={before} width="w-48" label="Confidence before your report" showWord={false} />
                </div>
              )}
              <div>
                <p className="m-0 text-sm text-muted"><span lang="hi">{tr("after", lang).primary}</span> / {tr("after", lang).secondary}</p>
                <ConfidenceMeter value={after} width="w-48" label="Confidence after your report" animateFrom={before} showWord={false} />
              </div>
            </div>
            <p className="m-0 text-asha">
              {delta > 0.005 && cases > 0 ? (
                <>
                  <span lang="hi">आपके {cases} मामलों से चेतावनी और पक्की हुई।</span>
                  <span className="block text-sm text-muted">Your {cases} {label.toLowerCase()} cases made the alert stronger.</span>
                </>
              ) : delta < -0.005 ? (
                <>
                  <span lang="hi">आपकी रिपोर्ट से चेतावनी कमज़ोर हुई।</span>
                  <span className="block text-sm text-muted">Your report weakened the alert.</span>
                </>
              ) : (
                <>
                  <span lang="hi">आपकी रिपोर्ट दर्ज हो गई।</span>
                  <span className="block text-sm text-muted">Your report is recorded.</span>
                </>
              )}
            </p>
          </>
        ) : (
          <p className="m-0 text-asha">
            <Bi k="noAlertChanged" lang={lang} />
          </p>
        )}
      </section>

      <BottomBar>
        <Button size="asha" onClick={onNext}>
          <Bi k="nextVisit" lang={lang} inline onAccent />
        </Button>
        <Button size="asha" variant="secondary" onClick={onList}>
          <Bi k="backToList" lang={lang} inline />
        </Button>
      </BottomBar>
    </div>
  );
}

// ------------------------------------------------------------------ flow

export function AshaFlow() {
  useDocumentTitle("ASHA");
  const { ashas, loading: refLoading } = useRefData();
  const { user } = useAuth();
  const fixedAsha = user?.roleId === "asha" ? user.ashaId : undefined;
  const [ashaId, setAshaId] = useState<string | null>(() => fixedAsha ?? (readStored(ASHA_KEY) || null));
  const [step, setStep] = useState<Step>("list");
  const [visit, setVisit] = useState<AshaVisit | null>(null);
  const [result, setResult] = useState<AshaReportResult | null>(null);
  const [values, setValues] = useState<Values | null>(null);
  const [firstResult, setFirstResult] = useState<AshaReportResult | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    applyAshaDefaultTheme();
    return releaseAshaDefaultTheme;
  }, []);

  const asha = ashas.find((a) => a.asha_id === ashaId) ?? null;
  const lang: AshaLang = asha?.language === "mr" ? "mr" : "hi";

  const choose = (id: string): void => {
    setAshaId(id);
    writeStored(ASHA_KEY, id);
    setStep("list");
  };

  const send = async (input: Input): Promise<void> => {
    if (!asha || !visit) return;
    setSending(true);
    setError(null);
    try {
      const res = await api.ashaReport({
        ashaId: asha.asha_id,
        localityId: visit.locality_id,
        file: input.kind === "audio" ? input.blob : undefined,
        fileName: input.kind === "audio" ? input.name : undefined,
        text: input.kind === "text" ? input.text : undefined,
      });
      setResult(res);
      setFirstResult(res);
      setValues(valuesOf(res));
      setStep("confirm");
    } catch (err) {
      setError(toApiError(err).message);
    } finally {
      setSending(false);
    }
  };

  const confirm = async (): Promise<void> => {
    if (!asha || !visit || !result || !values) return;
    const original = valuesOf(result);
    const changed = (Object.keys(original) as Array<keyof Values>).some((k) => original[k] !== values[k]);
    if (!changed) {
      setStep("done");
      return;
    }
    setSending(true);
    setError(null);
    try {
      const res = await api.ashaReport({ ashaId: asha.asha_id, localityId: visit.locality_id, text: correctionText(values) });
      const first = firstResult?.updates?.find((u) => u.alert_id === res.alert_id);
      // Show the move from before her first report to now, not just the correction.
      const merged: AshaReportResult = {
        ...res,
        updates: res.updates?.map((u) => (first && u.alert_id === first.alert_id ? { ...u, old_confidence: first.old_confidence } : u)),
      };
      setResult(merged);
      setStep("done");
    } catch (err) {
      setError(toApiError(err).message);
    } finally {
      setSending(false);
    }
  };

  const backToList = (): void => {
    setResult(null);
    setValues(null);
    setFirstResult(null);
    setVisit(null);
    setError(null);
    setStep("list");
  };

  return (
    <div className="mx-auto max-w-xl space-y-5 px-4 pb-44 pt-4 text-asha">
      {!asha ? (
        refLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : (
          <ChooseAsha ashas={ashas} onChoose={choose} />
        )
      ) : (
        <>
          <Progress step={step} lang={lang} />
          {step === "list" && (
            <>
              <VisitList
                asha={asha}
                lang={lang}
                onRecord={(v) => {
                  setVisit(v);
                  setError(null);
                  setStep("record");
                }}
              />
              <RecentReports asha={asha} lang={lang} />
              {!fixedAsha && (
                <button type="button" onClick={() => {
                    setAshaId(null);
                    writeStored(ASHA_KEY, "");
                  }} className="min-h-14 w-full text-base text-accentText underline">
                  <Bi k="switchPerson" lang={lang} inline />
                </button>
              )}
            </>
          )}
          {step === "record" && visit && <RecordStep visit={visit} lang={lang} sending={sending} error={error} onSend={(i) => void send(i)} />}
          {step === "confirm" && result && values && (
            <ConfirmStep result={result} lang={lang} values={values} setValues={setValues} saving={sending} error={error} onConfirm={() => void confirm()} />
          )}
          {step === "done" && result && values && (
            <DoneStep
              result={result}
              values={values}
              lang={lang}
              onNext={backToList}
              onList={backToList}
            />
          )}
        </>
      )}
    </div>
  );
}

import { BadgeCheck, Check, CircleHelp, ClipboardCheck, EyeOff, FlaskConical, KeyRound, type LucideIcon } from "lucide-react";
import { api } from "../api";
import { AiUsagePanel } from "../components/AiUsagePanel";
import { Badge } from "../components/ui/Badge";
import { PulseLine } from "../components/ui/Pulse";
import { ErrorPanel, Skeleton } from "../components/ui/States";
import { useAsync, useDocumentTitle } from "../lib/hooks";

const FLOW = [
  "WhatsApp message from a chemist",
  "Gemini reads the voice note or photo",
  "Catalogue match, doubts flagged",
  "Clerk checks and approves",
  "Counts per pin code, per medicine group",
  "Signal: baseline, breadth, co-movement",
  "Agent explains with Google Search",
  "Officer approves the actions",
  "ASHA visits the listed areas",
  "Gemini structures her voice report",
  "Alert confidence updates",
];

function FlowDiagram() {
  const boxH = 34;
  const gap = 20;
  const w = 340;
  const h = FLOW.length * boxH + (FLOW.length - 1) * gap + 8;
  return (
    <svg
      role="img"
      aria-label={`How FirstSign works, in order: ${FLOW.join(", then ")}. The last step feeds back into the signal.`}
      viewBox={`0 0 ${w + 60} ${h}`}
      className="mx-auto h-auto w-full max-w-md"
    >
      <defs>
        <marker id="arrow" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0 0 L8 4 L0 8 z" fill="var(--muted)" />
        </marker>
      </defs>
      {FLOW.map((label, i) => {
        const y = 4 + i * (boxH + gap);
        return (
          <g key={label}>
            <rect x="0" y={y} width={w} height={boxH} rx="6" fill="var(--surface)" stroke="var(--border-strong)" />
            <text x="12" y={y + boxH / 2 + 4.5} fontSize="13" fill="var(--text)" fontFamily="var(--font-body)">
              <tspan fontFamily="var(--font-mono)" fill="var(--accent-text)">{i + 1}  </tspan>
              {label}
            </text>
            {i < FLOW.length - 1 && (
              <line x1={w / 2} y1={y + boxH} x2={w / 2} y2={y + boxH + gap - 2} stroke="var(--muted)" strokeWidth="1.5" markerEnd="url(#arrow)" />
            )}
          </g>
        );
      })}
      <path
        d={`M${w} ${h - 4 - boxH / 2} H${w + 40} V${4 + (boxH + gap) * 5 + boxH / 2} H${w + 2}`}
        fill="none"
        stroke="var(--muted)"
        strokeWidth="1.5"
        strokeDasharray="4 3"
        markerEnd="url(#arrow)"
      />
      <text x={w + 46} y={h / 2 + 60} fontSize="11" fill="var(--muted)" transform={`rotate(90 ${w + 46} ${h / 2 + 60})`}>
        feeds back
      </text>
    </svg>
  );
}

const STEPS = [
  { title: "Chemists send orders as they always do.", body: "A voice note or a photo of a handwritten list, on WhatsApp." },
  { title: "FirstSign reads them. A clerk checks and approves.", body: "Every uncertain line is shown. Nothing is silently changed." },
  { title: "Rising groups trigger a visit list. ASHAs confirm on the ground.", body: "And every report teaches the system." },
];

const TRUST: Array<[LucideIcon, string]> = [
  [ClipboardCheck, "Every approval is logged"],
  [BadgeCheck, "Nothing is corrected silently"],
  [EyeOff, "No patient names stored"],
  [FlaskConical, "Simulated data"],
];

function PreviewCard() {
  return (
    <div className="card space-y-3" role="img" aria-label="Example of a parsed order with one line that needs a check and one matched line">
      <p className="label-xs">Example, read from a voice note</p>
      <div className="rounded-md border-l-4 border-confUnc bg-confUncBg p-3">
        <div className="flex items-center justify-between gap-2">
          <Badge className="bg-surface text-confUnc" icon={CircleHelp}>Check this</Badge>
          <span className="mono text-sm">10 strips</span>
        </div>
        <p lang="hi" className="mt-2 font-medium">&ldquo;पैन डी दस पत्ते&rdquo;</p>
        <p className="text-sm text-text">Heard &ldquo;pan di&rdquo;: could be Pan-D 40 or Pantop-D 40.</p>
      </div>
      <div className="rounded-md border border-border bg-surface p-3">
        <div className="flex items-center justify-between gap-2">
          <Badge className="bg-confHighBg text-confHigh" icon={Check}>Matched</Badge>
          <span className="mono text-sm">20 strips</span>
        </div>
        <p lang="hi" className="mt-2 font-medium">&ldquo;डोलो छे सौ पचास बीस&rdquo;</p>
        <p className="text-sm text-text">Dolo 650 mg tablet, strip of 15</p>
      </div>
    </div>
  );
}

function Row({ job, what, why }: { job: string; what: string; why: string }) {
  return (
    <tr className="border-t border-border align-top">
      <th scope="row" className="px-3 py-3 text-left font-medium">{job}</th>
      <td className="mono px-3 py-3 text-sm">{what}</td>
      <td className="px-3 py-3 text-sm text-muted">{why}</td>
    </tr>
  );
}

export function About() {
  useDocumentTitle("About");
  const health = useAsync((s) => api.health(s), []);
  const telemetry = useAsync((s) => api.telemetry(s), []);
  const h = health.data;
  const t = telemetry.data;

  return (
    <div className="mx-auto max-w-3xl space-y-10 px-4 py-8 md:py-12">
      <header className="space-y-3">
        <p lang="hi" className="font-display text-xl font-semibold text-accentText">पहला संकेत</p>
        <h1 className="text-h1">About FirstSign</h1>
        <p className="text-lg text-muted">A medicine distributor&rsquo;s AI order desk that also notices when a neighbourhood starts falling ill.</p>
      </header>

      <section aria-labelledby="what-h" className="space-y-3">
        <h2 id="what-h" className="text-h2">What FirstSign does</h2>
        <p>
          Chemists send their distributor orders on WhatsApp, as voice notes in Hindi or Marathi and as photos of handwritten lists. FirstSign reads them
          and prepares a bill-ready order. A clerk checks every line the AI is unsure about and approves.
        </p>
        <p>
          Because every order passes through, FirstSign also sees which medicine groups are rising in each pin code compared with normal. The distributor
          gets a stock radar. The health officer gets a ranked list of where ASHA workers should go next.
        </p>
        <p>
          Each ASHA records what she saw as a voice note in her own language. Gemini turns it into counts. Her report confirms or cancels the alert and
          becomes labelled ground truth for the next one.
        </p>
      </section>

      <PreviewCard />

      <section aria-labelledby="how-h" className="space-y-6">
        <div className="flex items-center gap-4">
          <h2 id="how-h" className="text-h2">How it works</h2>
          <PulseLine width={96} className="hidden sm:block" />
        </div>
        <ol className="m-0 grid list-none grid-cols-1 gap-6 p-0 md:grid-cols-3">
          {STEPS.map((st, i) => (
            <li key={st.title} className="flex gap-4">
              <span className="mono flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-accentFg" aria-hidden="true">
                {i + 1}
              </span>
              <div>
                <h3 className="text-h3">
                  <span className="sr-only">Step {i + 1}: </span>
                  {st.title}
                </h3>
                <p className="mt-1 text-muted">{st.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section aria-label="Our promises">
        <ul className="m-0 grid list-none grid-cols-2 gap-3 p-0 lg:grid-cols-4">
          {TRUST.map(([Icon, text]) => (
            <li key={text} className="flex items-center gap-3 rounded-lg border border-border bg-surface p-3 text-sm font-medium">
              <Icon size={20} strokeWidth={1.75} aria-hidden="true" className="shrink-0 text-accentText" />
              {text}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="flow-h" className="space-y-4">
        <h2 id="flow-h" className="text-h2">The path of one signal</h2>
        <FlowDiagram />
      </section>

      <section aria-labelledby="blame-h" className="space-y-3">
        <h2 id="blame-h" className="text-h2">Design for blame</h2>
        <ul className="list-disc space-y-1 pl-6">
          <li>The AI shows what it is unsure of. Doubtful lines are yellow, lines it could not find are red.</li>
          <li>Nothing is silently corrected. A line the clerk changes keeps the original AI reading beside it.</li>
          <li>Every approval is logged with a name and a time, and every edit is recorded.</li>
          <li>A human approves every outbound action. Drafts are marked &ldquo;Drafted by AI, not sent&rdquo; until then.</li>
        </ul>
      </section>

      <section aria-labelledby="rules-h" className="space-y-3">
        <h2 id="rules-h" className="text-h2">Data rules</h2>
        <ul className="list-disc space-y-1 pl-6">
          <li>No patient names are stored.</li>
          <li>Orders store the chemist, pin code, items and time only.</li>
          <li>ASHA reports store counts, not names.</li>
          <li>Voice notes and photos are processed in memory and not kept beyond the request. Demo samples are the exception.</li>
        </ul>
      </section>

      <section aria-labelledby="sim-h" className="panel-warn space-y-2">
        <h2 id="sim-h" className="flex items-center gap-2 text-h3">
          <FlaskConical size={20} strokeWidth={1.75} aria-hidden="true" /> What is simulated
        </h2>
        <p>
          The 90 days of order history, the chemists, the ASHA workers and the localities are simulated for this demo. The seeded events (a
          water-borne rise, a fever rise, a bad-air bump and one bulk-buying shop that must not raise an alert) are made up to show how the system reasons.
          No real patients or people appear anywhere.
        </p>
        <p lang="hi" className="m-0 text-sm">यह डेमो डेटा है, असली नहीं।</p>
      </section>

      <section aria-labelledby="auth-h" className="space-y-2">
        <h2 id="auth-h" className="flex items-center gap-2 text-h2">
          <KeyRound size={20} strokeWidth={1.75} aria-hidden="true" /> The sign-in is a demo gate
        </h2>
        <p>
          The sign-in screen is a demo gate, not real authentication. The accounts are a fixed list of fictional people, the passwords are shown on
          the login page, and the session lives only in this browser. It is there so the sandbox behaves like the real tool, with a workspace for
          each role. Do not treat it as a security control.
        </p>
      </section>

      <section aria-labelledby="google-h" className="space-y-3">
        <h2 id="google-h" className="text-h2">Google technology used</h2>
        {health.loading && !h ? (
          <Skeleton className="h-40 w-full" />
        ) : health.error ? (
          <ErrorPanel error={health.error} message="We could not read the live model settings." onRetry={health.reload} />
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border bg-surface">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-sunken text-xs uppercase tracking-wide text-muted">
                  <th scope="col" className="px-3 py-2">Job</th>
                  <th scope="col" className="px-3 py-2">Running now</th>
                  <th scope="col" className="px-3 py-2">Why</th>
                </tr>
              </thead>
              <tbody>
                <Row job="Reading voice notes and photos" what={h?.model_fast ?? "unknown"} why="Fast multimodal model. Returns structured JSON, with a fallback chain if a model is busy." />
                <Row job="Explaining a rise and drafting actions" what={h?.model_reason ?? "unknown"} why="Reasoning model with Google Search grounding. Sources come from the search metadata, not from the model's own words." />
                <Row job="Structuring ASHA voice reports" what={h?.model_fast ?? "unknown"} why="Same multimodal model turns speech in her language into counts." />
                <Row job="Hosting" what="Cloud Run, asia-south1" why="One container serves the app and the API close to users in India." />
                <Row job="Storage" what={h?.storage ?? "local"} why="Local by default so the demo runs anywhere. Firestore is optional." />
                <Row job="Signal baseline" what={h?.signal_backend ?? "local"} why="Local by default. BigQuery is an optional path for larger histories." />
              </tbody>
            </table>
          </div>
        )}
        {h?.offline && (
          <p className="panel-warn text-sm">
            This server is in <strong>demo mode</strong>: parsing results are pre-recorded, not live Gemini calls.
          </p>
        )}
        {t && (
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Gemini usage since the server started">
            {[
              ["Gemini calls", t.calls],
              ["Model fallbacks", t.fallbacks],
              ["Search sources found", t.grounded_sources_total],
              ["Cache hits", t.cache_hits],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-lg border border-border bg-surface p-3">
                <dt className="text-sm text-muted">{label}</dt>
                <dd className="mono text-2xl font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>

      <AiUsagePanel />

      <footer className="border-t border-border pt-6 text-sm text-muted">
        <p className="m-0">Built for the Google DeepMind x Google Cloud Startup Buildathon India 2026</p>
      </footer>
    </div>
  );
}

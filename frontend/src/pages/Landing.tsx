import { ArrowRight, BadgeCheck, Check, CircleHelp, ClipboardCheck, EyeOff, FlaskConical, MapPinned, Mic, PackageCheck, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { MetricsStrip } from "../components/MetricsStrip";
import { Badge } from "../components/ui/Badge";
import { PulseLine } from "../components/ui/Pulse";
import { useDocumentTitle } from "../lib/hooks";

interface Door {
  to: string;
  icon: LucideIcon;
  en: string;
  hi: string;
  body: string;
  cta: string;
}

const DOORS: Door[] = [
  {
    to: "/distributor/inbox",
    icon: PackageCheck,
    en: "Distributor",
    hi: "वितरक",
    body: "Turn voice notes and photo lists into bills. See what to stock.",
    cta: "Open inbox",
  },
  {
    to: "/officer",
    icon: MapPinned,
    en: "Health officer",
    hi: "स्वास्थ्य अधिकारी",
    body: "See where illness is rising and send ASHAs first.",
    cta: "Open map",
  },
  {
    to: "/asha",
    icon: Mic,
    en: "ASHA",
    hi: "आशा",
    body: "Record what you saw in your own language.",
    cta: "Start visit",
  },
];

const STEPS = [
  { title: "Chemists send orders as they always do.", body: "A voice note or a photo of a handwritten list, on WhatsApp." },
  { title: "FirstSign reads them. A clerk checks and approves.", body: "Every uncertain line is shown. Nothing is silently changed." },
  { title: "Rising groups trigger a visit list. ASHAs confirm on the ground.", body: "And every report teaches the system." },
];

const TRUST: Array<[LucideIcon, string]> = [
  [ClipboardCheck, "Every approval is logged"],
  [BadgeCheck, "Nothing is corrected silently"],
  [EyeOff, "No patient names stored"],
  [FlaskConical, "Simulated demo data"],
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

export function Landing() {
  useDocumentTitle("Know which medicine is moving");
  return (
    <div className="mx-auto max-w-[1440px] space-y-12 px-4 py-8 md:px-6 md:py-12 xl:px-8">
      <section className="grid items-center gap-8 lg:grid-cols-12">
        <div className="space-y-5 lg:col-span-7">
          <p lang="hi" className="font-display text-xl font-semibold text-accentText">पहला संकेत</p>
          <h1 className="text-[2.25rem] font-bold leading-[1.1] md:text-display">Know which medicine is moving before the clinic fills up.</h1>
          <p className="max-w-xl text-lg text-muted">
            FirstSign turns the WhatsApp orders chemists already send into ready-to-bill orders, and spots early signs of illness in the same stream.
          </p>
          <PulseLine width={192} />
        </div>
        <div className="lg:col-span-5">
          <PreviewCard />
        </div>
      </section>

      <MetricsStrip />

      <section aria-labelledby="doors-h">
        <h2 id="doors-h" className="sr-only">Choose your role</h2>
        <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 md:grid-cols-3">
          {DOORS.map((d) => {
            const Icon = d.icon;
            return (
              <li key={d.to} className="flex">
                <Link
                  to={d.to}
                  aria-label={`${d.en}, open`}
                  className="card-link flex min-h-24 w-full flex-col gap-3 rounded-xl p-6"
                >
                  <span className="flex h-12 w-12 items-center justify-center rounded-full bg-accentSoft text-accentText">
                    <Icon size={24} strokeWidth={1.75} aria-hidden="true" />
                  </span>
                  <span className="text-h3">
                    {d.en} <span lang="hi" className="text-muted">/ {d.hi}</span>
                  </span>
                  <span className="text-muted">{d.body}</span>
                  <span className="mt-auto inline-flex min-h-11 items-center gap-2 pt-2 font-semibold text-accentText">
                    {d.cta} <ArrowRight size={18} aria-hidden="true" />
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-labelledby="how-h" className="space-y-6">
        <div className="flex items-center gap-4">
          <h2 id="how-h" className="text-h2">How it works</h2>
          <PulseLine width={96} className="hidden sm:block" />
        </div>
        <ol className="m-0 grid list-none grid-cols-1 gap-6 p-0 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <li key={s.title} className="flex gap-4">
              <span className="mono flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-accentFg" aria-hidden="true">
                {i + 1}
              </span>
              <div>
                <h3 className="text-h3">
                  <span className="sr-only">Step {i + 1}: </span>
                  {s.title}
                </h3>
                <p className="mt-1 text-muted">{s.body}</p>
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

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-6 text-sm text-muted">
        <p className="m-0">Built for the Google DeepMind x Google Cloud Startup Buildathon India 2026</p>
        <Link to="/about" className="font-semibold text-accentText underline">How it works, in detail</Link>
      </footer>
    </div>
  );
}

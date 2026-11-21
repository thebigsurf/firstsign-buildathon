"""The explain-and-draft agent.

Two reliable steps:
  (a) a Gemini call with the Google Search grounding tool: recent local news, water, weather and
      disease reports for the area and dates; sources are read from the grounding metadata.
  (b) a reasoning call that receives OUR data (series, breadth, co-moving groups, decoy check,
      localities, ASHA reports) plus the search findings and returns structured JSON.
The result is cached per alert. If grounding fails we still return the reasoning with an honest
"no external sources found" note. A human approves every outbound action (see api.py).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .errors import UpstreamError
from .gemini import GeminiClient
from .models import (
    AgentActions,
    Alert,
    Explanation,
    LikelyCause,
    ModelExplain,
    Source,
    VisitItem,
)
from .signal import SignalService
from .store import Reference, Store

log = logging.getLogger("firstsign.agent")

SEARCH_SYSTEM = (
    "You are a public-health research assistant. Use Google Search. Report only what sources actually say, "
    "with dates. If you find nothing relevant for the area and dates, say so plainly. Never invent events."
)

REASON_SYSTEM = """You are the analyst inside FirstSign, a tool that watches medicine orders in Mumbai to give an \
early warning of local illness. You help a distributor and a health officer decide what to do. You are cautious: \
an order signal is a clue, not a diagnosis, and a human approves every action.

Rules:
1. Base every claim on the data provided. For outside causes (water contamination, rain, heat, local outbreaks) use \
ONLY the search findings; if they contain nothing relevant, say that no external source supports a cause and give \
only hypotheses with low confidence.
2. likely_causes: 2 to 4, most likely first. evidence must cite specific numbers from our data or a finding. \
confidence is 0 to 1.
3. asha_visit_list: choose 3 to 6 localities, using locality_id values copied exactly from the list provided. \
Rank by where ASHA workers should go first (priority 1 = first), considering which pin is rising most, number of \
households, and any ASHA reports already received. Give a short plain reason for each.
4. distributor_note: 2 to 4 sentences to the distributor's team about what to stock and why. officer_note: 3 to \
5 sentences to the ward health officer: what is rising, where, how sure we are, what to check, and a clear line \
that it is an early signal to verify, not a confirmed outbreak.
5. Plain English. No patient names. Do not claim certainty."""


class ExplainAgent:
    def __init__(self, gemini: GeminiClient, signal: SignalService, store: Store, ref: Reference) -> None:
        self.gemini, self.signal, self.store, self.ref = gemini, signal, store, ref

    # ----------------------------------------------------------------- public

    def explain(self, alert_id: str, refresh: bool = False) -> Explanation:
        if not refresh:
            cached = self.store.get_explanation(alert_id)
            if cached:
                return Explanation.model_validate({**cached, "cached": True})
        alert = self.signal.alert(alert_id)
        context = self.signal.explain_context(alert)
        explanation = self._build(alert, context)
        self.store.save_explanation(alert_id, explanation.model_dump())
        return explanation

    # ---------------------------------------------------------------- building

    def _build(self, alert: Alert, context: dict[str, Any]) -> Explanation:
        if self.gemini.offline:
            return self._fallback(alert, context, "offline-rules", 0, [], "Offline demo mode: no web search was run.")

        findings, sources, search_ms, search_note, queries = self._search(alert, context)
        prompt = self._reason_prompt(alert, context, findings, bool(sources))
        try:
            result = self.gemini.generate_structured(
                self.gemini.settings.model_reason, prompt, ModelExplain, system=REASON_SYSTEM, temperature=0.2
            )
            raw = ModelExplain.model_validate(result.json())
        except (UpstreamError, ValueError) as exc:
            log.warning("reasoning call failed (%s); using data-only explanation", type(exc).__name__)
            last = self._last_good(alert.alert_id)
            if last is not None:
                return last.model_copy(update={
                    "search_note": last.search_note + " Earlier Gemini explanation for this alert, shown because "
                                   "Gemini was unavailable just now; the counts above are live."})
            return self._fallback(alert, context, "data-only-fallback", search_ms, sources,
                                  search_note + " The reasoning model was unavailable, so this uses our data only.",
                                  queries)
        visits = self._clean_visits(raw, alert, context)
        built = Explanation(
            alert_id=alert.alert_id,
            summary=raw.summary.strip(),
            likely_causes=[LikelyCause(cause=c.cause, evidence=c.evidence, confidence=min(max(c.confidence, 0), 1))
                           for c in raw.likely_causes[:4]],
            sources=sources,
            actions=AgentActions(distributor_note=raw.distributor_note.strip(), officer_note=raw.officer_note.strip(),
                                 asha_visit_list=visits),
            model=result.model, latency_ms=search_ms + result.latency_ms,
            grounded=bool(sources), cached=False, search_note=search_note, search_queries=queries,
        )
        self._save_last_good(built)
        return built

    def _last_good_path(self, alert_id: str):
        cache_dir = getattr(self.gemini.settings, "cache_dir", None)
        return cache_dir / f"explain_last_{alert_id}.json" if cache_dir else None

    def _save_last_good(self, explanation: Explanation) -> None:
        path = self._last_good_path(explanation.alert_id)
        if path is None:
            return
        try:
            path.write_text(explanation.model_dump_json(), encoding="utf-8")
        except OSError:
            log.warning("could not save last-good explanation")

    def _last_good(self, alert_id: str) -> Explanation | None:
        path = self._last_good_path(alert_id)
        if path is None:
            return None
        try:
            return Explanation.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _search(self, alert: Alert, context: dict[str, Any]) -> tuple[str, list[Source], int, str, list[str]]:
        areas = ", ".join(f"{self.ref.area(p)} (pin {p})" for p in alert.pins)
        prompt = (
            f"Between {alert.started} and {context['as_of']}, what recent local news, water supply or contamination "
            f"reports, rainfall or flooding, heat, air quality, or disease and outbreak reports (dengue, diarrhoea, "
            f"cholera, typhoid, viral fever, respiratory illness) are there for {areas}, Mumbai, Maharashtra, India? "
            f"We are checking why orders for {alert.group_label.lower()} medicines rose there. "
            "Give short dated findings, each with the source name. If there is nothing relevant, say so."
        )
        try:
            result = self.gemini.generate_grounded(self.gemini.settings.model_reason, prompt, system=SEARCH_SYSTEM)
        except UpstreamError as exc:
            log.warning("grounded search failed: %s", exc.message[:120])
            return "No search findings are available.", [], 0, "No external sources found: the web search step failed.", []
        sources = [Source(title=s["title"], url=s["url"]) for s in result.sources][:8]
        if not sources:
            return result.text, [], result.latency_ms, "No external sources found for this area and period.", result.search_queries
        return result.text, sources, result.latency_ms, f"Grounded with Google Search ({len(sources)} sources).", result.search_queries

    def _reason_prompt(self, alert: Alert, context: dict[str, Any], findings: str, grounded: bool) -> str:
        data = {
            "alert": {"id": alert.alert_id, "group": alert.group_label, "level": alert.level,
                      "ratio_vs_normal": alert.ratio, "breadth": alert.breadth, "confidence": alert.confidence,
                      "started": alert.started, "reasons": alert.reasons},
            "our_data": context,
        }
        search_part = findings if grounded else "NO EXTERNAL SOURCES WERE FOUND. " + findings
        return (
            "OUR DATA (JSON):\n" + json.dumps(data, ensure_ascii=False, default=str)
            + "\n\nSEARCH FINDINGS (from Google Search grounding):\n" + search_part
            + "\n\nWrite the explanation and the three drafted actions."
        )

    # ------------------------------------------------------------- post-checks

    def _rank_localities(self, alert: Alert, context: dict[str, Any]) -> list[VisitItem]:
        """Deterministic ranking: rising pin first, then households. Used to fill gaps and as the fallback."""
        ratio_of = {p["pin"]: p["ratio_vs_normal"] for p in context["pins"]}
        scored = sorted(context["localities"], key=lambda x: -(ratio_of.get(x["pin"], 1.0) * x["households"]))
        return [
            VisitItem(locality_id=x["locality_id"], name=x["name"], landmark=x["landmark"], priority=i + 1,
                      reason=f"{x['households']} households in {self.ref.area(x['pin'])}, where orders are "
                             f"{ratio_of.get(x['pin'], 1.0):.1f}x normal.")
            for i, x in enumerate(scored[:6])
        ]

    def _clean_visits(self, raw: ModelExplain, alert: Alert, context: dict[str, Any]) -> list[VisitItem]:
        """Keep only real localities of the alert's pins, rank by priority, ensure at least three."""
        valid = {x["locality_id"]: x for x in context["localities"]}
        chosen: list[VisitItem] = []
        seen: set[str] = set()
        for item in sorted(raw.asha_visit_list, key=lambda v: v.priority):
            loc = valid.get(item.locality_id)
            if not loc or item.locality_id in seen:
                continue
            seen.add(item.locality_id)
            chosen.append(VisitItem(locality_id=item.locality_id, name=loc["name"], landmark=loc["landmark"],
                                    priority=len(chosen) + 1, reason=item.reason.strip()))
        for filler in self._rank_localities(alert, context):
            if len(chosen) >= 3:
                break
            if filler.locality_id not in seen:
                seen.add(filler.locality_id)
                chosen.append(filler.model_copy(update={"priority": len(chosen) + 1}))
        return chosen[:6]

    def _fallback(self, alert: Alert, context: dict[str, Any], model: str, latency: int,
                  sources: list[Source], note: str,
                  queries: list[str] | None = None) -> Explanation:
        top = max(context["pins"], key=lambda p: p["ratio_vs_normal"])
        areas = ", ".join(self.ref.area(p) for p in alert.pins)
        summary = (
            f"{alert.group_label} medicine orders are {alert.ratio:.1f}x normal in {areas}, since {alert.started}. "
            f"The rise is broad across chemists (breadth {alert.breadth:.2f}) and is strongest in {top['area']}."
        )
        causes = [LikelyCause(
            cause=f"A local rise in {alert.group_label.lower()} illness",
            evidence=f"{alert.reasons[1] if len(alert.reasons) > 1 else ''} Confidence from orders alone is {alert.confidence:.0%}.",
            confidence=alert.confidence,
        )]
        distributor = (f"Stock up on {alert.group_label.lower()} medicines for {areas}: orders are {alert.ratio:.1f}x "
                       "normal and many chemists are asking. See the stock radar for item quantities.")
        officer = (f"Early signal: {alert.group_label.lower()} medicine sales are {alert.ratio:.1f}x normal in {areas}. "
                   "Please send ASHA workers to the listed localities to check. This is an order-data signal to "
                   "verify, not a confirmed outbreak.")
        return Explanation(
            alert_id=alert.alert_id, summary=summary, likely_causes=causes, sources=sources,
            actions=AgentActions(distributor_note=distributor, officer_note=officer,
                                 asha_visit_list=self._rank_localities(alert, context)),
            model=model, latency_ms=latency, grounded=bool(sources), search_note=note,
            search_queries=queries or [],
        )

"""An offline stand-in used when no API key is set, so the app still runs.

It calls no model and costs nothing. Its replies come from a few simple rules,
and its briefing says so. Set ANTHROPIC_API_KEY to use a real model.
"""

import json
import re

from app.llm.base import LLMError, LLMRequest, LLMResponse

DEMO_MODEL = "demo"

_SUBSYSTEMS = {
    "propulsion": ("valve", "engine", "pressure", "thrust", "turbopump", "propellant"),
    "telemetry": ("telemetry", "link", "signal", "data", "antenna"),
    "avionics": ("computer", "software", "sensor", "guidance", "avionics"),
    "thermal": ("temperature", "heat", "cooling", "thermal"),
    "weather": ("wind", "lightning", "rain", "weather"),
    "structures": ("crack", "leak", "structure", "vibration"),
    "ground_systems": ("pad", "ground", "umbilical", "power"),
}
_INSTRUCTION_WORDS = (
    "ignore", "disregard", "system:", "instruction", "mark this", "mark it",
    "override", "approve the", "you must", "assistant", "set severity",
    "forget the above", "approve this", "new instructions",
)
# Phrases that only count as instructions in a certain shape, so honest notes such as
# "Forget all earlier readings, the sensor was reset" are not flagged.
_INSTRUCTION_PATTERNS = (
    re.compile(r"\bforget (all|everything)\b.{0,20}\b(previous|prior|above|earlier instructions|instructions|rules|limits)\b"),
    re.compile(r"\bforget (all|everything) above\b"),
    re.compile(r"\byou are now (the|a|an)\b"),
)


def _looks_like_instructions(lowered: str) -> bool:
    return any(w in lowered for w in _INSTRUCTION_WORDS) or any(
        p.search(lowered) for p in _INSTRUCTION_PATTERNS
    )


class DemoLLMClient:
    async def complete(self, request: LLMRequest) -> LLMResponse:
        reply = self._reply(request)
        text = reply if isinstance(reply, str) else json.dumps(reply)
        return LLMResponse(text=text, model=DEMO_MODEL, input_tokens=0, output_tokens=0)

    def _reply(self, request: LLMRequest) -> str | dict:
        step, note = request.step, _note(request.user)
        lowered = note.lower()
        if step == "sort":
            subsystem = next(
                (name for name, words in _SUBSYSTEMS.items() if any(w in lowered for w in words)),
                "unknown",
            )
            return {"subsystem": subsystem, "severity": "medium"}
        if step == "check_injection":
            hit = _looks_like_instructions(lowered)
            return {"flagged": hit, "reason": "Demo rule: the note contains instruction-like words."
                    if hit else "Demo rule: no instruction-like words found."}
        if step == "check_missing":
            short = len(note.split()) < 6
            return {"flagged": short, "reason": "Demo rule: the note is very short."
                    if short else "Demo rule: the note has enough words."}
        if step == "check_panic":
            # Three shouted words, not two: SQL-like text such as "DROP TABLE" must stay calm.
            shouting = note.count("!") >= 2 or len(re.findall(r"\b[A-Z]{4,}\b", note)) >= 3
            return {"flagged": shouting, "reason": "Demo rule: the note shouts."
                    if shouting else "Demo rule: the tone is calm."}
        if step == "draft":
            return self._briefing(request.user)
        if step == "review":
            return {"approved": True, "feedback": ""}
        raise LLMError(f"The demo client has no reply for step {step!r}")

    @staticmethod
    def _briefing(facts: str) -> str:
        def grab(pattern: str, default: str) -> str:
            found = re.search(pattern, facts)
            return found.group(1) if found else default

        verdict = grab(r"Verdict: (\S+)", "unknown")
        subsystem = grab(r"Subsystem: (\S+)", "unknown")
        minutes = grab(r"within (\d+) minutes", "?")
        violations = re.findall(r"^- (?!none).+$", facts, flags=re.M)
        problems = " ".join(v[2:] for v in violations) or "No limit violations."
        return (
            f"[Demo briefing, written by rules, not by a model.] Verdict: {verdict}. "
            f"Subsystem: {subsystem}. {problems} Brief the Flight Director within {minutes} minutes. "
            "Set ANTHROPIC_API_KEY for a model-written briefing."
        )


def _note(user: str) -> str:
    found = re.search(r"<report_note>\n(.*?)\n</report_note>", user, flags=re.S)
    return found.group(1) if found else user

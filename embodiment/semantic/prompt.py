from __future__ import annotations

import json

from semantic.context import SemanticContext
from semantic.registry import CapabilityRegistry


def build_planner_prompt(
    context: SemanticContext,
    registry: CapabilityRegistry,
) -> str:

    capability_json = json.dumps(
        registry.describe(),
        ensure_ascii=False,
        indent=2,
    )

    context_json = json.dumps(
        context.to_dict(),
        ensure_ascii=False,
        indent=2,
    )

    return f"""
You are the semantic planner for a persistent embodied desktop agent.

Interpret the user's natural language from meaning and context.
Do not depend on exact trigger phrases.

You may produce zero, one, or multiple capability steps.

Resolve pronouns and elliptical language using:
- current task
- current screen
- active application
- current visible people
- recent dialogue
- recent actions
- memory

Prefer acting from context when meaning is reasonably clear.
Ask a clarification only when a necessary ambiguity cannot be
resolved safely.

Never invent an executed result.
Execution happens after planning.

Available capabilities:

{capability_json}

Current context:

{context_json}

Return JSON ONLY with this shape:

{{
  "interpretation": "what the user means",
  "confidence": 0.0,
  "clarification_needed": false,
  "clarification_question": null,
  "steps": [
    {{
      "capability": "capability.name",
      "arguments": {{}},
      "reason": "why this capability is appropriate",
      "confidence": 0.0,
      "depends_on": []
    }}
  ],
  "reply": null
}}

Dependency contract:
- "depends_on" must always be a JSON array of integer step indices.
- Step indices are zero-based.
- A step may depend only on an earlier step.
- Never place capability names such as "screen.observe" in "depends_on".
- If a step has no dependency, use [].

Planning contract:
- A semantic plan has exactly one answer mode:
  1. Direct-answer mode:
     - "steps": []
     - put the user-facing answer in "reply".
  2. Capability-execution mode:
     - one or more capability steps
     - "reply": null
     - the final user-facing answer is produced only after grounded
       capability execution.
- Never return both a non-empty capability plan and a user-facing
  "reply" in the same semantic plan.
- For arithmetic, general knowledge, ordinary conversation, or reasoning
  that does not require live device state, sensors, memory, filesystem
  access, or external actions, return "steps": [] and put the answer
  directly in "reply".
- Do not call screen, memory, sensor, or execution capabilities merely
  to reason about information already present in the user's request.
- "reply" is a top-level semantic-plan field, never a capability.
- Never emit a step whose capability is "reply".
- For a direct answer, use "steps": [] and place the answer in "reply".
- Every non-empty step capability must exactly match one capability name
  from the supplied live capability catalog.

The capability names must come from the provided capability catalog.
""".strip()

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class InformationPermission(str, Enum):
    READ = "read"
    TRUST = "trust"
    PERSIST = "persist"
    EXECUTE = "execute"
    PROPAGATE = "propagate"


@dataclass(frozen=True)
class SecurityAssessment:
    ok: bool
    decision: str
    risk: float
    classifier_version: str
    policy_version: str
    concepts: dict
    reason_codes: tuple[str, ...]
    error: str = ""

    @property
    def allowed(self) -> bool:
        return (
            self.ok
            and self.decision == "ALLOW"
        )


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    permission: InformationPermission
    assessment: SecurityAssessment
    reason: str = ""


class SecurityBoundary:
    """
    Fail-closed bridge from Python embodiment code to Neuron's
    authoritative native PromptSecurityApi.

    Reading information is intentionally separate from trusting,
    persisting, executing, or propagating it.
    """

    def __init__(
        self,
        *,
        cli_path,
        timeout_seconds=3.0,
    ):
        self.cli_path = Path(cli_path)
        self.timeout_seconds = float(
            timeout_seconds
        )

    def assess(
        self,
        source_text,
    ) -> SecurityAssessment:
        source_text = str(
            source_text or ""
        )

        if not source_text.strip():
            return SecurityAssessment(
                ok=False,
                decision="BLOCK",
                risk=1.0,
                classifier_version="",
                policy_version="",
                concepts={},
                reason_codes=(),
                error="empty_source_text",
            )

        if not self.cli_path.is_file():
            return SecurityAssessment(
                ok=False,
                decision="BLOCK",
                risk=1.0,
                classifier_version="",
                policy_version="",
                concepts={},
                reason_codes=(),
                error="security_cli_missing",
            )

        try:
            completed = subprocess.run(
                [str(self.cli_path)],
                input=source_text,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except Exception as exc:
            return SecurityAssessment(
                ok=False,
                decision="BLOCK",
                risk=1.0,
                classifier_version="",
                policy_version="",
                concepts={},
                reason_codes=(),
                error=(
                    "security_cli_failed:"
                    + type(exc).__name__
                ),
            )

        if completed.returncode != 0:
            return SecurityAssessment(
                ok=False,
                decision="BLOCK",
                risk=1.0,
                classifier_version="",
                policy_version="",
                concepts={},
                reason_codes=(),
                error="security_cli_nonzero",
            )

        try:
            payload = json.loads(
                completed.stdout
            )
        except Exception:
            return SecurityAssessment(
                ok=False,
                decision="BLOCK",
                risk=1.0,
                classifier_version="",
                policy_version="",
                concepts={},
                reason_codes=(),
                error="invalid_security_json",
            )

        decision = str(
            payload.get(
                "decision",
                "BLOCK",
            )
        )

        if decision not in {
            "ALLOW",
            "REQUIRE_REVIEW",
            "ISOLATE",
            "BLOCK",
        }:
            decision = "BLOCK"

        return SecurityAssessment(
            ok=True,
            decision=decision,
            risk=float(
                payload.get(
                    "risk",
                    1.0,
                )
            ),
            classifier_version=str(
                payload.get(
                    "classifier_version",
                    "",
                )
            ),
            policy_version=str(
                payload.get(
                    "policy_version",
                    "",
                )
            ),
            concepts=dict(
                payload.get(
                    "concepts",
                    {},
                )
            ),
            reason_codes=tuple(
                str(x)
                for x in payload.get(
                    "reason_codes",
                    []
                )
            ),
        )

    def authorize(
        self,
        *,
        source_text,
        permission,
    ) -> PermissionDecision:
        permission = InformationPermission(
            permission
        )

        assessment = self.assess(
            source_text
        )

        #
        # Observation is not authority.
        #
        if permission is InformationPermission.READ:
            return PermissionDecision(
                allowed=True,
                permission=permission,
                assessment=assessment,
                reason="read_does_not_imply_trust",
            )

        if not assessment.ok:
            return PermissionDecision(
                allowed=False,
                permission=permission,
                assessment=assessment,
                reason="security_unavailable_fail_closed",
            )

        if assessment.decision != "ALLOW":
            return PermissionDecision(
                allowed=False,
                permission=permission,
                assessment=assessment,
                reason=(
                    "classifier_denied_"
                    + assessment.decision.lower()
                ),
            )

        concepts = assessment.concepts

        external = float(
            concepts.get(
                "external_instruction_provenance",
                0.0,
            )
        )

        authority = float(
            concepts.get(
                "authority_replacement",
                0.0,
            )
        )

        supersession = float(
            concepts.get(
                "instruction_supersession",
                0.0,
            )
        )

        bypass = float(
            concepts.get(
                "authorization_bypass",
                0.0,
            )
        )

        malicious = float(
            concepts.get(
                "malicious_intent",
                0.0,
            )
        )

        #
        # Higher permissions are stricter than mere classification.
        #
        if permission in {
            InformationPermission.TRUST,
            InformationPermission.PERSIST,
            InformationPermission.EXECUTE,
            InformationPermission.PROPAGATE,
        }:
            if (
                external >= 0.70
                or authority >= 0.70
                or supersession >= 0.70
                or bypass >= 0.70
                or malicious >= 0.70
            ):
                return PermissionDecision(
                    allowed=False,
                    permission=permission,
                    assessment=assessment,
                    reason="untrusted_instruction_provenance",
                )

        return PermissionDecision(
            allowed=True,
            permission=permission,
            assessment=assessment,
            reason="authorized",
        )


def default_security_boundary():
    """
    Locate the native bridge relative to the Neuron source tree.

    Returning a boundary whose CLI does not exist is intentional:
    SecurityBoundary then fails closed for trust/persist/execute/
    propagate permissions.
    """
    root = Path(__file__).resolve().parents[1]

    return SecurityBoundary(
        cli_path=(
            root
            / "build"
            / "neuron_security_cli"
        )
    )


def provenance_allows(
    provenance,
    permission: InformationPermission,
) -> bool:
    """
    Independent authority check.

    Text classification can further restrict authority,
    but cannot override inherited provenance restrictions.
    """
    permissions = provenance.permissions

    mapping = {
        InformationPermission.READ:
            permissions.read,
        InformationPermission.TRUST:
            permissions.trust,
        InformationPermission.PERSIST:
            permissions.persist,
        InformationPermission.EXECUTE:
            permissions.execute,
        InformationPermission.PROPAGATE:
            permissions.propagate,
    }

    return bool(mapping[permission])


def authorize_with_provenance(
    *,
    boundary,
    source_text: str,
    provenance,
    permission: InformationPermission,
):
    """
    Both independent gates must allow the operation:

      inherited authority
             AND
      current textual classification

    Provenance can never be upgraded by cleaner wording.
    """
    textual = boundary.authorize(
        source_text=source_text,
        permission=permission,
    )

    if not provenance_allows(
        provenance,
        permission,
    ):
        return PermissionDecision(
            allowed=False,
            permission=permission,
            assessment=textual.assessment,
            reason="provenance_denied",
        )

    return textual

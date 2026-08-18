#include "neuron/prompt_security_api.hpp"

#include <algorithm>

namespace neuron {
namespace {

int decision_rank(SecurityDecision decision) {
    switch (decision) {
        case SecurityDecision::Allow:
            return 0;
        case SecurityDecision::RequireReview:
            return 1;
        case SecurityDecision::Isolate:
            return 2;
        case SecurityDecision::Block:
            return 3;
    }

    return 3;
}

SecurityDecision more_restrictive(
    SecurityDecision a,
    SecurityDecision b
) {
    return decision_rank(a) >= decision_rank(b)
        ? a
        : b;
}

double sensitivity_floor(ResourceSensitivity sensitivity) {
    switch (sensitivity) {
        case ResourceSensitivity::Public:
            return 0.0;
        case ResourceSensitivity::Internal:
            return 0.10;
        case ResourceSensitivity::Confidential:
            return 0.20;
        case ResourceSensitivity::Restricted:
            return 0.30;
    }

    return 0.30;
}

bool is_high_impact_action(SecurityActionType action) {
    switch (action) {
        case SecurityActionType::Payment:
        case SecurityActionType::SecretAccess:
        case SecurityActionType::DatabaseMutation:
        case SecurityActionType::InventoryMutation:
        case SecurityActionType::Procurement:
        case SecurityActionType::ShellProcess:
            return true;
        default:
            return false;
    }
}

} // namespace

PromptSecurityResult PromptSecurityApi::classify_prompt(
    const std::string& input
) {
    const auto raw = classifier_.classify(input);

    PromptSecurityResult out;
    out.decision = raw.final_decision;
    out.risk = raw.final_risk;
    out.reason_codes = raw.reasons;

    out.concepts.authority_replacement =
        raw.semantic.concepts.authority_replacement;
    out.concepts.instruction_supersession =
        raw.semantic.concepts.instruction_supersession;
    out.concepts.secret_disclosure_request =
        raw.semantic.concepts.secret_disclosure_request;
    out.concepts.authorization_bypass =
        raw.semantic.concepts.authorization_bypass;
    out.concepts.privilege_acquisition =
        raw.semantic.concepts.privilege_acquisition;
    out.concepts.external_instruction_provenance =
        raw.semantic.concepts.external_instruction_provenance;
    out.concepts.quoted_or_educational_context =
        raw.semantic.concepts.quoted_or_educational_context;
    out.concepts.encoded_or_obfuscated_content =
        raw.semantic.concepts.encoded_or_obfuscated_content;
    out.concepts.malicious_intent =
        raw.semantic.concepts.malicious_intent;

    if (raw.contextual_downgrade) {
        out.reason_codes.push_back(
            "api:contextual_downgrade"
        );
    }

    if (raw.hard_legacy_floor) {
        out.reason_codes.push_back(
            "api:hard_legacy_floor"
        );
    }

    return out;
}

ActionSecurityResult PromptSecurityApi::authorize_action(
    const std::string& source_text,
    const ActionSecurityContext& context
) {
    ActionSecurityResult out;
    out.prompt = classify_prompt(source_text);
    out.decision = out.prompt.decision;
    out.risk = std::max(
        out.prompt.risk,
        sensitivity_floor(context.sensitivity)
    );
    out.reason_codes = out.prompt.reason_codes;

    if (
        context.sensitivity == ResourceSensitivity::Restricted &&
        out.decision == SecurityDecision::Allow
    ) {
        out.decision = SecurityDecision::RequireReview;
        out.reason_codes.push_back(
            "policy:restricted_resource_review"
        );
    }

    if (
        is_high_impact_action(context.action) &&
        out.prompt.decision == SecurityDecision::RequireReview
    ) {
        out.decision = SecurityDecision::Isolate;
        out.reason_codes.push_back(
            "policy:high_impact_review_isolated"
        );
    }

    if (
        context.action == SecurityActionType::Payment &&
        !context.human_confirmation_available &&
        out.decision == SecurityDecision::Allow
    ) {
        out.decision = SecurityDecision::RequireReview;
        out.reason_codes.push_back(
            "policy:payment_confirmation_required"
        );
    }

    if (
        out.prompt.concepts.secret_disclosure_request >= 0.70 &&
        context.action == SecurityActionType::SecretAccess
    ) {
        out.decision = more_restrictive(
            out.decision,
            SecurityDecision::Block
        );
        out.reason_codes.push_back(
            "policy:secret_access_exfiltration_block"
        );
    }

    if (
        out.prompt.concepts.authorization_bypass >= 0.70 &&
        is_high_impact_action(context.action)
    ) {
        out.decision = more_restrictive(
            out.decision,
            SecurityDecision::Block
        );
        out.reason_codes.push_back(
            "policy:authorization_bypass_high_impact_block"
        );
    }

    return out;
}

std::string security_action_name(SecurityActionType action) {
    switch (action) {
        case SecurityActionType::Informational:
            return "informational";
        case SecurityActionType::ShellProcess:
            return "shell_process";
        case SecurityActionType::ExternalApi:
            return "external_api";
        case SecurityActionType::Payment:
            return "payment";
        case SecurityActionType::Procurement:
            return "procurement";
        case SecurityActionType::InventoryMutation:
            return "inventory_mutation";
        case SecurityActionType::DatabaseMutation:
            return "database_mutation";
        case SecurityActionType::SecretAccess:
            return "secret_access";
        case SecurityActionType::BrowserAction:
            return "browser_action";
        case SecurityActionType::FilesystemWrite:
            return "filesystem_write";
        case SecurityActionType::AgentDelegation:
            return "agent_delegation";
    }

    return "unknown";
}

std::string resource_sensitivity_name(
    ResourceSensitivity sensitivity
) {
    switch (sensitivity) {
        case ResourceSensitivity::Public:
            return "public";
        case ResourceSensitivity::Internal:
            return "internal";
        case ResourceSensitivity::Confidential:
            return "confidential";
        case ResourceSensitivity::Restricted:
            return "restricted";
    }

    return "unknown";
}

} // namespace neuron

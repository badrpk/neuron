#include "neuron/prompt_security.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <regex>
#include <string>

namespace neuron {
namespace {

std::string lower_copy(
    const std::string& input
) {
    std::string out = input;

    std::transform(
        out.begin(),
        out.end(),
        out.begin(),
        [](unsigned char c) {
            return static_cast<char>(
                std::tolower(c)
            );
        }
    );

    return out;
}

double clamp01(double value) {
    return std::max(
        0.0,
        std::min(
            1.0,
            value
        )
    );
}

double keyword_score(
    const std::string& text,
    const std::vector<std::string>& patterns
) {
    double score = 0.0;

    for (const auto& pattern : patterns) {
        if (
            text.find(pattern) !=
            std::string::npos
        ) {
            score += 0.34;
        }
    }

    return clamp01(score);
}

bool regex_match_any(
    const std::string& text,
    const std::vector<std::regex>& patterns
) {
    for (const auto& pattern : patterns) {
        if (
            std::regex_search(
                text,
                pattern
            )
        ) {
            return true;
        }
    }

    return false;
}

} // namespace

PromptSecurityFeatures
PromptInjectionClassifier::extract_features(
    const std::string& prompt
) const {
    const std::string text =
        lower_copy(prompt);

    PromptSecurityFeatures f;

    f.instruction_override =
        keyword_score(
            text,
            {
                "ignore previous instructions",
                "ignore all previous instructions",
                "disregard previous instructions",
                "override previous instructions",
                "forget your instructions",
                "do not follow previous instructions"
            }
        );

    f.hierarchy_probe =
        keyword_score(
            text,
            {
                "system prompt",
                "developer prompt",
                "hidden instructions",
                "internal instructions",
                "reveal your instructions",
                "show your prompt"
            }
        );

    f.secret_exfiltration =
        keyword_score(
            text,
            {
                "api key",
                "access token",
                "password",
                "credentials",
                "secret key",
                "private key",
                "environment variables"
            }
        );

    f.privilege_escalation =
        keyword_score(
            text,
            {
                "bypass policy",
                "disable safety",
                "gain admin",
                "root access",
                "elevate privileges",
                "ignore authorization"
            }
        );

    f.tool_abuse =
        keyword_score(
            text,
            {
                "run this command",
                "execute this command",
                "call the tool",
                "invoke the tool",
                "send this file",
                "upload credentials"
            }
        );

    f.indirect_instruction =
        keyword_score(
            text,
            {
                "the document says to",
                "the webpage instructs you to",
                "follow the instructions in this file",
                "obey the instructions below",
                "retrieved content says"
            }
        );

    const std::vector<std::regex>
        obfuscation_patterns = {
            std::regex(
                R"([A-Za-z0-9+/]{40,}={0,2})"
            ),
            std::regex(
                R"(\\x[0-9a-fA-F]{2})"
            ),
            std::regex(
                R"(%[0-9a-fA-F]{2}%[0-9a-fA-F]{2})"
            )
        };

    if (
        regex_match_any(
            prompt,
            obfuscation_patterns
        )
    ) {
        f.obfuscation = 0.7;
    }

    return f;
}

PromptSecurityPrediction
PromptInjectionClassifier::classify(
    const std::string& prompt
) const {
    PromptSecurityPrediction result;

    result.features =
        extract_features(prompt);

    const auto& f =
        result.features;

    result.injection_probability =
        clamp01(
            f.instruction_override * 0.55 +
            f.indirect_instruction * 0.20 +
            f.obfuscation * 0.10 +
            f.tool_abuse * 0.15
        );

    result.jailbreak_probability =
        clamp01(
            f.instruction_override * 0.45 +
            f.privilege_escalation * 0.45 +
            f.hierarchy_probe * 0.10
        );

    result.exfiltration_probability =
        clamp01(
            f.secret_exfiltration * 0.65 +
            f.hierarchy_probe * 0.20 +
            f.tool_abuse * 0.15
        );

    result.privilege_escalation_probability =
        clamp01(
            f.privilege_escalation * 0.70 +
            f.instruction_override * 0.20 +
            f.tool_abuse * 0.10
        );

    result.overall_risk =
        clamp01(
            std::max({
                result.injection_probability,
                result.jailbreak_probability,
                result.exfiltration_probability,
                result.privilege_escalation_probability
            }) +
            f.obfuscation * 0.10
        );

    result.benign_probability =
        clamp01(
            1.0 -
            result.overall_risk
        );

    if (
        f.instruction_override >= 0.65
        &&
        (
            f.secret_exfiltration >= 0.30
            ||
            f.privilege_escalation >= 0.30
        )
    ) {
        result.decision =
            SecurityDecision::Block;

        result.reasons.push_back(
            "instruction_override_with_sensitive_intent"
        );
    } else if (
        result.exfiltration_probability >= 0.60
        ||
        result.privilege_escalation_probability >= 0.60
    ) {
        result.decision =
            SecurityDecision::Block;

        result.reasons.push_back(
            "high_sensitive_operation_risk"
        );
    } else if (
        result.injection_probability >= 0.55
        ||
        result.jailbreak_probability >= 0.55
    ) {
        result.decision =
            SecurityDecision::Isolate;

        result.reasons.push_back(
            "prompt_injection_risk"
        );
    } else if (
        result.overall_risk >= 0.30
    ) {
        result.decision =
            SecurityDecision::RequireReview;

        result.reasons.push_back(
            "ambiguous_security_risk"
        );
    } else {
        result.decision =
            SecurityDecision::Allow;
    }

    if (f.hierarchy_probe > 0.0) {
        result.reasons.push_back(
            "instruction_hierarchy_probe"
        );
    }

    if (f.obfuscation > 0.0) {
        result.reasons.push_back(
            "obfuscated_payload"
        );
    }

    if (f.indirect_instruction > 0.0) {
        result.reasons.push_back(
            "indirect_instruction"
        );
    }

    return result;
}

std::string
PromptInjectionClassifier::decision_name(
    SecurityDecision decision
) {
    switch (decision) {
        case SecurityDecision::Allow:
            return "ALLOW";

        case SecurityDecision::Isolate:
            return "ISOLATE";

        case SecurityDecision::RequireReview:
            return "REQUIRE_REVIEW";

        case SecurityDecision::Block:
            return "BLOCK";
    }

    return "UNKNOWN";
}

} // namespace neuron

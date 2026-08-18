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

std::string normalize_security_text(
    const std::string& input
) {
    std::string lowered =
        lower_copy(input);

    std::string out;
    out.reserve(
        lowered.size()
    );

    for (
        std::size_t i = 0;
        i < lowered.size();
        ++i
    ) {
        const unsigned char c =
            static_cast<unsigned char>(
                lowered[i]
            );

        /*
         * Normalize punctuation separators commonly
         * used to split security keywords:
         *
         *   i_g_n_o_r_e
         *   ignore...previous
         *   IGNORE-PREVIOUS
         */
        if (
            c == '_' ||
            c == '-' ||
            c == '.' ||
            c == '\t' ||
            c == '\n' ||
            c == '\r'
        ) {
            out.push_back(' ');
            continue;
        }

        out.push_back(
            static_cast<char>(c)
        );
    }

    /*
     * Collapse repeated spaces.
     */
    std::string compact;
    compact.reserve(
        out.size()
    );

    bool previous_space = false;

    for (char c : out) {
        const bool is_space =
            std::isspace(
                static_cast<unsigned char>(c)
            );

        if (is_space) {
            if (!previous_space) {
                compact.push_back(' ');
            }
        } else {
            compact.push_back(c);
        }

        previous_space =
            is_space;
    }

    return compact;
}

bool contains_any(
    const std::string& text,
    const std::vector<std::string>& patterns
) {
    for (const auto& pattern : patterns) {
        if (
            text.find(pattern) !=
            std::string::npos
        ) {
            return true;
        }
    }

    return false;
}

bool benign_discussion_context(
    const std::string& text
) {
    /*
     * These phrases usually describe or teach
     * security rather than requesting disclosure.
     *
     * This is deliberately narrow so it does not
     * suppress explicit attack verbs.
     */
    const bool educational =
        contains_any(
            text,
            {
                "explain ",
                "describe ",
                "what is ",
                "what does ",
                "how can ",
                "how should ",
                "why ",
                "write documentation",
                "create a checklist",
                "techniques for defending",
                "security concept",
                "security research"
            }
        );

    const bool active_attack =
        contains_any(
            text,
            {
                "reveal ",
                "show me ",
                "print ",
                "return the password",
                "expose ",
                "disclose ",
                "extract ",
                "send me ",
                "upload credentials",
                "gain admin",
                "become root",
                "elevate privileges",
                "bypass policy",
                "disable safety",
                "ignore authorization",
                "ignore previous",
                "ignore all previous",
                "disregard",
                "override previous",
                "forget your instructions",
                "forget every rule",
                "obey the commands"
            }
        );

    return (
        educational &&
        !active_attack
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
            /*
             * One explicit high-signal security phrase
             * must be meaningful by itself.
             *
             * Multiple corroborating phrases saturate
             * toward 1.0.
             */
            score += 0.60;
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
        normalize_security_text(
            prompt
        );

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
                "do not follow previous instructions",
                "disregard all prior instructions",
                "previous instructions are invalid",
                "forget every rule above",
                "obey the commands below",
                "previous instructions",
                "prior instructions"
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
                "ignore authorization",
                "turn off security restrictions",
                "authorization policy",
                "security restrictions",
                "disable the security layer",
                "administrator permissions",
                "restricted tools",
                "become root"
            }
        );

    /*
     * Compact multilingual attack lexicon.
     *
     * These phrases are intentionally narrow and
     * correspond to instruction override + secret
     * disclosure intents, not general language ID.
     */
    f.instruction_override =
        clamp01(
            f.instruction_override +
            keyword_score(
                text,
                {
                    "ignora todas las instrucciones anteriores",
                    "ignorez toutes les instructions précédentes",
                    "ignoriere alle vorherigen anweisungen",
                    "ignora le istruzioni precedenti",
                    "پچھلی تمام ہدایات نظر انداز کریں",
                    "تمام پچھلی ہدایات بھول جائیں",
                    "以前の指示をすべて無視",
                    "忽略之前的所有指令",
                    "игнорируй предыдущие инструкции",
                    "önceki tüm talimatları yok say"
                }
            )
        );

    f.secret_exfiltration =
        clamp01(
            f.secret_exfiltration +
            keyword_score(
                text,
                {
                    "revela la contraseña",
                    "révélez la clé api",
                    "zeige das passwort",
                    "mostra la chiave privata",
                    "پاس ورڈ دکھائیں",
                    "api key ظاہر کریں",
                    "apiキーを表示",
                    "显示密码",
                    "покажи пароль",
                    "api anahtarını göster"
                }
            )
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
                "retrieved content says",
                "instructions in this file",
                "retrieved document",
                "retrieved file",
                "hidden instructions in this document",
                "instructions below from the retrieved content",
                "conflict with your rules"
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

    /*
     * Delimiter-based evasion such as
     * i_g_n_o_r_e or IGNORE-PREVIOUS.
     */
    if (
        contains_any(
            text,
            {
                "i g n o r e previous instructions",
                "ignore previous instructions"
            }
        )
    ) {
        f.obfuscation =
            std::max(
                f.obfuscation,
                0.50
            );

        f.instruction_override =
            std::max(
                f.instruction_override,
                0.60
            );
    }

    if (
        benign_discussion_context(
            text
        )
    ) {
        /*
         * Mentioning passwords/API keys while
         * discussing defense is not equivalent to
         * requesting disclosure.
         */
        f.secret_exfiltration *= 0.15;
        f.hierarchy_probe *= 0.25;
        f.privilege_escalation *= 0.25;
        f.tool_abuse *= 0.25;
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
            f.instruction_override * 0.75 +
            f.indirect_instruction * 0.35 +
            f.obfuscation * 0.15 +
            f.tool_abuse * 0.20
        );

    result.jailbreak_probability =
        clamp01(
            f.instruction_override * 0.60 +
            f.privilege_escalation * 0.65 +
            f.hierarchy_probe * 0.20
        );

    result.exfiltration_probability =
        clamp01(
            f.secret_exfiltration * 0.75 +
            f.hierarchy_probe * 0.35 +
            f.tool_abuse * 0.25
        );

    result.privilege_escalation_probability =
        clamp01(
            f.privilege_escalation * 0.80 +
            f.instruction_override * 0.30 +
            f.tool_abuse * 0.20
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
        f.instruction_override >= 0.50
        &&
        (
            f.secret_exfiltration >= 0.50
            ||
            f.privilege_escalation >= 0.50
            ||
            f.hierarchy_probe >= 0.50
        )
    ) {
        result.decision =
            SecurityDecision::Block;

        result.reasons.push_back(
            "instruction_override_with_sensitive_intent"
        );
    } else if (
        result.exfiltration_probability >= 0.55
        ||
        result.privilege_escalation_probability >= 0.55
    ) {
        result.decision =
            SecurityDecision::Block;

        result.reasons.push_back(
            "high_sensitive_operation_risk"
        );
    } else if (
        result.injection_probability >= 0.40
        ||
        result.jailbreak_probability >= 0.45
        ||
        f.instruction_override >= 0.50
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

#ifndef NEURON_PROMPT_SECURITY_HPP
#define NEURON_PROMPT_SECURITY_HPP

#include <string>
#include <vector>

namespace neuron {

enum class SecurityDecision {
    Allow,
    Isolate,
    RequireReview,
    Block
};

struct PromptSecurityFeatures {
    double instruction_override = 0.0;
    double hierarchy_probe = 0.0;
    double secret_exfiltration = 0.0;
    double privilege_escalation = 0.0;
    double obfuscation = 0.0;
    double indirect_instruction = 0.0;
    double tool_abuse = 0.0;
};

struct PromptSecurityPrediction {
    double benign_probability = 1.0;
    double injection_probability = 0.0;
    double jailbreak_probability = 0.0;
    double exfiltration_probability = 0.0;
    double privilege_escalation_probability = 0.0;
    double overall_risk = 0.0;

    SecurityDecision decision =
        SecurityDecision::Allow;

    PromptSecurityFeatures features;

    std::vector<std::string> reasons;
};

class PromptInjectionClassifier {
public:
    PromptSecurityPrediction classify(
        const std::string& prompt
    ) const;

    static std::string decision_name(
        SecurityDecision decision
    );

private:
    PromptSecurityFeatures extract_features(
        const std::string& prompt
    ) const;
};

} // namespace neuron

#endif

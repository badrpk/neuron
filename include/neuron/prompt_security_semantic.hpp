#ifndef NEURON_PROMPT_SECURITY_SEMANTIC_HPP
#define NEURON_PROMPT_SECURITY_SEMANTIC_HPP

#include "neuron/prompt_security_spiking.hpp"

#include <string>
#include <vector>

namespace neuron {

struct PromptSecuritySemanticConcepts {
    double authority_replacement = 0.0;
    double instruction_supersession = 0.0;
    double secret_disclosure_request = 0.0;
    double authorization_bypass = 0.0;
    double privilege_acquisition = 0.0;
    double external_instruction_provenance = 0.0;
    double quoted_or_educational_context = 0.0;
    double encoded_or_obfuscated_content = 0.0;

    double malicious_intent = 0.0;
};

struct PromptSecuritySemanticPrediction {
    PromptSecuritySemanticConcepts concepts;

    double risk = 0.0;
    SecurityDecision decision =
        SecurityDecision::Allow;

    std::vector<std::string> reasons;
};

struct PromptSecurityV5Prediction {
    SpikingSecurityEnsemblePrediction legacy;
    PromptSecuritySemanticPrediction semantic;

    double final_risk = 0.0;

    bool contextual_downgrade = false;
    bool hard_legacy_floor = false;

    SecurityDecision final_decision =
        SecurityDecision::Allow;

    std::vector<std::string> reasons;
};

class PromptSecuritySemanticExtractor {
public:
    PromptSecuritySemanticPrediction
    classify(
        const std::string& prompt
    ) const;
};

class PromptSecurityV5Ensemble {
public:
    PromptSecurityV5Prediction
    classify(
        const std::string& prompt
    );

private:
    PromptSecuritySpikingEnsemble legacy_;
    PromptSecuritySemanticExtractor semantic_;
};

} // namespace neuron

#endif

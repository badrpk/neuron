#ifndef NEURON_PROMPT_SECURITY_SPIKING_HPP
#define NEURON_PROMPT_SECURITY_SPIKING_HPP

#include "neuron/neuron_engine.hpp"
#include "neuron/prompt_security.hpp"
#include "neuron/prompt_security_neural.hpp"

#include <array>
#include <string>

namespace neuron {

struct SpikingSecurityPrediction {
    double benign_activity = 0.0;
    double injection_activity = 0.0;
    double exfiltration_activity = 0.0;
    double privilege_activity = 0.0;

    double overall_risk = 0.0;

    SecurityDecision decision =
        SecurityDecision::Allow;
};

class PromptSecuritySpikingHead {
public:
    PromptSecuritySpikingHead();

    SpikingSecurityPrediction predict(
        const PromptSecurityFeatures& features
    );

private:
    NeuronEngine engine_;

    static std::array<double, 9>
    encode_features(
        const PromptSecurityFeatures& features
    );

    static double normalize_voltage(
        double voltage
    );
};

struct SpikingSecurityEnsemblePrediction {
    PromptSecurityPrediction deterministic;
    NeuralSecurityPrediction neural;
    SpikingSecurityPrediction spiking;

    SecurityDecision final_decision =
        SecurityDecision::Allow;

    double final_risk = 0.0;
};

class PromptSecuritySpikingEnsemble {
public:
    SpikingSecurityEnsemblePrediction classify(
        const std::string& prompt
    );

private:
    PromptInjectionClassifier deterministic_;
    PromptSecurityNeuralHead neural_;
    PromptSecuritySpikingHead spiking_;
};

} // namespace neuron

#endif

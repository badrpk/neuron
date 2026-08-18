#ifndef NEURON_PROMPT_SECURITY_NEURAL_HPP
#define NEURON_PROMPT_SECURITY_NEURAL_HPP

#include "neuron/prompt_security.hpp"

#include <array>
#include <string>
#include <vector>

namespace neuron {

struct NeuralSecurityPrediction {
    double benign_probability = 1.0;
    double injection_probability = 0.0;
    double exfiltration_probability = 0.0;
    double privilege_probability = 0.0;
    double overall_risk = 0.0;

    std::array<double, 4> raw_outputs{
        0.0, 0.0, 0.0, 0.0
    };
};

struct SecurityEnsemblePrediction {
    PromptSecurityPrediction deterministic;
    NeuralSecurityPrediction neural;

    SecurityDecision final_decision =
        SecurityDecision::Allow;

    double final_risk = 0.0;

    std::vector<std::string> reasons;
};

class PromptSecurityNeuralHead {
public:
    PromptSecurityNeuralHead();

    NeuralSecurityPrediction predict(
        const PromptSecurityFeatures& features
    );

    void train_fixture(
        const PromptSecurityFeatures& features,
        const std::array<double, 4>& target,
        double learning_rate = 0.10,
        int epochs = 16
    );

private:
    std::array<
        std::array<double, 7>,
        4
    > weights_{};

    std::array<double, 4> bias_{};

    static std::array<double, 7>
    feature_vector(
        const PromptSecurityFeatures& features
    );

    static double sigmoid(double x);
};

class PromptSecurityEnsemble {
public:
    SecurityEnsemblePrediction classify(
        const std::string& prompt
    );

    PromptSecurityNeuralHead&
    neural_head() {
        return neural_;
    }

private:
    PromptInjectionClassifier deterministic_;
    PromptSecurityNeuralHead neural_;
};

} // namespace neuron

#endif

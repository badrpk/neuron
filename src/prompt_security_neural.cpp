#include "neuron/prompt_security_neural.hpp"

#include <algorithm>
#include <cmath>

namespace neuron {
namespace {

double clamp01(double value) {
    return std::max(
        0.0,
        std::min(
            1.0,
            value
        )
    );
}

int decision_rank(
    SecurityDecision decision
) {
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

SecurityDecision max_decision(
    SecurityDecision a,
    SecurityDecision b
) {
    return (
        decision_rank(a) >=
        decision_rank(b)
    )
        ? a
        : b;
}

} // namespace

PromptSecurityNeuralHead::
PromptSecurityNeuralHead() {
    /*
     * Deterministic initialization.
     *
     * Rows:
     *   0 benign
     *   1 injection
     *   2 exfiltration
     *   3 privilege escalation
     *
     * Columns:
     *   instruction override
     *   hierarchy probe
     *   secret exfiltration
     *   privilege escalation
     *   obfuscation
     *   indirect instruction
     *   tool abuse
     */
    weights_ = {{
        {{
            -1.3, -0.8, -1.0,
            -1.0, -0.5, -0.7, -0.7
        }},
        {{
             1.6,  0.4,  0.2,
             0.5,  0.6,  1.1,  0.8
        }},
        {{
             0.5,  0.8,  1.8,
             0.3,  0.4,  0.3,  0.8
        }},
        {{
             0.7,  0.3,  0.2,
             1.9,  0.3,  0.2,  0.9
        }}
    }};

    bias_ = {{
        1.2,
        -0.8,
        -1.0,
        -1.0
    }};
}

std::array<double, 7>
PromptSecurityNeuralHead::feature_vector(
    const PromptSecurityFeatures& f
) {
    return {{
        f.instruction_override,
        f.hierarchy_probe,
        f.secret_exfiltration,
        f.privilege_escalation,
        f.obfuscation,
        f.indirect_instruction,
        f.tool_abuse
    }};
}

double
PromptSecurityNeuralHead::sigmoid(
    double x
) {
    return (
        1.0 /
        (
            1.0 +
            std::exp(-x)
        )
    );
}

NeuralSecurityPrediction
PromptSecurityNeuralHead::predict(
    const PromptSecurityFeatures& features
) {
    const auto input =
        feature_vector(features);

    std::array<double, 4> output{};

    for (
        std::size_t row = 0;
        row < weights_.size();
        ++row
    ) {
        double activation =
            bias_[row];

        /*
         * Event/spike-style accumulation:
         * security features act as normalized
         * sensory firing intensities.
         */
        for (
            std::size_t col = 0;
            col < input.size();
            ++col
        ) {
            activation +=
                weights_[row][col] *
                input[col];
        }

        output[row] =
            sigmoid(activation);
    }

    NeuralSecurityPrediction result;

    result.raw_outputs = output;

    result.benign_probability =
        output[0];

    result.injection_probability =
        output[1];

    result.exfiltration_probability =
        output[2];

    result.privilege_probability =
        output[3];

    result.overall_risk =
        clamp01(
            std::max({
                output[1],
                output[2],
                output[3]
            })
        );

    return result;
}

void
PromptSecurityNeuralHead::train_fixture(
    const PromptSecurityFeatures& features,
    const std::array<double, 4>& target,
    double learning_rate,
    int epochs
) {
    const auto input =
        feature_vector(features);

    const double rate =
        std::max(
            0.0001,
            std::min(
                1.0,
                learning_rate
            )
        );

    const int loops =
        std::max(
            1,
            std::min(
                10000,
                epochs
            )
        );

    for (
        int epoch = 0;
        epoch < loops;
        ++epoch
    ) {
        for (
            std::size_t row = 0;
            row < weights_.size();
            ++row
        ) {
            double activation =
                bias_[row];

            for (
                std::size_t col = 0;
                col < input.size();
                ++col
            ) {
                activation +=
                    weights_[row][col] *
                    input[col];
            }

            const double prediction =
                sigmoid(activation);

            const double error =
                clamp01(target[row]) -
                prediction;

            /*
             * Reward-like local plasticity:
             * output error modulates each
             * active feature synapse.
             */
            for (
                std::size_t col = 0;
                col < input.size();
                ++col
            ) {
                weights_[row][col] +=
                    rate *
                    error *
                    input[col];
            }

            bias_[row] +=
                rate *
                error *
                0.25;
        }
    }
}

SecurityEnsemblePrediction
PromptSecurityEnsemble::classify(
    const std::string& prompt
) {
    SecurityEnsemblePrediction result;

    result.deterministic =
        deterministic_.classify(prompt);

    result.neural =
        neural_.predict(
            result.deterministic.features
        );

    result.final_risk =
        std::max(
            result.deterministic.overall_risk,
            result.neural.overall_risk
        );

    SecurityDecision neural_decision =
        SecurityDecision::Allow;

    if (
        result.neural.exfiltration_probability >=
            0.75
        ||
        result.neural.privilege_probability >=
            0.75
    ) {
        neural_decision =
            SecurityDecision::Block;
    } else if (
        result.neural.injection_probability >=
            0.65
    ) {
        neural_decision =
            SecurityDecision::Isolate;
    } else if (
        result.neural.overall_risk >=
            0.50
    ) {
        neural_decision =
            SecurityDecision::RequireReview;
    }

    /*
     * CRITICAL SAFETY INVARIANT:
     *
     * Final decision is the more restrictive
     * of deterministic and neural decisions.
     *
     * Neural intelligence can escalate caution
     * but can never downgrade a deterministic
     * security decision.
     */
    result.final_decision =
        max_decision(
            result.deterministic.decision,
            neural_decision
        );

    result.reasons =
        result.deterministic.reasons;

    if (
        decision_rank(neural_decision) >
        decision_rank(
            result.deterministic.decision
        )
    ) {
        result.reasons.push_back(
            "neural_security_escalation"
        );
    }

    return result;
}

} // namespace neuron

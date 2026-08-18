#include "neuron/prompt_security_spiking.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <vector>

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

PromptSecuritySpikingHead::
PromptSecuritySpikingHead()
    : engine_(9, 18, 9) {
    /*
     * The clean origin/main NeuronEngine used by
     * this branch has no online-STDP API.
     *
     * Security inference therefore uses the
     * fixed LIF engine state from this base.
     */
}

std::array<double, 9>
PromptSecuritySpikingHead::encode_features(
    const PromptSecurityFeatures& f
) {
    return {{
        clamp01(
            f.instruction_override
        ),

        clamp01(
            f.hierarchy_probe
        ),

        clamp01(
            f.secret_exfiltration
        ),

        clamp01(
            f.privilege_escalation
        ),

        clamp01(
            f.obfuscation
        ),

        clamp01(
            f.indirect_instruction
        ),

        clamp01(
            f.tool_abuse
        ),

        /*
         * Composite injection activity.
         */
        clamp01(
            f.instruction_override * 0.60 +
            f.indirect_instruction * 0.25 +
            f.tool_abuse * 0.15
        ),

        /*
         * Composite sensitive-operation activity.
         */
        clamp01(
            f.secret_exfiltration * 0.50 +
            f.privilege_escalation * 0.35 +
            f.hierarchy_probe * 0.15
        )
    }};
}

double
PromptSecuritySpikingHead::normalize_voltage(
    double voltage
) {
    /*
     * Typical LIF operating range here is around
     * rest=-70 mV and threshold=-55 mV.
     */
    return clamp01(
        (voltage + 70.0) /
        15.0
    );
}

SpikingSecurityPrediction
PromptSecuritySpikingHead::predict(
    const PromptSecurityFeatures& features
) {
    engine_.reset();

    const auto encoded =
        encode_features(features);

    std::vector<double> sensory(
        encoded.begin(),
        encoded.end()
    );

    /*
     * Repeated event presentation converts
     * normalized security features into temporal
     * spiking dynamics.
     */
    constexpr int simulation_steps = 16;

    double injection_accumulator = 0.0;
    double exfiltration_accumulator = 0.0;
    double privilege_accumulator = 0.0;
    double benign_accumulator = 0.0;

    for (
        int step = 0;
        step < simulation_steps;
        ++step
    ) {
        engine_.set_sensory_input(
            sensory
        );

        engine_.step_simulation();

        const auto outputs =
            engine_.get_motor_outputs();

        if (outputs.size() >= 4) {
            benign_accumulator +=
                clamp01(outputs[0]);

            injection_accumulator +=
                clamp01(outputs[1]);

            exfiltration_accumulator +=
                clamp01(outputs[2]);

            privilege_accumulator +=
                clamp01(outputs[3]);
        }
    }

    /*
     * Preserve actual NeuronEngine temporal
     * activity but combine it with feature
     * excitation because the base network was
     * not originally trained for security labels.
     */
    const double temporal_injection =
        injection_accumulator /
        simulation_steps;

    const double temporal_exfiltration =
        exfiltration_accumulator /
        simulation_steps;

    const double temporal_privilege =
        privilege_accumulator /
        simulation_steps;

    SpikingSecurityPrediction result;

    result.benign_activity =
        clamp01(
            (
                benign_accumulator /
                simulation_steps
            ) *
            0.30 +
            (
                1.0 -
                std::max({
                    encoded[7],
                    encoded[8]
                })
            ) *
            0.70
        );

    result.injection_activity =
        clamp01(
            temporal_injection * 0.30 +
            encoded[7] * 0.70
        );

    result.exfiltration_activity =
        clamp01(
            temporal_exfiltration * 0.30 +
            features.secret_exfiltration * 0.70
        );

    result.privilege_activity =
        clamp01(
            temporal_privilege * 0.30 +
            features.privilege_escalation * 0.70
        );

    result.overall_risk =
        std::max({
            result.injection_activity,
            result.exfiltration_activity,
            result.privilege_activity
        });

    if (
        result.exfiltration_activity >=
            0.60
        ||
        result.privilege_activity >=
            0.60
    ) {
        result.decision =
            SecurityDecision::Block;
    } else if (
        result.injection_activity >=
            0.40
    ) {
        result.decision =
            SecurityDecision::Isolate;
    } else if (
        result.overall_risk >=
            0.25
    ) {
        result.decision =
            SecurityDecision::RequireReview;
    } else {
        result.decision =
            SecurityDecision::Allow;
    }

    return result;
}

SpikingSecurityEnsemblePrediction
PromptSecuritySpikingEnsemble::classify(
    const std::string& prompt
) {
    SpikingSecurityEnsemblePrediction result;

    result.deterministic =
        deterministic_.classify(
            prompt
        );

    result.neural =
        neural_.predict(
            result.deterministic.features
        );

    result.spiking =
        spiking_.predict(
            result.deterministic.features
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
     * Three-way monotonic ensemble:
     *
     * deterministic floor
     * neural head
     * real NeuronEngine LIF head
     */
    result.final_decision =
        max_decision(
            result.deterministic.decision,
            max_decision(
                neural_decision,
                result.spiking.decision
            )
        );

    result.final_risk =
        std::max({
            result.deterministic.overall_risk,
            result.neural.overall_risk,
            result.spiking.overall_risk
        });

    return result;
}

} // namespace neuron

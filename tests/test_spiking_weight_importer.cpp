#include "neuron/spiking_weight_importer.hpp"

#include <cassert>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

int main() {
    neuron::SpikingWeightImporter importer(32, 8);

    const std::vector<float> dense = {
        0.0f, 0.25f,
        -0.5f, 1.0f,
    };
    assert(importer.import_from_dense_weights(dense, 2, 2));
    assert(std::abs(importer.synaptic_weight(0, 0)) < 1e-12);
    assert(std::abs(importer.synaptic_weight(0, 1) - std::tanh(0.25) * 0.8) < 1e-12);

    bool malformed_rejected = false;
    try {
        importer.import_from_dense_weights({1.0f}, 2, 2);
    } catch (const std::invalid_argument&) {
        malformed_rejected = true;
    }
    assert(malformed_rejected);

    importer.train_stdp_on_text("alpha beta alpha gamma", 3);
    assert(importer.vocabulary_size() == 3);
    assert(importer.predict_next_token_spiking("alpha") == "beta");
    assert(importer.predict_next_token_spiking("unknown").empty());

    const double before = importer.synaptic_weight(0, 1);
    importer.train_stdp_on_text("alpha beta", 1);
    const double after = importer.synaptic_weight(0, 1);
    assert(after > before);

    bool negative_epochs_rejected = false;
    try {
        importer.train_stdp_on_text("alpha beta", -1);
    } catch (const std::invalid_argument&) {
        negative_epochs_rejected = true;
    }
    assert(negative_epochs_rejected);

    return 0;
}

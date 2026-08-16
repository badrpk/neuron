#ifndef NEURON_SPIKING_WEIGHT_IMPORTER_HPP
#define NEURON_SPIKING_WEIGHT_IMPORTER_HPP

#include <string>
#include <unordered_map>
#include <vector>

#include "neuron/neuron_engine.hpp"

namespace neuron {

struct TokenSpikeMapping {
    std::string token;
    int token_id;
    std::vector<double> spike_frequency_pattern;
};

class SpikingWeightImporter {
public:
    SpikingWeightImporter(int vocab_size = 32000, int hidden_dim = 512);

    bool import_from_dense_weights(
        const std::vector<float>& dense_weights,
        int rows,
        int cols
    );

    void train_stdp_on_text(const std::string& text_corpus, int epochs = 5);

    std::string predict_next_token_spiking(const std::string& prompt) const;

    int vocabulary_size() const noexcept;
    double synaptic_weight(int from_token_id, int to_token_id) const;

private:
    static constexpr int kMaxSynapses = 1000;

    int vocab_size_;
    int hidden_dim_;
    std::unordered_map<std::string, TokenSpikeMapping> vocab_map_;
    std::vector<std::string> id_to_token_;
    std::vector<std::vector<double>> stdp_synaptic_matrix_;
};

} // namespace neuron

#endif // NEURON_SPIKING_WEIGHT_IMPORTER_HPP

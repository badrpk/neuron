#include "neuron/spiking_weight_importer.hpp"

#include <algorithm>
#include <cmath>
#include <sstream>
#include <stdexcept>

namespace neuron {

SpikingWeightImporter::SpikingWeightImporter(int vocab_size, int hidden_dim)
    : vocab_size_(vocab_size), hidden_dim_(hidden_dim)
{
    if (vocab_size_ <= 0) {
        throw std::invalid_argument("vocab_size must be positive");
    }
    if (hidden_dim_ <= 0) {
        throw std::invalid_argument("hidden_dim must be positive");
    }
    stdp_synaptic_matrix_.assign(
        kMaxSynapses,
        std::vector<double>(kMaxSynapses, 0.1)
    );
}

bool SpikingWeightImporter::import_from_dense_weights(
    const std::vector<float>& dense_weights,
    int rows,
    int cols
) {
    if (rows <= 0 || cols <= 0) {
        throw std::invalid_argument("rows and cols must be positive");
    }
    const auto expected = static_cast<size_t>(rows) * static_cast<size_t>(cols);
    if (dense_weights.size() != expected) {
        throw std::invalid_argument("dense_weights size does not match rows * cols");
    }

    const int bounded_rows = std::min(rows, kMaxSynapses);
    const int bounded_cols = std::min(cols, kMaxSynapses);
    for (int r = 0; r < bounded_rows; ++r) {
        for (int c = 0; c < bounded_cols; ++c) {
            const float weight = dense_weights[
                static_cast<size_t>(r) * static_cast<size_t>(cols) +
                static_cast<size_t>(c)
            ];
            stdp_synaptic_matrix_[r][c] = std::tanh(weight) * 0.8;
        }
    }
    return bounded_rows > 0 && bounded_cols > 0;
}

void SpikingWeightImporter::train_stdp_on_text(
    const std::string& text_corpus,
    int epochs
) {
    if (epochs < 0) {
        throw std::invalid_argument("epochs must be non-negative");
    }

    std::stringstream stream(text_corpus);
    std::string token;
    std::vector<std::string> tokens;

    while (stream >> token) {
        tokens.push_back(token);
        auto found = vocab_map_.find(token);
        if (found == vocab_map_.end()) {
            if (static_cast<int>(id_to_token_.size()) >= std::min(vocab_size_, kMaxSynapses)) {
                continue;
            }
            const int id = static_cast<int>(id_to_token_.size());
            id_to_token_.push_back(token);
            vocab_map_.emplace(
                token,
                TokenSpikeMapping{token, id, {}}
            );
        }
    }

    const double potentiation = 0.05 * std::exp(-1.0 / 20.0);
    for (int epoch = 0; epoch < epochs; ++epoch) {
        for (size_t i = 0; i + 1 < tokens.size(); ++i) {
            const auto first = vocab_map_.find(tokens[i]);
            const auto second = vocab_map_.find(tokens[i + 1]);
            if (first == vocab_map_.end() || second == vocab_map_.end()) {
                continue;
            }
            stdp_synaptic_matrix_[first->second.token_id][second->second.token_id] += potentiation;
        }
    }
}

std::string SpikingWeightImporter::predict_next_token_spiking(
    const std::string& prompt
) const {
    std::stringstream stream(prompt);
    std::string token;
    std::string last_token;
    while (stream >> token) {
        last_token = token;
    }

    const auto found = vocab_map_.find(last_token);
    if (found == vocab_map_.end()) {
        return {};
    }

    const int from_id = found->second.token_id;
    int best_id = -1;
    double best_weight = -1.0;
    for (int to_id = 0; to_id < static_cast<int>(id_to_token_.size()); ++to_id) {
        const double weight = stdp_synaptic_matrix_[from_id][to_id];
        if (weight > best_weight) {
            best_weight = weight;
            best_id = to_id;
        }
    }

    return best_id >= 0 ? id_to_token_[best_id] : std::string{};
}

int SpikingWeightImporter::vocabulary_size() const noexcept {
    return static_cast<int>(id_to_token_.size());
}

double SpikingWeightImporter::synaptic_weight(
    int from_token_id,
    int to_token_id
) const {
    if (from_token_id < 0 || from_token_id >= kMaxSynapses ||
        to_token_id < 0 || to_token_id >= kMaxSynapses) {
        throw std::out_of_range("token id is outside synaptic matrix bounds");
    }
    return stdp_synaptic_matrix_[from_token_id][to_token_id];
}

} // namespace neuron

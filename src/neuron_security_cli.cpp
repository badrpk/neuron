#include "neuron/prompt_security_api.hpp"
#include "neuron/prompt_security.hpp"

#include <iostream>
#include <sstream>
#include <string>

namespace {

std::string decision_name(
    neuron::SecurityDecision decision
) {
    switch (decision) {
        case neuron::SecurityDecision::Allow:
            return "ALLOW";
        case neuron::SecurityDecision::RequireReview:
            return "REQUIRE_REVIEW";
        case neuron::SecurityDecision::Isolate:
            return "ISOLATE";
        case neuron::SecurityDecision::Block:
            return "BLOCK";
    }

    return "BLOCK";
}

std::string json_escape(
    const std::string& value
) {
    std::ostringstream out;

    for (const char ch : value) {
        switch (ch) {
            case '\\':
                out << "\\\\";
                break;

            case '"':
                out << "\\\"";
                break;

            case '\n':
                out << "\\n";
                break;

            case '\r':
                out << "\\r";
                break;

            case '\t':
                out << "\\t";
                break;

            default:
                out << ch;
                break;
        }
    }

    return out.str();
}

} // namespace

int main() {
    std::ostringstream buffer;
    buffer << std::cin.rdbuf();

    const std::string input = buffer.str();

    neuron::PromptSecurityApi api;

    const auto result =
        api.classify_prompt(input);

    std::cout
        << "{"
        << "\"decision\":\""
        << decision_name(result.decision)
        << "\","
        << "\"risk\":"
        << result.risk
        << ","
        << "\"classifier_version\":\""
        << json_escape(result.classifier_version)
        << "\","
        << "\"policy_version\":\""
        << json_escape(result.policy_version)
        << "\","
        << "\"concepts\":{"
        << "\"authority_replacement\":"
        << result.concepts.authority_replacement
        << ","
        << "\"instruction_supersession\":"
        << result.concepts.instruction_supersession
        << ","
        << "\"secret_disclosure_request\":"
        << result.concepts.secret_disclosure_request
        << ","
        << "\"authorization_bypass\":"
        << result.concepts.authorization_bypass
        << ","
        << "\"privilege_acquisition\":"
        << result.concepts.privilege_acquisition
        << ","
        << "\"external_instruction_provenance\":"
        << result.concepts.external_instruction_provenance
        << ","
        << "\"quoted_or_educational_context\":"
        << result.concepts.quoted_or_educational_context
        << ","
        << "\"encoded_or_obfuscated_content\":"
        << result.concepts.encoded_or_obfuscated_content
        << ","
        << "\"malicious_intent\":"
        << result.concepts.malicious_intent
        << "},"
        << "\"reason_codes\":[";

    for (
        std::size_t i = 0;
        i < result.reason_codes.size();
        ++i
    ) {
        if (i != 0) {
            std::cout << ",";
        }

        std::cout
            << "\""
            << json_escape(
                result.reason_codes[i]
            )
            << "\"";
    }

    std::cout
        << "]"
        << "}"
        << std::endl;

    return 0;
}

#ifndef NEURON_PROMPT_SECURITY_API_HPP
#define NEURON_PROMPT_SECURITY_API_HPP

#include "neuron/prompt_security_semantic.hpp"

#include <string>
#include <vector>

namespace neuron {

enum class SecurityActionType {
    Informational,
    ShellProcess,
    ExternalApi,
    Payment,
    Procurement,
    InventoryMutation,
    DatabaseMutation,
    SecretAccess,
    BrowserAction,
    FilesystemWrite,
    AgentDelegation
};

enum class ResourceSensitivity {
    Public,
    Internal,
    Confidential,
    Restricted
};

struct SecurityConceptSnapshot {
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

struct PromptSecurityResult {
    SecurityDecision decision = SecurityDecision::Allow;
    double risk = 0.0;
    SecurityConceptSnapshot concepts;
    std::vector<std::string> reason_codes;
    std::string classifier_version = "prompt-security-v5.4";
    std::string policy_version = "policy-v1";
};

struct ActionSecurityContext {
    SecurityActionType action = SecurityActionType::Informational;
    ResourceSensitivity sensitivity = ResourceSensitivity::Public;
    bool human_confirmation_available = false;
};

struct ActionSecurityResult {
    PromptSecurityResult prompt;
    SecurityDecision decision = SecurityDecision::Allow;
    double risk = 0.0;
    std::vector<std::string> reason_codes;
};

struct AuditSecurityEvent {
    std::string source_component;
    std::string request_id;
    std::string input_hash;
    SecurityActionType action = SecurityActionType::Informational;
    ResourceSensitivity sensitivity = ResourceSensitivity::Public;
    SecurityDecision decision = SecurityDecision::Allow;
    double risk = 0.0;
    std::vector<std::string> reason_codes;
    std::string classifier_version;
    std::string policy_version;
};

class PromptSecurityApi {
public:
    PromptSecurityResult classify_prompt(
        const std::string& input
    );

    ActionSecurityResult authorize_action(
        const std::string& source_text,
        const ActionSecurityContext& context
    );

private:
    PromptSecurityV5Ensemble classifier_;
};

std::string security_action_name(
    SecurityActionType action
);

std::string resource_sensitivity_name(
    ResourceSensitivity sensitivity
);

} // namespace neuron

#endif

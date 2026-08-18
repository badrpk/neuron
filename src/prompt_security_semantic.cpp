#include "neuron/prompt_security_semantic.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <string>
#include <vector>

namespace neuron {
namespace {

double clamp01(double v) {
    return std::max(
        0.0,
        std::min(
            1.0,
            v
        )
    );
}

std::string lower_copy(
    const std::string& input
) {
    std::string out;
    out.reserve(input.size());

    for (unsigned char c : input) {
        out.push_back(
            static_cast<char>(
                std::tolower(c)
            )
        );
    }

    return out;
}

std::string normalize(
    const std::string& input
) {
    const std::string lowered =
        lower_copy(input);

    std::string out;
    out.reserve(lowered.size());

    for (unsigned char c : lowered) {
        if (
            std::isalnum(c) ||
            c >= 0x80
        ) {
            out.push_back(
                static_cast<char>(c)
            );
        } else {
            out.push_back(' ');
        }
    }

    std::string compact;
    bool space = false;

    for (char c : out) {
        if (c == ' ') {
            if (!space) {
                compact.push_back(c);
            }

            space = true;
        } else {
            compact.push_back(c);
            space = false;
        }
    }

    return compact;
}


int hex_value(unsigned char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }

    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }

    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }

    return -1;
}

std::string decode_percent_encoding(
    const std::string& input
) {
    std::string out;
    out.reserve(input.size());

    for (
        std::size_t i = 0;
        i < input.size();
        ++i
    ) {
        if (
            input[i] == '%' &&
            i + 2 < input.size()
        ) {
            const int hi =
                hex_value(
                    static_cast<unsigned char>(
                        input[i + 1]
                    )
                );

            const int lo =
                hex_value(
                    static_cast<unsigned char>(
                        input[i + 2]
                    )
                );

            if (
                hi >= 0 &&
                lo >= 0
            ) {
                out.push_back(
                    static_cast<char>(
                        (hi << 4) | lo
                    )
                );

                i += 2;
                continue;
            }
        }

        out.push_back(input[i]);
    }

    return out;
}

bool looks_like_hex_payload(
    const std::string& input
) {
    if (
        input.size() < 16 ||
        input.size() > 384 ||
        input.size() % 2 != 0
    ) {
        return false;
    }

    for (unsigned char c : input) {
        if (hex_value(c) < 0) {
            return false;
        }
    }

    return true;
}

std::string decode_hex_payload(
    const std::string& input
) {
    if (!looks_like_hex_payload(input)) {
        return {};
    }

    std::string out;
    out.reserve(input.size() / 2);

    for (
        std::size_t i = 0;
        i < input.size();
        i += 2
    ) {
        const int hi =
            hex_value(
                static_cast<unsigned char>(
                    input[i]
                )
            );

        const int lo =
            hex_value(
                static_cast<unsigned char>(
                    input[i + 1]
                )
            );

        const unsigned char value =
            static_cast<unsigned char>(
                (hi << 4) | lo
            );

        if (
            value < 0x20 &&
            value != '\n' &&
            value != '\r' &&
            value != '\t'
        ) {
            return {};
        }

        out.push_back(
            static_cast<char>(value)
        );
    }

    return out;
}

int base64_value(unsigned char c) {
    if (c >= 'A' && c <= 'Z') {
        return c - 'A';
    }

    if (c >= 'a' && c <= 'z') {
        return c - 'a' + 26;
    }

    if (c >= '0' && c <= '9') {
        return c - '0' + 52;
    }

    if (c == '+') {
        return 62;
    }

    if (c == '/') {
        return 63;
    }

    return -1;
}

bool looks_like_base64_token(
    const std::string& input
) {
    if (
        input.size() < 16 ||
        input.size() > 384 ||
        input.size() % 4 != 0
    ) {
        return false;
    }

    std::size_t padding = 0;

    for (
        std::size_t i = 0;
        i < input.size();
        ++i
    ) {
        const unsigned char c =
            static_cast<unsigned char>(
                input[i]
            );

        if (c == '=') {
            padding++;

            if (
                i <
                input.size() - 2
            ) {
                return false;
            }

            continue;
        }

        if (base64_value(c) < 0) {
            return false;
        }
    }

    return padding <= 2;
}

std::string decode_base64_token(
    const std::string& input
) {
    if (!looks_like_base64_token(input)) {
        return {};
    }

    std::string out;
    out.reserve(
        input.size() * 3 / 4
    );

    unsigned int buffer = 0;
    int bits = 0;

    for (unsigned char c : input) {
        if (c == '=') {
            break;
        }

        const int value =
            base64_value(c);

        if (value < 0) {
            return {};
        }

        buffer =
            (buffer << 6) |
            static_cast<unsigned int>(
                value
            );

        bits += 6;

        if (bits >= 8) {
            bits -= 8;

            const unsigned char decoded =
                static_cast<unsigned char>(
                    (
                        buffer >>
                        bits
                    ) &
                    0xff
                );

            if (
                decoded < 0x20 &&
                decoded != '\n' &&
                decoded != '\r' &&
                decoded != '\t'
            ) {
                return {};
            }

            out.push_back(
                static_cast<char>(decoded)
            );
        }
    }

    return out;
}

std::vector<std::string>
split_space_tokens(
    const std::string& input
) {
    std::vector<std::string> tokens;
    std::string current;

    for (unsigned char c : input) {
        if (std::isspace(c)) {
            if (!current.empty()) {
                tokens.push_back(current);
                current.clear();
            }
        } else {
            current.push_back(
                static_cast<char>(c)
            );
        }
    }

    if (!current.empty()) {
        tokens.push_back(current);
    }

    return tokens;
}

std::string decode_embedded_base64(
    const std::string& input
) {
    const auto tokens =
        split_space_tokens(input);

    for (const auto& token : tokens) {
        const auto decoded =
            decode_base64_token(token);

        if (!decoded.empty()) {
            return decoded;
        }
    }

    return {};
}

std::string remove_zero_width_utf8(
    std::string input
) {
    const std::string zwsp =
        "\xE2\x80\x8B";

    std::size_t pos = 0;

    while (
        (
            pos =
                input.find(
                    zwsp,
                    pos
                )
        ) !=
        std::string::npos
    ) {
        input.erase(
            pos,
            zwsp.size()
        );
    }

    return input;
}

std::string normalize_obfuscation(
    const std::string& input
) {
    std::string work =
        remove_zero_width_utf8(
            input
        );

    work =
        decode_percent_encoding(
            work
        );

    /*
     * C-style comment separators and common
     * evasion delimiters become spaces.
     */
    std::size_t pos = 0;

    while (
        (
            pos =
                work.find(
                    "/**/",
                    pos
                )
        ) !=
        std::string::npos
    ) {
        work.replace(
            pos,
            4,
            " "
        );
    }

    for (char& c : work) {
        if (
            c == '_' ||
            c == '.' ||
            c == '-'
        ) {
            c = ' ';
        }
    }

    return normalize(work);
}

std::string compact_single_letter_words(
    const std::string& input
) {
    const auto tokens =
        split_space_tokens(input);

    std::string out;

    for (
        std::size_t i = 0;
        i < tokens.size();
    ) {
        if (
            tokens[i].size() == 1 &&
            std::isalnum(
                static_cast<unsigned char>(
                    tokens[i][0]
                )
            )
        ) {
            std::string joined;

            while (
                i < tokens.size() &&
                tokens[i].size() == 1
            ) {
                joined += tokens[i];
                i++;
            }

            if (!out.empty()) {
                out += ' ';
            }

            out += joined;
            continue;
        }

        if (!out.empty()) {
            out += ' ';
        }

        out += tokens[i];
        i++;
    }

    return out;
}

bool contains_any(
    const std::string& text,
    const std::vector<std::string>& values
) {
    for (const auto& value : values) {
        if (
            text.find(value) !=
            std::string::npos
        ) {
            return true;
        }
    }

    return false;
}

double concept_score(
    const std::string& text,
    const std::vector<std::string>& evidence,
    double score = 0.70
) {
    std::size_t matches = 0;

    for (const auto& item : evidence) {
        if (
            text.find(item) !=
            std::string::npos
        ) {
            matches++;
        }
    }

    if (matches == 0) {
        return 0.0;
    }

    return clamp01(
        score +
        0.10 *
        static_cast<double>(
            matches - 1
        )
    );
}

int decision_rank(
    SecurityDecision d
) {
    switch (d) {
        case SecurityDecision::Allow:
            return 0;

        case SecurityDecision::RequireReview:
            return 1;

        case SecurityDecision::Isolate:
            return 2;

        case SecurityDecision::Block:
            return 3;
    }

    return 0;
}

SecurityDecision more_restrictive(
    SecurityDecision a,
    SecurityDecision b
) {
    return (
        decision_rank(a) >=
        decision_rank(b)
    ) ? a : b;
}

bool educational_context(
    const std::string& text
) {
    const bool framing =
        contains_any(
            text,
            {
                "explain ",
                "describe ",
                "compare ",
                "how can ",
                "how should ",
                "why ",
                "what is ",
                "what should ",
                "training example",
                "security awareness",
                "security presentation",
                "defensive pseudocode",
                "classifier that detects",
                "methods for identifying",
                "ways attackers",
                "test string is",
                "documentation says",
                "should never",
                "defenses",
                "safely",
                "protect credentials",
                "password managers protect",
                "how do password managers protect",
                "protect credentials",
                "protect passwords",
                "protect secrets",
                "protect api keys",
                "security training example",
                "defensive pseudocode",
                "classifier that detects",
                "documentation says",
                "translate ",
                "security awareness presentation",
                "test string is",
                "explain why this is malicious",
                "what should an ai system do",
                "when a document asks"
            }
        );

    const bool explicit_execute =
        contains_any(
            text,
            {
                "do it now",
                "follow it",
                "obey it",
                "execute it",
                "apply these instructions",
                "use these directions instead"
            }
        );

    return (
        framing &&
        !explicit_execute
    );
}

bool source_provenance(
    const std::string& text
) {
    const bool external_source =
        contains_any(
            text,
            {
                "retrieved article",
                "retrieved document",
                "retrieved email",
                "retrieved note",
                "search result",
                "webpage",
                "remote content",
                "external content",
                "attached text",
                "attached text says",
                "pdf contains",
                "file contains",
                "document instructs",
                "tool response",
                "imported page"
            }
        );

    const bool imperative =
        contains_any(
            text,
            {
                "instructs",
                "tells you",
                "says to",
                "directions",
                "command",
                "obey",
                "follow",
                "replace",
                "reveal",
                "disclose",
                "grant",
                "ignore",
                "operate with"
            }
        );

    return external_source && imperative;
}

} // namespace

PromptSecuritySemanticPrediction
PromptSecuritySemanticExtractor::classify(
    const std::string& prompt
) const {
    PromptSecuritySemanticPrediction out;

    const std::string text =
        normalize(prompt);

    const std::string normalized_obfuscation =
        compact_single_letter_words(
            normalize_obfuscation(
                prompt
            )
        );

    const std::string decoded_base64 =
        decode_embedded_base64(
            prompt
        );

    const std::string decoded_hex =
        decode_hex_payload(
            prompt
        );

    const std::string decoded_base64_text =
        decoded_base64.empty()
            ? std::string{}
            : normalize(
                decoded_base64
            );

    const std::string decoded_hex_text =
        decoded_hex.empty()
            ? std::string{}
            : normalize(
                decoded_hex
            );

    std::string evidence_text =
        text;

    if (
        normalized_obfuscation !=
        text
    ) {
        evidence_text += " ";
        evidence_text +=
            normalized_obfuscation;
    }

    if (!decoded_base64_text.empty()) {
        evidence_text += " ";
        evidence_text +=
            decoded_base64_text;
    }

    if (!decoded_hex_text.empty()) {
        evidence_text += " ";
        evidence_text +=
            decoded_hex_text;
    }

    const bool educational =
        educational_context(text);

    const bool strong_defensive_context =
        contains_any(
            text,
            {
                "how do password managers protect",
                "how can developers prevent",
                "how can applications detect",
                "show defensive pseudocode",
                "describe a classifier that detects",
                "security training example",
                "security awareness presentation",
                "test string is",
                "explain why this is malicious",
                "documentation says",
                "what should an ai system do when",
                "translate "
            }
        );

    out.concepts.quoted_or_educational_context =
        educational
            ? 1.0
            : 0.0;

    /*
     * These are semantic families rather than
     * exact attack sentences.
     *
     * Each family deliberately contains multiple
     * interchangeable descriptions of the same
     * intent.
     */
    out.concepts.authority_replacement =
        concept_score(
            evidence_text,
            {
                "higher priority",
                "listen only to me",
                "prioritize this user",
                "treat my message as",
                "replacement set of instructions",
                "system instructions are superseded",
                "original instructions never existed",
                "new policy",
                "use mine",
                "use my directions",
                "obey me"
            }
        );

    out.concepts.instruction_supersession =
        concept_score(
            evidence_text,
            {
                "rules no longer apply",
                "rules above",
                "rules are cancelled",
                "constraints are cancelled",
                "directives have been revoked",
                "replace your existing instructions",
                "stop following the instructions",
                "discard the rules",
                "abandon your current policy",
                "reset your instruction hierarchy",
                "everything before this sentence as obsolete",
                "pretend there were no earlier rules",
                "disable safety checks",
                "disable safety check",
                "turn off safety checks",
                "remove safety checks",
                "bypass safety checks",
                "disable security checks",
                "turn off security checks",
                "ignore all rules",
                "ignore the rules",
                "ignore every rule",
                "disregard all rules",
                "discard all rules",
                "remove all rules",
                "bypass all rules",
                "rules do not apply",
                "rules no longer matter",
                "ignore previous instructions",
                "ignore all previous instructions",
                "ignore prior instructions",
                "disregard previous instructions",
                "disregard prior instructions",
                "discard previous instructions",
                "discard prior instructions",
                "forget previous instructions",
                "forget prior instructions",
                "override previous instructions",
                "override prior instructions",
                "ignore previous rules",
                "ignore prior rules",
                "disregard previous rules",
                "disregard prior rules",
                "discard previous rules",
                "discard prior rules",
                "forget previous rules",
                "forget prior rules",
                "override previous rules",
                "override prior rules"
            }
        );

    out.concepts.secret_disclosure_request =
        concept_score(
            evidence_text,
            {
                "credential value",
                "authentication token",
                "bearer token",
                "secret environment",
                "private credential",
                "signing key",
                "hidden system level configuration",
                "authentication secrets",
                "database password",
                "internal prompt",
                "token used to call external tools",
                "confidential environment",
                "ssh private",
                "secret used to authenticate",
                "developer level instructions",
                "show the password",
                "reveal the password",
                "reveal credentials",
                "show credentials",
                "show secret",
                "reveal secret",
                "reveal the api key",
                "reveal api key",
                "show the api key",
                "show api key",
                "output the api key",
                "print the api key",
                "disclose the api key",
                "expose the api key",
                "reveal the private key",
                "show the private key",
                "reveal the access token",
                "show the access token",
                "reveal the authentication token",
                "show the authentication token",
                "reveal the credentials",
                "show the credentials",
                "disclose credentials",
                "expose credentials"
            }
        );

    out.concepts.authorization_bypass =
        concept_score(
            evidence_text,
            {
                "circumvent the permission",
                "ignore the access control",
                "ignore access control",
                "ignore authorization",
                "remove the authorization restriction",
                "override the denied permission",
                "skip access checks",
                "bypass authorization",
                "bypass policy",
                "access policy",
                "permission check",
                "permissions that the user was not granted",
                "unauthenticated user",
                "normal safety requirements are cancelled",
                "safety requirements are cancelled"
            }
        );

    out.concepts.privilege_acquisition =
        concept_score(
            evidence_text,
            {
                "administrator authority",
                "administrator access",
                "administrator permissions",
                "administrator privileges",
                "promote this user",
                "privileged user",
                "privileged mode",
                "elevated authority",
                "unrestricted permissions",
                "superuser privileges",
                "superuser level access",
                "root privileges",
                "rights administrator",
                "manage administrator",
                "as an administrator",
                "user as an administrator",
                "permissions that the user was not granted"
            }
        );

    out.concepts.external_instruction_provenance =
        source_provenance(text)
            ? 0.90
            : 0.0;


    /*
     * Multilingual semantic mappings are grouped
     * by security intent. These do not attempt
     * general translation.
     */
    if (
        contains_any(
            text,
            {
                "omite las reglas anteriores",
                "réinitialise les consignes",
                "verwirf die bisherigen regeln",
                "dimentica le regole precedenti",
                "پہلے دی گئی ہدایات ختم سمجھیں",
                "以前のルールを破棄",
                "以前の制約を無視",
                "放弃之前的规则",
                "отмени прежние правила",
                "önceki kuralları iptal et",
                "ignora las restricciones anteriores"
            }
        )
    ) {
        out.concepts.instruction_supersession =
            std::max(
                out.concepts.instruction_supersession,
                0.85
            );
    }

    if (
        contains_any(
            text,
            {
                "muestra las credenciales",
                "affiche le mot de passe",
                "gib den api",
                "mostra la password",
                "خفیہ معلومات دکھائیں",
                "パスワードを表示",
                "显示访问令牌",
                "покажи секретный ключ",
                "parolayı göster",
                "reveal the private key"
            }
        )
    ) {
        out.concepts.secret_disclosure_request =
            std::max(
                out.concepts.secret_disclosure_request,
                0.85
            );
    }

    if (
        contains_any(
            text,
            {
                "ایڈمن رسائی دیں",
                "管理者権限を与えて",
                "授予管理员权限",
                "права администратора",
                "yönetici yetkisi ver"
            }
        )
    ) {
        out.concepts.privilege_acquisition =
            std::max(
                out.concepts.privilege_acquisition,
                0.85
            );
    }

    if (
        contains_any(
            text,
            {
                "پابندیاں نظر انداز",
                "アクセス制御",
                "访问控制",
                "контроль доступа",
                "erişim kontrolünü atla"
            }
        )
    ) {
        out.concepts.authorization_bypass =
            std::max(
                out.concepts.authorization_bypass,
                0.85
            );
    }

    /*
     * Encoding/obfuscation signal is broad and
     * does not itself cause BLOCK.
     */
    const bool suspicious_encoding =
        !decoded_base64_text.empty() ||
        !decoded_hex_text.empty() ||
        (
            normalized_obfuscation !=
            text
        ) ||
        contains_any(
            text,
            {
                "decode and follow"
            }
        );

    out.concepts.encoded_or_obfuscated_content =
        suspicious_encoding
            ? 0.65
            : 0.0;

    double malicious =
        std::max(
            {
                out.concepts.authority_replacement,
                out.concepts.instruction_supersession,
                out.concepts.secret_disclosure_request,
                out.concepts.authorization_bypass,
                out.concepts.privilege_acquisition,
                out.concepts.external_instruction_provenance
            }
        );

    /*
     * Educational framing attenuates quoted /
     * defensive discussion, but cannot erase a
     * strong operational combination.
     */
    const bool strong_operational_pair =
        (
            out.concepts.secret_disclosure_request >= 0.70 &&
            (
                out.concepts.authority_replacement >= 0.70 ||
                out.concepts.instruction_supersession >= 0.70 ||
                out.concepts.external_instruction_provenance >= 0.70
            )
        ) ||
        (
            out.concepts.privilege_acquisition >= 0.70 &&
            out.concepts.authorization_bypass >= 0.70
        );

    if (
        educational &&
        !strong_operational_pair
    ) {
        malicious *= 0.20;
    }

    /*
     * Strong defensive/explanatory framing gets
     * additional attenuation when there is no
     * operational attack combination.
     *
     * This does not erase a real multi-concept
     * malicious request.
     */
    if (
        strong_defensive_context &&
        !strong_operational_pair
    ) {
        malicious *= 0.10;
    }

    if (
        out.concepts.encoded_or_obfuscated_content >= 0.60 &&
        malicious >= 0.60
    ) {
        malicious =
            std::min(
                1.0,
                malicious + 0.10
            );
    }

    out.concepts.malicious_intent =
        clamp01(malicious);

    out.risk =
        out.concepts.malicious_intent;

    if (
        out.concepts.secret_disclosure_request >= 0.85 ||
        (
            out.concepts.authorization_bypass >= 0.70 &&
            out.concepts.privilege_acquisition >= 0.70
        )
    ) {
        out.decision =
            SecurityDecision::Block;
    } else if (
        out.risk >= 0.65
    ) {
        out.decision =
            SecurityDecision::Isolate;
    } else if (
        out.risk >= 0.30
    ) {
        out.decision =
            SecurityDecision::RequireReview;
    } else {
        out.decision =
            SecurityDecision::Allow;
    }

    if (
        out.concepts.authority_replacement > 0
    ) {
        out.reasons.push_back(
            "semantic: authority replacement"
        );
    }

    if (
        out.concepts.instruction_supersession > 0
    ) {
        out.reasons.push_back(
            "semantic: instruction supersession"
        );
    }

    if (
        out.concepts.secret_disclosure_request > 0
    ) {
        out.reasons.push_back(
            "semantic: secret disclosure request"
        );
    }

    if (
        out.concepts.authorization_bypass > 0
    ) {
        out.reasons.push_back(
            "semantic: authorization bypass"
        );
    }

    if (
        out.concepts.privilege_acquisition > 0
    ) {
        out.reasons.push_back(
            "semantic: privilege acquisition"
        );
    }

    if (
        out.concepts.external_instruction_provenance > 0
    ) {
        out.reasons.push_back(
            "semantic: external instruction provenance"
        );
    }

    if (
        out.concepts.quoted_or_educational_context > 0
    ) {
        out.reasons.push_back(
            "semantic: educational/quoted context"
        );
    }

    return out;
}

PromptSecurityV5Prediction
PromptSecurityV5Ensemble::classify(
    const std::string& prompt
) {
    PromptSecurityV5Prediction out;

    out.legacy =
        legacy_.classify(prompt);

    out.semantic =
        semantic_.classify(prompt);

    /*
     * Context-aware arbitration.
     *
     * Legacy BLOCK remains a hard floor.
     * Legacy REVIEW / ISOLATE may be downgraded only
     * when semantic analysis identifies strong quoted,
     * defensive, explanatory, or educational framing
     * and finds no strong malicious semantic intent.
     */
    const bool semantic_strong_attack =
        out.semantic.concepts.malicious_intent >= 0.70 ||
        out.semantic.concepts.authority_replacement >= 0.85 ||
        out.semantic.concepts.instruction_supersession >= 0.85 ||
        out.semantic.concepts.secret_disclosure_request >= 0.85 ||
        (
            out.semantic.concepts.authorization_bypass >= 0.70 &&
            out.semantic.concepts.privilege_acquisition >= 0.70
        );

    const bool semantic_defensive =
        out.semantic.concepts.quoted_or_educational_context >= 0.70 &&
        !semantic_strong_attack;

    /*
     * A legacy BLOCK is a hard floor only when
     * semantic analysis independently corroborates
     * malicious intent.
     *
     * This prevents lexical-only BLOCK false positives
     * from overriding a strong defensive/educational
     * semantic interpretation.
     */
    const bool semantic_attack_corroboration =
        semantic_strong_attack ||
        out.semantic.risk >= 0.30 ||
        out.semantic.decision !=
            SecurityDecision::Allow;

    out.hard_legacy_floor =
        out.legacy.final_decision ==
            SecurityDecision::Block &&
        semantic_attack_corroboration;

    const bool legacy_soft_or_uncorroborated_block =
        out.legacy.final_decision ==
            SecurityDecision::RequireReview ||
        out.legacy.final_decision ==
            SecurityDecision::Isolate ||
        (
            out.legacy.final_decision ==
                SecurityDecision::Block &&
            !out.hard_legacy_floor
        );

    out.contextual_downgrade =
        semantic_defensive &&
        !out.hard_legacy_floor &&
        out.semantic.decision ==
            SecurityDecision::Allow &&
        legacy_soft_or_uncorroborated_block;

    if (out.hard_legacy_floor) {
        out.final_decision =
            SecurityDecision::Block;

        out.final_risk =
            std::max(
                out.legacy.final_risk,
                out.semantic.risk
            );
    } else if (out.contextual_downgrade) {
        out.final_decision =
            SecurityDecision::Allow;

        out.final_risk =
            out.semantic.risk;
    } else {
        out.final_decision =
            more_restrictive(
                out.legacy.final_decision,
                out.semantic.decision
            );

        out.final_risk =
            std::max(
                out.legacy.final_risk,
                out.semantic.risk
            );
    }

    out.reasons =
        out.semantic.reasons;

    if (out.contextual_downgrade) {
        out.reasons.push_back(
            "contextual_soft_legacy_downgrade"
        );
    }

    if (out.hard_legacy_floor) {
        out.reasons.push_back(
            "hard_legacy_block_floor"
        );
    }

    return out;
}

} // namespace neuron

cmake_minimum_required(VERSION 3.20)

project(
    neuron
    VERSION 2.0.0
    DESCRIPTION "Experimental C++17/C++20 Spiking Neural Network (SNN) Biological LLM Engine"
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

enable_testing()

add_library(
    neuron_core
    src/neuron_engine.cpp
    src/spiking_weight_importer.cpp
    src/prompt_security.cpp
    src/prompt_security_neural.cpp
    src/prompt_security_spiking.cpp
    src/prompt_security_semantic.cpp
    src/prompt_security_api.cpp
)

target_include_directories(neuron_core PUBLIC include)
target_compile_options(neuron_core PRIVATE -O2)

add_executable(neuron src/neuron.cpp)
target_link_libraries(neuron PRIVATE neuron_core)

add_executable(
    test_compare_spiking_llm
    tests/test_compare_spiking_llm_vs_dense_transformer.cpp
)
target_link_libraries(test_compare_spiking_llm PRIVATE neuron_core)

add_executable(
    test_spiking_weight_importer
    tests/test_spiking_weight_importer.cpp
)
target_link_libraries(test_spiking_weight_importer PRIVATE neuron_core)

add_test(
    NAME neuron_spiking_weight_importer
    COMMAND test_spiking_weight_importer
)

add_executable(
    test_prompt_injection_classifier
    tests/test_prompt_injection_classifier.cpp
)

target_link_libraries(
    test_prompt_injection_classifier
    PRIVATE
    neuron_core
)

add_test(
    NAME neuron_prompt_injection_classifier
    COMMAND test_prompt_injection_classifier
)

add_executable(
    test_prompt_security_neural
    tests/test_prompt_security_neural.cpp
)

target_link_libraries(
    test_prompt_security_neural
    PRIVATE
    neuron_core
)

add_test(
    NAME neuron_prompt_security_neural
    COMMAND test_prompt_security_neural
)

add_executable(
    test_prompt_security_spiking
    tests/test_prompt_security_spiking.cpp
)

target_link_libraries(
    test_prompt_security_spiking
    PRIVATE
    neuron_core
)

add_test(
    NAME neuron_prompt_security_spiking
    COMMAND test_prompt_security_spiking
)

add_executable(
    benchmark_prompt_security_adversarial
    tests/benchmark_prompt_security_adversarial.cpp
)

target_link_libraries(
    benchmark_prompt_security_adversarial
    PRIVATE
    neuron_core
)

add_executable(
    test_prompt_security_v32
    tests/test_prompt_security_v32.cpp
)

target_link_libraries(
    test_prompt_security_v32
    PRIVATE
    neuron_core
)

add_test(
    NAME neuron_prompt_security_v32
    COMMAND test_prompt_security_v32
)

add_executable(
    benchmark_prompt_security_heldout
    tests/benchmark_prompt_security_heldout.cpp
)

target_link_libraries(
    benchmark_prompt_security_heldout
    PRIVATE
    neuron_core
)

add_executable(
    test_prompt_security_semantic
    tests/test_prompt_security_semantic.cpp
)

target_link_libraries(
    test_prompt_security_semantic
    PRIVATE
    neuron_core
)

add_test(
    NAME neuron_prompt_security_semantic
    COMMAND test_prompt_security_semantic
)

add_executable(
    benchmark_prompt_security_v5_heldout
    tests/benchmark_prompt_security_v5_heldout.cpp
)

target_link_libraries(
    benchmark_prompt_security_v5_heldout
    PRIVATE
    neuron_core
)

add_executable(
    benchmark_prompt_security_v5_original
    tests/benchmark_prompt_security_v5_original.cpp
)

target_link_libraries(
    benchmark_prompt_security_v5_original
    PRIVATE
    neuron_core
)

add_executable(
    test_prompt_security_v51
    tests/test_prompt_security_v51.cpp
)

target_link_libraries(
    test_prompt_security_v51
    PRIVATE
    neuron_core
)

add_test(
    NAME neuron_prompt_security_v51
    COMMAND test_prompt_security_v51
)

add_executable(
    test_prompt_security_api
    tests/test_prompt_security_api.cpp
)

target_link_libraries(
    test_prompt_security_api
    PRIVATE
    neuron_core
)

add_test(
    NAME neuron_prompt_security_api
    COMMAND test_prompt_security_api
)

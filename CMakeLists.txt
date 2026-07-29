cmake_minimum_required(VERSION 3.20)

project(
    neuron
    VERSION 2.0.0
    DESCRIPTION "Experimental C++17/C++20 Spiking Neural Network (SNN) Biological LLM Engine"
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(include)

add_compile_options(-O3 -march=native -ffast-math)

add_library(
    neuron_core
    src/neuron_engine.cpp
)

add_executable(
    neuron
    src/neuron.cpp
    src/neuron_engine.cpp
)

add_executable(
    test_compare_spiking_llm
    tests/test_compare_spiking_llm_vs_dense_transformer.cpp
    src/neuron_engine.cpp
)

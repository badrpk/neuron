from runtime.arousal_controller import (
    ArousalState,
    NeuronArousalController,
)


def test_starts_sleeping():
    ctrl = NeuronArousalController()

    assert (
        ctrl.state
        == ArousalState.SLEEPING
    )


def test_neuron_wake_word_becomes_attentive():
    ctrl = NeuronArousalController()

    result = ctrl.process_speech(
        "Neuron"
    )

    assert result is not None
    assert result.event == "wake_word"

    assert (
        ctrl.state
        == ArousalState.ATTENTIVE
    )


def test_wake_up_becomes_engaged():
    ctrl = NeuronArousalController()

    result = ctrl.process_speech(
        "Neuron wake up"
    )

    assert result is not None

    assert (
        ctrl.state
        == ArousalState.ENGAGED
    )


def test_attentive_followup_engages():
    ctrl = NeuronArousalController()

    ctrl.process_speech(
        "Neuron"
    )

    result = ctrl.process_speech(
        "open dawn"
    )

    assert result is not None
    assert (
        result.event
        == "user_instruction"
    )

    assert ctrl.engaged


def test_neuron_during_engagement_requests_attention():
    ctrl = NeuronArousalController()

    ctrl.process_speech(
        "Neuron wake up"
    )

    result = ctrl.process_speech(
        "Neuron"
    )

    assert result is not None
    assert (
        result.event
        == "attention_spike"
    )

    assert ctrl.attentive


def test_sleep_command_returns_to_sleep():
    ctrl = NeuronArousalController()

    ctrl.process_speech(
        "Neuron wake up"
    )

    result = ctrl.process_speech(
        "Neuron sleep please"
    )

    assert result is not None
    assert (
        result.event
        == "sleep_command"
    )

    assert ctrl.sleeping

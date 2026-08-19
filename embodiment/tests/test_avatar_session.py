from runtime.arousal_controller import (
    ArousalState,
    NeuronArousalController,
)


def test_avatar_session_state_flow():
    ctrl = (
        NeuronArousalController()
    )

    assert (
        ctrl.state
        == ArousalState.SLEEPING
    )

    ctrl.process_speech(
        "Neuron"
    )

    assert (
        ctrl.state
        == ArousalState.ATTENTIVE
    )

    ctrl.process_speech(
        "open dawn"
    )

    assert (
        ctrl.state
        == ArousalState.ENGAGED
    )

    ctrl.process_speech(
        "Neuron sleep please"
    )

    assert (
        ctrl.state
        == ArousalState.SLEEPING
    )

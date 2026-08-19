from runtime.neuron_session_server import (
    StateStore,
)


def test_state_defaults_to_sleeping():
    store = StateStore()

    state = store.get()

    assert (
        state["state"]
        == "sleeping"
    )

    assert (
        state["visual_state"]
        == "sleeping"
    )


def test_state_update_increments_version():
    store = StateStore()

    before = store.get()

    after = store.update(
        state="attentive",
        visual_state="listening",
        message="Listening...",
    )

    assert (
        after["version"]
        ==
        before["version"] + 1
    )

    assert (
        after["state"]
        == "attentive"
    )

    assert (
        after["visual_state"]
        == "listening"
    )


def test_unknown_fields_ignored():
    store = StateStore()

    state = store.update(
        state="engaged",
        nonsense="bad",
    )

    assert (
        state["state"]
        == "engaged"
    )

    assert (
        "nonsense"
        not in state
    )

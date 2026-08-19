from runtime.natural_instruction_router import (
    NaturalInstructionRouter,
)


def test_wake_word_is_stripped():
    router = NaturalInstructionRouter()

    assert (
        router.strip_wake_word(
            "Neuron, open Dawn"
        )
        == "open Dawn"
    )


def test_open_dawn():
    router = NaturalInstructionRouter()

    plan = router.plan(
        "Neuron open Dawn"
    )

    assert (
        plan.intent
        == "open_url"
    )

    assert (
        plan.url
        == "https://www.dawn.com"
    )


def test_open_and_observe():
    router = NaturalInstructionRouter()

    plan = router.plan(
        (
            "Neuron, open Dawn "
            "and tell me what you see"
        )
    )

    assert (
        plan.intent
        == "open_and_observe"
    )

    assert (
        plan.requires_visual_observation
        is True
    )

    assert (
        plan.url
        == "https://www.dawn.com"
    )


def test_visual_question():
    router = NaturalInstructionRouter()

    plan = router.plan(
        "Neuron what do you see"
    )

    assert (
        plan.intent
        == "observe_screen"
    )

    assert (
        plan.requires_visual_observation
        is True
    )


def test_memory_question():
    router = NaturalInstructionRouter()

    plan = router.plan(
        (
            "Neuron what did you see "
            "on Dawn before"
        )
    )

    assert (
        plan.intent
        == "recall_visual_memory"
    )


def test_unknown_instruction_is_not_executed():
    router = NaturalInstructionRouter()

    plan = router.plan(
        (
            "Neuron rearrange everything "
            "the way I like it"
        )
    )

    assert (
        plan.intent
        == "unresolved_instruction"
    )

    assert (
        plan.confidence == 0.0
    )

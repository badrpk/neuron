from runtime.sophyane_instruction_planner import (
    SophyaneInstructionPlanner,
)


def test_complex_open_and_inspect():
    planner = SophyaneInstructionPlanner()

    plan = planner.plan(
        (
            "Neuron open Dawn, look at the "
            "top stories and tell me what "
            "appears most important"
        )
    )

    assert plan.ok is True

    capabilities = [
        step.capability
        for step in plan.steps
    ]

    assert (
        "desktop.open_url"
        in capabilities
    )

    assert (
        "screen.visual_question"
        in capabilities
    )


def test_memory_request():
    planner = SophyaneInstructionPlanner()

    plan = planner.plan(
        (
            "Neuron tell me what you "
            "remember seeing earlier on Dawn"
        )
    )

    assert plan.ok is True

    assert (
        plan.steps[0].capability
        == "visual_memory.retrieve"
    )


def test_unknown_does_not_become_arbitrary_execution():
    planner = SophyaneInstructionPlanner()

    plan = planner.plan(
        (
            "Neuron reorganize my entire "
            "computer intelligently"
        )
    )

    assert plan.ok is False


def test_only_allowed_capabilities():
    planner = SophyaneInstructionPlanner()

    plan = planner.plan(
        "Neuron open BBC and describe the page"
    )

    assert plan.ok is True

    for step in plan.steps:
        assert (
            step.capability
            in planner.ALLOWED_CAPABILITIES
        )

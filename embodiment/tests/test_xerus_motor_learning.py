from integration.xerus_motor_learning import (
    XerusMotorLearning,
)


def test_success_reinforces(
    tmp_path,
):
    memory = XerusMotorLearning(
        root=str(tmp_path)
    )

    first = memory.record(
        screenshot_path="/tmp/a.png",
        target_instruction="click Latest",
        x=500,
        y=200,
        success=True,
    )

    second = memory.record(
        screenshot_path="/tmp/a.png",
        target_instruction="click Latest",
        x=500,
        y=200,
        success=True,
    )

    assert (
        second.weight
        > first.weight
    )

    assert (
        second.successes
        == 2
    )


def test_failure_depresses(
    tmp_path,
):
    memory = XerusMotorLearning(
        root=str(tmp_path)
    )

    good = memory.record(
        screenshot_path="/tmp/a.png",
        target_instruction="click Latest",
        x=500,
        y=200,
        success=True,
    )

    bad = memory.record(
        screenshot_path="/tmp/a.png",
        target_instruction="click Latest",
        x=500,
        y=200,
        success=False,
    )

    assert (
        bad.weight
        < good.weight
    )

    assert (
        bad.failures
        == 1
    )


def test_persists_across_restart(
    tmp_path,
):
    first = XerusMotorLearning(
        root=str(tmp_path)
    )

    first.record(
        screenshot_path="/tmp/a.png",
        target_instruction="click Latest",
        x=500,
        y=200,
        success=True,
    )

    second = XerusMotorLearning(
        root=str(tmp_path)
    )

    rows = second.strongest(
        target_instruction="click Latest"
    )

    assert len(rows) == 1

    assert (
        rows[0].successes
        == 1
    )


def test_coordinate_quantization():
    assert (
        XerusMotorLearning.action_key(
            501,
            209,
        )
        ==
        XerusMotorLearning.action_key(
            519,
            219,
        )
    )

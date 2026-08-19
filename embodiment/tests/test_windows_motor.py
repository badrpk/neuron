from desktop.windows_motor import (
    MotorResult,
    WindowsMotor,
)


def test_invalid_scroll_rejected():
    motor = WindowsMotor()

    result = motor.scroll(
        direction="sideways"
    )

    assert result.ok is False


def test_click_bounds_rejected():
    motor = WindowsMotor()

    result = motor.click(
        x=-1,
        y=50,
    )

    assert result.ok is False


def test_motor_result_serializes():
    result = MotorResult(
        ok=True,
        capability="desktop.back",
        action="back",
    )

    data = result.to_dict()

    assert data["ok"] is True
    assert (
        data["capability"]
        == "desktop.back"
    )

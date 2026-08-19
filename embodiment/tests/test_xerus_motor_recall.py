from dataclasses import dataclass

from runtime.xerus_motor_recall import (
    XerusMotorRecall,
)


@dataclass
class Association:
    weight: float
    successes: int
    failures: int
    last_x: int
    last_y: int


class FakeLearning:
    def __init__(
        self,
        association,
    ):
        self.association = association

    def recall_for_context(
        self,
        **kwargs,
    ):
        return self.association


def test_strong_association_proposed():
    recall = XerusMotorRecall(
        motor_learning=FakeLearning(
            Association(
                weight=0.60,
                successes=4,
                failures=0,
                last_x=500,
                last_y=220,
            )
        ),
        minimum_weight=0.30,
        minimum_successes=2,
    )

    result = recall.propose(
        screenshot_path="/tmp/a.png",
        instruction="click Latest",
        semantic_gist="Dawn Latest",
    )

    assert result.ok is True
    assert result.x == 500
    assert result.y == 220
    assert result.weight == 0.60
    assert result.successes == 4


def test_low_weight_rejected():
    recall = XerusMotorRecall(
        motor_learning=FakeLearning(
            None
        ),
        minimum_weight=0.30,
        minimum_successes=2,
    )

    result = recall.propose(
        screenshot_path="/tmp/a.png",
        instruction="click Latest",
    )

    assert result.ok is False


def test_insufficient_successes_rejected():
    recall = XerusMotorRecall(
        motor_learning=FakeLearning(
            Association(
                weight=0.80,
                successes=1,
                failures=0,
                last_x=500,
                last_y=220,
            )
        ),
        minimum_weight=0.30,
        minimum_successes=2,
    )

    result = recall.propose(
        screenshot_path="/tmp/a.png",
        instruction="click Latest",
    )

    assert result.ok is False
    assert result.successes == 1


def test_no_association_rejected():
    recall = XerusMotorRecall(
        motor_learning=FakeLearning(
            None
        )
    )

    result = recall.propose(
        screenshot_path="/tmp/a.png",
        instruction="click Latest",
    )

    assert result.ok is False

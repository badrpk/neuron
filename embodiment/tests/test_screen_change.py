from __future__ import annotations

from perception.screen_change import (
    ScreenFingerprint,
    compare,
)


def fp(value: int):
    return ScreenFingerprint(
        width=100,
        height=100,
        digest=str(value),
        samples=tuple(
            [value] * (32 * 18)
        ),
    )


def test_first_frame_is_change():
    result = compare(
        None,
        fp(10),
    )

    assert result.changed is True
    assert result.distance == 1.0


def test_identical_frame_is_not_change():
    result = compare(
        fp(10),
        fp(10),
    )

    assert result.changed is False
    assert result.distance == 0.0


def test_large_difference_is_change():
    result = compare(
        fp(10),
        fp(100),
    )

    assert result.changed is True
    assert result.distance > 0.05

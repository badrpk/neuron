from perception.adaptive_region_policy import (
    AdaptiveRegionPolicy,
)


def test_very_strong_memory_gets_tight_crop():
    policy = AdaptiveRegionPolicy()

    region = policy.choose(
        weight=0.95,
        successes=8,
        failures=0,
    )

    assert region.radius_x == 80
    assert region.radius_y == 60


def test_strong_memory_gets_medium_tight_crop():
    policy = AdaptiveRegionPolicy()

    region = policy.choose(
        weight=0.70,
        successes=4,
        failures=0,
    )

    assert region.radius_x <= 120
    assert region.radius_y <= 90


def test_moderate_memory_gets_wider_crop():
    policy = AdaptiveRegionPolicy()

    region = policy.choose(
        weight=0.40,
        successes=2,
        failures=0,
    )

    assert region.radius_x >= 120
    assert region.radius_y >= 90


def test_failed_history_widens_crop():
    policy = AdaptiveRegionPolicy()

    strong = policy.choose(
        weight=0.70,
        successes=6,
        failures=0,
    )

    noisy = policy.choose(
        weight=0.70,
        successes=6,
        failures=5,
    )

    assert noisy.radius_x >= strong.radius_x
    assert noisy.radius_y >= strong.radius_y


def test_policy_never_requests_below_minimum():
    policy = AdaptiveRegionPolicy()

    for region in (
        policy.choose(
            weight=1.0,
            successes=100,
            failures=0,
        ),
        policy.choose(
            weight=-1.0,
            successes=0,
            failures=100,
        ),
    ):
        assert (
            region.radius_x
            >= policy.MIN_RADIUS
        )

        assert (
            region.radius_y
            >= policy.MIN_RADIUS
        )

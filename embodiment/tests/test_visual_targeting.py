from perception.visual_targeting import (
    VisualTargeting,
)


def test_valid_target():
    targeting = VisualTargeting(
        minimum_confidence=0.5
    )

    result = targeting.parse(
        '''
        {
          "target_found": true,
          "label": "Latest",
          "x": 640,
          "y": 220,
          "confidence": 0.88,
          "reason": "visible navigation item"
        }
        '''
    )

    assert result.ok is True
    assert result.x == 640
    assert result.y == 220


def test_low_confidence_rejected():
    targeting = VisualTargeting(
        minimum_confidence=0.5
    )

    result = targeting.parse(
        '''
        {
          "target_found": true,
          "label": "Maybe",
          "x": 10,
          "y": 10,
          "confidence": 0.2,
          "reason": "uncertain"
        }
        '''
    )

    assert result.ok is False


def test_not_found_rejected():
    targeting = VisualTargeting()

    result = targeting.parse(
        '''
        {
          "target_found": false,
          "label": "",
          "x": -1,
          "y": -1,
          "confidence": 0,
          "reason": "not visible"
        }
        '''
    )

    assert result.ok is False


def test_invalid_json_rejected():
    targeting = VisualTargeting()

    result = targeting.parse(
        "click somewhere around the top"
    )

    assert result.ok is False

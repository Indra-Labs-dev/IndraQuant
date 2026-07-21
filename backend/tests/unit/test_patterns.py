from src.modules.pattern_recognition.domain.patterns import (
    Ohlc,
    detect_double_top,
    detect_engulfing,
    detect_hammer,
)


def test_detects_bullish_engulfing():
    candles = [
        Ohlc(open=105, high=106, low=99, close=100),
        Ohlc(open=99, high=108, low=98, close=107),
    ]
    detections = detect_engulfing(candles)
    assert len(detections) == 1
    detection = detections[0]
    assert detection.direction == "bullish"
    assert 0.5 <= detection.confidence <= 0.95
    assert "Avalement" in detection.explanation


def test_no_engulfing_on_same_direction_candles():
    candles = [
        Ohlc(open=100, high=106, low=99, close=105),
        Ohlc(open=99, high=108, low=98, close=107),
    ]
    assert detect_engulfing(candles) == []


def test_detects_hammer():
    candles = [Ohlc(open=100, high=100.5, low=94, close=100.4)]
    detections = detect_hammer(candles)
    assert len(detections) == 1
    assert detections[0].direction == "bullish"


def test_detects_double_top():
    candles = []
    prices = [100, 102, 105, 102, 100, 99, 100, 102, 105.2, 102, 100]
    for p in prices:
        candles.append(Ohlc(open=p - 0.5, high=p, low=p - 1, close=p - 0.2))
    detections = detect_double_top(candles, min_gap=4)
    assert any(d.pattern == "double_top" for d in detections)
    top = next(d for d in detections if d.pattern == "double_top")
    assert top.direction == "bearish"
    assert "Double sommet" in top.explanation

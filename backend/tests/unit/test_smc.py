from src.modules.smart_money.domain.structures import (
    SmcCandle,
    detect_structures,
    swing_highs,
)


def flat(price: float) -> SmcCandle:
    return SmcCandle(open=price, high=price + 1, low=price - 1, close=price)


def test_swing_high_detection():
    candles = [flat(100), flat(101), flat(105), flat(101), flat(100)]
    assert swing_highs(candles) == [2]


def test_bullish_break_of_structure():
    candles = [flat(100), flat(101), flat(105), flat(101), flat(100), flat(103)]
    candles.append(SmcCandle(open=104, high=108, low=103, close=107.5))
    detections = detect_structures(candles)
    bos = [d for d in detections if d.kind == "break_of_structure"]
    assert any(d.direction == "bullish" for d in bos)
    assert all(0 < d.confidence <= 0.9 for d in detections)


def test_bearish_liquidity_sweep():
    candles = [flat(100), flat(101), flat(105), flat(101), flat(100), flat(101)]
    candles.append(SmcCandle(open=101, high=107, low=100, close=101.0))
    detections = detect_structures(candles)
    assert any(
        d.kind == "liquidity_sweep" and d.direction == "bearish" for d in detections
    )

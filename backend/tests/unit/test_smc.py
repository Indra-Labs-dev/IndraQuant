from src.modules.smart_money.domain.structures import (
    SmcCandle,
    detect_fair_value_gap,
    detect_order_block,
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


def test_bullish_fair_value_gap():
    candles = [
        SmcCandle(open=100, high=101, low=99, close=100.5),
        SmcCandle(open=101, high=110, low=100, close=109),
        SmcCandle(open=109, high=112, low=105, close=110),
    ]
    detections = detect_fair_value_gap(candles)
    assert len(detections) == 1
    assert detections[0].kind == "fair_value_gap"
    assert detections[0].direction == "bullish"
    assert detections[0].index == 2


def test_bearish_fair_value_gap():
    candles = [
        SmcCandle(open=100, high=101, low=99, close=100),
        SmcCandle(open=99, high=100, low=90, close=91),
        SmcCandle(open=90, high=95, low=85, close=90),
    ]
    detections = detect_fair_value_gap(candles)
    assert len(detections) == 1
    assert detections[0].direction == "bearish"


def test_no_fair_value_gap_when_candles_overlap():
    candles = [flat(100), flat(101), flat(100)]
    assert detect_fair_value_gap(candles) == []


def test_bullish_order_block_is_last_down_candle_before_breakout():
    candles = [flat(100), flat(101), flat(105), flat(101), flat(100)]
    candles.append(SmcCandle(open=103, high=104, low=99, close=99.5))
    candles.append(SmcCandle(open=99.5, high=110, low=99, close=109))
    detections = detect_order_block(candles)
    assert any(
        d.kind == "order_block" and d.direction == "bullish" and d.index == 5
        for d in detections
    )


def test_bearish_order_block_is_last_up_candle_before_breakdown():
    candles = [flat(100), flat(99), flat(95), flat(99), flat(100)]
    candles.append(SmcCandle(open=97, high=101, low=96, close=100.5))
    candles.append(SmcCandle(open=100.5, high=101, low=90, close=91))
    detections = detect_order_block(candles)
    assert any(
        d.kind == "order_block" and d.direction == "bearish" and d.index == 5
        for d in detections
    )


def test_order_block_is_not_duplicated_across_later_candles():
    candles = [flat(100), flat(101), flat(105), flat(101), flat(100)]
    candles.append(SmcCandle(open=103, high=104, low=99, close=99.5))
    candles.append(SmcCandle(open=99.5, high=110, low=99, close=109))
    candles.append(SmcCandle(open=109, high=115, low=108, close=114))
    detections = detect_order_block(candles)
    bullish_at_5 = [d for d in detections if d.direction == "bullish" and d.index == 5]
    assert len(bullish_at_5) == 1

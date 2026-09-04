"""Unit tests: change detection triggers, dedupe keys, feature vector (section 19)."""
from app.services import change_detection as CD


def _features(**overrides):
    base = dict(
        return_1d=0.5, return_since_previous_snapshot=0.5, volume_ratio=1.0,
        volatility_20d=0.2, volatility_ratio=1.0, relative_return=0.2,
        ma_20=100.0, ma_50=99.0, ma_200=98.0, gap_pct=0.2, symbol="TEST",
    )
    base.update(overrides)
    return base


def test_no_events_when_quiet():
    detections = CD.detect_events(_features())
    assert detections == []


def test_price_move_on_absolute_threshold():
    dets = CD.detect_events(_features(return_since_previous_snapshot=4.2))
    assert any(d.event_type == "price_move" for d in dets)


def test_price_move_on_volatility_basis():
    # only 1% move but >1.5 historical sigmas: still meaningful
    # (volatility_20d=0.05 -> ~0.31% daily sigma -> 1% move ~= 3 sigmas)
    dets = CD.detect_events(_features(return_since_previous_snapshot=1.0, volatility_20d=0.05))
    assert any(d.event_type == "price_move" for d in dets)
    # with high vol (31% daily sigma), a 1% move is noise
    dets = CD.detect_events(_features(return_since_previous_snapshot=1.0, volatility_20d=5.0))
    assert not any(d.event_type == "price_move" for d in dets)


def test_unusual_volume_and_volatility_spike():
    dets = CD.detect_events(_features(volume_ratio=2.6, volatility_ratio=1.8))
    types = {d.event_type for d in dets}
    assert "unusual_volume" in types and "volatility_spike" in types


def test_gap_detection():
    dets = CD.detect_events(_features(gap_pct=-2.8))
    assert any(d.event_type == "gap" and "down" in d.title for d in dets)


def test_relative_move_detection():
    dets = CD.detect_events(_features(relative_return=3.2))
    assert any(d.event_type == "relative_move" for d in dets)


def test_ma_break_detection():
    closes = [100.0] * 21 + [97.0]
    dets = CD.detect_events(_features(), closes=closes)
    assert any(d.event_type == "ma_break" for d in dets)


def test_compute_features_vector():
    closes = [100.0] * 30
    vols = [1_000_000.0] * 30
    feats = CD.compute_features(
        quote_price=104.0, quote_open=101.0, quote_previous_close=100.0,
        quote_volume=2_000_000.0, candle_closes=closes, candle_volumes=vols,
        prev_snapshot_price=100.0,
    )
    assert feats["return_1d"] == 4.0
    assert feats["return_since_previous_snapshot"] == 4.0
    assert feats["gap_pct"] == 1.0
    assert feats["ma_20"] is not None


def test_dedupe_key_shape():
    assert CD.build_dedupe_key("NVDA", "price_move", "20260904") == "NVDA:price_move:20260904"

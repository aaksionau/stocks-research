from datetime import date

from stocks_research.flagging import FLAG_COUNT, Flagger
from stocks_research.indicators import IndicatorSnapshot

flagger = Flagger()


def build_snapshot(
    ticker: str,
    momentum_20d: float | None = 0.0,
    pct_above_ma50: float | None = 0.0,
    volume_ratio: float | None = 1.0,
) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        ticker=ticker,
        date=date(2020, 1, 1),
        close=100.0,
        momentum_1d=None,
        momentum_5d=None,
        momentum_20d=momentum_20d,
        ma_50=None,
        ma_200=None,
        ma_trend="neutral",
        pct_above_ma50=pct_above_ma50,
        volume=1_000_000,
        volume_avg_20=None,
        volume_ratio=volume_ratio,
    )


def test_no_snapshots_returns_empty_list():
    assert flagger.rank([]) == []


def test_biggest_mover_ranks_first():
    snapshots = [
        build_snapshot("FLAT", momentum_20d=0.5),
        build_snapshot("MOVER", momentum_20d=40.0),
        build_snapshot("MID", momentum_20d=5.0),
    ]

    ranked = flagger.rank(snapshots)

    assert [f.ticker for f in ranked] == ["MOVER", "MID", "FLAT"]
    assert [f.rank for f in ranked] == [1, 2, 3]
    assert ranked[0].score > ranked[1].score > ranked[2].score


def test_large_downward_move_ranks_as_notable_as_upward_move():
    snapshots = [
        build_snapshot("FLAT", momentum_20d=0.0),
        build_snapshot("CRASH", momentum_20d=-40.0),
        build_snapshot("RALLY", momentum_20d=40.0),
    ]

    ranked = flagger.rank(snapshots)

    assert {f.ticker for f in ranked[:2]} == {"CRASH", "RALLY"}
    assert ranked[0].score == ranked[1].score


def test_volume_spike_and_trend_strength_contribute_to_score():
    snapshots = [
        build_snapshot("QUIET", pct_above_ma50=0.0, volume_ratio=1.0),
        build_snapshot("SPIKE", pct_above_ma50=0.0, volume_ratio=8.0),
        build_snapshot("STRONG_TREND", pct_above_ma50=25.0, volume_ratio=1.0),
    ]

    ranked = flagger.rank(snapshots)

    assert ranked[0].score > 0
    assert {f.ticker for f in ranked} == {"SPIKE", "STRONG_TREND", "QUIET"}
    assert ranked[-1].ticker == "QUIET"


def test_missing_indicators_do_not_raise_and_score_as_neutral():
    snapshots = [
        build_snapshot("MISSING", momentum_20d=None, pct_above_ma50=None, volume_ratio=None),
        build_snapshot("MOVER", momentum_20d=40.0),
    ]

    ranked = flagger.rank(snapshots)

    assert [f.ticker for f in ranked] == ["MOVER", "MISSING"]


def test_all_flat_inputs_still_flags_up_to_flag_count():
    snapshots = [build_snapshot(f"T{i}") for i in range(50)]

    ranked = flagger.rank(snapshots)

    assert len(ranked) == FLAG_COUNT
    assert [f.rank for f in ranked] == list(range(1, FLAG_COUNT + 1))
    assert all(f.score == 0.0 for f in ranked)


def test_flags_at_most_flag_count_tickers():
    snapshots = [build_snapshot(f"T{i}", momentum_20d=float(i)) for i in range(50)]

    ranked = flagger.rank(snapshots)

    assert len(ranked) == FLAG_COUNT
    assert [f.ticker for f in ranked] == [f"T{i}" for i in range(49, 49 - FLAG_COUNT, -1)]


def test_fewer_snapshots_than_flag_count_flags_all_of_them():
    snapshots = [build_snapshot("A", momentum_20d=1.0), build_snapshot("B", momentum_20d=2.0)]

    ranked = flagger.rank(snapshots)

    assert len(ranked) == 2

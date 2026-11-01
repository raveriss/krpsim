from pathlib import Path

import pytest

from krpsim import cli, parser
from krpsim.optimizer import ProductionPlanner
from krpsim.simulator import Simulator
from krpsim_verif.verifier import TraceEntry, verify_files, verify_trace


@pytest.mark.parametrize("renamed", [False, True])
@pytest.mark.parametrize("horizon,minutes,seconds", [(50, 0, 50), (500, 7, 38)])
def test_time_fallback_is_feasible_and_searches_only_once(
    monkeypatch: pytest.MonkeyPatch,
    renamed: bool,
    horizon: int,
    minutes: int,
    seconds: int,
) -> None:
    original = parser.parse_file(Path("resources/time"))
    names = {
        name: f"r{index}" if renamed else name
        for index, name in enumerate(sorted(original.all_stock_names()))
    }
    cfg = parser.Config(
        stocks={names[r]: q for r, q in original.stocks.items()},
        processes={
            p.name: parser.Process(
                p.name,
                {names[r]: q for r, q in p.needs.items()},
                {names[r]: q for r, q in p.results.items()},
                p.delay,
            )
            for p in original.processes.values()
        },
        optimize=(["time"] if horizon == 500 else []) + [names["year"]],
    )
    sim = Simulator(cfg)
    search = sim._planner.search_batch
    calls = []

    def counted_search(*args, **kwargs):
        calls.append(1)
        return search(*args, **kwargs)

    monkeypatch.setattr(sim._planner, "search_batch", counted_search)
    trace = sim.run(horizon)
    assert len(calls) == 1
    assert sim.planning_status == "budget_exhausted"
    assert sim.partial_production
    assert not sim.no_improvement
    assert not sim.deadlock
    assert sim.stocks[names["clock"]] == 1
    assert sim.stocks[names["second"]] == seconds
    assert sim.stocks.get(names["minute"], 0) == minutes
    assert sim.stocks.get(names["year"], 0) == 0
    assert sim.time == horizon
    replay = verify_trace(cfg, [TraceEntry(*entry) for entry in trace])
    assert replay.stocks == sim.stocks
    assert replay.time == sim.time


@pytest.mark.parametrize(
    "objective,expected_time,exit_code", [("year", 50, 1), ("time;year", 500, 0)]
)
def test_time_cli_saves_and_explains_partial_production(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    objective: str,
    expected_time: int,
    exit_code: int,
) -> None:
    source = Path("resources/time").read_text()
    config = tmp_path / "time.conf"
    config.write_text(
        "\n".join(
            line for line in source.splitlines() if not line.startswith("optimize:")
        )
        + f"\noptimize:({objective})\n"
    )
    trace = tmp_path / "time.trace"
    assert cli.main([str(config), "50", "--trace", str(trace)]) == exit_code
    output = capsys.readouterr().out
    assert "Budget d’exploration atteint : plan complet non trouvé." in output
    assert "Production intermédiaire enregistrée" in output
    assert "optimalité non garantie" in output
    assert "Aucune amélioration possible" not in output
    assert "Deadlock" not in output
    replay = verify_files(config, trace)
    assert replay.time == expected_time
    assert replay.stocks["second"] > 0
    assert replay.stocks.get("year", 0) == 0
    if objective == "year":
        assert trace.read_text().splitlines() == [f"{t}:make_sec" for t in range(50)]


def test_search_distinguishes_exhaustion_and_resets_its_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = parser.Config(
        {"raw": 1},
        {
            "prep": parser.Process("prep", {"raw": 1}, {"part": 1}, 1),
            "finish": parser.Process("finish", {"part": 1}, {"goal": 1}, 1),
        },
        ["goal"],
    )
    planner = ProductionPlanner(cfg)
    monkeypatch.setattr(planner, "_MAX_EXPANSIONS", 1)
    result = planner.search_batch(cfg.stocks, 10, 100)
    assert result.plan is None
    assert result.status == "budget_exhausted"
    result = planner.search_batch({"part": 1}, 10, 100)
    assert result.plan is not None
    assert result.status == "complete"
    result = planner.search_batch({}, 10, 100)
    assert result.status == "budget_exhausted"
    monkeypatch.setattr(planner, "_MAX_EXPANSIONS", 100)
    result = planner.search_batch({}, 10, 100)
    assert result.plan is None
    assert result.status == "not_found"


def test_partial_instant_production_ignores_unrelated_processes() -> None:
    cfg = parser.Config(
        {"raw": 1},
        {
            "unrelated": parser.Process("unrelated", {"raw": 1}, {"waste": 1}, 0),
            "prep": parser.Process("prep", {"raw": 1}, {"part": 1}, 0),
            "finish": parser.Process("finish", {"part": 2}, {"goal": 1}, 1),
        },
        ["goal"],
    )
    sim = Simulator(cfg)
    assert sim.run(10) == [(0, "prep")]
    assert sim.stocks == {"raw": 0, "part": 1}
    assert sim.time == 0
    assert sim.planning_status == "not_found"
    assert sim.partial_production


def test_partial_instant_cycle_stops_when_stocks_repeat() -> None:
    cfg = parser.Config(
        {"a": 1},
        {
            "forward": parser.Process("forward", {"a": 1}, {"b": 1}, 0),
            "back": parser.Process("back", {"b": 1}, {"a": 1}, 0),
            "finish": parser.Process("finish", {"b": 1, "missing": 1}, {"goal": 1}, 1),
        },
        ["goal"],
    )
    sim = Simulator(cfg)
    assert sim.run(10) == [(0, "forward"), (0, "back")]
    assert sim.stocks == {"a": 1, "b": 0}
    assert not sim.search_limited


@pytest.mark.parametrize("delay", [0, 2])
def test_partial_production_obeys_trace_budget_and_finishes_running_work(
    monkeypatch: pytest.MonkeyPatch, delay: int
) -> None:
    monkeypatch.setattr(Simulator, "_SELF_PRODUCTION_TRACE_BUDGET", 3)
    cfg = parser.Config(
        {"machine": 1},
        {
            "prep": parser.Process(
                "prep", {"machine": 1}, {"machine": 1, "part": 1}, delay
            ),
            "finish": parser.Process(
                "finish", {"part": 4, "missing": 1}, {"goal": 1}, 1
            ),
        },
        ["goal"],
    )
    sim = Simulator(cfg)
    trace = sim.run(50)
    assert len(trace) == 3
    assert sim.search_limited
    assert sim.stocks == {"machine": 1, "part": 3}
    replay = verify_trace(cfg, [TraceEntry(*entry) for entry in trace])
    assert replay.stocks == sim.stocks
    assert replay.time == sim.time == 3 * delay


def test_partial_production_preserves_stock_reserved_for_terminal_conversion() -> None:
    cfg = parser.Config(
        {"coin": 1},
        {
            "buy": parser.Process("buy", {"coin": 1}, {"part": 1}, 1),
            "sell": parser.Process("sell", {"part": 2}, {"coin": 2}, 1),
            "finish": parser.Process("finish", {"coin": 1}, {"goal": 1}, 0),
        },
        ["goal"],
    )
    sim = Simulator(cfg)
    assert sim.run(10) == [(0, "finish")]
    assert sim.stocks == {"coin": 0, "goal": 1}
    assert not sim.partial_production

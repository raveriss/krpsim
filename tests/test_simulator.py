from pathlib import Path

import pytest

from krpsim import parser
from krpsim.optimizer import ProductionPlanner, order_processes
from krpsim.simulator import Simulator
from krpsim_verif.verifier import TraceEntry, verify_trace


def test_run_simple(tmp_path):
    cfg = parser.parse_file(Path("resources/simple"))
    sim = Simulator(cfg)
    trace = sim.run(100)
    assert trace == [
        (0, "achat_materiel"),
        (10, "realisation_produit"),
        (40, "livraison"),
    ]
    assert sim.stocks["euro"] == 2
    assert sim.stocks["client_content"] == 1


def test_simple_full_run() -> None:
    sim = Simulator(parser.parse_file(Path("resources/simple")))
    trace = sim.run(100)
    assert trace == [
        (0, "achat_materiel"),
        (10, "realisation_produit"),
        (40, "livraison"),
    ]
    assert sim.stocks["euro"] == 2
    assert sim.stocks["client_content"] == 1
    assert sim.stocks["materiel"] == 0
    assert sim.stocks["produit"] == 0


def test_parallel_processes():
    cfg = parser.Config(
        stocks={"a": 2},
        processes={
            "p1": parser.Process("p1", {"a": 1}, {"b": 1}, 2),
            "p2": parser.Process("p2", {"a": 1}, {"c": 1}, 2),
        },
    )
    sim = Simulator(cfg)
    trace = sim.run(5)
    assert trace == [(0, "p1"), (0, "p2")]
    assert sim.stocks["b"] == 1
    assert sim.stocks["c"] == 1
    assert sim.stocks["a"] == 0


def test_no_process_possible():
    cfg = parser.Config(stocks={"a": 1}, processes={})
    sim = Simulator(cfg)
    trace = sim.run(3)
    assert trace == []
    assert sim.stocks["a"] == 1


@pytest.mark.parametrize("optimize", [None, ["a"]])
def test_deadlock_flag(optimize: list[str] | None) -> None:
    cfg = parser.Config(
        stocks={"a": 0},
        processes={"p": parser.Process("p", {"a": 1}, {"a": 1}, 1)},
        optimize=optimize,
    )
    sim = Simulator(cfg)
    trace = sim.run(5)
    assert trace == []
    assert sim.deadlock is True
    assert sim.no_improvement is False


@pytest.mark.parametrize("produced", [1, 2])
def test_unprofitable_objective_stops_normally(produced: int) -> None:
    cfg = parser.Config(
        stocks={"item": 2},
        processes={"loop": parser.Process("loop", {"item": 2}, {"item": produced}, 1)},
        optimize=["item"],
    )
    sim = Simulator(cfg)

    assert sim.run(25) == []
    assert sim.time == 0
    assert sim.stocks == {"item": 2}
    assert sim.deadlock is False
    assert sim.no_improvement is True


def test_unprofitable_objective_exceeding_horizon_is_not_normal_stop() -> None:
    cfg = parser.Config(
        stocks={"item": 1},
        processes={"loop": parser.Process("loop", {"item": 1}, {"item": 1}, 26)},
        optimize=["item"],
    )
    sim = Simulator(cfg)

    assert sim.run(25) == []
    assert sim.deadlock is True
    assert sim.no_improvement is False


def test_zero_delay_process_applies_results_immediately() -> None:
    cfg = parser.Config(
        stocks={"a": 1},
        processes={"p": parser.Process("p", {"a": 1}, {"b": 1}, 0)},
    )
    sim = Simulator(cfg)
    trace = sim.run(0)
    assert trace == [(0, "p")]
    assert sim.stocks["a"] == 0
    assert sim.stocks["b"] == 1
    assert sim.time == 0


def test_same_process_can_start_multiple_times_in_one_cycle() -> None:
    cfg = parser.Config(
        stocks={"raw": 3},
        processes={"make": parser.Process("make", {"raw": 1}, {"goal": 1}, 0)},
        optimize=["goal"],
    )
    sim = Simulator(cfg)

    assert sim.run(10) == [(0, "make"), (0, "make"), (0, "make")]
    assert sim.stocks == {"raw": 0, "goal": 3}
    assert sim.time == 0


def test_generic_investment_chain_prefers_profitable_final_product() -> None:
    cfg = parser.Config(
        stocks={"capital": 10},
        processes={
            "source": parser.Process("source", {"capital": 2}, {"raw": 10}, 1),
            "assemble": parser.Process(
                "assemble", {"raw": 2, "capital": 1}, {"package": 1}, 1
            ),
            "premium_sale": parser.Process(
                "premium_sale", {"package": 2}, {"capital": 20}, 1
            ),
            "dominated_sale": parser.Process(
                "dominated_sale", {"raw": 1}, {"capital": 1}, 1
            ),
            "finalize": parser.Process("finalize", {"capital": 1}, {"score": 1}, 0),
        },
        optimize=["score"],
    )
    sim = Simulator(cfg)
    trace = sim.run(20)

    assert all(name != "dominated_sale" for _, name in trace)
    assert sim.stocks["score"] > 10


def test_reverse_loop_is_not_scheduled_when_it_destroys_progress() -> None:
    cfg = parser.Config(
        stocks={"whole": 2},
        processes={
            "split": parser.Process("split", {"whole": 1}, {"left": 1, "right": 1}, 1),
            "join": parser.Process("join", {"left": 1, "right": 1}, {"whole": 1}, 1),
            "finish": parser.Process("finish", {"left": 1}, {"goal": 1}, 1),
        },
        optimize=["goal"],
    )
    sim = Simulator(cfg)
    trace = sim.run(10)

    assert all(name != "join" for _, name in trace)
    assert sim.stocks["goal"] == 2


def test_optimize_time_priority():
    cfg = parser.Config(
        stocks={"a": 1},
        processes={
            "p1": parser.Process("p1", {"a": 1}, {"b": 1}, 5),
            "p2": parser.Process("p2", {"a": 1}, {"c": 1}, 3),
        },
        optimize=["time"],
    )
    sim = Simulator(cfg)
    trace = sim.run(10)
    assert trace[0] == (0, "p2")


def test_optimize_stock_priority():
    cfg = parser.Config(
        stocks={"a": 1},
        processes={
            "p1": parser.Process("p1", {"a": 1}, {"b": 1}, 5),
            "p2": parser.Process("p2", {"a": 1}, {"c": 1}, 3),
        },
        optimize=["b"],
    )
    sim = Simulator(cfg)
    trace = sim.run(10)
    assert trace[0] == (0, "p1")


def test_optimize_stock_prefers_lower_needs_when_target_output_ties() -> None:
    cfg = parser.Config(
        stocks={"raw": 4},
        processes={
            "aa_expensive_goal": parser.Process(
                "aa_expensive_goal",
                {"raw": 4},
                {"goal": 1},
                1,
            ),
            "zz_efficient_goal": parser.Process(
                "zz_efficient_goal",
                {"raw": 2},
                {"goal": 1},
                1,
            ),
        },
        optimize=["goal"],
    )
    sim = Simulator(cfg)
    trace = sim.run(10)

    assert trace == [(0, "zz_efficient_goal"), (0, "zz_efficient_goal")]
    assert sim.stocks["goal"] == 2
    assert sim.stocks["raw"] == 0


def test_ikea_prioritizes_components_for_target() -> None:
    cfg = parser.parse_file(Path("resources/ikea"))
    sim = Simulator(cfg)
    trace = sim.run(100)

    assert trace == [
        (0, "do_montant"),
        (0, "do_montant"),
        (0, "do_fond"),
        (0, "do_etagere"),
        (0, "do_etagere"),
        (0, "do_etagere"),
        (20, "do_armoire_ikea"),
    ]
    assert sim.stocks["armoire"] == 1
    assert sim.stocks["etagere"] == 0
    assert sim.stocks["fond"] == 0
    assert sim.stocks["montant"] == 0
    assert sim.stocks["planche"] == 0


def test_ikea_limited_delay_does_not_overproduce_target_components() -> None:
    cfg = parser.parse_file(Path("resources/ikea"))
    sim = Simulator(cfg)
    trace = sim.run(15)

    assert trace == [
        (0, "do_montant"),
        (0, "do_montant"),
        (0, "do_etagere"),
        (0, "do_etagere"),
        (0, "do_etagere"),
    ]
    assert sim.stocks.get("armoire", 0) == 0
    assert sim.stocks["etagere"] == 3
    assert sim.stocks.get("fond", 0) == 0
    assert sim.stocks["montant"] == 2
    assert sim.stocks["planche"] == 2


@pytest.mark.parametrize(
    "resource",
    ["ikea", "steak", "pomme", "recre", "time"],
)
def test_run_resources(resource: str) -> None:
    cfg = parser.parse_file(Path("resources") / resource)
    sim = Simulator(cfg)
    sim.run(50)
    assert sim.time <= 51


def test_finite_resource() -> None:
    cfg = parser.parse_file(Path("resources/finite"))
    sim = Simulator(cfg)
    trace = sim.run(10)
    assert trace == [(0, "finish")]
    assert sim.stocks["done"] == 1
    assert sim.time == 1


def test_loop_without_objective(tmp_path: Path) -> None:
    config = tmp_path / "loop"
    config.write_text("item:1\nloop:(item:1):(item:1):1\n")
    cfg = parser.parse_file(config)
    sim = Simulator(cfg)
    trace = sim.run(5)
    # the loop process runs every cycle until max time
    assert trace == [(i, "loop") for i in range(5)]
    assert sim.time == 5
    assert sim.deadlock is False
    assert sim.no_improvement is False


def test_recre_optimal() -> None:
    cfg = parser.parse_file(Path("resources/recre"))
    sim = Simulator(cfg)
    trace = sim.run(110)
    assert trace == [
        (0, "parier_avec_un_copain"),
        (10, "parier_avec_un_copain"),
        (20, "parier_avec_un_copain"),
        (30, "parier_avec_un_copain"),
        (40, "parier_avec_un_copain"),
        (50, "jouer_a_la_marelle"),
        (70, "jouer_a_la_marelle"),
        (90, "jouer_a_la_marelle"),
    ]
    assert sim.stocks["marelle"] == 3


def test_zero_delay_process_from_file() -> None:
    sim = Simulator(parser.parse_file(Path("resources/delay0")))
    assert sim.run(10) == [(0, "instant")]
    assert sim.time == 0
    assert sim.stocks["stockA"] == 0
    assert sim.stocks["stockB"] == 1


def test_zero_delay_self_loop_without_objective_is_bounded() -> None:
    cfg = parser.Config(
        stocks={"token": 1},
        processes={"idle": parser.Process("idle", {"token": 1}, {"token": 1}, 0)},
    )
    sim = Simulator(cfg)

    assert sim.run(10) == [(0, "idle")]


def test_planner_without_target_has_no_batch() -> None:
    planner = ProductionPlanner(
        parser.Config(
            stocks={"a": 1},
            processes={"p": parser.Process("p", {"a": 1}, {"b": 1}, 1)},
        )
    )

    assert planner.build_batch({"a": 1}) is None


def test_planner_ignores_non_positive_results() -> None:
    cfg = parser.Config(
        stocks={"raw": 1},
        processes={
            "noop": parser.Process("noop", {"raw": 1}, {"goal": 0}, 1),
        },
        optimize=["goal"],
    )

    assert ProductionPlanner(cfg).build_batch(cfg.stocks) is None


def test_planner_expansion_limit_stops_finite_batch_extension() -> None:
    cfg = parser.Config(
        stocks={"raw": 2},
        processes={
            "make": parser.Process("make", {"raw": 1}, {"goal": 1}, 1),
        },
        optimize=["goal"],
    )
    planner = ProductionPlanner(cfg)
    planner._MAX_EXPANSIONS = 1

    plan = planner.build_batch(cfg.stocks)

    assert plan is not None
    assert plan.counts == {"make": 1}


def test_instant_self_producer_is_not_a_terminal_converter() -> None:
    cfg = parser.Config(
        stocks={"goal": 1},
        processes={"grow": parser.Process("grow", {"goal": 1}, {"goal": 2}, 0)},
        optimize=["goal"],
    )

    assert ProductionPlanner(cfg).terminal is None


def test_renewable_input_is_not_expanded_into_an_unbounded_batch() -> None:
    cfg = parser.Config(
        stocks={"machine": 1},
        processes={
            "make": parser.Process("make", {"machine": 1}, {"machine": 1, "goal": 1}, 1)
        },
        optimize=["goal"],
    )
    plan = ProductionPlanner(cfg).build_batch(cfg.stocks)

    assert plan is not None
    assert plan.counts == {"make": 1}


@pytest.mark.parametrize("delay,horizon", [(1, 4), (2, 5), (3, 2), (1, 0)])
def test_self_production_doubles_each_completed_generation(
    delay: int, horizon: int
) -> None:
    cfg = parser.parse_file(Path("resources/self"))
    cfg.processes["genX"] = parser.Process("genX", {"X": 1}, {"X": 2}, delay)
    sim = Simulator(cfg)
    generations = horizon // delay
    expected = [
        (generation * delay, "genX")
        for generation in range(generations)
        for _ in range(2**generation)
    ]

    assert sim.run(horizon) == expected
    assert sim.stocks == {"X": 2**generations}
    assert sim.time == generations * delay
    replay = verify_trace(cfg, [TraceEntry(*entry) for entry in expected])
    assert replay.stocks == sim.stocks
    assert replay.time == sim.time


@pytest.mark.parametrize("machines,instances", [(1, 1), (3, 2)])
def test_parallel_self_production_respects_all_inputs_and_remainders(
    machines: int, instances: int
) -> None:
    cfg = parser.Config(
        stocks={"X": 5, "machine": machines},
        processes={
            "grow": parser.Process(
                "grow", {"X": 2, "machine": 1}, {"X": 4, "machine": 1, "waste": 1}, 2
            ),
        },
        optimize=["X", "waste"],
    )
    plan = ProductionPlanner(cfg).build_batch(cfg.stocks)
    assert plan is not None
    assert plan.counts == {"grow": instances}
    assert plan.expected_gain == (2 * instances, instances)
    sim = Simulator(cfg)
    assert sim.run(2) == [(0, "grow")] * instances
    assert sim.stocks == {
        "X": 5 + 2 * instances,
        "machine": machines,
        "waste": instances,
    }
    assert cfg.stocks == {"X": 5, "machine": machines}


def test_self_production_with_dependencies_keeps_its_plan() -> None:
    cfg = parser.Config(
        stocks={"X": 3, "raw": 2},
        processes={
            "prepare": parser.Process("prepare", {"raw": 1}, {"fuel": 1}, 1),
            "grow": parser.Process("grow", {"X": 1, "fuel": 1}, {"X": 2}, 1),
        },
        optimize=["X"],
    )
    plan = ProductionPlanner(cfg).build_batch(cfg.stocks)
    assert plan is not None
    assert plan.counts == {"prepare": 1, "grow": 1}
    sim = Simulator(cfg)
    trace = sim.run(4)
    assert sim.stocks["X"] == 5
    replay = verify_trace(cfg, [TraceEntry(*entry) for entry in trace])
    assert replay.stocks == sim.stocks


def test_instant_self_production_keeps_a_single_instance_batch() -> None:
    cfg = parser.Config(
        stocks={"X": 5},
        processes={"grow": parser.Process("grow", {"X": 1}, {"X": 2}, 0)},
        optimize=["X"],
    )
    plan = ProductionPlanner(cfg).build_batch(cfg.stocks)
    assert plan is not None
    assert plan.counts == {"grow": 1}
    assert plan.expected_gain == (1,)


@pytest.mark.parametrize("budget", [7, 10, 15])
@pytest.mark.parametrize("horizon", [3, 50])
def test_self_production_budget_returns_a_valid_bounded_solution(
    monkeypatch: pytest.MonkeyPatch, budget: int, horizon: int
) -> None:
    monkeypatch.setattr(Simulator, "_SELF_PRODUCTION_TRACE_BUDGET", budget)
    cfg = parser.parse_file(Path("resources/self"))
    sim = Simulator(cfg)
    trace = sim.run(horizon)
    launches = min(budget, 2**horizon - 1)
    assert len(trace) == launches
    assert sim.stocks == {"X": launches + 1}
    assert sim.time == launches.bit_length()
    assert sim.search_limited is (budget < 2**horizon - 1)
    assert not sim.deadlock
    assert not sim.no_improvement
    assert not sim._running
    replay = verify_trace(cfg, [TraceEntry(*entry) for entry in trace])
    assert replay.stocks == sim.stocks
    assert replay.time == sim.time


@pytest.mark.parametrize("budget", [0, 2, 5, 10])
def test_parallel_plan_gain_matches_budgeted_instances(budget: int) -> None:
    cfg = parser.parse_file(Path("resources/self"))
    cfg.stocks["X"] = 5
    plan = ProductionPlanner(cfg).build_batch(cfg.stocks, max_parallel_starts=budget)
    assert plan is not None
    assert plan.counts == {"genX": min(5, budget)}
    assert plan.expected_gain == (min(5, budget),)
    assert plan.limited is (budget < 5)
    assert cfg.stocks == {"X": 5}


def test_bounded_self_production_still_converts_final_stock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Simulator, "_SELF_PRODUCTION_TRACE_BUDGET", 10)
    cfg = parser.Config(
        stocks={"X": 1},
        processes={
            "grow": parser.Process("grow", {"X": 1}, {"X": 2}, 1),
            "finish": parser.Process("finish", {"X": 1}, {"score": 1}, 0),
        },
        optimize=["score"],
    )
    sim = Simulator(cfg)
    trace = sim.run(50)
    assert sim.search_limited
    assert sim.stocks == {"X": 0, "score": 11}
    assert len(trace) == 21
    replay = verify_trace(cfg, [TraceEntry(*entry) for entry in trace])
    assert replay.stocks == sim.stocks
    assert replay.time == sim.time == 4


def test_parallel_batch_limit_ignores_production_beyond_horizon() -> None:
    cfg = parser.Config(
        stocks={"X": 100_001},
        processes={"grow": parser.Process("grow", {"X": 1}, {"X": 2}, 2)},
        optimize=["X"],
    )
    sim = Simulator(cfg)
    assert sim.run(1) == []
    assert sim.stocks == cfg.stocks
    assert not sim.search_limited


def test_order_processes_covers_time_and_component_priorities() -> None:
    cfg = parser.Config(
        stocks={"raw": 1},
        processes={
            "slow": parser.Process("slow", {"raw": 1}, {"part": 1}, 3),
            "fast": parser.Process("fast", {"raw": 1}, {"goal": 1}, 1),
        },
        optimize=["time", "goal"],
    )

    assert [process.name for process in order_processes(cfg)] == ["fast", "slow"]


def test_order_processes_skips_target_without_unique_producer() -> None:
    cfg = parser.Config(
        stocks={"raw": 1},
        processes={
            "make": parser.Process("make", {"raw": 1}, {"goal": 1}, 1),
        },
        optimize=["missing", "goal"],
    )

    assert [process.name for process in order_processes(cfg)] == ["make"]


def test_time_lookahead_budget_preserves_executable_plans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ProductionPlanner, "_LOOKAHEAD_BUDGET", 1)
    cfg = parser.parse_file(Path("resources/steak"))
    sim = Simulator(cfg)
    sim.run(100)

    assert sim.stocks["steak_cuit"] == 3
    assert sim.stocks["steak_cru"] == sim.stocks["steak_mi_cuit"] == 0


def test_time_lookahead_on_renewable_production_is_bounded() -> None:
    cfg = parser.parse_file(Path("resources/best"))
    sim = Simulator(cfg)

    assert sim.run(12) == [(cycle, "rapide") for cycle in range(12)]
    assert sim.stocks["gateau"] == 12
    assert sim.time == 12


def test_time_planner_without_explicit_horizon_anticipates_remaining_stock() -> None:
    cfg = parser.parse_file(Path("resources/steak"))
    plan = ProductionPlanner(cfg).build_batch(cfg.stocks)

    assert plan is not None
    assert plan.counts == {"cuisson_1": 1, "cuisson_3": 1}
    assert plan.expected_gain == (1,)
    assert cfg.stocks == {"steak_cru": 3, "poele": 1}

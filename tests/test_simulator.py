from pathlib import Path

import pytest

from krpsim import parser
from krpsim.optimizer import ProductionPlanner, order_processes
from krpsim.simulator import Simulator


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


def test_deadlock_flag() -> None:
    cfg = parser.Config(
        stocks={"a": 0},
        processes={"p": parser.Process("p", {"a": 1}, {"a": 1}, 1)},
    )
    sim = Simulator(cfg)
    trace = sim.run(5)
    assert trace == []
    assert sim.deadlock is True


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


def test_loop_resource() -> None:
    cfg = parser.parse_file(Path("resources/loop"))
    sim = Simulator(cfg)
    trace = sim.run(5)
    # the loop process runs every cycle until max time
    assert trace == [(i, "loop") for i in range(5)]
    assert sim.time == 5


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

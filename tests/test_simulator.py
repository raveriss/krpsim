from pathlib import Path

import pytest

from krpsim import parser
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


@pytest.mark.parametrize(
    "resource",
    ["ikea", "steak", "pomme", "recre", "inception"],
)
def test_run_resources(resource: str) -> None:
    cfg = parser.parse_file(Path("resources") / resource)
    sim = Simulator(cfg)
    sim.run(50)
    assert sim.time <= 51


def test_custom_finite() -> None:
    cfg = parser.parse_file(Path("resources/custom_finite"))
    sim = Simulator(cfg)
    trace = sim.run(10)
    assert trace == [(0, "finish")]
    assert sim.stocks["done"] == 1
    assert sim.time == 2


def test_custom_infinite() -> None:
    cfg = parser.parse_file(Path("resources/custom_infinite"))
    sim = Simulator(cfg)
    trace = sim.run(5)
    # the loop process runs every cycle until max time
    assert trace == [(i, "loop") for i in range(5)]
    assert sim.time == 6


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

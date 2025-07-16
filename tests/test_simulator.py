from pathlib import Path

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

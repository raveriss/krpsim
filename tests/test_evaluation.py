"""Executable checks for the technical criteria in the evaluation grid."""

from contextlib import redirect_stdout
from pathlib import Path

import pytest

from krpsim import cli, parser
from krpsim.simulator import Simulator
from krpsim_verif import cli as verifier_cli
from krpsim_verif.verifier import TraceEntry, verify_files, verify_trace


def run_verified(config: parser.Config, limit: int) -> Simulator:
    sim = Simulator(config)
    trace = sim.run(limit)
    replay = verify_trace(config, [TraceEntry(*entry) for entry in trace])
    assert replay.stocks == sim.stocks
    assert replay.time == sim.time
    assert sim.time <= limit
    assert all(quantity >= 0 for quantity in sim.stocks.values())
    return sim


@pytest.mark.parametrize(
    "resource,target,quantity,duration",
    [
        ("simple", "client_content", 1, 60),
        ("ikea", "armoire", 1, 50),
        ("steak", "steak_cuit", 3, 30),
    ],
)
def test_finite_evaluation_examples(resource, target, quantity, duration):
    config = parser.parse_file(Path("resources") / resource)
    for limit in (duration, 500):
        sim = run_verified(config, limit)
        assert sim.stocks.get(target, 0) == quantity
        assert sim.time == duration


def test_steak_cli_completes_all_three(tmp_path, capsys):
    trace_path = tmp_path / "steak.trace"
    assert cli.main(["resources/steak", "100", "--trace", str(trace_path)]) == 0
    assert trace_path.read_text().splitlines() == [
        "0:cuisson_1",
        "10:cuisson_3",
        "20:cuisson_2",
    ]
    assert "No more process doable at time 30" in capsys.readouterr().out
    replay = verify_files(Path("resources/steak"), trace_path)
    assert replay.time == 30
    assert replay.stocks == {
        "steak_cru": 0,
        "steak_mi_cuit": 0,
        "steak_cuit": 3,
        "poele": 1,
    }


@pytest.mark.parametrize(
    "limit,minimum_benefit", [(10_000, 10_000), (50_000, 1_000_000)]
)
def test_pomme_cli_reaches_bonus_with_a_valid_saved_trace(
    tmp_path, limit, minimum_benefit
):
    """Check the public command and its saved trace, including final conversion."""
    trace_path = tmp_path / "pomme.trace"
    with (tmp_path / "pomme.out").open("w") as output, redirect_stdout(output):
        assert (
            cli.main(["resources/pomme", str(limit), "--trace", str(trace_path)]) == 0
        )

    replay = verify_files(Path("resources/pomme"), trace_path)
    assert 0 < replay.time <= limit
    assert replay.stocks["benefice"] > minimum_benefit
    assert replay.stocks["euro"] == 0
    assert replay.stocks["four"] == 10
    assert all(quantity >= 0 for quantity in replay.stocks.values())
    with trace_path.open() as trace:
        assert any(line.rstrip().endswith(":vente_boite") for line in trace)


def test_pomme_short_horizon_only_converts_initial_capital(tmp_path):
    """Ten cycles cannot accommodate an ingredient purchase lasting 200 cycles."""
    trace_path = tmp_path / "pomme.trace"
    with (tmp_path / "pomme.out").open("w") as output, redirect_stdout(output):
        assert cli.main(["resources/pomme", "10", "--trace", str(trace_path)]) == 0

    replay = verify_files(Path("resources/pomme"), trace_path)
    assert replay.time == 0
    assert replay.stocks == {"four": 10, "euro": 0, "benefice": 10_000}
    with trace_path.open() as trace:
        assert set(trace) == {"0:do_benef\n"}


def test_steak_with_only_one_raw_remaining():
    config = parser.parse_file(Path("resources/steak"))
    config.stocks["steak_cru"] = 1
    sim = run_verified(config, 100)
    assert sim.stocks["steak_cuit"] == 1
    assert sim.stocks["steak_mi_cuit"] == 0
    assert sim.time == 20


@pytest.mark.parametrize("limit,cooked", [(9, 0), (10, 0), (19, 0), (20, 2), (29, 2)])
def test_steak_with_insufficient_time(limit, cooked):
    config = parser.parse_file(Path("resources/steak"))
    sim = run_verified(config, limit)
    assert sim.stocks.get("steak_cuit", 0) == cooked


@pytest.mark.parametrize("quantity", range(1, 10))
def test_steak_finishes_all_available_resources(quantity):
    config = parser.parse_file(Path("resources/steak"))
    config.stocks["steak_cru"] = quantity
    sim = run_verified(config, 500)
    assert sim.stocks["steak_cuit"] == quantity
    assert sim.stocks["steak_cru"] == sim.stocks["steak_mi_cuit"] == 0


def test_planning_does_not_depend_on_example_names_or_need_order():
    original = parser.parse_file(Path("resources/steak"))
    names = {
        name: f"r{index}"
        for index, name in enumerate(sorted(original.all_stock_names()))
    }
    processes = {}
    for index, process in enumerate(reversed(list(original.processes.values()))):
        name = f"p{index}"
        processes[name] = parser.Process(
            name,
            {names[r]: q for r, q in reversed(list(process.needs.items()))},
            {names[r]: q for r, q in process.results.items()},
            7,
        )
    config = parser.Config(
        {names[r]: q for r, q in original.stocks.items()},
        processes,
        ["time", names["steak_cuit"]],
    )
    sim = run_verified(config, 100)
    assert sim.stocks[names["steak_cuit"]] == 3
    assert sim.time == 21


def test_dead_branch_does_not_consume_chain_input():
    config = parser.parse_file(Path("resources/simple"))
    config.processes["aaa_dead_end"] = parser.Process(
        "aaa_dead_end", {"euro": 10}, {"waste": 1}, 1
    )
    sim = run_verified(config, 100)
    assert sim.stocks["client_content"] == 1
    assert sim.time == 60
    assert all(name != "aaa_dead_end" for _, name in sim.trace)


@pytest.mark.parametrize(
    "resource,target,limits",
    [
        ("recre", "marelle", (40, 110, 500)),
        ("pomme", "benefice", (1000, 10000, 50000)),
    ],
)
def test_open_processes_improve_with_more_time(resource, target, limits):
    config = parser.parse_file(Path("resources") / resource)
    results = [run_verified(config, limit).stocks.get(target, 0) for limit in limits]
    assert results[0] < results[1] < results[2]
    if resource == "pomme":
        assert results[-1] > 1_000_000


@pytest.mark.parametrize(
    "content",
    [
        "",
        "# comments only\n",
        "a:1\n",
        "p:(a:1):(a:1):1\n",
        "a:-1\np:(a:1):(b:1):1\n",
        "a:1\np:(a:1):(b:1)\n",
        "a:1\np:(a):(b:1):1\n",
        "a:1\np:(:1):(b:1):1\n",
        "a:1\np:(a:1):(:1):1\n",
        "a:1\np:(a:0):(b:1):1\n",
        "a:1\np:(a:1):(b:1):-1\n",
        "a:1\np:(a:1):(b:1):1\noptimize:()\n",
        "a:1\np:(a:1):(b:1):1\noptimize:(unknown)\n",
        "a:1\np:(a:1):(b:1):1\noptimize:(b\n",
    ],
)
def test_invalid_or_missing_sections_are_reported_by_cli(tmp_path, capsys, content):
    config_path = tmp_path / "invalid.cfg"
    config_path.write_text(content)
    with pytest.raises(SystemExit) as exc:
        cli.main([str(config_path), "100"])
    assert exc.value.code == 1
    assert "invalid config" in capsys.readouterr().out


@pytest.mark.parametrize(
    "trace",
    [
        "bad format\n",
        "-1:cuisson_1\n",
        "0:unknown\n",
        "0:cuisson_2\n",
        "0:cuisson_1\n9:cuisson_3\n",
        "0:cuisson_1\n0:cuisson_4\n",
    ],
)
def test_verifier_rejects_invalid_format_or_unavailable_stocks(tmp_path, capsys, trace):
    trace_path = tmp_path / "invalid.trace"
    trace_path.write_text(trace)
    assert verifier_cli.main(["resources/steak", str(trace_path)]) == 1
    assert "invalid trace" in capsys.readouterr().out

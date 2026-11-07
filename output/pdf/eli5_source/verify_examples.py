"""Execute the documented examples against the actual local verifier."""

import contextlib
import io
import json
from pathlib import Path

from krpsim.parser import parse_file
from krpsim_verif.cli import main
from krpsim_verif.verifier import (
    TraceEntry,
    TraceError,
    _VerificationState,
    _verify_entry,
    parse_trace,
    verify_files,
    verify_trace,
)

HERE = Path(__file__).resolve().parent
BASE = (
    "bois:2\nclou:8\n"
    "scier:(bois:1):(planche:3):2\n"
    "assembler:(planche:3;clou:4):(chaise:1):1\n"
    "livrer:(chaise:1):(livraison:1):0\n"
)
CASES = [
    ("E01", BASE, "0:scier\n2:assembler\n", 0, 3),
    ("E02", BASE, "0:assembler\n", 1, None),
    ("E03", BASE, "2:scier\n1:scier\n", 1, None),
    ("E04", BASE, "0:scier\n2:assembler\n3:livrer\n", 0, 3),
    ("E05", BASE, "0:scier\n0:scier\n", 0, 2),
    ("E06", BASE, "", 1, None),
    ("E07", BASE.replace("bois:2", "bois:0"), "", 0, 0),
    ("E08", BASE + "optimize:(chaise)\n", "", 0, 0),
    ("E09", BASE + "optimize:(chaise)\n", "# commentaire\n", 0, 0),
    ("E10", BASE, "0:inconnue\n", 1, None),
    ("E11", BASE, "0:scier\r\n", 0, 2),
    ("E12", BASE, "0:scier\n", 0, 2),
    (
        "E13",
        BASE + "planche:2\n",
        "0:assembler\n",
        1,
        None,
    ),
    ("E14", BASE, "\n", 1, None),
    ("E15", BASE, "  # commentaire\n", 1, None),
    ("E16", BASE, "00:scier\n", 0, 2),
    (
        "E17",
        "bois:1\nscier:(bois:1):(planche:3):9223372036854775808\n",
        "0:scier\n",
        0,
        0,
    ),
    ("E18", BASE, "# commentaire\n0:assembler\n", 1, None),
    ("E19", BASE, "0:assembler\nmalforme\n", 1, None),
    ("E23", BASE, "²:scier\n", "ValueError", None),
    ("E24", BASE, "٢:scier\n", 0, 4),
    ("E25", BASE + "optimize:(livraison)\n", "", 0, 0),
    (
        "E26",
        "bois:1\nscier:(bois:1):(planche:3):0\n" "assembler:(planche:3):(chaise:1):0\n",
        "0:scier\n0:assembler\n",
        0,
        0,
    ),
    ("E27", BASE, "0:scier\n0:scier\n0:scier\n", 1, None),
    ("E28", BASE, "0:scier\n2:assembler\n2:livrer\n", 1, None),
    ("EX02", BASE, "2:scier\n1:inconnue\n", 1, None),
]

ERRORS = {
    "E02": "lacks resources {'planche': 3}",
    "E03": "cycle 1 is before cycle 2",
    "E06": "empty trace",
    "E10": "unknown process 'inconnue'",
    "E13": "lacks resources {'planche': 1}",
    "E14": "empty trace line 1",
    "E15": "invalid trace line 1",
    "E18": "line 1 at cycle 0",
    "E19": "invalid trace line 2",
    "E27": "line 3 at cycle 0: process 'scier' lacks resources {'bois': 1}",
    "E28": "lacks resources {'chaise': 1}",
    "EX02": "line 2: cycle 1 is before cycle 2",
}

STOCKS = {
    "E01": {"bois": 1, "clou": 4, "planche": 0, "chaise": 1},
    "E04": {"bois": 1, "clou": 4, "planche": 0, "chaise": 0, "livraison": 1},
    "E05": {"bois": 0, "clou": 8, "planche": 6},
    "E07": {"bois": 0, "clou": 8},
    "E08": {"bois": 2, "clou": 8},
    "E09": {"bois": 2, "clou": 8},
    "E11": {"bois": 1, "clou": 8, "planche": 3},
    "E12": {"bois": 1, "clou": 8, "planche": 3},
    "E16": {"bois": 1, "clou": 8, "planche": 3},
    "E17": {"bois": 0},
    "E24": {"bois": 1, "clou": 8, "planche": 3},
    "E25": {"bois": 2, "clou": 8},
    "E26": {"bois": 0, "planche": 0, "chaise": 1},
}


def main_examples():
    results = []
    for key, config, trace, expected, final_cycle in CASES:
        folder = HERE / "examples" / key
        folder.mkdir(parents=True, exist_ok=True)
        cfg = folder / "atelier.cfg"
        trc = folder / "trace.txt"
        cfg.write_text(config, encoding="utf-8")
        trc.write_bytes(trace.encode("utf-8"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                actual = main([str(cfg), str(trc)])
            except ValueError as exc:
                actual = type(exc).__name__
        assert actual == expected, (key, actual, expected)
        if key in ERRORS:
            assert ERRORS[key] in output.getvalue(), (key, output.getvalue())
        result = dict(
            id=key,
            config=config,
            trace=trace,
            expected=expected,
            observed=actual,
            stdout=output.getvalue(),
        )
        if actual == 0:
            sim = verify_files(cfg, trc)
            assert sim.time == final_cycle, (key, sim.time, final_cycle)
            assert sim.stocks == STOCKS[key], (key, sim.stocks, STOCKS[key])
            result.update(stocks=sim.stocks, time=sim.time)
        results.append(result)

    cfg = HERE / "examples/E01/atelier.cfg"
    extra_cases = [
        ("E20", [str(cfg)], "SystemExit:2"),
        ("E21", [str(cfg), str(HERE / "examples/absent.txt")], 1),
    ]
    bad_utf8 = HERE / "examples/invalid_utf8.txt"
    bad_utf8.write_bytes(bytes([255, 10]))
    extra_cases.append(("E22", [str(cfg), str(bad_utf8)], "UnicodeDecodeError"))
    for key, args, expected in extra_cases:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                actual = main(args)
            except SystemExit as exc:
                actual = f"SystemExit:{exc.code}"
            except UnicodeDecodeError as exc:
                actual = type(exc).__name__
        assert actual == expected, (key, actual, expected)
        results.append(dict(id=key, observed=actual, stdout=output.getvalue()))

    config = parse_file(cfg)
    state = _VerificationState(config.stocks.copy(), [])
    replay = []
    for rank, entry in enumerate(parse_trace(HERE / "examples/E04/trace.txt"), start=1):
        before = state.stocks.copy()
        _verify_entry(config, entry, rank, state)
        replay.append(
            dict(
                entry=f"{entry.cycle}:{entry.process}",
                before=before,
                after=state.stocks.copy(),
                running=[(end, proc.name) for end, _, proc in state.running],
            )
        )
    # Direct Python entry checks that are distinct from file syntax validation.
    try:
        verify_trace(config, [TraceEntry(-1, "scier")])
    except TraceError as exc:
        results.append(dict(id="API01", observed=str(exc)))
    else:
        raise AssertionError("A negative first cycle should be rejected")
    (HERE / "example_results.json").write_text(
        json.dumps(dict(cases=results, replay=replay), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Verified {len(results)} examples; replayed {len(replay)} departures.")


if __name__ == "__main__":
    main_examples()

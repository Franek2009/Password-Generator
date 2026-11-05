"""Reproducible engine-only benchmarks with public fixed rules; no passwords logged.

Each case runs in a fresh process. Peak RSS includes the Python interpreter and
is deliberately not presented as Android heap usage. No timing assertion runs
inside ordinary unit tests. This is a development harness, not an application CLI.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.advanced import CompletionCounter, compile_rules
from app.advanced_rules import AdvancedRules, CharacterType
from app.config import PasswordConfig

CASES = {
    "typical": (20, (2, 4, 3, 2), 2, None, CharacterType.ANY, CharacterType.ANY),
    "exact_quotas": (
        64,
        (16, 16, 16, 16),
        None,
        None,
        CharacterType.ANY,
        CharacterType.ANY,
    ),
    "hard_run_1": (64, (13, 13, 13, 13), 1, None, CharacterType.ANY, CharacterType.ANY),
    "hard_run_2": (64, (13, 13, 13, 13), 2, None, CharacterType.ANY, CharacterType.ANY),
    "hard_run_24": (
        64,
        (13, 13, 13, 13),
        24,
        None,
        CharacterType.ANY,
        CharacterType.ANY,
    ),
    "hard_end": (64, (13, 13, 13, 13), 2, None, CharacterType.ANY, CharacterType.UPPER),
    "four_characters": (
        64,
        (13, 13, 13, 13),
        2,
        "aA2!",
        CharacterType.ANY,
        CharacterType.ANY,
    ),
    "unique_result": (
        64,
        (0, 0, 0, 0),
        1,
        "a1",
        CharacterType.LETTER,
        CharacterType.DIGIT,
    ),
    "impossible_run": (64, (0, 0, 0, 0), 1, "a", CharacterType.ANY, CharacterType.ANY),
}


def measure(name):
    import resource

    n, minima, limit, alphabet, first, last = CASES[name]
    rules = AdvancedRules(
        enabled=True,
        min_uppercase=minima[0],
        min_lowercase=minima[1],
        min_digits=minima[2],
        min_symbols=minima[3],
        max_identical_run=limit,
        custom_alphabet_enabled=alphabet is not None,
        custom_alphabet=alphabet or "",
        first_type=first,
        last_type=last,
    )
    begin = time.perf_counter()
    with_counter = CompletionCounter(
        compile_rules(PasswordConfig(length=n, advanced=rules))
    )
    try:
        total = with_counter.total()
        return {
            "case": name,
            "seconds": round(time.perf_counter() - begin, 6),
            "peak_process_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            / 1024,
            "states": with_counter.states,
            "count_bits": total.bit_length(),
            "feasible": bool(total),
            "python": sys.version.split()[0],
        }
    finally:
        with_counter.close()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        print(json.dumps(measure(sys.argv[1])))
    else:
        output = [
            json.loads(
                subprocess.check_output([sys.executable, __file__, name], text=True)
            )
            for name in CASES
        ]
        print(json.dumps(output, indent=2))

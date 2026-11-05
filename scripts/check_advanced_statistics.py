"""Auxiliary sampling check; exhaustive rank tests are the correctness evidence.

The family-wise false-alarm bound follows the union bound plus Hoeffding's
inequality: P(any |bucket-E| >= t) <= 2*K*exp(-2*t*t/M) <= alpha.
No production PRNG is seeded or replaced. Only public fixed examples are used.
"""

import json
import math
import secrets
import sys
from collections import Counter
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.advanced import CompletionCounter, compile_rules
from app.advanced_rules import AdvancedRules
from app.config import PasswordConfig


def main():
    expected = {"".join(x) for x in product("a1", repeat=4) if "a" in x and "1" in x}
    samples, alpha = 140000, 1e-6
    counter = CompletionCounter(
        compile_rules(
            PasswordConfig(
                length=4,
                advanced=AdvancedRules(
                    enabled=True,
                    custom_alphabet_enabled=True,
                    custom_alphabet="a1",
                    min_lowercase=1,
                    min_digits=1,
                ),
            )
        )
    )
    try:
        total = counter.total()
        assert total == len(expected)
        observed = Counter(
            counter.unrank(secrets.randbelow(total)) for _ in range(samples)
        )
        assert set(observed) == expected
        threshold = math.ceil(
            math.sqrt(samples / 2 * math.log(2 * len(expected) / alpha))
        )
        largest_deviation = max(
            abs(observed[word] - samples / len(expected)) for word in expected
        )
        print(
            json.dumps(
                {
                    "samples": samples,
                    "outcomes": len(expected),
                    "family_wise_alpha": alpha,
                    "threshold": threshold,
                    "largest_deviation": largest_deviation,
                    "passed": largest_deviation < threshold,
                }
            )
        )
        assert largest_deviation < threshold
    finally:
        counter.close()


if __name__ == "__main__":
    main()

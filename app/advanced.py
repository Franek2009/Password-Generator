"""Exact completion counts and uniform unranking. No password rejection/repair.

For each prefix, every possible next character owns an interval of ranks whose
size is its exact number of valid completions. These disjoint intervals cover
[0, N). Induction gives a bijection between ranks and valid strings, so one
secrets.randbelow(N) gives probability 1/N to each valid password.

Category aggregation is valid because position rules distinguish categories,
not individual characters. Within the previous category only the previous
character differs (run extension); all other characters have equal counts.
"""

import secrets
import string
from dataclasses import dataclass
from functools import cache

from app.advanced_rules import CharacterType
from app.errors import GenerationError
from app.generator import SIMILAR_CHARACTERS

POOLS = (
    string.ascii_uppercase,
    string.ascii_lowercase,
    string.digits,
    string.punctuation,
)
TYPE_MASKS = {
    CharacterType.ANY: 15,
    CharacterType.LETTER: 3,
    CharacterType.UPPER: 1,
    CharacterType.LOWER: 2,
    CharacterType.DIGIT: 4,
    CharacterType.SYMBOL: 8,
}
SHIFTS = (0, 7, 14, 21)


class GenerationCancelled(Exception):
    """Operational cancellation, never a claim that rules are impossible."""


@dataclass(frozen=True)
class CompiledRules:
    length: int
    pools: tuple[str, ...]
    minima: tuple[int, ...]
    masks: tuple[int, ...]
    run_limit: int


def compile_rules(config):
    rules = config.advanced
    rules.validate_structure()
    n = config.length
    if type(n) is not int or not 1 <= n <= 64:
        raise GenerationError("invalid_length", "Advanced length must be from 1 to 64.")
    flags = (config.uppercase, config.lowercase, config.numbers, config.special)
    if any(type(v) is not bool for v in (*flags, config.exclude_similar)):
        raise GenerationError("rules_invalid", "Invalid character-set flags.")
    if not any(flags):
        raise GenerationError("no_sets", "Select at least one character set.")
    if any(m and not enabled for m, enabled in zip(rules.minima, flags)):
        raise GenerationError(
            "minimum_disabled", "A required character set is disabled."
        )
    allowed = (
        set(rules.custom_alphabet)
        if rules.custom_alphabet_enabled
        else set("".join(POOLS))
    )
    forbidden = set(rules.forbidden_characters)
    if config.exclude_similar:
        forbidden.update(SIMILAR_CHARACTERS)
    pools = tuple(
        "".join(c for c in p if c in allowed and c not in forbidden) if enabled else ""
        for p, enabled in zip(POOLS, flags)
    )
    if not any(pools):
        raise GenerationError("empty_alphabet", "The effective alphabet is empty.")
    if any(m and not p for m, p in zip(rules.minima, pools)):
        raise GenerationError(
            "minimum_unavailable",
            "A required character set has no available characters.",
        )
    if sum(rules.minima) > n:
        raise GenerationError(
            "minimum_sum", "The sum of minima exceeds the password length."
        )
    available = sum(1 << i for i, p in enumerate(pools) if p)
    first = available & TYPE_MASKS[rules.first_type]
    last = available & TYPE_MASKS[rules.last_type]
    if not first:
        raise GenerationError(
            "first_unavailable", "No character matches the first-position rule."
        )
    if not last:
        raise GenerationError(
            "last_unavailable", "No character matches the last-position rule."
        )
    masks = [available] * n
    masks[0] &= first
    masks[-1] &= last
    if not masks[0]:
        raise GenerationError(
            "no_valid_password", "The position rules cannot both be satisfied."
        )
    return CompiledRules(
        n, pools, rules.minima, tuple(masks), rules.max_identical_run or n
    )


class CompletionCounter:
    """Per-job cache contains counts of non-secret states, never prefixes/results."""

    def __init__(self, compiled, cancelled=None):
        self.rules = compiled
        self.cancelled = cancelled or (lambda: False)
        self.sizes = tuple(map(len, compiled.pools))
        self.alphabet = tuple(
            sorted((c, i) for i, p in enumerate(compiled.pools) for c in p)
        )
        self.initial = sum(m << shift for m, shift in zip(compiled.minima, SHIFTS))
        self.states = 0
        n, masks, sizes, limit = (
            compiled.length,
            compiled.masks,
            self.sizes,
            compiled.run_limit,
        )
        free = [1]
        for mask in reversed(masks):
            free.append(free[-1] * sum(sizes[j] for j in range(4) if mask & (1 << j)))

        @cache
        def deficits(packed):
            ds = tuple((packed >> shift) & 127 for shift in SHIFTS)
            return ds, sum(ds)

        def checkpoint():
            self.states += 1
            if self.states & 1023 == 0 and self.cancelled():
                raise GenerationCancelled()

        @cache
        def plain(r, packed):
            checkpoint()
            if not packed:
                return free[r]
            ds, total = deficits(packed)
            if total > r:
                return 0
            if not r:
                return 0
            mask = masks[n - r]
            return sum(
                sizes[j] * plain(r - 1, packed - (1 << SHIFTS[j]) if ds[j] else packed)
                for j in range(4)
                if mask & (1 << j)
            )

        def subtract(packed, category, amount):
            value = (packed >> SHIFTS[category]) & 127
            return packed - (min(value, amount) << SHIFTS[category])

        # Algebraic elimination of the last-character/run dimensions.
        # For a single character with class marker y, allowed run lengths have
        # B=y+...+y^R. Last-run decomposition gives H=B/(1+B)
        # = (y-y^(R+1))/(1-y^(R+1)). Thus all words have series
        # F=1/(1-sum(a_i*H_i)). G_i=H_i*F counts words ending in a
        # particular character of class i. Saturated minima commute with each
        # monomial shift: (r,d) -> (r-k, max(0,d-k*e_i)).
        q = limit + 1

        groups = tuple(
            tuple(i for i, size in enumerate(sizes) if size == a)
            for a in sorted(set(sizes))
            if a and sizes.count(a) > 1
        )

        @cache
        def canonical(packed):
            mapping = list(range(4))
            normalized = packed
            for group in groups:
                values = [(packed >> SHIFTS[i]) & 127 for i in group]
                ordered = sorted(values, reverse=True)
                for i, value in zip(group, ordered):
                    normalized = (normalized & ~(127 << SHIFTS[i])) | (
                        value << SHIFTS[i]
                    )
                for i, value in zip(group, values):
                    mapping[i] = group[ordered.index(value)]
            return normalized, tuple(mapping)

        def words(r, packed):
            return node(r, canonical(packed)[0] if groups else packed)[0]

        def ending(r, packed, category):
            if groups:
                packed, mapping = canonical(packed)
                category = mapping[category]
            return node(r, packed)[category + 1]

        zero = (0, 0, 0, 0, 0)

        @cache
        def node(r, packed):
            checkpoint()
            ds, total = deficits(packed)
            if r < 0 or total > r:
                return zero
            if not r:
                return (1, 0, 0, 0, 0)
            endings = [0, 0, 0, 0]
            for category in range(4):
                if not sizes[category]:
                    continue
                equivalent = next(
                    (
                        j
                        for j in range(category)
                        if sizes[j] == sizes[category] and ds[j] == ds[category]
                    ),
                    None,
                )
                if equivalent is not None:
                    endings[category] = endings[equivalent]
                    continue
                value = words(r - 1, subtract(packed, category, 1))
                if r >= q:
                    shifted = subtract(packed, category, q)
                    if groups:
                        shifted, mapping = canonical(shifted)
                        marked = mapping[category]
                    else:
                        marked = category
                    previous = node(r - q, shifted)
                    value += previous[marked + 1] - previous[0]
                endings[category] = value
            return (sum(a * b for a, b in zip(sizes, endings)), *endings)

        end_mask = masks[-1]

        @cache
        def with_end(r, packed):
            if r == 0:
                return 0
            if end_mask == sum(1 << i for i, a in enumerate(sizes) if a):
                return words(r, packed)
            return sum(
                sizes[j] * ending(r, packed, j) for j in range(4) if end_mask & (1 << j)
            )

        @cache
        def count(r, packed, previous, run):
            checkpoint()
            ds, total = deficits(packed)
            if total > r:
                return 0
            if not r:
                return int(not packed)
            if limit >= r - total + max(ds[j] for j in range(4) if sizes[j]) and (
                previous == 4 or limit >= run + r - total + ds[previous]
            ):
                return plain(r, packed)
            if previous == 4:
                if masks[0] == sum(1 << j for j, size in enumerate(sizes) if size):
                    return with_end(r, packed)
                # Root first-position restriction. Later counts only need the
                # last-position mask, since the first character is already fixed.
                return sum(
                    sizes[j] * count(r - 1, subtract(packed, j, 1), j, 1)
                    for j in range(4)
                    if masks[0] & (1 << j)
                )
            # Restrict the first run of the remaining suffix to R-run copies
            # of the preceding character. Its multiplier is
            # (1-y^(R-run+1))/(1-y^(R+1)). For the end-constrained series
            # there is also the all-one-character boundary correction below.
            value = 0
            offset = q - run
            for k in range(0, r + 1, q):
                value += with_end(r - k, subtract(packed, previous, k))
                if k + offset <= r:
                    value -= with_end(
                        r - k - offset, subtract(packed, previous, k + offset)
                    )
            if end_mask & (1 << previous) and all(
                d == 0 for j, d in enumerate(ds) if j != previous
            ):
                if r >= q and r % q == 0:
                    value += 1
                if r >= offset and r % q == offset:
                    value -= 1
            return value

        self._count = count
        self._cache_functions = (count, plain, node, canonical, with_end, deficits)

    def total(self):
        if self.cancelled():
            raise GenerationCancelled()
        return self._count(self.rules.length, self.initial, 4, 0)

    def unrank(self, rank):
        total = self.total()
        if type(rank) is not int or not 0 <= rank < total:
            raise ValueError("Rank outside the valid range")
        packed, previous, run = self.initial, "", 0
        result = []
        for position in range(self.rules.length):
            if self.cancelled():
                raise GenerationCancelled()
            for char, category in self.alphabet:
                if not self.rules.masks[position] & (1 << category):
                    continue
                next_run = run + 1 if char == previous else 1
                if next_run > self.rules.run_limit:
                    continue
                next_packed = (
                    packed - (1 << SHIFTS[category])
                    if (packed >> SHIFTS[category]) & 127
                    else packed
                )
                width = self._count(
                    self.rules.length - position - 1, next_packed, category, next_run
                )
                if rank < width:
                    result.append(char)
                    packed, previous, run = next_packed, char, next_run
                    break
                rank -= width
            else:
                raise AssertionError("Completion-count invariant violated")
        return "".join(result)

    def close(self):
        for function in self._cache_functions:
            function.cache_clear()


def generate_advanced(config, cancelled=None):
    counter = CompletionCounter(compile_rules(config), cancelled)
    try:
        total = counter.total()
        if not total:
            raise GenerationError(
                "no_valid_password", "No password satisfies these rules."
            )
        return counter.unrank(secrets.randbelow(total))
    finally:
        counter.close()

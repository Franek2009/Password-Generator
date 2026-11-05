"""Independent exhaustive oracle: no engine compiler/count helpers in accepts()."""

from dataclasses import replace
from itertools import product

import pytest

from app.advanced import CompletionCounter, GenerationCancelled, compile_rules
from app.advanced_rules import AdvancedRules, CharacterType
from app.config import PasswordConfig, PasswordMode
from app.errors import GenerationError
from app.generator import generate_password


def category(char):
    if "A" <= char <= "Z":
        return 0
    if "a" <= char <= "z":
        return 1
    if "0" <= char <= "9":
        return 2
    return 3


def matches(char, kind):
    c = category(char)
    return (
        kind == CharacterType.ANY
        or (kind == CharacterType.LETTER and c in (0, 1))
        or {
            CharacterType.UPPER: 0,
            CharacterType.LOWER: 1,
            CharacterType.DIGIT: 2,
            CharacterType.SYMBOL: 3,
        }.get(kind)
        == c
    )


def accepts(word, rules):
    if any(
        sum(category(c) == i for c in word) < minimum
        for i, minimum in enumerate(rules.minima)
    ):
        return False
    if not matches(word[0], rules.first_type) or not matches(word[-1], rules.last_type):
        return False
    run = 0
    previous = None
    for char in word:
        run = run + 1 if char == previous else 1
        previous = char
        if rules.max_identical_run is not None and run > rules.max_identical_run:
            return False
    return True


@pytest.mark.parametrize("alphabet", ["a", "ab", "a2", "aA2", "aA2!", "abAB12!?"])
def test_exhaustive_count_and_every_rank_are_a_bijection(alphabet):
    # Full output enumeration, with grids of endpoint, quota and run rules.
    for n in range(1, 5):
        for first, last in product(CharacterType, repeat=2):
            for limit in (None, 1, 2):
                for minimum in ((0, 0, 0, 0), (1, 0, 0, 0), (0, 1, 1, 0), (1, 1, 1, 1)):
                    rules = AdvancedRules(
                        enabled=True,
                        custom_alphabet_enabled=True,
                        custom_alphabet=alphabet,
                        first_type=first,
                        last_type=last,
                        max_identical_run=limit,
                        min_uppercase=minimum[0],
                        min_lowercase=minimum[1],
                        min_digits=minimum[2],
                        min_symbols=minimum[3],
                    )
                    expected = [
                        "".join(w)
                        for w in product(sorted(alphabet), repeat=n)
                        if accepts(w, rules)
                    ]
                    config = PasswordConfig(length=n, advanced=rules)
                    try:
                        counter = CompletionCounter(compile_rules(config))
                    except GenerationError:
                        assert expected == []
                        continue
                    try:
                        assert counter.total() == len(expected)
                        actual = [counter.unrank(i) for i in range(len(expected))]
                        assert actual == expected
                    finally:
                        counter.close()


@pytest.mark.parametrize("alphabet", ["ab12", "ABab12!?", "aA2!"])
def test_minimum_grid(alphabet):
    n = 4
    for minima in product(range(n + 1), repeat=4):
        if sum(minima) > n:
            continue
        rules = AdvancedRules(
            enabled=True,
            custom_alphabet_enabled=True,
            custom_alphabet=alphabet,
            min_uppercase=minima[0],
            min_lowercase=minima[1],
            min_digits=minima[2],
            min_symbols=minima[3],
            max_identical_run=2,
        )
        expected = sorted(
            "".join(w) for w in product(alphabet, repeat=n) if accepts(w, rules)
        )
        try:
            counter = CompletionCounter(
                compile_rules(PasswordConfig(length=n, advanced=rules))
            )
        except GenerationError:
            assert expected == []
            continue
        try:
            assert counter.total() == len(expected)
            assert [counter.unrank(i) for i in range(len(expected))] == expected
        finally:
            counter.close()


def test_filters_deduplication_case_and_legacy_independence():
    rules = AdvancedRules(
        enabled=True,
        custom_alphabet_enabled=True,
        custom_alphabet="aaAAbb0022!!",
        forbidden_characters="!A",
        min_digits=1,
    )
    config = PasswordConfig(length=12, exclude_similar=True, advanced=rules)
    assert set("".join(compile_rules(config).pools)) == set("ab2")
    for _ in range(20):
        result = generate_password(config)
        assert set(result) <= set("ab2") and "2" in result
    # Inactive advanced semantics must not affect the existing generator.
    inactive = replace(rules, enabled=False, min_digits=64)
    result = generate_password(PasswordConfig(length=8, advanced=inactive))
    assert len(result) == 8


def test_empty_alphabet_and_impossible_run_are_distinct():
    with pytest.raises(GenerationError) as e:
        generate_password(
            PasswordConfig(
                advanced=AdvancedRules(enabled=True, custom_alphabet_enabled=True)
            )
        )
    assert e.value.code == "empty_alphabet"
    with pytest.raises(GenerationError) as e:
        generate_password(
            PasswordConfig(
                length=8,
                advanced=AdvancedRules(
                    enabled=True,
                    custom_alphabet_enabled=True,
                    custom_alphabet="a",
                    max_identical_run=1,
                ),
            )
        )
    assert e.value.code == "no_valid_password"


def test_unique_64_character_result_and_rank_bounds():
    rules = AdvancedRules(
        enabled=True,
        custom_alphabet_enabled=True,
        custom_alphabet="a1",
        first_type=CharacterType.LETTER,
        last_type=CharacterType.DIGIT,
        max_identical_run=1,
    )
    counter = CompletionCounter(
        compile_rules(PasswordConfig(length=64, advanced=rules))
    )
    try:
        assert counter.total() == 1
        assert counter.unrank(0) == "a1" * 32
        for bad in (-1, 1, True):
            with pytest.raises(ValueError):
                counter.unrank(bad)
    finally:
        counter.close()


def test_cancellation_is_not_reported_as_invalid_rules():
    counter = CompletionCounter(
        compile_rules(PasswordConfig(advanced=AdvancedRules(enabled=True))),
        lambda: True,
    )
    with pytest.raises(GenerationCancelled):
        counter.total()
    counter.close()


@pytest.mark.parametrize(
    "fields",
    [
        {"min_digits": True},
        {"min_digits": -1},
        {"min_digits": 65},
        {"max_identical_run": 0},
        {"max_identical_run": False},
        {"first_type": "bad"},
        {"custom_alphabet": "a "},
        {"forbidden_characters": "\n"},
        {"custom_alphabet": "ż"},
    ],
)
def test_invalid_rule_types_and_ascii(fields):
    with pytest.raises(GenerationError):
        AdvancedRules(**fields).validate_structure()


def test_roundtrip_is_strict_and_contains_only_rule_parameters():
    rules = AdvancedRules(
        enabled=True,
        custom_alphabet_enabled=True,
        custom_alphabet="baab",
        forbidden_characters="!!",
    )
    data = rules.to_data()
    assert data["custom_alphabet"] == "ab" and data["forbidden_characters"] == "!"
    assert AdvancedRules.from_data(data).to_data() == data
    with pytest.raises(GenerationError):
        AdvancedRules.from_data({**data, "password": "secret"})


def test_human_generator_ignores_random_rules(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text("iPhone\n")
    result = generate_password(
        PasswordConfig(
            mode=PasswordMode.HUMAN,
            words=2,
            numbers=False,
            special=False,
            wordlist_path=str(path),
            advanced=AdvancedRules(enabled=True, custom_alphabet_enabled=True),
        )
    )
    assert result == "IPhone-IPhone"


def test_shared_rank_contract_and_large_exact_counts():
    import json
    from pathlib import Path

    for case in json.loads(
        (Path(__file__).parent / "fixtures/advanced_contract.json").read_text()
    ):
        rules = AdvancedRules.from_data(case["rules"])
        try:
            counter = CompletionCounter(
                compile_rules(PasswordConfig(length=case["length"], advanced=rules))
            )
        except GenerationError:
            assert case["count"] == "0"
            continue
        try:
            assert counter.total() == int(case["count"])
            for example in case["ranks"]:
                assert counter.unrank(int(example["rank"])) == example["result"]
        finally:
            counter.close()


def test_partial_repeat_bound_matches_reference_state_recurrence():
    from functools import cache

    # Independent original state recurrence, per *actual character* rather
    # than algebraic run elimination or category aggregation.
    for alphabet, n in [("aA1!", 8), ("abA1!", 7)]:
        rules = AdvancedRules(
            enabled=True,
            custom_alphabet_enabled=True,
            custom_alphabet=alphabet,
            min_lowercase=2,
            min_uppercase=1,
            min_digits=1,
            min_symbols=1,
            first_type=CharacterType.LETTER,
            last_type=CharacterType.SYMBOL,
            max_identical_run=2,
        )

        @cache
        def reference(left, ds, previous, run, *, alphabet=alphabet, n=n, rules=rules):
            if sum(ds) > left:
                return 0
            if not left:
                return int(not any(ds))
            result = 0
            for char in alphabet:
                if left == n and not matches(char, rules.first_type):
                    continue
                if left == 1 and not matches(char, rules.last_type):
                    continue
                next_run = run + 1 if char == previous else 1
                if next_run > rules.max_identical_run:
                    continue
                updated = list(ds)
                updated[category(char)] = max(0, updated[category(char)] - 1)
                result += reference(left - 1, tuple(updated), char, next_run)
            return result

        counter = CompletionCounter(
            compile_rules(PasswordConfig(length=n, advanced=rules))
        )
        try:
            assert counter.total() == reference(n, rules.minima, "", 0)
        finally:
            counter.close()
            reference.cache_clear()

# Delivery snapshot — 2026-11-05

Working branch: `master`. Base HEAD:
`11aed57e3e1c038415f2fe5bc28aecc9d62490b5`.
This is the snapshot taken before the owner authorized committing and pushing
the review branch. No tag or release was published. Build outputs are local,
ignored development artifacts; see [hashes and commands](evidence/builds.json).

`assets/icon.svg` was already modified before this work (Inkscape metadata).
It was left untouched and is included in Git's raw status/stat below, but is
excluded from the implementation's file list and proposed commits.

## Changed/new implementation files

* `README.md`
* `android/app/src/androidTest/java/pl/franek/passwordgenerator/AdvancedEngineBenchmarkTest.kt`
* `android/app/src/androidTest/java/pl/franek/passwordgenerator/AdvancedUiTest.kt`
* `android/app/src/androidTest/java/pl/franek/passwordgenerator/GeneratorFeaturesTest.kt`
* `android/app/src/main/assets/ui.json`
* `android/app/src/main/java/pl/franek/passwordgenerator/AdvancedRules.kt`
* `android/app/src/main/java/pl/franek/passwordgenerator/MainActivity.kt`
* `android/app/src/main/java/pl/franek/passwordgenerator/PasswordGenerator.kt`
* `android/app/src/main/java/pl/franek/passwordgenerator/Presets.kt`
* `android/app/src/main/java/pl/franek/passwordgenerator/UiModel.kt`
* `android/app/src/test/java/pl/franek/passwordgenerator/AdvancedGenerationTest.kt`
* `android/app/src/test/java/pl/franek/passwordgenerator/PresetsTest.kt`
* `app/advanced.py`
* `app/advanced_rules.py`
* `app/advanced_ui.py`
* `app/config.py`
* `app/generator.py`
* `app/presentation.py`
* `app/presets.py`
* `app/ui.py`
* `data/ui.json`
* `docs/v1.3.0/README.md`
* `docs/v1.3.0/algorithm.md`
* `docs/v1.3.0/delivery.md`
* `docs/v1.3.0/evidence/android-api35-tests.txt`
* `docs/v1.3.0/evidence/android-engine-metrics.txt`
* `docs/v1.3.0/evidence/android-jvm-tests.json`
* `docs/v1.3.0/evidence/android-lint.json`
* `docs/v1.3.0/evidence/builds.json`
* `docs/v1.3.0/evidence/linux-smoke-output.txt`
* `docs/v1.3.0/evidence/linux-smoke.json`
* `docs/v1.3.0/evidence/python-benchmarks.json`
* `docs/v1.3.0/evidence/python-lint.txt`
* `docs/v1.3.0/evidence/python-tests.txt`
* `docs/v1.3.0/evidence/statistics.json`
* `docs/v1.3.0/presets.md`
* `docs/v1.3.0/preview/android-dark-alphabet.png`
* `docs/v1.3.0/preview/android-dark-endpoints.png`
* `docs/v1.3.0/preview/android-dark-result.png`
* `docs/v1.3.0/preview/android-dark-rules.png`
* `docs/v1.3.0/preview/android-light-alphabet.png`
* `docs/v1.3.0/preview/android-light-endpoints.png`
* `docs/v1.3.0/preview/android-light-result.png`
* `docs/v1.3.0/preview/android-light-rules.png`
* `docs/v1.3.0/preview/desktop-dark-narrow.png`
* `docs/v1.3.0/preview/desktop-dark-rules.png`
* `docs/v1.3.0/preview/desktop-light-narrow.png`
* `docs/v1.3.0/preview/desktop-light-rules.png`
* `docs/v1.3.0/security-review.md`
* `scripts/benchmark_advanced.py`
* `scripts/check_advanced_statistics.py`
* `scripts/preview_advanced_desktop.py`
* `tests/fixtures/advanced_contract.json`
* `tests/fixtures/legacy_presets_v1.json`
* `tests/fixtures/preset_contract.json`
* `tests/test_advanced.py`
* `tests/test_advanced_ui.py`
* `tests/test_presentation.py`
* `tests/test_presets.py`

## Git status

```text
 M README.md
 M android/app/src/androidTest/java/pl/franek/passwordgenerator/GeneratorFeaturesTest.kt
 M android/app/src/main/assets/ui.json
 M android/app/src/main/java/pl/franek/passwordgenerator/MainActivity.kt
 M android/app/src/main/java/pl/franek/passwordgenerator/PasswordGenerator.kt
 M android/app/src/main/java/pl/franek/passwordgenerator/Presets.kt
 M android/app/src/main/java/pl/franek/passwordgenerator/UiModel.kt
 M android/app/src/test/java/pl/franek/passwordgenerator/PresetsTest.kt
 M app/config.py
 M app/generator.py
 M app/presentation.py
 M app/presets.py
 M app/ui.py
 M assets/icon.svg
 M data/ui.json
 M tests/fixtures/preset_contract.json
 M tests/test_presentation.py
 M tests/test_presets.py
?? android/app/src/androidTest/java/pl/franek/passwordgenerator/AdvancedEngineBenchmarkTest.kt
?? android/app/src/androidTest/java/pl/franek/passwordgenerator/AdvancedUiTest.kt
?? android/app/src/main/java/pl/franek/passwordgenerator/AdvancedRules.kt
?? android/app/src/test/java/pl/franek/passwordgenerator/AdvancedGenerationTest.kt
?? app/advanced.py
?? app/advanced_rules.py
?? app/advanced_ui.py
?? docs/v1.3.0/
?? scripts/benchmark_advanced.py
?? scripts/check_advanced_statistics.py
?? scripts/preview_advanced_desktop.py
?? tests/fixtures/advanced_contract.json
?? tests/fixtures/legacy_presets_v1.json
?? tests/test_advanced.py
?? tests/test_advanced_ui.py
```

## Git diff --stat

```text
 README.md                                          |  33 +++++
 .../passwordgenerator/GeneratorFeaturesTest.kt     |  27 ++--
 android/app/src/main/assets/ui.json                |  70 ++++++++-
 .../pl/franek/passwordgenerator/MainActivity.kt    |  68 ++++++++-
 .../franek/passwordgenerator/PasswordGenerator.kt  |   2 +
 .../java/pl/franek/passwordgenerator/Presets.kt    | 156 ++++++++++++++-------
 .../java/pl/franek/passwordgenerator/UiModel.kt    | 144 ++++++++++++++++---
 .../pl/franek/passwordgenerator/PresetsTest.kt     |  30 +++-
 app/config.py                                      |  12 +-
 app/generator.py                                   |   3 +
 app/presentation.py                                |  18 +++
 app/presets.py                                     |  94 +++++++++----
 app/ui.py                                          | 152 +++++++++++++++++++-
 assets/icon.svg                                    |   8 +-
 data/ui.json                                       |  70 ++++++++-
 tests/fixtures/preset_contract.json                |  32 ++++-
 tests/test_presentation.py                         |  18 +++
 tests/test_presets.py                              |  62 +++++++-
 18 files changed, 861 insertions(+), 138 deletions(-)
```

This is the literal tracked diff statistic: it includes the pre-existing icon
metadata edit and excludes all untracked files. There are 42 new untracked
files listed above, including proofs, tests, fixtures, evidence and screenshots.
`git diff --check` completed successfully.

## Proposed logical commits (not created)

1. **Exact advanced generation engines.** Rule types, alphabet compilation,
   completion counting/unranking in Python/Kotlin, generator opt-in dispatch,
   independent exhaustive/shared contracts, benchmark/statistical harnesses and
   the mathematical argument. Preserve the classic/passphrase paths.
2. **Versioned settings and preset migration.** Strict v2 whitelists, lazy v1
   migration, separate preference object, safe storage errors, legacy fixtures
   and preset/preference tests. Include the UiState advanced field here.
3. **Desktop advanced controls.** Native collapsible panel, cancellable worker,
   atomic advanced preset application, persistent errors, singleton warning,
   accessible controls, default-window action visibility and Qt integration tests.
   Shared strings and the identical Android assets copy can land together here.
4. **Android advanced controls.** Compose fields, background feasibility/generation,
   revision cancellation, checked preference writes and updated/new instrumented
   tests. The same UiModel file spans steps 2 and 4; stage its relevant hunks.
5. **Documentation and acceptance evidence.** README development scope, storage/
   security notes, preview harness/captures, test/build measurements and this
   snapshot. Keep the earlier v1.2 references and release mechanisms unchanged.

This is a logical review split, not pre-staged commits. Re-run the relevant
checks after assembling each commit. This is the historical implementation snapshot. Current release acceptance and
remaining measurement limits are recorded in the
[verification report](README.md#release-acceptance).

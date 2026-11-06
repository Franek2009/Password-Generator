# Clipboard expiry — local validation

Local pre-release checks on top of v1.4.0, performed on Linux on
2026-11-06. This section records validation before committing or publishing.

| Check | Result |
| --- | --- |
| Full Python suite, Python 3.14.10 / PySide6 6.11.2, offscreen | 313 passed, normal process exit |
| Changed Python files, Ruff lint and format | Passed |
| Android JVM tests | 27 passed, 0 failures/errors |
| Android lintDebug | Passed: 0 errors, 11 warnings |
| Android assembleDebug and assembleDebugAndroidTest | Passed |
| Android instrumented suite, API 26 x86 | 22 passed |
| Android instrumented suite, API 35 x86_64 | 22 passed |
| Local Linux PyInstaller build | Passed |
| Bundled Linux startup, isolated settings / offscreen | Passed: alive after 5 seconds |
| git diff --check | Passed |

## What was exercised

The Python and Kotlin guards run the same 18 public-example scenarios from
`tests/fixtures/clipboard_contract.json`: off/default behavior, exact deadline
boundaries, recopy/reset, identical foreign text, changed content retaining a
marker, background deferral and return, foreign changes in the background,
duration changes, disabling, suspend-sized elapsed time, Unicode/non-breaking
spaces, failed clearing/retry, invalid duration and empty copy.

Additional unit tests cover reentrant change callbacks from clearing, stale
reads during recopy, copy failure, disposal, Qt ownership/marker/content checks,
Wayland focus gating, 64-bit Windows clock binding and Linux boot-time clock
selection. The Windows clock binding test uses a stub; it is not native Windows
validation.

Desktop UI tests cover copy-button, keyboard and shared result-copy routing,
full original Unicode text, automatic copying, unchanged deadlines during result
or mode changes, retained displayed text, persisted settings, defaults for bad
settings, cancellation on closing, accessible field labels and an actual QTimer
callback with a controlled elapsed clock. Existing context-menu/copy regression
tests also remain in the full suite.

Android tests use a controlled elapsed clock with the real clipboard adapter
and main-thread scheduler. They exercise foreground scheduled expiry without a
focus transition, deferred cleanup after return, API-26 empty-text fallback,
foreign clipboard replacement, and rotation. A small Java activity exists only
in the test APK under the test application's package; it acquires focus and
writes a public foreign entry before returning. Production manifests and
permissions are unchanged.

UI tests exercise the settings choice, its accessible label, persisted duration,
ViewModel reconstruction, unchanged sensitive-data metadata on API 35, raw-text
copy and exclusion of transient metadata/passwords from saved preferences and
presets. Settings screenshots use public test data; existing release screenshots
remain intact.

The first instrumented run failed only because a new test looked for a
standalone Settings button; the app opens Settings through More options. The
selector was corrected. The final reruns also include the subsequent one-second
elapsed-time scheduling safeguard and foreground-timer regression test.

The computer interruption left the final emulator sessions without completion
summaries. Their partial logs were preserved as `build/v150-instrumentation*-interrupted.log`;
those runs were not counted as passes. The task-owned emulators were restarted,
a boot-time System UI ANR dialog on API 35 was closed before testing, and the
complete suites were rerun. Final logs end with `OK (22 tests)` on both APIs.

## Packages for local testing

Ignored local output:

- `build/v150-packages/PasswordGenerator-linux-development.tar.gz`
- `build/v150-packages/PasswordGenerator-android-debug.apk`

Both use **development** version metadata, not a manually assigned 1.5.0.
The Linux package was built locally on Arch Linux and is not the Ubuntu-built
portable release artifact. The APK uses the existing debug signing mechanism;
it is not a distribution-signed update to an installed release. No signing
configuration or keys were changed.

Not performed: native Windows clipboard/runtime/package tests, isolated X11 and
Wayland clipboard interoperability tests, physical-phone tests, or manual
TalkBack/desktop screen-reader sessions. No isolated native X11/Wayland test
server is installed here; the user's desktop clipboard was not used for those
experiments. These remain manual acceptance checks before a release. CI was not triggered during that local validation stage.

The implementation conservatively skips unverified entries. OS restrictions,
process termination, clipboard managers and cross-process compare/clear races
still prevent an unconditional secure-erasure guarantee; see the feature guide.

## Reproduction

Use an environment with `requirements-dev.txt`. Ruff and PyInstaller were
installed in an ignored environment without changing dependency pins.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME= python -m pytest
git diff --check
./android/gradlew -p android testDebugUnitTest lintDebug assembleDebug assembleDebugAndroidTest
```

Gradle used JDK 21, two workers and in-process Kotlin compilation. Emulator runs
installed both debug APKs on the task-owned API-26 and API-35 AVDs, followed by:

```bash
adb -s emulator-5590 shell am instrument -w \
  pl.franek.passwordgenerator.test/androidx.test.runner.AndroidJUnitRunner
```

API 26 uses serial `emulator-5592`. Logs are under ignored
`build/v150-python-final.log`, `build/v150-gradle-final-checked.log`,
`build/v150-instrumentation26-final.log`, `build/v150-instrumentation35-final.log`
and `build/v150-linux-smoke.log`. Package checksums and metadata are recorded in
`build/v150-packages/verification.json`.

## Originally proposed commit split

1. `feat(clipboard): add matching expiry guards and platform adapters` — Python
   and Kotlin guards, clock/scheduler adapters and shared-contract tests.
2. `feat(ui): configure clipboard expiry and route every copy action` — settings,
   PL/EN labels, copy/focus/lifetime integration and native UI tests.
3. `docs: document clipboard expiry and add verified settings previews` — README,
   behavior/limitations, validation, gallery and preview script.

The owner's existing `assets/icon.svg` edit remains untouched and must not be
included in these commits.

## Working-tree inventory

`git status --short --branch --untracked-files=all` at completion:

```text
## master...origin/master
 M README.md
 M android/app/src/main/assets/ui.json
 M android/app/src/main/java/pl/franek/passwordgenerator/MainActivity.kt
 M android/app/src/main/java/pl/franek/passwordgenerator/UiModel.kt
 M app/presentation.py
 M app/result_view.py
 M app/ui.py
 M assets/icon.svg
 M data/ui.json
?? android/app/src/androidTest/AndroidManifest.xml
?? android/app/src/androidTest/java/pl/franek/passwordgenerator/ClipboardProbeActivity.java
?? android/app/src/androidTest/java/pl/franek/passwordgenerator/ClipboardUiTest.kt
?? android/app/src/main/java/pl/franek/passwordgenerator/AndroidClipboardController.kt
?? android/app/src/main/java/pl/franek/passwordgenerator/ClipboardGuard.kt
?? android/app/src/test/java/pl/franek/passwordgenerator/ClipboardGuardTest.kt
?? app/clipboard.py
?? docs/v1.5.0/README.md
?? docs/v1.5.0/preview/android-dark-clipboard.png
?? docs/v1.5.0/preview/android-light-clipboard.png
?? docs/v1.5.0/preview/desktop-dark-clipboard.png
?? docs/v1.5.0/preview/desktop-light-clipboard.png
?? docs/v1.5.0/validation.md
?? scripts/preview_clipboard_settings.py
?? tests/fixtures/clipboard_contract.json
?? tests/test_clipboard.py
```

`git diff --stat` below covers tracked files only, including the owner's
pre-existing icon edit. The new controllers, tests, shared fixture, documentation,
preview script and four screenshots are in the untracked inventory above.

```text
 README.md                                          | 12 +++++++
 android/app/src/main/assets/ui.json                | 16 +++++++--
 .../pl/franek/passwordgenerator/MainActivity.kt    | 17 +++++++++-
 .../java/pl/franek/passwordgenerator/UiModel.kt    | 35 ++++++++++++--------
 app/presentation.py                                |  3 ++
 app/result_view.py                                 |  8 +++--
 app/ui.py                                          | 38 +++++++++++++++++-----
 assets/icon.svg                                    |  8 ++---
 data/ui.json                                       | 16 +++++++--
 9 files changed, 119 insertions(+), 34 deletions(-)
```

## Release acceptance

The owner confirmed that the application works and authorized the v1.5.0
release and README update. The local limitations above remain an explicit record
of tests not performed by the agent; this acceptance is not a substitute for
those measurements or an independent security audit.

Release preparation updates README references, release notes and this acceptance
record without changing the locally tested application code. The pull request
runs Python tests, Android JVM/lint/build checks and instrumented UI tests on API
26 and 35 before merging. Desktop packaging is checked separately. The existing
tag-triggered [release workflow](https://github.com/Franek2009/Password-Generator/actions/workflows/release.yml)
then rebuilds versioned Linux/Windows packages and the signed APK, verifies all
53 corresponding-source files and publishes the four existing release assets.
Signing, licensing, provenance checks and distribution mechanisms are unchanged.
Application version metadata is derived from the release tag.

## Headless Qt shutdown regression

Release CI initially passed all 312 assertions but exited with SIGSEGV during
interpreter shutdown on Python 3.14.10. A local reproduction and native backtrace
isolated Python-created `QMimeData` retained by Qt's headless clipboard. Qt's
[default clipboard implementation](https://github.com/qt/qtbase/blob/v6.11.2/src/gui/kernel/qplatformclipboard.cpp)
keeps that data in a C++ global whose destruction can occur after Python bindings
are finalized. Clearing the isolated test clipboard before interpreter teardown
avoids that destruction-order failure.

The session fixture in `tests/conftest.py` releases only the **offscreen** test
clipboard while Python is alive. It does not touch a native desktop clipboard
or change production cleanup-on-close policy. An isolated subprocess regression
runs a complete pytest session with custom MIME data and checks successful
process exit. The full Python 3.14.10 run now passes 313 tests and exits normally.
The original Python 3.14.8 local run passed 312 tests before this regression was
added. Application code, Android behavior and package dependency pins are
unchanged by this test-resource cleanup.

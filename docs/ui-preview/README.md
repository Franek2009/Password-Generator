# Unified interface preview — v1.1.0

This preview follows the supplied desktop/Android reference. The existing
password-generation defaults (20 characters, 3 words, `-`) are retained.
The screenshots use public example strings, not user passwords.

| View | Dark | Light |
| --- | --- | --- |
| Desktop: random password | [Screenshot](desktop-dark-random.png) | [Screenshot](desktop-light-random.png) |
| Desktop: passphrase | [Screenshot](desktop-dark-phrase.png) | [Screenshot](desktop-light-phrase.png) |
| Desktop: settings | [Screenshot](desktop-dark-settings.png) | [Screenshot](desktop-light-settings.png) |
| Android: random password | [Screenshot](android-dark-random.png) | [Screenshot](android-light-random.png) |
| Android: passphrase | [Screenshot](android-dark-phrase.png) | [Screenshot](android-light-phrase.png) |
| Android: settings | [Screenshot](android-dark-settings.png) | [Screenshot](android-light-settings.png) |

[Desktop with English labels at minimum width](desktop-english-narrow.png).
[Android with English labels](android-english.png) and
[larger system font](android-english-large-font.png).
Android screenshots are captured from an Android 15 emulator by
`UnifiedUiTest.captureReviewScreenshots`.

Validation: 186 Python tests, 7 Android unit tests in each variant, Android
lint and debug build, and 3 instrumented tests on Android 15. Tests exercise
settings/language switching, copying, real orientation change, persistence
without storing the current result, and screenshot capture. CI also runs the
instrumented suite on Android API 26 and 35. Windows/Linux package builds
passed for the implementation branch.

Recreate desktop previews with:

```bash
QT_QPA_PLATFORM=offscreen python scripts/preview_desktop.py
```

The native window title bar is supplied by the operating system and is not
included in Qt's offscreen captures.

The application now shares Polish/English strings, icon paths and color tokens
between PySide6 and Compose (`data/ui.json`, mirrored in Android assets).
The Python test suite checks that both copies remain identical.

Settings contain General (automatic clipboard copying) and Appearance
(system/light/dark theme and system/Polish/English language).
All passphrase controls remain on the generator screen. Each generation mode
retains its own numbers/symbols choices. Preferences are stored with QSettings
and SharedPreferences; passwords are never written to those stores. Android
keeps the current result in a ViewModel during configuration changes. There is
no password history.

This is a review build. Publishing v1.1.0 follows visual approval.

# Unified interface preview — v1.1.0

This preview follows the supplied desktop/Android reference. The existing
password-generation defaults (20 characters, 3 words, `-`) are retained.
The screenshots use public example strings, not user passwords.

| View | Dark | Light |
| --- | --- | --- |
| Desktop: random password | [Screenshot](desktop-dark-random.png) | [Screenshot](desktop-light-random.png) |
| Desktop: passphrase | [Screenshot](desktop-dark-phrase.png) | [Screenshot](desktop-light-phrase.png) |
| Desktop: settings | [Screenshot](desktop-dark-settings.png) | [Screenshot](desktop-light-settings.png) |

[Desktop with English labels at minimum width](desktop-english-narrow.png).
Android screenshots are captured by `UnifiedUiTest.captureReviewScreenshots`.

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

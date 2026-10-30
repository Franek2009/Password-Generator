# Password Generator for Android

Natywna wersja aplikacji w Kotlinie i Jetpack Compose. Wymaga Android Studio,
JDK 17 oraz Android SDK 35. Minimalna obsługiwana wersja systemu to Android 8.0
(API 26).

## Uruchomienie

1. Otwórz katalog `android` w Android Studio.
2. Poczekaj na synchronizację Gradle.
3. Wybierz emulator lub podłączone urządzenie.
4. Uruchom konfigurację `app`.

Testy logiki można uruchomić poleceniem `./gradlew test` (Linux/macOS) lub
`gradlew.bat test` (Windows).

Hasła są generowane lokalnie przy użyciu `SecureRandom`. Aplikacja nie wymaga
dostępu do internetu i nie zapisuje wygenerowanych haseł.

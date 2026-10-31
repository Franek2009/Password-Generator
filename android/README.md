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

## Podpisane APK w GitHub Releases

Wydanie z tagu `vMAJOR.MINOR.PATCH` buduje testowane, podpisane APK
`PasswordGenerator-android.apk` i publikuje je obok paczek desktopowych.
`versionName` pochodzi z tagu, a `versionCode` to
`major * 1000000 + minor * 1000 + patch` (minor i patch < 1000).
Kolejne wydania muszą mieć rosnącą wersję. Wersje debug są dostępne w
Artifacts przebiegu Android APK i nie wymagają klucza wydawniczego.

Sekrety repozytorium wymagane do wydania:

- `ANDROID_KEYSTORE_BASE64`: zawartość magazynu PKCS12 zakodowana w base64;
- `ANDROID_KEYSTORE_PASSWORD`: hasło magazynu;
- `ANDROID_KEY_ALIAS`: alias klucza, domyślnie `password-generator`;
- `ANDROID_KEY_PASSWORD`: hasło klucza (dla PKCS12 takie samo jak magazynu).

Nowy klucz można wygenerować JDK `keytool`:

```bash
keytool -genkeypair -storetype PKCS12 -keystore password-generator.keystore \
  -alias password-generator -keyalg RSA -keysize 3072 -validity 10000
```

Zachowaj magazyn oraz hasło w bezpiecznej kopii zapasowej poza repozytorium.
Aktualizacje wymagają tego samego klucza. Nie dodawaj magazynu ani haseł do Git.
Lokalny build release wymaga zmiennych `PASSWORD_GENERATOR_RELEASE_TAG`,
`ANDROID_KEYSTORE_PATH`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`
i `ANDROID_KEY_PASSWORD`, a następnie `./gradlew test lintRelease assembleRelease`.

Pobierz APK z Releases na telefon i zezwól przeglądarce lub menedżerowi plików
na instalowanie aplikacji z tego źródła. Wymagany jest Android 8.0 lub nowszy.
Przejście z wersji debug może wymagać odinstalowania starej aplikacji,
ponieważ jest podpisana innym kluczem.

## Podgląd nowego interfejsu v1.1.0

Ekran generatora i ustawień używa wspólnych tekstów PL/EN i kolorów z desktopem.
Preferencje zapisuje SharedPreferences. Bieżące hasło jest wyłącznie w ViewModel,
więc przetrwa obrót ekranu, ale nie ponowne uruchomienie procesu aplikacji.
Własny słownik korzysta z trwałego uprawnienia do odczytu wybranego dokumentu.

Testy UI i zrzuty z emulatora:

```bash
./gradlew connectedDebugAndroidTest
adb pull /sdcard/Android/data/pl.franek.passwordgenerator/files/ui-preview ../docs/ui-preview
```

Zrzuty używają publicznych danych przykładowych. Przed publikacją v1.1.0
należy zaakceptować porównanie obu platform w `docs/ui-preview/`.

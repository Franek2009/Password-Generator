#!/usr/bin/env bash
# Preserve Gradle's instrumented reports and capture previews before uninstall.
set -uo pipefail
output=build/android-ui-preview
mkdir -p "$output"
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
result=0
./android/gradlew -p android connectedDebugAndroidTest --stacktrace || result=$?
# AGP removes the tested packages (and external app files) after connected tests.
# Reinstall the same APKs and capture public examples directly so they remain
# available until adb pull has finished. Gradle reports above remain authoritative.
if [ "$result" -eq 0 ]; then
  adb install -r android/app/build/outputs/apk/debug/app-debug.apk || exit 1
  adb install -r android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk || exit 1
  adb shell am instrument -w \
    -e class 'pl.franek.passwordgenerator.UnifiedUiTest#captureReviewScreenshots' \
    pl.franek.passwordgenerator.test/androidx.test.runner.AndroidJUnitRunner \
    > "$output/capture.txt" 2>&1 || result=$?
  cat "$output/capture.txt"
  if ! grep -Eq '^OK \(1 test\)' "$output/capture.txt"; then result=1; fi
  adb pull /sdcard/Android/data/pl.franek.passwordgenerator/files/ui-preview "$output/" || result=1
fi
adb logcat -d > "$output/logcat.txt" || true
exit "$result"

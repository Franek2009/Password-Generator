#!/usr/bin/env bash
# Keep test diagnostics and public-example screenshots even when a test fails.
set -uo pipefail
mkdir -p build/android-ui-preview
result=0
./android/gradlew -p android connectedDebugAndroidTest --stacktrace || result=$?
adb pull /sdcard/Android/data/pl.franek.passwordgenerator/files/ui-preview build/android-ui-preview/ || true
adb logcat -d > build/android-ui-preview/logcat.txt || true
exit "$result"

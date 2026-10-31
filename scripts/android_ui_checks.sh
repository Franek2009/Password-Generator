#!/usr/bin/env bash
# Keep test diagnostics and public-example screenshots even when a test fails.
set -uo pipefail
mkdir -p build/android-ui-preview
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
result=0
./android/gradlew -p android connectedDebugAndroidTest --stacktrace || result=$?
adb pull /sdcard/Android/data/pl.franek.passwordgenerator/files/ui-preview build/android-ui-preview/ || true
adb logcat -d > build/android-ui-preview/logcat.txt || true
exit "$result"

#!/bin/bash

./gradlew --stop
rm -rf .gradle/
rm -rf ~/.gradle/caches/

# ensure Java 17:
export JAVA_HOME=$(/usr/libexec/java_home -v 17)

# once it builds, you can bump the wrapper to 9.0:
./gradlew wrapper --gradle-version 9.0 --distribution-type all
./gradlew --version   # should report Gradle 9.0

./gradlew clean assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk

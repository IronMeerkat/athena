@file:Suppress("UnstableApiUsage")
pluginManagement {
  plugins {
    id("com.google.gms.google-services") version "4.4.3"
  }
  repositories {
    gradlePluginPortal()
    google()
    mavenCentral()
  }
}
dependencyResolutionManagement {
  repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
  repositories {
    google()
    mavenCentral()
  }
}
rootProject.name = "athena-android"
include(":app", ":digipaws-core", ":athena-sdk")



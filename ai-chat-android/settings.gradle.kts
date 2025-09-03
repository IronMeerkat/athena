pluginManagement {
  includeBuild("build-logic")
  repositories {
    google {
      content {
        includeGroupByRegex("com\\.android.*")
        includeGroupByRegex("com\\.google.*")
        includeGroupByRegex("androidx.*")
      }
    }
    mavenCentral()
    gradlePluginPortal()
    maven(url = "https://jitpack.io")
  }
}
plugins {
  id("org.gradle.toolchains.foojay-resolver-convention") version "0.8.0"
}
dependencyResolutionManagement {
  repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
  repositories {
    google()
    mavenCentral()
    maven(url = "https://jitpack.io")
  }
}

rootProject.name = "ai-chat-android"
include(":app")
include(":core:model")
include(":core:designsystem")
include(":core:network")
include(":core:navigation")
include(":core:data")
include(":core:logging")
include(":feature:channels")
include(":feature:messages")
include(":feature:login")
include(":baselineprofile")
include(":athena-api")
include(":digital-wellbeing")

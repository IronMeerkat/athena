/*
 * Designed and developed by 2024 skydoves (Jaewoong Eum)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
plugins {
  id("skydoves.android.application")
  id("skydoves.android.application.compose")
  id("skydoves.android.hilt")
  id("skydoves.spotless")
  alias(libs.plugins.kotlin.serialization)
  alias(libs.plugins.baselineprofile)
}

android {
  namespace = "com.ironmeerkat.athena"
  compileSdk = 36

  defaultConfig {
    applicationId = "com.ironmeerkat.athena"
    minSdk = 24
    targetSdk = 36
    versionCode = 1
    versionName = "1.0"

    testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    vectorDrawables {
      useSupportLibrary = true
    }
  }

  buildTypes {
    release {
      isMinifyEnabled = false
      proguardFiles(
        getDefaultProguardFile("proguard-android-optimize.txt"),
        "proguard-rules.pro"
      )
    }
  }
  compileOptions {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
  }
  kotlinOptions {
    jvmTarget = "17"
  }
  buildFeatures {
    compose = true
  }
  packaging {
    resources {
      excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
  }
}

dependencies {
  // Cores
  implementation(projects.core.designsystem)
  implementation(projects.core.navigation)

  // Features
  implementation(projects.feature.channels)
  implementation(projects.feature.messages)
  implementation(projects.feature.login)

  // Digital Wellbeing module (accessibility service, policy engine)
  implementation(projects.digitalWellbeing)

  // Athena API (Auth + Retrofit/OkHttp)
  implementation(projects.athenaApi)

  // Compose
  implementation(libs.androidx.activity.compose)
  implementation(libs.androidx.navigation.compose)
  implementation(libs.androidx.hilt.navigation.compose)
  implementation(libs.androidx.compose.ui)
  implementation(libs.androidx.compose.ui.tooling.preview)
  implementation(libs.androidx.compose.runtime)
  implementation(libs.androidx.compose.foundation)
  implementation(libs.androidx.compose.foundation.layout)
  implementation(libs.androidx.lifecycle.runtimeCompose)
  implementation(libs.androidx.lifecycle.viewModelCompose)
  implementation(libs.androidx.compose.material)
  implementation(libs.androidx.compose.material.iconsExtended)

  // Compose Image Loading
  implementation(libs.landscapist.glide)
  implementation(libs.landscapist.animation)
  implementation(libs.landscapist.placeholder)

  // Coroutines
  implementation(libs.kotlinx.coroutines.android)

  // Network
  implementation(libs.sandwich)
  implementation(libs.okhttp.logging)

  // Serialization
  implementation(libs.kotlinx.serialization.json)

  // Logger
  implementation(libs.stream.log)
  implementation(projects.core.logging)

  // Baseline Profiles
  implementation(libs.androidx.profileinstaller)
  baselineProfile(project(":baselineprofile"))

  // Firebase BOM at app level to align transitive Firebase artifacts
  implementation(enforcedPlatform(libs.firebase.bom))
  implementation(libs.firebase.messaging)
}
java {
  toolchain {
    languageVersion = JavaLanguageVersion.of(17)
  }
}

val skipGoogleServices = providers.gradleProperty("skipGoogleServices").orNull == "true"
if (!skipGoogleServices && file("google-services.json").exists()) {
  apply(plugin = libs.plugins.gms.googleServices.get().pluginId)
}
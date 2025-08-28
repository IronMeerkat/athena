plugins {
  alias(libs.plugins.android.library)
  alias(libs.plugins.kotlin.android)
}

android {
  namespace = "athena.sdk"
  compileSdk = 35

  defaultConfig {
    minSdk = 26
    targetSdk = 35
    consumerProguardFiles("consumer-rules.pro")
    buildConfigField("String", "ATHENA_BASE_URL", "\"https://192.168.0.213:8000\"")
  }

  buildFeatures {
    buildConfig = true
  }

  compileOptions {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
  }
  kotlinOptions { jvmTarget = "17" }
}

dependencies {
  api(libs.okhttp)
  implementation(libs.okhttp.logging)
  implementation(libs.kotlinx.coroutines.android)
  implementation(libs.androidx.datastore.preferences)
  implementation(platform(libs.firebase.bom))
  implementation(libs.firebase.auth)
}



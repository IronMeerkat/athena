plugins {
  id("skydoves.android.library")
  id("skydoves.android.hilt")
  id(libs.plugins.kotlin.serialization.get().pluginId)
  id(libs.plugins.google.secrets.get().pluginId)
  id("skydoves.spotless")
}

android {
  namespace = "com.ironmeerkat.athena.api"

  buildFeatures {
    buildConfig = true
  }
}

dependencies {
  // serialization
  implementation(libs.kotlinx.serialization.json)

  // okhttp/retrofit
  api(libs.sandwich)
  api(libs.okhttp.logging)
  implementation(platform(libs.retrofit.bom))
  implementation(libs.retrofit)
  implementation(libs.retrofit.kotlinx.serialization)

  // coroutines (Flow)
  implementation(libs.kotlinx.coroutines.android)
}

secrets {
  propertiesFileName = "secrets.properties"
  defaultPropertiesFileName = "secrets.defaults.properties"
}



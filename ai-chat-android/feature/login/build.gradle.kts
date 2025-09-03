plugins {
  id("skydoves.android.library")
  id("skydoves.android.library.compose")
  id("skydoves.android.feature")
  id("skydoves.android.hilt")
  id("skydoves.spotless")
}

android {
  namespace = "com.ironmeerkat.athena.feature.login"
}

dependencies {
  implementation(projects.athenaApi)
  implementation(libs.kotlinx.serialization.json)
  implementation(libs.androidx.hilt.navigation.compose)
  implementation(projects.core.logging)
}



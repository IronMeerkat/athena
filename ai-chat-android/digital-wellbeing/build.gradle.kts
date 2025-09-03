plugins {
  id("skydoves.android.library")
  id("skydoves.android.hilt")
  id("skydoves.spotless")
}

android {
  namespace = "com.ironmeerkat.athena.digitalwellbeing"
}

dependencies {
  implementation(projects.core.network)
  implementation(projects.athenaApi)
  implementation(projects.core.logging)
  implementation(libs.androidx.room.runtime)
  implementation(libs.androidx.room.ktx)
  ksp(libs.androidx.room.compiler)
}


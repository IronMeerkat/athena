plugins {
  id("skydoves.android.library")
  id("skydoves.spotless")
}

android {
  namespace = "com.ironmeerkat.athena.core.logging"
  buildFeatures {
    buildConfig = true
  }
}

dependencies {
  // Expose Timber to consumers so they can use Timber directly
  api(libs.timber)

  // AndroidX Startup to auto-initialize Timber trees
  implementation(libs.androidx.startup)
}



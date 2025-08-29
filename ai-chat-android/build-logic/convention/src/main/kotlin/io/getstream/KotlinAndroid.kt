package io.getstream

import com.android.build.api.dsl.CommonExtension
import org.gradle.api.JavaVersion
import org.gradle.api.Project
import org.gradle.kotlin.dsl.configure
import org.jetbrains.kotlin.gradle.dsl.KotlinJvmCompilerOptions
import org.jetbrains.kotlin.gradle.dsl.KotlinAndroidProjectExtension

/**
 * Configure base Kotlin with Android options
 */
internal fun Project.configureKotlinAndroid(
  commonExtension: CommonExtension<*, *, *, *, *, *>,
) {
  commonExtension.apply {
    compileSdk = 36

    defaultConfig {
      minSdk = 21
    }

    compileOptions {
      this.sourceCompatibility = JavaVersion.VERSION_17
      this.targetCompatibility = JavaVersion.VERSION_17
    }

    lint {
      abortOnError = false
    }

    // Configure Kotlin compiler options via the KotlinAndroidProjectExtension
    // Access the extension from the Project to avoid unresolved references
    this@configureKotlinAndroid.extensions.configure<KotlinAndroidProjectExtension> {
      compilerOptions {
        // Treat all Kotlin warnings as errors (disabled by default)
        (this as? KotlinJvmCompilerOptions)?.allWarningsAsErrors?.set(properties["warningsAsErrors"] as? Boolean ?: false)

        freeCompilerArgs.addAll(
          "-opt-in=kotlin.RequiresOptIn",
          // Enable experimental coroutines APIs, including Flow
          "-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi",
          // Enable experimental compose APIs
          "-opt-in=androidx.compose.material3.ExperimentalMaterial3Api",
          "-opt-in=androidx.lifecycle.compose.ExperimentalLifecycleComposeApi",
        )

        // Set JVM target
        (this as? KotlinJvmCompilerOptions)?.jvmTarget?.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
      }
    }
  }
}

// Removed custom CommonExtension.kotlinOptions extension to avoid referencing 'project' from a DSL receiver
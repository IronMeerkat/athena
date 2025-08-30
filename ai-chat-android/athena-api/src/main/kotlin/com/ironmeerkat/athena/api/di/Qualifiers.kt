package com.ironmeerkat.athena.api.di

import javax.inject.Qualifier

/** Qualifier for injecting the Athena base URL (as HttpUrl). */
@Qualifier
annotation class AthenaBaseUrl

/** Qualifier for injecting the default agent ID used for chat. */
@Qualifier
annotation class AthenaDefaultAgent



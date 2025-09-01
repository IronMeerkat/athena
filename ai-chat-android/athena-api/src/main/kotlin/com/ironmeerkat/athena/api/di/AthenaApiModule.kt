package com.ironmeerkat.athena.api.di

import com.ironmeerkat.athena.api.AthenaClient
import com.ironmeerkat.athena.api.AthenaService
import com.ironmeerkat.athena.api.BuildConfig
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import okhttp3.MediaType.Companion.toMediaType

@Module
@InstallIn(SingletonComponent::class)
internal object AthenaApiModule {

  /** Provides a configured JSON serializer/deserializer used by Retrofit and parsing SSE data. */
  @Provides
  @Singleton
  fun provideJson(): Json = Json {
    ignoreUnknownKeys = true
    isLenient = true
  }

  /** Expose the server base URL from secrets-generated BuildConfig. */
  @Provides
  @Singleton
  @AthenaBaseUrl
  fun provideBaseUrl(): HttpUrl = BuildConfig.ATHENA_API_BASE_URL.toHttpUrl()

  /** Default agent ID to route messages to (change via secrets). */
  @Provides
  @Singleton
  @AthenaDefaultAgent
  fun provideDefaultAgent(): String = BuildConfig.ATHENA_DEFAULT_AGENT

  /** Adds basic logging for development and a hook for auth headers if needed later. */
  @Provides
  @Singleton
  fun provideOkHttpClient(): OkHttpClient {
    val logging = HttpLoggingInterceptor().apply {
      level = HttpLoggingInterceptor.Level.BASIC
    }
    val headers = Interceptor { chain ->
      val request = chain.request()
        .newBuilder()
        // Optionally add JWT: .addHeader("Authorization", "Bearer ${token}")
        .build()
      chain.proceed(request)
    }
    return OkHttpClient.Builder()
      .addInterceptor(logging)
      .addInterceptor(headers)
      .build()
  }

  /** Retrofit instance with Kotlinx Serialization converter. */
  @Provides
  @Singleton
  fun provideRetrofit(
    @AthenaBaseUrl baseUrl: HttpUrl,
    json: Json,
    client: OkHttpClient,
  ): Retrofit {
    val contentType = "application/json".toMediaType()
    return Retrofit.Builder()
      .baseUrl(baseUrl)
      .client(client)
      .addConverterFactory(json.asConverterFactory(contentType))
      .build()
  }

  /** Typed Retrofit service for low-level endpoints. */
  @Provides
  @Singleton
  fun provideAthenaService(retrofit: Retrofit): AthenaService =
    retrofit.create(AthenaService::class.java)

  /** WebSocket manager for DRF subservices. */
  @Provides
  @Singleton
  fun provideWebSocketService(
    client: OkHttpClient,
    @AthenaBaseUrl baseUrl: HttpUrl,
    json: Json,
  ): com.ironmeerkat.athena.api.ws.WebSocketService =
    com.ironmeerkat.athena.api.ws.WebSocketService(client, baseUrl, json)

  /** Default journaling WS subservice. */
  @Provides
  @Singleton
  fun provideJournalWebSocketSubservice(): com.ironmeerkat.athena.api.ws.subservices.JournalWebSocketSubservice =
    com.ironmeerkat.athena.api.ws.subservices.JournalWebSocketSubservice()

  /** High-level client that orchestrates runs and streaming. */
  @Provides
  @Singleton
  fun provideAthenaClient(
    service: AthenaService,
    client: OkHttpClient,
    @AthenaBaseUrl baseUrl: HttpUrl,
    json: Json,
    wsService: com.ironmeerkat.athena.api.ws.WebSocketService,
    journalSubservice: com.ironmeerkat.athena.api.ws.subservices.JournalWebSocketSubservice,
  ): AthenaClient = AthenaClient(service, client, baseUrl, json, wsService, journalSubservice)
}



package com.example.mob.data.remote

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {

    // TODO: BuildConfig 또는 환경변수로 교체 필요
    private const val BASE_URL = "https://k14e105.p.ssafy.io"

    private var accessToken: String = ""

    fun setToken(token: String) {
        accessToken = token
    }

    private val okHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor { chain ->
                val builder = chain.request().newBuilder()
                if (accessToken.isNotBlank()) {
                    builder.addHeader("Authorization", "Bearer $accessToken")
                }
                chain.proceed(builder.build())
            }
            .addInterceptor(
                HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BODY
                }
            )
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    private val retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    val authApiService: AuthApiService by lazy {
        retrofit.create(AuthApiService::class.java)
    }

    val healthApiService: HealthApiService by lazy {
        retrofit.create(HealthApiService::class.java)
    }
}

package com.qode.roadsafety.data.api

import com.qode.roadsafety.data.model.*
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface ApiService {

    @POST("nv/verify")
    suspend fun verifyNumber(@Body request: VerifyRequest): Response<VerifyResponse>

    @POST("qod/session")
    suspend fun createQoDSession(@Body request: QoDRequest): Response<QoDResponse>

    @Multipart
    @POST("upload")
    suspend fun uploadVideo(@Part file: MultipartBody.Part): Response<UploadResponse>

    @POST("ai-run")
    suspend fun runAi(): Response<AiRunResponse>

    @GET("ai-result")
    suspend fun getAiResult(): Response<AiResultResponse>
}

object ApiClient {
    // 10.0.2.2 connects Android Emulator to host Mac localhost:8000!
    // Set to "http://34.86.94.186:8000/" for remote VM.
    var baseUrl: String = "http://10.0.2.2:8000/"

    private fun getOkHttpClient(): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        return OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    val service: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(getOkHttpClient())
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}

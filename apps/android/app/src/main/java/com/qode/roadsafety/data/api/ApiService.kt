package com.qode.roadsafety.data.api

import com.qode.roadsafety.BuildConfig
import com.qode.roadsafety.data.model.*
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import okhttp3.RequestBody
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface ApiService {

    @POST("api/number-verification/verify")
    suspend fun verifyNumber(@Body request: VerifyRequest): Response<VerifyResponse>

    @POST("api/qod/sessions")
    suspend fun createQoDSession(@Body request: QoDRequest): Response<QoDResponse>

    @DELETE("api/qod/sessions/{session_id}")
    suspend fun deleteQoDSession(@Path("session_id") sessionId: String): Response<Void>

    @Multipart
    @POST("api/videos")
    suspend fun uploadVideo(
        @Part("flow_id") flowId: RequestBody,
        @Part file: MultipartBody.Part
    ): Response<JobStatusResponse>

    @GET("api/jobs/{job_id}")
    suspend fun getJobStatus(@Path("job_id") jobId: String): Response<JobStatusResponse>

    @GET("api/jobs/{job_id}/result")
    suspend fun getAiResult(@Path("job_id") jobId: String): Response<FtrResult>
}

object ApiClient {
    private val baseUrl: String = BuildConfig.QODE_API_BASE_URL

    private fun getOkHttpClient(): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        return OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .writeTimeout(120, TimeUnit.SECONDS)
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

    val mobileAuthorizationUrl: String
        get() = baseUrl.trimEnd('/') + "/api/auth/start?mobile=true"
}

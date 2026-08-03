package com.qode.roadsafety.data.model

import com.google.gson.annotations.SerializedName

data class VerifyRequest(
    val access_token: String = "mock-token",
    val phone_number: String
)

data class VerifyResponse(
    val devicePhoneNumberVerified: Boolean
)

data class QoDRequest(
    val access_token: String = "mock-token",
    val duration: Int = 60
)

data class QoDResponse(
    val sessionId: String? = null,
    val duration: Int? = null,
    val qosStatus: String? = null
)

data class UploadResponse(
    val message: String,
    val filename: String
)

data class AiRunResponse(
    val status: String
)

data class AiResultResponse(
    val status: String, // IDLE, UPLOADED, PROCESSING, DONE, FAILED
    val progress: Float = 0f, // 0.0 to 1.0
    val message: String? = null,
    val result: FtrResult? = null,
    val detail: String? = null
)

data class FtrResult(
    @SerializedName("arac_bilgisi") val aracBilgisi: VehicleInfo? = null,
    @SerializedName("tespitler") val tespitler: List<DetectionItem>? = null
)

data class VehicleInfo(
    val tip: String,
    val plaka: String,
    val renk: String,
    @SerializedName("confidence_score") val confidenceScore: Double
)

data class DetectionItem(
    @SerializedName("zaman_saniye") val zamanSaniye: Double,
    val kategori: String,
    val etiket: String,
    @SerializedName("confidence_score") val confidenceScore: Double
)

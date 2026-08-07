package com.qode.roadsafety.data.model

import com.google.gson.annotations.SerializedName

data class VerifyRequest(
    val flowId: String,
    val phoneNumber: String
)

data class VerifyResponse(
    val flowId: String,
    val devicePhoneNumberVerified: Boolean,
    val phoneNumber: String? = null,
    val correlator: String? = null
)

data class QoDRequest(
    val flowId: String,
    val duration: Int = 60
)

data class QoDResponse(
    val flowId: String,
    val sessionId: String? = null,
    val duration: Int? = null,
    val qosStatus: String? = null,
    val streamingAllowed: Boolean,
    val fallbackMaxResolution: String? = null,
    val reasonCode: String? = null,
    val correlator: String? = null
)

data class JobStatusResponse(
    val jobId: String,
    val flowId: String,
    val status: String,
    val checksumSha256: String?,
    val durationSeconds: Double?,
    val failureCode: String?
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

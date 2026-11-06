
package com.wegotchu.app.network

import com.google.gson.annotations.SerializedName
import com.wegotchu.app.data.model.TelemetryPayload
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

data class TelemetryResponse(
    val status: String,
    val message: String,
    val device_id: String
)

data class SOSAlertRequest(
    val latitude: Double? = null,
    val longitude: Double? = null,
    @SerializedName("accuracy_meters")
    val accuracyMeters: Double? = null,
    val note: String? = null
)

data class SOSAlertResponse(
    val id: Int,
    val status: String,
    val source: String,
    val latitude: Double?,
    val longitude: Double?,
    @SerializedName("accuracy_meters")
    val accuracyMeters: Double?,
    @SerializedName("created_at")
    val createdAt: String,
    @SerializedName("notification_status")
    val notificationStatus: String
)

data class StartSafetyTimerRequest(
    @SerializedName("trip_id")
    val tripId: String,
    @SerializedName("timer_duration_seconds")
    val timerDurationSeconds: Int
)

data class ExpireSafetyTimerRequest(
    @SerializedName("trip_id")
    val tripId: String
)

data class CompleteSafetyTimerRequest(
    @SerializedName("trip_id")
    val tripId: String
)

data class SafetyTimerResponse(
    val status: String,
    @SerializedName("trip_id")
    val tripId: String,
    @SerializedName("trip_status")
    val tripStatus: String,
    @SerializedName("started_at")
    val startedAt: String? = null,
    @SerializedName("ended_at")
    val endedAt: String? = null,
    @SerializedName("timer_duration_seconds")
    val timerDurationSeconds: Int? = null,
    @SerializedName("timer_expires_at")
    val timerExpiresAt: String? = null
)

interface TelemetryApi {

    @POST("api/v1/telemetry")
    suspend fun sendTelemetry(
        @Header("Authorization") authorization: String,
        @Body payload: TelemetryPayload
    ): Response<TelemetryResponse>

    @POST("api/v1/sos")
    suspend fun createSOSAlert(
        @Header("Authorization") authorization: String,
        @Body payload: SOSAlertRequest
    ): Response<SOSAlertResponse>

    @POST("api/v1/telemetry/trips/start")
    suspend fun startSafetyTimer(
        @Header("Authorization") authorization: String,
        @Body payload: StartSafetyTimerRequest
    ): Response<SafetyTimerResponse>

    @POST("api/v1/telemetry/trips/expire")
    suspend fun expireSafetyTimer(
        @Header("Authorization") authorization: String,
        @Body payload: ExpireSafetyTimerRequest
    ): Response<SafetyTimerResponse>

    @POST("api/v1/telemetry/trips/complete")
    suspend fun completeSafetyTimer(
        @Header("Authorization") authorization: String,
        @Body payload: CompleteSafetyTimerRequest
    ): Response<SafetyTimerResponse>
}

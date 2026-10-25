
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
}

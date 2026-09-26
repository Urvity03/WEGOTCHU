package com.wegotchu.app.network

import com.wegotchu.app.data.model.TelemetryPayload
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

data class TelemetryResponse(
    val status: String,
    val message: String,
    val device_id: String
)

interface TelemetryApi {

    @POST("api/v1/telemetry")
    suspend fun sendTelemetry(
        @Body payload: TelemetryPayload
    ): Response<TelemetryResponse>
}
package com.wegotchu.app.network

import android.util.Log
import com.wegotchu.app.data.model.TelemetryPayload

class TelemetrySender {

    private val api = RetrofitClient.api

    suspend fun send(payload: TelemetryPayload): Boolean {
        return try {

            val response = api.sendTelemetry(payload)

            if (response.isSuccessful) {
                Log.d(
                    "TelemetrySender",
                    "Telemetry sent successfully: ${response.body()}"
                )
                true
            } else {
                Log.e(
                    "TelemetrySender",
                    "Telemetry failed: HTTP ${response.code()} - ${response.errorBody()?.string()}"
                )
                false
            }

        } catch (e: Exception) {

            Log.e(
                "TelemetrySender",
                "Network error while sending telemetry",
                e
            )

            false
        }
    }
}
package com.wegotchu.app.network

import android.util.Base64
import com.google.gson.JsonParser
import com.wegotchu.app.BuildConfig

object AuthTokenProvider {

    fun getToken(): String {
        return BuildConfig.TELEMETRY_JWT
    }

    fun getDeviceId(): String {
        val token = getToken()

        require(token.isNotBlank()) {
            "TELEMETRY_JWT is not configured"
        }

        val parts = token.split(".")

        require(parts.size == 3) {
            "Invalid JWT format"
        }

        val payload = String(
            Base64.decode(
                parts[1],
                Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
            ),
            Charsets.UTF_8
        )

        return JsonParser.parseString(payload)
            .asJsonObject
            .get("sub")
            ?.asString
            ?.takeIf { it.isNotBlank() }
            ?: error("JWT does not contain a valid sub claim")
    }
}
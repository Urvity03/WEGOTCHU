package com.wegotchu.app.safety

import android.content.Context
import java.util.UUID

data class SafetyTimerState(
    val tripId: String,
    val expiresAt: String,
    val durationSeconds: Int
)

class SafetyTimerStorage(context: Context) {

    private val preferences = context.applicationContext
        .getSharedPreferences("safety_timer", Context.MODE_PRIVATE)

    fun save(state: SafetyTimerState) {
        require(runCatching { UUID.fromString(state.tripId) }.isSuccess) {
            "Invalid safety timer trip ID"
        }
        require(state.expiresAt.isNotBlank()) {
            "Safety timer expiry is missing"
        }
        require(state.durationSeconds in 60..86400) {
            "Invalid safety timer duration"
        }

        val saved = preferences.edit()
            .putString("trip_id", state.tripId)
            .putString("expires_at", state.expiresAt)
            .putInt("duration_seconds", state.durationSeconds)
            .commit()

        check(saved) { "Could not persist safety timer state" }
    }

    fun load(): SafetyTimerState? {
        val tripId = preferences.getString("trip_id", null)
        val expiresAt = preferences.getString("expires_at", null)
        val duration = preferences.getInt("duration_seconds", 0)

        if (
            tripId.isNullOrBlank() ||
            expiresAt.isNullOrBlank() ||
            duration !in 60..86400 ||
            runCatching { UUID.fromString(tripId) }.isFailure
        ) {
            return null
        }

        return SafetyTimerState(
            tripId = tripId,
            expiresAt = expiresAt,
            durationSeconds = duration
        )
    }

    fun clear() {
        val cleared = preferences.edit().clear().commit()
        check(cleared) { "Could not clear safety timer state" }
    }
}
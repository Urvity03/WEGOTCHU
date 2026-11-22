package com.wegotchu.app.contacts

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.telephony.SmsManager
import android.util.Log
import androidx.core.content.ContextCompat

object EmergencyDispatcher {

    private const val TAG = "EmergencyDispatcher"

    /**
     * Attempts to send a direct SMS to trusted contacts via Android SmsManager
     * if the SEND_SMS permission has been granted by the user.
     *
     * Returns the count of SMS messages successfully queued for transmission.
     */
    fun dispatchLocalSms(
        context: Context,
        contacts: List<TrustedContact>,
        latitude: Double?,
        longitude: Double?,
        note: String? = null
    ): Int {
        val hasPermission = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.SEND_SMS
        ) == PackageManager.PERMISSION_GRANTED

        if (!hasPermission) {
            Log.d(TAG, "SEND_SMS permission not granted; skipping direct device SMS")
            return 0
        }

        if (contacts.isEmpty()) {
            Log.d(TAG, "No trusted contacts available to dispatch")
            return 0
        }

        val locationText = if (latitude != null && longitude != null) {
            "Location: https://maps.google.com/?q=$latitude,$longitude"
        } else {
            "Location: Unavailable"
        }

        val noteText = if (!note.isNullOrBlank()) " Note: $note" else ""
        val message = "[WEGOTCHU SOS] Emergency alert! I need immediate assistance. $locationText$noteText"

        val smsManager: SmsManager = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            context.getSystemService(SmsManager::class.java)
        } else {
            @Suppress("DEPRECATION")
            SmsManager.getDefault()
        }

        var sentCount = 0
        for (contact in contacts) {
            try {
                val phone = contact.phoneNumber.trim()
                if (phone.isNotBlank()) {
                    val parts = smsManager.divideMessage(message)
                    if (parts.size > 1) {
                        smsManager.sendMultipartTextMessage(phone, null, parts, null, null)
                    } else {
                        smsManager.sendTextMessage(phone, null, message, null, null)
                    }
                    sentCount++
                    Log.d(TAG, "Queued direct SMS to ${contact.name} ($phone)")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send direct SMS to ${contact.name}", e)
            }
        }

        return sentCount
    }
}

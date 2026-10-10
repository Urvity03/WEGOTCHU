package com.wegotchu.app.network

import com.wegotchu.app.BuildConfig

object DeviceIdentity {

    fun getDeviceId(): String {
        return BuildConfig.TELEMETRY_DEVICE_ID
    }
}
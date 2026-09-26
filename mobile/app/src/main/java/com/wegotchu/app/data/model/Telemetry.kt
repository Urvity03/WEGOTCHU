package com.wegotchu.app.data.model

import com.google.gson.annotations.SerializedName

data class Location(

    val latitude: Double,

    val longitude: Double,

    @SerializedName("altitude_meters")
    val altitudeMeters: Double?,

    @SerializedName("accuracy_meters")
    val accuracyMeters: Double
)

data class Accelerometer(

    val x: Double,

    val y: Double,

    val z: Double
)

data class Gyroscope(

    val x: Double,

    val y: Double,

    val z: Double
)

data class TelemetryPayload(

    val version: String,

    @SerializedName("device_id")
    val deviceId: String,

    val timestamp: String,

    val location: Location,

    @SerializedName("speed_mps")
    val speedMps: Double?,

    @SerializedName("bearing_degrees")
    val bearingDegrees: Double?,

    val accelerometer: Accelerometer,

    val gyroscope: Gyroscope,

    @SerializedName("battery_level")
    val batteryLevel: Double,

    @SerializedName("network_status")
    val networkStatus: String
)
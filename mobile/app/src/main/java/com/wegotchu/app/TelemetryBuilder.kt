package com.wegotchu.app

import android.util.Log
import com.wegotchu.app.data.model.Accelerometer
import com.wegotchu.app.data.model.Gyroscope
import com.wegotchu.app.data.model.Location
import com.wegotchu.app.data.model.TelemetryPayload
import com.wegotchu.app.location.LocationCollector
import com.wegotchu.app.sensors.SensorCollector
import java.time.Instant

class TelemetryBuilder(
    private val locationCollector: LocationCollector,
    private val sensorCollector: SensorCollector,
    private val batteryCollector: BatteryCollector,
    private val networkCollector: NetworkCollector
) {

    fun build(): TelemetryPayload? {

        val location = locationCollector.latestLocation()

        if (location == null) {
            Log.d(
                "TelemetryBuilder",
                "Waiting for location data..."
            )
            return null
        }

        val imuSnapshot = sensorCollector.snapshot()

        val accelerometer = imuSnapshot.accelerometer

        if (accelerometer == null) {
            Log.d(
                "TelemetryBuilder",
                "Waiting for accelerometer data..."
            )
            return null
        }

        val gyroscope = imuSnapshot.gyroscope

        if (gyroscope == null) {
            Log.d(
                "TelemetryBuilder",
                "Waiting for gyroscope data..."
            )
            return null
        }

        val payload = TelemetryPayload(
            version = "0.1",

            // Synthetic ID for prototype/testing.
            // Do not replace with a real personal identifier yet.
            deviceId = "usr_dev_example",

            timestamp = Instant.now().toString(),

            location = Location(
                latitude = location.latitude,
                longitude = location.longitude,
                altitudeMeters = location.altitudeMeters,
                accuracyMeters = location.accuracyMeters.toDouble()
            ),

            speedMps = location.speedMps?.toDouble(),

            bearingDegrees = location.bearingDegrees?.toDouble(),

            accelerometer = Accelerometer(
                x = accelerometer.x.toDouble(),
                y = accelerometer.y.toDouble(),
                z = accelerometer.z.toDouble()
            ),

            gyroscope = Gyroscope(
                x = gyroscope.x.toDouble(),
                y = gyroscope.y.toDouble(),
                z = gyroscope.z.toDouble()
            ),

            batteryLevel = batteryCollector.getBatteryLevel(),

            networkStatus = networkCollector.getNetworkStatus()
        )

        Log.d(
            "TelemetryBuilder",
            "Telemetry payload created successfully"
        )

        return payload
    }
}
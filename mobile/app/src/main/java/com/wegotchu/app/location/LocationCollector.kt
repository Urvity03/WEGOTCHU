package com.wegotchu.app.location

import android.annotation.SuppressLint
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Looper
import android.util.Log

data class LocationSample(
    val timestampMillis: Long,
    val latitude: Double,
    val longitude: Double,
    val altitudeMeters: Double?,
    val accuracyMeters: Float,
    val speedMps: Float?,
    val bearingDegrees: Float?
)

class LocationCollector(
    private val locationManager: LocationManager
) {

    private var latestLocation: LocationSample? = null

    private val locationListener = object : LocationListener {

        override fun onLocationChanged(location: Location) {
            updateLatestLocation(location)
        }
    }

    @SuppressLint("MissingPermission")
    fun start() {

        // Try to use an existing location immediately.
        val lastGpsLocation =
            if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                locationManager.getLastKnownLocation(
                    LocationManager.GPS_PROVIDER
                )
            } else {
                null
            }

        val lastNetworkLocation =
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                locationManager.getLastKnownLocation(
                    LocationManager.NETWORK_PROVIDER
                )
            } else {
                null
            }

        // Use whichever available location is newer.
        val lastKnownLocation = listOfNotNull(
            lastGpsLocation,
            lastNetworkLocation
        ).maxByOrNull { it.time }

        if (lastKnownLocation != null) {
            updateLatestLocation(lastKnownLocation)

            Log.d(
                "LocationCollector",
                "Using last known location"
            )
        }

        if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
            locationManager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                1000L,
                0f,
                locationListener,
                Looper.getMainLooper()
            )
        }

        if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
            locationManager.requestLocationUpdates(
                LocationManager.NETWORK_PROVIDER,
                1000L,
                0f,
                locationListener,
                Looper.getMainLooper()
            )
        }

        Log.d(
            "LocationCollector",
            "Location collection started"
        )
    }

    fun stop() {
        locationManager.removeUpdates(locationListener)

        Log.d(
            "LocationCollector",
            "Location collection stopped"
        )
    }

    fun latestLocation(): LocationSample? {
        return latestLocation
    }

    private fun updateLatestLocation(location: Location) {

        val sample = LocationSample(
            timestampMillis = location.time,
            latitude = location.latitude,
            longitude = location.longitude,
            altitudeMeters =
                if (location.hasAltitude()) {
                    location.altitude
                } else {
                    null
                },
            accuracyMeters = location.accuracy,
            speedMps =
                if (location.hasSpeed()) {
                    location.speed
                } else {
                    null
                },
            bearingDegrees =
                if (location.hasBearing()) {
                    location.bearing
                } else {
                    null
                }
        )

        latestLocation = sample

        Log.d(
            "LocationCollector",
            "Location: lat=${sample.latitude}, " +
                    "lon=${sample.longitude}, " +
                    "accuracy=${sample.accuracyMeters}m, " +
                    "speed=${sample.speedMps}"
        )
    }
}
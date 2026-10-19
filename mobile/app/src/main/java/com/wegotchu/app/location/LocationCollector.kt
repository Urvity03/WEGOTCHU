package com.wegotchu.app.location

import android.Manifest
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
    private val locationManager: LocationManager,
    private val permissionChecker: (String) -> Boolean
) {
    private var latestLocation: LocationSample? = null
    private var isCollecting = false

    private val locationListener = object : LocationListener {
        override fun onLocationChanged(location: Location) {
            if (shouldReplaceCurrentLocation(location)) {
                updateLatestLocation(location)
                Log.d(
                    "LocationCollector",
                    "Accepted location: accuracy=${location.accuracy}m"
                )
            } else {
                Log.d(
                    "LocationCollector",
                    "Ignored poorer/stale location: accuracy=${location.accuracy}m"
                )
            }
        }
    }

    @SuppressLint("MissingPermission")
    fun start() {
        if (isCollecting) {
            Log.d("LocationCollector", "Location collection is already running")
            return
        }

        val fineLocationGranted =
            permissionChecker(Manifest.permission.ACCESS_FINE_LOCATION)
        val coarseLocationGranted =
            permissionChecker(Manifest.permission.ACCESS_COARSE_LOCATION)

        if (!fineLocationGranted && !coarseLocationGranted) {
            Log.e("LocationCollector", "Location permission is not granted")
            return
        }

        var providerStarted = false

        if (
            shouldUseGps(fineLocationGranted) &&
            locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)
        ) {
            val lastGpsLocation =
                locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER)

            if (
                lastGpsLocation != null &&
                shouldReplaceCurrentLocation(lastGpsLocation)
            ) {
                updateLatestLocation(lastGpsLocation)
            }

            locationManager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                1000L,
                0f,
                locationListener,
                Looper.getMainLooper()
            )
            providerStarted = true
        }

        if (
            coarseLocationGranted &&
            locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
        ) {
            val lastNetworkLocation =
                locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)

            if (
                lastNetworkLocation != null &&
                shouldReplaceCurrentLocation(lastNetworkLocation)
            ) {
                updateLatestLocation(lastNetworkLocation)
            }

            locationManager.requestLocationUpdates(
                LocationManager.NETWORK_PROVIDER,
                1000L,
                0f,
                locationListener,
                Looper.getMainLooper()
            )
            providerStarted = true
        }

        isCollecting = providerStarted
        Log.d(
            "LocationCollector",
            if (providerStarted) {
                "Location collection started"
            } else {
                "No eligible location provider is enabled"
            }
        )
    }

    fun stop() {
        locationManager.removeUpdates(locationListener)
        isCollecting = false
        Log.d("LocationCollector", "Location collection stopped")
    }

    fun latestLocation(): LocationSample? = latestLocation

    private fun updateLatestLocation(location: Location) {
        latestLocation = LocationSample(
            timestampMillis = location.time,
            latitude = location.latitude,
            longitude = location.longitude,
            altitudeMeters = if (location.hasAltitude()) location.altitude else null,
            accuracyMeters = location.accuracy,
            speedMps = if (location.hasSpeed()) location.speed else null,
            bearingDegrees = if (location.hasBearing()) location.bearing else null
        )
    }
    private fun shouldReplaceCurrentLocation(location: Location): Boolean =
        shouldReplaceCurrentLocation(
            currentTimestampMillis = latestLocation?.timestampMillis,
            currentAccuracyMeters = latestLocation?.accuracyMeters,
            newTimestampMillis = location.time,
            newAccuracyMeters = location.accuracy
        )

    companion object {
        internal fun shouldUseGps(fineLocationGranted: Boolean): Boolean =
            fineLocationGranted

        internal fun shouldReplaceCurrentLocation(
            currentTimestampMillis: Long?,
            currentAccuracyMeters: Float?,
            newTimestampMillis: Long,
            newAccuracyMeters: Float
        ): Boolean {
            if (currentTimestampMillis == null || currentAccuracyMeters == null) {
                return true
            }

            val isNewer = newTimestampMillis > currentTimestampMillis
            val isMoreAccurate = newAccuracyMeters < currentAccuracyMeters

            return isNewer && isMoreAccurate
        }
    }
}

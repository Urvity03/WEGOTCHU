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

    private val locationListener = object : LocationListener {

        override fun onLocationChanged(location: Location) {
            updateLatestLocation(location)
        }
    }

    @SuppressLint("MissingPermission")
    fun start() {

        val fineLocationGranted =
            permissionChecker(Manifest.permission.ACCESS_FINE_LOCATION)

        val coarseLocationGranted =
            permissionChecker(Manifest.permission.ACCESS_COARSE_LOCATION)

        if (!fineLocationGranted && !coarseLocationGranted) {
            Log.e(
                "LocationCollector",
                "Location permission is not granted"
            )
            return
        }

        // GPS requires fine location permission.
        if (
            shouldUseGps(fineLocationGranted) &&
            locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)
        ) {
            val lastGpsLocation =
                locationManager.getLastKnownLocation(
                    LocationManager.GPS_PROVIDER
                )

            if (lastGpsLocation != null) {
                updateLatestLocation(lastGpsLocation)
            }

            locationManager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                1000L,
                0f,
                locationListener,
                Looper.getMainLooper()
            )
        }

        // Network provider can be used with coarse location.
        if (
            coarseLocationGranted &&
            locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
        ) {
            val lastNetworkLocation =
                locationManager.getLastKnownLocation(
                    LocationManager.NETWORK_PROVIDER
                )

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
    }
    private fun shouldReplaceCurrentLocation(location: Location): Boolean {

        val current = latestLocation ?: return true

        val isNewer = location.time > current.timestampMillis

        val isMoreAccurate =
            location.accuracy < current.accuracyMeters

        return isNewer && isMoreAccurate
    }
    companion object {
        internal fun shouldUseGps(
            fineLocationGranted: Boolean
        ): Boolean {
            return fineLocationGranted
        }
    }
}
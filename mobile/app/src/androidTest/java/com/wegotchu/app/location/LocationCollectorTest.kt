package com.wegotchu.app.location

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LocationCollectorTest {

    @Test
    fun coarseOnlyPermissionDoesNotAllowGps() {
        assertFalse(LocationCollector.shouldUseGps(false))
    }

    @Test
    fun fineLocationPermissionAllowsGps() {
        assertTrue(LocationCollector.shouldUseGps(true))
    }

    @Test
    fun newerLocationWithBetterAccuracyIsAccepted() {
        assertTrue(
            LocationCollector.shouldReplaceCurrentLocation(
                currentTimestampMillis = 1000L,
                currentAccuracyMeters = 20f,
                newTimestampMillis = 2000L,
                newAccuracyMeters = 10f
            )
        )
    }

    @Test
    fun olderLocationIsRejected() {
        assertFalse(
            LocationCollector.shouldReplaceCurrentLocation(
                currentTimestampMillis = 2000L,
                currentAccuracyMeters = 20f,
                newTimestampMillis = 1000L,
                newAccuracyMeters = 10f
            )
        )
    }

    @Test
    fun newerButLessAccurateLocationIsRejected() {
        assertFalse(
            LocationCollector.shouldReplaceCurrentLocation(
                currentTimestampMillis = 1000L,
                currentAccuracyMeters = 10f,
                newTimestampMillis = 2000L,
                newAccuracyMeters = 20f
            )
        )
    }
}

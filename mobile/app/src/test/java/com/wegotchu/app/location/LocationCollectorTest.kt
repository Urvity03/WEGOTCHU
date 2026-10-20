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
    fun consecutiveNewerLocationsWithVaryingAccuracyAreAccepted() {
        // First reading: 4 m accuracy.
        assertTrue(
            LocationCollector.shouldReplaceCurrentLocation(
                currentTimestampMillis = 1000L,
                currentAccuracyMeters = 4f,
                newTimestampMillis = 2000L,
                newAccuracyMeters = 8f
            )
        )

        // Next reading: accuracy improves to 5 m.
        assertTrue(
            LocationCollector.shouldReplaceCurrentLocation(
                currentTimestampMillis = 2000L,
                currentAccuracyMeters = 8f,
                newTimestampMillis = 3000L,
                newAccuracyMeters = 5f
            )
        )

        // Next reading: accuracy fluctuates to 10 m.
        assertTrue(
            LocationCollector.shouldReplaceCurrentLocation(
                currentTimestampMillis = 3000L,
                currentAccuracyMeters = 5f,
                newTimestampMillis = 4000L,
                newAccuracyMeters = 10f
            )
        )
    }
}

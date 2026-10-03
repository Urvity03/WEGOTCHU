package com.wegotchu.app.location

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LocationCollectorTest {

    @Test
    fun coarseOnlyPermissionDoesNotAllowGps() {
        val fineLocationGranted = false

        val shouldUseGps =
            LocationCollector.shouldUseGps(fineLocationGranted)

        assertFalse(shouldUseGps)
    }

    @Test
    fun fineLocationPermissionAllowsGps() {
        val fineLocationGranted = true

        val shouldUseGps =
            LocationCollector.shouldUseGps(fineLocationGranted)

        assertTrue(shouldUseGps)
    }
}
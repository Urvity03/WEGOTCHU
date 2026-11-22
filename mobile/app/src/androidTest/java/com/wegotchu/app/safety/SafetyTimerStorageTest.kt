package com.wegotchu.app.safety

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SafetyTimerStorageTest {

    private lateinit var storage: SafetyTimerStorage

    @Before
    fun setUp() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        storage = SafetyTimerStorage(context)
        storage.clear()
    }

    @Test
    fun saveAndLoadTimerState_success() {
        val state = SafetyTimerState(
            tripId = "trip-test-12345",
            expiresAt = "2026-11-22T14:00:00Z",
            durationSeconds = 600
        )
        storage.save(state)

        val loaded = storage.load()
        assertNotNull(loaded)
        assertEquals("trip-test-12345", loaded?.tripId)
        assertEquals("2026-11-22T14:00:00Z", loaded?.expiresAt)
        assertEquals(600, loaded?.durationSeconds)
    }

    @Test
    fun clearTimerState_clearsStorage() {
        val state = SafetyTimerState(
            tripId = "trip-to-clear",
            expiresAt = "2026-11-22T14:00:00Z",
            durationSeconds = 300
        )
        storage.save(state)
        assertNotNull(storage.load())

        storage.clear()
        assertNull(storage.load())
    }

    @Test(expected = IllegalArgumentException::class)
    fun saveTimerState_invalidDuration_throws() {
        val invalid = SafetyTimerState(
            tripId = "trip-invalid-duration",
            expiresAt = "2026-11-22T14:00:00Z",
            durationSeconds = 10 // must be >= 60
        )
        storage.save(invalid)
    }
}

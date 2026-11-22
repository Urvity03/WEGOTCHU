package com.wegotchu.app.safety

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class SafetyPinStorageTest {

    private lateinit var storage: SafetyPinStorage

    @Before
    fun setUp() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val file = File(context.filesDir, "safety_pin.enc")
        if (file.exists()) {
            file.delete()
        }
        storage = SafetyPinStorage(context)
    }

    @Test
    fun unconfiguredPin_returnsNotConfigured() {
        assertFalse(storage.isPinConfigured())
        val result = storage.verifyPin("1234")
        assertEquals(SafetyPinStorage.VerificationResult.NOT_CONFIGURED, result)
    }

    @Test
    fun setupAndVerifyCorrectPin_returnsSuccess() {
        storage.setupPin("4321")
        assertTrue(storage.isPinConfigured())

        val result = storage.verifyPin("4321")
        assertEquals(SafetyPinStorage.VerificationResult.SUCCESS, result)
    }

    @Test
    fun verifyWrongPin_returnsIncorrect() {
        storage.setupPin("9999")
        val result = storage.verifyPin("1111")
        assertEquals(SafetyPinStorage.VerificationResult.INCORRECT, result)
    }

    @Test
    fun repeatedWrongPinAttempts_triggersLockout() {
        storage.setupPin("5555")

        repeat(4) {
            val result = storage.verifyPin("0000")
            assertEquals(SafetyPinStorage.VerificationResult.INCORRECT, result)
        }

        // 5th attempt locks out
        val lockoutResult = storage.verifyPin("0000")
        assertEquals(SafetyPinStorage.VerificationResult.LOCKED_OUT, lockoutResult)

        // Subsequent attempt is still locked out
        val lockedResult = storage.verifyPin("5555")
        assertEquals(SafetyPinStorage.VerificationResult.LOCKED_OUT, lockedResult)
    }
}

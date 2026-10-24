package com.wegotchu.app.contacts

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ContactValidatorTest {

    @Test
    fun validNamesAreAccepted() {
        assertTrue(ContactValidator.validateName("Alice"))
        assertTrue(ContactValidator.validateName("  Shubhi Gupta  "))
    }

    @Test
    fun blankOrExcessivelyLongNamesAreRejected() {
        assertFalse(ContactValidator.validateName("   "))
        assertFalse(ContactValidator.validateName("A".repeat(101)))
    }

    @Test
    fun validPhoneNumbersAreAccepted() {
        assertTrue(ContactValidator.validatePhoneNumber("+91 98765-43210"))
        assertTrue(ContactValidator.validatePhoneNumber("(212) 555-1234"))
        assertTrue(ContactValidator.validatePhoneNumber("9876543"))
    }

    @Test
    fun invalidPhoneNumbersAreRejected() {
        assertFalse(ContactValidator.validatePhoneNumber(""))
        assertFalse(ContactValidator.validatePhoneNumber("12345"))
        assertFalse(ContactValidator.validatePhoneNumber("phone12345"))
        assertFalse(ContactValidator.validatePhoneNumber("+1234567890123456"))
    }

    @Test
    fun phoneNumbersCanBeNormalized() {
        assertEquals("+919876543210",
            ContactValidator.normalizePhoneNumber("+91 98765-43210"))
        assertEquals("2125551234",
            ContactValidator.normalizePhoneNumber("(212) 555-1234"))
    }
}

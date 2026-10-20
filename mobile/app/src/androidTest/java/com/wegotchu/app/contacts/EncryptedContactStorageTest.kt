package com.wegotchu.app.contacts

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class EncryptedContactStorageTest {

    private lateinit var storage: EncryptedContactStorage

    private val plaintext =
        """[{"id":"test-1","name":"Trusted Person","phoneNumber":"+919876543210"}]"""

    @Before
    fun setUp() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        storage = EncryptedContactStorage(context)
        storage.delete()
    }

    @Test
    fun savedDataCanBeLoaded() {
        storage.save(plaintext)
        assertEquals(plaintext, storage.load())
    }
    @Test
    fun savingAgainReplacesPreviouslySavedData() {
        val firstValue = """[{"id":"first","name":"First Person","phoneNumber":"9876543210"}]"""
        val secondValue = """[{"id":"second","name":"Second Person","phoneNumber":"9123456780"}]"""

        storage.save(firstValue)
        storage.save(secondValue)

        assertEquals(secondValue, storage.load())
    }

    @Test
    fun storedFileDoesNotContainPlaintext() {
        storage.save(plaintext)

        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val stored = context.filesDir.resolve("trusted_contacts.enc")
            .readText(Charsets.UTF_8)

        assertFalse(stored.contains("Trusted Person"))
        assertFalse(stored.contains("+919876543210"))
    }

    @Test
    fun deleteRemovesSavedData() {
        storage.save(plaintext)
        storage.delete()

        assertNull(storage.load())

        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertFalse(context.filesDir.resolve("trusted_contacts.enc").exists())
    }

    @Test
    fun missingFileReturnsNull() {
        assertNull(storage.load())
    }
}

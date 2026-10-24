
package com.wegotchu.app.contacts

import android.util.Base64
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.security.KeyStore

@RunWith(AndroidJUnit4::class)
class EncryptedContactStorageTest {

    private lateinit var storage: EncryptedContactStorage

    private val plaintext =
        """[{"id":"test-1","name":"Trusted Person","phoneNumber":"+919876543210"}]"""

    @Before
    fun setUp() {
        val context =
            InstrumentationRegistry.getInstrumentation().targetContext
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
        val firstValue =
            """[{"id":"first","name":"First Person","phoneNumber":"9876543210"}]"""
        val secondValue =
            """[{"id":"second","name":"Second Person","phoneNumber":"9123456780"}]"""

        storage.save(firstValue)
        storage.save(secondValue)

        assertEquals(secondValue, storage.load())
    }

    @Test
    fun storedFileDoesNotContainPlaintext() {
        storage.save(plaintext)

        val context =
            InstrumentationRegistry.getInstrumentation().targetContext
        val stored = context.filesDir
            .resolve("trusted_contacts.enc")
            .readText(Charsets.UTF_8)

        assertFalse(stored.contains("Trusted Person"))
        assertFalse(stored.contains("+919876543210"))
    }

    @Test
    fun deleteRemovesSavedData() {
        storage.save(plaintext)
        storage.delete()

        assertNull(storage.load())

        val context =
            InstrumentationRegistry.getInstrumentation().targetContext
        assertFalse(
            context.filesDir.resolve("trusted_contacts.enc").exists()
        )
    }

    @Test
    fun missingFileReturnsNull() {
        assertNull(storage.load())
    }

    @Test
    fun tamperedCiphertextFailsAuthenticationAndPreservesFile() {
        storage.save(plaintext)

        val context =
            InstrumentationRegistry.getInstrumentation().targetContext
        val file = context.filesDir.resolve("trusted_contacts.enc")
        val parts = file.readText(Charsets.UTF_8).split(":")

        assertEquals("v1", parts[0])
        val ciphertext = Base64.decode(parts[2], Base64.NO_WRAP)
        ciphertext[0] = (ciphertext[0].toInt() xor 1).toByte()

        file.writeText(
            listOf(
                parts[0],
                parts[1],
                Base64.encodeToString(ciphertext, Base64.NO_WRAP)
            ).joinToString(":"),
            Charsets.UTF_8
        )

        try {
            storage.load()
            fail("Tampered ciphertext must fail AES-GCM authentication")
        } catch (expected: EncryptedContactStorageException) {
            assertTrue(expected.cause != null)
        }

        assertTrue("Corrupted file should be preserved for recovery", file.exists())
    }

    @Test
    fun missingKeystoreKeyFailsWithoutDeletingEncryptedFile() {
        storage.save(plaintext)

        val context =
            InstrumentationRegistry.getInstrumentation().targetContext
        val file = context.filesDir.resolve("trusted_contacts.enc")
        assertTrue(file.exists())

        val keyStore = KeyStore.getInstance("AndroidKeyStore")
        keyStore.load(null)
        keyStore.deleteEntry("wegotchu_trusted_contacts_key")

        try {
            storage.load()
            fail("Loading should fail when the encryption key is missing")
        } catch (expected: EncryptedContactStorageException) {
            assertTrue(expected.cause != null)
        }

        assertTrue("Encrypted file should be preserved", file.exists())
    }
}

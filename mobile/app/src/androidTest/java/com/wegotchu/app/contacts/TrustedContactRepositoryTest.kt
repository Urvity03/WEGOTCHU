
package com.wegotchu.app.contacts

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TrustedContactRepositoryTest {

    private lateinit var storage: EncryptedContactStorage
    private lateinit var repository: TrustedContactRepository

    private val validContact = TrustedContact(
        id = "test-2",
        name = "Another Person",
        phoneNumber = "+919876543211"
    )

    @Before
    fun setUp() {
        val context =
            InstrumentationRegistry.getInstrumentation().targetContext

        storage = EncryptedContactStorage(context)
        storage.delete()
        repository = TrustedContactRepository(context)
    }

    @Test
    fun malformedStoredJsonFailsWithoutOverwritingData() {
        storage.save("not-json")

        try {
            repository.getAll()
            fail("Invalid stored JSON should fail")
        } catch (exception: TrustedContactRepositoryException) {
            assertEquals(
                "Stored trusted contacts are invalid",
                exception.message
            )
        }

        assertEquals("not-json", storage.load())
    }

    @Test
    fun addingContactDoesNotOverwriteInvalidStoredJson() {
        storage.save("not-json")

        try {
            repository.add(validContact)
            fail("Adding to invalid storage should fail")
        } catch (exception: TrustedContactRepositoryException) {
            // Expected: existing data must not be overwritten.
        }

        assertEquals("not-json", storage.load())
    }

    @Test
    fun removingContactDoesNotOverwriteInvalidStoredJson() {
        storage.save("not-json")

        try {
            repository.remove("test-1")
            fail("Removing from invalid storage should fail")
        } catch (exception: TrustedContactRepositoryException) {
            // Expected: existing data must not be overwritten.
        }

        assertEquals("not-json", storage.load())
    }
}

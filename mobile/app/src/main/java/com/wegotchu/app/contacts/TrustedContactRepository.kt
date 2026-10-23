
package com.wegotchu.app.contacts

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

class TrustedContactRepository(context: Context) {

    private val storage = EncryptedContactStorage(context)

    @Synchronized
    fun getAll(): List<TrustedContact> {
        val json = storage.load() ?: return emptyList()

        return try {
            val array = JSONArray(json)

            (0 until array.length()).map { index ->
                val item = array.getJSONObject(index)

                TrustedContact(
                    id = item.getString("id"),
                    name = item.getString("name"),
                    phoneNumber = item.getString("phoneNumber")
                )
            }
        } catch (exception: Exception) {
            throw TrustedContactRepositoryException(
                "Stored trusted contacts are invalid",
                exception
            )
        }
    }

    @Synchronized
    fun add(contact: TrustedContact): List<TrustedContact> {
        require(contact.id.isNotBlank()) {
            "Invalid contact ID"
        }
        require(ContactValidator.validateName(contact.name)) {
            "Invalid contact name"
        }
        require(ContactValidator.validatePhoneNumber(contact.phoneNumber)) {
            "Invalid phone number"
        }

        // Storage errors must propagate. Never treat corrupted data as empty.
        val current = getAll()
        val normalizedPhone =
            ContactValidator.normalizePhoneNumber(contact.phoneNumber)

        require(
            current.none {
                it.id == contact.id ||
                    ContactValidator.normalizePhoneNumber(it.phoneNumber) ==
                    normalizedPhone
            }
        ) {
            "This contact is already saved"
        }

        val updated = current + contact.copy(
            name = contact.name.trim(),
            phoneNumber = normalizedPhone
        )

        persist(updated)
        return updated
    }

    @Synchronized
    fun remove(contactId: String): List<TrustedContact> {
        val updated = getAll().filterNot { it.id == contactId }
        persist(updated)
        return updated
    }

    private fun persist(contacts: List<TrustedContact>) {
        val array = JSONArray()

        contacts.forEach { contact ->
            array.put(
                JSONObject()
                    .put("id", contact.id)
                    .put("name", contact.name)
                    .put("phoneNumber", contact.phoneNumber)
            )
        }

        storage.save(array.toString())
    }
}

class TrustedContactRepositoryException(
    message: String,
    cause: Throwable? = null
) : IllegalStateException(message, cause)

package com.wegotchu.app.contacts

import android.content.ContentResolver
import android.content.Context
import android.net.Uri
import android.provider.ContactsContract

object TrustedContactPicker {

    fun readContact(
        context: Context,
        contactUri: Uri
    ): TrustedContact? {
        val resolver = context.contentResolver

        val contact = resolver.query(
            contactUri,
            arrayOf(
                ContactsContract.Contacts._ID,
                ContactsContract.Contacts.DISPLAY_NAME
            ),
            null,
            null,
            null
        )?.use { cursor ->
            if (!cursor.moveToFirst()) return null

            val id = cursor.getString(0) ?: return null
            val name = cursor.getString(1) ?: return null
            id to name
        } ?: return null

        val (contactId, name) = contact

        val phoneNumber = resolver.query(
            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
            arrayOf(ContactsContract.CommonDataKinds.Phone.NUMBER),
            "${ContactsContract.CommonDataKinds.Phone.CONTACT_ID} = ?",
            arrayOf(contactId),
            null
        )?.use { cursor ->
            if (cursor.moveToFirst()) cursor.getString(0) else null
        } ?: return null

        if (!ContactValidator.validateName(name)) return null
        if (!ContactValidator.validatePhoneNumber(phoneNumber)) return null

        return TrustedContact(
            id = contactId,
            name = name.trim(),
            phoneNumber = ContactValidator.normalizePhoneNumber(phoneNumber)
        )
    }
}

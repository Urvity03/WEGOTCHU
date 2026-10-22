
package com.wegotchu.app.contacts

import android.content.Context
import android.net.Uri
import android.provider.ContactsContract

object TrustedContactPicker {

    fun readContact(
        context: Context,
        phoneUri: Uri
    ): TrustedContact? {
        val projection = arrayOf(
            ContactsContract.CommonDataKinds.Phone.CONTACT_ID,
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
            ContactsContract.CommonDataKinds.Phone.NUMBER
        )

        return context.contentResolver.query(
            phoneUri,
            projection,
            null,
            null,
            null
        )?.use { cursor ->
            if (!cursor.moveToFirst()) return null

            val idIndex = cursor.getColumnIndexOrThrow(
                ContactsContract.CommonDataKinds.Phone.CONTACT_ID
            )
            val nameIndex = cursor.getColumnIndexOrThrow(
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME
            )
            val numberIndex = cursor.getColumnIndexOrThrow(
                ContactsContract.CommonDataKinds.Phone.NUMBER
            )

            val id = cursor.getString(idIndex) ?: return null
            val name = cursor.getString(nameIndex) ?: return null
            val number = cursor.getString(numberIndex) ?: return null

            if (!ContactValidator.validateName(name)) return null
            if (!ContactValidator.validatePhoneNumber(number)) return null

            TrustedContact(
                id = id,
                name = name.trim(),
                phoneNumber = ContactValidator.normalizePhoneNumber(number)
            )
        }
    }
}

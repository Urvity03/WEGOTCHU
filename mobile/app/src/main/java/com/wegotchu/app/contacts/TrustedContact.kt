package com.wegotchu.app.contacts

/**
 * Represents one trusted contact selected by the user.
 *
 * The phone number should be validated before saving.
 */
data class TrustedContact(
    val id: String,
    val name: String,
    val phoneNumber: String
)

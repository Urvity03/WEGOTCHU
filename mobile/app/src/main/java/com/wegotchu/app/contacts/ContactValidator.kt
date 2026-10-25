package com.wegotchu.app.contacts

object ContactValidator {

    fun validateName(name: String): Boolean {
        return name.trim().isNotEmpty() && name.trim().length <= 100
    }

    /**
     * Accepts 7–15 digits, optionally prefixed with +.
     * Spaces, parentheses, dots, and hyphens are allowed as separators.
     */
    fun validatePhoneNumber(phoneNumber: String): Boolean {
        val normalized = phoneNumber.trim()

        if (normalized.isEmpty()) return false
        if (!normalized.matches(Regex("""\+?[0-9().\s-]+"""))) return false

        val digits = normalized.filter { it.isDigit() }
        return digits.length in 7..15
    }

    fun normalizePhoneNumber(phoneNumber: String): String {
        require(validatePhoneNumber(phoneNumber)) {
            "Invalid phone number"
        }

        val trimmed = phoneNumber.trim()
        val digits = trimmed.filter { it.isDigit() }
        return (if (trimmed.startsWith("+")) "+" else "") + digits
    }
}

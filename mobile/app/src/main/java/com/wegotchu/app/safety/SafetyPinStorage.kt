
package com.wegotchu.app.safety

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.io.File
import java.io.IOException
import java.security.KeyStore
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec

class SafetyPinStorage(context: Context) {

    private val appContext = context.applicationContext

    private val storageFile =
        File(appContext.filesDir, "safety_pin.enc")

    private val random = SecureRandom()

    enum class VerificationResult {
        SUCCESS,
        INCORRECT,
        LOCKED_OUT,
        NOT_CONFIGURED
    }

    private data class PinRecord(
        val salt: String,
        val hash: String,
        val attempts: Int,
        val lockoutUntil: Long
    )

    @Synchronized
    fun setupPin(pin: String) {
        require(pin.matches(Regex("\\d{4,8}"))) {
            "PIN must contain 4 to 8 digits"
        }

        val salt = ByteArray(16).also(random::nextBytes)
        val hash = deriveHash(pin, salt)

        saveRecord(
            PinRecord(
                salt = encode(salt),
                hash = encode(hash),
                attempts = 0,
                lockoutUntil = 0L
            )
        )
    }

    @Synchronized
    fun verifyPin(pin: String): VerificationResult {
        if (!pin.matches(Regex("\\d{4,8}"))) {
            return VerificationResult.INCORRECT
        }

        val record = loadRecord()
            ?: return VerificationResult.NOT_CONFIGURED

        val now = System.currentTimeMillis()

        if (now < record.lockoutUntil) {
            return VerificationResult.LOCKED_OUT
        }

        val salt = decode(record.salt)
        val expectedHash = decode(record.hash)
        val actualHash = deriveHash(pin, salt)

        if (java.security.MessageDigest.isEqual(
                expectedHash,
                actualHash
            )
        ) {
            saveRecord(record.copy(attempts = 0, lockoutUntil = 0L))
            return VerificationResult.SUCCESS
        }

        val attempts = record.attempts + 1

        val updatedRecord = if (attempts >= MAX_ATTEMPTS) {
            record.copy(
                attempts = 0,
                lockoutUntil = now + LOCKOUT_DURATION_MS
            )
        } else {
            record.copy(attempts = attempts)
        }

        saveRecord(updatedRecord)

        return if (attempts >= MAX_ATTEMPTS) {
            VerificationResult.LOCKED_OUT
        } else {
            VerificationResult.INCORRECT
        }
    }

    @Synchronized
    fun isPinConfigured(): Boolean = loadRecord() != null

    private fun deriveHash(pin: String, salt: ByteArray): ByteArray {
        val spec = PBEKeySpec(
            pin.toCharArray(),
            salt,
            PBKDF2_ITERATIONS,
            HASH_LENGTH_BITS
        )

        return try {
            SecretKeyFactory
                .getInstance("PBKDF2WithHmacSHA256")
                .generateSecret(spec)
                .encoded
        } finally {
            spec.clearPassword()
        }
    }

    private fun saveRecord(record: PinRecord) {
        val plaintext = listOf(
            record.salt,
            record.hash,
            record.attempts.toString(),
            record.lockoutUntil.toString()
        ).joinToString(":")

        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())

        val encrypted = cipher.doFinal(
            plaintext.toByteArray(Charsets.UTF_8)
        )

        val payload = listOf(
            encode(cipher.iv),
            encode(encrypted)
        ).joinToString(":")

        val tempFile = File(
            appContext.filesDir,
            "safety_pin.enc.tmp"
        )

        try {
            tempFile.writeText(payload, Charsets.UTF_8)

            if (!tempFile.renameTo(storageFile)) {
                throw IOException("Could not save safety PIN")
            }
        } catch (exception: Exception) {
            tempFile.delete()
            throw IOException("Could not save safety PIN securely", exception)
        }
    }

    private fun loadRecord(): PinRecord? {
        if (!storageFile.exists()) return null

        try {
            val parts = storageFile.readText(Charsets.UTF_8).split(":")

            require(parts.size == 2) {
                "Invalid safety PIN storage format"
            }

            val iv = decode(parts[0])
            val encrypted = decode(parts[1])

            require(iv.size == GCM_IV_LENGTH_BYTES) {
                "Invalid safety PIN encryption IV"
            }

            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                getExistingKey()
                    ?: throw IOException("Safety PIN key is missing"),
                GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv)
            )

            val plaintext = String(
                cipher.doFinal(encrypted),
                Charsets.UTF_8
            )

            val fields = plaintext.split(":")

            require(fields.size == 4) {
                "Invalid safety PIN record"
            }

            return PinRecord(
                salt = fields[0],
                hash = fields[1],
                attempts = fields[2].toInt(),
                lockoutUntil = fields[3].toLong()
            )
        } catch (exception: Exception) {
            throw IOException(
                "Could not read or verify safety PIN storage",
                exception
            )
        }
    }

    private fun getExistingKey(): SecretKey? {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)

        return keyStore.getKey(KEY_ALIAS, null) as? SecretKey
    }

    private fun getOrCreateKey(): SecretKey {
        getExistingKey()?.let { return it }

        val generator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            ANDROID_KEYSTORE
        )

        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or
                    KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(
                    KeyProperties.ENCRYPTION_PADDING_NONE
                )
                .setRandomizedEncryptionRequired(true)
                .setKeySize(256)
                .build()
        )

        return generator.generateKey()
    }

    private fun encode(bytes: ByteArray): String =
        Base64.encodeToString(bytes, Base64.NO_WRAP)

    private fun decode(value: String): ByteArray =
        Base64.decode(value, Base64.NO_WRAP)

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "wegotchu_safety_pin_key"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val PBKDF2_ITERATIONS = 210_000
        const val HASH_LENGTH_BITS = 256
        const val GCM_TAG_LENGTH_BITS = 128
        const val GCM_IV_LENGTH_BYTES = 12
        const val MAX_ATTEMPTS = 5
        const val LOCKOUT_DURATION_MS = 5 * 60 * 1000L
    }
}

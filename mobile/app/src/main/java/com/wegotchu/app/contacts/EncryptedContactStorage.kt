
package com.wegotchu.app.contacts

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.io.File
import java.io.IOException
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.AEADBadTagException
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class EncryptedContactStorage(context: Context) {

    private val appContext = context.applicationContext

    private val storageFile: File
        get() = File(appContext.filesDir, STORAGE_FILE_NAME)

    @Synchronized
    fun save(plaintext: String) {
        val temporaryFile =
            File(appContext.filesDir, "$STORAGE_FILE_NAME.tmp")

        try {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())

            val ciphertext = cipher.doFinal(
                plaintext.toByteArray(StandardCharsets.UTF_8)
            )

            val payload = listOf(
                FORMAT_VERSION,
                Base64.encodeToString(cipher.iv, Base64.NO_WRAP),
                Base64.encodeToString(ciphertext, Base64.NO_WRAP)
            ).joinToString(":")

            temporaryFile.writeText(payload, StandardCharsets.UTF_8)

            if (!temporaryFile.renameTo(storageFile)) {
                throw IOException("Could not replace encrypted contacts file")
            }
        } catch (exception: Exception) {
            temporaryFile.delete()
            throw EncryptedContactStorageException(
                "Could not save encrypted contacts",
                exception
            )
        }
    }

    @Synchronized
    fun load(): String? {
        if (!storageFile.exists()) return null

        try {
            val parts = storageFile
                .readText(StandardCharsets.UTF_8)
                .split(":")

            if (parts.size != 3 || parts[0] != FORMAT_VERSION) {
                throw IOException("Unsupported encrypted contacts format")
            }

            val iv = Base64.decode(parts[1], Base64.NO_WRAP)
            val ciphertext = Base64.decode(parts[2], Base64.NO_WRAP)

            if (iv.size != GCM_IV_LENGTH_BYTES) {
                throw IOException("Invalid encrypted contacts IV")
            }

            if (ciphertext.size < GCM_TAG_LENGTH_BITS / 8) {
                throw IOException("Encrypted contacts payload is truncated")
            }

            val key = getExistingKey()
                ?: throw IOException("Trusted contacts encryption key is missing")

            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                key,
                GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv)
            )

            return String(
                cipher.doFinal(ciphertext),
                StandardCharsets.UTF_8
            )
        } catch (exception: Exception) {
            throw EncryptedContactStorageException(
                if (exception is AEADBadTagException) {
                    "Trusted contacts failed authentication"
                } else {
                    "Could not read or decrypt trusted contacts"
                },
                exception
            )
        }
    }

    @Synchronized
    fun delete() {
        try {
            if (storageFile.exists() && !storageFile.delete()) {
                throw IOException("Could not delete encrypted contacts")
            }
        } catch (exception: Exception) {
            throw EncryptedContactStorageException(
                "Could not delete encrypted contacts",
                exception
            )
        }
    }

    private fun getExistingKey(): SecretKey? {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply {
            load(null)
        }

        return keyStore.getKey(KEY_ALIAS, null) as? SecretKey
    }

    private fun getOrCreateKey(): SecretKey {
        getExistingKey()?.let { return it }

        val keyGenerator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            ANDROID_KEYSTORE
        )

        keyGenerator.init(
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
                .setKeySize(AES_KEY_SIZE_BITS)
                .build()
        )

        return keyGenerator.generateKey()
    }

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "wegotchu_trusted_contacts_key"
        const val STORAGE_FILE_NAME = "trusted_contacts.enc"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val FORMAT_VERSION = "v1"
        const val AES_KEY_SIZE_BITS = 256
        const val GCM_TAG_LENGTH_BITS = 128
        const val GCM_IV_LENGTH_BYTES = 12
    }
}

class EncryptedContactStorageException(
    message: String,
    cause: Throwable? = null
) : IOException(message, cause)

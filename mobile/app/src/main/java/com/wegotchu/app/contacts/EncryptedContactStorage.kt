package com.wegotchu.app.contacts

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.io.File
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Encrypts trusted-contact data with an AES-GCM key held in Android Keystore.
 *
 * Store only the encrypted payload in the private app files directory.
 * The caller is responsible for validating and serializing contact data.
 */
class EncryptedContactStorage(context: Context) {

    private val appContext = context.applicationContext
    private val storageFile: File
        get() = File(appContext.filesDir, STORAGE_FILE_NAME)

    @Synchronized
    fun save(plaintext: String) {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())

        val ciphertext = cipher.doFinal(
            plaintext.toByteArray(StandardCharsets.UTF_8)
        )
        val iv = cipher.iv

        // Versioned format: version:base64(iv):base64(ciphertext)
        val payload = listOf(
            FORMAT_VERSION,
            Base64.encodeToString(iv, Base64.NO_WRAP),
            Base64.encodeToString(ciphertext, Base64.NO_WRAP)
        ).joinToString(":")

        val temporaryFile = File(appContext.filesDir, "$STORAGE_FILE_NAME.tmp")
        temporaryFile.writeText(payload, StandardCharsets.UTF_8)

        if (!temporaryFile.renameTo(storageFile)) {
            temporaryFile.delete()
            throw IllegalStateException("Could not save encrypted contacts")
        }
    }

    @Synchronized
    fun load(): String? {
        if (!storageFile.exists()) return null

        val parts = storageFile.readText(StandardCharsets.UTF_8).split(":")
        require(parts.size == 3 && parts[0] == FORMAT_VERSION) {
            "Encrypted contacts have an unsupported format"
        }

        val iv = Base64.decode(parts[1], Base64.NO_WRAP)
        val ciphertext = Base64.decode(parts[2], Base64.NO_WRAP)

        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            getOrCreateKey(),
            GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv)
        )

        return String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8)
    }

    @Synchronized
    fun delete() {
        if (storageFile.exists() && !storageFile.delete()) {
            throw IllegalStateException("Could not delete encrypted contacts")
        }
    }

    private fun getOrCreateKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply {
            load(null)
        }

        val existingKey = keyStore.getKey(KEY_ALIAS, null) as? SecretKey
        if (existingKey != null) return existingKey

        val keyGenerator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            ANDROID_KEYSTORE
        )

        keyGenerator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
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
    }
}

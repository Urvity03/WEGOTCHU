package com.wegotchu.app.contacts

import android.net.Uri
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TrustedContactPickerTest {

    @Test
    fun inaccessibleContactProviderReturnsNullWithoutCrashing() {
        val context =
            InstrumentationRegistry.getInstrumentation().targetContext

        val inaccessibleUri =
            Uri.parse("content://com.invalid.wegotchu.provider/phones/1")

        val result = TrustedContactPicker.readContact(
            context,
            inaccessibleUri
        )

        assertNull(result)
    }
}

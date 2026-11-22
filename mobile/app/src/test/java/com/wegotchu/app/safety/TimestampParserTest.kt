package com.wegotchu.app.safety

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class TimestampParserTest {

    @Test
    fun parseServerTimestamp_sixDigitMicrosecondsWithOffset_success() {
        // Sample from FastAPI: 2026-11-21T13:19:10.729286+00:00
        val timestamp = "2026-11-21T13:19:10.729286+00:00"
        val parsed = TimestampParser.parseServerTimestamp(timestamp)

        assertNotNull(parsed)
        // 2026-11-21 13:19:10 UTC in epoch millis is 1795267150000 + 729 = 1795267150729
        assertEquals(1795267150729L, parsed)
    }

    @Test
    fun parseServerTimestamp_sixDigitMicrosecondsWithZ_success() {
        val timestamp = "2026-11-21T13:19:10.729286Z"
        val parsed = TimestampParser.parseServerTimestamp(timestamp)

        assertNotNull(parsed)
        assertEquals(1795267150729L, parsed)
    }

    @Test
    fun parseServerTimestamp_threeDigitMillisecondsWithOffset_success() {
        val timestamp = "2026-11-21T13:19:10.729+00:00"
        val parsed = TimestampParser.parseServerTimestamp(timestamp)

        assertNotNull(parsed)
        assertEquals(1795267150729L, parsed)
    }

    @Test
    fun parseServerTimestamp_noFractionalSecondsWithOffset_success() {
        val timestamp = "2026-11-21T13:19:10+00:00"
        val parsed = TimestampParser.parseServerTimestamp(timestamp)

        assertNotNull(parsed)
        assertEquals(1795267150000L, parsed)
    }

    @Test
    fun parseServerTimestamp_invalidFormat_returnsNull() {
        assertNull(TimestampParser.parseServerTimestamp(""))
        assertNull(TimestampParser.parseServerTimestamp("   "))
        assertNull(TimestampParser.parseServerTimestamp("invalid-timestamp"))
    }
}

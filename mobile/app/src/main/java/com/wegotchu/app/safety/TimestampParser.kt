package com.wegotchu.app.safety

import java.text.SimpleDateFormat
import java.util.Locale

object TimestampParser {

    /**
     * Parses ISO-8601 server timestamps supporting arbitrary fractional second precision
     * (e.g. 6-digit microseconds from Python FastAPI) and both offset (+00:00) and UTC (Z) suffixes.
     */
    fun parseServerTimestamp(value: String): Long? {
        if (value.isBlank()) return null

        // 1. Try Java 8 java.time (OffsetDateTime / Instant) which natively supports 1-9 fractional digits
        try {
            return java.time.OffsetDateTime.parse(value).toInstant().toEpochMilli()
        } catch (_: Throwable) {
            try {
                return java.time.Instant.parse(value).toEpochMilli()
            } catch (_: Throwable) {
                // Fallback to SimpleDateFormat below
            }
        }

        // 2. Fallback: normalize >3 fractional digits down to 3 milliseconds digits for SimpleDateFormat
        val normalized = value.replace(Regex("""\.(\d{3})\d+"""), """.$1""")
        val formats = listOf(
            "yyyy-MM-dd'T'HH:mm:ss.SSSXXX",
            "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",
            "yyyy-MM-dd'T'HH:mm:ssXXX",
            "yyyy-MM-dd'T'HH:mm:ss'Z'"
        )

        for (format in formats) {
            try {
                val parser = SimpleDateFormat(format, Locale.US)
                parser.isLenient = false
                val parsed = parser.parse(normalized)
                if (parsed != null) {
                    return parsed.time
                }
            } catch (_: Exception) {
                // Try next pattern
            }
        }

        return null
    }
}

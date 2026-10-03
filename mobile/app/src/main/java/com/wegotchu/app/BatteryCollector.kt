package com.wegotchu.app

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager

class BatteryCollector(
    private val context: Context
) {

    fun getBatteryLevel(): Double {
        val batteryIntent = context.registerReceiver(
            null,
            IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        )

        val level = batteryIntent?.getIntExtra(
            BatteryManager.EXTRA_LEVEL,
            -1
        ) ?: -1

        val scale = batteryIntent?.getIntExtra(
            BatteryManager.EXTRA_SCALE,
            -1
        ) ?: -1

        if (level < 0 || scale <= 0) {
            return 0.0
        }

        return level.toDouble() / scale.toDouble()
    }
}
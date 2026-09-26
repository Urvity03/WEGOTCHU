package com.wegotchu.app.sensors

import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.util.Log
import java.util.ArrayDeque

data class ImuSample(
    val timestampNanos: Long,
    val x: Float,
    val y: Float,
    val z: Float
)

data class ImuSnapshot(
    val accelerometer: ImuSample?,
    val gyroscope: ImuSample?
)

class SensorCollector(
    private val sensorManager: SensorManager,
    private val bufferSize: Int = 250
) : SensorEventListener {

    private val accelerometerBuffer = ArrayDeque<ImuSample>(bufferSize)
    private val gyroscopeBuffer = ArrayDeque<ImuSample>(bufferSize)

    private val lock = Any()

    private val accelerometer: Sensor? =
        sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)

    private val gyroscope: Sensor? =
        sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)

    fun start() {

        if (accelerometer == null) {
            Log.e(
                "SensorCollector",
                "Accelerometer sensor is NOT available"
            )
        } else {
            sensorManager.registerListener(
                this,
                accelerometer,
                SensorManager.SENSOR_DELAY_GAME
            )

            Log.d(
                "SensorCollector",
                "Accelerometer registered: ${accelerometer.name}"
            )
        }

        if (gyroscope == null) {
            Log.e(
                "SensorCollector",
                "Gyroscope sensor is NOT available"
            )
        } else {
            sensorManager.registerListener(
                this,
                gyroscope,
                SensorManager.SENSOR_DELAY_GAME
            )

            Log.d(
                "SensorCollector",
                "Gyroscope registered: ${gyroscope.name}"
            )
        }
    }

    fun stop() {
        sensorManager.unregisterListener(this)

        Log.d(
            "SensorCollector",
            "Sensor collection stopped"
        )
    }

    fun snapshot(): ImuSnapshot {
        synchronized(lock) {
            return ImuSnapshot(
                accelerometer = accelerometerBuffer.lastOrNull(),
                gyroscope = gyroscopeBuffer.lastOrNull()
            )
        }
    }

    fun accelerometerSamples(): List<ImuSample> {
        synchronized(lock) {
            return accelerometerBuffer.toList()
        }
    }

    fun gyroscopeSamples(): List<ImuSample> {
        synchronized(lock) {
            return gyroscopeBuffer.toList()
        }
    }

    override fun onSensorChanged(event: SensorEvent) {

        val sample = ImuSample(
            timestampNanos = event.timestamp,
            x = event.values[0],
            y = event.values[1],
            z = event.values[2]
        )

        Log.d(
            "SensorCollector",
            "${event.sensor.name}: " +
                    "x=${event.values[0]}, " +
                    "y=${event.values[1]}, " +
                    "z=${event.values[2]}"
        )

        synchronized(lock) {
            when (event.sensor.type) {

                Sensor.TYPE_ACCELEROMETER -> {
                    addToBuffer(
                        accelerometerBuffer,
                        sample
                    )
                }

                Sensor.TYPE_GYROSCOPE -> {
                    addToBuffer(
                        gyroscopeBuffer,
                        sample
                    )
                }
            }
        }
    }

    private fun addToBuffer(
        buffer: ArrayDeque<ImuSample>,
        sample: ImuSample
    ) {
        if (buffer.size >= bufferSize) {
            buffer.removeFirst()
        }

        buffer.addLast(sample)
    }

    override fun onAccuracyChanged(
        sensor: Sensor?,
        accuracy: Int
    ) {
        // Accuracy changes can be handled later if required.
    }
}
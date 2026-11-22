package com.wegotchu.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.hardware.SensorManager
import android.location.LocationManager
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.wegotchu.app.BatteryCollector
import com.wegotchu.app.MainActivity
import com.wegotchu.app.NetworkCollector
import com.wegotchu.app.R
import com.wegotchu.app.TelemetryBuilder
import com.wegotchu.app.location.LocationCollector
import com.wegotchu.app.network.TelemetrySender
import com.wegotchu.app.sensors.SensorCollector
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class SafetyMonitoringService : Service() {

    private val serviceJob = Job()
    private val serviceScope = CoroutineScope(Dispatchers.IO + serviceJob)

    private var activeTripId: String? = null
    private var streamingJob: Job? = null

    private lateinit var locationCollector: LocationCollector
    private lateinit var sensorCollector: SensorCollector
    private lateinit var telemetryBuilder: TelemetryBuilder
    private val telemetrySender = TelemetrySender()

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "SafetyMonitoringService created")

        val sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager
        sensorCollector = SensorCollector(sensorManager)

        val locationManager = getSystemService(LOCATION_SERVICE) as LocationManager
        locationCollector = LocationCollector(
            locationManager = locationManager,
            permissionChecker = { perm ->
                ContextCompat.checkSelfPermission(this, perm) ==
                    android.content.pm.PackageManager.PERMISSION_GRANTED
            }
        )

        val batteryCollector = BatteryCollector(this)
        val networkCollector = NetworkCollector(this)

        telemetryBuilder = TelemetryBuilder(
            locationCollector = locationCollector,
            sensorCollector = sensorCollector,
            batteryCollector = batteryCollector,
            networkCollector = networkCollector
        )

        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action

        when (action) {
            ACTION_STOP_MONITORING -> {
                Log.d(TAG, "Stopping SafetyMonitoringService via action")
                stopMonitoring()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_START_MONITORING, null -> {
                val tripId = intent?.getStringExtra(EXTRA_TRIP_ID)
                if (tripId != null) {
                    activeTripId = tripId
                }

                val notification = buildNotification("Monitoring active: trip ${activeTripId ?: "standard"}")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    startForeground(
                        NOTIFICATION_ID,
                        notification,
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION
                    )
                } else {
                    startForeground(NOTIFICATION_ID, notification)
                }

                startMonitoring()
            }
        }

        return START_STICKY
    }

    private fun startMonitoring() {
        if (streamingJob?.isActive == true) return

        sensorCollector.start()
        locationCollector.start()
        isMonitoring = true

        streamingJob = serviceScope.launch {
            Log.d(TAG, "Starting periodic telemetry transmission loop (interval: ${INTERVAL_MS}ms)")

            while (isActive) {
                try {
                    val payload = telemetryBuilder.build(tripId = activeTripId)
                    if (payload != null) {
                        val success = telemetrySender.send(payload)
                        Log.d(TAG, "Streamed telemetry for trip $activeTripId. Success=$success")
                    } else {
                        Log.d(TAG, "Telemetry not ready yet (waiting on sensors/GPS)")
                    }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    Log.e(TAG, "Error in telemetry streaming loop", e)
                }

                delay(INTERVAL_MS)
            }
        }
    }

    private fun stopMonitoring() {
        isMonitoring = false
        streamingJob?.cancel()
        streamingJob = null
        sensorCollector.stop()
        locationCollector.stop()
    }

    override fun onDestroy() {
        stopMonitoring()
        serviceJob.cancel()
        Log.d(TAG, "SafetyMonitoringService destroyed")
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "WEGOTCHU Safety Monitoring",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Active safety telemetry and location tracking"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(contentText: String): Notification {
        val launchIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("WEGOTCHU Safety Active")
            .setContentText(contentText)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    companion object {
        private const val TAG = "SafetyMonitoringService"
        const val CHANNEL_ID = "wegotchu_safety_channel"
        const val NOTIFICATION_ID = 1001

        const val ACTION_START_MONITORING = "com.wegotchu.app.action.START_MONITORING"
        const val ACTION_STOP_MONITORING = "com.wegotchu.app.action.STOP_MONITORING"
        const val EXTRA_TRIP_ID = "extra_trip_id"

        private const val INTERVAL_MS = 3000L

        @Volatile
        var isMonitoring: Boolean = false
            private set

        fun start(context: Context, tripId: String? = null) {
            val intent = Intent(context, SafetyMonitoringService::class.java).apply {
                action = ACTION_START_MONITORING
                if (tripId != null) {
                    putExtra(EXTRA_TRIP_ID, tripId)
                }
            }
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            val intent = Intent(context, SafetyMonitoringService::class.java).apply {
                action = ACTION_STOP_MONITORING
            }
            context.startService(intent)
        }
    }
}

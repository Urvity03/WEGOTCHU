package com.wegotchu.app

import android.Manifest
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.wegotchu.app.location.LocationCollector
import com.wegotchu.app.network.TelemetrySender
import com.wegotchu.app.sensors.SensorCollector
import com.wegotchu.app.ui.theme.WEGOTCHUTheme
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private lateinit var sensorCollector: SensorCollector
    private lateinit var locationCollector: LocationCollector
    private lateinit var telemetryBuilder: TelemetryBuilder

    private val telemetrySender = TelemetrySender()

    private val locationPermissionLauncher =
        registerForActivityResult(
            ActivityResultContracts.RequestMultiplePermissions()
        ) { permissions ->

            val fineGranted =
                permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true

            val coarseGranted =
                permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true

            if (fineGranted || coarseGranted) {
                locationCollector.start()
                startTelemetryTest()
            } else {
                Log.e(
                    "TelemetryBuilder",
                    "Location permission denied"
                )
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val sensorManager =
            getSystemService(SENSOR_SERVICE) as android.hardware.SensorManager

        sensorCollector = SensorCollector(sensorManager)

        val locationManager =
            getSystemService(LOCATION_SERVICE) as LocationManager

        locationCollector = LocationCollector(locationManager)

        val batteryCollector = BatteryCollector(this)

        val networkCollector = NetworkCollector(this)

        telemetryBuilder = TelemetryBuilder(
            locationCollector = locationCollector,
            sensorCollector = sensorCollector,
            batteryCollector = batteryCollector,
            networkCollector = networkCollector
        )

        setContent {
            WEGOTCHUTheme {
                Scaffold(
                    modifier = Modifier.fillMaxSize()
                ) { innerPadding ->
                    Greeting(
                        name = "WEGOTCHU",
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()

        sensorCollector.start()

        if (
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_COARSE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            locationCollector.start()
            startTelemetryTest()
        } else {
            locationPermissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                )
            )
        }
    }

    private fun startTelemetryTest() {

        lifecycleScope.launch {

            Log.d(
                "TelemetrySender",
                "Waiting for sensor and location data..."
            )

            delay(3000)

            repeat(3) { attempt ->

                val payload = telemetryBuilder.build()

                if (payload == null) {
                    Log.d(
                        "TelemetrySender",
                        "Attempt ${attempt + 1}: telemetry not ready yet"
                    )
                } else {

                    Log.d(
                        "TelemetrySender",
                        "Attempt ${attempt + 1}: sending telemetry..."
                    )

                    val success =
                        telemetrySender.send(payload)

                    if (success) {
                        Log.d(
                            "TelemetrySender",
                            "Attempt ${attempt + 1}: backend accepted telemetry"
                        )
                    } else {
                        Log.e(
                            "TelemetrySender",
                            "Attempt ${attempt + 1}: backend rejected or unreachable"
                        )
                    }
                }

                if (attempt < 2) {
                    delay(3000)
                }
            }
        }
    }

    override fun onPause() {
        locationCollector.stop()
        sensorCollector.stop()

        super.onPause()
    }
}

@Composable
fun Greeting(
    name: String,
    modifier: Modifier = Modifier
) {
    Text(
        text = "Hello $name!",
        modifier = modifier
    )
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    WEGOTCHUTheme {
        Greeting("WEGOTCHU")
    }
}
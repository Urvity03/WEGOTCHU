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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.wegotchu.app.contacts.TrustedContact
import com.wegotchu.app.contacts.TrustedContactPicker
import com.wegotchu.app.contacts.TrustedContactRepository
import com.wegotchu.app.contacts.TrustedContactsScreen
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import androidx.compose.runtime.LaunchedEffect
import android.app.Activity
import android.content.Intent
import android.provider.ContactsContract
import android.widget.Toast
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private lateinit var sensorCollector: SensorCollector
    private lateinit var locationCollector: LocationCollector
    private lateinit var telemetryBuilder: TelemetryBuilder

    private val telemetrySender = TelemetrySender()
    private lateinit var trustedContactRepository: TrustedContactRepository
    private var refreshContacts: (() -> Unit)? = null



private val trustedContactPickerLauncher =
    registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val phoneUri = result.data?.data

        if (result.resultCode != Activity.RESULT_OK || phoneUri == null) {
            Log.d("TrustedContacts", "Phone selection cancelled")
        } else {
            lifecycleScope.launch {
                try {
                    // Read the selected phone URI off the main thread.
                    val contact = withContext(Dispatchers.IO) {
                        TrustedContactPicker.readContact(
                            this@MainActivity,
                            phoneUri
                        )
                    }

                    if (contact == null) {
                        Toast.makeText(
                            this@MainActivity,
                            "Unable to read this contact. Please try another.",
                            Toast.LENGTH_LONG
                        ).show()
                    } else {
                        // Save the encrypted contact off the main thread.
                        withContext(Dispatchers.IO) {
                            trustedContactRepository.add(contact)
                        }

                        // Refresh Compose state on the main thread.
                        refreshContacts?.invoke()

                        Toast.makeText(
                            this@MainActivity,
                            "Trusted contact added",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } catch (exception: Exception) {
                    Log.e(
                        "TrustedContacts",
                        "Failed to read or save selected phone number",
                        exception
                    )

                    Toast.makeText(
                        this@MainActivity,
                        "Could not add trusted contact. Please try again.",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }
    }



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
       trustedContactRepository = TrustedContactRepository(applicationContext)

       Log.d("MainActivity", "onCreate() started")
        enableEdgeToEdge()

        val sensorManager =
            getSystemService(SENSOR_SERVICE) as android.hardware.SensorManager

        sensorCollector = SensorCollector(sensorManager)

        val locationManager =
            getSystemService(LOCATION_SERVICE) as LocationManager

        locationCollector = LocationCollector(
            locationManager = locationManager,
            permissionChecker = { permission ->
                ContextCompat.checkSelfPermission(
                    this,
                    permission
                ) == PackageManager.PERMISSION_GRANTED
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

        setContent {
    WEGOTCHUTheme {
        var contacts by remember {
            mutableStateOf(emptyList<TrustedContact>())
        }
var isSOSSubmitting by remember { mutableStateOf(false) }
var sosMessage by remember { mutableStateOf<String?>(null) }
        LaunchedEffect(Unit) {
            refreshContacts = {
                contacts = try {
                    trustedContactRepository.getAll()
                } catch (exception: Exception) {
                   Log.e(
                    "TrustedContacts",
                    "Could not load or refresh contacts",
                     exception
                    )
                    emptyList()
                }
            }

        refreshContacts?.invoke()
        }

        Scaffold(
            modifier = Modifier.fillMaxSize()
        ) { innerPadding ->
            TrustedContactsScreen(
                contacts = contacts,
                onAddContact = {
                    val intent = Intent(
                        Intent.ACTION_PICK,
                        ContactsContract.CommonDataKinds.Phone.CONTENT_URI
                    )
                    trustedContactPickerLauncher.launch(intent)
                },
                onRemoveContact = { contact ->
                    contacts = try {
                        trustedContactRepository.remove(contact.id)
                    } catch (exception: Exception) {
                        Log.e(
                            "TrustedContacts",
                            "Could not remove contact",
                            exception
                        )
                        contacts
                    }
                },
                onSOS = {
    if (!isSOSSubmitting) {
        isSOSSubmitting = true
        sosMessage = null

        lifecycleScope.launch {
            try {
                val location = locationCollector.latestLocation()

                val payload = com.wegotchu.app.network.SOSAlertRequest(
                    latitude = location?.latitude,
                    longitude = location?.longitude,
                    accuracyMeters = location?.accuracyMeters?.toDouble(),
                    note = "Manual SOS triggered from Android app"
                )

                val token = com.wegotchu.app.network.AuthTokenProvider.getToken()
                val response = com.wegotchu.app.network.RetrofitClient.api.createSOSAlert(
                    authorization = "Bearer $token",
                    payload = payload
                )

                if (response.isSuccessful) {
                    val alert = response.body()
                    sosMessage = if (alert != null) {
                        "SOS #${alert.id} recorded. Emergency notifications: ${alert.notificationStatus}."
                    } else {
                        "SOS request succeeded, but the response was empty."
                    }
                } else {
                    sosMessage = "SOS request failed (HTTP ${response.code()}). Please try again."
                }
            } catch (exception: Exception) {
                Log.e("ManualSOS", "Failed to submit SOS alert", exception)
                sosMessage = "Could not send SOS. Check your connection and try again."
            } finally {
                isSOSSubmitting = false
            }
        }
    }
},
isSOSSubmitting = isSOSSubmitting,
sosMessage = sosMessage,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
            )
        }
    }
}
    }

    override fun onResume() {
      super.onResume()

      Log.d("MainActivity", "onResume() started")
        sensorCollector.start()

        val fineLocationGranted =
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED

        val coarseLocationGranted =
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_COARSE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED

        if (fineLocationGranted || coarseLocationGranted) {
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

      Log.d("MainActivity", "startTelemetryTest() called")

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
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
import com.wegotchu.app.safety.SafetyPinStorage
import com.wegotchu.app.safety.SafetyTimerStorage
import java.text.SimpleDateFormat
import java.util.Locale
import kotlinx.coroutines.CancellationException

class MainActivity : ComponentActivity() {

    private lateinit var sensorCollector: SensorCollector
    private lateinit var locationCollector: LocationCollector
    private lateinit var telemetryBuilder: TelemetryBuilder
    private lateinit var safetyPinStorage: SafetyPinStorage
    private lateinit var safetyTimerStorage: SafetyTimerStorage

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
            } else {
                Log.e(
                    "TelemetryBuilder",
                    "Location permission denied"
                )
            }

            // Start telemetry whether location permission is granted or denied.
            startTelemetryTest()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
       super.onCreate(savedInstanceState)
       trustedContactRepository = TrustedContactRepository(applicationContext)
       safetyPinStorage = SafetyPinStorage(applicationContext)
       safetyTimerStorage = SafetyTimerStorage(applicationContext)

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
var timerState by remember {
    mutableStateOf(safetyTimerStorage.load())
}
var timerRemainingSeconds by remember {
    mutableStateOf<Long?>(null)
}
var isTimerSubmitting by remember {
    mutableStateOf(false)
}
var timerMessage by remember {
    mutableStateOf<String?>(null)
}
var pinConfigured by remember {
    mutableStateOf(
        runCatching {
            safetyPinStorage.isPinConfigured()
        }.onFailure { exception ->
            Log.e("SafetyTimer", "Could not check PIN configuration", exception)
        }.getOrDefault(false)
    )
}
var showCheckInDialog by remember { mutableStateOf(false) }
var checkInErrorMessage by remember { mutableStateOf<String?>(null) }
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
LaunchedEffect(timerState) {
    val activeTimer = timerState

    if (activeTimer == null) {
        timerRemainingSeconds = null
        return@LaunchedEffect
    }

    val expiryMillis = parseServerTimestamp(activeTimer.expiresAt)

    if (expiryMillis == null) {
        timerMessage = "Could not read the server timer deadline."
        return@LaunchedEffect
    }

    while (true) {
        val remaining = (
            (expiryMillis - System.currentTimeMillis() + 999) / 1000
        ).coerceAtLeast(0)

        timerRemainingSeconds = remaining

        if (remaining in 1L..60L && !showCheckInDialog) {
            showCheckInDialog = true
        }

        if (remaining == 0L) {
            showCheckInDialog = false
            isTimerSubmitting = true

            try {
                com.wegotchu.app.service.SafetyMonitoringService.stop(this@MainActivity)

                val token =
                    com.wegotchu.app.network.AuthTokenProvider.getToken()

                val response =
                    com.wegotchu.app.network.RetrofitClient.api.expireSafetyTimer(
                        authorization = "Bearer $token",
                        payload = com.wegotchu.app.network.ExpireSafetyTimerRequest(
                            tripId = activeTimer.tripId
                        )
                    )

                if (response.isSuccessful) {
                    safetyTimerStorage.clear()
                    timerState = null

                    // Auto-escalate SOS alert to trusted contacts
                    val currentContacts = withContext(Dispatchers.IO) {
                        try { trustedContactRepository.getAll() } catch (_: Exception) { emptyList() }
                    }
                    val loc = locationCollector.latestLocation()

                    withContext(Dispatchers.IO) {
                        com.wegotchu.app.contacts.EmergencyDispatcher.dispatchLocalSms(
                            context = this@MainActivity,
                            contacts = currentContacts,
                            latitude = loc?.latitude,
                            longitude = loc?.longitude,
                            note = "Automatic SOS: safety timer expired"
                        )
                    }

                    val sosPayload = com.wegotchu.app.network.SOSAlertRequest(
                        latitude = loc?.latitude,
                        longitude = loc?.longitude,
                        accuracyMeters = loc?.accuracyMeters?.toDouble(),
                        note = "Automatic SOS escalation: safety timer expired without deactivation",
                        tripId = activeTimer.tripId,
                        recipients = currentContacts.map { it.phoneNumber }
                    )

                    try {
                        com.wegotchu.app.network.RetrofitClient.api.createSOSAlert(
                            authorization = "Bearer $token",
                            payload = sosPayload
                        )
                    } catch (e: Exception) {
                        Log.e("SafetyTimer", "Failed to submit automatic SOS", e)
                    }

                    timerMessage =
                        "Safety timer expired! Emergency SOS escalated to ${currentContacts.size} trusted contact(s)."
		    return@LaunchedEffect
                } else {
                    timerMessage =
                        "Timer deadline reached, but the server could not confirm expiry (HTTP ${response.code()}). Please retry when connected."
                }
            } catch (exception: CancellationException) {
                throw exception
            } catch (exception: Exception) {
                Log.e("SafetyTimer", "Expiry request failed", exception)
                timerMessage =
                    "Timer deadline reached, but server confirmation failed. Please check your connection."
            } finally {
                isTimerSubmitting = false
            }

            // Retry server confirmation while the timer remains locally active.
            // The backend deadline remains authoritative.
            if (timerState?.tripId == activeTimer.tripId) {
                delay(30_000)
            }
            continue
        }

        delay(1000)
    }
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
                val currentContacts = withContext(Dispatchers.IO) {
                    try { trustedContactRepository.getAll() } catch (_: Exception) { emptyList() }
                }
                val recipientNumbers = currentContacts.map { it.phoneNumber }

                // Attempt local direct SMS dispatch
                val localDispatchedCount = withContext(Dispatchers.IO) {
                    com.wegotchu.app.contacts.EmergencyDispatcher.dispatchLocalSms(
                        context = this@MainActivity,
                        contacts = currentContacts,
                        latitude = location?.latitude,
                        longitude = location?.longitude,
                        note = "Manual SOS triggered from Android app"
                    )
                }

                val payload = com.wegotchu.app.network.SOSAlertRequest(
                    latitude = location?.latitude,
                    longitude = location?.longitude,
                    accuracyMeters = location?.accuracyMeters?.toDouble(),
                    note = "Manual SOS triggered from Android app",
                    tripId = timerState?.tripId,
                    recipients = recipientNumbers
                )

                val token = com.wegotchu.app.network.AuthTokenProvider.getToken()

                val response =
                    com.wegotchu.app.network.RetrofitClient.api.createSOSAlert(
                        authorization = "Bearer $token",
                        payload = payload
                    )

                if (response.isSuccessful) {
                    val alert = response.body()

                    sosMessage = if (alert != null) {
                        val locationMessage = if (location != null) {
                            "Location attached."
                        } else {
                            "Location could not be attached."
                        }

                        val notificationMessage =
                            if (alert.notificationStatus.equals(
                                    "not_configured",
                                    ignoreCase = true
                                )
                            ) {
                                if (localDispatchedCount > 0) {
                                    "Direct SMS dispatched to $localDispatchedCount contact(s)."
                                } else {
                                    "Emergency contacts have NOT been notified (no contacts or SMS permission)."
                                }
                            } else {
                                "Alert dispatched to ${alert.recipientsCount ?: recipientNumbers.size} contact(s) (Status: ${alert.notificationStatus})."
                            }

                        "SOS alert recorded successfully. $locationMessage $notificationMessage"
                    } else {
                        "SOS request succeeded, but the response was empty."
                    }
                } else {
                    sosMessage =
                        "SOS request failed (HTTP ${response.code()}). Please try again."
                }

            } catch (exception: Exception) {
                Log.e("ManualSOS", "Failed to submit SOS alert", exception)
                sosMessage =
                    "Could not send SOS. Check your connection and try again."
            } finally {
                isSOSSubmitting = false
            }
        }
    }
},

isSOSSubmitting = isSOSSubmitting,
sosMessage = sosMessage,
timerActive = timerState != null,
timerRemainingSeconds = timerRemainingSeconds,
isTimerSubmitting = isTimerSubmitting,
timerMessage = timerMessage,
pinConfigured = pinConfigured,

onSetupSafetyPin = { pin ->
    lifecycleScope.launch {
        try {
            withContext(Dispatchers.IO) {
                safetyPinStorage.setupPin(pin)
            }
            pinConfigured = true
            timerMessage = "Safety PIN configured successfully."
        } catch (exception: Exception) {
            Log.e("SafetyTimer", "PIN setup failed", exception)
            timerMessage = "Could not securely save your PIN."
        }
    }
},

onStartSafetyTimer = { duration ->
    if (!isTimerSubmitting && timerState == null) {
        isTimerSubmitting = true
        timerMessage = null

        lifecycleScope.launch {
            try {
                val token =
                    com.wegotchu.app.network.AuthTokenProvider.getToken()

                val tripId = java.util.UUID.randomUUID().toString()

                val response =
                    com.wegotchu.app.network.RetrofitClient.api.startSafetyTimer(
                        authorization = "Bearer $token",
                        payload = com.wegotchu.app.network.StartSafetyTimerRequest(
                            tripId = tripId,
                            timerDurationSeconds = duration
                        )
                    )

                val body = response.body()

                if (response.isSuccessful && body?.timerExpiresAt != null) {
                    val newState = com.wegotchu.app.safety.SafetyTimerState(
                        tripId = body.tripId,
                        expiresAt = body.timerExpiresAt,
                        durationSeconds = body.timerDurationSeconds ?: duration
                    )

                    withContext(Dispatchers.IO) {
                        safetyTimerStorage.save(newState)
                    }

                    com.wegotchu.app.service.SafetyMonitoringService.start(this@MainActivity, body.tripId)
                    timerState = newState
                    timerMessage = "Safety timer started successfully. Continuous safety monitoring active."
                } else {
                    timerMessage = "Could not start timer (HTTP ${response.code()})."
                }
            } catch (exception: Exception) {
                Log.e("SafetyTimer", "Timer start failed", exception)
                timerMessage = "Could not start timer. Check your connection."
            } finally {
                isTimerSubmitting = false
            }
        }
    }
},

onDeactivateSafetyTimer = { pin ->
    if (!isTimerSubmitting) {
        isTimerSubmitting = true

        lifecycleScope.launch {
            try {
                val verification = withContext(Dispatchers.IO) {
                    safetyPinStorage.verifyPin(pin)
                }

                when (verification) {
                    SafetyPinStorage.VerificationResult.SUCCESS -> {
                        val activeTimer = timerState

                        if (activeTimer != null) {
                            val token =
                                com.wegotchu.app.network.AuthTokenProvider.getToken()

                            val response =
                                com.wegotchu.app.network.RetrofitClient.api.completeSafetyTimer(
                                    authorization = "Bearer $token",
                                    payload = com.wegotchu.app.network.CompleteSafetyTimerRequest(
                                        tripId = activeTimer.tripId
                                    )
                                )

                            if (response.isSuccessful) {
                                com.wegotchu.app.service.SafetyMonitoringService.stop(this@MainActivity)
                                withContext(Dispatchers.IO) {
                                    safetyTimerStorage.clear()
                                }
                                val infStatus = response.body()?.inferenceStatus
                                val riskNote = if (infStatus != null) " (Inference: $infStatus)" else ""
                                timerState = null
                                timerRemainingSeconds = null
                                timerMessage = "Safety timer deactivated successfully.$riskNote"
                            } else {
                                timerMessage = "Could not deactivate timer (HTTP ${response.code()})."
                            }
                        }
                    }

                    SafetyPinStorage.VerificationResult.INCORRECT ->
                        timerMessage = "Incorrect PIN. Please try again."

                    SafetyPinStorage.VerificationResult.LOCKED_OUT ->
                        timerMessage = "PIN locked for 5 minutes after repeated incorrect attempts."

                    SafetyPinStorage.VerificationResult.NOT_CONFIGURED ->
                        timerMessage = "Please configure a safety PIN first."
                }
            } catch (exception: Exception) {
                Log.e("SafetyTimer", "Timer deactivation failed", exception)
                timerMessage = "Could not deactivate timer. Please try again."
            } finally {
                isTimerSubmitting = false
            }
        }
    }
},
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
            )

            if (showCheckInDialog) {
                com.wegotchu.app.safety.SafetyCheckInDialog(
                    initialCountdownSeconds = (timerRemainingSeconds ?: 60L).toInt().coerceIn(1, 60),
                    reason = "Safety timer expires in under 60 seconds.",
                    errorMessage = checkInErrorMessage,
                    onConfirmSafe = { pin ->
                        lifecycleScope.launch {
                            val verification = withContext(Dispatchers.IO) {
                                safetyPinStorage.verifyPin(pin)
                            }
                            if (verification == com.wegotchu.app.safety.SafetyPinStorage.VerificationResult.SUCCESS) {
                                showCheckInDialog = false
                                checkInErrorMessage = null

                                val activeTimer = timerState
                                if (activeTimer != null) {
                                    try {
                                        val token = com.wegotchu.app.network.AuthTokenProvider.getToken()
                                        com.wegotchu.app.network.RetrofitClient.api.completeSafetyTimer(
                                            authorization = "Bearer $token",
                                            payload = com.wegotchu.app.network.CompleteSafetyTimerRequest(
                                                tripId = activeTimer.tripId
                                            )
                                        )
                                        com.wegotchu.app.service.SafetyMonitoringService.stop(this@MainActivity)
                                        withContext(Dispatchers.IO) { safetyTimerStorage.clear() }
                                        timerState = null
                                        timerRemainingSeconds = null
                                        timerMessage = "Safety confirmed. Timer deactivated successfully."
                                    } catch (_: Exception) {
                                        timerMessage = "Safety confirmed locally."
                                    }
                                }
                            } else {
                                checkInErrorMessage = "Incorrect PIN. Please try again."
                            }
                        }
                    },
                    onTriggerSOS = {
                        showCheckInDialog = false
                        lifecycleScope.launch {
                            val loc = locationCollector.latestLocation()
                            val curContacts = withContext(Dispatchers.IO) {
                                try { trustedContactRepository.getAll() } catch (_: Exception) { emptyList() }
                            }
                            withContext(Dispatchers.IO) {
                                com.wegotchu.app.contacts.EmergencyDispatcher.dispatchLocalSms(
                                    context = this@MainActivity,
                                    contacts = curContacts,
                                    latitude = loc?.latitude,
                                    longitude = loc?.longitude,
                                    note = "Emergency SOS from Safety Check-in"
                                )
                            }
                            val token = com.wegotchu.app.network.AuthTokenProvider.getToken()
                            try {
                                com.wegotchu.app.network.RetrofitClient.api.createSOSAlert(
                                    authorization = "Bearer $token",
                                    payload = com.wegotchu.app.network.SOSAlertRequest(
                                        latitude = loc?.latitude,
                                        longitude = loc?.longitude,
                                        accuracyMeters = loc?.accuracyMeters?.toDouble(),
                                        note = "Emergency confirmed during Safety Check-in",
                                        recipients = curContacts.map { it.phoneNumber }
                                    )
                                )
                            } catch (_: Exception) {}
                            sosMessage = "SOS triggered from check-in dialog."
                        }
                    },
                    onTimeout = {
                        showCheckInDialog = false
                    }
                )
            }
        }
    }
}
    }
private fun parseServerTimestamp(value: String): Long? {
    return com.wegotchu.app.safety.TimestampParser.parseServerTimestamp(value)
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

package com.wegotchu.app.contacts

import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun TrustedContactsScreen(
    contacts: List<TrustedContact>,
    onAddContact: () -> Unit,
    onRemoveContact: (TrustedContact) -> Unit,
    onSOS: () -> Unit,
    isSOSSubmitting: Boolean,
    sosMessage: String?,
    timerActive: Boolean,
    timerRemainingSeconds: Long?,
    isTimerSubmitting: Boolean,
    timerMessage: String?,
    pinConfigured: Boolean,
    onStartSafetyTimer: (Int) -> Unit,
    onSetupSafetyPin: (String) -> Unit,
    onDeactivateSafetyTimer: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val selectedDuration = remember { mutableIntStateOf(600) }
    val pinInput = remember { mutableStateOf("") }

    Column(
        modifier = modifier.padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "WEGOTCHU Safety",
            style = MaterialTheme.typography.headlineSmall
        )

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text("Safety Timer", style = MaterialTheme.typography.titleLarge)

                if (timerActive) {
                    Text(
                        text = "Time remaining: ${
                            timerRemainingSeconds?.coerceAtLeast(0)?.let {
                                "%02d:%02d".format(it / 60, it % 60)
                            } ?: "--:--"
                        }",
                        style = MaterialTheme.typography.headlineMedium
                    )
                    Text("Your timer is active.")

                    OutlinedTextField(
                        value = pinInput.value,
                        onValueChange = {
                            if (it.length <= 8 && it.all(Char::isDigit)) {
                                pinInput.value = it
                            }
                        },
                        label = { Text("Enter safety PIN to deactivate") },
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.NumberPassword
                        ),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Button(
                        onClick = {
                            onDeactivateSafetyTimer(pinInput.value)
                            pinInput.value = ""
                        },
                        enabled = !isTimerSubmitting &&
                            pinInput.value.length in 4..8,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Deactivate timer")
                    }
                } else {
                    Text("Choose how long your safety timer should run.")

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf(300, 600, 900, 1800).forEach { seconds ->
                            Button(
                                onClick = { selectedDuration.intValue = seconds }
                            ) {
                                Text(
                                    if (selectedDuration.intValue == seconds) {
                                        "✓ ${seconds / 60}m"
                                    } else {
                                        "${seconds / 60}m"
                                    }
                                )
                            }
                        }
                    }

                    if (!pinConfigured) {
                        OutlinedTextField(
                            value = pinInput.value,
                            onValueChange = {
                                if (it.length <= 8 && it.all(Char::isDigit)) {
                                    pinInput.value = it
                                }
                            },
                            label = { Text("Create safety PIN (4–8 digits)") },
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.NumberPassword
                            ),
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )

                        Button(
                            onClick = {
                                onSetupSafetyPin(pinInput.value)
                                pinInput.value = ""
                            },
                            enabled = pinInput.value.length in 4..8,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Set safety PIN")
                        }
                    } else {
                        Text("Your safety PIN is configured.")
                        Button(
                            onClick = {
                                onStartSafetyTimer(selectedDuration.intValue)
                            },
                            enabled = !isTimerSubmitting,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Start safety timer")
                        }
                    }
                }

                if (isTimerSubmitting) {
                    Text("Processing safety timer...")
                }

                timerMessage?.let {
                    Text(it, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }

        Text("If you need help, hold the SOS button for 1.5 seconds.")

        Surface(
            color = if (isSOSSubmitting) Color.Gray else Color(0xFFB71C1C),
            contentColor = Color.White,
            shape = MaterialTheme.shapes.large,
            modifier = Modifier
                .fillMaxWidth()
                .semantics { role = Role.Button }
                .pointerInput(isSOSSubmitting) {
                    if (!isSOSSubmitting) {
                        detectTapGestures(
                            onPress = {
                                coroutineScope {
                                    val holdJob = launch {
                                        delay(1500)
                                        onSOS()
                                    }
                                    tryAwaitRelease()
                                    holdJob.cancel()
                                }
                            }
                        )
                    }
                }
        ) {
            Text(
                text = if (isSOSSubmitting) {
                    "Sending SOS..."
                } else {
                    "SOS — HOLD FOR 1.5 SECONDS"
                },
                modifier = Modifier.padding(20.dp),
                style = MaterialTheme.typography.titleMedium
            )
        }

        sosMessage?.let {
            Text(it, style = MaterialTheme.typography.bodyMedium)
        }

        Text("Trusted Contacts", style = MaterialTheme.typography.titleLarge)
        Text("Choose people you trust for your safety plan.")

        Button(
            onClick = onAddContact,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Add contact")
        }

        if (contacts.isEmpty()) {
            Text("No trusted contacts added yet.")
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(contacts, key = { it.id }) { contact ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(contact.name)
                                Text(
                                    text = contact.phoneNumber,
                                    style = MaterialTheme.typography.bodyMedium
                                )
                            }

                            Button(onClick = { onRemoveContact(contact) }) {
                                Text("Remove")
                            }
                        }
                    }
                }
            }
        }
    }
}
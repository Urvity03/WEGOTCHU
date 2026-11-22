package com.wegotchu.app.safety

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay

@Composable
fun SafetyCheckInDialog(
    initialCountdownSeconds: Int = 60,
    reason: String = "Unusual motion or upcoming safety timer deadline detected.",
    onConfirmSafe: (String) -> Unit,
    onTriggerSOS: () -> Unit,
    onTimeout: () -> Unit,
    errorMessage: String? = null
) {
    var remainingSeconds by remember { mutableIntStateOf(initialCountdownSeconds) }
    var pinInput by remember { mutableStateOf("") }

    LaunchedEffect(key1 = remainingSeconds) {
        if (remainingSeconds > 0) {
            delay(1000L)
            remainingSeconds -= 1
        } else {
            onTimeout()
        }
    }

    AlertDialog(
        onDismissRequest = { /* Inviolable: user cannot simply tap outside to dismiss */ },
        title = {
            Text(
                text = "Safety Check-in Required",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.error
            )
        },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = reason,
                    style = MaterialTheme.typography.bodyMedium
                )

                Text(
                    text = "Time to auto-escalate: %02d:%02d".format(
                        remainingSeconds / 60,
                        remainingSeconds % 60
                    ),
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.error,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )

                Text(
                    text = "Enter your Safety PIN to confirm you are safe. If you do not respond, emergency contacts will be alerted.",
                    style = MaterialTheme.typography.bodySmall
                )

                OutlinedTextField(
                    value = pinInput,
                    onValueChange = {
                        if (it.length <= 8 && it.all(Char::isDigit)) {
                            pinInput = it
                        }
                    },
                    label = { Text("Safety PIN") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                if (errorMessage != null) {
                    Text(
                        text = errorMessage,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (pinInput.length in 4..8) {
                        onConfirmSafe(pinInput)
                    }
                },
                enabled = pinInput.length in 4..8
            ) {
                Text("I am safe")
            }
        },
        dismissButton = {
            OutlinedButton(
                onClick = onTriggerSOS,
                colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFFB71C1C))
            ) {
                Text("Trigger SOS now")
            }
        }
    )
}

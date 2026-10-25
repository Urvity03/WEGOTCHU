
package com.wegotchu.app.contacts

import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.graphics.Color
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
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "WEGOTCHU Safety",
            style = MaterialTheme.typography.headlineSmall
        )

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

        sosMessage?.let { message ->
            Text(
                text = message,
                style = MaterialTheme.typography.bodyMedium
            )
        }

        Text(
            text = "Trusted Contacts",
            style = MaterialTheme.typography.titleLarge
        )

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
                            Column(
                                modifier = Modifier.weight(1f)
                            ) {
                                Text(contact.name)
                                Text(
                                    text = contact.phoneNumber,
                                    style = MaterialTheme.typography.bodyMedium
                                )
                            }

                            Button(
                                onClick = { onRemoveContact(contact) }
                            ) {
                                Text("Remove")
                            }
                        }
                    }
                }
            }
        }
    }
}

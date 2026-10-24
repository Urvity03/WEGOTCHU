package com.wegotchu.app.contacts

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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun TrustedContactsScreen(
    contacts: List<TrustedContact>,
    onAddContact: () -> Unit,
    onRemoveContact: (TrustedContact) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "Trusted Contacts",
            style = MaterialTheme.typography.headlineSmall
        )

        Text(
            text = "Choose people you trust for your safety plan."
        )

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

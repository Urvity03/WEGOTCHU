package com.wegotchu.app

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities

class NetworkCollector(
    private val context: Context
) {

    fun getNetworkStatus(): String {

        val connectivityManager =
            context.getSystemService(
                Context.CONNECTIVITY_SERVICE
            ) as ConnectivityManager

        val network = connectivityManager.activeNetwork
            ?: return "NO_NETWORK"

        val capabilities =
            connectivityManager.getNetworkCapabilities(network)
                ?: return "NO_NETWORK"

        return when {
            capabilities.hasTransport(
                NetworkCapabilities.TRANSPORT_WIFI
            ) -> "WIFI"

            capabilities.hasTransport(
                NetworkCapabilities.TRANSPORT_CELLULAR
            ) -> "CELLULAR"

            capabilities.hasTransport(
                NetworkCapabilities.TRANSPORT_ETHERNET
            ) -> "ETHERNET"

            else -> "UNKNOWN"
        }
    }
}
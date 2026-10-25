package com.lacertastardust.utils

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.PowerManager
import android.provider.Settings

object BatteryOptimization {

    /**
     * Request standard Doze mode exemption.
     */
    fun requestExemptionIfNeeded(activity: Activity) {
        val pm = activity.getSystemService(PowerManager::class.java)
        if (!pm.isIgnoringBatteryOptimizations(activity.packageName)) {
            activity.startActivity(
                Intent(
                    Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                    Uri.parse("package:${activity.packageName}")
                )
            )
        }
    }

    /**
     * On Samsung devices, open the device-specific battery settings
     * so the user can set the app to "Unrestricted" — this prevents
     * Samsung from killing the Accessibility Service in the background.
     */
    fun openSamsungBatterySettings(activity: Activity) {
        try {
            // Samsung-specific battery usage detail screen
            val intent = Intent().apply {
                component = android.content.ComponentName(
                    "com.samsung.android.lool",
                    "com.samsung.android.sm.ui.battery.BatteryActivity"
                )
            }
            activity.startActivity(intent)
        } catch (e: Exception) {
            // Fall back to standard app info screen
            try {
                activity.startActivity(
                    Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                        data = Uri.parse("package:${activity.packageName}")
                    }
                )
            } catch (e2: Exception) {
                android.util.Log.e("BatteryOptimization", "Could not open battery settings: $e2")
            }
        }
    }

    fun isSamsungDevice(): Boolean {
        return android.os.Build.MANUFACTURER.lowercase() == "samsung"
    }
}

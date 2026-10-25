package com.lacertastardust.services

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.KeyEvent
import android.view.accessibility.AccessibilityEvent
import com.lacertastardust.services.RemoteService

class AccessibilityRemote : AccessibilityService() {

    private val tag = "AccessibilityRemote"

    companion object {
        // Controlled by RemoteService — true only when connected to Windows
        var isActive: Boolean = false

        // Set by RemoteService to forward signals to BlePeripheral
        var onSignal: ((String) -> Unit)? = null
    }

    override fun onKeyEvent(event: KeyEvent): Boolean {
        Log.d(tag, "onKeyEvent: keyCode=${event.keyCode} action=${event.action} isActive=$isActive")

        if (!isActive) {
            Log.d(tag, "Service not active — passing key through")
            return false
        }

        if (event.action != KeyEvent.ACTION_DOWN) return true

        return when (event.keyCode) {
            KeyEvent.KEYCODE_VOLUME_UP -> {
                Log.d(tag, "Volume UP intercepted → invoking NEXT signal")
                if (onSignal == null) Log.e(tag, "onSignal is NULL — signal won't be sent!")
                onSignal?.invoke("NEXT")
                Log.d(tag, "NEXT signal invoked")
                true
            }
            KeyEvent.KEYCODE_VOLUME_DOWN -> {
                Log.d(tag, "Volume DOWN intercepted → invoking PREV signal")
                if (onSignal == null) Log.e(tag, "onSignal is NULL — signal won't be sent!")
                onSignal?.invoke("PREV")
                Log.d(tag, "PREV signal invoked")
                true
            }
            else -> false
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent) { }

    override fun onInterrupt() {
        Log.d(tag, "Accessibility service interrupted")
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.d(tag, "Accessibility service connected")

        // Explicitly set key filter flag at runtime — required on Samsung
        // devices where the XML config alone is not always respected
        val info = serviceInfo
        info.flags = info.flags or
                android.accessibilityservice.AccessibilityServiceInfo.FLAG_REQUEST_FILTER_KEY_EVENTS
        serviceInfo = info
        Log.d(tag, "Key filter flag set: ${info.flags}")

        // Wire signal callback to BlePeripheral via RemoteService
        onSignal = { signal ->
            RemoteService.instance?.let { service ->
                Log.d(tag, "Signal '$signal' → forwarding to BlePeripheral")
                service.forwardSignal(signal)
            } ?: Log.e(tag, "Signal '$signal' dropped — RemoteService not running!")
        }
    }

    override fun onDestroy() {
        isActive = false
        onSignal = null
        super.onDestroy()
        Log.d(tag, "Accessibility service destroyed")
    }
}

package com.lacertastardust.services

import android.app.*
import android.bluetooth.BluetoothDevice
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.lacertastardust.R
import com.lacertastardust.ble.BlePeripheral
import com.lacertastardust.ui.ConnectionRequestActivity
import com.lacertastardust.ui.MainActivity

class RemoteService : Service() {

    private val tag = "RemoteService"

    companion object {
        // Use explicit package intent for disconnect so PendingIntent
        // works even with RECEIVER_NOT_EXPORTED
        const val ACTION_DISCONNECT  = "com.lacertastardust.ACTION_DISCONNECT"
        const val ACTION_ACCEPT      = "com.lacertastardust.ACTION_ACCEPT"
        const val ACTION_DECLINE     = "com.lacertastardust.ACTION_DECLINE"
        const val ACTION_STOP        = "com.lacertastardust.ACTION_STOP"
        const val EXTRA_DEVICE_NAME  = "device_name"

        const val NOTIF_CHANNEL_ID   = "lacerta_stardust_channel"
        const val NOTIF_ID           = 1

        var instance: RemoteService? = null
    }

    private lateinit var blePeripheral: BlePeripheral
    private var pendingDevice: BluetoothDevice? = null
    var connectedDeviceName: String? = null

    // Direct UI callback — more reliable than broadcast when app is in foreground
    var onUiUpdate: ((connected: Boolean, deviceName: String) -> Unit)? = null

    // Guard against multiple popups from repeated GATT callbacks
    private var connectionRequestPending = false

    // ------------------------------------------------------------------ //
    //  Lifecycle                                                          //
    // ------------------------------------------------------------------ //

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()

        blePeripheral = BlePeripheral(
            context = this,
            onDeviceConnected = ::onDeviceConnected,
            onDeviceDisconnected = ::onDeviceDisconnected
        )

        // onSignal is now wired in AccessibilityRemote.onServiceConnected()
        // so the order of service startup doesn't matter

        // FIX 1: Use RECEIVER_EXPORTED so PendingIntent from notification
        // can reach our receiver (notification actions come from system)
        val filter = IntentFilter().apply {
            addAction(ACTION_DISCONNECT)
            addAction(ACTION_ACCEPT)
            addAction(ACTION_DECLINE)
            addAction(ACTION_STOP)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(actionReceiver, filter, RECEIVER_EXPORTED)
        } else {
            registerReceiver(actionReceiver, filter)
        }

        // Screen on/off receiver — rewires onSignal if screen was off
        // System broadcasts don't need RECEIVER_EXPORTED flag
        registerReceiver(
            screenReceiver,
            IntentFilter().apply {
                addAction(Intent.ACTION_SCREEN_ON)
                addAction(Intent.ACTION_SCREEN_OFF)
            }
        )

        Log.d(tag, "RemoteService created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIF_ID, buildIdleNotification())
        blePeripheral.start()
        Log.d(tag, "RemoteService started — advertising")
        return START_STICKY
    }

    override fun onDestroy() {
        instance = null
        onUiUpdate = null
        blePeripheral.stop()
        AccessibilityRemote.isActive = false
        AccessibilityRemote.onSignal = null
        connectionRequestPending = false
        unregisterReceiver(actionReceiver)
        try { unregisterReceiver(screenReceiver) } catch (e: Exception) { }
        super.onDestroy()
        Log.d(tag, "RemoteService destroyed")
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // ------------------------------------------------------------------ //
    //  Signal forwarding from AccessibilityRemote                        //
    // ------------------------------------------------------------------ //

    fun forwardSignal(signal: String) {
        if (!AccessibilityRemote.isActive) {
            Log.d(tag, "forwardSignal('$signal') ignored — not active")
            return
        }
        Log.d(tag, "forwardSignal('$signal') → BlePeripheral")
        blePeripheral.sendSignal(signal)
    }

    // ------------------------------------------------------------------ //
    //  BLE callbacks                                                      //
    // ------------------------------------------------------------------ //

    private fun onDeviceConnected(device: BluetoothDevice) {
        // FIX 3: Ignore repeated GATT callbacks — only show one popup at a time
        if (connectionRequestPending) {
            Log.d(tag, "Connection request already pending — ignoring duplicate")
            return
        }
        connectionRequestPending = true
        pendingDevice = device
        Log.d(tag, "Connection request from: ${device.name ?: device.address}")

        android.os.Handler(mainLooper).postDelayed({
            // Only launch if still pending (not already accepted/declined)
            if (connectionRequestPending) {
                val intent = Intent(this, ConnectionRequestActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
                    putExtra(EXTRA_DEVICE_NAME, device.name ?: device.address)
                }
                startActivity(intent)
            }
        }, 200)
    }

    private fun onDeviceDisconnected() {
        // FIX 2: Reset GATT server fully on disconnect so next connection works
        connectionRequestPending = false
        AccessibilityRemote.isActive = false
        connectedDeviceName = null
        updateNotification(buildIdleNotification())
        notifyMainActivity(connected = false)

        // Restart BLE peripheral so it's ready for next connection
        blePeripheral.stop()
        blePeripheral.start()

        Log.d(tag, "Disconnected — BLE reset, advertising resumed")
    }

    // ------------------------------------------------------------------ //
    //  Accept / Decline / Disconnect                                      //
    // ------------------------------------------------------------------ //

    fun acceptConnection() {
        connectionRequestPending = false
        AccessibilityRemote.isActive = true
        connectedDeviceName = pendingDevice?.name ?: pendingDevice?.address ?: "Unknown"
        updateNotification(buildConnectedNotification())

        // Warn if accessibility service isn't running
        val accessibilityRunning = AccessibilityRemote.onSignal != null
        Log.d(tag, "acceptConnection — AccessibilityRemote.onSignal set: $accessibilityRunning")
        if (!accessibilityRunning) {
            Log.e(tag, "WARNING: Accessibility service not running — volume buttons won't work!")
        }

        notifyMainActivity(connected = true, deviceName = connectedDeviceName!!)

        Log.d(tag, "Connection accepted — volume buttons hijacked")
    }

    fun declineConnection() {
        connectionRequestPending = false
        blePeripheral.sendSignal("DISCONNECT")
        android.os.Handler(mainLooper).postDelayed({
            pendingDevice = null
            blePeripheral.stop()
            blePeripheral.start()
        }, 300)
        Log.d(tag, "Connection declined — advertising resumed")
    }

    fun disconnect() {
        connectionRequestPending = false
        AccessibilityRemote.isActive = false
        connectedDeviceName = null

        blePeripheral.sendSignal("DISCONNECT")
        android.os.Handler(mainLooper).postDelayed({
            pendingDevice = null
            blePeripheral.stop()
            blePeripheral.start()
            updateNotification(buildIdleNotification())
            notifyMainActivity(connected = false)
        }, 150)

        Log.d(tag, "Disconnected manually — sent DISCONNECT signal")
    }

    // ------------------------------------------------------------------ //
    //  Broadcast receiver                                                 //
    // ------------------------------------------------------------------ //

    private val screenReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                Intent.ACTION_SCREEN_ON -> {
                    Log.d(tag, "Screen ON — rewiring AccessibilityRemote.onSignal")
                    // Rewire in case Samsung cleared it while screen was off
                    AccessibilityRemote.onSignal = { signal -> forwardSignal(signal) }
                }
                Intent.ACTION_SCREEN_OFF -> {
                    Log.d(tag, "Screen OFF — service remains active")
                }
            }
        }
    }

    private val actionReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            Log.d(tag, "Broadcast received: ${intent.action}")
            when (intent.action) {
                ACTION_DISCONNECT -> disconnect()
                ACTION_ACCEPT     -> acceptConnection()
                ACTION_DECLINE    -> declineConnection()
                ACTION_STOP       -> stopSelf()
            }
        }
    }

    private fun notifyMainActivity(connected: Boolean, deviceName: String = "") {
        // Direct callback — instant update when app is in foreground
        android.os.Handler(mainLooper).post {
            onUiUpdate?.invoke(connected, deviceName)
        }
        // Broadcast — fallback when app is in background or receiver is registered
        sendBroadcast(Intent(MainActivity.ACTION_UPDATE_UI).apply {
            putExtra(MainActivity.EXTRA_CONNECTED, connected)
            if (deviceName.isNotEmpty())
                putExtra(MainActivity.EXTRA_DEVICE_NAME, deviceName)
        })
    }

    // ------------------------------------------------------------------ //
    //  Notifications                                                      //
    // ------------------------------------------------------------------ //

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NOTIF_CHANNEL_ID,
                "Lacerta Stardust",
                NotificationManager.IMPORTANCE_LOW
            ).apply { setShowBadge(false) }
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    private fun buildIdleNotification(): Notification {
        val openIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        val stopIntent = PendingIntent.getBroadcast(
            this, 2,
            Intent(ACTION_STOP).apply { `package` = packageName },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        return NotificationCompat.Builder(this, NOTIF_CHANNEL_ID)
            .setContentTitle("Lacerta Stardust")
            .setContentText("Waiting for connection...")
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(openIntent)
            .addAction(R.drawable.ic_disconnect, "Stop", stopIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }

    private fun buildConnectedNotification(): Notification {
        val openIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        // FIX 1: Add explicit package to intent so system can deliver it
        val disconnectIntent = PendingIntent.getBroadcast(
            this, 1,
            Intent(ACTION_DISCONNECT).apply { `package` = packageName },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val stopIntent = PendingIntent.getBroadcast(
            this, 2,
            Intent(ACTION_STOP).apply { `package` = packageName },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, NOTIF_CHANNEL_ID)
            .setContentTitle("Lacerta Stardust")
            .setContentText("Connected — volume buttons control your slides")
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(openIntent)
            .addAction(R.drawable.ic_disconnect, "Disconnect", disconnectIntent)
            .addAction(R.drawable.ic_disconnect, "Stop", stopIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }

    private fun updateNotification(notification: Notification) {
        getSystemService(NotificationManager::class.java)
            .notify(NOTIF_ID, notification)
    }
}

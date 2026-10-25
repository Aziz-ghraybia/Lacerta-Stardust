package com.lacertastardust.ui

import android.Manifest
import android.accessibilityservice.AccessibilityServiceInfo
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.view.accessibility.AccessibilityManager
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.lacertastardust.databinding.ActivityMainBinding
import com.lacertastardust.services.AccessibilityRemote
import com.lacertastardust.services.RemoteService
import com.lacertastardust.utils.BatteryOptimization

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    companion object {
        const val ACTION_UPDATE_UI  = "com.lacertastardust.UPDATE_UI"
        const val EXTRA_CONNECTED   = "connected"
        const val EXTRA_DEVICE_NAME = "device_name"
    }

    // ------------------------------------------------------------------ //
    //  Permission launcher                                               //
    // ------------------------------------------------------------------ //

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val allGranted = results.values.all { it }
        if (allGranted) {
            startRemoteService()
            BatteryOptimization.requestExemptionIfNeeded(this)
        } else {
            AlertDialog.Builder(this)
                .setTitle("Bluetooth Permission Required")
                .setMessage("Lacerta Stardust needs Bluetooth permissions to work. Please grant them.")
                .setPositiveButton("Try Again") { _, _ -> requestBluetoothPermissions() }
                .setNegativeButton("Cancel", null)
                .show()
        }
    }

    // ------------------------------------------------------------------ //
    //  Lifecycle                                                          //
    // ------------------------------------------------------------------ //

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupUI()
        requestBluetoothPermissions()

        // Auto-prompt for accessibility on every launch if disabled
        // Samsung kills it aggressively so this is necessary
        if (!isAccessibilityServiceEnabled()) {
            android.os.Handler(mainLooper).postDelayed({
                showAccessibilityExplanation()
            }, 800)
        }
    }

    private fun requestBluetoothPermissions() {
        val permissions = mutableListOf<String>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            permissions += listOf(
                Manifest.permission.BLUETOOTH_ADVERTISE,
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.BLUETOOTH_SCAN
            )
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions += Manifest.permission.POST_NOTIFICATIONS
        }

        val allGranted = permissions.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }

        if (allGranted || permissions.isEmpty()) {
            startRemoteService()
            BatteryOptimization.requestExemptionIfNeeded(this)
        } else {
            permissionLauncher.launch(permissions.toTypedArray())
        }
    }

    override fun onResume() {
        super.onResume()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(uiUpdateReceiver, IntentFilter(ACTION_UPDATE_UI), RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(uiUpdateReceiver, IntentFilter(ACTION_UPDATE_UI))
        }

        // Listen for Bluetooth state changes while app is visible
        registerReceiver(
            bluetoothStateReceiver,
            IntentFilter(BluetoothAdapter.ACTION_STATE_CHANGED)
        )

        // Check Bluetooth state immediately on resume
        checkBluetoothState()
        refreshAccessibilityWarning()

        // Wire direct callback so UI updates instantly without broadcast
        RemoteService.instance?.onUiUpdate = { connected, deviceName ->
            runOnUiThread {
                if (connected) setConnectedState(deviceName.ifEmpty { "Unknown Device" })
                else setDisconnectedState()
            }
        }

        // Sync UI with current state on resume
        val service = RemoteService.instance
        if (service != null) {
            if (AccessibilityRemote.isActive) {
                setConnectedState(service.connectedDeviceName ?: "Unknown Device")
            } else {
                setDisconnectedState()
            }
        }
    }

    override fun onPause() {
        super.onPause()
        unregisterReceiver(uiUpdateReceiver)
        try { unregisterReceiver(bluetoothStateReceiver) } catch (e: Exception) { }
        RemoteService.instance?.onUiUpdate = null
    }

    // ------------------------------------------------------------------ //
    //  UI                                                                 //
    // ------------------------------------------------------------------ //

    private fun setupUI() {
        binding.btnEnableAccessibility.setOnClickListener {
            showAccessibilityExplanation()
        }
        setDisconnectedState()
    }

    private fun setConnectedState(deviceName: String) {
        binding.tvStatus.text = "★  STARS ALIGNED  ★"
        binding.tvStatus.setTextColor(android.graphics.Color.parseColor("#f0b429"))
        binding.tvDeviceName.text = deviceName
        binding.tvDeviceName.visibility = View.VISIBLE
        binding.tvHint.text =
            "Volume buttons are controlling your slides.\nPull down the notification to disconnect."
        binding.tvHint.setTextColor(android.graphics.Color.parseColor("#6a8fff"))
    }

    private fun setDisconnectedState() {
        binding.tvStatus.text = "✦  AWAITING ALIGNMENT"
        binding.tvStatus.setTextColor(android.graphics.Color.parseColor("#3a4a6a"))
        binding.tvDeviceName.visibility = View.GONE
        binding.tvHint.text =
            "Open Lacerta Stardust on your Windows PC\nand click Connect to begin."
        binding.tvHint.setTextColor(android.graphics.Color.parseColor("#3a4a6a"))
    }

    private fun refreshAccessibilityWarning() {
        val enabled = isAccessibilityServiceEnabled()
        binding.layoutAccessibilityWarning.visibility =
            if (enabled) View.GONE else View.VISIBLE
    }

    // ------------------------------------------------------------------ //
    //  Bluetooth state                                                   //
    // ------------------------------------------------------------------ //

    fun openBluetoothSettings(view: View) {
        startActivity(Intent(android.provider.Settings.ACTION_BLUETOOTH_SETTINGS))
    }

    private fun checkBluetoothState() {
        val bm = getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        val adapter = bm.adapter
        if (adapter == null || !adapter.isEnabled) {
            showBluetoothWarning(true)
        } else {
            showBluetoothWarning(false)
        }
    }

    private fun showBluetoothWarning(show: Boolean) {
        binding.layoutBluetoothWarning.visibility = if (show) View.VISIBLE else View.GONE
    }

    private val bluetoothStateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val state = intent.getIntExtra(
                BluetoothAdapter.EXTRA_STATE, BluetoothAdapter.ERROR
            )
            when (state) {
                BluetoothAdapter.STATE_OFF -> {
                    showBluetoothWarning(true)
                    // If connected, the connection will drop — UI will update via onUiUpdate
                }
                BluetoothAdapter.STATE_ON -> {
                    showBluetoothWarning(false)
                }
            }
        }
    }

    // ------------------------------------------------------------------ //
    //  Accessibility check                                                //
    // ------------------------------------------------------------------ //

    private fun isAccessibilityServiceEnabled(): Boolean {
        val am = getSystemService(Context.ACCESSIBILITY_SERVICE) as AccessibilityManager
        return am.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
            .any { it.resolveInfo.serviceInfo.packageName == packageName }
    }

    private fun showAccessibilityExplanation() {
        val message = buildString {
            append(
                "Lacerta Stardust needs Accessibility access to intercept " +
                "volume button presses so they control your slides instead of " +
                "changing the phone volume.\n\n" +
                "On the next screen, find \"Lacerta Stardust\" and enable it."
            )
            if (BatteryOptimization.isSamsungDevice()) {
                append(
                    "\n\n⚠ Samsung device detected: After enabling Accessibility, " +
                    "also set Battery usage to \"Unrestricted\" to prevent Samsung " +
                    "from disabling it in the background."
                )
            }
        }

        AlertDialog.Builder(this)
            .setTitle("Enable Accessibility Permission")
            .setMessage(message)
            .setPositiveButton("Open Settings") { _, _ ->
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            }
            .apply {
                if (BatteryOptimization.isSamsungDevice()) {
                    setNeutralButton("Battery Settings") { _, _ ->
                        BatteryOptimization.openSamsungBatterySettings(this@MainActivity)
                    }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    // ------------------------------------------------------------------ //
    //  Service                                                            //
    // ------------------------------------------------------------------ //

    private fun startRemoteService() {
        startForegroundService(Intent(this, RemoteService::class.java))
    }

    // ------------------------------------------------------------------ //
    //  Broadcast receiver                                                 //
    // ------------------------------------------------------------------ //

    private val uiUpdateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val connected = intent.getBooleanExtra(EXTRA_CONNECTED, false)
            if (connected) {
                val name = intent.getStringExtra(EXTRA_DEVICE_NAME) ?: "Unknown Device"
                setConnectedState(name)
            } else {
                setDisconnectedState()
            }
        }
    }
}

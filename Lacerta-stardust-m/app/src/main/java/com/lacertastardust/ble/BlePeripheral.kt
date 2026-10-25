package com.lacertastardust.ble

import android.bluetooth.*
import android.bluetooth.le.AdvertiseCallback
import android.bluetooth.le.AdvertiseData
import android.bluetooth.le.AdvertiseSettings
import android.bluetooth.le.BluetoothLeAdvertiser
import android.content.Context
import android.os.ParcelUuid
import android.util.Log
import java.util.UUID

// Must match the Windows app exactly
val SERVICE_UUID: UUID     = UUID.fromString("0000ff00-0000-1000-8000-00805f9b34fb")
val COMMAND_CHAR_UUID: UUID = UUID.fromString("0000ff01-0000-1000-8000-00805f9b34fb")
val CCCD_UUID: UUID         = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

class BlePeripheral(
    private val context: Context,
    private val onDeviceConnected: (device: BluetoothDevice) -> Unit,
    private val onDeviceDisconnected: () -> Unit,
) {
    private val tag = "BlePeripheral"

    private val bluetoothManager =
        context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val bluetoothAdapter: BluetoothAdapter = bluetoothManager.adapter

    private var gattServer: BluetoothGattServer? = null
    private var advertiser: BluetoothLeAdvertiser? = null
    private var connectedDevice: BluetoothDevice? = null
    private lateinit var commandCharacteristic: BluetoothGattCharacteristic

    // ------------------------------------------------------------------ //
    //  Public API                                                         //
    // ------------------------------------------------------------------ //

    fun start() {
        startGattServer()
        startAdvertising()
        Log.d(tag, "BLE peripheral started — advertising as Lacerta Stardust")
    }

    fun stop() {
        try { advertiser?.stopAdvertising(advertiseCallback) } catch (e: Exception) { }
        try { gattServer?.close() } catch (e: Exception) { }
        connectedDevice = null
        Log.d(tag, "BLE peripheral stopped")
    }

    fun sendSignal(signal: String) {
        val device = connectedDevice
        val server  = gattServer

        if (device == null) {
            Log.e(tag, "sendSignal('$signal') — NO connected device!")
            return
        }
        if (server == null) {
            Log.e(tag, "sendSignal('$signal') — NO GATT server!")
            return
        }

        commandCharacteristic.value = signal.toByteArray(Charsets.UTF_8)
        val result = server.notifyCharacteristicChanged(device, commandCharacteristic, false)
        Log.d(tag, "sendSignal('$signal') → notifyCharacteristicChanged result: $result")
    }

    fun isConnected() = connectedDevice != null

    // ------------------------------------------------------------------ //
    //  GATT Server                                                        //
    // ------------------------------------------------------------------ //

    private fun startGattServer() {
        gattServer = bluetoothManager.openGattServer(context, gattServerCallback)

        commandCharacteristic = BluetoothGattCharacteristic(
            COMMAND_CHAR_UUID,
            BluetoothGattCharacteristic.PROPERTY_NOTIFY or
                    BluetoothGattCharacteristic.PROPERTY_READ,
            BluetoothGattCharacteristic.PERMISSION_READ
        )

        // CCCD descriptor — required for notifications
        val cccd = BluetoothGattDescriptor(
            CCCD_UUID,
            BluetoothGattDescriptor.PERMISSION_READ or
                    BluetoothGattDescriptor.PERMISSION_WRITE
        )
        commandCharacteristic.addDescriptor(cccd)

        val service = BluetoothGattService(
            SERVICE_UUID,
            BluetoothGattService.SERVICE_TYPE_PRIMARY
        )
        service.addCharacteristic(commandCharacteristic)
        gattServer?.addService(service)
    }

    private val gattServerCallback = object : BluetoothGattServerCallback() {

        override fun onConnectionStateChange(
            device: BluetoothDevice, status: Int, newState: Int
        ) {
            when (newState) {
                BluetoothProfile.STATE_CONNECTED -> {
                    connectedDevice = device
                    Log.d(tag, "Windows connected: ${device.address}")
                    onDeviceConnected(device)
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    connectedDevice = null
                    Log.d(tag, "Windows disconnected")
                    onDeviceDisconnected()
                    // Resume advertising so Windows can connect again next time
                    startAdvertising()
                }
            }
        }

        override fun onDescriptorWriteRequest(
            device: BluetoothDevice, requestId: Int,
            descriptor: BluetoothGattDescriptor,
            preparedWrite: Boolean, responseNeeded: Boolean,
            offset: Int, value: ByteArray
        ) {
            descriptor.value = value
            if (responseNeeded) {
                gattServer?.sendResponse(
                    device, requestId,
                    BluetoothGatt.GATT_SUCCESS, 0, value
                )
            }
        }
    }

    // ------------------------------------------------------------------ //
    //  BLE Advertising                                                    //
    // ------------------------------------------------------------------ //

    private fun startAdvertising() {
        advertiser = bluetoothAdapter.bluetoothLeAdvertiser
        if (advertiser == null) {
            Log.e(tag, "BLE advertising not supported on this device")
            return
        }

        val settings = AdvertiseSettings.Builder()
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
            .setConnectable(true)
            .setTimeout(0)
            .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_MEDIUM)
            .build()

        val data = AdvertiseData.Builder()
            .setIncludeDeviceName(true)
            .addServiceUuid(ParcelUuid(SERVICE_UUID))
            .build()

        advertiser?.startAdvertising(settings, data, advertiseCallback)
    }

    private val advertiseCallback = object : AdvertiseCallback() {
        override fun onStartSuccess(settingsInEffect: AdvertiseSettings) {
            Log.d(tag, "Advertising started successfully")
        }
        override fun onStartFailure(errorCode: Int) {
            Log.e(tag, "Advertising failed with error code: $errorCode")
        }
    }
}

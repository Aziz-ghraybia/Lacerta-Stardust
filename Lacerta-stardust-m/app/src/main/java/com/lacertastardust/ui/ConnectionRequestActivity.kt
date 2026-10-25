package com.lacertastardust.ui

import android.os.Bundle
import android.view.WindowManager
import androidx.appcompat.app.AppCompatActivity
import com.lacertastardust.databinding.ActivityConnectionRequestBinding
import com.lacertastardust.services.RemoteService

class ConnectionRequestActivity : AppCompatActivity() {

    private lateinit var binding: ActivityConnectionRequestBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Show over lock screen and wake display
        window.addFlags(
            WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON        or
            WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD      or
            WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED      or
            WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
        )

        binding = ActivityConnectionRequestBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val deviceName = intent.getStringExtra(RemoteService.EXTRA_DEVICE_NAME)
            ?: "Unknown Device"
        binding.tvDeviceName.text = "\"$deviceName\" wants to connect"

        binding.btnAccept.setOnClickListener {
            RemoteService.instance?.acceptConnection()
            finish()
        }

        binding.btnDecline.setOnClickListener {
            RemoteService.instance?.declineConnection()
            finish()
        }
    }
}

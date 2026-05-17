package com.example.alfred_financas_mobile

import android.Manifest
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import org.json.JSONArray

class MainActivity : FlutterActivity() {
    private val channelName = "alfred_financas/notifications"
    private val smsPermissionRequestCode = 4040
    private var smsPermissionResult: MethodChannel.Result? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "isNotificationAccessEnabled" -> {
                        result.success(isNotificationAccessEnabled())
                    }
                    "openNotificationAccessSettings" -> {
                        val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
                        startActivity(intent)
                        result.success(true)
                    }
                    "setApiBaseUrl" -> {
                        val apiBaseUrl = call.argument<String>("api_base_url").orEmpty()
                        NotificationCaptureStore.setApiBaseUrl(this, apiBaseUrl)
                        result.success(true)
                    }
                    "setSmsCaptureConfig" -> {
                        val smsEnabled = call.argument<Boolean>("sms_enabled") == true
                        val bancos = call.argument<List<String>>("bancos_selecionados") ?: emptyList()
                        val mappingRaw = call.argument<Map<*, *>>("mapeamento_cartao_ultimos4") ?: emptyMap<Any, Any>()
                        val mapping = mappingRaw.entries.associate { entry ->
                            entry.key.toString() to entry.value.toString()
                        }
                        NotificationCaptureStore.setSmsCaptureConfig(
                            context = this,
                            smsEnabled = smsEnabled,
                            bancosSelecionados = bancos,
                            mapeamentoCartaoUltimos4 = mapping,
                        )
                        result.success(true)
                    }
                    "isSmsPermissionGranted" -> {
                        result.success(isSmsPermissionGranted())
                    }
                    "requestSmsPermission" -> {
                        if (isSmsPermissionGranted()) {
                            result.success(true)
                        } else {
                            smsPermissionResult = result
                            ActivityCompat.requestPermissions(
                                this,
                                arrayOf(Manifest.permission.RECEIVE_SMS),
                                smsPermissionRequestCode,
                            )
                        }
                    }
                    "listPendingFinancialNotifications" -> {
                        val items: JSONArray = NotificationCaptureStore.listPendingNotifications(this)
                        val list = mutableListOf<Map<String, Any?>>()
                        for (index in 0 until items.length()) {
                            val obj = items.getJSONObject(index)
                            list.add(
                                mapOf(
                                    "package_name" to obj.optString("package_name"),
                                    "app_name" to obj.optString("app_name"),
                                    "title" to jsonValueToNullable(obj.opt("title")),
                                    "text" to obj.optString("text"),
                                    "sub_text" to jsonValueToNullable(obj.opt("sub_text")),
                                    "posted_at" to obj.optString("posted_at"),
                                    "notification_key" to obj.optString("notification_key"),
                                )
                            )
                        }
                        result.success(list)
                    }
                    "consumePendingFinancialNotifications" -> {
                        val items: JSONArray = NotificationCaptureStore.listPendingNotifications(this)
                        val list = mutableListOf<Map<String, Any?>>()
                        for (index in 0 until items.length()) {
                            val obj = items.getJSONObject(index)
                            list.add(
                                mapOf(
                                    "package_name" to obj.optString("package_name"),
                                    "app_name" to obj.optString("app_name"),
                                    "title" to jsonValueToNullable(obj.opt("title")),
                                    "text" to obj.optString("text"),
                                    "sub_text" to jsonValueToNullable(obj.opt("sub_text")),
                                    "posted_at" to obj.optString("posted_at"),
                                    "notification_key" to obj.optString("notification_key"),
                                )
                            )
                        }
                        result.success(list)
                    }
                    "removePendingFinancialNotification" -> {
                        val notificationKey = call.argument<String>("notification_key").orEmpty()
                        NotificationCaptureStore.removePendingNotification(this, notificationKey)
                        result.success(true)
                    }
                    "getLastNotificationProcessedAt" -> {
                        result.success(NotificationCaptureStore.getLastProcessedAt(this))
                    }
                    "getPendingOpenRoute" -> {
                        val route = intent?.getStringExtra("open_route")
                        intent?.removeExtra("open_route")
                        result.success(route)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != smsPermissionRequestCode) return
        val granted = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED
        smsPermissionResult?.success(granted)
        smsPermissionResult = null
    }

    private fun isNotificationAccessEnabled(): Boolean {
        val enabled = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
        val componentName = ComponentName(this, AlfredNotificationListenerService::class.java)
        return enabled?.contains(componentName.flattenToString()) == true
    }

    private fun isSmsPermissionGranted(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECEIVE_SMS,
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun jsonValueToNullable(value: Any?): Any? {
        return if (value == org.json.JSONObject.NULL) null else value
    }
}

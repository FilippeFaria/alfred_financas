package com.example.alfred_financas_mobile

import android.content.ComponentName
import android.content.Intent
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import org.json.JSONArray

class MainActivity : FlutterActivity() {
    private val channelName = "alfred_financas/notifications"

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
                    "consumePendingFinancialNotifications" -> {
                        val items: JSONArray = NotificationCaptureStore.consume(this)
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
                    "getLastNotificationProcessedAt" -> {
                        result.success(NotificationCaptureStore.getLastProcessedAt(this))
                    }
                    else -> result.notImplemented()
                }
            }
    }

    private fun isNotificationAccessEnabled(): Boolean {
        val enabled = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
        val componentName = ComponentName(this, AlfredNotificationListenerService::class.java)
        return enabled?.contains(componentName.flattenToString()) == true
    }

    private fun jsonValueToNullable(value: Any?): Any? {
        return if (value == org.json.JSONObject.NULL) null else value
    }
}

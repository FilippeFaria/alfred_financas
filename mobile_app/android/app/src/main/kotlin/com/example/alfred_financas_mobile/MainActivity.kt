package com.example.alfred_financas_mobile

import android.Manifest
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.provider.Telephony
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

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
                    "getSmsPermissionStatus" -> {
                        result.success(
                            mapOf(
                                "receive_sms" to isSmsReceivePermissionGranted(),
                                "read_sms" to isSmsReadPermissionGranted(),
                                "all_required" to isSmsPermissionGranted(),
                            )
                        )
                    }
                    "requestSmsPermission" -> {
                        if (isSmsPermissionGranted()) {
                            result.success(true)
                        } else {
                            smsPermissionResult = result
                            ActivityCompat.requestPermissions(
                                this,
                                arrayOf(Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_SMS),
                                smsPermissionRequestCode,
                            )
                        }
                    }
                    "importRecentSmsEvents" -> {
                        val hours = call.argument<Int>("hours") ?: 48
                        val maxItems = call.argument<Int>("max_items") ?: 200
                        result.success(importRecentSmsEvents(hours = hours, maxItems = maxItems))
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
                    "listPendingSmsEvents" -> {
                        val items: JSONArray = NotificationCaptureStore.listPendingSms(this)
                        val list = mutableListOf<Map<String, Any?>>()
                        for (index in 0 until items.length()) {
                            val obj = items.getJSONObject(index)
                            list.add(
                                mapOf(
                                    "sender" to obj.optString("sender"),
                                    "text" to obj.optString("text"),
                                    "received_at" to obj.optString("received_at"),
                                    "sms_message_id" to obj.optString("sms_message_id"),
                                )
                            )
                        }
                        result.success(list)
                    }
                    "removePendingSmsEvent" -> {
                        val smsMessageId = call.argument<String>("sms_message_id").orEmpty()
                        NotificationCaptureStore.removePendingSms(this, smsMessageId)
                        result.success(true)
                    }
                    "getCaptureDiagnostics" -> {
                        val items: JSONArray = NotificationCaptureStore.listCaptureDiagnostics(this)
                        val list = mutableListOf<Map<String, Any?>>()
                        for (index in 0 until items.length()) {
                            list.add(jsonObjectToMap(items.getJSONObject(index)))
                        }
                        result.success(list)
                    }
                    "clearCaptureDiagnostics" -> {
                        NotificationCaptureStore.clearCaptureDiagnostics(this)
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
        val granted = isSmsPermissionGranted()
        smsPermissionResult?.success(granted)
        smsPermissionResult = null
    }

    private fun isNotificationAccessEnabled(): Boolean {
        val enabled = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
        val componentName = ComponentName(this, AlfredNotificationListenerService::class.java)
        return enabled?.contains(componentName.flattenToString()) == true
    }

    private fun isSmsPermissionGranted(): Boolean {
        return isSmsReceivePermissionGranted() && isSmsReadPermissionGranted()
    }

    private fun isSmsReceivePermissionGranted(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECEIVE_SMS,
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun isSmsReadPermissionGranted(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.READ_SMS,
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun importRecentSmsEvents(hours: Int, maxItems: Int): Map<String, Any> {
        val clampedHours = hours.coerceIn(1, 168)
        val clampedMaxItems = maxItems.coerceIn(1, 400)

        if (!isSmsPermissionGranted()) {
            val hasReceive = isSmsReceivePermissionGranted()
            val hasRead = isSmsReadPermissionGranted()
            NotificationCaptureStore.recordCaptureDiagnostic(
                context = this,
                source = "android_sms",
                stage = "manual_import",
                status = "blocked",
                eventKey = null,
                message = "missing_sms_permissions",
                details = JSONObject()
                    .put("receive_sms", hasReceive)
                    .put("read_sms", hasRead),
            )
            return mapOf(
                "imported" to 0,
                "scanned" to 0,
                "hours" to clampedHours,
                "blocked" to true,
                "receive_sms" to hasReceive,
                "read_sms" to hasRead,
            )
        }

        val now = System.currentTimeMillis()
        val sinceMs = now - (clampedHours.toLong() * 60L * 60L * 1000L)
        val projection = arrayOf(
            Telephony.Sms.ADDRESS,
            Telephony.Sms.BODY,
            Telephony.Sms.DATE,
        )
        val selection = "${Telephony.Sms.DATE} >= ?"
        val selectionArgs = arrayOf(sinceMs.toString())
        val sortOrder = "${Telephony.Sms.DATE} DESC"

        var scanned = 0
        var imported = 0
        var skippedBlank = 0

        val cursor = contentResolver.query(
            Telephony.Sms.Inbox.CONTENT_URI,
            projection,
            selection,
            selectionArgs,
            sortOrder,
        )

        cursor?.use {
            val senderIdx = it.getColumnIndex(Telephony.Sms.ADDRESS)
            val bodyIdx = it.getColumnIndex(Telephony.Sms.BODY)
            val dateIdx = it.getColumnIndex(Telephony.Sms.DATE)
            while (it.moveToNext() && scanned < clampedMaxItems) {
                scanned += 1
                val sender = if (senderIdx >= 0) (it.getString(senderIdx) ?: "").trim() else ""
                val body = if (bodyIdx >= 0) (it.getString(bodyIdx) ?: "").trim() else ""
                val dateMs = if (dateIdx >= 0) it.getLong(dateIdx) else 0L
                if (sender.isBlank() || body.isBlank() || dateMs <= 0L) {
                    skippedBlank += 1
                    continue
                }

                val smsMessageId = "$sender|$dateMs|${body.hashCode()}"
                val payload = JSONObject()
                    .put("source", "android_sms")
                    .put("sender", sender)
                    .put("text", body)
                    .put("received_at", formatIsoOffset(dateMs))
                    .put("sms_message_id", smsMessageId)
                NotificationCaptureStore.enqueuePendingSms(this, payload)
                imported += 1
            }
        }

        NotificationCaptureStore.recordCaptureDiagnostic(
            context = this,
            source = "android_sms",
            stage = "manual_import",
            status = "queued",
            eventKey = null,
            message = "retroactive_sms_imported",
            details = JSONObject()
                .put("hours", clampedHours)
                .put("scanned", scanned)
                .put("imported", imported)
                .put("skipped_blank", skippedBlank),
        )

        return mapOf(
            "imported" to imported,
            "scanned" to scanned,
            "hours" to clampedHours,
            "blocked" to false,
            "skipped_blank" to skippedBlank,
        )
    }

    private fun formatIsoOffset(timestamp: Long): String {
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
        formatter.timeZone = TimeZone.getDefault()
        return formatter.format(Date(timestamp))
    }

    private fun jsonValueToNullable(value: Any?): Any? {
        return if (value == org.json.JSONObject.NULL) null else value
    }

    private fun jsonObjectToMap(obj: JSONObject): Map<String, Any?> {
        val map = mutableMapOf<String, Any?>()
        val keys = obj.keys()
        while (keys.hasNext()) {
            val key = keys.next()
            map[key] = jsonToPlatformValue(obj.opt(key))
        }
        return map
    }

    private fun jsonArrayToList(array: JSONArray): List<Any?> {
        val list = mutableListOf<Any?>()
        for (index in 0 until array.length()) {
            list.add(jsonToPlatformValue(array.opt(index)))
        }
        return list
    }

    private fun jsonToPlatformValue(value: Any?): Any? {
        return when (value) {
            null, JSONObject.NULL -> null
            is JSONObject -> jsonObjectToMap(value)
            is JSONArray -> jsonArrayToList(value)
            else -> value
        }
    }
}

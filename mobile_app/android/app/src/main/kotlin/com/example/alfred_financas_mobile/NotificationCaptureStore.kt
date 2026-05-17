package com.example.alfred_financas_mobile

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

private const val PREFS_NAME = "alfred_notification_listener"
private const val KEY_QUEUE = "pending_notifications"
private const val KEY_LAST_PROCESSED_AT = "last_processed_at"
private const val KEY_NOTIFIED_KEYS = "notified_notification_keys"
private const val KEY_API_BASE_URL = "api_base_url"
private const val KEY_SMS_ENABLED = "sms_enabled"
private const val KEY_SMS_BANKS = "sms_banks"
private const val KEY_SMS_CARD_MAPPING = "sms_card_mapping"
private const val KEY_SMS_ENABLED_SINCE = "sms_enabled_since_ms"
private const val KEY_SMS_QUEUE = "pending_sms_events"
private const val KEY_MAX_QUEUE_ITEMS = 40
private const val KEY_MAX_NOTIFIED_KEYS = 400

object NotificationCaptureStore {
    private fun prefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    @Synchronized
    fun enqueue(context: Context, payload: JSONObject) {
        val notificationKey = payload.optString("notification_key").trim()
        val pref = prefs(context)
        val current = pref.getString(KEY_QUEUE, null)
        val items = if (current.isNullOrBlank()) JSONArray() else JSONArray(current)
        val deduped = JSONArray()
        for (i in 0 until items.length()) {
            val item = items.optJSONObject(i) ?: continue
            if (notificationKey.isNotBlank() && item.optString("notification_key").trim() == notificationKey) {
                continue
            }
            deduped.put(item)
        }
        deduped.put(payload)

        while (deduped.length() > KEY_MAX_QUEUE_ITEMS) {
            deduped.remove(0)
        }

        pref.edit().putString(KEY_QUEUE, deduped.toString()).apply()
    }

    @Synchronized
    fun listPendingNotifications(context: Context): JSONArray {
        val pref = prefs(context)
        val current = pref.getString(KEY_QUEUE, null)
        return if (current.isNullOrBlank()) JSONArray() else JSONArray(current)
    }

    @Synchronized
    fun removePendingNotification(context: Context, notificationKey: String) {
        if (notificationKey.isBlank()) return
        val pref = prefs(context)
        val current = pref.getString(KEY_QUEUE, null)
        if (current.isNullOrBlank()) return

        val items = JSONArray(current)
        val filtrados = JSONArray()
        for (i in 0 until items.length()) {
            val item = items.optJSONObject(i) ?: continue
            if (item.optString("notification_key") == notificationKey) {
                continue
            }
            filtrados.put(item)
        }
        pref.edit().putString(KEY_QUEUE, filtrados.toString()).apply()
    }

    fun setLastProcessedAt(context: Context, isoDateTime: String) {
        prefs(context).edit().putString(KEY_LAST_PROCESSED_AT, isoDateTime).apply()
    }

    fun getLastProcessedAt(context: Context): String? {
        return prefs(context).getString(KEY_LAST_PROCESSED_AT, null)
    }

    fun wasNotificationNotified(context: Context, notificationKey: String): Boolean {
        if (notificationKey.isBlank()) return false
        val pref = prefs(context)
        val current = pref.getString(KEY_NOTIFIED_KEYS, null)
        val items = if (current.isNullOrBlank()) JSONArray() else JSONArray(current)
        for (i in 0 until items.length()) {
            if (items.optString(i) == notificationKey) {
                return true
            }
        }
        return false
    }

    fun markNotificationNotified(context: Context, notificationKey: String) {
        if (notificationKey.isBlank()) return
        val pref = prefs(context)
        val current = pref.getString(KEY_NOTIFIED_KEYS, null)
        val items = if (current.isNullOrBlank()) JSONArray() else JSONArray(current)
        items.put(notificationKey)

        while (items.length() > KEY_MAX_NOTIFIED_KEYS) {
            items.remove(0)
        }

        pref.edit().putString(KEY_NOTIFIED_KEYS, items.toString()).apply()
    }

    fun setApiBaseUrl(context: Context, apiBaseUrl: String) {
        prefs(context).edit().putString(KEY_API_BASE_URL, apiBaseUrl.trim()).apply()
    }

    fun getApiBaseUrl(context: Context): String? {
        return prefs(context).getString(KEY_API_BASE_URL, null)?.trim()?.takeIf { it.isNotEmpty() }
    }

    fun setSmsCaptureConfig(
        context: Context,
        smsEnabled: Boolean,
        bancosSelecionados: List<String>,
        mapeamentoCartaoUltimos4: Map<String, String>,
    ) {
        val pref = prefs(context)
        val now = System.currentTimeMillis()
        val previousEnabled = pref.getBoolean(KEY_SMS_ENABLED, false)
        val banks = JSONArray().apply {
            bancosSelecionados.forEach { put(it) }
        }
        val mapping = JSONObject()
        mapeamentoCartaoUltimos4.forEach { (cartao, sufixo) ->
            mapping.put(cartao, sufixo)
        }
        val editor = pref.edit()
            .putBoolean(KEY_SMS_ENABLED, smsEnabled)
            .putString(KEY_SMS_BANKS, banks.toString())
            .putString(KEY_SMS_CARD_MAPPING, mapping.toString())
        if (smsEnabled && !previousEnabled) {
            editor.putLong(KEY_SMS_ENABLED_SINCE, now)
        }
        if (!smsEnabled) {
            editor.remove(KEY_SMS_ENABLED_SINCE)
        }
        editor.apply()
    }

    fun isSmsCaptureEnabled(context: Context): Boolean {
        return prefs(context).getBoolean(KEY_SMS_ENABLED, false)
    }

    fun getSmsBanks(context: Context): List<String> {
        val current = prefs(context).getString(KEY_SMS_BANKS, null)
        val items = if (current.isNullOrBlank()) JSONArray() else JSONArray(current)
        val result = mutableListOf<String>()
        for (i in 0 until items.length()) {
            val value = items.optString(i).trim()
            if (value.isNotEmpty()) result.add(value)
        }
        return result
    }

    fun getSmsCardMapping(context: Context): JSONObject {
        val current = prefs(context).getString(KEY_SMS_CARD_MAPPING, null)
        return if (current.isNullOrBlank()) JSONObject() else JSONObject(current)
    }

    fun getSmsEnabledSince(context: Context): Long? {
        val value = prefs(context).getLong(KEY_SMS_ENABLED_SINCE, 0L)
        return if (value > 0L) value else null
    }

    fun enqueuePendingSms(context: Context, payload: JSONObject) {
        val pref = prefs(context)
        val current = pref.getString(KEY_SMS_QUEUE, null)
        val items = if (current.isNullOrBlank()) JSONArray() else JSONArray(current)
        items.put(payload)
        while (items.length() > KEY_MAX_QUEUE_ITEMS) {
            items.remove(0)
        }
        pref.edit().putString(KEY_SMS_QUEUE, items.toString()).apply()
    }

    fun removePendingSms(context: Context, smsMessageId: String) {
        if (smsMessageId.isBlank()) return
        val pref = prefs(context)
        val current = pref.getString(KEY_SMS_QUEUE, null)
        if (current.isNullOrBlank()) return
        val items = JSONArray(current)
        val filtrados = JSONArray()
        for (i in 0 until items.length()) {
            val item = items.optJSONObject(i) ?: continue
            if (item.optString("sms_message_id") == smsMessageId) {
                continue
            }
            filtrados.put(item)
        }
        pref.edit().putString(KEY_SMS_QUEUE, filtrados.toString()).apply()
    }
}

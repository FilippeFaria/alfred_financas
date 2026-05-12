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
private const val KEY_MAX_QUEUE_ITEMS = 40
private const val KEY_MAX_NOTIFIED_KEYS = 400

object NotificationCaptureStore {
    private fun prefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    fun enqueue(context: Context, payload: JSONObject) {
        val pref = prefs(context)
        val current = pref.getString(KEY_QUEUE, null)
        val items = if (current.isNullOrBlank()) JSONArray() else JSONArray(current)
        items.put(payload)

        while (items.length() > KEY_MAX_QUEUE_ITEMS) {
            items.remove(0)
        }

        pref.edit().putString(KEY_QUEUE, items.toString()).apply()
    }

    fun listPendingNotifications(context: Context): JSONArray {
        val pref = prefs(context)
        val current = pref.getString(KEY_QUEUE, null)
        return if (current.isNullOrBlank()) JSONArray() else JSONArray(current)
    }

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
}

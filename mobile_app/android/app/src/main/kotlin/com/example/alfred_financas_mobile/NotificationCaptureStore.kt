package com.example.alfred_financas_mobile

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

private const val PREFS_NAME = "alfred_notification_listener"
private const val KEY_QUEUE = "pending_notifications"
private const val KEY_LAST_PROCESSED_AT = "last_processed_at"
private const val KEY_MAX_QUEUE_ITEMS = 40

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

    fun consume(context: Context): JSONArray {
        val pref = prefs(context)
        val current = pref.getString(KEY_QUEUE, null)
        pref.edit().remove(KEY_QUEUE).apply()
        return if (current.isNullOrBlank()) JSONArray() else JSONArray(current)
    }

    fun setLastProcessedAt(context: Context, isoDateTime: String) {
        prefs(context).edit().putString(KEY_LAST_PROCESSED_AT, isoDateTime).apply()
    }

    fun getLastProcessedAt(context: Context): String? {
        return prefs(context).getString(KEY_LAST_PROCESSED_AT, null)
    }
}

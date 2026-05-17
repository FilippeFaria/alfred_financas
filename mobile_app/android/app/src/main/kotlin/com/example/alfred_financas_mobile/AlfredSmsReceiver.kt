package com.example.alfred_financas_mobile

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Telephony
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import kotlin.concurrent.thread
import org.json.JSONObject

class AlfredSmsReceiver : BroadcastReceiver() {
    private val localChannelId = "alfred_detected_transactions"
    private val localChannelName = "Transacoes detectadas"
    private val localChannelDescription =
        "Notificacoes enviadas quando o Alfred identifica uma possivel transacao automaticamente"

    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        if (!NotificationCaptureStore.isSmsCaptureEnabled(context)) return

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isNullOrEmpty()) return

        val sender = messages.firstOrNull()?.originatingAddress?.trim().orEmpty()
        if (sender.isBlank()) return

        val smsTimestamp = messages.firstOrNull()?.timestampMillis ?: System.currentTimeMillis()
        val enabledSince = NotificationCaptureStore.getSmsEnabledSince(context)
        if (enabledSince != null && smsTimestamp < enabledSince) return

        val body = buildString {
            messages.forEach { part ->
                append(part.messageBody.orEmpty())
            }
        }.trim()
        if (body.isBlank()) return

        val smsMessageId = "$sender|$smsTimestamp|${body.hashCode()}"
        val payload = JSONObject()
            .put("source", "android_sms")
            .put("sender", sender)
            .put("text", body)
            .put("received_at", formatIsoOffset(smsTimestamp))
            .put("sms_message_id", smsMessageId)

        NotificationCaptureStore.enqueuePendingSms(context, payload)
        thread(name = "alfred-sms-sync-${smsMessageId.hashCode()}") {
            sincronizarSms(context, payload)
        }
    }

    private fun sincronizarSms(context: Context, payload: JSONObject) {
        val smsMessageId = payload.optString("sms_message_id")
        if (smsMessageId.isBlank()) return
        val apiBaseUrl = NotificationCaptureStore.getApiBaseUrl(context) ?: return
        val resposta = postJson(apiBaseUrl, "/ai/sms/transacao", payload) ?: return

        NotificationCaptureStore.removePendingSms(context, smsMessageId)

        val created = resposta.optBoolean("created", false)
        if (!created) return
        val pendingTransactionId = resposta.optString("pending_transaction_id").takeIf { it.isNotBlank() }
        showLocalDetectedNotification(context, payload, pendingTransactionId)
    }

    private fun postJson(baseUrl: String, path: String, payload: JSONObject): JSONObject? {
        val normalizedBaseUrl = baseUrl.trim().trimEnd('/')
        if (normalizedBaseUrl.isBlank()) return null
        val connection = try {
            val url = URL("$normalizedBaseUrl$path")
            (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 5_000
                readTimeout = 10_000
                doInput = true
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Accept", "application/json")
            }
        } catch (error: Exception) {
            Log.w("AlfredSmsReceiver", "Falha ao preparar chamada HTTP", error)
            return null
        }

        return try {
            connection.outputStream.use { stream ->
                stream.write(payload.toString().toByteArray(Charsets.UTF_8))
            }
            val responseCode = connection.responseCode
            val stream = if (responseCode in 200..299) connection.inputStream else connection.errorStream
            val responseBody = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (responseCode !in 200..299 || responseBody.isBlank()) {
                Log.w("AlfredSmsReceiver", "Backend recusou SMS. status=$responseCode body=$responseBody")
                return null
            }
            JSONObject(responseBody)
        } catch (error: Exception) {
            Log.w("AlfredSmsReceiver", "Falha ao sincronizar SMS", error)
            null
        } finally {
            connection.disconnect()
        }
    }

    private fun formatIsoOffset(timestamp: Long): String {
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
        formatter.timeZone = TimeZone.getDefault()
        return formatter.format(Date(timestamp))
    }

    private fun showLocalDetectedNotification(context: Context, payload: JSONObject, pendingTransactionId: String?) {
        val notificationIdentity = pendingTransactionId ?: payload.optString("sms_message_id")
        if (notificationIdentity.isBlank()) return
        if (NotificationCaptureStore.wasNotificationNotified(context, notificationIdentity)) return

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED
            if (!granted) return
        }

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                localChannelId,
                localChannelName,
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = localChannelDescription
            }
            manager.createNotificationChannel(channel)
        }

        val sender = payload.optString("sender").ifBlank { "SMS" }
        val text = payload.optString("text").ifBlank { "Nova transacao detectada por SMS" }
        val launchIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("open_route", "/insights?from_notification=1" +
                if (!pendingTransactionId.isNullOrBlank()) "&pending_id=$pendingTransactionId" else "")
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            notificationIdentity.hashCode(),
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val body = "$text - $sender"
        val notification = NotificationCompat.Builder(context, localChannelId)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("Nova transacao detectada")
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        manager.notify(notificationIdentity.hashCode(), notification)
        NotificationCaptureStore.markNotificationNotified(context, notificationIdentity)
    }
}

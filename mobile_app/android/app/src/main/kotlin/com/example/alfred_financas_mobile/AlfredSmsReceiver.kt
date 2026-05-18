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
        if (!NotificationCaptureStore.isSmsCaptureEnabled(context)) {
            recordDiagnostic(
                context = context,
                stage = "filter",
                status = "skipped",
                eventKey = null,
                message = "sms_capture_disabled",
            )
            return
        }

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isNullOrEmpty()) {
            recordDiagnostic(
                context = context,
                stage = "filter",
                status = "skipped",
                eventKey = null,
                message = "empty_sms_intent",
            )
            return
        }

        val sender = messages.firstOrNull()?.originatingAddress?.trim().orEmpty()
        if (sender.isBlank()) {
            recordDiagnostic(
                context = context,
                stage = "filter",
                status = "skipped",
                eventKey = null,
                message = "blank_sender",
            )
            return
        }

        val smsTimestamp = messages.firstOrNull()?.timestampMillis ?: System.currentTimeMillis()
        val enabledSince = NotificationCaptureStore.getSmsEnabledSince(context)
        if (enabledSince != null && smsTimestamp < enabledSince) {
            recordDiagnostic(
                context = context,
                stage = "filter",
                status = "skipped",
                eventKey = "$sender|$smsTimestamp",
                message = "sms_before_capture_enabled",
                details = JSONObject().put("sender", sender),
            )
            return
        }

        val body = buildString {
            messages.forEach { part ->
                append(part.messageBody.orEmpty())
            }
        }.trim()
        if (body.isBlank()) {
            recordDiagnostic(
                context = context,
                stage = "filter",
                status = "skipped",
                eventKey = "$sender|$smsTimestamp",
                message = "blank_body",
                details = JSONObject().put("sender", sender),
            )
            return
        }

        val smsMessageId = "$sender|$smsTimestamp|${body.hashCode()}"
        val payload = JSONObject()
            .put("source", "android_sms")
            .put("sender", sender)
            .put("text", body)
            .put("received_at", formatIsoOffset(smsTimestamp))
            .put("sms_message_id", smsMessageId)

        NotificationCaptureStore.enqueuePendingSms(context, payload)
        recordDiagnostic(
            context = context,
            stage = "capture",
            status = "queued",
            eventKey = smsMessageId,
            message = "sms_queued",
            details = JSONObject()
                .put("sender", sender)
                .put("text_preview", preview(body)),
        )
        thread(name = "alfred-sms-sync-${smsMessageId.hashCode()}") {
            sincronizarSms(context, payload)
        }
    }

    private fun sincronizarSms(context: Context, payload: JSONObject) {
        val smsMessageId = payload.optString("sms_message_id")
        if (smsMessageId.isBlank()) {
            recordDiagnostic(
                context = context,
                stage = "sync",
                status = "skipped",
                eventKey = null,
                message = "blank_sms_message_id",
            )
            return
        }
        val apiBaseUrl = NotificationCaptureStore.getApiBaseUrl(context)
        if (apiBaseUrl == null) {
            recordDiagnostic(
                context = context,
                stage = "sync",
                status = "skipped",
                eventKey = smsMessageId,
                message = "missing_api_base_url",
            )
            return
        }
        val resposta = postJson(context, apiBaseUrl, "/ai/sms/transacao", payload) ?: return

        NotificationCaptureStore.removePendingSms(context, smsMessageId)

        val created = resposta.optBoolean("created", false)
        if (!created) {
            recordDiagnostic(
                context = context,
                stage = "api_result",
                status = if (resposta.optBoolean("duplicate", false)) "duplicate" else "ignored",
                eventKey = smsMessageId,
                message = resposta.optString("message").ifBlank { "not_created" },
                details = JSONObject()
                    .put("duplicate", resposta.optBoolean("duplicate", false))
                    .put("pending_transaction_id", resposta.optString("pending_transaction_id")),
            )
            return
        }
        val pendingTransactionId = resposta.optString("pending_transaction_id").takeIf { it.isNotBlank() }
        recordDiagnostic(
            context = context,
            stage = "api_result",
            status = "created",
            eventKey = smsMessageId,
            message = "pending_transaction_created",
            details = JSONObject().put("pending_transaction_id", pendingTransactionId ?: JSONObject.NULL),
        )
        showLocalDetectedNotification(context, payload, pendingTransactionId)
    }

    private fun postJson(context: Context, baseUrl: String, path: String, payload: JSONObject): JSONObject? {
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
            recordDiagnostic(
                context = context,
                stage = "http",
                status = "error",
                eventKey = payload.optString("sms_message_id"),
                message = "prepare_failed",
                details = JSONObject().put("error", error.javaClass.simpleName),
            )
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
                recordDiagnostic(
                    context = context,
                    stage = "http",
                    status = "error",
                    eventKey = payload.optString("sms_message_id"),
                    message = if (responseBody.isBlank()) "blank_backend_response" else "backend_rejected",
                    details = JSONObject()
                        .put("status_code", responseCode)
                        .put("body_preview", preview(responseBody)),
                )
                return null
            }
            JSONObject(responseBody)
        } catch (error: Exception) {
            Log.w("AlfredSmsReceiver", "Falha ao sincronizar SMS", error)
            recordDiagnostic(
                context = context,
                stage = "http",
                status = "error",
                eventKey = payload.optString("sms_message_id"),
                message = "request_failed",
                details = JSONObject().put("error", error.javaClass.simpleName),
            )
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

    private fun recordDiagnostic(
        context: Context?,
        stage: String,
        status: String,
        eventKey: String?,
        message: String,
        details: JSONObject? = null,
    ) {
        val targetContext = context ?: return
        NotificationCaptureStore.recordCaptureDiagnostic(
            context = targetContext,
            source = "android_sms",
            stage = stage,
            status = status,
            eventKey = eventKey,
            message = message,
            details = details,
        )
    }

    private fun preview(value: String): String {
        val trimmed = value.trim()
        return if (trimmed.length <= 120) trimmed else trimmed.take(117) + "..."
    }
}

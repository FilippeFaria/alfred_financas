package com.example.alfred_financas_mobile

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
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

class AlfredNotificationListenerService : NotificationListenerService() {
    private val localChannelId = "alfred_detected_transactions"
    private val localChannelName = "Transacoes detectadas"
    private val localChannelDescription =
        "Notificacoes enviadas quando o Alfred identifica uma possivel transacao automaticamente"

    private val allowedPackages = setOf(
        "com.nu.production",
        "com.itau",
        "br.com.intermedium",
        "com.c6bank.app",
        "com.mercadopago.wallet",
        "com.picpay",
        "com.xp.wintrade",
        "com.google.android.apps.walletnfcrel",
        "com.samsung.android.spay",
    )
    private val allowedPackagePrefixes = listOf(
        "com.itau.",
        "com.itau",
    )

    private val financeHints = listOf(
        "r$",
        "compra",
        "pagamento",
        "pix",
        "transfer",
        "recebido",
        "deb",
    )

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val packageName = sbn.packageName ?: return
        val allowedByPrefix = allowedPackagePrefixes.any { prefix -> packageName.startsWith(prefix) }
        if (!allowedPackages.contains(packageName) && !allowedByPrefix) {
            if (looksLikePotentialFinancePackage(packageName)) {
                recordDiagnostic(
                    stage = "filter",
                    status = "skipped",
                    eventKey = sbn.key,
                    message = "package_not_allowed",
                    details = JSONObject().put("package_name", packageName),
                )
            }
            return
        }

        val extras = sbn.notification.extras
        val title = extras?.getCharSequence("android.title")?.toString()?.trim().orEmpty()
        val text = extras?.getCharSequence("android.text")?.toString()?.trim().orEmpty()
        val subText = extras?.getCharSequence("android.subText")?.toString()?.trim().orEmpty()

        if (text.isBlank()) {
            recordDiagnostic(
                stage = "filter",
                status = "skipped",
                eventKey = sbn.key,
                message = "blank_text",
                details = JSONObject().put("package_name", packageName),
            )
            return
        }
        val rawText = "$title $text $subText".lowercase(Locale.ROOT)
        if (financeHints.none { rawText.contains(it) }) {
            recordDiagnostic(
                stage = "filter",
                status = "skipped",
                eventKey = sbn.key,
                message = "no_financial_hint",
                details = JSONObject()
                    .put("package_name", packageName)
                    .put("title", title)
                    .put("text_preview", preview(text)),
            )
            return
        }

        val appName = try {
            val appInfo = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(appInfo).toString()
        } catch (_: Exception) {
            packageName
        }

        val payload = JSONObject()
            .put("package_name", packageName)
            .put("app_name", appName)
            .put("title", title.ifBlank { JSONObject.NULL })
            .put("text", text)
            .put("sub_text", subText.ifBlank { JSONObject.NULL })
            .put("posted_at", formatIsoOffset(sbn.postTime))
            .put("notification_key", sbn.key)

        NotificationCaptureStore.enqueue(this, payload)
        NotificationCaptureStore.setLastProcessedAt(this, formatIsoOffset(System.currentTimeMillis()))
        recordDiagnostic(
            stage = "capture",
            status = "queued",
            eventKey = sbn.key,
            message = "notification_queued",
            details = JSONObject()
                .put("package_name", packageName)
                .put("app_name", appName)
                .put("title", title)
                .put("text_preview", preview(text)),
        )

        thread(name = "alfred-notification-sync-${sbn.key.hashCode()}") {
            sincronizarNotificacao(payload)
        }
    }

    private fun sincronizarNotificacao(payload: JSONObject) {
        val notificationKey = payload.optString("notification_key")
        if (notificationKey.isBlank()) {
            recordDiagnostic(
                stage = "sync",
                status = "skipped",
                eventKey = null,
                message = "blank_notification_key",
            )
            return
        }

        val apiBaseUrl = NotificationCaptureStore.getApiBaseUrl(this)
        if (apiBaseUrl == null) {
            recordDiagnostic(
                stage = "sync",
                status = "skipped",
                eventKey = notificationKey,
                message = "missing_api_base_url",
            )
            return
        }
        val resposta = postJson(apiBaseUrl, "/ai/notificacao/transacao", payload) ?: return

        NotificationCaptureStore.removePendingNotification(this, notificationKey)

        if (!resposta.optBoolean("created", false)) {
            recordDiagnostic(
                stage = "api_result",
                status = if (resposta.optBoolean("duplicate", false)) "duplicate" else "ignored",
                eventKey = notificationKey,
                message = resposta.optString("message").ifBlank { "not_created" },
                details = JSONObject()
                    .put("duplicate", resposta.optBoolean("duplicate", false))
                    .put("pending_transaction_id", resposta.optString("pending_transaction_id")),
            )
            return
        }

        val pendingTransactionId = resposta.optString("pending_transaction_id").takeIf { it.isNotBlank() }
        recordDiagnostic(
            stage = "api_result",
            status = "created",
            eventKey = notificationKey,
            message = "pending_transaction_created",
            details = JSONObject().put("pending_transaction_id", pendingTransactionId ?: JSONObject.NULL),
        )
        showLocalDetectedNotification(payload, pendingTransactionId)
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
            Log.w("AlfredNotifListener", "Falha ao preparar chamada HTTP", error)
            recordDiagnostic(
                stage = "http",
                status = "error",
                eventKey = payload.optString("notification_key"),
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

            if (responseCode !in 200..299) {
                Log.w(
                    "AlfredNotifListener",
                    "Backend recusou notificacao. status=$responseCode body=$responseBody",
                )
                recordDiagnostic(
                    stage = "http",
                    status = "error",
                    eventKey = payload.optString("notification_key"),
                    message = "backend_rejected",
                    details = JSONObject()
                        .put("status_code", responseCode)
                        .put("body_preview", preview(responseBody)),
                )
                return null
            }

            if (responseBody.isBlank()) {
                Log.w("AlfredNotifListener", "Backend retornou resposta vazia para notificacao.")
                recordDiagnostic(
                    stage = "http",
                    status = "error",
                    eventKey = payload.optString("notification_key"),
                    message = "blank_backend_response",
                    details = JSONObject().put("status_code", responseCode),
                )
                return null
            }

            JSONObject(responseBody)
        } catch (error: Exception) {
            Log.w("AlfredNotifListener", "Falha ao sincronizar notificacao", error)
            recordDiagnostic(
                stage = "http",
                status = "error",
                eventKey = payload.optString("notification_key"),
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

    private fun showLocalDetectedNotification(payload: JSONObject, pendingTransactionId: String?) {
        val notificationIdentity = pendingTransactionId ?: payload.optString("notification_key")
        if (notificationIdentity.isBlank()) return
        if (NotificationCaptureStore.wasNotificationNotified(this, notificationIdentity)) return

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED
            if (!granted) return
        }

        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
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

        val appName = payload.optString("app_name").ifBlank { "Conta" }
        val text = payload.optString("text").ifBlank { "Nova transacao detectada" }
        val title = "Nova transacao detectada"
        val body = "$text - $appName"

        val launchIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("open_route", "/insights?from_notification=1" +
                if (!pendingTransactionId.isNullOrBlank()) "&pending_id=$pendingTransactionId" else "")
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            notificationIdentity.hashCode(),
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(this, localChannelId)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        manager.notify(notificationIdentity.hashCode(), notification)
        NotificationCaptureStore.markNotificationNotified(
            this,
            notificationIdentity,
        )
    }

    private fun recordDiagnostic(
        stage: String,
        status: String,
        eventKey: String?,
        message: String,
        details: JSONObject? = null,
    ) {
        NotificationCaptureStore.recordCaptureDiagnostic(
            context = this,
            source = "android_notification",
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

    private fun looksLikePotentialFinancePackage(packageName: String): Boolean {
        val normalized = packageName.lowercase(Locale.ROOT)
        return listOf("bank", "banco", "itau", "nu", "inter", "c6", "mercado", "picpay", "wallet", "pay")
            .any { normalized.contains(it) }
    }
}

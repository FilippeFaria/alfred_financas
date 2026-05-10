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
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import org.json.JSONObject

class AlfredNotificationListenerService : NotificationListenerService() {
    private val localChannelId = "alfred_detected_transactions"
    private val localChannelName = "Transações detectadas"
    private val localChannelDescription =
        "Notificações enviadas quando o Alfred identifica uma possível transação automaticamente"

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
        if (!allowedPackages.contains(packageName) && !allowedByPrefix) return

        val extras = sbn.notification.extras
        val title = extras?.getCharSequence("android.title")?.toString()?.trim().orEmpty()
        val text = extras?.getCharSequence("android.text")?.toString()?.trim().orEmpty()
        val subText = extras?.getCharSequence("android.subText")?.toString()?.trim().orEmpty()

        if (text.isBlank()) return
        val rawText = "$title $text $subText".lowercase(Locale.ROOT)
        if (financeHints.none { rawText.contains(it) }) return

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
        showLocalDetectedNotification(payload)
    }

    private fun formatIsoOffset(timestamp: Long): String {
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
        formatter.timeZone = TimeZone.getDefault()
        return formatter.format(Date(timestamp))
    }

    private fun showLocalDetectedNotification(payload: JSONObject) {
        val notificationKey = payload.optString("notification_key")
        if (notificationKey.isBlank()) return
        if (NotificationCaptureStore.wasNotificationNotified(this, notificationKey)) return

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
        val text = payload.optString("text").ifBlank { "Nova transação detectada" }
        val title = "Nova transação detectada"
        val body = "$text — $appName"

        val launchIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("open_route", "/insights")
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            notificationKey.hashCode(),
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

        manager.notify(notificationKey.hashCode(), notification)
        NotificationCaptureStore.markNotificationNotified(this, notificationKey)
    }
}

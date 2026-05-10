package com.example.alfred_financas_mobile

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import org.json.JSONObject

class AlfredNotificationListenerService : NotificationListenerService() {
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
        if (!allowedPackages.contains(packageName)) return

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
    }

    private fun formatIsoOffset(timestamp: Long): String {
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
        formatter.timeZone = TimeZone.getDefault()
        return formatter.format(Date(timestamp))
    }
}

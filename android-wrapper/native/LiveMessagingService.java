package com.spacexbot.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import androidx.core.app.NotificationCompat;
import com.google.firebase.messaging.RemoteMessage;
import java.util.Map;

/**
 * Handles every push message. Normal alerts go to Capacitor's own service (super).
 * A silent message with type=live becomes the pinned "Bot running" notification, updated in place (same id).
 * The server sends title, text, big and ts; off=1 removes the notification.
 */
public class LiveMessagingService extends com.capacitorjs.plugins.pushnotifications.MessagingService {
    static final String CHANNEL = "sxb_live";
    static final int NOTIF_ID = 7001;

    @Override
    public void onMessageReceived(RemoteMessage message) {
        Map<String, String> d = message.getData();
        if (d != null && "live".equals(d.get("type"))) {
            try { handleLive(d); } catch (Exception ignored) { }
            return;
        }
        super.onMessageReceived(message);
    }

    private void handleLive(Map<String, String> d) {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;
        if ("1".equals(d.get("off"))) { nm.cancel(NOTIF_ID); return; }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "Bot running", NotificationManager.IMPORTANCE_LOW);
            ch.setDescription("Live status while the bot is running");
            ch.setShowBadge(false);
            nm.createNotificationChannel(ch);
        }

        PendingIntent pi = null;
        Intent open = getPackageManager().getLaunchIntentForPackage(getPackageName());
        if (open != null) {
            open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            pi = PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        }
        int icon = getResources().getIdentifier("ic_stat_sxb", "drawable", getPackageName());
        if (icon == 0) icon = android.R.drawable.ic_dialog_info;

        String title = d.get("title") == null ? "Bot running" : d.get("title");
        String text = d.get("text") == null ? "" : d.get("text");
        String big = d.get("big") == null ? text : d.get("big");
        long when = System.currentTimeMillis();
        try { if (d.get("ts") != null) when = Long.parseLong(d.get("ts")) * 1000L; } catch (NumberFormatException ignored) { }

        // On the lock screen show only "Bot running", never the balance.
        NotificationCompat.Builder pub = new NotificationCompat.Builder(this, CHANNEL)
                .setSmallIcon(icon).setContentTitle("Bot running").setContentText("Open the app to see details");

        NotificationCompat.Builder b = new NotificationCompat.Builder(this, CHANNEL)
                .setSmallIcon(icon)
                .setContentTitle(title)
                .setContentText(text)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(big))
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setShowWhen(true)
                .setWhen(when)
                .setCategory(NotificationCompat.CATEGORY_STATUS)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
                .setPublicVersion(pub.build())
                .setTimeoutAfter(6 * 60 * 1000L);   // disappears by itself if the server stops sending
        if (pi != null) b.setContentIntent(pi);
        nm.notify(NOTIF_ID, b.build());
    }
}

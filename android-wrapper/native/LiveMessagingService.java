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
 * Handles every push message. Normal alerts go to Capacitor's own service (super); while the app is open they are also drawn here (N1b).
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
        /* N1b: Android calls this for a notification message ONLY while the app is open (closed or in the background it draws the banner itself).
           Capacitor's service draws nothing, so without this the person saw no alert while the app was open. */
        try { showForeground(message); } catch (Exception ignored) { }
        super.onMessageReceived(message);   // still tell the page (pushNotificationReceived)
    }

    static final String CH_HIGH = "sxb_high";
    static final String CH_LOW = "sxb_low";
    static final int ALERT_ID = 7100;

    /** Same channel as the server asked for, small icon ic_stat_sxb, tap opens the app carrying the message data (route, kind, tag...). */
    private void showForeground(RemoteMessage message) {
        RemoteMessage.Notification n = message.getNotification();
        if (n == null) return;                                   // data-only message: nothing to show
        Map<String, String> d = message.getData();
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;

        String channel = n.getChannelId();
        if (channel == null || channel.isEmpty()) channel = CH_HIGH;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && nm.getNotificationChannel(channel) == null) {
            boolean low = CH_LOW.equals(channel);
            NotificationChannel ch = new NotificationChannel(channel, low ? "Reports and tips" : "Trades and alerts",
                    low ? NotificationManager.IMPORTANCE_LOW : NotificationManager.IMPORTANCE_HIGH);
            nm.createNotificationChannel(ch);
        }

        int icon = getResources().getIdentifier("ic_stat_sxb", "drawable", getPackageName());
        if (icon == 0) icon = android.R.drawable.ic_dialog_info;

        String tag = n.getTag();
        if ((tag == null || tag.isEmpty()) && d != null) tag = d.get("tag");

        PendingIntent pi = null;
        Intent open = getPackageManager().getLaunchIntentForPackage(getPackageName());
        if (open != null) {
            open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            // Capacitor's push plugin fires "tap" only when this key is present; the rest is the data the page reads (route).
            String mid = message.getMessageId();
            open.putExtra("google.message_id", mid == null ? String.valueOf(System.currentTimeMillis()) : mid);
            if (d != null) for (Map.Entry<String, String> e : d.entrySet()) open.putExtra(e.getKey(), e.getValue());
            int req = (int) (System.currentTimeMillis() & 0x7fffffff);   // unique, so an older alert keeps its own data
            pi = PendingIntent.getActivity(this, req, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        }

        String title = n.getTitle() == null ? "spaceXBot" : n.getTitle();
        String body = n.getBody() == null ? "" : n.getBody();
        NotificationCompat.Builder b = new NotificationCompat.Builder(this, channel)
                .setSmallIcon(icon)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
                .setAutoCancel(true)
                .setPriority(CH_LOW.equals(channel) ? NotificationCompat.PRIORITY_LOW : NotificationCompat.PRIORITY_HIGH);
        if (pi != null) b.setContentIntent(pi);
        android.graphics.Bitmap lg = largeIcon(); if (lg != null) b.setLargeIcon(lg);
        if (tag != null && !tag.isEmpty()) nm.notify(tag, ALERT_ID, b.build());   // same tag = replaces, like the background banner
        else nm.notify((int) (System.currentTimeMillis() & 0x7ffffff), b.build());
    }

    /** Rk4: the round badge (res/drawable-nodpi/ic_large_sxb.png). No file = no large icon, never an error. */
    private android.graphics.Bitmap largeIcon() {
        try {
            int id = getResources().getIdentifier("ic_large_sxb", "drawable", getPackageName());
            if (id == 0) return null;
            return android.graphics.BitmapFactory.decodeResource(getResources(), id);
        } catch (Exception e) { return null; }
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
        android.graphics.Bitmap lg2 = largeIcon(); if (lg2 != null) b.setLargeIcon(lg2);
        nm.notify(NOTIF_ID, b.build());
    }
}

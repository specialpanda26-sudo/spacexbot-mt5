package com.spacexbot.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.os.Build;
import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(GoogleSignInPlugin.class);   // must come BEFORE super.onCreate
        registerPlugin(AppUpdatePlugin.class);
        registerPlugin(ScreenPlugin.class);
        super.onCreate(savedInstanceState);
        makeChannels();
    }

    /** Two Android channels: high = trades, risk, EA offline, billing; low = reports, tips, nudges. */
    private void makeChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm == null) return;
        NotificationChannel hi = new NotificationChannel("sxb_high", "Trades and alerts", NotificationManager.IMPORTANCE_HIGH);
        hi.setDescription("Trades, risk limits, EA offline and billing");
        NotificationChannel lo = new NotificationChannel("sxb_low", "Reports and tips", NotificationManager.IMPORTANCE_LOW);
        lo.setDescription("Daily and weekly reports, tips and reminders");
        nm.createNotificationChannel(hi);
        nm.createNotificationChannel(lo);
    }
}

package com.spacexbot.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.text.SpannableStringBuilder;
import android.text.style.StyleSpan;
import android.util.Base64;
import android.util.DisplayMetrics;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.ByteBuffer;

/** SC3 / SC3b: the floating bubble. The bubble itself is the app's own icon (res/drawable-nodpi/ic_large_sxb.png, the purple, yellow and white one the alerts show); the card
 *  next to it shows the website's own cartoon for the situation (res/drawable-nodpi/sxart_<name>.png, drawn from window.IL2 by tools/make_screen_art.py, chosen by
 *  ScreenLogic.Verdict.pic like pick() in static/screen.js). Nothing is drawn here by hand except the ring colour.
 *  A foreground service of type mediaProjection keeps one screen capture open; a tap on the bubble = ONE picture, sent to
 *  POST /api/screen/read by this service itself (the page is paused in the background). Long press = stop. The AI only READS; the answer shown is the
 *  server's: the bot's own words, entry, stop and target.
 *  PRIVACY: the picture exists only as local variables while it is sent; it is never written to disk, never logged. The token lives in memory only and is
 *  dropped when the service ends. Windows that block capture (FLAG_SECURE) come out black; nothing here tries to get around that. */
public class OverlayService extends Service {
    static final String ACTION_START = "com.spacexbot.app.SCREEN_START", ACTION_STOP = "com.spacexbot.app.SCREEN_STOP";
    private static final String CHANNEL = "sxb_screen";
    private static final int NOTE_ID = 7301;

    private static volatile String endpoint, token, context = "trade";
    private static volatile boolean running = false;

    static boolean running() { return running; }
    static void configure(String ep, String tk, String ctx) { endpoint = ep; token = tk; context = ctx; }
    static void setToken(String tk) { token = tk; }
    static void clear() { if (!running) { endpoint = null; token = null; } }

    private final Handler main = new Handler(Looper.getMainLooper());
    private WindowManager wm;
    private MediaProjection projection;
    private VirtualDisplay display;
    private ImageReader reader;
    private int capW, capH;
    private BubbleView bubble;
    private WindowManager.LayoutParams bubbleLp;
    private LinearLayout card;
    private ImageView cardPic;
    private TextView cardText;
    private long lastRead = 0;
    private boolean busy = false, down = false;
    private final Runnable hideCard = new Runnable() { @Override public void run() { if (card != null) card.setVisibility(View.GONE); } };

    @Override public IBinder onBind(Intent i) { return null; }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) { shutdown(); return START_NOT_STICKY; }
        if (intent == null || !ACTION_START.equals(intent.getAction())) { shutdown(); return START_NOT_STICKY; }
        // Android 14+: the foreground service of type mediaProjection must be running BEFORE the projection is created. It is also started first of all, so that
        // an early exit below never leaves a service that was started with startForegroundService() without its startForeground() (Android 8+ would crash).
        Notification n = notification();
        if (Build.VERSION.SDK_INT >= 29) startForeground(NOTE_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION); else startForeground(NOTE_ID, n);
        if (projection != null) return START_NOT_STICKY;            // already running
        if (endpoint == null || token == null || down) { shutdown(); return START_NOT_STICKY; }
        try {
            MediaProjectionManager mpm = (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
            projection = mpm.getMediaProjection(intent.getIntExtra("code", 0), (Intent) intent.getParcelableExtra("data"));
            if (projection == null) { shutdown(); return START_NOT_STICKY; }
            // Android 14+: a callback must be registered before the virtual display is made, and a projection makes ONE display only.
            projection.registerCallback(new MediaProjection.Callback() {
                @Override public void onStop() { main.post(new Runnable() { @Override public void run() { shutdown(); } }); }
            }, main);
            wm = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
            DisplayMetrics dm = getResources().getDisplayMetrics();
            capW = dm.widthPixels; capH = dm.heightPixels;
            reader = ImageReader.newInstance(capW, capH, PixelFormat.RGBA_8888, 2);
            display = projection.createVirtualDisplay("sxb-screen", capW, capH, dm.densityDpi, DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, reader.getSurface(), null, main);
            addBubble();
            running = true;
        } catch (Exception e) { shutdown(); return START_NOT_STICKY; }
        return START_NOT_STICKY;
    }

    @Override public void onDestroy() { shutdown(); super.onDestroy(); }

    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }

    private int overlayType() { return Build.VERSION.SDK_INT >= 26 ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY : WindowManager.LayoutParams.TYPE_PHONE; }

    private Notification notification() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) nm.createNotificationChannel(new NotificationChannel(CHANNEL, "Screen assistant", NotificationManager.IMPORTANCE_LOW));
        }
        int fl = PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0);
        Intent stop = new Intent(this, OverlayService.class); stop.setAction(ACTION_STOP);
        PendingIntent stopPi = PendingIntent.getService(this, 1, stop, fl);
        Intent open = getPackageManager().getLaunchIntentForPackage(getPackageName());
        Notification.Builder b = Build.VERSION.SDK_INT >= 26 ? new Notification.Builder(this, CHANNEL) : new Notification.Builder(this);
        b.setSmallIcon(getApplicationInfo().icon).setContentTitle("spaceXBot is watching your screen")
         .setContentText("Tap the bubble to read your chart. Stop here when you are done.").setOngoing(true).addAction(0, "Stop", stopPi);
        if (open != null) b.setContentIntent(PendingIntent.getActivity(this, 2, open, fl));
        return b.build();
    }

    // ---------------------------------------------------------------- the bubble
    private static final class BubbleView extends View {
        private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Bitmap icon;                     // the app's own purple, yellow and white icon; null only if the file is missing from the build
        private int ring = ScreenLogic.MUTED; private boolean working = false;
        BubbleView(Context c, Bitmap icon) { super(c); this.icon = icon; }
        void set(int r, boolean w) { ring = r; working = w; invalidate(); }
        @Override protected void onDraw(Canvas cv) {
            float w = getWidth(), h = getHeight(), r = Math.min(w, h) / 2f, ringW = r * 0.14f, inner = r - ringW - 1f;
            p.setStyle(Paint.Style.FILL); p.setColor(ScreenLogic.SURFACE); cv.drawCircle(w / 2f, h / 2f, r - 1f, p);
            if (icon != null) {
                Path clip = new Path(); clip.addCircle(w / 2f, h / 2f, inner, Path.Direction.CW);
                cv.save(); cv.clipPath(clip);
                cv.drawBitmap(icon, null, new RectF(w / 2f - inner, h / 2f - inner, w / 2f + inner, h / 2f + inner), p);
                cv.restore();
            } else {                                   // no picture in this build: the old plain eye, so the bubble is never empty
                p.setColor(ScreenLogic.FG); cv.drawOval(new RectF(w * 0.24f, h * 0.35f, w * 0.76f, h * 0.65f), p);
                p.setColor(ScreenLogic.SURFACE); cv.drawCircle(w / 2f, h / 2f, r * 0.17f, p);
            }
            p.setStyle(Paint.Style.STROKE); p.setStrokeWidth(ringW); p.setColor(working ? ScreenLogic.SKY : ring); cv.drawCircle(w / 2f, h / 2f, r - ringW / 2f - 1f, p);
        }
    }

    /** A picture the build put in res/drawable-nodpi (0 = not there). */
    private Bitmap pic(String name) {
        int id = getResources().getIdentifier(name, "drawable", getPackageName());
        if (id == 0) return null;
        try { return BitmapFactory.decodeResource(getResources(), id); } catch (Exception e) { return null; }
    }

    private void addBubble() {
        bubble = new BubbleView(this, pic("ic_large_sxb"));
        bubble.setContentDescription("spaceXBot. Tap to read your chart. Hold to stop.");
        int size = dp(56);
        bubbleLp = new WindowManager.LayoutParams(size, size, overlayType(),
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL, PixelFormat.TRANSLUCENT);
        bubbleLp.gravity = Gravity.TOP | Gravity.START; bubbleLp.x = dp(12); bubbleLp.y = dp(160);
        bubble.setOnTouchListener(new View.OnTouchListener() {
            private int sx, sy; private float tx, ty; private boolean moved, held;
            private final Runnable hold = new Runnable() { @Override public void run() { held = true; shutdown(); } };
            @Override public boolean onTouch(View v, MotionEvent e) {
                switch (e.getAction()) {
                    case MotionEvent.ACTION_DOWN: sx = bubbleLp.x; sy = bubbleLp.y; tx = e.getRawX(); ty = e.getRawY(); moved = false; held = false; main.postDelayed(hold, 700); return true;
                    case MotionEvent.ACTION_MOVE: {
                        float dx = e.getRawX() - tx, dy = e.getRawY() - ty;
                        if (Math.abs(dx) > dp(6) || Math.abs(dy) > dp(6)) { moved = true; main.removeCallbacks(hold); }
                        if (moved && !down) { bubbleLp.x = sx + (int) dx; bubbleLp.y = sy + (int) dy; wm.updateViewLayout(v, bubbleLp); }
                        return true;
                    }
                    case MotionEvent.ACTION_UP: main.removeCallbacks(hold); if (!moved && !held) readNow(); return true;
                    case MotionEvent.ACTION_CANCEL: main.removeCallbacks(hold); return true;
                    default: return false;
                }
            }
        });
        wm.addView(bubble, bubbleLp);
    }

    private void showCard(ScreenLogic.Verdict v) {
        if (down) return;
        if (card == null) {
            card = new LinearLayout(this); card.setOrientation(LinearLayout.VERTICAL); card.setGravity(Gravity.CENTER_HORIZONTAL);
            card.setPadding(dp(14), dp(10), dp(14), dp(12));
            cardPic = new ImageView(this); cardPic.setAdjustViewBounds(true); cardPic.setScaleType(ImageView.ScaleType.FIT_CENTER);
            card.addView(cardPic, new LinearLayout.LayoutParams(dp(150), dp(106)));
            cardText = new TextView(this); cardText.setTextColor(ScreenLogic.FG); cardText.setTextSize(14f);
            card.addView(cardText, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
            card.setOnClickListener(new View.OnClickListener() { @Override public void onClick(View x) { card.setVisibility(View.GONE); } });
            int w = Math.min(dp(300), getResources().getDisplayMetrics().widthPixels - dp(24));
            WindowManager.LayoutParams lp = new WindowManager.LayoutParams(w, WindowManager.LayoutParams.WRAP_CONTENT, overlayType(),
                    WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL, PixelFormat.TRANSLUCENT);
            lp.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL; lp.y = dp(72);
            wm.addView(card, lp);
        }
        GradientDrawable bg = new GradientDrawable(); bg.setColor(ScreenLogic.SURFACE); bg.setStroke(dp(2), v.ring); bg.setCornerRadius(dp(16));
        card.setBackground(bg);
        Bitmap art = pic("sxart_" + v.pic);                  // the website's own cartoon for this situation; the card still works without it
        if (art != null) { cardPic.setImageBitmap(art); cardPic.setVisibility(View.VISIBLE); } else cardPic.setVisibility(View.GONE);
        SpannableStringBuilder sb = new SpannableStringBuilder(v.head);
        sb.setSpan(new StyleSpan(Typeface.BOLD), 0, v.head.length(), 0);
        if (v.say.length() > 0) sb.append("\n").append(v.say);
        sb.append("\n").append("A read of your screen, not advice.");
        cardText.setText(sb); card.setVisibility(View.VISIBLE);
        main.removeCallbacks(hideCard); main.postDelayed(hideCard, v.pic.equals("eye") ? 60000 : 12000);
    }

    // ---------------------------------------------------------------- one read
    private void readNow() {
        if (down || busy) return;
        long left = ScreenLogic.waitLeft(System.currentTimeMillis(), lastRead);
        if (left > 0) { showCard(new ScreenLogic.Verdict("watch", "One moment", "One read every 10 seconds. Try again in " + ((left + 999) / 1000) + " s.", ScreenLogic.SUN, false, "wait")); return; }
        busy = true; lastRead = System.currentTimeMillis();
        bubble.set(ScreenLogic.SKY, true);
        if (card != null) card.setVisibility(View.GONE);      // out of the picture
        bubble.setVisibility(View.INVISIBLE);                // keep our own bubble out of the picture
        main.postDelayed(new Runnable() { @Override public void run() { grab(); } }, 300);
    }

    private void finish(ScreenLogic.Verdict v) {
        busy = false;
        if (down) return;
        bubble.setVisibility(View.VISIBLE); bubble.set(v.ring, false); showCard(v);
    }

    private void grab() {
        if (down) return;
        Bitmap shot = null;
        try {
            Image img = reader.acquireLatestImage();
            if (img == null) { finish(new ScreenLogic.Verdict("info", "Nothing captured yet", "Try again in a moment.", ScreenLogic.SKY, false, "wait")); return; }
            try {
                Image.Plane pl = img.getPlanes()[0]; ByteBuffer buf = pl.getBuffer();
                int ps = pl.getPixelStride(), rs = pl.getRowStride();
                Bitmap full = Bitmap.createBitmap(rs / ps, capH, Bitmap.Config.ARGB_8888);
                full.copyPixelsFromBuffer(buf);
                shot = Bitmap.createBitmap(full, 0, 0, capW, capH);
                if (shot != full) full.recycle();
            } finally { img.close(); }
        } catch (Exception e) { finish(new ScreenLogic.Verdict("stop", "I could not capture the screen", "Try again, or stop and start the screen assistant.", ScreenLogic.BERRY, false, "cx")); return; }
        final Bitmap pic = shot; final String ep = endpoint, tk = token, cx = context;
        bubble.setVisibility(View.VISIBLE);
        showCard(new ScreenLogic.Verdict("info", "Looking at your chart...", "Hold on. I am reading the chart and asking the bot what it thinks.", ScreenLogic.SKY, false, "eye"));
        new Thread(new Runnable() { @Override public void run() {
            final ScreenLogic.Verdict v = send(pic, ep, tk, cx);
            main.post(new Runnable() { @Override public void run() { finish(v); } });
        } }).start();
    }

    /** Encodes (long side 1280, JPEG 70/55/40 until under the server's limit), posts, drops the picture. Runs off the main thread. */
    private ScreenLogic.Verdict send(Bitmap pic, String ep, String tk, String cx) {
        String b64 = null;
        try {
            if (ep == null || tk == null) return ScreenLogic.verdict(401, "");
            int[] sz = ScreenLogic.fit(pic.getWidth(), pic.getHeight());
            if (sz == null) return ScreenLogic.verdict(500, "");
            Bitmap small = (sz[0] == pic.getWidth()) ? pic : Bitmap.createScaledBitmap(pic, sz[0], sz[1], true);
            for (int q : ScreenLogic.QUALITY) {
                ByteArrayOutputStream bo = new ByteArrayOutputStream();
                small.compress(Bitmap.CompressFormat.JPEG, q, bo);
                b64 = Base64.encodeToString(bo.toByteArray(), Base64.NO_WRAP);
                if (b64.length() <= ScreenLogic.MAX_B64) break;
                b64 = null;
            }
            if (small != pic) small.recycle();
            if (b64 == null) return ScreenLogic.verdict(413, "{\"error\":\"That picture is too big to send.\"}");
            byte[] payload = ScreenLogic.body(b64, cx).getBytes("UTF-8");
            HttpURLConnection c = (HttpURLConnection) new URL(ep).openConnection();
            try {
                c.setRequestMethod("POST"); c.setDoOutput(true); c.setConnectTimeout(15000); c.setReadTimeout(45000);
                c.setRequestProperty("Content-Type", "application/json"); c.setRequestProperty("Authorization", "Bearer " + tk);
                c.setFixedLengthStreamingMode(payload.length);
                OutputStream os = c.getOutputStream(); os.write(payload); os.close();
                int code = c.getResponseCode();
                InputStream in = code >= 400 ? c.getErrorStream() : c.getInputStream();
                String text = "";
                if (in != null) {
                    ByteArrayOutputStream ro = new ByteArrayOutputStream(); byte[] buf = new byte[4096]; int n;
                    while ((n = in.read(buf)) > 0 && ro.size() < 65536) ro.write(buf, 0, n);
                    in.close(); text = ro.toString("UTF-8");
                }
                if (code == 401) token = null;                   // expired: the page must hand over a new one
                return ScreenLogic.verdict(code, text);
            } finally { c.disconnect(); }
        } catch (Exception e) {
            return ScreenLogic.verdict(0, "");
        } finally { b64 = null; pic.recycle(); }
    }

    // ---------------------------------------------------------------- stop
    private void shutdown() {
        if (down) return;
        down = true; running = false;
        main.removeCallbacksAndMessages(null);
        try { if (bubble != null) wm.removeView(bubble); } catch (Exception e) { /* already gone */ }
        try { if (card != null) wm.removeView(card); } catch (Exception e) { /* already gone */ }
        bubble = null; card = null; cardPic = null; cardText = null;
        try { if (display != null) display.release(); } catch (Exception e) { /* ignore */ }
        try { if (reader != null) reader.close(); } catch (Exception e) { /* ignore */ }
        try { if (projection != null) projection.stop(); } catch (Exception e) { /* ignore */ }
        display = null; reader = null; projection = null;
        token = null; endpoint = null;                          // nothing about the person outlives the service
        try { stopForeground(true); } catch (Exception e) { /* ignore */ }
        stopSelf();
    }
}

package com.spacexbot.app;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import androidx.activity.result.ActivityResult;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

/** SC3: the page asks for the floating bubble. Order: https address and sign-in token -> "Display over other apps" permission -> Android's own screen-share
 *  consent (asked EVERY time, Android 14+) -> OverlayService (foreground service of type mediaProjection) shows the bubble and posts the pictures itself,
 *  because the page's JavaScript is paused while the app is in the background. The token is kept in memory only. */
@CapacitorPlugin(name = "SxbScreen")
public class ScreenPlugin extends Plugin {

    @PluginMethod
    public void status(PluginCall call) {
        JSObject o = new JSObject();
        o.put("sdk", Build.VERSION.SDK_INT);
        o.put("overlayAllowed", Build.VERSION.SDK_INT < 23 || Settings.canDrawOverlays(getContext()));
        o.put("running", OverlayService.running());
        call.resolve(o);
    }

    @PluginMethod
    public void start(PluginCall call) {
        String endpoint = ScreenLogic.endpoint(call.getString("server"), true);
        String token = call.getString("token");
        if (endpoint == null) { call.reject("The server address must start with https://", "BAD_SERVER"); return; }
        if (token == null || token.length() < 20) { call.reject("Please sign in first.", "NO_TOKEN"); return; }
        if (Build.VERSION.SDK_INT >= 23 && !Settings.canDrawOverlays(getContext())) {
            Intent i = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:" + getContext().getPackageName()));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(i);
            call.reject("Allow \"Display over other apps\" for spaceXBot, then press Watch again.", "NEED_OVERLAY");
            return;
        }
        MediaProjectionManager mpm = (MediaProjectionManager) getContext().getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        if (mpm == null) { call.reject("This phone cannot share its screen.", "NO_PROJECTION"); return; }
        OverlayService.configure(endpoint, token, "learn".equals(call.getString("context")) ? "learn" : "trade");
        startActivityForResult(call, mpm.createScreenCaptureIntent(), "onCapture");
    }

    @ActivityCallback
    private void onCapture(PluginCall call, ActivityResult result) {
        if (call == null) return;
        if (result == null || result.getResultCode() != Activity.RESULT_OK || result.getData() == null) {
            OverlayService.clear();
            call.reject("Screen sharing was not allowed.", "DENIED");
            return;
        }
        Intent svc = new Intent(getContext(), OverlayService.class);
        svc.setAction(OverlayService.ACTION_START);
        svc.putExtra("code", result.getResultCode());
        svc.putExtra("data", result.getData());
        try {
            if (Build.VERSION.SDK_INT >= 26) getContext().startForegroundService(svc); else getContext().startService(svc);
        } catch (Exception e) {
            OverlayService.clear();
            call.reject("Could not start the screen assistant.", "START_FAILED");
            return;
        }
        JSObject o = new JSObject(); o.put("running", true); call.resolve(o);
    }

    /** The page hands over a fresh sign-in token (they expire); kept in memory only. */
    @PluginMethod
    public void setToken(PluginCall call) {
        String t = call.getString("token");
        if (t == null || t.length() < 20) { call.reject("Bad token.", "NO_TOKEN"); return; }
        OverlayService.setToken(t);
        call.resolve();
    }

    @PluginMethod
    public void stop(PluginCall call) {
        Intent svc = new Intent(getContext(), OverlayService.class);
        svc.setAction(OverlayService.ACTION_STOP);
        try { getContext().startService(svc); } catch (Exception e) { /* not running */ }
        OverlayService.clear();
        call.resolve();
    }
}

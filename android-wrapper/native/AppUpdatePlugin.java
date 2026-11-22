package com.spacexbot.app;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import androidx.core.content.FileProvider;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/** In-app update: downloads the new APK itself (no browser, no GitHub page), reports progress to the page, then opens Android's installer. */
@CapacitorPlugin(name = "SxbUpdate")
public class AppUpdatePlugin extends Plugin {
    interface Progress { void on(long done, long total); }

    private volatile boolean busy = false;

    static File apkFile(File cache) { return new File(new File(cache, "updates"), "spacexbot.apk"); }

    /** Only https on GitHub's own hosts is trusted (the release link redirects to githubusercontent). strict=false is for tests. */
    static boolean allowed(URL u, boolean strict) {
        if (!strict) return true;
        String h = u.getHost() == null ? "" : u.getHost().toLowerCase();
        return "https".equals(u.getProtocol()) && (h.equals("github.com") || h.endsWith(".github.com") || h.endsWith(".githubusercontent.com"));
    }

    /** Downloads url into <cache>/updates/spacexbot.apk. Follows up to 6 redirects, checks the size and the APK (zip) header. Returns the file. */
    static File fetch(String url, File cache, Progress cb, boolean strict) throws Exception {
        File out = apkFile(cache); File dir = out.getParentFile();
        if (!dir.exists() && !dir.mkdirs()) throw new Exception("cannot make the update folder");
        File part = new File(dir, "spacexbot.apk.part");
        URL u = new URL(url);
        HttpURLConnection c = null;
        for (int hop = 0; hop <= 6; hop++) {
            if (!allowed(u, strict)) throw new Exception("the download address is not allowed");
            c = (HttpURLConnection) u.openConnection();
            c.setInstanceFollowRedirects(false); c.setConnectTimeout(15000); c.setReadTimeout(30000);
            int code = c.getResponseCode();
            if (code >= 300 && code < 400) {
                String loc = c.getHeaderField("Location"); c.disconnect();
                if (loc == null) throw new Exception("bad redirect");
                u = new URL(u, loc); c = null; continue;
            }
            if (code != 200) { c.disconnect(); throw new Exception("server answered " + code); }
            break;
        }
        if (c == null) throw new Exception("too many redirects");
        long total = c.getContentLengthLong(), done = 0, lastT = 0; int lastP = -1;
        try (InputStream in = c.getInputStream(); FileOutputStream fo = new FileOutputStream(part)) {
            byte[] buf = new byte[32768]; int n;
            while ((n = in.read(buf)) > 0) {
                fo.write(buf, 0, n); done += n;
                int p = total > 0 ? (int) (done * 100 / total) : 0; long now = System.currentTimeMillis();
                if (cb != null && (p != lastP) && (now - lastT > 120 || p == 100)) { lastP = p; lastT = now; cb.on(done, total); }
            }
        } finally { c.disconnect(); }
        if (total > 0 && done != total) { part.delete(); throw new Exception("the download was cut short"); }
        boolean zip = false;
        try (InputStream in = new java.io.FileInputStream(part)) { zip = in.read() == 'P' && in.read() == 'K'; }
        if (done < 1024 || !zip) { part.delete(); throw new Exception("the file is not an app"); }
        if (out.exists()) out.delete();
        if (!part.renameTo(out)) throw new Exception("cannot save the file");
        if (cb != null) cb.on(done, done);
        return out;
    }

    @PluginMethod
    public void download(final PluginCall call) {
        final String url = call.getString("url");
        if (url == null || url.length() == 0) { call.reject("no address"); return; }
        if (busy) { call.reject("already downloading"); return; }
        busy = true;
        final File cache = getContext().getCacheDir();
        new Thread(new Runnable() { public void run() {
            try {
                File f = fetch(url, cache, new Progress() { public void on(long d, long t) {
                    JSObject o = new JSObject(); o.put("pct", t > 0 ? (int) (d * 100 / t) : 0); o.put("done", d); o.put("total", t); notifyListeners("progress", o);
                } }, true);
                JSObject r = new JSObject(); r.put("bytes", f.length()); call.resolve(r);
            } catch (Exception e) { call.reject("download failed: " + (e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage())); }
            finally { busy = false; }
        } }).start();
    }

    @PluginMethod
    public void install(PluginCall call) {
        Context c = getContext(); File f = apkFile(c.getCacheDir());
        if (!f.exists()) { call.reject("no downloaded update"); return; }
        JSObject r = new JSObject();
        if (Build.VERSION.SDK_INT >= 26 && !c.getPackageManager().canRequestPackageInstalls()) {
            Intent s = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + c.getPackageName()));
            s.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); c.startActivity(s);
            r.put("needPermission", true); call.resolve(r); return;
        }
        Uri uri = FileProvider.getUriForFile(c, c.getPackageName() + ".sxbupdate", f);
        Intent i = new Intent(Intent.ACTION_VIEW); i.setDataAndType(uri, "application/vnd.android.package-archive");
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK); c.startActivity(i);
        r.put("needPermission", false); r.put("started", true); call.resolve(r);
    }

    /** Deletes the downloaded file (called after a successful update). */
    @PluginMethod
    public void cleanup(PluginCall call) {
        File f = apkFile(getContext().getCacheDir()); boolean gone = !f.exists() || f.delete();
        JSObject r = new JSObject(); r.put("deleted", gone); call.resolve(r);
    }
}

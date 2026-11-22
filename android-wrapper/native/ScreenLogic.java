package com.spacexbot.app;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** SC3: the screen assistant's logic that needs no Android classes, so it can be tested with plain javac. Nothing here keeps or logs a picture or a token.
 *  Colours are baked ONCE from the site's dark palette (the native bubble cannot read CSS variables): green #4CD97B, sun #FFCB3D, berry #FF7377, sky #5BB0FF,
 *  muted #9AA5BF, surface #1A2130, line #303A52, fg #EEF1F8. */
final class ScreenLogic {
    private ScreenLogic() {}

    static final int GAP_MS = 11000;            // the server wants 10 s between reads of one person; one second more
    static final int MAX_SIDE = 1280;           // long side of the picture sent
    static final int MAX_B64 = 780000;          // the server refuses more than 800000 base64 characters
    static final int[] QUALITY = {70, 55, 40};  // JPEG quality steps, best first
    static final String PATH = "/api/screen/read";

    static final int GREEN = 0xFF4CD97B, SUN = 0xFFFFCB3D, BERRY = 0xFFFF7377, SKY = 0xFF5BB0FF, MUTED = 0xFF9AA5BF, SURFACE = 0xFF1A2130, LINE = 0xFF303A52, FG = 0xFFEEF1F8;

    /** Only an https address is accepted (strict=false is for tests). Returns the full read address, or null. */
    static String endpoint(String server, boolean strict) {
        if (server == null) return null;
        String s = server.trim();
        while (s.endsWith("/")) s = s.substring(0, s.length() - 1);
        boolean ok = s.startsWith("https://") || (!strict && s.startsWith("http://"));
        if (!ok || s.length() < 12 || s.indexOf(' ') >= 0 || s.indexOf('?') >= 0 || s.indexOf('#') >= 0 || s.indexOf('@') >= 0) return null;
        return s + PATH;
    }

    /** Milliseconds still to wait before the next read is allowed (0 = go). */
    static long waitLeft(long now, long last) {
        if (last <= 0) return 0;
        long left = GAP_MS - (now - last);
        return left > 0 ? left : 0;
    }

    /** Size to send: long side at most MAX_SIDE, never bigger than the source. Returns {w, h} or null. */
    static int[] fit(int w, int h) {
        if (w < 1 || h < 1) return null;
        double k = Math.min(1.0, (double) MAX_SIDE / Math.max(w, h));
        return new int[] {Math.max(1, (int) Math.round(w * k)), Math.max(1, (int) Math.round(h * k))};
    }

    /** The request body. The picture is base64 (only A-Z a-z 0-9 + / =), the context is trade or learn; nothing else is allowed in. */
    static String body(String b64, String ctx) {
        if (b64 == null || !b64.matches("[A-Za-z0-9+/=]+")) throw new IllegalArgumentException("picture is not base64");
        String c = "learn".equals(ctx) ? "learn" : "trade";
        return "{\"context\":\"" + c + "\",\"image\":\"" + b64 + "\"}";
    }

    /** What the bubble shows. tone: ok | watch | stop | info. ring = the colour of the bubble's ring. */
    static final class Verdict {
        final String tone, head, say; final int ring; final boolean signIn;
        Verdict(String tone, String head, String say, int ring, boolean signIn) { this.tone = tone; this.head = head; this.say = say; this.ring = ring; this.signIn = signIn; }
    }

    private static String s(Object o) { return o instanceof String ? (String) o : ""; }

    /** Server answer -> what to show. Mirrors pick() in static/screen.js. status 0 = no connection. */
    @SuppressWarnings("unchecked")
    static Verdict verdict(int status, String json) {
        Object root = null;
        try { root = Json.parse(json); } catch (RuntimeException e) { root = null; }
        Map<String, Object> m = root instanceof Map ? (Map<String, Object>) root : new HashMap<String, Object>();
        if (status == 0) return new Verdict("stop", "No connection", "I could not reach the server. Check your internet and tap me again.", BERRY, false);
        if (status == 401) return new Verdict("stop", "Please sign in", "Open spaceXBot once so I can sign in again, then tap me.", BERRY, true);
        if (status != 200) {
            String t = s(m.get("error")); if (t.length() == 0) t = "Something went wrong. Try again in a moment.";
            if (status == 429) return new Verdict("watch", "One moment", t, SUN, false);
            if (status == 402) return new Verdict("watch", "You need an active plan", t, SUN, false);
            if (status == 403) return new Verdict("stop", "The screen assistant is off", t, BERRY, false);
            return new Verdict("stop", "I could not read it this time", t, BERRY, false);
        }
        Object rd0 = m.get("read"); Map<String, Object> rd = rd0 instanceof Map ? (Map<String, Object>) rd0 : new HashMap<String, Object>();
        if (!Boolean.TRUE.equals(rd.get("readable"))) {
            String n = s(rd.get("note")); if (n.length() == 0) n = "Show one market with its name and price on the screen, then try again.";
            return new Verdict("stop", "I could not read this chart", n, BERRY, false);
        }
        Object b0 = m.get("bot");
        if (!(b0 instanceof Map)) return new Verdict("info", "I read the chart", s(rd.get("note")), SKY, false);
        Map<String, Object> b = (Map<String, Object>) b0; String code = s(b.get("code")), say = s(b.get("text"));
        if ("agree".equals(code)) return new Verdict("ok", "I see a possible trade.", say + side(b) + sizeText(b), GREEN, false);
        if ("blocked".equals(code)) return new Verdict("watch", "I see a setup, but I cannot trade right now.", say, SUN, false);
        if ("disagree".equals(code)) return new Verdict("watch", "We do not agree, so I stay out.", say, SUN, false);
        if ("no_setup".equals(code)) return new Verdict("info", "Nothing to trade here yet.", say, MUTED, false);
        if ("bot_only".equals(code)) return new Verdict("watch", "The bot sees a setup.", say, SUN, false);
        return new Verdict("info", "I can only give you the AI read.", say, SKY, false);
    }

    /** The bot's OWN entry, stop and target in words (never the AI's). Empty when the bot gave no signal. */
    @SuppressWarnings("unchecked")
    private static String side(Map<String, Object> bot) {
        Object g = bot.get("signal"); if (!(g instanceof Map)) return "";
        Map<String, Object> x = (Map<String, Object>) g;
        if (!(x.get("entry") instanceof Number) || !(x.get("sl") instanceof Number) || !(x.get("tp") instanceof Number)) return "";
        return "  Entry " + num(x.get("entry")) + ", stop " + num(x.get("sl")) + ", target " + num(x.get("tp")) + " (the bot's own).";
    }

    /** PH3 Suggest: the lot size the server worked out from the person's own balance and risk, or its plain-words reason. Empty when the server sent none. */
    @SuppressWarnings("unchecked")
    private static String sizeText(Map<String, Object> bot) {
        Object z0 = bot.get("size"); if (!(z0 instanceof Map)) return "";
        Map<String, Object> z = (Map<String, Object>) z0;
        if (z.get("lots") instanceof Number) return "  Suggested size " + num(z.get("lots")) + " lot" + (z.get("risk_usd") instanceof Number ? ", risk about $" + num(z.get("risk_usd")) : "") + ". Check it in your MT5 order screen.";
        String w = s(z.get("why")); return w.length() > 0 ? "  " + w : "";
    }

    private static String num(Object o) {
        double d = ((Number) o).doubleValue();
        return d == Math.rint(d) ? String.valueOf((long) d) : String.format(java.util.Locale.US, "%.2f", d);
    }

    /** A small JSON reader (objects, arrays, strings, numbers, true/false/null). Throws RuntimeException on anything else. */
    static final class Json {
        private final String t; private int i = 0;
        private Json(String t) { this.t = t == null ? "" : t; }
        static Object parse(String text) { Json j = new Json(text); j.ws(); Object v = j.val(0); j.ws(); if (j.i != j.t.length()) throw new RuntimeException("extra text"); return v; }
        private void ws() { while (i < t.length() && " \t\r\n".indexOf(t.charAt(i)) >= 0) i++; }
        private char peek() { if (i >= t.length()) throw new RuntimeException("end"); return t.charAt(i); }
        private Object val(int depth) {
            if (depth > 20) throw new RuntimeException("too deep");
            char c = peek();
            if (c == '{') {
                i++; Map<String, Object> m = new HashMap<String, Object>(); ws();
                if (peek() == '}') { i++; return m; }
                while (true) { ws(); String k = str(); ws(); if (peek() != ':') throw new RuntimeException(":"); i++; ws(); m.put(k, val(depth + 1)); ws();
                    char d = peek(); i++; if (d == '}') return m; if (d != ',') throw new RuntimeException(","); }
            }
            if (c == '[') {
                i++; List<Object> a = new ArrayList<Object>(); ws();
                if (peek() == ']') { i++; return a; }
                while (true) { ws(); a.add(val(depth + 1)); ws(); char d = peek(); i++; if (d == ']') return a; if (d != ',') throw new RuntimeException(","); }
            }
            if (c == '"') return str();
            if (t.startsWith("true", i)) { i += 4; return Boolean.TRUE; }
            if (t.startsWith("false", i)) { i += 5; return Boolean.FALSE; }
            if (t.startsWith("null", i)) { i += 4; return null; }
            int s0 = i; while (i < t.length() && "+-0123456789.eE".indexOf(t.charAt(i)) >= 0) i++;
            if (s0 == i) throw new RuntimeException("bad value");
            return Double.valueOf(t.substring(s0, i));
        }
        private String str() {
            if (peek() != '"') throw new RuntimeException("string expected"); i++;
            StringBuilder b = new StringBuilder();
            while (true) {
                char c = peek(); i++;
                if (c == '"') return b.toString();
                if (c != '\\') { b.append(c); continue; }
                char e = peek(); i++;
                switch (e) {
                    case 'n': b.append('\n'); break; case 't': b.append('\t'); break; case 'r': b.append('\r'); break; case 'b': b.append('\b'); break; case 'f': b.append('\f'); break;
                    case '/': case '"': case '\\': b.append(e); break;
                    case 'u': if (i + 4 > t.length()) throw new RuntimeException("bad escape"); b.append((char) Integer.parseInt(t.substring(i, i + 4), 16)); i += 4; break;
                    default: throw new RuntimeException("bad escape");
                }
            }
        }
    }
}

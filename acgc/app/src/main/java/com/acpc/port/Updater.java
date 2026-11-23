package com.acpc.port;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import androidx.core.content.FileProvider;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/** Checks the GitHub releases for a newer build, downloads it in the background and offers to install it. */
final class Updater {
    private static final String API = "https://api.github.com/repos/logie-github/Warcrafting/releases/latest";
    private static boolean started;

    static void check(final Activity a) {
        if (started) return;
        started = true;
        new Thread(() -> {
            try {
                PackageInfo pi = a.getPackageManager().getPackageInfo(a.getPackageName(), 0);
                long have = Build.VERSION.SDK_INT >= 28 ? pi.getLongVersionCode() : pi.versionCode;
                JSONObject rel = new JSONObject(readText(API));
                String tag = rel.optString("tag_name", "");
                int dash = tag.lastIndexOf('-');
                long latest = dash >= 0 ? Long.parseLong(tag.substring(dash + 1)) : -1;
                if (latest <= have) return;
                String url = null;
                JSONArray assets = rel.optJSONArray("assets");
                for (int i = 0; assets != null && i < assets.length(); i++) {
                    JSONObject o = assets.getJSONObject(i);
                    if (o.optString("name").endsWith(".apk")) { url = o.getString("browser_download_url"); break; }
                }
                if (url == null) return;
                File dir = new File(a.getExternalFilesDir(null), "updates");
                dir.mkdirs();
                File[] old = dir.listFiles();
                if (old != null) for (File f : old) if (!f.getName().equals("Warcrafting-" + latest + ".apk")) f.delete();
                final File apk = new File(dir, "Warcrafting-" + latest + ".apk");
                if (!apk.exists() || apk.length() < 1_000_000) download(url, apk);
                final String name = rel.optString("name", "build " + latest);
                a.runOnUiThread(() -> prompt(a, name, apk));
            } catch (Throwable t) {
                // offline or rate limited: try again on the next launch
            }
        }, "updater").start();
    }

    private static void prompt(final Activity a, String name, final File apk) {
        if (a.isFinishing()) return;
        new AlertDialog.Builder(a)
            .setTitle("Update ready")
            .setMessage(name + " has been downloaded. Install it now?")
            .setPositiveButton("Install", (d, w) -> install(a, apk))
            .setNegativeButton("Later", null)
            .show();
    }

    private static void install(Activity a, File apk) {
        if (Build.VERSION.SDK_INT >= 26 && !a.getPackageManager().canRequestPackageInstalls()) {
            a.startActivity(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + a.getPackageName())));
            return;
        }
        Uri u = FileProvider.getUriForFile(a, a.getPackageName() + ".updates", apk);
        Intent i = new Intent(Intent.ACTION_VIEW);
        i.setDataAndType(u, "application/vnd.android.package-archive");
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
        a.startActivity(i);
    }

    private static HttpURLConnection open(String u) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(u).openConnection();
        c.setConnectTimeout(15000);
        c.setReadTimeout(30000);
        c.setRequestProperty("Accept", "application/vnd.github+json");
        c.setRequestProperty("User-Agent", "Warcrafting-Updater");
        c.setInstanceFollowRedirects(true);
        return c;
    }

    private static String readText(String u) throws Exception {
        HttpURLConnection c = open(u);
        try (InputStream in = c.getInputStream()) {
            java.io.ByteArrayOutputStream b = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[8192]; int n;
            while ((n = in.read(buf)) > 0) b.write(buf, 0, n);
            return b.toString("UTF-8");
        }
    }

    private static void download(String u, File out) throws Exception {
        File tmp = new File(out.getPath() + ".part");
        HttpURLConnection c = open(u);
        try (InputStream in = c.getInputStream(); FileOutputStream o = new FileOutputStream(tmp)) {
            byte[] buf = new byte[65536]; int n;
            while ((n = in.read(buf)) > 0) o.write(buf, 0, n);
        }
        if (!tmp.renameTo(out)) throw new java.io.IOException("rename failed");
    }

    private Updater() {}
}

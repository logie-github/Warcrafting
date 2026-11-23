package com.acpc.port;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.ViewGroup;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

/** The Town Builder: place Warcraft III buildings and props, replace original buildings. The page lives in
 *  assets/builder/index.html; every change is written to the placements file the game loads at launch. */
public class BuilderActivity extends Activity {

    static File placementsFile(android.content.Context ctx, String faction) {
        return new File(ctx.getFilesDir(), "build_placements_" + faction + ".txt");
    }

    private WebView web;

    private final Object bridge = new Object() {
        @JavascriptInterface
        public void save(String faction, String text) {
            try (FileOutputStream o = new FileOutputStream(placementsFile(BuilderActivity.this,
                    "Horde".equals(faction) ? "Horde" : "Alliance"))) {
                o.write(text.getBytes(StandardCharsets.UTF_8));
            } catch (Exception ignored) {
            }
        }

        @JavascriptInterface
        public void share(String text) {
            Intent i = new Intent(Intent.ACTION_SEND);
            i.setType("text/plain");
            i.putExtra(Intent.EXTRA_TEXT, text);
            startActivity(Intent.createChooser(i, "Share town report"));
        }
    };

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        web = new WebView(this);
        web.setBackgroundColor(Color.rgb(21, 22, 26));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        web.setWebViewClient(new WebViewClient());
        web.addJavascriptInterface(bridge, "Android");
        setContentView(web, new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        web.loadUrl("file:///android_asset/builder/index.html");
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) web.goBack(); else super.onBackPressed();
    }
}

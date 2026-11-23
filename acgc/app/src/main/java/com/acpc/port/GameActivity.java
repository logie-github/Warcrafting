package com.acpc.port;

import android.os.Bundle;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.ViewGroup;
import android.view.WindowManager;

import org.libsdl.app.SDLActivity;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

public class GameActivity extends SDLActivity {

    /** Pushes the on-screen pad state into PADRead (android_glue.c). */
    public static native void nativeTouchPad(int buttons, int stickX, int stickY, int cstickX, int cstickY);
    public static native void nativeBuildCmd(int cmd, int arg);
    public static native String nativeBuildStatus();

    private TouchControlsView touchControls;

    @Override
    protected String[] getLibraries() {
        // single library: game code + SDL2 static
        return new String[]{"AnimalCrossing"};
    }

    @Override
    protected String[] getArguments() {
        return new String[0]; // "--verbose" enables the diagnostic logs in files/stdout.log
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        extractAssetsOnce();
        try {
            int ch = getSharedPreferences("warcrafting", MODE_PRIVATE).getInt("character", 0);
            android.system.Os.setenv("AC_PLAYER_MODEL", String.valueOf(Math.max(0, Math.min(3, ch))), true);
            String town = getSharedPreferences("warcrafting", MODE_PRIVATE).getString("town", "alliance");
            android.system.Os.setenv("AC_TOWN", "horde".equals(town) ? "horde" : "alliance", true);
            android.system.Os.setenv("AC_MUSIC", "horde".equals(town) ? "orgrimmar" : "off", true);
            if (getIntent() != null && getIntent().getBooleanExtra("builder", false)) android.system.Os.setenv("AC_BUILDER", "1", true);
            else android.system.Os.unsetenv("AC_BUILDER");
            android.system.Os.setenv("AC_MODELS_BIN", new File(getFilesDir(), "models.bin").getAbsolutePath(), true);
            android.system.Os.setenv("AC_BUILD_FILE", BuilderActivity.placementsFile(this, "horde".equals(town) ? "Horde" : "Alliance").getAbsolutePath(), true);
        } catch (Exception ignored) {
        }
        super.onCreate(savedInstanceState);
        if (mLayout != null && touchOverlayEnabled(this)) {
            touchControls = new TouchControlsView(this);
            mLayout.addView(touchControls, new ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        }
        if (mLayout != null && getIntent() != null && getIntent().getBooleanExtra("builder", false)) {
            mLayout.addView(buildToolbar(), new ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        }
    }

    static boolean touchOverlayEnabled(android.content.Context ctx) {
        return ctx.getSharedPreferences("controls", MODE_PRIVATE).getBoolean("touch_overlay", true);
    }

    static void setTouchOverlayEnabled(android.content.Context ctx, boolean on) {
        ctx.getSharedPreferences("controls", MODE_PRIVATE).edit().putBoolean("touch_overlay", on).apply();
    }

    /** A physical controller or keyboard hides the overlay; touching the screen shows it again. */
    private void hideTouchControls() {
        if (touchControls != null && touchControls.getAlpha() > 0f) {
            touchControls.setAlpha(0f);
            touchControls.reset();
        }
    }

    @Override
    public boolean dispatchTouchEvent(MotionEvent ev) {
        if (touchControls != null && touchControls.getAlpha() == 0f
                && ev.getActionMasked() == MotionEvent.ACTION_DOWN) {
            touchControls.setAlpha(1f);
        }
        return super.dispatchTouchEvent(ev);
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        int vol = event.getKeyCode();
        if (vol != KeyEvent.KEYCODE_VOLUME_UP && vol != KeyEvent.KEYCODE_VOLUME_DOWN
                && vol != KeyEvent.KEYCODE_BACK && event.getDeviceId() > 0) {
            hideTouchControls();
        }
        return super.dispatchKeyEvent(event);
    }

    @Override
    public boolean dispatchGenericMotionEvent(MotionEvent ev) {
        if ((ev.getSource() & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK) {
            hideTouchControls();
        }
        return super.dispatchGenericMotionEvent(ev);
    }

    /** The native layer loads shaders and writes saves relative to filesDir. */
    private void extractAssetsOnce() {
        File dir = getFilesDir();
        File[] dirs = {
                new File(dir, "rom"), new File(dir, "save"),
                new File(dir, "save/card_a"), new File(dir, "save/card_b"),
                new File(dir, "texture_pack"), new File(dir, "shaders"),
        };
        for (File d : dirs) if (!d.exists()) d.mkdirs();

        installMod(dir);
        copyAssetIfNeeded("shaders/default.vert", new File(dir, "shaders/default.vert"));
        copyAssetIfNeeded("shaders/default.frag", new File(dir, "shaders/default.frag"));
    }

    /** Mod texture pack bundled in the APK (assets/mod). Re-extracted when the app version or the town changes. */
    private void installMod(File filesDir) {
        try {
            String town = getSharedPreferences("warcrafting", MODE_PRIVATE).getString("town", "alliance");
            if (!"horde".equals(town)) town = "alliance";
            String version;
            try {
                version = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
            } catch (Exception e) {
                version = "0";
            }
            String stamp = version + "|" + town;
            File packDir = new File(filesDir, "texture_pack");
            File marker = new File(packDir, ".warcrafting_mod");
            if (marker.exists()) {
                try (java.io.BufferedReader r = new java.io.BufferedReader(new java.io.FileReader(marker))) {
                    if (stamp.equals(r.readLine())) return;
                }
            }
            // drop the previous town's files, then copy this town's pack plus the common files
            File[] old = packDir.listFiles();
            if (old != null) {
                for (File f : old) {
                    if (f.getName().startsWith("tex1_") && f.getName().endsWith(".dds")) f.delete();
                }
            }
            for (String sub : new String[] { town, "common" }) {
                String[] names = getAssets().list("mod/" + sub);
                if (names == null) continue;
                for (String n : names) {
                    File out = new File(packDir, n);
                    try (InputStream in = getAssets().open("mod/" + sub + "/" + n);
                         OutputStream os = new FileOutputStream(out)) {
                        byte[] buf = new byte[1 << 16];
                        int c;
                        while ((c = in.read(buf)) > 0) os.write(buf, 0, c);
                    }
                }
            }
            // Warcraft III model library for the build mode
            try (InputStream in = getAssets().open("mod/models.bin");
                 OutputStream os = new FileOutputStream(new File(filesDir, "models.bin"))) {
                byte[] buf = new byte[1 << 16];
                int c;
                while ((c = in.read(buf)) > 0) os.write(buf, 0, c);
            } catch (java.io.IOException ignored) {
            }
            // replacement town music (OGG) next to the working directory: music/
            String[] tracks = getAssets().list("mod/music");
            if (tracks != null && tracks.length > 0) {
                File musicDir = new File(filesDir, "music");
                musicDir.mkdirs();
                for (String n : tracks) {
                    File out = new File(musicDir, n);
                    try (InputStream in = getAssets().open("mod/music/" + n);
                         OutputStream os = new FileOutputStream(out)) {
                        byte[] buf = new byte[1 << 16];
                        int c;
                        while ((c = in.read(buf)) > 0) os.write(buf, 0, c);
                    }
                }
            }
            try (java.io.FileWriter w = new java.io.FileWriter(marker)) {
                w.write(stamp + "\n");
            }
        } catch (Exception ignored) {
        }
    }

    private void copyAssetIfNeeded(String asset, File target) {
        if (target.exists() && target.length() > 0) return;
        try (InputStream in = getAssets().open(asset);
             OutputStream out = new FileOutputStream(target)) {
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        } catch (Exception ignored) {
        }
    }

    /* ---------- Town Builder (the real game with a placement toolbar) ---------- */

    private android.widget.TextView builderStatus;
    private final android.os.Handler builderHandler = new android.os.Handler(android.os.Looper.getMainLooper());
    private java.util.List<String> libNames, libCats;

    private void loadLibrary() {
        libNames = new java.util.ArrayList<>(); libCats = new java.util.ArrayList<>();
        try (java.io.BufferedReader r = new java.io.BufferedReader(new java.io.InputStreamReader(getAssets().open("mod/library.txt")))) {
            String line;
            while ((line = r.readLine()) != null) {
                int i = line.indexOf(" | ");
                if (i < 0) continue;
                libCats.add(line.substring(0, i)); libNames.add(line.substring(i + 3));
            }
        } catch (Exception ignored) {
        }
    }

    private android.widget.Button tbBtn(String label, final int cmd) {
        android.widget.Button b = new android.widget.Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(13);
        b.setTextColor(0xFFF6E7B4);
        b.setTypeface(android.graphics.Typeface.create(android.graphics.Typeface.SERIF, android.graphics.Typeface.BOLD));
        android.graphics.drawable.GradientDrawable g = new android.graphics.drawable.GradientDrawable();
        g.setColor(0xDD1A1208); g.setCornerRadius(10f); g.setStroke(3, 0xFFB8892B);
        b.setBackground(g);
        b.setMinWidth(0); b.setMinimumWidth(0);
        b.setPadding(24, 6, 24, 6);
        b.setOnClickListener(v -> nativeBuildCmd(cmd, 0));
        android.widget.LinearLayout.LayoutParams lp = new android.widget.LinearLayout.LayoutParams(-2, -2);
        lp.setMargins(6, 4, 6, 4);
        b.setLayoutParams(lp);
        return b;
    }

    private android.view.View buildToolbar() {
        loadLibrary();
        android.widget.LinearLayout bar = new android.widget.LinearLayout(this);
        bar.setOrientation(android.widget.LinearLayout.VERTICAL);
        bar.setBackgroundColor(0xAA000000);
        builderStatus = new android.widget.TextView(this);
        builderStatus.setTextColor(0xFFFFD35A); builderStatus.setTextSize(13); builderStatus.setPadding(14, 6, 14, 2);
        builderStatus.setTypeface(android.graphics.Typeface.create(android.graphics.Typeface.SERIF, android.graphics.Typeface.BOLD));
        bar.addView(builderStatus);
        android.widget.HorizontalScrollView hs = new android.widget.HorizontalScrollView(this);
        android.widget.LinearLayout row = new android.widget.LinearLayout(this);
        android.widget.Button pick = tbBtn("Models ▾", 0);
        pick.setOnClickListener(v -> pickModel());
        row.addView(pick);
        row.addView(tbBtn("◀", 3)); row.addView(tbBtn("▶", 2));
        row.addView(tbBtn("Place", 4)); row.addView(tbBtn("Pick up", 13)); row.addView(tbBtn("Delete", 5)); row.addView(tbBtn("Undo", 11));
        row.addView(tbBtn("⟲", 12)); row.addView(tbBtn("⟳", 6)); row.addView(tbBtn("＋", 7)); row.addView(tbBtn("－", 8));
        row.addView(tbBtn("◄", 17)); row.addView(tbBtn("►", 16)); row.addView(tbBtn("▲", 14)); row.addView(tbBtn("▼", 15)); row.addView(tbBtn("Reset", 18));
        row.addView(tbBtn("Top / Player view", 30)); row.addView(tbBtn("Zoom in", 31)); row.addView(tbBtn("Zoom out", 32));
        row.addView(tbBtn("Replace building", 9)); row.addView(tbBtn("Restore building", 10));
        android.widget.Button share = tbBtn("Share", 0);
        share.setOnClickListener(v -> shareLayout());
        row.addView(share);
        hs.addView(row);
        bar.addView(hs);
        android.widget.FrameLayout.LayoutParams lp = new android.widget.FrameLayout.LayoutParams(-1, -2);
        lp.gravity = android.view.Gravity.TOP;
        bar.setLayoutParams(lp);
        builderHandler.post(new Runnable() {
            @Override public void run() {
                try { builderStatus.setText(nativeBuildStatus()); } catch (Throwable ignored) { }
                builderHandler.postDelayed(this, 400);
            }
        });
        return bar;
    }

    private void pickModel() {
        if (libNames == null || libNames.isEmpty()) return;
        final android.widget.EditText q = new android.widget.EditText(this);
        q.setHint("Search buildings and props");
        final android.widget.ListView lv = new android.widget.ListView(this);
        final java.util.List<Integer> shown = new java.util.ArrayList<>();
        final android.widget.ArrayAdapter<String> ad = new android.widget.ArrayAdapter<>(this, android.R.layout.simple_list_item_1, new java.util.ArrayList<String>());
        lv.setAdapter(ad);
        final Runnable refill = () -> {
            String t = q.getText().toString().trim().toLowerCase(java.util.Locale.ROOT);
            ad.clear(); shown.clear();
            for (int i = 0; i < libNames.size(); i++) {
                String label = libNames.get(i) + "   (" + libCats.get(i) + ")";
                if (t.isEmpty() || label.toLowerCase(java.util.Locale.ROOT).contains(t)) { ad.add(label); shown.add(i); }
            }
        };
        q.addTextChangedListener(new android.text.TextWatcher() {
            public void beforeTextChanged(CharSequence s, int a, int b, int c) { }
            public void onTextChanged(CharSequence s, int a, int b, int c) { refill.run(); }
            public void afterTextChanged(android.text.Editable e) { }
        });
        refill.run();
        android.widget.LinearLayout box = new android.widget.LinearLayout(this);
        box.setOrientation(android.widget.LinearLayout.VERTICAL);
        box.addView(q); box.addView(lv);
        final android.app.AlertDialog d = new android.app.AlertDialog.Builder(this).setTitle("Choose a model").setView(box).setNegativeButton("Close", null).create();
        lv.setOnItemClickListener((p, v, pos, id) -> { nativeBuildCmd(40, shown.get(pos)); d.dismiss(); });
        d.show();
    }

    private void shareLayout() {
        try {
            String town = getSharedPreferences("warcrafting", MODE_PRIVATE).getString("town", "alliance");
            File f = BuilderActivity.placementsFile(this, "horde".equals(town) ? "Horde" : "Alliance");
            StringBuilder sb = new StringBuilder();
            if (f.exists()) {
                try (java.io.BufferedReader r = new java.io.BufferedReader(new java.io.FileReader(f))) {
                    String line;
                    while ((line = r.readLine()) != null) sb.append(line).append('\n');
                }
            }
            android.content.Intent i = new android.content.Intent(android.content.Intent.ACTION_SEND);
            i.setType("text/plain");
            i.putExtra(android.content.Intent.EXTRA_TEXT, sb.length() == 0 ? "(nothing placed yet)" : sb.toString());
            startActivity(android.content.Intent.createChooser(i, "Share town layout"));
        } catch (Exception ignored) {
        }
    }
}

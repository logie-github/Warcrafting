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
}

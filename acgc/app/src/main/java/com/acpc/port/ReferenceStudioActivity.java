package com.acpc.port;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Rect;
import android.net.Uri;
import android.os.Bundle;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.Spinner;
import android.widget.ArrayAdapter;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;

/** Local staging area for generated character references. */
public class ReferenceStudioActivity extends Activity {
    private static final int PICK_SHEET = 105;
    private static final int PICK_VIEW = 110;
    private static final int EXPORT = 120;
    private static final String[] VIEW_NAMES = {"Front", "Right", "Back", "Left"};
    private boolean busy;
    private int selectedResolution=96;
    private LinearLayout layout;
    private TextView status;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        ScrollView scroll = new ScrollView(this);
        layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(32, 32, 32, 32);
        layout.setBackgroundColor(Color.rgb(21, 22, 26));
        scroll.addView(layout);
        setContentView(scroll);
        showHome();
    }
    private TextView text(String value, int size) {
        TextView v = new TextView(this);
        v.setText(value); v.setTextSize(size); v.setTextColor(Color.WHITE);
        v.setPadding(0, 12, 0, 12); return v;
    }
    private void showHome() {
        layout.removeAllViews();
        layout.addView(text("Character Reference Studio", 24));
        layout.addView(text("Import separate generated views of the same character. Images are stored on this device.", 16));
        status = text("", 16); layout.addView(status);
        layout.addView(text("Experimental silhouette guide", 20));
        layout.addView(text("Reference sheet: top left FRONT · top right RIGHT · bottom left BACK · bottom right LEFT", 16));
        Button prompt=new Button(this); prompt.setText("Copy reference-sheet prompt");
        prompt.setOnClickListener(v -> {
            String value="Create a single 2 by 2 character reference image for: [describe character]. "
                    + "Top left: front view. Top right: right-side view. Bottom left: back view. Bottom right: left-side view. "
                    + "Every panel shows the exact same full-body character, pose, proportions, outfit and lighting. "
                    + "Upright neutral A-pose with arms separated from the body and legs separated. "
                    + "Orthographic camera, centered body at exactly the same height and scale in each equal-sized panel. "
                    + "Use a plain white background and fill each panel with the full body, including head and feet, without cropping. "
                    + "No words, borders, labels, shadows, extra characters, perspective, or decorative elements. "
                    + "Place each view fully within its own quadrant without overlapping panel boundaries.";
            android.content.ClipboardManager clipboard=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
            clipboard.setPrimaryClip(ClipData.newPlainText("Character reference prompt",value));
            status.setText("Prompt copied. Replace [describe character] before sending it.");
        });
        layout.addView(prompt);
        Button sheet=new Button(this); sheet.setText("Import 2 × 2 reference sheet");
        sheet.setOnClickListener(v -> {
            if(busy)return;
            Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT); intent.addCategory(Intent.CATEGORY_OPENABLE); intent.setType("image/*");
            startActivityForResult(intent,PICK_SHEET);
        });
        layout.addView(sheet);
        layout.addView(text("Choose four separate, aligned full-body images on transparent or plain backgrounds. This creates a rough, photo-projected guide; it does not yet produce a finished character.", 16));
        for (int i=0; i<VIEW_NAMES.length; i++) {
            final int view=i;
            Button button=new Button(this);
            button.setText(VIEW_NAMES[i] + (viewFile(i).isFile() ? " ✓" : " — select image"));
            button.setOnClickListener(v -> {
                if (busy) return;
                Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("image/*");
                startActivityForResult(intent, PICK_VIEW+view);
            });
            layout.addView(button);
            if(viewFile(i).isFile()) {
                BitmapFactory.Options bounds=new BitmapFactory.Options(); bounds.inJustDecodeBounds=true;
                BitmapFactory.decodeFile(viewFile(i).getAbsolutePath(),bounds);
                BitmapFactory.Options thumbOptions=new BitmapFactory.Options(); thumbOptions.inSampleSize=1;
                while(bounds.outWidth/thumbOptions.inSampleSize>320 || bounds.outHeight/thumbOptions.inSampleSize>320) thumbOptions.inSampleSize*=2;
                Bitmap thumbnail=BitmapFactory.decodeFile(viewFile(i).getAbsolutePath(),thumbOptions);
                if(thumbnail!=null) {
                    ImageView image=new ImageView(this); image.setImageBitmap(thumbnail); image.setAdjustViewBounds(true);
                    image.setContentDescription(VIEW_NAMES[i]+" reference image");
                    int height=(int)(160*getResources().getDisplayMetrics().density);
                    image.setMaxHeight(height); image.setScaleType(ImageView.ScaleType.FIT_CENTER);
                    layout.addView(image,new LinearLayout.LayoutParams(-1,height));
                }
            }
        }
        layout.addView(text("Guide detail", 16));
        Spinner quality=new Spinner(this);
        String[] choices={"Draft (faster)", "Standard", "High (uses more memory)"};
        quality.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,choices));
        quality.setSelection(1);
        layout.addView(quality);
        Button generate=new Button(this);
        generate.setText("Export rough rigged GLB");
        generate.setOnClickListener(v -> {
            if (busy) return;
            for(int i=0;i<4;i++) if(!viewFile(i).isFile()) { status.setText("Choose all four views first."); return; }
            selectedResolution=quality.getSelectedItemPosition()==0?64:quality.getSelectedItemPosition()==2?128:96;
            Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT);
            save.addCategory(Intent.CATEGORY_OPENABLE);
            save.setType("model/gltf-binary");
            save.putExtra(Intent.EXTRA_TITLE,"character-guide.glb");
            startActivityForResult(save, EXPORT);
        });
        layout.addView(generate);
    }
    private File viewFile(int i) { return new File(getNoBackupFilesDir(), "character_view_"+i+".image"); }
    private void importSheet(Uri uri) {
        busy=true; status.setText("Splitting reference sheet…");
        new Thread(() -> {
            String error=null;
            File[] tmp=new File[4];
            try {
                BitmapFactory.Options options=new BitmapFactory.Options(); options.inSampleSize=1;
                Bitmap bitmap;
                try(InputStream in=getContentResolver().openInputStream(uri)) {
                    if(in==null)throw new java.io.IOException("Cannot open image");
                    BitmapFactory.Options bounds=new BitmapFactory.Options(); bounds.inJustDecodeBounds=true;
                    BitmapFactory.decodeStream(in,null,bounds);
                    if(bounds.outWidth<4 || bounds.outHeight<4)throw new java.io.IOException("Not a supported image");
                    while(bounds.outWidth/options.inSampleSize>4096 || bounds.outHeight/options.inSampleSize>4096)options.inSampleSize*=2;
                }
                try(InputStream in=getContentResolver().openInputStream(uri)) {
                    if(in==null)throw new java.io.IOException("Cannot open image");
                    bitmap=BitmapFactory.decodeStream(in,null,options);
                }
                if(bitmap==null)throw new java.io.IOException("Cannot decode reference sheet");
                int w=bitmap.getWidth()/2,h=bitmap.getHeight()/2;
                try {
                    for(int i=0;i<4;i++) {
                        tmp[i]=new File(getCacheDir(),"sheet-view-"+i+".png");
                        Bitmap part=Bitmap.createBitmap(bitmap,(i%2)*w,(i/2)*h,w,h);
                        try(FileOutputStream out=new FileOutputStream(tmp[i])) {
                            if(!part.compress(Bitmap.CompressFormat.PNG,100,out))throw new java.io.IOException("Cannot save panel");
                            out.getFD().sync();
                        } finally {part.recycle();}
                    }
                } finally {bitmap.recycle();}
                for(int i=0;i<4;i++) if(!tmp[i].renameTo(viewFile(i)))throw new java.io.IOException("Cannot save panel "+VIEW_NAMES[i]);
            } catch(Exception e) {error=e.getMessage();}
            for(File f:tmp)if(f!=null)f.delete();
            final String result=error;
            runOnUiThread(() -> {busy=false;showHome();status.setText(result==null?"Four views imported from the sheet.":"Sheet import failed: "+result);});
        }).start();
    }
    private void copyView(Uri uri, int view) {
        File temporary = new File(getCacheDir(), "reference-view-"+view+".tmp");
        busy=true; status.setText("Saving " + VIEW_NAMES[view] + " view…");
        new Thread(() -> {
            String error=null;
            try (InputStream in=getContentResolver().openInputStream(uri); FileOutputStream out=new FileOutputStream(temporary)) {
                if(in==null) throw new java.io.IOException("Cannot open image");
                byte[] bytes=new byte[32768]; int n; while((n=in.read(bytes))!=-1)out.write(bytes,0,n);
                out.getFD().sync();
            } catch(Exception e) { error=e.getMessage(); }
            if(error==null) {
                BitmapFactory.Options opts=new BitmapFactory.Options(); opts.inJustDecodeBounds=true;
                BitmapFactory.decodeFile(temporary.getAbsolutePath(),opts);
                if(opts.outWidth<2 || opts.outHeight<2) error="That file is not a supported image.";
                else if(!temporary.renameTo(viewFile(view))) error="Could not save the image.";
            }
            temporary.delete(); final String result=error;
            runOnUiThread(() -> {busy=false; showHome(); if(result!=null) status.setText("Import failed: "+result);});
        }).start();
    }
    private void exportGuide(Uri uri) {
        busy=true; status.setText("Building a rough guide on this device…");
        new Thread(() -> {
            String error=null; boolean success=false;
            try {
                VisualHull.Mask[] masks=new VisualHull.Mask[4];
                for(int i=0;i<4;i++) {
                    BitmapFactory.Options bounds=new BitmapFactory.Options(); bounds.inJustDecodeBounds=true;
                    BitmapFactory.decodeFile(viewFile(i).getAbsolutePath(),bounds);
                    BitmapFactory.Options options=new BitmapFactory.Options(); options.inSampleSize=1;
                    while(bounds.outWidth/options.inSampleSize>1024 || bounds.outHeight/options.inSampleSize>1024) options.inSampleSize*=2;
                    Bitmap bitmap=BitmapFactory.decodeFile(viewFile(i).getAbsolutePath(),options);
                    if(bitmap==null) throw new java.io.IOException("Cannot decode "+VIEW_NAMES[i]+" view");
                    int w=bitmap.getWidth(),h=bitmap.getHeight(); int[] pixels=new int[w*h]; bitmap.getPixels(pixels,0,w,0,0,w,h); bitmap.recycle();
                    masks[i]=new VisualHull.Mask(w,h,ReferenceMask.extract(pixels,w,h,35),pixels);
                }
                masks=ReferenceAlignment.align(masks,768);
                Bitmap atlas=Bitmap.createBitmap(2048,2048,Bitmap.Config.ARGB_8888);
                Canvas canvas=new Canvas(atlas); Paint paint=new Paint(Paint.FILTER_BITMAP_FLAG);
                for(int i=0;i<4;i++) {
                    Bitmap panel=Bitmap.createBitmap(masks[i].colors,masks[i].width,masks[i].height,Bitmap.Config.ARGB_8888);
                    canvas.drawBitmap(panel,null,new Rect((i%2)*1024,(i/2)*1024,(i%2+1)*1024,(i/2+1)*1024),paint);
                    panel.recycle();
                }
                java.io.ByteArrayOutputStream texture=new java.io.ByteArrayOutputStream();
                try {if(!atlas.compress(Bitmap.CompressFormat.PNG,100,texture))throw new java.io.IOException("Cannot encode the texture");} finally {atlas.recycle();}
                VisualHull.Mesh mesh=VisualHull.build(masks,selectedResolution);
                try(java.io.OutputStream out=getContentResolver().openOutputStream(uri,"wt")) {
                    if(out==null) throw new java.io.IOException("Cannot open output document");
                    RiggedGlbWriter.writeTextured(out,mesh.positions,mesh.triangles,mesh.uv,texture.toByteArray(),mesh.normals);
                }
                success=true;
            } catch(OutOfMemoryError e) { error="Not enough memory. Try Draft quality."; }
            catch(Exception e) { error=e.getMessage(); }
            final boolean ok=success; final String message=error;
            runOnUiThread(() -> {busy=false; status.setText(ok ? "Rough guide exported. Inspect the shape and rig before using it." : "Export failed: "+message);});
        }).start();
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (result != RESULT_OK || data == null) return;
        if(request==PICK_SHEET && data.getData()!=null) { importSheet(data.getData()); return; }
        if(request>=PICK_VIEW && request<PICK_VIEW+4 && data.getData()!=null) { copyView(data.getData(), request-PICK_VIEW); return; }
        if(request==EXPORT && data.getData()!=null) { exportGuide(data.getData()); return; }
    }
}

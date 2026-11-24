package com.acpc.port;

import java.io.FileOutputStream;
import java.util.Arrays;
import java.nio.file.Files;
import java.nio.file.Paths;

public final class ConversionCheck {
    private static void check(boolean ok,String message) { if(!ok)throw new AssertionError(message); }
    private static int[] bounds(VisualHull.Mask m) {
        int x0=m.width,y0=m.height,x1=0,y1=0;
        for(int y=0;y<m.height;y++)for(int x=0;x<m.width;x++)if(m.foreground[y*m.width+x]){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
        return new int[]{x0,y0,x1,y1};
    }
    public static void main(String[] args) throws Exception {
        int[] rgba={0xffffffff,0xffffffff,0xffffffff,0xffffffff,0xff211700,0xffffffff,0xffffffff,0xffffffff,0xffffffff};
        boolean[] mask=ReferenceMask.extract(rgba,3,3,20);
        check(mask[4] && !mask[0],"Flood fill must preserve the subject and remove the background");
        int[] transparent={0,0,0,0,0xffffffff,0,0,0,0};
        boolean[] alpha=ReferenceMask.extract(transparent,3,3,20);
        check(alpha[4] && !alpha[0],"Alpha mask must preserve opaque pixels");
        int w=40,h=80; boolean[] silhouette=new boolean[w*h]; int[] colors=new int[w*h]; Arrays.fill(colors,0xffa76f48);
        for(int y=0;y<h;y++) for(int x=0;x<w;x++) {
            float xx=(x-w*.5f)/(w*.32f), yy=(y-h*.5f)/(h*.46f);
            silhouette[y*w+x]=xx*xx+yy*yy<1;
        }
        VisualHull.Mask view=new VisualHull.Mask(w,h,silhouette,colors);
        boolean[] shifted=new boolean[w*h];
        for(int y=12;y<68;y++)for(int x=8;x<23;x++)shifted[y*w+x]=true;
        VisualHull.Mask other=new VisualHull.Mask(w,h,shifted,colors);
        VisualHull.Mask[] aligned=ReferenceAlignment.align(new VisualHull.Mask[]{view,other,view,other},128);
        int[] first=bounds(aligned[0]),second=bounds(aligned[1]);
        check(Math.abs(first[1]-second[1])<=2 && Math.abs(first[3]-second[3])<=2,"Heads and feet should align");
        check(Math.abs((first[0]+first[2])-(second[0]+second[2]))<=2,"Subjects should be horizontally centered");
        VisualHull.Mesh model=VisualHull.build(new VisualHull.Mask[]{view,view,view,view},40);
        check(model.positions.length>0 && model.triangles.length>0,"No reconstructed surface");
        check(model.colors.length==model.positions.length/3*4,"Missing projected colors");
        float minX=1,maxX=-1;
        for(int i=0;i<model.positions.length;i+=3){minX=Math.min(minX,model.positions[i]);maxX=Math.max(maxX,model.positions[i]);}
        check(maxX-minX<.5f,"Portrait aspect must be reflected in model proportions");
        HumanoidRig.Result rig=HumanoidRig.estimate(model.positions);
        for(int i=0;i<rig.weights.length;i+=4) {
            float sum=rig.weights[i]+rig.weights[i+1]+rig.weights[i+2]+rig.weights[i+3];
            check(Math.abs(sum-1f)<1e-5,"Vertex weights must sum to one");
        }
        try(FileOutputStream out=new FileOutputStream(args[0])) { RiggedGlbWriter.writeTextured(out,model.positions,model.triangles,model.uv,Files.readAllBytes(Paths.get(args[1])),model.normals); }
        boolean[] empty=new boolean[w*h]; VisualHull.Mask e=new VisualHull.Mask(w,h,empty);
        boolean rejected=false;
        try{VisualHull.build(new VisualHull.Mask[]{e,e,e,e},16);} catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"Empty silhouettes must be rejected");
        System.out.println("Mask, visual hull, aspect ratio, skin weights and GLB export passed");
    }
}

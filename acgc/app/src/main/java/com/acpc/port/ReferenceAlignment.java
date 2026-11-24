package com.acpc.port;

import java.util.Arrays;

/** Aligns the foreground bounding boxes without changing each view's aspect ratio. */
public final class ReferenceAlignment {
    private ReferenceAlignment() {}
    public static VisualHull.Mask[] align(VisualHull.Mask[] input, int size) {
        if(input==null || input.length!=4 || size<32 || size>2048) throw new IllegalArgumentException("Four reference views are required");
        int[][] boxes=new int[4][4]; float widest=1;
        for(int i=0;i<4;i++) {
            VisualHull.Mask m=input[i]; if(m==null)throw new IllegalArgumentException("Missing reference view");
            int x0=m.width,y0=m.height,x1=-1,y1=-1;
            for(int y=0;y<m.height;y++)for(int x=0;x<m.width;x++)if(m.foreground[y*m.width+x]) {x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
            if(x1<x0 || y1<y0)throw new IllegalArgumentException("A reference view contains no subject");
            boxes[i]=new int[]{x0,y0,x1+1,y1+1}; widest=Math.max(widest,(float)(x1-x0+1)/(y1-y0+1));
        }
        float targetHeight=size*.88f/widest;
        VisualHull.Mask[] out=new VisualHull.Mask[4];
        for(int i=0;i<4;i++) {
            VisualHull.Mask m=input[i];int[] box=boxes[i];
            float scale=targetHeight/(box[3]-box[1]);
            float center=(box[0]+box[2])*.5f, left=size*.5f-center*scale, top=(size-targetHeight)*.5f-box[1]*scale;
            boolean[] mask=new boolean[size*size]; int[] colors=m.colors==null?null:new int[size*size];
            if(colors!=null)Arrays.fill(colors,0xffffffff);
            for(int y=0;y<size;y++) {
                int sy=(int)Math.floor((y+.5f-top)/scale); if(sy<0 || sy>=m.height)continue;
                for(int x=0;x<size;x++) {
                    int sx=(int)Math.floor((x+.5f-left)/scale); if(sx<0 || sx>=m.width)continue;
                    int src=sy*m.width+sx,dst=y*size+x;mask[dst]=m.foreground[src];if(colors!=null)colors[dst]=m.colors[src];
                }
            }
            out[i]=new VisualHull.Mask(size,size,mask,colors);
        }
        return out;
    }
}

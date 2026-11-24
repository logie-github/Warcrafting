package com.acpc.port;

/** Extracts foreground from transparency or a near-uniform border background. */
public final class ReferenceMask {
    private ReferenceMask() {}
    public static boolean[] extract(int[] pixels, int width, int height, int tolerance) {
        if(width<2 || height<2 || pixels==null || (long)width*height!=pixels.length || tolerance<0 || tolerance>255)
            throw new IllegalArgumentException("Invalid reference image");
        int clearPixels=0;
        for(int c:pixels) if((c>>>24)<128) clearPixels++;
        boolean transparent=clearPixels >= Math.max(1,pixels.length/100);
        boolean[] fg=new boolean[pixels.length];
        if(transparent) {
            for(int i=0;i<pixels.length;i++) fg[i]=(pixels[i]>>>24)>=128;
            return clean(fg,width,height);
        }
        int corner=pixels[0]; boolean[] bg=new boolean[pixels.length]; int[] queue=new int[pixels.length]; int head=0,tail=0;
        for(int x=0;x<width;x++) {int a=x,b=(height-1)*width+x; if(!bg[a] && near(pixels[a],corner,tolerance)){bg[a]=true;queue[tail++]=a;} if(!bg[b] && near(pixels[b],corner,tolerance)){bg[b]=true;queue[tail++]=b;}}
        for(int y=1;y<height-1;y++) {int a=y*width,b=a+width-1; if(!bg[a] && near(pixels[a],corner,tolerance)){bg[a]=true;queue[tail++]=a;} if(!bg[b] && near(pixels[b],corner,tolerance)){bg[b]=true;queue[tail++]=b;}}
        while(head<tail) {
            int i=queue[head++], x=i%width,y=i/width;
            if(x>0) tail=push(i-1,pixels,bg,queue,tail,corner,tolerance);
            if(x+1<width) tail=push(i+1,pixels,bg,queue,tail,corner,tolerance);
            if(y>0) tail=push(i-width,pixels,bg,queue,tail,corner,tolerance);
            if(y+1<height) tail=push(i+width,pixels,bg,queue,tail,corner,tolerance);
        }
        for(int i=0;i<fg.length;i++) fg[i]=!bg[i];
        return clean(fg,width,height);
    }
    private static boolean[] clean(boolean[] fg,int width,int height) {
        int[] labels=new int[fg.length], sizes=new int[fg.length/2+2], queue=new int[fg.length];
        int components=0,largest=0,total=0;
        for(int start=0;start<fg.length;start++) {
            if(!fg[start] || labels[start]!=0) continue;
            int id=++components,head=0,tail=0; labels[start]=id;queue[tail++]=start;
            while(head<tail) {
                int i=queue[head++],x=i%width,y=i/width;
                if(x>0)tail=label(i-1,id,fg,labels,queue,tail);
                if(x+1<width)tail=label(i+1,id,fg,labels,queue,tail);
                if(y>0)tail=label(i-width,id,fg,labels,queue,tail);
                if(y+1<height)tail=label(i+width,id,fg,labels,queue,tail);
            }
            sizes[id]=tail;largest=Math.max(largest,tail);total+=tail;
        }
        if(total < fg.length/200 || total > fg.length*95L/100) throw new IllegalArgumentException("Could not separate the subject from the background. Use a plain background or transparency.");
        int threshold=Math.max(1,largest/1000);
        for(int i=0;i<fg.length;i++)if(labels[i]>0 && sizes[labels[i]]<threshold)fg[i]=false;
        return fg;
    }
    private static int label(int i,int id,boolean[] fg,int[] labels,int[] queue,int tail) {
        if(fg[i] && labels[i]==0){labels[i]=id;queue[tail++]=i;}return tail;
    }
    private static int push(int i,int[] pixels,boolean[] bg,int[] queue,int tail,int corner,int tolerance){
        if(!bg[i] && near(pixels[i],corner,tolerance)){bg[i]=true;queue[tail++]=i;} return tail;
    }
    private static boolean near(int a,int b,int t) {
        return Math.abs(((a>>>16)&255)-((b>>>16)&255))<=t && Math.abs(((a>>>8)&255)-((b>>>8)&255))<=t && Math.abs((a&255)-(b&255))<=t;
    }
}

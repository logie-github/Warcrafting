package com.acpc.port;

import java.util.Arrays;

/** Silhouette-derived guide geometry for four orthographic views: front, right, back, left. */
public final class VisualHull {
    private VisualHull() {}
    public static final int FRONT=0, RIGHT=1, BACK=2, LEFT=3;
    public static final class Mask {
        public final int width, height;
        public final boolean[] foreground;
        public final int[] colors;
        public Mask(int width, int height, boolean[] foreground) { this(width,height,foreground,null); }
        public Mask(int width, int height, boolean[] foreground, int[] colors) {
            if(width<2 || height<2 || foreground==null || (long)width*height!=foreground.length) throw new IllegalArgumentException("Invalid silhouette dimensions");
            if(colors!=null && colors.length!=foreground.length) throw new IllegalArgumentException("Invalid color dimensions");
            this.width=width; this.height=height; this.foreground=foreground; this.colors=colors;
        }
        int color(float horizontal, float vertical) {
            if(colors==null) return 0xffffffff;
            int x=Math.max(0,Math.min(width-1,(int)(horizontal*width)));
            int y=Math.max(0,Math.min(height-1,(int)(vertical*height)));
            return colors[y*width+x];
        }
        boolean sample(float horizontal, float vertical) {
            if(horizontal<0 || horizontal>1 || vertical<0 || vertical>1) return false;
            int x=Math.min(width-1,(int)(horizontal*width));
            int y=Math.min(height-1,(int)(vertical*height));
            return foreground[y*width+x];
        }
    }
    public static final class Mesh {
        public final float[] positions;
        public final int[] triangles;
        public final float[] colors;
        public final float[] uv;
        public final float[] normals;
        Mesh(float[] positions,int[] triangles,float[] colors,float[] uv,float[] normals){this.positions=positions;this.triangles=triangles;this.colors=colors;this.uv=uv;this.normals=normals;}
    }
    /** Images are aligned, same scale, upright, with their subject centered; background already masked out. */
    public static Mesh build(Mask[] views, int resolution) {
        if(views==null || views.length!=4) throw new IllegalArgumentException("Four silhouette slots are required");
        for(Mask m:views) if(m==null) throw new IllegalArgumentException("Front, right, back and left silhouettes are required");
        if(resolution<8 || resolution>160) throw new IllegalArgumentException("Resolution must be between 8 and 160");
        int n=resolution; long volume=(long)n*n*n;
        boolean[] voxels=new boolean[(int)volume]; int count=0;
        for(int y=0;y<n;y++) for(int z=0;z<n;z++) for(int x=0;x<n;x++) {
            float fx=(x+.5f)/n, fy=1f-(y+.5f)/n, fz=(z+.5f)/n;
            if(views[FRONT].sample(fx,fy) && views[RIGHT].sample(1-fz,fy) && views[BACK].sample(1-fx,fy) && views[LEFT].sample(fz,fy)) {
                voxels[(y*n+z)*n+x]=true; count++;
            }
        }
        if(count==0) throw new IllegalArgumentException("The four silhouettes do not overlap; align the images and try again");
        Floats positions=new Floats(), normals=new Floats(); Colors vertexColors=new Colors(); UVs texcoords=new UVs(); Ints triangles=new Ints();
        float scaleX=((float)views[FRONT].width/views[FRONT].height+(float)views[BACK].width/views[BACK].height)*.5f;
        float scaleZ=((float)views[RIGHT].width/views[RIGHT].height+(float)views[LEFT].width/views[LEFT].height)*.5f;
        // Vertices ordered counter-clockwise when viewed from outside.
        int[][] corners={{0,0,0,0,0,1,0,1,1,0,1,0}, {1,0,0,1,1,0,1,1,1,1,0,1},
                         {0,0,0,1,0,0,1,0,1,0,0,1}, {0,1,0,0,1,1,1,1,1,1,1,0},
                         {0,0,0,0,1,0,1,1,0,1,0,0}, {0,0,1,1,0,1,1,1,1,0,1,1}};
        int[][] dirs={{-1,0,0},{1,0,0},{0,-1,0},{0,1,0},{0,0,-1},{0,0,1}};
        for(int y=0;y<n;y++)for(int z=0;z<n;z++)for(int x=0;x<n;x++) {
            if(!voxels[(y*n+z)*n+x])continue;
            for(int f=0;f<6;f++) {
                int nx=x+dirs[f][0],ny=y+dirs[f][1],nz=z+dirs[f][2];
                if(nx>=0 && nx<n && ny>=0 && ny<n && nz>=0 && nz<n && voxels[(ny*n+nz)*n+nx])continue;
                if(triangles.size/6>=100000) throw new IllegalArgumentException("Surface is too complex for this quality. Try a cleaner background or lower quality.");
                int base=positions.size/3; int[] face=corners[f];
                for(int j=0;j<4;j++) {
                    float fx=(x+face[j*3])/(float)n, fy=(y+face[j*3+1])/(float)n, fz=(z+face[j*3+2])/(float)n;
                    int gx=x+face[j*3],gy=y+face[j*3+1],gz=z+face[j*3+2];
                    float sx=0,sy=0,sz=0;int neighbours=0;
                    for(int oy=-1;oy<=0;oy++)for(int oz=-1;oz<=0;oz++)for(int ox=-1;ox<=0;ox++) {
                        int px=gx+ox,py=gy+oy,pz=gz+oz;
                        if(px>=0 && px<n && py>=0 && py<n && pz>=0 && pz<n && voxels[(py*n+pz)*n+px]) {
                            sx+=ox+.5f;sy+=oy+.5f;sz+=oz+.5f;neighbours++;
                        }
                    }
                    float shift=neighbours==0?0:.45f/neighbours;
                    positions.add((fx+sx*shift/n-.5f)*scaleX,fy+sy*shift/n,(fz+sz*shift/n-.5f)*scaleZ);
                    float normalX=-sx/scaleX,normalY=-sy,normalZ=-sz/scaleZ,mag=(float)Math.sqrt(normalX*normalX+normalY*normalY+normalZ*normalZ);
                    if(mag>1e-6f)normals.add(normalX/mag,normalY/mag,normalZ/mag); else normals.add(dirs[f][0],dirs[f][1],dirs[f][2]);
                    int v=f==0?RIGHT:f==1?LEFT:f==4?BACK:FRONT;
                    float u=v==FRONT?fx:v==BACK?1-fx:v==RIGHT?1-fz:fz;
                    vertexColors.add(views[v].color(u,1-fy));
                    texcoords.add((v%2+.001f+.998f*u)*.5f,(v/2+.001f+.998f*(1-fy))*.5f);
                }
                triangles.add(base,base+1,base+2,base,base+2,base+3);
            }
        }
        return new Mesh(positions.array(),triangles.array(),vertexColors.array(),texcoords.array(),normals.array());
    }
    private static final class UVs { float[] a=new float[1024]; int size; void add(float x,float y){if(size+2>a.length)a=Arrays.copyOf(a,a.length*2);a[size++]=x;a[size++]=y;} float[] array(){return Arrays.copyOf(a,size);} }
    private static final class Colors {
        float[] a=new float[1024]; int size;
        void add(int color) {
            if(size+4>a.length)a=Arrays.copyOf(a,a.length*2);
            a[size++]=linear((color>>>16)&255); a[size++]=linear((color>>>8)&255); a[size++]=linear(color&255); a[size++]=1;
        }
        float linear(int value){float s=value/255f;return s<=.04045f?s/12.92f:(float)Math.pow((s+.055f)/1.055f,2.4);}
        float[] array(){return Arrays.copyOf(a,size);}
    }
    private static final class Floats {float[] a=new float[1024]; int size; void add(float x,float y,float z){if(size+3>a.length)a=Arrays.copyOf(a,a.length*2);a[size++]=x;a[size++]=y;a[size++]=z;}float[] array(){return Arrays.copyOf(a,size);}}
    private static final class Ints {int[] a=new int[1024]; int size; void add(int x,int y,int z,int p,int q,int r){if(size+6>a.length)a=Arrays.copyOf(a,a.length*2);a[size++]=x;a[size++]=y;a[size++]=z;a[size++]=p;a[size++]=q;a[size++]=r;}int[] array(){return Arrays.copyOf(a,size);}}
}

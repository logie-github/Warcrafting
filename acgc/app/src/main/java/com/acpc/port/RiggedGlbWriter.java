package com.acpc.port;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;

/** Writes a skinned triangle mesh to a self-contained glTF 2.0 binary. Coordinates are Y-up. */
public final class RiggedGlbWriter {
    private RiggedGlbWriter() {}
    private static void putInt(OutputStream out, int v) throws IOException {
        out.write(v); out.write(v >>> 8); out.write(v >>> 16); out.write(v >>> 24);
    }
    private static int align(int n) { return (n + 3) & ~3; }
    private static void pad(ByteArrayOutputStream out) { while ((out.size() & 3) != 0) out.write(0); }
    private static byte[] floats(float[] values) {
        ByteBuffer b=ByteBuffer.allocate(values.length*4).order(ByteOrder.LITTLE_ENDIAN);
        for(float v:values) b.putFloat(v); return b.array();
    }
    private static byte[] shorts(short[] values) {
        ByteBuffer b=ByteBuffer.allocate(values.length*2).order(ByteOrder.LITTLE_ENDIAN);
        for(short v:values) b.putShort(v); return b.array();
    }
    private static byte[] ints(int[] values) {
        ByteBuffer b=ByteBuffer.allocate(values.length*4).order(ByteOrder.LITTLE_ENDIAN);
        for(int v:values) b.putInt(v); return b.array();
    }
    /** Mesh positions and face indices are copied into the output stream; caller retains ownership. */
    public static void write(OutputStream out, float[] positions, int[] triangles) throws IOException {
        write(out,positions,triangles,null);
    }
    public static void write(OutputStream out, float[] positions, int[] triangles, float[] colors) throws IOException {
        writeMesh(out,positions,triangles,colors,null,null,null);
    }
    public static void writeTextured(OutputStream out, float[] positions, int[] triangles, float[] uv, byte[] png) throws IOException {
        if(uv==null || png==null || png.length<8) throw new IllegalArgumentException("UV coordinates and PNG texture are required");
        writeMesh(out,positions,triangles,null,uv,png,null);
    }
    public static void writeTextured(OutputStream out, float[] positions, int[] triangles, float[] uv, byte[] png, float[] normals) throws IOException {
        if(uv==null || png==null || png.length<8 || normals==null) throw new IllegalArgumentException("UV coordinates, PNG texture and normals are required");
        writeMesh(out,positions,triangles,null,uv,png,normals);
    }
    private static void writeMesh(OutputStream out, float[] positions, int[] triangles, float[] colors, float[] uv, byte[] png, float[] suppliedNormals) throws IOException {
        if(out==null || positions==null || positions.length<9 || positions.length%3!=0 || triangles==null || triangles.length<3 || triangles.length%3!=0)
            throw new IllegalArgumentException("A triangular mesh is required");
        int count=positions.length/3;
        if(colors!=null && colors.length!=count*4) throw new IllegalArgumentException("Expected one RGBA color per vertex");
        if(colors!=null) for(float color:colors) if(!Float.isFinite(color) || color<0 || color>1) throw new IllegalArgumentException("Invalid vertex color");
        if(uv!=null && uv.length!=count*2) throw new IllegalArgumentException("Expected one UV pair per vertex");
        if(uv!=null) for(float f:uv) if(!Float.isFinite(f) || f<0 || f>1) throw new IllegalArgumentException("Invalid UV coordinates");
        for(int i:triangles) if(i<0 || i>=count) throw new IllegalArgumentException("Triangle index out of range");
        HumanoidRig.Result rig=HumanoidRig.estimate(positions);
        if(suppliedNormals!=null && suppliedNormals.length!=positions.length) throw new IllegalArgumentException("Expected one normal per vertex");
        float[] normals=suppliedNormals==null ? new float[positions.length] : suppliedNormals.clone();
        if(suppliedNormals==null) for(int i=0;i<triangles.length;i+=3) {
            int a=triangles[i]*3,b=triangles[i+1]*3,c=triangles[i+2]*3;
            float ux=positions[b]-positions[a], uy=positions[b+1]-positions[a+1], uz=positions[b+2]-positions[a+2];
            float vx=positions[c]-positions[a], vy=positions[c+1]-positions[a+1], vz=positions[c+2]-positions[a+2];
            float nx=uy*vz-uz*vy, ny=uz*vx-ux*vz, nz=ux*vy-uy*vx;
            for(int k : new int[]{a,b,c}) {normals[k]+=nx; normals[k+1]+=ny; normals[k+2]+=nz;}
        }
        for(int i=0;i<normals.length;i+=3) { float x=normals[i],y=normals[i+1],z=normals[i+2]; if(!Float.isFinite(x)||!Float.isFinite(y)||!Float.isFinite(z))throw new IllegalArgumentException("Invalid normal"); float n=(float)Math.sqrt(x*x+y*y+z*z); if(n>1e-12f){normals[i]/=n;normals[i+1]/=n;normals[i+2]/=n;} else normals[i+1]=1; }
        float[] inverse=new float[HumanoidRig.NAMES.length*16];
        for(int j=0;j<HumanoidRig.NAMES.length;j++) {int i=j*16; inverse[i]=inverse[i+5]=inverse[i+10]=inverse[i+15]=1; inverse[i+12]=-rig.joints[j*3]; inverse[i+13]=-rig.joints[j*3+1]; inverse[i+14]=-rig.joints[j*3+2];}
        byte[][] chunks={floats(positions),floats(normals),shorts(rig.indices),floats(rig.weights),ints(triangles),floats(inverse),colors==null?null:floats(colors),uv==null?null:floats(uv),png};
        ByteArrayOutputStream bin=new ByteArrayOutputStream(); int[] offsets=new int[chunks.length], viewIndex=new int[chunks.length];
        int viewCount=0;
        for(int i=0;i<chunks.length;i++){if(chunks[i]==null)continue;pad(bin);viewIndex[i]=viewCount++;offsets[i]=bin.size();bin.write(chunks[i]);} pad(bin);
        float[] min={Float.POSITIVE_INFINITY,Float.POSITIVE_INFINITY,Float.POSITIVE_INFINITY}, max={Float.NEGATIVE_INFINITY,Float.NEGATIVE_INFINITY,Float.NEGATIVE_INFINITY};
        for(int i=0;i<positions.length;i++){int a=i%3;min[a]=Math.min(min[a],positions[i]);max[a]=Math.max(max[a],positions[i]);}
        StringBuilder json=new StringBuilder("{\"asset\":{\"version\":\"2.0\",\"generator\":\"Warcrafting\"},\"scene\":0,\"scenes\":[{\"nodes\":[0,1]}],\"nodes\":[{\"name\":\"Character\",\"mesh\":0,\"skin\":0},");
        for(int j=0;j<HumanoidRig.NAMES.length;j++) {
            int parent=HumanoidRig.PARENTS[j]; float x=rig.joints[j*3],y=rig.joints[j*3+1],z=rig.joints[j*3+2];
            if(parent>=0){x-=rig.joints[parent*3];y-=rig.joints[parent*3+1];z-=rig.joints[parent*3+2];}
            json.append("{\"name\":\"").append(HumanoidRig.NAMES[j]).append("\",\"translation\":[").append(x).append(',').append(y).append(',').append(z).append(']');
            boolean first=true; for(int child=0;child<HumanoidRig.NAMES.length;child++) if(HumanoidRig.PARENTS[child]==j) {if(first){json.append(",\"children\":[");first=false;}else json.append(',');json.append(child+1);} if(!first)json.append(']');
            json.append('}'); if(j+1<HumanoidRig.NAMES.length)json.append(',');
        }
        json.append("],\"skins\":[{\"inverseBindMatrices\":5,\"skeleton\":1,\"joints\":[");
        for(int j=0;j<HumanoidRig.NAMES.length;j++){if(j>0)json.append(',');json.append(j+1);} json.append("]}],\"meshes\":[{\"primitives\":[{\"attributes\":{\"POSITION\":0,\"NORMAL\":1,\"JOINTS_0\":2,\"WEIGHTS_0\":3"); if(colors!=null)json.append(",\"COLOR_0\":6"); if(uv!=null)json.append(",\"TEXCOORD_0\":6"); json.append("},\"indices\":4"); if(png!=null)json.append(",\"material\":0"); json.append("}]}],");
        if(png!=null)json.append("\"materials\":[{\"pbrMetallicRoughness\":{\"baseColorTexture\":{\"index\":0},\"metallicFactor\":0,\"roughnessFactor\":1}}],\"textures\":[{\"source\":0}],\"images\":[{\"bufferView\":").append(viewIndex[8]).append(",\"mimeType\":\"image/png\"}],");
        json.append("\"buffers\":[{\"byteLength\":").append(bin.size()).append("}],\"bufferViews\":[");
        for(int i=0;i<chunks.length;i++){if(chunks[i]==null)continue;if(i>0)json.append(',');json.append("{\"buffer\":0,\"byteOffset\":").append(offsets[i]).append(",\"byteLength\":").append(chunks[i].length); if(i<5 || i==6 || i==7)json.append(",\"target\":").append(i==4?34963:34962);json.append('}');} json.append("],\"accessors\":[");
        json.append("{\"bufferView\":0,\"componentType\":5126,\"count\":").append(count).append(",\"type\":\"VEC3\",\"min\":[").append(min[0]).append(',').append(min[1]).append(',').append(min[2]).append("],\"max\":[").append(max[0]).append(',').append(max[1]).append(',').append(max[2]).append("]},");
        json.append("{\"bufferView\":1,\"componentType\":5126,\"count\":").append(count).append(",\"type\":\"VEC3\"},");
        json.append("{\"bufferView\":2,\"componentType\":5123,\"count\":").append(count).append(",\"type\":\"VEC4\"},");
        json.append("{\"bufferView\":3,\"componentType\":5126,\"count\":").append(count).append(",\"type\":\"VEC4\"},");
        json.append("{\"bufferView\":4,\"componentType\":5125,\"count\":").append(triangles.length).append(",\"type\":\"SCALAR\"},");
        json.append("{\"bufferView\":5,\"componentType\":5126,\"count\":").append(HumanoidRig.NAMES.length).append(",\"type\":\"MAT4\"}");
        if(colors!=null)json.append(",{\"bufferView\":").append(viewIndex[6]).append(",\"componentType\":5126,\"count\":").append(count).append(",\"type\":\"VEC4\"}");
        if(uv!=null)json.append(",{\"bufferView\":").append(viewIndex[7]).append(",\"componentType\":5126,\"count\":").append(count).append(",\"type\":\"VEC2\"}");
        json.append("]}");
        byte[] js=json.toString().getBytes(StandardCharsets.UTF_8); int jslen=align(js.length), total=12+8+jslen+8+bin.size();
        putInt(out,0x46546c67);putInt(out,2);putInt(out,total);putInt(out,jslen);putInt(out,0x4e4f534a);out.write(js);for(int i=js.length;i<jslen;i++)out.write(' ');
        putInt(out,bin.size());putInt(out,0x004e4942);bin.writeTo(out);
    }
}

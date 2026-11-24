package com.acpc.port;

/** Basic upright, Y-up humanoid skeleton and skin-weight estimation for a neutral A-pose mesh. */
public final class HumanoidRig {
    private HumanoidRig() {}
    public static final String[] NAMES = {"hips", "spine", "chest", "neck", "head", "rightUpperArm", "rightForearm", "rightHand", "leftUpperArm", "leftForearm", "leftHand", "rightUpperLeg", "rightLowerLeg", "rightFoot", "leftUpperLeg", "leftLowerLeg", "leftFoot"};
    public static final int[] PARENTS = {-1, 0, 1, 2, 3, 2, 5, 6, 2, 8, 9, 0, 11, 12, 0, 14, 15};
    public static final class Result {
        public final float[] joints;
        public final short[] indices;
        public final float[] weights;
        Result(float[] joints, short[] indices, float[] weights) { this.joints = joints; this.indices = indices; this.weights = weights; }
    }
    private static float smooth(float low,float high,float x) {
        float t=Math.max(0,Math.min(1,(x-low)/(high-low)));
        return t*t*(3-2*t);
    }
    /** Coordinates must be upright Y-up, centered and approximately symmetrical, in an A-pose. */
    public static Result estimate(float[] xyz) {
        if (xyz == null || xyz.length < 9 || xyz.length % 3 != 0) throw new IllegalArgumentException("Expected xyz positions");
        float minX=Float.POSITIVE_INFINITY, maxX=Float.NEGATIVE_INFINITY, minY=Float.POSITIVE_INFINITY, maxY=Float.NEGATIVE_INFINITY, minZ=Float.POSITIVE_INFINITY, maxZ=Float.NEGATIVE_INFINITY;
        for (int i=0;i<xyz.length;i+=3) {
            float x=xyz[i], y=xyz[i+1], z=xyz[i+2];
            if (!Float.isFinite(x) || !Float.isFinite(y) || !Float.isFinite(z)) throw new IllegalArgumentException("Non-finite vertex");
            minX=Math.min(minX,x); maxX=Math.max(maxX,x); minY=Math.min(minY,y); maxY=Math.max(maxY,y); minZ=Math.min(minZ,z); maxZ=Math.max(maxZ,z);
        }
        float h=maxY-minY, width=maxX-minX, cx=(maxX+minX)/2, z=(maxZ+minZ)/2;
        if (h < 1e-6f || width < 1e-6f) throw new IllegalArgumentException("Degenerate mesh");
        float[] p = {0,.52f, 0,.62f, 0,.74f, 0,.84f, 0,.90f,
            -.17f,.78f, -.29f,.67f, -.43f,.56f, .17f,.78f, .29f,.67f, .43f,.56f,
            -.10f,.49f, -.10f,.27f, -.10f,.06f, .10f,.49f, .10f,.27f, .10f,.06f};
        float[] joints = new float[NAMES.length*3];
        for (int j=0;j<NAMES.length;j++) { joints[3*j]=cx+p[2*j]*width; joints[3*j+1]=minY+p[2*j+1]*h; joints[3*j+2]=z; }
        short[] ids = new short[xyz.length/3*4]; float[] weights = new float[ids.length];
        for (int v=0;v<xyz.length/3;v++) {
            float y=(xyz[3*v+1]-minY)/h, x=(xyz[3*v]-cx)/width, ax=Math.abs(x);
            int a,b; float t;
            if(y>.84f && ax<.16f) { a=3; b=4; t=smooth(.86f,.93f,y); }
            else if(y>.42f && ax>.13f) {
                int arm=x<0?5:8;
                if(ax<.21f) { a=2; b=arm; t=smooth(.13f,.21f,ax); }
                else if(ax<.34f) { a=arm; b=arm+1; t=smooth(.25f,.33f,ax); }
                else { a=arm+1; b=arm+2; t=smooth(.39f,.47f,ax); }
            } else if(y<.51f) {
                int leg=x<0?11:14;
                if(y<.15f) { a=leg+2; b=leg+1; t=smooth(.05f,.13f,y); }
                else if(y<.36f) { a=leg+1; b=leg; t=smooth(.23f,.31f,y); }
                else { a=leg; b=0; t=smooth(.46f,.52f,y); }
            } else if(y<.68f) { a=0; b=1; t=smooth(.58f,.66f,y); }
            else if(y<.80f) { a=1; b=2; t=smooth(.70f,.78f,y); }
            else { a=2; b=3; t=smooth(.80f,.88f,y); }
            float first=1f-t;
            ids[4*v]=(short)(first>0 ? a : 0); weights[4*v]=first;
            ids[4*v+1]=(short)(t>0 ? b : 0); weights[4*v+1]=t;
        }
        return new Result(joints,ids,weights);
    }
}

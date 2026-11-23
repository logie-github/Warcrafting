#include "sys_math.h"
#include "libultra/libultra.h"
#include "libc64/qrand.h"
#include "libc64/math64.h"

extern void init_rnd() {
#ifdef TARGET_PC
    {
        extern char* getenv(const char*);
        extern int atoi(const char*);
        const char* ac_seed = getenv("AC_SEED");
        sqrand(ac_seed ? (u32)atoi(ac_seed) : osGetCount());
    }
#else
    sqrand(osGetCount());
#endif
}

#ifdef MUST_MATCH
FORCESTRIP static f32 _rodata_order(int in) {
    return (f32)in;
}
#endif

extern f32 sinf_table(f32 x) {
    s16 v = (SHT_MAX / M_PI) * x;
    s16 sin = sins(v);

    return sin * SHT_MINV;
}

extern f32 cosf_table(f32 x) {
    s16 v = (SHT_MAX / M_PI) * x;
    s16 cos = coss(v);

    return cos * SHT_MINV;
}

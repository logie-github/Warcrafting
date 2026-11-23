/* pc_music.c - replacement town music (Orgrimmar) streamed from OGG files and mixed into the game audio.
 *
 * Replaces the game's hourly town BGM (ids 1..24) when AC_MUSIC=orgrimmar. Tracks live in music/ next to
 * the executable (the Android launcher extracts them into the files directory). Decoding runs on a worker
 * thread; the audio callback mixes the decoded 32 kHz stereo PCM over the game's own output. */
#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define STB_VORBIS_NO_PUSHDATA_API
#include "../lib/stb_vorbis/stb_vorbis.c"

#define PC_MUSIC_RATE 32000
#define PC_MUSIC_VOLUME 0.55f

static const char* const k_tracks[5] = {
    "music/orgrimmar01-zone.ogg", "music/orgrimmar02-zone.ogg", "music/orgrimmar01-moment.ogg",
    "music/orgrimmar02-moment.ogg", "music/orgrimmar-intro.ogg",
};

typedef struct {
    short* pcm;      /* interleaved stereo at PC_MUSIC_RATE */
    int frames;
} MusicBuf;

static SDL_atomic_t g_state;        /* 0 idle, 1 loading, 2 playing, 3 fading out */
static MusicBuf g_buf;
static volatile int g_pos;
static volatile int g_fade_left;
static volatile int g_fade_total = 1;
static int g_request = -1;
static SDL_Thread* g_thread;
static int g_enabled = -1;

static int music_enabled(void) {
    if (g_enabled < 0) {
        const char* e = getenv("AC_MUSIC");
        g_enabled = (e && e[0] == 'o') ? 1 : 0;
    }
    return g_enabled;
}

static short* decode_resample(const char* path, int* out_frames) {
    int ch = 0, sr = 0;
    short* raw = NULL;
    int n = stb_vorbis_decode_filename(path, &ch, &sr, &raw);
    if (n <= 0 || !raw || ch < 1 || sr < 8000) {
        free(raw);
        return NULL;
    }
    int of = (int)((long long)n * PC_MUSIC_RATE / sr);
    short* out = (short*)malloc((size_t)of * 2 * sizeof(short));
    if (!out) { free(raw); return NULL; }
    for (int i = 0; i < of; i++) {
        double src = (double)i * sr / PC_MUSIC_RATE;
        int i0 = (int)src; double f = src - i0;
        int i1 = i0 + 1 < n ? i0 + 1 : i0;
        for (int c = 0; c < 2; c++) {
            int cc = (ch >= 2) ? c : 0;
            double a = raw[i0 * ch + cc], b = raw[i1 * ch + cc];
            out[i * 2 + c] = (short)(a + (b - a) * f);
        }
    }
    free(raw);
    *out_frames = of;
    return out;
}

static int load_thread(void* data) {
    int slot = (int)(intptr_t)data;
    int frames = 0;
    short* pcm = decode_resample(k_tracks[slot % 5], &frames);
    if (!pcm) {
        printf("[MUSIC] failed to load %s\n", k_tracks[slot % 5]);
        SDL_AtomicSet(&g_state, 0);
        return 0;
    }
    short* old = g_buf.pcm;
    g_pos = 0;
    g_buf.pcm = pcm;
    g_buf.frames = frames;
    SDL_MemoryBarrierRelease();
    SDL_AtomicSet(&g_state, 2);
    printf("[MUSIC] playing %s (%d s)\n", k_tracks[slot % 5], frames / PC_MUSIC_RATE);
    free(old);
    return 0;
}

/* Called from sAdo_BgmStart / sAdo_BgmCrossfadeStart. Returns 1 when the game's own track is replaced. */
int pc_music_override_start(unsigned char id) {
    if (!music_enabled() || id < 1 || id > 24) return 0;
    int hour = id - 1;
    int slot = hour % 5;
    if (g_thread) { SDL_WaitThread(g_thread, NULL); g_thread = NULL; }
    SDL_AtomicSet(&g_state, 1);
    g_thread = SDL_CreateThread(load_thread, "MusicLoad", (void*)(intptr_t)slot);
    return 1;
}

/* Called from sAdo_BgmStop. Fades our track out; the game's own stop still runs. */
void pc_music_override_stop(void) {
    if (SDL_AtomicGet(&g_state) == 2) {
        g_fade_total = PC_MUSIC_RATE; /* one second */
        g_fade_left = g_fade_total;
        SDL_AtomicSet(&g_state, 3);
    }
}

/* Mix into an interleaved stereo S16 buffer (called on the SDL audio thread). */
void pc_music_mix(short* out, int n_samples) {
    int st = SDL_AtomicGet(&g_state);
    if ((st != 2 && st != 3) || !g_buf.pcm) return;
    SDL_MemoryBarrierAcquire();
    int frames = n_samples / 2;
    int pos = g_pos;
    for (int i = 0; i < frames; i++) {
        float gain = PC_MUSIC_VOLUME;
        if (st == 3) {
            if (g_fade_left <= 0) { SDL_AtomicSet(&g_state, 0); break; }
            gain *= (float)g_fade_left / (float)g_fade_total;
            g_fade_left--;
        }
        for (int c = 0; c < 2; c++) {
            int v = out[i * 2 + c] + (int)(g_buf.pcm[pos * 2 + c] * gain);
            out[i * 2 + c] = (short)(v > 32767 ? 32767 : (v < -32768 ? -32768 : v));
        }
        if (++pos >= g_buf.frames) pos = 0;
    }
    g_pos = pos;
    {
        static int logged = 0;
        if (!logged && pos > PC_MUSIC_RATE * 2) {
            int peak = 0;
            for (int i = 0; i < 2000; i++) { int a = abs(g_buf.pcm[(pos - 2000 + i) * 2]); if (a > peak) peak = a; }
            printf("[MUSIC] mixing, recent peak %d\n", peak);
            logged = 1;
        }
    }
}

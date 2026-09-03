/* Tape Echo 2 for Ableton Move (Schwung audio_fx module).
 *
 * The Move-facing parameter surface. Single source of truth: the DSP shell,
 * the chain_params JSON served via get_param, the ui_hierarchy, and the state
 * blob all iterate this table. The te2_knobs_* page tables in
 * tape_echo_plugin.cpp mirror it by hand — tools/check_config.py fails the
 * build if they drift.
 *
 * Order matters: the first TE2_VISIBLE_PARAM_COUNT entries are the published
 * surface. Everything after that is still settable via set_param and still
 * round-trips in state, but is deliberately NOT offered as a knob — either it
 * is a compatibility control, or it duplicates something the Move already does
 * at the mixer/chain level (output trim, panning, slot bypass).
 *
 * The DSP core and its parameter semantics are Tape Echo 2 by Dusk Audio
 * (GPL-3.0, github.com/dusk-audio/dusk-audio-plugins); see src/ported/.
 */

#ifndef TE2_PARAMS_H
#define TE2_PARAMS_H

enum Te2ParamIndex {
    /* ---- published: page 1, the echo itself ---- */
    TE2_P_MODE = 0,     /* enum 0..11 -> DSP mode 1..12 */
    TE2_P_RATE,         /* repeat rate 0..1 (0 = slow/177ms, 1 = fast/69ms) */
    TE2_P_INTENSITY,    /* feedback; self-oscillates above ~0.75 */
    TE2_P_ECHO_VOL,
    TE2_P_REVERB_VOL,   /* audible in modes 5-12 only */
    TE2_P_MIX,          /* dry/wet crossfade, 0.5 = both at unity */
    TE2_P_SYNC,         /* enum Off/On: leading head locks to host tempo */
    TE2_P_NOTE,         /* physical 1..11 Echo Rate detent (Galaxy-style) */
    /* ---- published: page 2, tape character ---- */
    TE2_P_INPUT,        /* preamp drive / saturation amount */
    TE2_P_BASS,         /* -1..1, echo path only */
    TE2_P_TREBLE,       /* -1..1, echo path only */
    TE2_P_WOW,          /* wow & flutter amount */
    TE2_P_AGE,          /* enum New/Used/Old -> 0.0/0.5/1.0 */
    TE2_P_SEND,         /* enum Off/On: program feed to tape ("dub" switch) */
    TE2_P_PINGPONG,     /* enum Off/On: alternate successive repeats L/R */
    TE2_P_WIDTH,        /* 0..100: how far the ping-pong swings (0 = centred) */
    /* ---- published: MACROS. Main's simple front page. ----
     * Each one is a real param that fans out to real params on write, so the
     * members move everywhere that reads them — the web UI included, which is
     * the point. They are ABSOLUTE and re-latch: edit a member directly and
     * the macro's own position is stale until it is next turned. That is what
     * every hardware macro does, and the alternative (inferring a position
     * back from the members) cannot be inverted when two members share one
     * knob. */
    TE2_P_TIME_MS,      /* ms. Drives RATE, or NOTE when SYNC is on. */
    TE2_P_TONE_TILT,    /* -1..1 tilt across BASS and TREBLE together */
    TE2_P_TAPE_WEAR,    /* 0..1 wear: WOW + AGE. Deliberately NOT drive. */
    /* ---- not published (see header comment) ---- */
    TE2_P_OUTPUT_VOL,   /* -20..+20 dB; left at 0.5 = unity, use the mixer */
    TE2_P_ECHO_PAN,     /* left at 0.5 = center */
    TE2_P_REVERB_PAN,   /* left at 0.5 = center */
    TE2_P_POWER,        /* left On; the chain slot does bypass */
    TE2_P_PRESET,       /* factory program launcher, still usable via set_param */
    TE2_P_DRY,          /* legacy dry level, default 1.0 */
    TE2_PARAM_COUNT,
    TE2_VISIBLE_PARAM_COUNT = TE2_P_OUTPUT_VOL
};

typedef enum { TE2_FLOAT, TE2_INT, TE2_ENUM } te2_type_t;

typedef struct {
    const char  *key;
    const char  *name;
    te2_type_t   type;
    float        min, max, def;
    const char *const *options;  /* TE2_ENUM only */
    int          n_options;
    /* Optional presentation, passed through to chain_params. Without these a
     * float renders as "0.41", which is what the raw repeat_rate knob showed
     * and which means nothing to anybody — TIME exists partly to say "400". */
    const char  *unit;           /* e.g. "ms"; null for none */
    const char  *display_format; /* printf-ish ".0f" / ".0%"; null for none */
} te2_param_t;

/* Kept short and distinct at the front: the display has room for a few
 * characters per knob, and "Head 1"/"Head 2"/"Head 3" are indistinguishable
 * once cut. R = spring reverb; digits are the active playback heads. */
static const char *const te2_opts_mode[12] = {
    "H1", "H2", "H3", "H2+3",
    "H1+R", "H2+R", "H3+R", "H12+R",
    "H23+R", "H13+R", "H123R", "Rev",
};
static const char *const te2_opts_offon[2] = { "Off", "On" };
static const char *const te2_opts_age[3]   = { "New", "Used", "Old" };
/* Order matches kFactoryPresets in the vendored TapeEchoParams.hpp. */
static const char *const te2_opts_preset[13] = {
    "Default", "Slapback Vocal", "Rockabilly Gtr", "Classic Tape",
    "Dub Throw", "Synced 1/8 Dub", "Multi-Head", "Orbital Echo",
    "Full Wash", "Ambient Trails", "Worn Tape", "Runaway Drone",
    "Spring Only",
};

/* Defaults.
 *
 * These are NOT the reference machine's power-on state, and the change is
 * separable from everything else in this branch — see the commit that makes it.
 *
 * As shipped in 1.3.3 a fresh insert was mode H1 at the slowest motor with
 * intensity 0, which is one repeat about 22 dB below the dry and no train at
 * all. Measured against it, mode H3 / repeat_rate 0.414888 (= 400 ms) /
 * intensity 0.44 / echo_volume 1.0 gives three audible repeats decaying about
 * 12 dB each: a usable echo rather than a slap you have to go and build.
 *
 * The numbers came from matching the old schwung `tapedelay` module, which
 * this engine briefly replaced — intensity 0.44 reproduces its -12.1 dB per
 * repeat and echo_volume 1.0 its wet-to-dry ratio. That module is gone as a
 * comparison point, but the resulting voicing stands on its own and the
 * derivation is at least a measured one rather than a guess.
 *
 * reverb_volume defaults non-zero so that choosing one of the +R modes is
 * audible immediately. kModeTable zeroes the reverb send in the non-R modes,
 * so this cannot colour the default H3 sound.
 *
 * tools/loadtest.cpp pins them against the legacy import path, so they cannot
 * drift from the mapping they were derived from. */
static const te2_param_t te2_params[TE2_PARAM_COUNT] = {
    { "mode",           "Mode",          TE2_ENUM,  0,  11, 2,    te2_opts_mode,   12 },
    { "repeat_rate",    "Rate",          TE2_FLOAT, 0,   1, 0.414888f, 0, 0 },
    { "intensity",      "Fbk",           TE2_FLOAT, 0,   1, 0.44f, 0, 0 },
    { "echo_volume",    "Echo",          TE2_FLOAT, 0,   1, 1.0f, 0, 0 },
    { "reverb_volume",  "Verb",          TE2_FLOAT, 0,   1, 0.35f, 0, 0 },
    { "mix",            "Mix",           TE2_FLOAT, 0,   1, 0.5f, 0, 0 },
    { "tempo_sync",     "Sync",          TE2_ENUM,  0,   1, 0,    te2_opts_offon,  2 },
    { "echo_rate_note", "Div",           TE2_INT,   1,  11, 5,    0, 0 },
    { "input_volume",   "Drive",         TE2_FLOAT, 0,   1, 0.5f, 0, 0 },
    { "bass",           "Bass",          TE2_FLOAT, -1,  1, 0.0f, 0, 0 },
    { "treble",         "Treble",        TE2_FLOAT, -1,  1, 0.0f, 0, 0 },
    { "wow_flutter",    "W&F",           TE2_FLOAT, 0,   1, 0.0f, 0, 0 },
    { "tape_age",       "Age",           TE2_ENUM,  0,   2, 1,    te2_opts_age,    3 },
    { "input_send",     "Arm",           TE2_ENUM,  0,   1, 1,    te2_opts_offon,  2 },
    { "ping_pong",      "Pong",          TE2_ENUM,  0,   1, 0,    te2_opts_offon,  2 },
    { "stereo_width",   "Width",         TE2_INT,   0, 100, 0,    0, 0 },
    /* macros — see the enum. TIME's default is TapeDelay's 400 ms, which is
     * what the RATE/MODE defaults below already encode; the two agree and
     * tools/loadtest.cpp checks that they do. */
    /* NOT "time"/"tone": both are taken by the TapeDelay one-key-at-a-time
     * aliases in te2_set_param, which run before the table lookup — and the
     * ranges differ (legacy tone is 0..1, this tilt is -1..1), so sharing a
     * key would silently reinterpret an old module's values. */
    { "time_ms",        "Time",          TE2_FLOAT, 69, 490, 400.0f, 0, 0, "ms", ".0f" },
    { "tone_tilt",      "Tone",          TE2_FLOAT, -1,  1, 0.0f, 0, 0 },
    { "tape_wear",      "Tape",          TE2_FLOAT, 0,   1, 0.25f, 0, 0 },
    /* unpublished */
    { "output_volume",  "Output Volume", TE2_FLOAT, 0,   1, 0.5f, 0, 0 },
    { "echo_pan",       "Echo Pan",      TE2_FLOAT, 0,   1, 0.5f, 0, 0 },
    { "reverb_pan",     "Reverb Pan",    TE2_FLOAT, 0,   1, 0.5f, 0, 0 },
    { "power",          "Power",         TE2_ENUM,  0,   1, 1,    te2_opts_offon,  2 },
    { "preset",         "Preset",        TE2_ENUM,  0,  12, 0,    te2_opts_preset, 13 },
    { "dry_level",      "Dry Level",     TE2_FLOAT, 0,   1, 1.0f, 0, 0 },
};

#endif /* TE2_PARAMS_H */

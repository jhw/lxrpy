"""
LXR-02 Kit/Sound file handling.

Kit files (.SND) are 255 bytes containing:
- 8-byte name
- 247 bytes of parameter data for 6 voices plus kit-level FX/morph settings

The parameter bytes are the firmware's sound parameter array in enum order
(Parameters.h in the LXR firmware), so file offset = 8 + firmware parameter
number. The same parameter number is used by step automation and, offset by
the modulation target table, by LFO and velocity modulation destinations.

Each voice has different synthesis models:
- V1-V3: Standard (Osc + FM + Mod)
- V4: Snare (Standard + Noise, no FM)
- V5-V6: HiHat (Alternate FM model with paired oscillators)
"""
import os
import sys

from typing import Optional, Tuple

from .enums import (
    Waveform, FmMode, ClickWave, FilterType,
    LfoWave, LfoSync, LfoRetrig, OutputRouting,
    FxType, FxDistType, FxRatio, FxReverbType, FxDelayType
)


KIT_SIZE = 255
KIT_NAME_SIZE = 8


# Parameter offset mappings by voice (V1-V6, 0-indexed)
# None means parameter doesn't apply to that voice
PARAM_OFFSETS = {
    # Osc screen
    'osc_wav': [9, 10, 11, 12, 14, 15],  # skips 13
    'osc_coa': [16, 18, 20, 22, 24, 26],
    'osc_fin': [17, 19, 21, 23, 25, 27],
    'osc_pwm': [236, 237, 238, 239, 240, 241],
    'osc_noi': [None, None, None, 35, None, None],  # V4 only
    'osc_mix': [None, None, None, 36, None, None],  # V4 only
    # AEG screen
    'aeg_atk': [57, 59, 61, 63, 65, 67],
    'aeg_dec': [58, 60, 62, 64, 66, 68],
    'aeg_slp': [70, 71, 72, 73, 74, 75],
    'aeg_rpt': [None, None, None, 76, 77, None],  # V4-V5 only
    'aeg_dec_open': [None, None, None, None, None, 69],  # V6 only (open hi-hat, track 7)
    # FM screen (V1-V3)
    'fm_wav': [28, 29, 30, None, 31, 33],
    'fm_amt': [90, 92, 94, None, None, None],  # V1-V3 only
    'fm_frq': [91, 93, 95, None, None, None],  # V1-V3 only
    'fm_mod': [142, 143, 144, None, None, None],  # V1-V3 only
    # FM screen (V5-V6 alternate model)
    'fm_wav2': [None, None, None, None, 32, 34],  # V5-V6 only
    'fm_f1': [None, None, None, None, 37, 41],  # V5-V6 only
    'fm_f2': [None, None, None, None, 38, 42],  # V5-V6 only
    'fm_g1': [None, None, None, None, 39, 43],  # V5-V6 only
    'fm_g2': [None, None, None, None, 40, 44],  # V5-V6 only
    # Mod screen
    'mod_dec': [78, 79, 80, 81, None, None],  # V1-V4 only
    'mod_mod': [82, 83, 84, 85, None, None],  # V1-V4 only
    'mod_slp': [86, 87, 88, 89, None, None],  # V1-V4 only
    'mod_vol': [145, 146, 147, 148, 149, 150],
    'mod_amt': [151, 152, 153, 154, 155, 156],
    'mod_dst': [157, 158, 159, 160, 161, 162],
    # Click screen
    'click_vol': [205, 206, 207, 208, 209, 210],
    'click_wav': [211, 212, 213, 214, 215, 216],
    'click_frq': [217, 218, 219, 220, 221, 222],
    # Filter screen
    'flt_frq': [45, 46, 47, 48, 49, 50],
    'flt_res': [51, 52, 53, 54, 55, 56],
    'flt_drv': [136, 137, 138, 139, 140, 141],
    'flt_typ': [199, 200, 201, 202, 203, 204],
    # LFO screen
    'lfo_frq': [123, 124, 125, 126, 127, 128],
    'lfo_mod': [129, 130, 131, 132, 133, 134],
    'lfo_wav': [163, 164, 165, 166, 167, 168],
    'lfo_voi': [169, 170, 171, 172, 173, 174],
    'lfo_dst': [175, 176, 177, 178, 179, 180],
    'lfo_rtg': [181, 182, 183, 184, 185, 186],
    'lfo_snc': [187, 188, 189, 190, 191, 192],
    'lfo_ofs': [193, 194, 195, 196, 197, 198],
    # Mix screen
    'mix_vol': [96, 97, 98, 99, 100, 101],
    'mix_pan': [102, 103, 104, 107, 108, 109],  # skips 105-106
    'mix_drv': [110, 111, 112, 113, 114, 115],
    'mix_srt': [116, 117, 118, 119, 120, 121],
    'mix_out': [223, 224, 225, 226, 227, 228],
}

# Parameters with center offset (stored = display + center)
CENTERED_PARAMS = {
    'osc_coa': 60,  # -60 to +67
    'osc_fin': 63,  # -63 to +64
    'fm_frq': 60,   # -60 to +67
    'fm_f1': 60,    # -60 to +67
    'fm_f2': 60,    # -60 to +67
    'mix_pan': 63,  # -63 to +64
}

# Parameters that use enums (for type checking)
ENUM_PARAMS = {
    'osc_wav': Waveform,
    'fm_wav': Waveform,
    'fm_wav2': Waveform,
    'fm_mod': FmMode,
    'click_wav': ClickWave,
    'flt_typ': FilterType,
    'lfo_wav': LfoWave,
    'lfo_snc': LfoSync,
    'lfo_rtg': LfoRetrig,
    'mix_out': OutputRouting,
}

# Kit-level parameter offsets (not per voice)
KIT_PARAM_OFFSETS = {
    'srt_all': 122,    # Global sample rate reduction (all voices)
    # FX screen
    'fx_typ': 242,
    'fx_out': 243,     # FX bus output routing (ST1-R2, no FX)
    'fx_dw': 244,      # Dry/wet (0-100)
    'fx_dis': 245,     # Drive distortion type
    'fx_p1': 246,      # P1-P4 meaning depends on fx_typ
    'fx_p2': 247,
    'fx_p3': 248,
    'fx_p4': 249,
    'fx_rat': 250,     # Compressor ratio
    'fx_wav': 251,     # Ring modulator waveform
    'fx_rev': 252,
    'fx_del': 253,
    # Morph
    'morph_kit': 254,  # Kit index used as the morph destination
}

KIT_ENUM_PARAMS = {
    'fx_typ': FxType,
    'fx_out': OutputRouting,
    'fx_dis': FxDistType,
    'fx_rat': FxRatio,
    'fx_wav': Waveform,
    'fx_rev': FxReverbType,
    'fx_del': FxDelayType,
}

# Display value ranges where they differ from the default 0-127
PARAM_RANGES = {
    'mod_vol': (0, 1),
    'mod_dst': (0, 228),  # Index into MOD_TARGETS
    'lfo_dst': (0, 228),
    'lfo_voi': (1, 6),
    'fx_dw': (0, 100),
    'fx_out': (0, 5),    # OutputRouting without FX
}

# Modulation target table (modTargets[] in the firmware's Cc2Text.c).
# lfo_dst and mod_dst store an index into this table; each entry is a
# firmware parameter number (file offset - 8). Index 0 is off and index 1
# is the kit-level sample rate; the rest are grouped per voice, see
# MOD_TARGET_VOICE_RANGES.
MOD_TARGETS = [
      0, 114,   8,   9,   1, 228,  49,  50,  62,  70,  78,  74, 149, 143, 137,  82,
     83,  20, 134, 203, 197, 209,  37,  43, 191, 128, 115, 179, 121, 155, 173, 185,
     88,  94, 108, 102, 238, 239, 240, 241,  10,  11,   2, 229,  51,  52,  63,  71,
     79,  75, 150, 144, 138,  84,  85,  21, 135, 204, 198, 210,  38,  44, 192, 129,
    116, 180, 122, 156, 174, 186,  89,  95, 109, 103, 238, 239, 240, 241,  12,  13,
      3, 230,  53,  54,  64,  72,  80,  76, 151, 145, 139,  86,  87,  22, 136, 205,
    199, 211,  39,  45, 193, 130, 117, 181, 123, 157, 175, 187,  90,  96, 110, 104,
    238, 239, 240, 241,  14,  15,  27,  28,   4, 231,  55,  56,  68,  65,  73,  81,
     77, 152, 146, 140, 206, 200, 212,  40,  46, 194, 131, 118, 182, 124, 158, 176,
    188,  91,  99, 111, 105, 238, 239, 240, 241,  16,  17,   6, 232,  57,  58,  69,
     66, 153, 147, 141,  29,  30,  31,  32,  23,  24, 207, 201, 213,  41,  47, 195,
    132, 119, 183, 125, 159, 177, 189,  92, 100, 112, 106, 238, 239, 240, 241,  18,
     19,   7, 233,  59,  60,  61,  67, 154, 148, 142,  33,  34,  35,  36,  25,  26,
    208, 202, 214,  42,  48, 196, 133, 120, 184, 126, 160, 178, 190,  93, 101, 113,
    107, 238, 239, 240, 241,
]

# Inclusive index ranges into MOD_TARGETS for each voice (V1-V6)
MOD_TARGET_VOICE_RANGES = [(2, 39), (40, 77), (78, 115), (116, 152), (153, 190), (191, 228)]

# Step automation slot value meaning "no automation"
NO_AUTOMATION = 0xFF


def param_number(param: str, voice: int = None) -> int:
    """
    Get the firmware parameter number for a named parameter.

    This is file offset - 8, and the number Step.get/set_automation use
    (the slot byte itself is encoded, see lxr.pattern).

    Args:
        param: Parameter name, either per-voice (e.g. 'flt_frq') or
               kit-level (e.g. 'fx_dw').
        voice: Voice number (1-6). Required for per-voice parameters.

    Returns:
        Firmware parameter number.
    """
    if param in KIT_PARAM_OFFSETS:
        return KIT_PARAM_OFFSETS[param] - KIT_NAME_SIZE
    offsets = PARAM_OFFSETS.get(param)
    if offsets is None:
        raise ValueError(f"Unknown parameter: {param}")
    if voice is None or not 1 <= voice <= 6:
        raise ValueError(f"Voice must be 1-6 for {param}, got {voice}")
    offset = offsets[voice - 1]
    if offset is None:
        raise ValueError(f"Parameter {param} not available for voice {voice}")
    return offset - KIT_NAME_SIZE


def param_from_number(number: int) -> Optional[Tuple[str, Optional[int]]]:
    """
    Look up a firmware parameter number.

    Args:
        number: Firmware parameter number (file offset - 8).

    Returns:
        (param, voice) for per-voice parameters, (param, None) for kit-level
        parameters, or None if the number isn't a mapped parameter.
    """
    offset = number + KIT_NAME_SIZE
    for param, offsets in PARAM_OFFSETS.items():
        if offset in offsets:
            return param, offsets.index(offset) + 1
    for param, kit_offset in KIT_PARAM_OFFSETS.items():
        if offset == kit_offset:
            return param, None
    return None


def mod_target(index: int) -> Optional[Tuple[str, Optional[int]]]:
    """
    Decode a modulation target index (lfo_dst, mod_dst).

    Args:
        index: Index into the modulation target table (0-228).

    Returns:
        (param, voice) as for param_from_number, or None for 0 (off).
    """
    if not 0 <= index < len(MOD_TARGETS):
        raise ValueError(f"Mod target must be 0-{len(MOD_TARGETS) - 1}, got {index}")
    if index == 0:
        return None
    return param_from_number(MOD_TARGETS[index])


def mod_target_index(param: str, voice: int = None) -> int:
    """
    Encode a modulation target for lfo_dst or mod_dst.

    Args:
        param: Parameter name, per-voice or kit-level.
        voice: Target voice (1-6). Required for per-voice parameters; for
               kit-level FX parameters selects which voice's entry to use
               (defaults to the global entry for srt_all, V1 otherwise).

    Returns:
        Index into the modulation target table.
    """
    if param == 'srt_all' and voice is None:
        return 1
    number = param_number(param, voice)
    start, end = MOD_TARGET_VOICE_RANGES[(voice or 1) - 1]
    for i in range(start, end + 1):
        if MOD_TARGETS[i] == number:
            return i
    raise ValueError(f"{param} is not a modulation target for voice {voice}")


class Voice:
    """
    Represents a single voice in an LXR-02 kit.

    Provides property-based access to all voice parameters. Parameters are
    stored/retrieved with appropriate conversions (centered values, enums).

    Voice types:
    - V1-V3: Standard synthesis (Osc + FM + Mod)
    - V4: Snare (has osc.noi, osc.mix; no FM)
    - V5-V6: HiHat (alternate FM with f1, f2, g1, g2)
    """

    def __init__(self, kit: 'Kit', voice_num: int):
        """
        Initialize a voice reference.

        Args:
            kit: Parent Kit object containing the binary data
            voice_num: Voice number (1-6)
        """
        if not 1 <= voice_num <= 6:
            raise ValueError(f"Voice number must be 1-6, got {voice_num}")
        self._kit = kit
        self._voice_num = voice_num
        self._voice_idx = voice_num - 1

    @property
    def voice_num(self) -> int:
        """Voice number (1-6)."""
        return self._voice_num

    def _get_offset(self, param: str) -> int:
        """Get byte offset for a parameter on this voice."""
        offsets = PARAM_OFFSETS.get(param)
        if offsets is None:
            raise ValueError(f"Unknown parameter: {param}")
        offset = offsets[self._voice_idx]
        if offset is None:
            raise ValueError(f"Parameter {param} not available for voice {self._voice_num}")
        return offset

    def _get_raw(self, param: str) -> int:
        """Get raw byte value for a parameter."""
        offset = self._get_offset(param)
        return self._kit._data[offset]

    def _set_raw(self, param: str, value: int):
        """Set raw byte value for a parameter."""
        offset = self._get_offset(param)
        if not 0 <= value <= 255:
            raise ValueError(f"Raw value must be 0-255, got {value}")
        self._kit._data[offset] = value

    def _get_value(self, param: str) -> int:
        """Get display value for a parameter (with center offset applied)."""
        raw = self._get_raw(param)
        center = CENTERED_PARAMS.get(param, 0)
        return raw - center

    def _set_value(self, param: str, value: int):
        """Set display value for a parameter (with center offset applied)."""
        center = CENTERED_PARAMS.get(param, 0)
        low, high = PARAM_RANGES.get(param, (0 - center, 127 - center))
        value = max(low, min(high, value))
        self._set_raw(param, value + center)

    def _get_enum(self, param: str):
        """Get enum value for a parameter."""
        enum_class = ENUM_PARAMS.get(param)
        if enum_class is None:
            raise ValueError(f"Parameter {param} is not an enum type")
        raw = self._get_raw(param)
        try:
            return enum_class(raw)
        except ValueError:
            return raw  # Return raw value if not a valid enum

    def _set_enum(self, param: str, value):
        """Set enum value for a parameter."""
        enum_class = ENUM_PARAMS.get(param)
        if enum_class is None:
            raise ValueError(f"Parameter {param} is not an enum type")
        if isinstance(value, enum_class):
            self._set_raw(param, value.value)
        elif isinstance(value, int):
            self._set_raw(param, value)
        else:
            raise ValueError(f"Expected {enum_class.__name__} or int, got {type(value)}")

    def has_param(self, param: str) -> bool:
        """Check if this voice has a particular parameter."""
        offsets = PARAM_OFFSETS.get(param)
        if offsets is None:
            return False
        return offsets[self._voice_idx] is not None

    # ===== OSC Screen =====

    @property
    def osc_wav(self) -> Waveform:
        """Oscillator waveform."""
        return self._get_enum('osc_wav')

    @osc_wav.setter
    def osc_wav(self, value):
        self._set_enum('osc_wav', value)

    @property
    def osc_coa(self) -> int:
        """Oscillator coarse tune (-60 to +67)."""
        return self._get_value('osc_coa')

    @osc_coa.setter
    def osc_coa(self, value: int):
        self._set_value('osc_coa', value)

    @property
    def osc_fin(self) -> int:
        """Oscillator fine tune (-63 to +64)."""
        return self._get_value('osc_fin')

    @osc_fin.setter
    def osc_fin(self, value: int):
        self._set_value('osc_fin', value)

    @property
    def osc_pwm(self) -> int:
        """Oscillator pulse width (0-127)."""
        return self._get_value('osc_pwm')

    @osc_pwm.setter
    def osc_pwm(self, value: int):
        self._set_value('osc_pwm', value)

    @property
    def osc_noi(self) -> int:
        """Oscillator noise amount (0-127). V4 only."""
        return self._get_value('osc_noi')

    @osc_noi.setter
    def osc_noi(self, value: int):
        self._set_value('osc_noi', value)

    @property
    def osc_mix(self) -> int:
        """Oscillator/noise mix (0-127). V4 only."""
        return self._get_value('osc_mix')

    @osc_mix.setter
    def osc_mix(self, value: int):
        self._set_value('osc_mix', value)

    # ===== AEG Screen =====

    @property
    def aeg_atk(self) -> int:
        """Amplitude envelope attack (0-127)."""
        return self._get_value('aeg_atk')

    @aeg_atk.setter
    def aeg_atk(self, value: int):
        self._set_value('aeg_atk', value)

    @property
    def aeg_dec(self) -> int:
        """Amplitude envelope decay (0-127). Closed hi-hat decay on V6."""
        return self._get_value('aeg_dec')

    @aeg_dec.setter
    def aeg_dec(self, value: int):
        self._set_value('aeg_dec', value)

    @property
    def aeg_slp(self) -> int:
        """Amplitude envelope slope (0-127)."""
        return self._get_value('aeg_slp')

    @aeg_slp.setter
    def aeg_slp(self, value: int):
        self._set_value('aeg_slp', value)

    @property
    def aeg_dec_open(self) -> int:
        """Open hi-hat decay (0-127). V6 only; used when track 7 triggers V6."""
        return self._get_value('aeg_dec_open')

    @aeg_dec_open.setter
    def aeg_dec_open(self, value: int):
        self._set_value('aeg_dec_open', value)

    @property
    def aeg_rpt(self) -> int:
        """Amplitude envelope repeat (0-127). V4-V5 only."""
        return self._get_value('aeg_rpt')

    @aeg_rpt.setter
    def aeg_rpt(self, value: int):
        self._set_value('aeg_rpt', value)

    # ===== FM Screen (V1-V3) =====

    @property
    def fm_wav(self) -> Waveform:
        """FM modulator waveform."""
        return self._get_enum('fm_wav')

    @fm_wav.setter
    def fm_wav(self, value):
        self._set_enum('fm_wav', value)

    @property
    def fm_amt(self) -> int:
        """FM amount (0-127). V1-V3 only."""
        return self._get_value('fm_amt')

    @fm_amt.setter
    def fm_amt(self, value: int):
        self._set_value('fm_amt', value)

    @property
    def fm_frq(self) -> int:
        """FM frequency (-60 to +67). V1-V3 only."""
        return self._get_value('fm_frq')

    @fm_frq.setter
    def fm_frq(self, value: int):
        self._set_value('fm_frq', value)

    @property
    def fm_mod(self) -> FmMode:
        """FM mode. V1-V3 only."""
        return self._get_enum('fm_mod')

    @fm_mod.setter
    def fm_mod(self, value):
        self._set_enum('fm_mod', value)

    # ===== FM Screen (V5-V6 alternate model) =====

    @property
    def fm_wav2(self) -> Waveform:
        """FM waveform 2 (V5-V6 only)."""
        return self._get_enum('fm_wav2')

    @fm_wav2.setter
    def fm_wav2(self, value):
        self._set_enum('fm_wav2', value)

    @property
    def fm_f1(self) -> int:
        """FM frequency 1 (-60 to +67). V5-V6 only."""
        return self._get_value('fm_f1')

    @fm_f1.setter
    def fm_f1(self, value: int):
        self._set_value('fm_f1', value)

    @property
    def fm_f2(self) -> int:
        """FM frequency 2 (-60 to +67). V5-V6 only."""
        return self._get_value('fm_f2')

    @fm_f2.setter
    def fm_f2(self, value: int):
        self._set_value('fm_f2', value)

    @property
    def fm_g1(self) -> int:
        """FM gain 1 (0-127). V5-V6 only."""
        return self._get_value('fm_g1')

    @fm_g1.setter
    def fm_g1(self, value: int):
        self._set_value('fm_g1', value)

    @property
    def fm_g2(self) -> int:
        """FM gain 2 (0-127). V5-V6 only."""
        return self._get_value('fm_g2')

    @fm_g2.setter
    def fm_g2(self, value: int):
        self._set_value('fm_g2', value)

    # ===== Mod Screen =====

    @property
    def mod_dec(self) -> int:
        """Modulator decay (0-127). V1-V4 only."""
        return self._get_value('mod_dec')

    @mod_dec.setter
    def mod_dec(self, value: int):
        self._set_value('mod_dec', value)

    @property
    def mod_mod(self) -> int:
        """Modulation amount (0-127). V1-V4 only."""
        return self._get_value('mod_mod')

    @mod_mod.setter
    def mod_mod(self, value: int):
        self._set_value('mod_mod', value)

    @property
    def mod_slp(self) -> int:
        """Modulator slope (0-127). V1-V4 only."""
        return self._get_value('mod_slp')

    @mod_slp.setter
    def mod_slp(self, value: int):
        self._set_value('mod_slp', value)

    @property
    def mod_vol(self) -> int:
        """Velocity modulates volume, on/off (0-1)."""
        return self._get_value('mod_vol')

    @mod_vol.setter
    def mod_vol(self, value: int):
        self._set_value('mod_vol', value)

    @property
    def mod_amt(self) -> int:
        """Velocity modulation amount (0-127)."""
        return self._get_value('mod_amt')

    @mod_amt.setter
    def mod_amt(self, value: int):
        self._set_value('mod_amt', value)

    @property
    def mod_dst(self) -> int:
        """Velocity modulation destination (0=off). Index into MOD_TARGETS, see mod_target()."""
        return self._get_value('mod_dst')

    @mod_dst.setter
    def mod_dst(self, value: int):
        self._set_value('mod_dst', value)

    # ===== Click Screen =====

    @property
    def click_vol(self) -> int:
        """Click volume (0-127)."""
        return self._get_value('click_vol')

    @click_vol.setter
    def click_vol(self, value: int):
        self._set_value('click_vol', value)

    @property
    def click_wav(self) -> ClickWave:
        """Click waveform."""
        return self._get_enum('click_wav')

    @click_wav.setter
    def click_wav(self, value):
        self._set_enum('click_wav', value)

    @property
    def click_frq(self) -> int:
        """Click frequency (0-127)."""
        return self._get_value('click_frq')

    @click_frq.setter
    def click_frq(self, value: int):
        self._set_value('click_frq', value)

    # ===== Filter Screen =====

    @property
    def flt_frq(self) -> int:
        """Filter frequency (0-127)."""
        return self._get_value('flt_frq')

    @flt_frq.setter
    def flt_frq(self, value: int):
        self._set_value('flt_frq', value)

    @property
    def flt_res(self) -> int:
        """Filter resonance (0-127)."""
        return self._get_value('flt_res')

    @flt_res.setter
    def flt_res(self, value: int):
        self._set_value('flt_res', value)

    @property
    def flt_drv(self) -> int:
        """Filter drive (0-127)."""
        return self._get_value('flt_drv')

    @flt_drv.setter
    def flt_drv(self, value: int):
        self._set_value('flt_drv', value)

    @property
    def flt_typ(self) -> FilterType:
        """Filter type."""
        return self._get_enum('flt_typ')

    @flt_typ.setter
    def flt_typ(self, value):
        self._set_enum('flt_typ', value)

    # ===== LFO Screen =====

    @property
    def lfo_frq(self) -> int:
        """LFO frequency (0-127)."""
        return self._get_value('lfo_frq')

    @lfo_frq.setter
    def lfo_frq(self, value: int):
        self._set_value('lfo_frq', value)

    @property
    def lfo_mod(self) -> int:
        """LFO modulation amount (0-127)."""
        return self._get_value('lfo_mod')

    @lfo_mod.setter
    def lfo_mod(self, value: int):
        self._set_value('lfo_mod', value)

    @property
    def lfo_wav(self) -> LfoWave:
        """LFO waveform."""
        return self._get_enum('lfo_wav')

    @lfo_wav.setter
    def lfo_wav(self, value):
        self._set_enum('lfo_wav', value)

    @property
    def lfo_voi(self) -> int:
        """LFO target voice (1-6)."""
        return self._get_value('lfo_voi')

    @lfo_voi.setter
    def lfo_voi(self, value: int):
        self._set_value('lfo_voi', value)

    @property
    def lfo_dst(self) -> int:
        """LFO destination (0=off). Index into MOD_TARGETS, see mod_target()."""
        return self._get_value('lfo_dst')

    @lfo_dst.setter
    def lfo_dst(self, value: int):
        self._set_value('lfo_dst', value)

    @property
    def lfo_rtg(self) -> LfoRetrig:
        """LFO retrigger source."""
        return self._get_enum('lfo_rtg')

    @lfo_rtg.setter
    def lfo_rtg(self, value):
        self._set_enum('lfo_rtg', value)

    @property
    def lfo_snc(self) -> LfoSync:
        """LFO sync division."""
        return self._get_enum('lfo_snc')

    @lfo_snc.setter
    def lfo_snc(self, value):
        self._set_enum('lfo_snc', value)

    @property
    def lfo_ofs(self) -> int:
        """LFO offset (0-127)."""
        return self._get_value('lfo_ofs')

    @lfo_ofs.setter
    def lfo_ofs(self, value: int):
        self._set_value('lfo_ofs', value)

    # ===== Mix Screen =====

    @property
    def mix_vol(self) -> int:
        """Mix volume (0-127)."""
        return self._get_value('mix_vol')

    @mix_vol.setter
    def mix_vol(self, value: int):
        self._set_value('mix_vol', value)

    @property
    def mix_pan(self) -> int:
        """Mix pan (-63 to +64)."""
        return self._get_value('mix_pan')

    @mix_pan.setter
    def mix_pan(self, value: int):
        self._set_value('mix_pan', value)

    @property
    def mix_drv(self) -> int:
        """Mix drive (0-127)."""
        return self._get_value('mix_drv')

    @mix_drv.setter
    def mix_drv(self, value: int):
        self._set_value('mix_drv', value)

    @property
    def mix_srt(self) -> int:
        """Sample rate reduction (0-127)."""
        return self._get_value('mix_srt')

    @mix_srt.setter
    def mix_srt(self, value: int):
        self._set_value('mix_srt', value)

    @property
    def mix_out(self) -> OutputRouting:
        """Mix output routing."""
        return self._get_enum('mix_out')

    @mix_out.setter
    def mix_out(self, value):
        self._set_enum('mix_out', value)

    def to_dict(self) -> dict:
        """Export voice parameters to a dictionary."""
        result = {'voice_num': self._voice_num}
        for param in PARAM_OFFSETS:
            if self.has_param(param):
                if param in ENUM_PARAMS:
                    val = self._get_enum(param)
                    result[param] = val.name if hasattr(val, 'name') else val
                else:
                    result[param] = self._get_value(param)
        return result


class Kit:
    """
    Represents an LXR-02 kit/sound file (.SND).

    Kit files are 255 bytes containing synthesis parameters for 6 voices.
    Always initialize from a template or existing file to preserve unmapped bytes.

    Example:
        # Load from file
        kit = Kit.from_file('my_kit.SND')

        # Initialize from template
        kit = Kit.init()

        # Access voices
        v1 = kit.voice(1)
        v1.osc_wav = Waveform.SAW
        v1.mix_vol = 100

        # Save
        kit.save('new_kit.SND')
    """

    def __init__(self, data: bytes = None):
        """
        Initialize a Kit from binary data.

        Args:
            data: Raw 255-byte kit data. If None, must use init() or from_file().
        """
        if data is not None:
            if len(data) != KIT_SIZE:
                raise ValueError(f"Kit data must be {KIT_SIZE} bytes, got {len(data)}")
            self._data = bytearray(data)
        else:
            self._data = None
        self._voices = {}

    @classmethod
    def init(cls, template_name: str = None) -> 'Kit':
        """
        Initialize a new Kit from a template.

        Args:
            template_name: Optional template name (without extension).
                          If None, uses default TEMPLATE.SND.

        Returns:
            New Kit instance.
        """
        template_filename = f"{template_name}.SND" if template_name else "TEMPLATE.SND"
        template_path = cls._find_template(template_filename)
        if template_path is None:
            raise FileNotFoundError(f"Template not found: {template_filename}")
        return cls.from_file(template_path)

    @classmethod
    def _find_template(cls, filename: str) -> str:
        """Find a template file, searching multiple locations."""
        # Strategy 1: Try importlib.resources
        try:
            import importlib.resources
            if hasattr(importlib.resources, 'files'):
                # Python 3.9+
                files = importlib.resources.files('lxr.templates')
                template_path = files.joinpath(filename)
                if template_path.is_file():
                    return str(template_path)
            else:
                # Python 3.7-3.8
                with importlib.resources.path('lxr.templates', filename) as p:
                    if p.exists():
                        return str(p)
        except (ImportError, ModuleNotFoundError, FileNotFoundError, TypeError):
            pass

        # Strategy 2: Search sys.path
        for path in sys.path:
            potential_path = os.path.join(path, 'lxr', 'templates', filename)
            if os.path.exists(potential_path):
                return potential_path

        # Strategy 3: Relative to module
        module_path = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(module_path, 'templates', filename)
        if os.path.exists(template_path):
            return template_path

        return None

    @classmethod
    def from_file(cls, filename: str) -> 'Kit':
        """
        Load a Kit from a file.

        Args:
            filename: Path to .SND file.

        Returns:
            Kit instance.
        """
        with open(filename, 'rb') as f:
            data = f.read()
        return cls(data)

    def save(self, filename: str):
        """
        Save the Kit to a file.

        Args:
            filename: Path to save .SND file.
        """
        if self._data is None:
            raise ValueError("Kit not initialized")
        with open(filename, 'wb') as f:
            f.write(self._data)

    def to_bytes(self) -> bytes:
        """Return the raw kit data as bytes."""
        if self._data is None:
            raise ValueError("Kit not initialized")
        return bytes(self._data)

    def clone(self) -> 'Kit':
        """Create a deep copy of this Kit."""
        if self._data is None:
            raise ValueError("Kit not initialized")
        return Kit(bytes(self._data))

    @property
    def name(self) -> str:
        """Kit name (up to 8 characters)."""
        if self._data is None:
            raise ValueError("Kit not initialized")
        return self._data[0:KIT_NAME_SIZE].decode('ascii', errors='replace').rstrip('\x00 ')

    @name.setter
    def name(self, value: str):
        if self._data is None:
            raise ValueError("Kit not initialized")
        # Truncate and pad to 8 bytes
        name_bytes = value[:KIT_NAME_SIZE].encode('ascii', errors='replace')
        name_bytes = name_bytes.ljust(KIT_NAME_SIZE, b'\x00')
        self._data[0:KIT_NAME_SIZE] = name_bytes

    def _get_kit_param(self, param: str):
        """Get a kit-level parameter (enum where applicable)."""
        if self._data is None:
            raise ValueError("Kit not initialized")
        raw = self._data[KIT_PARAM_OFFSETS[param]]
        enum_class = KIT_ENUM_PARAMS.get(param)
        if enum_class is not None:
            try:
                return enum_class(raw)
            except ValueError:
                return raw
        return raw

    def _set_kit_param(self, param: str, value):
        """Set a kit-level parameter (enum or int, clamped to its range)."""
        if self._data is None:
            raise ValueError("Kit not initialized")
        enum_class = KIT_ENUM_PARAMS.get(param)
        if enum_class is not None and not isinstance(value, int):
            raise ValueError(f"Expected {enum_class.__name__} or int, got {type(value)}")
        if param == 'morph_kit':
            low, high = 0, 63
        else:
            low, high = PARAM_RANGES.get(param, (0, 127))
        self._data[KIT_PARAM_OFFSETS[param]] = max(low, min(high, int(value)))

    # ===== Kit-level (FX / morph) =====

    @property
    def srt_all(self) -> int:
        """Global sample rate reduction applied to all voices (0-127)."""
        return self._get_kit_param('srt_all')

    @srt_all.setter
    def srt_all(self, value):
        self._set_kit_param('srt_all', value)

    @property
    def fx_typ(self) -> FxType:
        """FX bus processor type."""
        return self._get_kit_param('fx_typ')

    @fx_typ.setter
    def fx_typ(self, value):
        self._set_kit_param('fx_typ', value)

    @property
    def fx_out(self) -> OutputRouting:
        """FX bus output routing (ST1-R2; FX is not valid here)."""
        return self._get_kit_param('fx_out')

    @fx_out.setter
    def fx_out(self, value):
        self._set_kit_param('fx_out', value)

    @property
    def fx_dw(self) -> int:
        """FX dry/wet mix (0-100)."""
        return self._get_kit_param('fx_dw')

    @fx_dw.setter
    def fx_dw(self, value):
        self._set_kit_param('fx_dw', value)

    @property
    def fx_dis(self) -> FxDistType:
        """FX drive distortion type."""
        return self._get_kit_param('fx_dis')

    @fx_dis.setter
    def fx_dis(self, value):
        self._set_kit_param('fx_dis', value)

    @property
    def fx_p1(self) -> int:
        """FX parameter 1 (0-127). Meaning depends on fx_typ."""
        return self._get_kit_param('fx_p1')

    @fx_p1.setter
    def fx_p1(self, value):
        self._set_kit_param('fx_p1', value)

    @property
    def fx_p2(self) -> int:
        """FX parameter 2 (0-127). Meaning depends on fx_typ."""
        return self._get_kit_param('fx_p2')

    @fx_p2.setter
    def fx_p2(self, value):
        self._set_kit_param('fx_p2', value)

    @property
    def fx_p3(self) -> int:
        """FX parameter 3 (0-127). Meaning depends on fx_typ."""
        return self._get_kit_param('fx_p3')

    @fx_p3.setter
    def fx_p3(self, value):
        self._set_kit_param('fx_p3', value)

    @property
    def fx_p4(self) -> int:
        """FX parameter 4 (0-127). Meaning depends on fx_typ."""
        return self._get_kit_param('fx_p4')

    @fx_p4.setter
    def fx_p4(self, value):
        self._set_kit_param('fx_p4', value)

    @property
    def fx_rat(self) -> FxRatio:
        """FX compressor ratio."""
        return self._get_kit_param('fx_rat')

    @fx_rat.setter
    def fx_rat(self, value):
        self._set_kit_param('fx_rat', value)

    @property
    def fx_wav(self) -> Waveform:
        """FX ring modulator waveform."""
        return self._get_kit_param('fx_wav')

    @fx_wav.setter
    def fx_wav(self, value):
        self._set_kit_param('fx_wav', value)

    @property
    def fx_rev(self) -> FxReverbType:
        """FX reverb type."""
        return self._get_kit_param('fx_rev')

    @fx_rev.setter
    def fx_rev(self, value):
        self._set_kit_param('fx_rev', value)

    @property
    def fx_del(self) -> FxDelayType:
        """FX delay type."""
        return self._get_kit_param('fx_del')

    @fx_del.setter
    def fx_del(self, value):
        self._set_kit_param('fx_del', value)

    @property
    def morph_kit(self) -> int:
        """Kit index (0-63) used as the morph destination."""
        return self._get_kit_param('morph_kit')

    @morph_kit.setter
    def morph_kit(self, value):
        self._set_kit_param('morph_kit', value)

    def voice(self, num: int) -> Voice:
        """
        Get a Voice object for accessing voice parameters.

        Args:
            num: Voice number (1-6).

        Returns:
            Voice object.
        """
        if self._data is None:
            raise ValueError("Kit not initialized")
        if num not in self._voices:
            self._voices[num] = Voice(self, num)
        return self._voices[num]

    def copy_voice_from(self, source_kit: 'Kit', source_voice: int, dest_voice: int):
        """
        Copy all voice data from another kit.

        Copies every per-voice parameter in PARAM_OFFSETS that exists on both
        voices. Parameters a voice doesn't have (e.g. V4 noise, V5/V6 FM
        gains) are skipped, and kit-level FX/morph settings are left alone.

        Args:
            source_kit: Source Kit to copy from.
            source_voice: Source voice number (1-6).
            dest_voice: Destination voice number (1-6).
        """
        if self._data is None or source_kit._data is None:
            raise ValueError("Kit not initialized")
        if not 1 <= source_voice <= 6:
            raise ValueError(f"Source voice must be 1-6, got {source_voice}")
        if not 1 <= dest_voice <= 6:
            raise ValueError(f"Dest voice must be 1-6, got {dest_voice}")

        # Copy all parameters for this voice
        for param, offsets in PARAM_OFFSETS.items():
            src_offset = offsets[source_voice - 1]
            dst_offset = offsets[dest_voice - 1]
            if src_offset is not None and dst_offset is not None:
                self._data[dst_offset] = source_kit._data[src_offset]

    def to_dict(self) -> dict:
        """Export kit to a dictionary."""
        return {
            'name': self.name,
            'voices': [self.voice(i).to_dict() for i in range(1, 7)],
            'kit': {
                param: (val.name if hasattr(val, 'name') else val)
                for param in KIT_PARAM_OFFSETS
                for val in [self._get_kit_param(param)]
            },
        }

    def __repr__(self) -> str:
        name = self.name if self._data else "(uninitialized)"
        return f"Kit('{name}')"


def format_kit_filename(index: int, name: str) -> str:
    """
    Format a kit filename for the LXR-02 SD card.

    The LXR-02 uses the format: NN-XXXXX.SND
    where NN is the 2-digit index (00-63) and XXXXX is a 5-character name.

    Args:
        index: Kit index (0-63).
        name: Kit name (will be truncated to 5 characters, uppercased).

    Returns:
        Formatted filename.
    """
    if not 0 <= index <= 63:
        raise ValueError(f"Kit index must be 0-63, got {index}")
    # Truncate to 5 chars and uppercase
    short_name = name[:5].upper()
    return f"{index:02d}-{short_name}.SND"

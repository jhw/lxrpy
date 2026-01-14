"""
Enum definitions for LXR-02 parameters.

Based on reverse-engineered LXR-02 binary format.
"""
from enum import IntEnum


class Waveform(IntEnum):
    """Oscillator waveform types (osc.wav, fm.wav)."""
    SIN = 0
    TRI = 1
    SAW = 2
    REC = 3  # Rectangle/Square
    NOI = 4  # Noise
    PWM = 5


class FmMode(IntEnum):
    """FM modulation mode (fm.mod for V1-V3)."""
    FM = 0
    MIX = 1


class ClickWave(IntEnum):
    """Click/transient waveform types (click.wav)."""
    SNP = 0   # Snap
    OFS = 1   # Offset
    CLK = 2   # Click
    CK2 = 3   # Click 2
    TIK = 4   # Tick
    KIK = 5   # Kick
    RIM = 6   # Rim
    DRP = 7   # Drop
    HAT = 8   # Hat
    CLP = 9   # Clap
    KK2 = 10  # Kick 2
    SNR = 11  # Snare
    TOM = 12  # Tom
    SP2 = 13  # Special 2


class FilterType(IntEnum):
    """Filter types (flt.typ)."""
    LP = 0    # Low Pass
    HP = 1    # High Pass
    BP = 2    # Band Pass
    UBP = 3   # Ultra Band Pass
    NCH = 4   # Notch
    PEK = 5   # Peak
    LP2 = 6   # Low Pass 2
    OFF = 7   # Off


class LfoWave(IntEnum):
    """LFO waveform types (lfo.wav)."""
    SIN = 0   # Sine
    TRI = 1   # Triangle
    SUP = 2   # Slope Up
    SDN = 3   # Slope Down
    SQR = 4   # Square
    RND = 5   # Random
    XUP = 6   # Exponential Up
    XDN = 7   # Exponential Down


class LfoSync(IntEnum):
    """LFO sync/division settings (lfo.snc)."""
    OFF = 0
    DIV_4_1 = 1   # 4/1
    DIV_2_1 = 2   # 2/1
    DIV_1_1 = 3   # 1/1
    DIV_1_2 = 4   # 1/2
    DIV_1_3 = 5   # 1/3
    DIV_1_4 = 6   # 1/4
    DIV_1_6 = 7   # 1/6
    DIV_1_8 = 8   # 1/8
    DIV_12 = 9    # 12
    DIV_16 = 10   # 16
    DIV_32 = 11   # 32


class LfoRetrig(IntEnum):
    """LFO retrigger source (lfo.rtg)."""
    OFF = 0
    V1 = 1
    V2 = 2
    V3 = 3
    V4 = 4
    V5 = 5
    V6 = 6


class OutputRouting(IntEnum):
    """Output routing options (mix.out)."""
    ST1 = 0  # Stereo 1
    ST2 = 1  # Stereo 2
    L1 = 2   # Left 1
    R1 = 3   # Right 1
    L2 = 4   # Left 2
    R2 = 5   # Right 2
    FX = 6   # Effects bus


class FlamAmount(IntEnum):
    """Flam amount settings for pattern steps."""
    OFF = 0
    X2 = 1
    X3 = 2
    X4 = 3
    X6 = 4
    X8 = 5

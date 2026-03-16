"""
lxrpy - Python tools for Erica Synths LXR-02 drum synthesizer files.

This package provides tools for reading and writing LXR-02 binary files:
- Kit/Sound files (.SND) - 255 bytes, synthesis parameters for 6 voices
- Pattern files (.PAT) - 3663 bytes, step sequencer data for 6 voices
- Global config (GLO.CFG) - 30 bytes, BPM and MIDI settings

Example usage:

    from lxr import Kit, Pattern, GlobalConfig, Waveform

    # Load and modify a kit
    kit = Kit.from_file('my_kit.SND')
    kit.name = "KICK"
    kit.voice(1).osc_wav = Waveform.SAW
    kit.voice(1).mix_vol = 100
    kit.save('new_kit.SND')

    # Load and modify a pattern
    pattern = Pattern.from_file('my_pattern.PAT')
    v1 = pattern.voice(1)
    v1.length = 16
    v1.set_triggers([1, 5, 9, 13])  # 4-on-the-floor
    v1.step(1).velocity = 127
    pattern.save('new_pattern.PAT')

    # Copy voice between kits
    source_kit = Kit.from_file('source.SND')
    dest_kit = Kit.from_file('dest.SND')
    dest_kit.copy_voice_from(source_kit, 1, 1)  # Copy V1 to V1

    # Copy voice pattern between patterns
    source_pat = Pattern.from_file('source.PAT')
    dest_pat = Pattern.from_file('dest.PAT')
    dest_pat.copy_voice_from(source_pat, 1, 2)  # Copy V1 pattern to V2
"""

__version__ = "0.1.0"

from .enums import (
    Waveform,
    FmMode,
    ClickWave,
    FilterType,
    LfoWave,
    LfoSync,
    LfoRetrig,
    OutputRouting,
    FlamAmount,
)

from .kit import (
    Kit,
    Voice,
    format_kit_filename,
)

from .pattern import (
    Pattern,
    VoicePattern,
    Step,
    format_pattern_filename,
)

from .config import (
    GlobalConfig,
)

from .project import (
    note_name,
    read_project_name,
    write_project_name,
    load_kit,
    load_kits,
    is_populated,
    find_empty_slot,
)

__all__ = [
    # Version
    '__version__',
    # Enums
    'Waveform',
    'FmMode',
    'ClickWave',
    'FilterType',
    'LfoWave',
    'LfoSync',
    'LfoRetrig',
    'OutputRouting',
    'FlamAmount',
    # Kit
    'Kit',
    'Voice',
    'format_kit_filename',
    # Pattern
    'Pattern',
    'VoicePattern',
    'Step',
    'format_pattern_filename',
    # Config
    'GlobalConfig',
    # Project utilities
    'note_name',
    'read_project_name',
    'write_project_name',
    'load_kit',
    'load_kits',
    'is_populated',
    'find_empty_slot',
]

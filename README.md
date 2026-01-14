# lxrpy

Python tools for reading and writing Erica Synths LXR-02 drum synthesizer files.

## Resources

- [Erica Synths LXR-02 Product Page](https://www.ericasynths.lv/drum-synthesizer-lxr-02-1132/)
- [LXR-02 Tutorial Video](https://www.youtube.com/watch?v=Wvjx5t_XRwg)
- [LXR-02 Factory Reset Guide](https://www.youtube.com/watch?v=R1lOFlADtiQ)
- [LXR-02 Binary Format Documentation](https://gist.github.com/jhw/ae2a6eb8127dc4b0851f55d26d0ebb65) - Reverse-engineered file format specifications

## Concepts

### Project Structure

The LXR-02 organizes data hierarchically:

```
Project (PROJ00-PROJ63)
├── Global Config (GLO.CFG) ─── BPM, MIDI channels, MIDI notes
├── Patterns (00-.PAT to 63-.PAT)
│   └── Each pattern references a Kit by index
└── Kits (00-NAME.SND to 63-NAME.SND)
```

### Patterns Own Kits

**Kits are subordinate to patterns.** Each pattern stores a `kit_index` that references which kit (.SND file) provides the sound design for that pattern. This means:

- Different patterns can use different kits
- Switching patterns can also switch the active kit
- You can reassign a pattern to use a different kit by changing its `kit_index`

```python
# Pattern 00 uses kit 05
pattern = Pattern.from_file('00-.PAT')
pattern.kit_index = 5  # Now references 05-*.SND
pattern.save('00-.PAT')
```

### Global Config is Project-Wide

**MIDI settings span all patterns within a project.** The `GLO.CFG` file stores:

- BPM (tempo for the entire project)
- MIDI channel per voice (V1-V6)
- MIDI note per voice (V1-V6)

These settings apply to all 64 patterns in the project. If you need different MIDI configurations, use different projects.

### Per-Voice Pattern Lengths

Each voice within a pattern can have a different length (1-64 steps), enabling polymetric patterns. The step triggers, velocities, and other step data are independent per voice.

### Capacity

- 64 projects per SD card
- 64 patterns per project (4096 total)
- 64 kits per project (4096 total)
- 6 voices per kit/pattern
- 64 steps per voice

## Installation

```bash
pip install git+https://github.com/jhw/lxrpy.git@v0.1.0
```

## Features

- Read and write LXR-02 kit/sound files (.SND)
- Read and write pattern files (.PAT)
- Read and write global config files (GLO.CFG)
- Copy voices between kits
- Copy voice patterns between patterns
- SD card utilities for file management

## Quick Start

### Working with Kits

```python
from lxr import Kit, Waveform, FilterType

# Load a kit from file
kit = Kit.from_file('/Volumes/LXR/PROJ00/00-BADON.SND')

# Or initialize from template
kit = Kit.init()

# Set kit name
kit.name = "MYKICK"

# Access and modify voice parameters
v1 = kit.voice(1)
v1.osc_wav = Waveform.SAW
v1.osc_coa = -29  # Coarse tune
v1.aeg_dec = 50   # Decay
v1.flt_frq = 80   # Filter frequency
v1.flt_typ = FilterType.LP
v1.mix_vol = 127  # Volume

# Save to file
kit.save('new_kit.SND')

# Copy a voice from another kit
source_kit = Kit.from_file('source.SND')
kit.copy_voice_from(source_kit, source_voice=1, dest_voice=1)
```

### Working with Patterns

```python
from lxr import Pattern, FlamAmount

# Load a pattern
pattern = Pattern.from_file('/Volumes/LXR/PROJ00/00-.PAT')

# Or initialize from template
pattern = Pattern.init()

# Set which kit this pattern uses
pattern.kit_index = 0  # References 00-*.SND

# Access voice patterns
v1 = pattern.voice(1)

# Set pattern length
v1.length = 16

# Set step triggers (4-on-the-floor)
v1.set_triggers([1, 5, 9, 13])

# Modify step data
step = v1.step(1)
step.velocity = 127
step.note = 36  # C2
step.probability = 100
step.flam = FlamAmount.OFF
step.shift = 0

# Copy voice pattern from another pattern
source_pat = Pattern.from_file('source.PAT')
pattern.copy_voice_from(source_pat, source_voice=1, dest_voice=2)

# Save
pattern.save('new_pattern.PAT')
```

### Working with Global Config

```python
from lxr import GlobalConfig

# Load config
config = GlobalConfig.from_file('/Volumes/LXR/PROJ00/GLO.CFG')

# Or initialize from template
config = GlobalConfig.init()

# Set BPM
config.bpm = 120

# Set MIDI channel per voice
config.set_midi_channel(1, 1)   # Voice 1 on channel 1
config.set_midi_channel(2, 2)   # Voice 2 on channel 2

# Set MIDI note per voice
config.set_midi_note(1, 36)     # Voice 1 triggers C2
config.set_midi_note(2, 38)     # Voice 2 triggers D2

# Save
config.save('GLO.CFG')
```

## CLI Tools

### List SD Card Contents

```bash
# List all projects and their contents
lxr-list

# Use custom SD card path
lxr-list --sd-path /Volumes/LXR

# Show detailed information
lxr-list --detailed
```

### Copy Files to SD Card

```bash
# Copy a kit to project 00 at index 10
lxr-copy mykit.SND --project 0 --index 10 --name KICK

# Copy multiple kits
lxr-copy kit1.SND kit2.SND --project 0 --start-index 20

# Force overwrite
lxr-copy mykit.SND --project 0 --index 10 --force
```

### Clean SD Card

```bash
# Clean all kits and patterns from project 05
lxr-clean --project 5

# Clean only kits
lxr-clean --project 5 --kits-only

# Clean specific index range
lxr-clean --project 5 --start 10 --end 20

# Dry run (preview without deleting)
lxr-clean --project 5 --dry-run
```

## Voice Types

The LXR-02 has 6 voices with different synthesis models:

| Voice | Name | Model | Special Parameters |
|-------|------|-------|-------------------|
| 1-3 | Drum 1-3 | Standard | Full FM + Mod |
| 4 | Snare | Standard + Noise | `osc_noi`, `osc_mix` (no FM) |
| 5-6 | HiHat 1-2 | Alternate FM | `fm_wav2`, `fm_f1`, `fm_f2`, `fm_g1`, `fm_g2` |

## Available Parameters

### Oscillator (all voices)
- `osc_wav` - Waveform (Sin, Tri, Saw, Rec, Noi, Pwm)
- `osc_coa` - Coarse tune (-60 to +67)
- `osc_fin` - Fine tune (-63 to +64)
- `osc_pwm` - Pulse width (0-127)
- `osc_noi` - Noise amount (V4 only, 0-127)
- `osc_mix` - Osc/noise mix (V4 only, 0-127)

### Amplitude Envelope
- `aeg_atk` - Attack (0-127)
- `aeg_dec` - Decay (0-127)
- `aeg_slp` - Slope (0-127)
- `aeg_rpt` - Repeat (V4-V5 only, 0-127)

### FM (V1-V3)
- `fm_wav` - FM waveform
- `fm_amt` - FM amount (0-127)
- `fm_frq` - FM frequency (-60 to +67)
- `fm_mod` - FM mode (FM, Mix)

### FM (V5-V6 alternate)
- `fm_wav`, `fm_wav2` - FM waveforms
- `fm_f1`, `fm_f2` - Frequencies (-60 to +67)
- `fm_g1`, `fm_g2` - Gains (0-127)

### Modulator (V1-V4)
- `mod_dec` - Decay (0-127)
- `mod_slp` - Slope (0-127)
- `mod_mod` - Modulation (0-127)
- `mod_amt` - Amount (0-127)
- `mod_dst` - Destination
- `mod_vol` - On/off (all voices, 0-1)

### Click (all voices)
- `click_wav` - Waveform
- `click_vol` - Volume (0-127)
- `click_frq` - Frequency (0-127)

### Filter (all voices)
- `flt_frq` - Frequency (0-127)
- `flt_res` - Resonance (0-127)
- `flt_drv` - Drive (0-127)
- `flt_typ` - Type (LP, HP, BP, UBP, NCH, PEK, LP2, OFF)

### LFO (all voices)
- `lfo_frq` - Frequency (0-127)
- `lfo_mod` - Modulation (0-127)
- `lfo_wav` - Waveform
- `lfo_snc` - Sync division
- `lfo_rtg` - Retrigger source
- `lfo_ofs` - Offset (0-127)
- `lfo_voi` - Voice target
- `lfo_dst` - Destination

### Mix (all voices)
- `mix_vol` - Volume (0-127)
- `mix_pan` - Pan (-63 to +64)
- `mix_drv` - Drive (0-127)
- `mix_srt` - Start (0-127)
- `mix_out` - Output routing (St1, St2, L1, R1, L2, R2, FX)

## File Formats

| Type | Extension | Size | Description |
|------|-----------|------|-------------|
| Kit/Sound | .SND | 255 bytes | Synthesis parameters for 6 voices |
| Pattern | .PAT | 3663 bytes | Step sequencer data for 6 voices |
| Global Config | GLO.CFG | 30 bytes | BPM and MIDI settings |

## SD Card Structure

```
/Volumes/LXR/
├── PROJ00/ - PROJ63/           # 64 project folders
│   ├── 00-NAME.SND - 63-NAME.SND   # Kit files
│   ├── 00-NAME.PAT - 63-NAME.PAT   # Pattern files
│   ├── 00-EMPTY.SNG - 63-EMPTY.SNG # Song files
│   ├── GLO.CFG                      # Global config
│   └── PRJ.NFO                      # Project info
├── SAMPLES/
└── SYSTEM/
```

## Roadmap

The following features are not yet implemented:

### Unmapped Binary Ranges
Some byte ranges in the binary files contain non-zero data but their purpose is not yet documented. These bytes are preserved when loading/saving but not exposed via the API.

### SD Card Factory Reset
A utility to perform a factory reset on the SD card, restoring default projects, kits, and patterns. See the [Factory Reset Guide](https://www.youtube.com/watch?v=R1lOFlADtiQ) for the manual process.

### MIDI Pattern Changes
Support for MIDI program change messages to switch patterns, and pattern chaining/song mode automation.

### Mod/LFO Destination Enums
The `mod_dst` and `lfo_dst` parameters currently accept raw integer values. Full enum mappings for all ~40 modulation destinations need to be documented and implemented.

### Per-Step Parameter Locks
Pattern steps have 4 unmapped bytes (bytes 3-6 of each 7-byte step record) that likely contain per-step parameter automation/locks. These need to be reverse-engineered and exposed via the Step API.

## Development

```bash
# Clone repository
git clone https://github.com/jhw/lxrpy.git
cd lxrpy

# Run tests
python run_tests.py
```

## License

MIT

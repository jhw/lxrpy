# lxrpy

Python tools for reading and writing Erica Synths LXR-02 drum synthesizer files.

## Resources

- [Erica Synths LXR-02 Product Page](https://www.ericasynths.lv/drum-synthesizer-lxr-02-1132/)
- [LXR-02 Tutorial Video](https://www.youtube.com/watch?v=Wvjx5t_XRwg)
- [LXR-02 Factory Reset Guide](https://www.youtube.com/watch?v=R1lOFlADtiQ)
- [LXR-02 Binary Format Documentation](https://gist.github.com/jhw/ae2a6eb8127dc4b0851f55d26d0ebb65) - Reverse-engineered file format specifications
- [LXR-02 Firmware Source](https://github.com/erica-synths/lxr-desktop-app) - Erica Synths' open-sourced firmware; `Core/Src/Preset/presetManager.c` reads and writes every file format and `Core/Inc/Parameters.h` defines the kit byte order

## Concepts

### Project Structure

The LXR-02 organizes data hierarchically:

```
Project (PROJ00-PROJ63)
├── Project name (PRJ.NFO) ───── required for the LXR to load the project
├── Global Config (GLO.CFG) ─── BPM, MIDI, clock settings
├── Patterns (00-.PAT to 63-.PAT)
│   └── Each pattern references a Kit by index
├── Kits (00-NAME.SND to 63-NAME.SND)
└── Songs (00-NAME.SNG to 63-NAME.SNG) ─── pattern play order
```

### Patterns Own Kits

**Kits are subordinate to patterns.** Each pattern stores a `kit_index` that references which kit (.SND file) provides the sound design for that pattern. This means:

- Different patterns can use different kits
- Switching patterns also switches the active kit when `GlobalConfig.pattern_mode` is `AUTO` (the default)
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
- MIDI channel and note per track (V1-V7), plus a global channel (0 = all)
- MIDI routing and TX/RX filters
- Trigger clock in/out resolution
- Follow, screensaver, bar reset and kit change mode

These settings apply to all 64 patterns in the project. If you need different MIDI configurations, use different projects. Shuffle is not global: each pattern has its own (`Pattern.shuffle`).

### Per-Voice Pattern Lengths

Each voice within a pattern can have a different length (1-64 steps), enabling polymetric patterns. The step triggers, velocities, and other step data are independent per voice.

### Capacity

- 64 projects per SD card
- 64 patterns per project (4096 total)
- 64 kits per project (4096 total)
- 6 voices per kit; 7 tracks per pattern (track 7 is the open hi-hat, played on V6)
- 64 steps per track
- 64 songs per project, up to 64 positions each

## Installation

```bash
pip install git+https://github.com/jhw/lxrpy.git@v0.3.0
```

## Features

- Read and write LXR-02 kit/sound files (.SND)
- Read and write pattern files (.PAT)
- Read and write song files (.SNG)
- Read and write global config files (GLO.CFG)
- Kit-level FX bus settings
- Per-step parameter automation
- Decode and encode LFO/velocity modulation destinations
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

# Kit-level FX bus
from lxr import FxType, OutputRouting
kit.fx_typ = FxType.DEL
kit.fx_dw = 40          # dry/wet, 0-100
kit.fx_p1 = 64          # P1-P4 depend on the FX type
v1.mix_out = OutputRouting.FX  # send V1 to the FX bus

# LFO / velocity modulation destinations
from lxr import mod_target, mod_target_index
v1.lfo_dst = mod_target_index('flt_frq', voice=2)
mod_target(v1.lfo_dst)  # ('flt_frq', 2)
```

### Working with Songs

```python
from lxr import Song, format_song_filename

song = Song()
song.name = "SET1"
song.set_patterns([0, 0, 1, 2], loop=True)
song.save(format_song_filename(0, song.name))  # 00-SET1.SNG
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
step.note = 36  # C3 (LXR labelling)
step.probability = 100
step.flam = FlamAmount.OFF
step.shift = 0

# Per-step automation: two slots, each sets one parameter when the step plays
step.set_automation(1, 'flt_frq', 100)          # this track's voice
step.set_automation(2, 'osc_coa', 70, voice=4)  # any voice's parameter
step.get_automation(1)                           # (param_number, value)
step.clear_automation()

# Pattern name and shuffle
pattern.name = "GROOVE"
pattern.shuffle = 32  # 0-127

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

# Set MIDI note per voice (LXR-02 labelling: MIDI 48 = C4)
config.set_midi_note(1, 36)     # Voice 1 triggers C3
config.set_midi_note(2, 38)     # Voice 2 triggers D3
config.set_midi_note(3, 0)      # Voice 3 sends each step's own note

# Other settings
from lxr import MidiFilter, PatternMode
config.global_midi_channel = 0  # 0 = all channels
config.midi_rx_filter = MidiFilter.NOTES | MidiFilter.CC
config.pattern_mode = PatternMode.AUTO

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

# Replace whatever file already uses index 10, whatever its name
lxr-copy mykit.SND --project 0 --index 10 --force
```

The LXR opens files by index (`10-*.SND`), so an existing file with the same index is a conflict even if its name differs; `--force` removes it rather than leaving two index-10 files.

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
- `aeg_dec_open` - Open hi-hat decay (V6 only, 0-127; `aeg_dec` is the closed decay)

### FM (V1-V3)
- `fm_wav` - FM waveform
- `fm_amt` - FM amount (0-127)
- `fm_frq` - FM frequency (-60 to +67)
- `fm_mod` - FM mode (FM, Mix)

### FM (V5-V6 alternate)
- `fm_wav`, `fm_wav2` - FM waveforms
- `fm_f1`, `fm_f2` - Frequencies (-60 to +67)
- `fm_g1`, `fm_g2` - Gains (0-127)

### Pitch Modulation (V1-V4)
- `mod_dec` - Decay (0-127)
- `mod_slp` - Slope (0-127)
- `mod_mod` - Amount (0-127)

### Velocity Modulation (all voices)
- `mod_amt` - Amount (0-127)
- `mod_dst` - Destination (index into `MOD_TARGETS`; see `mod_target()`)
- `mod_vol` - Velocity modulates volume (0-1)

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
- `lfo_voi` - Target voice (1-6)
- `lfo_dst` - Destination (index into `MOD_TARGETS`; see `mod_target()`)

### Mix (all voices)
- `mix_vol` - Volume (0-127)
- `mix_pan` - Pan (-63 to +64)
- `mix_drv` - Drive (0-127)
- `mix_srt` - Sample rate reduction (0-127)
- `mix_out` - Output routing (St1, St2, L1, R1, L2, R2, FX)

### Kit-level (`Kit` properties)
- `fx_typ` - FX type (off, drv, rng, cmp, del)
- `fx_out` - FX output routing (St1-R2)
- `fx_dw` - Dry/wet (0-100)
- `fx_p1`-`fx_p4` - FX parameters (0-127, meaning depends on type)
- `fx_dis`, `fx_rat`, `fx_wav`, `fx_rev`, `fx_del` - Distortion type, compressor ratio, ring mod waveform, reverb type, delay type
- `srt_all` - Global sample rate reduction (0-127)
- `morph_kit` - Morph destination kit index (0-63)

## File Formats

| Type | Extension | Size | Description |
|------|-----------|------|-------------|
| Kit/Sound | .SND | 255 bytes | Name + synthesis parameters for 6 voices + FX |
| Pattern | .PAT | 3663 bytes | Name + step data for 7 tracks, shuffle, lengths, kit index |
| Song | .SNG | 72 bytes | Name + 64 pattern positions |
| Global Config | GLO.CFG | 30 bytes | BPM, MIDI and clock settings |
| Project Info | PRJ.NFO | 8 bytes | Project name |

## SD Card Structure

```
/Volumes/LXR/
├── PROJ00/ - PROJ63/           # 64 project folders
│   ├── 00-NAME.SND - 63-NAME.SND   # Kit files
│   ├── 00-NAME.PAT - 63-NAME.PAT   # Pattern files
│   ├── 00-EMPTY.SNG - 63-EMPTY.SNG # Song files
│   ├── GLO.CFG                      # Global config
│   └── PRJ.NFO                      # Project name (required)
├── TMP/                        # Working state restored at power-on
├── PROJ.IDX                    # Last loaded project number
├── SAMPLES/
└── SYSTEM/
```

At power-on the LXR restores its working state from `TMP/`, not from a project folder, and kits or patterns saved on the device go to `TMP/` until you save the project. Files copied into `PROJxx/` therefore appear once you load that project on the device. Missing kits, patterns and songs are fine, but a project without `PRJ.NFO` won't load.

## Roadmap

The following features are not yet implemented:

### SD Card Factory Reset
A utility to perform a factory reset on the SD card, restoring default projects, kits, and patterns. See the [Factory Reset Guide](https://www.youtube.com/watch?v=R1lOFlADtiQ) for the manual process.

### MIDI Pattern Changes
Support for MIDI program change messages to switch patterns.

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

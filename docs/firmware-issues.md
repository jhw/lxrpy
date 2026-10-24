# LXR-02 firmware issues

Issues found by reading the open-sourced firmware
([erica-synths/lxr-desktop-app](https://github.com/erica-synths/lxr-desktop-app),
v1.7, commit `a43cd4f`). Nothing here has been built or tested on a device yet.
Paths are relative to the firmware repo root.

Confidence: **confirmed** = traced through the code; **suspect** = likely, needs
a device test.

## 1. MIDI CC 0 (bank select) kit switching is half-implemented

Reported to Erica Synths support on 2026-03-13 (request 28474). They said it is
probably left over from the DIY LXR v1 firmware and added it to the FW update
list; no fix followed.

Handler: `Core/Src/frontPanelParser.c:108-116` (`frontPanel_ccHandler`):

```c
if(parNr == 255/*PAR_BANK_CHANGE*/)   // CC 0: data1 - 1 wraps to 255
{
    menu_selectedPresetNr[0] = frontParser_midiMsg.data2;
    preset_loadDrumsetRam(frontParser_midiMsg.data2,0, 0);
    preset_touchTimer(PRESET_KIT_TIMER);
    menu_repaint();
    return;
}
```

Reached from MIDI in via `MidiParser.c:1880-1894` (CC forwarded to the front
panel on any configured channel when the CC filter allows it).

### 1a. Kit name on screen doesn't update (confirmed: the reported glitch)

The load/save page draws the name from `nameEditBuffer`, a cached copy
(`menu.c:1316-1326`; the direct `savefileNames` read is `#if 0`). The cache
is only refreshed by `copyNameToEditBuffer()` when the encoder changes the
preset number (`menu.c:2398`) or the page changes (`menu.c:3341`, `3359`).
The CC handler updates the number but not the cache, so the number changes
and the name doesn't.

### 1b. Out-of-bounds kit index (confirmed)

`data2` is 0-127 but there are 64 kit slots (`NUM_KIT_SLOTS`). Values 64-127
make `preset_loadDrumsetRam()` copy `mainParameters[data2]` from past the end
of the array (garbage loaded as a kit) and leave `menu_selectedPresetNr[0]`
out of range for later `savefileNames[...]` reads and saves. Program change
has the guard this lacks (`sequencer.c:459`: `if(patNr >= MAX_PATTERN) return;`).

### 1c. State the menu load path sets but CC 0 doesn't (confirmed)

Compare the menu kit load (`menu.c:2192-2206`) and pattern-change autoload
(`sequencer.c:646-655`):

- `menu_loadedPresetNr[CURRENT_KIT]` isn't updated, so the save page's
  "copy name from loaded kit" (`menu.c:2167`) uses the previous kit.
- `menu_TargetVoiceGapIndex` isn't recomputed (it's `static` in `menu.c`, so
  the fix needs a small helper in `menu.c`).
- The menu load also stores the kit in the current pattern
  (`seq_patternSet.kitNr[seq_activePattern]`). For CC 0 that's a design
  choice: leaving it out keeps CC 0 a performance change, and with pattern
  mode AUTO the next pattern change reloads the pattern's own kit.

### 1d. CC 0 is recorded as step automation while recording (suspect)

`MidiParser.c:1887` calls `seq_recordAutomation()` for every CC before
handling it, including CC 0, mod wheel and NRPN CCs. Each CC 0 while
recording writes automation destination 0 into the current step, using up a
slot. On playback it is sent as CC 0, which the sound engine ignores
(`MidiParser.c:179`).

### Proposed fix (sketch)

Add to `menu.c` (it owns the static state) and call it from the CC 0 branch:

```c
// called when a kit is loaded from outside the menu (MIDI bank select)
void menu_onExternalKitLoad(uint8_t kitNr)
{
	menu_selectedPresetNr[SAVE_TYPE_KIT] = kitNr;
	menu_loadedPresetNr[CURRENT_KIT] = kitNr;
	menu_TargetVoiceGapIndex = getModTargetGapIndex(activeParameters[PAR_TARGET_LFO1 + menu_activeVoice]);
	// the load page shows the cached name; don't clobber a name being edited on the save page
	if(menu_activePage == LOAD_PAGE && menu_saveOptions.category == SAVE_TYPE_KIT)
		copyNameToEditBuffer(kitNr, KIT_NAMES);
}
```

```c
if(parNr == 255/*PAR_BANK_CHANGE*/)
{
	const uint8_t kitNr = frontParser_midiMsg.data2;
	if(kitNr >= NUM_KIT_SLOTS) return;
	preset_loadDrumsetRam(kitNr, 0, 0);
	menu_onExternalKitLoad(kitNr);
	preset_touchTimer(PRESET_KIT_TIMER);
	menu_repaint();
	return;
}
```

Optionally skip `seq_recordAutomation()` for CCs that aren't sound
parameters (1d).

## 2. Pattern files: track length and kit index aren't validated (confirmed)

`Core/Src/Preset/presetManager.c:1949-1966` (`preset_readPatternData`):

- Track lengths are read into `next` without checking `bytesRead` or range.
  A truncated file gives every track length 0 (`next` starts at 0) or the
  previous track's value; a corrupt byte gives anything 0-255.
- Length 0 reaches `(step+1) % length` in `sequencer.c:1111` (and the
  `#if 0` copy at 946). On the Cortex-M7 unsigned divide by zero returns 0
  unless `DIV_0_TRP` is set (it isn't), so no fault, but
  `prevStep = length-1` is 255, an out-of-bounds step index. Lengths above
  64 index past the 64 steps too.
- `kitNr` isn't checked against 64. With pattern mode AUTO, switching to the
  pattern runs `preset_loadDrumsetRam(seq_patternSet.kitNr[...])`
  (`sequencer.c:651`) with an out-of-range index.

The same pattern applies to the autosave loader `preset_LoadTmpPat()`
(`presetManager.c:302-480`).

Fix: clamp lengths to 1-64 (default 16 when missing) and reset bad kit
numbers to 0 after reading.

## 3. Song entries above 65 index past the patterns (confirmed)

`seq_determineNextPattern()` (`sequencer.c:565-589`) returns the raw song
byte. Only 64 (`SONG_END`) and 65 (`SONG_LOOP`) are handled
(`sequencer.c:1303-1317`); 66-255 flow into `seq_setPendingPatternActive()`
(`sequencer.c:602`), which indexes the pattern arrays with no check. Song
bytes come straight from `.SNG` files (`presetManager.c:2591`).

Fix: treat any value above `SONG_LOOP` as `SONG_END`, or validate on load.
Related TODO at `sequencer.c:577`: a song using all 64 positions loops
instead of stopping.

## 4. Global MIDI channel 0 ("all") is sent as 0xFF (suspect)

The firmware default sets `PAR_MIDI_CHAN_GLOBAL = 0 //all`
(`presetManager.c:1067`), but the menu can only set 1-16 (`DTYPE_1B16`
clamps, `menu.c:2966`). When globals are sent (`menu.c:3436-3446`) the
channel is `value-1`, so 0 becomes 255 and the packed byte
`(7<<4) | channel` is 0xFF. That goes through `frontPanel_sendData()` →
`frontParser_parseUartData()` (`frontPanelParser.c:617-633`) as a data
byte with the top bit set, which a MIDI-style parser would treat as a status
byte. If so, the global channel is never set, and program change
(`MidiParser.c:1874`) and global-channel CCs only match whatever
`midi_MidiChannels[7]` happens to hold.

Device test: fresh project (global channel 0), send program change on
channel 1 and on another channel, and see whether the pattern changes.

## 5. Kit values other than mod targets aren't validated on load (unverified)

`preset_readDrumsetData()` (`presetManager.c:1136-1170`) only normalises
velocity/LFO mod targets. Menu-type values (filter type, waveforms, LFO
voice 1-6, output routing, FX enums) are used as indices into name tables.
Check `getMenuItemNameForValue()` and the sound engine for bounds before
calling this a bug.

## 6. LXR v1 leftovers (cleanup, not bugs)

- **Parameter/CC off-by-one.** Front-panel parameter numbers start at 1 and
  sound-engine CCs at 2 (CC 1 is the mod wheel). `CortexParser.c:430-436` adds 1
  and wraps to 7 bits; `automationNode.c:51` has "todo why +1 offset?".
  Step automation stores the shifted CC number for parameters below 128 and
  the plain parameter number above. (lxrpy now encodes this, see
  `lxr/pattern.py`.) `frontPanelParser.c:108` detects CC 0 by relying on
  `data1 - 1` wrapping to 255.
- **Sub-step active bit.** `STEP_ACTIVE_MASK` (velocity bit 7) is ignored
  (`seq_intIsStepActive()` returns 1, `sequencer.c:2018-2025`), but
  `seq_clearTrack()` still sets it on every 8th step and `seq_toggleStep()`
  still exists.
- **`USE_PATTERN_EDIT_BUFFER`** is described as "a doomed approach" in
  `sequencer.h` but its `#if` branches remain throughout.
- **Unused parameters still handled:** `PAR_FETCH`, `PAR_QUANTISATION`,
  `PAR_MIDI_MODE`, `PAR_PRESCALER_CLOCK_OUT2`, `PAR_TRIG_GATE_MODE`,
  `PAR_POS_Y`, `PAR_FLUX`, `PAR_SOM_FREQ`, `PAR_PATTERN_NEXT` (some still send
  sequencer messages, e.g. `SEQ_POSY`/`SEQ_FLUX` in `menu.c`).
- **Follow mode.** `followNames` has off/bar/pat/p+b and `FOLLOW_BAR` /
  `FOLLOW_PATTERN` are defined, but `PAR_FOLLOW` is `DTYPE_ON_OFF` and used as
  a bool.
- **Stale numbering comments** in `Parameters.h` (e.g. `PAR_ROLL` marked 228;
  `END_OF_SOUND_PARAMETERS` is actually 247).
- **Old file formats.** The `p001.snd` filename fallback
  (`preset_makeFileNameOld`) and the `.all`/`.prj` project formats are still
  in `presetManager.c`, partly `#if`'d out.

## Next steps

1. **Toolchain** (see the firmware README): `brew install cmake ninja` and
   `brew install --cask gcc-arm-embedded`, then build to get
   `LXR_V2_V1.7.img`.
2. **Licence.** Modified firmware must show it is modified on the start-up
   screen and must not be presented as official (README "Licence" section,
   NOTICE.md).
3. **Device test** of the CC 0 fix: CC 0 values 0-63 load the kit and update
   the name on the Load/Kit page; 64-127 are ignored. Then items 2-4.
4. **Upstreaming.** As of 2026-10-24 the repo has no issues, no PRs and no
   contributing guide. Opening an issue first (citing support request 28474)
   is the low-cost way to find out whether they accept PRs; otherwise fork
   and PR.

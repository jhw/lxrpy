"""
LXR-02 Global Configuration file handling.

Global config files (GLO.CFG) are 30 bytes, one per firmware global
parameter, stored in each project folder:

     0  BPM (0=EXT, 1=MIDI, 2-255=BPM)
   1-6  MIDI channel V1-V6 (1-16)
     7  Fetch (unused)
     8  Follow (0/1)
     9  Quantisation (unused)
    10  Screensaver (0/1)
    11  MIDI mode (unused)
    12  MIDI channel V7 (1-16)
    13  MIDI routing (MidiRouting)
    14  MIDI TX filter (MidiFilter bitmask)
    15  MIDI RX filter (MidiFilter bitmask)
    16  Trigger clock in PPQ (ClockInPpq)
    17  Trigger clock out PPQ (ClockOutPpq)
    18  Trigger clock out 2 PPQ (unused)
    19  Trigger gate mode (unused)
    20  Pattern change resets bar counter (0/1)
    21  Global MIDI channel (0=all, 1-16)
 22-28  MIDI note V1-V7 (0=any: send the step's note)
    29  Pattern mode (PatternMode)

Shuffle is not global; it is stored per pattern (Pattern.shuffle).
"""
import os
import sys

from .enums import MidiRouting, MidiFilter, ClockInPpq, ClockOutPpq, PatternMode


CONFIG_SIZE = 30

# Offsets
BPM_OFFSET = 0
MIDI_CH_OFFSET = 1  # 6 bytes (V1-V6)
FOLLOW_OFFSET = 8
SCREENSAVER_OFFSET = 10
V7_MIDI_CH_OFFSET = 12
MIDI_ROUTING_OFFSET = 13
MIDI_TX_FILTER_OFFSET = 14
MIDI_RX_FILTER_OFFSET = 15
CLOCK_IN_PPQ_OFFSET = 16
CLOCK_OUT_PPQ_OFFSET = 17
BAR_RESET_OFFSET = 20
GLOBAL_MIDI_CH_OFFSET = 21
MIDI_NOTE_OFFSET = 22  # 6 bytes (V1-V6)
V7_MIDI_NOTE_OFFSET = 28
PATTERN_MODE_OFFSET = 29


class GlobalConfig:
    """
    Represents an LXR-02 global configuration file (GLO.CFG).

    Global config files are 30 bytes containing BPM and MIDI settings.
    Always initialize from a template or existing file to preserve unmapped bytes.

    Example:
        # Load from file
        config = GlobalConfig.from_file('GLO.CFG')

        # Initialize from template
        config = GlobalConfig.init()

        # Modify settings
        config.bpm = 120
        config.set_midi_channel(1, 1)  # Voice 1 on MIDI channel 1
        config.set_midi_note(1, 36)    # Voice 1 triggers note C2

        # Save
        config.save('GLO.CFG')
    """

    def __init__(self, data: bytes = None):
        """
        Initialize a GlobalConfig from binary data.

        Args:
            data: Raw 30-byte config data. If None, must use init() or from_file().
        """
        if data is not None:
            if len(data) != CONFIG_SIZE:
                raise ValueError(f"Config data must be {CONFIG_SIZE} bytes, got {len(data)}")
            self._data = bytearray(data)
        else:
            self._data = None

    @classmethod
    def init(cls, template_name: str = None) -> 'GlobalConfig':
        """
        Initialize a new GlobalConfig from a template.

        Args:
            template_name: Optional template name (without extension).
                          If None, uses default TEMPLATE.CFG.

        Returns:
            New GlobalConfig instance.
        """
        template_filename = f"{template_name}.CFG" if template_name else "GLO.CFG"
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
                files = importlib.resources.files('lxr.templates')
                template_path = files.joinpath(filename)
                if template_path.is_file():
                    return str(template_path)
            else:
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
    def from_file(cls, filename: str) -> 'GlobalConfig':
        """
        Load a GlobalConfig from a file.

        Args:
            filename: Path to GLO.CFG file.

        Returns:
            GlobalConfig instance.
        """
        with open(filename, 'rb') as f:
            data = f.read()
        return cls(data)

    def save(self, filename: str):
        """
        Save the GlobalConfig to a file.

        Args:
            filename: Path to save GLO.CFG file.
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        with open(filename, 'wb') as f:
            f.write(self._data)

    def to_bytes(self) -> bytes:
        """Return the raw config data as bytes."""
        if self._data is None:
            raise ValueError("Config not initialized")
        return bytes(self._data)

    def clone(self) -> 'GlobalConfig':
        """Create a deep copy of this GlobalConfig."""
        if self._data is None:
            raise ValueError("Config not initialized")
        return GlobalConfig(bytes(self._data))

    @property
    def bpm(self) -> int:
        """
        BPM (tempo) or sync mode.

        Values: 0=EXT sync, 1=MIDI sync, 2-255=BPM.
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        return self._data[BPM_OFFSET]

    @bpm.setter
    def bpm(self, value: int):
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 0 <= value <= 255:
            raise ValueError(f"BPM must be 0-255, got {value}")
        self._data[BPM_OFFSET] = value

    @property
    def global_midi_channel(self) -> int:
        """
        Global MIDI channel for program changes and kit-wide CCs.

        Values: 0=all channels, 1-16.
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        return self._data[GLOBAL_MIDI_CH_OFFSET]

    @global_midi_channel.setter
    def global_midi_channel(self, value: int):
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 0 <= value <= 16:
            raise ValueError(f"Global MIDI channel must be 0-16, got {value}")
        self._data[GLOBAL_MIDI_CH_OFFSET] = value

    def _get_byte(self, offset: int) -> int:
        if self._data is None:
            raise ValueError("Config not initialized")
        return self._data[offset]

    def _set_byte(self, offset: int, value: int, low: int, high: int, label: str):
        if self._data is None:
            raise ValueError("Config not initialized")
        value = int(value)
        if not low <= value <= high:
            raise ValueError(f"{label} must be {low}-{high}, got {value}")
        self._data[offset] = value

    @staticmethod
    def _as_enum(enum_class, raw: int):
        try:
            return enum_class(raw)
        except ValueError:
            return raw

    @property
    def follow(self) -> bool:
        """Sequencer page follows the playing position."""
        return bool(self._get_byte(FOLLOW_OFFSET))

    @follow.setter
    def follow(self, value: bool):
        self._set_byte(FOLLOW_OFFSET, bool(value), 0, 1, "Follow")

    @property
    def screensaver(self) -> bool:
        """Screensaver enabled."""
        return bool(self._get_byte(SCREENSAVER_OFFSET))

    @screensaver.setter
    def screensaver(self, value: bool):
        self._set_byte(SCREENSAVER_OFFSET, bool(value), 0, 1, "Screensaver")

    @property
    def midi_routing(self) -> MidiRouting:
        """MIDI routing between USB and DIN ports."""
        return self._as_enum(MidiRouting, self._get_byte(MIDI_ROUTING_OFFSET))

    @midi_routing.setter
    def midi_routing(self, value):
        self._set_byte(MIDI_ROUTING_OFFSET, value, 0, len(MidiRouting) - 1, "MIDI routing")

    @property
    def midi_tx_filter(self) -> MidiFilter:
        """MIDI message types transmitted (bitmask)."""
        return MidiFilter(self._get_byte(MIDI_TX_FILTER_OFFSET) & MidiFilter.ALL)

    @midi_tx_filter.setter
    def midi_tx_filter(self, value):
        self._set_byte(MIDI_TX_FILTER_OFFSET, value, 0, MidiFilter.ALL, "MIDI TX filter")

    @property
    def midi_rx_filter(self) -> MidiFilter:
        """MIDI message types received (bitmask)."""
        return MidiFilter(self._get_byte(MIDI_RX_FILTER_OFFSET) & MidiFilter.ALL)

    @midi_rx_filter.setter
    def midi_rx_filter(self, value):
        self._set_byte(MIDI_RX_FILTER_OFFSET, value, 0, MidiFilter.ALL, "MIDI RX filter")

    @property
    def clock_in_ppq(self) -> ClockInPpq:
        """Trigger clock input resolution."""
        return self._as_enum(ClockInPpq, self._get_byte(CLOCK_IN_PPQ_OFFSET))

    @clock_in_ppq.setter
    def clock_in_ppq(self, value):
        self._set_byte(CLOCK_IN_PPQ_OFFSET, value, 0, len(ClockInPpq) - 1, "Clock in PPQ")

    @property
    def clock_out_ppq(self) -> ClockOutPpq:
        """Trigger clock output resolution."""
        return self._as_enum(ClockOutPpq, self._get_byte(CLOCK_OUT_PPQ_OFFSET))

    @clock_out_ppq.setter
    def clock_out_ppq(self, value):
        self._set_byte(CLOCK_OUT_PPQ_OFFSET, value, 0, len(ClockOutPpq) - 1, "Clock out PPQ")

    @property
    def bar_reset(self) -> bool:
        """Manual pattern change resets the bar counter."""
        return bool(self._get_byte(BAR_RESET_OFFSET))

    @bar_reset.setter
    def bar_reset(self, value: bool):
        self._set_byte(BAR_RESET_OFFSET, bool(value), 0, 1, "Bar reset")

    @property
    def pattern_mode(self) -> PatternMode:
        """Kit change mode: AUTO loads each pattern's kit when the pattern changes."""
        raw = self._get_byte(PATTERN_MODE_OFFSET)
        # The firmware uses 2 internally ("skip next autoload") and treats it as AUTO
        return PatternMode.AUTO if raw >= PatternMode.AUTO else PatternMode.OFF

    @pattern_mode.setter
    def pattern_mode(self, value):
        self._set_byte(PATTERN_MODE_OFFSET, value, 0, 1, "Pattern mode")

    def _midi_ch_offset(self, voice: int) -> int:
        """Get byte offset for a voice's MIDI channel."""
        if voice == 7:
            return V7_MIDI_CH_OFFSET
        return MIDI_CH_OFFSET + voice - 1

    def _midi_note_offset(self, voice: int) -> int:
        """Get byte offset for a voice's MIDI note."""
        if voice == 7:
            return V7_MIDI_NOTE_OFFSET
        return MIDI_NOTE_OFFSET + voice - 1

    def get_midi_channel(self, voice: int) -> int:
        """
        Get MIDI channel for a voice.

        Args:
            voice: Voice number (1-7).

        Returns:
            MIDI channel (1-16).
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 1 <= voice <= 7:
            raise ValueError(f"Voice must be 1-7, got {voice}")
        return self._data[self._midi_ch_offset(voice)]

    def set_midi_channel(self, voice: int, channel: int):
        """
        Set MIDI channel for a voice.

        Args:
            voice: Voice number (1-7).
            channel: MIDI channel (1-16).
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 1 <= voice <= 7:
            raise ValueError(f"Voice must be 1-7, got {voice}")
        if not 1 <= channel <= 16:
            raise ValueError(f"Channel must be 1-16, got {channel}")
        self._data[self._midi_ch_offset(voice)] = channel

    def get_midi_note(self, voice: int) -> int:
        """
        Get MIDI note for a voice.

        Args:
            voice: Voice number (1-7).

        Returns:
            MIDI note (0-127, where C-4=48 in LXR numbering). 0 means "any":
            the voice sends each step's own note instead of a fixed note.
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 1 <= voice <= 7:
            raise ValueError(f"Voice must be 1-7, got {voice}")
        return self._data[self._midi_note_offset(voice)]

    def set_midi_note(self, voice: int, note: int):
        """
        Set MIDI note for a voice.

        Args:
            voice: Voice number (1-7).
            note: MIDI note (0-127). 0 sends each step's own note.
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 1 <= voice <= 7:
            raise ValueError(f"Voice must be 1-7, got {voice}")
        if not 0 <= note <= 127:
            raise ValueError(f"Note must be 0-127, got {note}")
        self._data[self._midi_note_offset(voice)] = note

    def to_dict(self) -> dict:
        """Export config to a dictionary."""
        return {
            'bpm': self.bpm,
            'global_midi_channel': self.global_midi_channel,
            'midi_channels': [self.get_midi_channel(i) for i in range(1, 8)],
            'midi_notes': [self.get_midi_note(i) for i in range(1, 8)],
            'follow': self.follow,
            'screensaver': self.screensaver,
            'midi_routing': self._enum_name(self.midi_routing),
            'midi_tx_filter': int(self.midi_tx_filter),
            'midi_rx_filter': int(self.midi_rx_filter),
            'clock_in_ppq': self._enum_name(self.clock_in_ppq),
            'clock_out_ppq': self._enum_name(self.clock_out_ppq),
            'bar_reset': self.bar_reset,
            'pattern_mode': self.pattern_mode.name,
        }

    @staticmethod
    def _enum_name(value):
        return value.name if hasattr(value, 'name') else value

    def __repr__(self) -> str:
        if self._data is None:
            return "GlobalConfig(uninitialized)"
        return f"GlobalConfig(bpm={self.bpm})"

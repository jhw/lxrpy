"""
LXR-02 Global Configuration file handling.

Global config files (GLO.CFG) are 30 bytes containing:
- BPM (1 byte)
- MIDI channel per voice (6 bytes)
- Shuffle (1 byte)
- Unknown (13 bytes)
- Global MIDI channel (1 byte)
- MIDI note per voice (6 bytes)
- Unknown (1 byte)
"""
import os
import sys


CONFIG_SIZE = 30

# Offsets
BPM_OFFSET = 0
MIDI_CH_OFFSET = 1  # 6 bytes (V1-V6)
SHUFFLE_OFFSET = 7
GLOBAL_MIDI_CH_OFFSET = 21
MIDI_NOTE_OFFSET = 22  # 6 bytes (V1-V6)


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
        Global MIDI channel for receiving pattern change messages.

        Values: 1-16.
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        return self._data[GLOBAL_MIDI_CH_OFFSET]

    @global_midi_channel.setter
    def global_midi_channel(self, value: int):
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 1 <= value <= 16:
            raise ValueError(f"Global MIDI channel must be 1-16, got {value}")
        self._data[GLOBAL_MIDI_CH_OFFSET] = value

    def get_midi_channel(self, voice: int) -> int:
        """
        Get MIDI channel for a voice.

        Args:
            voice: Voice number (1-6).

        Returns:
            MIDI channel (1-16).
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 1 <= voice <= 6:
            raise ValueError(f"Voice must be 1-6, got {voice}")
        return self._data[MIDI_CH_OFFSET + voice - 1]

    def set_midi_channel(self, voice: int, channel: int):
        """
        Set MIDI channel for a voice.

        Args:
            voice: Voice number (1-6).
            channel: MIDI channel (1-16).
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 1 <= voice <= 6:
            raise ValueError(f"Voice must be 1-6, got {voice}")
        if not 1 <= channel <= 16:
            raise ValueError(f"Channel must be 1-16, got {channel}")
        self._data[MIDI_CH_OFFSET + voice - 1] = channel

    def get_midi_note(self, voice: int) -> int:
        """
        Get MIDI note for a voice.

        Args:
            voice: Voice number (1-6).

        Returns:
            MIDI note (0-127, where C-4=48 in LXR numbering).
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 1 <= voice <= 6:
            raise ValueError(f"Voice must be 1-6, got {voice}")
        return self._data[MIDI_NOTE_OFFSET + voice - 1]

    def set_midi_note(self, voice: int, note: int):
        """
        Set MIDI note for a voice.

        Args:
            voice: Voice number (1-6).
            note: MIDI note (0-127).
        """
        if self._data is None:
            raise ValueError("Config not initialized")
        if not 1 <= voice <= 6:
            raise ValueError(f"Voice must be 1-6, got {voice}")
        if not 0 <= note <= 127:
            raise ValueError(f"Note must be 0-127, got {note}")
        self._data[MIDI_NOTE_OFFSET + voice - 1] = note

    def to_dict(self) -> dict:
        """Export config to a dictionary."""
        return {
            'bpm': self.bpm,
            'global_midi_channel': self.global_midi_channel,
            'midi_channels': [self.get_midi_channel(i) for i in range(1, 7)],
            'midi_notes': [self.get_midi_note(i) for i in range(1, 7)],
        }

    def __repr__(self) -> str:
        if self._data is None:
            return "GlobalConfig(uninitialized)"
        return f"GlobalConfig(bpm={self.bpm})"

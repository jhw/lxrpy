"""
LXR-02 Pattern file handling.

Pattern files (.PAT) are 3663 bytes containing:
- 8-byte header (reserved/name)
- 6-byte magic "PatV03"
- 7 voice sections (512 bytes each = 448 step data + 64 flam+shift)
- Step triggers (56 bytes, 8 per voice)
- 1 byte unknown
- Pattern lengths (7 bytes, one per voice)
- Kit index (1 byte)

Each voice has 64 steps, each step is 7 bytes.
"""
import os
import sys
from typing import List, Optional

from .enums import FlamAmount


PATTERN_SIZE = 3663
MAGIC = b"PatV03"
MAGIC_OFFSET = 8
STEPS_PER_VOICE = 64
STEP_SIZE = 7
VOICE_SECTION_SIZE = 512  # 448 step data + 64 flam+shift


# Voice base offsets (V1-V7)
VOICE_STEP_BASES = [0x0E, 0x20E, 0x40E, 0x60E, 0x80E, 0xA0E, 0xC0E]
VOICE_FLAM_BASES = [0x1CE, 0x3CE, 0x5CE, 0x7CE, 0x9CE, 0xBCE, 0xDCE]

# Trigger offsets (8 bytes per voice, little-endian bitmask, V1-V7)
TRIGGER_BASES = [0x0E0E, 0x0E16, 0x0E1E, 0x0E26, 0x0E2E, 0x0E36, 0x0E3E]

# Other offsets
MIX_LEN_OFFSET = 0x0E47  # 3655 - pattern length per voice (7 bytes)
KIT_INDEX_OFFSET = 0x0E4E  # 3662 - kit index (last byte)


class Step:
    """
    Represents a single step in a pattern voice.

    Step data is 7 bytes:
    - Byte 0: Velocity (bits 0-6) + flag (bit 7)
    - Byte 1: Probability (0-100)
    - Byte 2: Note (0-127, MIDI style where C0=0)
    - Bytes 3-6: Unknown (possibly automation)

    Flam and shift are stored separately (packed byte).
    """

    def __init__(self, pattern: 'Pattern', voice_num: int, step_num: int):
        """
        Initialize a step reference.

        Args:
            pattern: Parent Pattern object.
            voice_num: Voice number (1-7).
            step_num: Step number (1-64).
        """
        if not 1 <= voice_num <= 7:
            raise ValueError(f"Voice number must be 1-7, got {voice_num}")
        if not 1 <= step_num <= 64:
            raise ValueError(f"Step number must be 1-64, got {step_num}")

        self._pattern = pattern
        self._voice_num = voice_num
        self._step_num = step_num
        self._voice_idx = voice_num - 1
        self._step_idx = step_num - 1

        # Calculate offsets
        self._step_offset = VOICE_STEP_BASES[self._voice_idx] + (self._step_idx * STEP_SIZE)
        self._flam_offset = VOICE_FLAM_BASES[self._voice_idx] + self._step_idx

    @property
    def voice_num(self) -> int:
        """Voice number (1-7)."""
        return self._voice_num

    @property
    def step_num(self) -> int:
        """Step number (1-64)."""
        return self._step_num

    @property
    def velocity(self) -> int:
        """Step velocity (0-127)."""
        return self._pattern._data[self._step_offset] & 0x7F

    @velocity.setter
    def velocity(self, value: int):
        if not 0 <= value <= 127:
            raise ValueError(f"Velocity must be 0-127, got {value}")
        # Preserve flag bit
        flag = self._pattern._data[self._step_offset] & 0x80
        self._pattern._data[self._step_offset] = flag | value

    @property
    def velocity_flag(self) -> bool:
        """Velocity flag bit (bit 7, purpose unknown)."""
        return bool(self._pattern._data[self._step_offset] & 0x80)

    @velocity_flag.setter
    def velocity_flag(self, value: bool):
        vel = self._pattern._data[self._step_offset] & 0x7F
        if value:
            self._pattern._data[self._step_offset] = vel | 0x80
        else:
            self._pattern._data[self._step_offset] = vel

    @property
    def probability(self) -> int:
        """Step probability (0-100)."""
        return self._pattern._data[self._step_offset + 1]

    @probability.setter
    def probability(self, value: int):
        if not 0 <= value <= 100:
            raise ValueError(f"Probability must be 0-100, got {value}")
        self._pattern._data[self._step_offset + 1] = value

    @property
    def note(self) -> int:
        """Step note (0-127, MIDI style where C0=0)."""
        return self._pattern._data[self._step_offset + 2]

    @note.setter
    def note(self, value: int):
        if not 0 <= value <= 127:
            raise ValueError(f"Note must be 0-127, got {value}")
        self._pattern._data[self._step_offset + 2] = value

    @property
    def flam(self) -> FlamAmount:
        """Step flam amount."""
        packed = self._pattern._data[self._flam_offset]
        flam_val = packed & 0x0F
        try:
            return FlamAmount(flam_val)
        except ValueError:
            return FlamAmount.OFF

    @flam.setter
    def flam(self, value):
        if isinstance(value, FlamAmount):
            flam_val = value.value
        elif isinstance(value, int):
            if not 0 <= value <= 5:
                raise ValueError(f"Flam must be 0-5, got {value}")
            flam_val = value
        else:
            raise ValueError(f"Expected FlamAmount or int, got {type(value)}")

        packed = self._pattern._data[self._flam_offset]
        shift_encoded = packed >> 4
        self._pattern._data[self._flam_offset] = (shift_encoded << 4) | flam_val

    @property
    def shift(self) -> int:
        """Step shift (-7 to +7)."""
        packed = self._pattern._data[self._flam_offset]
        shift_encoded = packed >> 4
        return shift_encoded - 7

    @shift.setter
    def shift(self, value: int):
        if not -7 <= value <= 7:
            raise ValueError(f"Shift must be -7 to +7, got {value}")
        shift_encoded = value + 7
        packed = self._pattern._data[self._flam_offset]
        flam_val = packed & 0x0F
        self._pattern._data[self._flam_offset] = (shift_encoded << 4) | flam_val

    def to_dict(self) -> dict:
        """Export step to a dictionary."""
        return {
            'step_num': self._step_num,
            'velocity': self.velocity,
            'probability': self.probability,
            'note': self.note,
            'flam': self.flam.name,
            'shift': self.shift,
        }


class VoicePattern:
    """
    Represents the pattern data for a single voice.

    Provides access to step triggers, step data, and pattern length.
    """

    def __init__(self, pattern: 'Pattern', voice_num: int):
        """
        Initialize a voice pattern reference.

        Args:
            pattern: Parent Pattern object.
            voice_num: Voice number (1-7).
        """
        if not 1 <= voice_num <= 7:
            raise ValueError(f"Voice number must be 1-7, got {voice_num}")

        self._pattern = pattern
        self._voice_num = voice_num
        self._voice_idx = voice_num - 1
        self._steps = {}

    @property
    def voice_num(self) -> int:
        """Voice number (1-7)."""
        return self._voice_num

    @property
    def length(self) -> int:
        """Pattern length for this voice (1-64)."""
        return self._pattern._data[MIX_LEN_OFFSET + self._voice_idx]

    @length.setter
    def length(self, value: int):
        if not 1 <= value <= 64:
            raise ValueError(f"Length must be 1-64, got {value}")
        self._pattern._data[MIX_LEN_OFFSET + self._voice_idx] = value

    def step(self, num: int) -> Step:
        """
        Get a Step object for accessing step parameters.

        Args:
            num: Step number (1-64).

        Returns:
            Step object.
        """
        if num not in self._steps:
            self._steps[num] = Step(self._pattern, self._voice_num, num)
        return self._steps[num]

    def _get_triggers_bytes(self) -> bytearray:
        """Get the 8-byte trigger bitmask for this voice."""
        base = TRIGGER_BASES[self._voice_idx]
        return self._pattern._data[base:base + 8]

    def _set_triggers_bytes(self, data: bytes):
        """Set the 8-byte trigger bitmask for this voice."""
        if len(data) != 8:
            raise ValueError("Trigger data must be 8 bytes")
        base = TRIGGER_BASES[self._voice_idx]
        self._pattern._data[base:base + 8] = data

    def get_triggers(self) -> List[int]:
        """
        Get list of triggered step numbers (1-64).

        Returns:
            List of step numbers that have triggers enabled.
        """
        trigger_bytes = self._get_triggers_bytes()
        # Convert little-endian bytes to 64-bit int
        trigger_bits = int.from_bytes(trigger_bytes, 'little')
        triggers = []
        for i in range(64):
            if trigger_bits & (1 << i):
                triggers.append(i + 1)  # 1-indexed
        return triggers

    def set_triggers(self, steps: List[int]):
        """
        Set which steps are triggered.

        Args:
            steps: List of step numbers (1-64) to trigger.
        """
        trigger_bits = 0
        for step in steps:
            if not 1 <= step <= 64:
                raise ValueError(f"Step must be 1-64, got {step}")
            trigger_bits |= (1 << (step - 1))
        trigger_bytes = trigger_bits.to_bytes(8, 'little')
        self._set_triggers_bytes(trigger_bytes)

    def set_trigger(self, step: int, enabled: bool = True):
        """
        Enable or disable a single step trigger.

        Args:
            step: Step number (1-64).
            enabled: Whether to enable the trigger.
        """
        if not 1 <= step <= 64:
            raise ValueError(f"Step must be 1-64, got {step}")
        trigger_bytes = self._get_triggers_bytes()
        trigger_bits = int.from_bytes(trigger_bytes, 'little')
        if enabled:
            trigger_bits |= (1 << (step - 1))
        else:
            trigger_bits &= ~(1 << (step - 1))
        self._set_triggers_bytes(trigger_bits.to_bytes(8, 'little'))

    def is_triggered(self, step: int) -> bool:
        """
        Check if a step is triggered.

        Args:
            step: Step number (1-64).

        Returns:
            True if step is triggered.
        """
        if not 1 <= step <= 64:
            raise ValueError(f"Step must be 1-64, got {step}")
        trigger_bytes = self._get_triggers_bytes()
        trigger_bits = int.from_bytes(trigger_bytes, 'little')
        return bool(trigger_bits & (1 << (step - 1)))

    def clear_all_triggers(self):
        """Clear all step triggers."""
        self._set_triggers_bytes(bytes(8))

    def to_dict(self) -> dict:
        """Export voice pattern to a dictionary."""
        triggers = self.get_triggers()
        return {
            'voice_num': self._voice_num,
            'length': self.length,
            'triggers': triggers,
            'steps': [self.step(s).to_dict() for s in triggers]
        }


class Pattern:
    """
    Represents an LXR-02 pattern file (.PAT).

    Pattern files are 3663 bytes containing step sequencer data for 7 voices.
    Always initialize from a template or existing file to preserve unmapped bytes.

    Example:
        # Load from file
        pattern = Pattern.from_file('my_pattern.PAT')

        # Initialize from template
        pattern = Pattern.init()

        # Access voice patterns
        v1 = pattern.voice(1)
        v1.length = 16
        v1.set_triggers([1, 5, 9, 13])  # 4-on-the-floor

        # Modify step data
        step = v1.step(1)
        step.velocity = 127
        step.note = 36  # C2 (kick)

        # Set associated kit
        pattern.kit_index = 0

        # Save
        pattern.save('new_pattern.PAT')
    """

    def __init__(self, data: bytes = None):
        """
        Initialize a Pattern from binary data.

        Args:
            data: Raw 3663-byte pattern data. If None, must use init() or from_file().
        """
        if data is not None:
            if len(data) != PATTERN_SIZE:
                raise ValueError(f"Pattern data must be {PATTERN_SIZE} bytes, got {len(data)}")
            # Verify magic
            if data[MAGIC_OFFSET:MAGIC_OFFSET + 6] != MAGIC:
                raise ValueError(f"Invalid pattern magic, expected {MAGIC!r}")
            self._data = bytearray(data)
        else:
            self._data = None
        self._voices = {}

    @classmethod
    def init(cls, template_name: str = None) -> 'Pattern':
        """
        Initialize a new Pattern from a template.

        Args:
            template_name: Optional template name (without extension).
                          If None, uses default TEMPLATE.PAT.

        Returns:
            New Pattern instance.
        """
        template_filename = f"{template_name}.PAT" if template_name else "TEMPLATE.PAT"
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
    def from_file(cls, filename: str) -> 'Pattern':
        """
        Load a Pattern from a file.

        Args:
            filename: Path to .PAT file.

        Returns:
            Pattern instance.
        """
        with open(filename, 'rb') as f:
            data = f.read()
        return cls(data)

    def save(self, filename: str):
        """
        Save the Pattern to a file.

        Args:
            filename: Path to save .PAT file.
        """
        if self._data is None:
            raise ValueError("Pattern not initialized")
        with open(filename, 'wb') as f:
            f.write(self._data)

    def to_bytes(self) -> bytes:
        """Return the raw pattern data as bytes."""
        if self._data is None:
            raise ValueError("Pattern not initialized")
        return bytes(self._data)

    def clone(self) -> 'Pattern':
        """Create a deep copy of this Pattern."""
        if self._data is None:
            raise ValueError("Pattern not initialized")
        return Pattern(bytes(self._data))

    @property
    def kit_index(self) -> int:
        """Kit/SND file index (0-63)."""
        if self._data is None:
            raise ValueError("Pattern not initialized")
        return self._data[KIT_INDEX_OFFSET]

    @kit_index.setter
    def kit_index(self, value: int):
        if self._data is None:
            raise ValueError("Pattern not initialized")
        if not 0 <= value <= 63:
            raise ValueError(f"Kit index must be 0-63, got {value}")
        self._data[KIT_INDEX_OFFSET] = value

    def voice(self, num: int) -> VoicePattern:
        """
        Get a VoicePattern object for accessing voice pattern data.

        Args:
            num: Voice number (1-7).

        Returns:
            VoicePattern object.
        """
        if self._data is None:
            raise ValueError("Pattern not initialized")
        if num not in self._voices:
            self._voices[num] = VoicePattern(self, num)
        return self._voices[num]

    def copy_voice_from(self, source_pattern: 'Pattern', source_voice: int, dest_voice: int):
        """
        Copy all voice pattern data from another pattern.

        This copies the full binary data for the voice, including step data,
        triggers, and pattern length.

        Args:
            source_pattern: Source Pattern to copy from.
            source_voice: Source voice number (1-7).
            dest_voice: Destination voice number (1-7).
        """
        if self._data is None or source_pattern._data is None:
            raise ValueError("Pattern not initialized")
        if not 1 <= source_voice <= 7:
            raise ValueError(f"Source voice must be 1-7, got {source_voice}")
        if not 1 <= dest_voice <= 7:
            raise ValueError(f"Dest voice must be 1-7, got {dest_voice}")

        src_idx = source_voice - 1
        dst_idx = dest_voice - 1

        # Copy step data (448 bytes)
        src_step_base = VOICE_STEP_BASES[src_idx]
        dst_step_base = VOICE_STEP_BASES[dst_idx]
        self._data[dst_step_base:dst_step_base + 448] = source_pattern._data[src_step_base:src_step_base + 448]

        # Copy flam+shift data (64 bytes)
        src_flam_base = VOICE_FLAM_BASES[src_idx]
        dst_flam_base = VOICE_FLAM_BASES[dst_idx]
        self._data[dst_flam_base:dst_flam_base + 64] = source_pattern._data[src_flam_base:src_flam_base + 64]

        # Copy triggers (8 bytes)
        src_trig_base = TRIGGER_BASES[src_idx]
        dst_trig_base = TRIGGER_BASES[dst_idx]
        self._data[dst_trig_base:dst_trig_base + 8] = source_pattern._data[src_trig_base:src_trig_base + 8]

        # Copy pattern length (1 byte)
        self._data[MIX_LEN_OFFSET + dst_idx] = source_pattern._data[MIX_LEN_OFFSET + src_idx]

    def to_dict(self) -> dict:
        """Export pattern to a dictionary."""
        return {
            'kit_index': self.kit_index,
            'voices': [self.voice(i).to_dict() for i in range(1, 8)]
        }

    def __repr__(self) -> str:
        if self._data is None:
            return "Pattern(uninitialized)"
        return f"Pattern(kit={self.kit_index})"


def format_pattern_filename(index: int, name: str = "") -> str:
    """
    Format a pattern filename for the LXR-02 SD card.

    The LXR-02 uses the format: NN-XXXXX.PAT
    where NN is the 2-digit index (00-63) and XXXXX is an optional 5-character name.

    Args:
        index: Pattern index (0-63).
        name: Optional pattern name (will be truncated to 5 characters, uppercased).

    Returns:
        Formatted filename.
    """
    if not 0 <= index <= 63:
        raise ValueError(f"Pattern index must be 0-63, got {index}")
    short_name = name[:5].upper() if name else ""
    return f"{index:02d}-{short_name}.PAT"

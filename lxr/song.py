"""
LXR-02 Song file handling.

Song files (.SNG) are 72 bytes containing:
- 8-byte song name
- 64 song positions, one byte each:
  - 0-63: pattern index to play
  - 64 (SONG_END): stop playback
  - 65 (SONG_LOOP): jump back to the first position

Unused positions are filled with SONG_END.
"""
from typing import List


SONG_NAME_SIZE = 8
SONG_LENGTH = 64
SONG_SIZE = SONG_NAME_SIZE + SONG_LENGTH
SONG_END = 64
SONG_LOOP = 65


class Song:
    """
    Represents an LXR-02 song file (.SNG): a list of patterns played in order.

    Example:
        song = Song()
        song.name = "MYSONG"
        song.set_patterns([0, 0, 1, 2], loop=True)
        song.save('00-MYSON.SNG')

        song = Song.from_file('00-MYSON.SNG')
        song.patterns  # [0, 0, 1, 2]
        song.loop      # True
    """

    def __init__(self, data: bytes = None):
        """
        Initialize a Song from binary data.

        Args:
            data: Raw 72-byte song data. If None, creates an empty song.
        """
        if data is None:
            data = bytes(SONG_NAME_SIZE) + bytes([SONG_END] * SONG_LENGTH)
        if len(data) != SONG_SIZE:
            raise ValueError(f"Song data must be {SONG_SIZE} bytes, got {len(data)}")
        self._data = bytearray(data)

    @classmethod
    def from_file(cls, filename: str) -> 'Song':
        """
        Load a Song from a file.

        Args:
            filename: Path to .SNG file.

        Returns:
            Song instance.
        """
        with open(filename, 'rb') as f:
            data = f.read()
        return cls(data)

    def save(self, filename: str):
        """
        Save the Song to a file.

        Args:
            filename: Path to save .SNG file.
        """
        with open(filename, 'wb') as f:
            f.write(self._data)

    def to_bytes(self) -> bytes:
        """Return the raw song data as bytes."""
        return bytes(self._data)

    def clone(self) -> 'Song':
        """Create a deep copy of this Song."""
        return Song(bytes(self._data))

    @property
    def name(self) -> str:
        """Song name (up to 8 characters)."""
        return self._data[0:SONG_NAME_SIZE].decode('ascii', errors='replace').rstrip('\x00 ')

    @name.setter
    def name(self, value: str):
        name_bytes = value[:SONG_NAME_SIZE].encode('ascii', errors='replace')
        self._data[0:SONG_NAME_SIZE] = name_bytes.ljust(SONG_NAME_SIZE, b'\x00')

    @property
    def positions(self) -> List[int]:
        """All 64 raw song positions, including SONG_END/SONG_LOOP markers."""
        return list(self._data[SONG_NAME_SIZE:])

    @property
    def patterns(self) -> List[int]:
        """Pattern indices played, up to the first SONG_END/SONG_LOOP marker."""
        result = []
        for value in self.positions:
            if value >= SONG_END:
                break
            result.append(value)
        return result

    @property
    def loop(self) -> bool:
        """True if the song loops back to the start instead of stopping."""
        for value in self.positions:
            if value >= SONG_END:
                return value == SONG_LOOP
        return False

    def set_patterns(self, patterns: List[int], loop: bool = False):
        """
        Set the patterns played by the song.

        Args:
            patterns: Pattern indices (0-63) in play order. Up to 64, or 63
                      when loop is True (the loop marker takes a position).
            loop: If True, return to the start after the last pattern;
                  otherwise stop.
        """
        limit = SONG_LENGTH - 1 if loop else SONG_LENGTH
        if len(patterns) > limit:
            raise ValueError(f"Song can hold at most {limit} patterns, got {len(patterns)}")
        for index in patterns:
            if not 0 <= index <= 63:
                raise ValueError(f"Pattern index must be 0-63, got {index}")
        positions = list(patterns)
        if loop:
            positions.append(SONG_LOOP)
        positions += [SONG_END] * (SONG_LENGTH - len(positions))
        self._data[SONG_NAME_SIZE:] = bytes(positions)

    def to_dict(self) -> dict:
        """Export song to a dictionary."""
        return {
            'name': self.name,
            'patterns': self.patterns,
            'loop': self.loop,
        }

    def __repr__(self) -> str:
        return f"Song('{self.name}', patterns={len(self.patterns)})"


def format_song_filename(index: int, name: str = "") -> str:
    """
    Format a song filename for the LXR-02 SD card.

    The LXR-02 uses the format: NN-XXXXX.SNG
    where NN is the 2-digit index (00-63) and XXXXX is an optional 5-character name.

    Args:
        index: Song index (0-63).
        name: Optional song name (will be truncated to 5 characters, uppercased).

    Returns:
        Formatted filename.
    """
    if not 0 <= index <= 63:
        raise ValueError(f"Song index must be 0-63, got {index}")
    short_name = name[:5].upper() if name else ""
    return f"{index:02d}-{short_name}.SNG"

"""
LXR-02 SD card project utilities.

Provides functions for working with LXR-02 projects on the SD card:
- Reading/writing project names (PRJ.NFO)
- Loading kits from project directories
- Finding populated and empty project slots
- MIDI note name conversion
"""

import os

from .kit import Kit


NUM_SLOTS = 64
DEFAULT_NAMES = ['Initkit', 'Empty', '']


def note_name(midi_note):
    """Convert MIDI note number to name (e.g. 60 -> C4).

    Args:
        midi_note: MIDI note number (0-127).

    Returns:
        Note name string (e.g. "C4", "F#3").
    """
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi_note // 12) - 1
    return f"{names[midi_note % 12]}{octave}"


def read_project_name(proj_dir):
    """Read project name from PRJ.NFO.

    Args:
        proj_dir: Path to project directory.

    Returns:
        Project name string, or empty string if not found.
    """
    prj_nfo = os.path.join(proj_dir, 'PRJ.NFO')
    if os.path.exists(prj_nfo):
        return open(prj_nfo, 'rb').read().decode('latin-1', errors='replace').strip('\x00')
    return ''


def write_project_name(proj_dir, name):
    """Write project name to PRJ.NFO.

    Args:
        proj_dir: Path to project directory.
        name: Project name (truncated to 8 characters).
    """
    prj_nfo = os.path.join(proj_dir, 'PRJ.NFO')
    name_bytes = name[:8].ljust(8, '\x00').encode('latin-1')
    with open(prj_nfo, 'wb') as f:
        f.write(name_bytes)


def load_kit(proj_dir, index):
    """Load a specific kit by index from a project directory.

    Kit files are named NN-XXXXX.SND where NN is the 2-digit index.

    Args:
        proj_dir: Path to project directory.
        index: Kit index (0-63).

    Returns:
        Kit object, or None if not found.
    """
    for f in sorted(os.listdir(proj_dir)):
        if not f.endswith('.SND'):
            continue
        try:
            idx = int(f[:2])
        except ValueError:
            continue
        if idx == index:
            return Kit.from_file(os.path.join(proj_dir, f))
    return None


def load_kits(proj_dir, exclude_defaults=True):
    """Load all kits from a project directory.

    Args:
        proj_dir: Path to project directory.
        exclude_defaults: If True, skip kits with default names
                         ('Initkit', 'Empty', '').

    Returns:
        List of Kit objects.
    """
    kits = []
    for f in sorted(os.listdir(proj_dir)):
        if not f.endswith('.SND'):
            continue
        try:
            kit = Kit.from_file(os.path.join(proj_dir, f))
            if exclude_defaults and kit.name in DEFAULT_NAMES:
                continue
            kits.append(kit)
        except Exception:
            pass
    return kits


def is_populated(proj_dir):
    """Check if a project directory contains any kit files.

    Args:
        proj_dir: Path to project directory.

    Returns:
        True if the directory contains at least one .SND file.
    """
    return any(f.endswith('.SND') for f in os.listdir(proj_dir))


def find_empty_slot(sd_path, start=6):
    """Find the first empty project slot on the SD card.

    A slot is considered empty if the directory doesn't exist or
    contains no .SND files.

    Args:
        sd_path: Path to SD card mount point.
        start: First slot to check (default 6, skipping source projects 0-5).

    Returns:
        Slot number (int), or None if no empty slots available.
    """
    for i in range(start, NUM_SLOTS):
        proj_dir = os.path.join(sd_path, f'PROJ{i:02d}')
        if not os.path.exists(proj_dir):
            return i
        if not any(f.endswith('.SND') for f in os.listdir(proj_dir)):
            return i
    return None

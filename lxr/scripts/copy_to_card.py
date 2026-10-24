#!/usr/bin/env python3
"""
Copy kit, pattern and song files to the LXR-02 SD card.

This script copies .SND, .PAT and .SNG files to a specified project on the SD
card, with proper filename formatting and index management.

The LXR loads files by index (NN-*.EXT), so any existing file with the same
index is treated as a conflict and replaced with --force, whatever its name.

Usage:
    # Copy a kit to project 00 at index 10
    lxr-copy kit.SND --project 0 --index 10 --name MYKICK

    # Copy a pattern to project 00 at index 10
    lxr-copy pattern.PAT --project 0 --index 10 --name MYPAT

    # Copy multiple files
    lxr-copy kit1.SND kit2.SND --project 0 --start-index 10

    # Copy and auto-increment index
    lxr-copy *.SND --project 0 --start-index 0
"""

import argparse
import os
import shutil
import sys
from pathlib import Path


# SD Card Configuration
DEFAULT_SD_PATH = '/Volumes/LXR'


def check_sd_card_mounted(sd_path):
    """Check if the SD card is mounted at the expected path."""
    return os.path.exists(sd_path) and os.path.isdir(sd_path)


def get_project_path(sd_path, project_num):
    """Get the project directory path."""
    return Path(sd_path) / f"PROJ{project_num:02d}"


def format_filename(index, name, extension):
    """
    Format a filename for the LXR-02 SD card.

    Format: NN-XXXXX.EXT (5-character name limit)
    """
    if not 0 <= index <= 63:
        raise ValueError(f"Index must be 0-63, got {index}")
    short_name = name[:5].upper() if name else ""
    return f"{index:02d}-{short_name}{extension}"


def find_index_conflicts(project_path, index, extension):
    """
    Find existing files in a project that use the given index and extension.

    The firmware opens files with a wildcard (NN-*.EXT) and takes the first
    match, so two files with the same index make the loaded one ambiguous.

    Returns:
        List of Path objects.
    """
    prefix = f"{index:02d}-"
    return sorted(
        f for f in project_path.iterdir()
        if f.is_file() and f.name.upper().startswith(prefix) and f.suffix.upper() == extension
    )


def copy_file(src_path, dest_path, force=False):
    """
    Copy a file to the destination, replacing any file with the same index.

    Args:
        src_path: Source file path
        dest_path: Destination file path (NN-NAME.EXT)
        force: Overwrite/remove existing files with the same index

    Returns:
        Tuple of (success, message)
    """
    index = int(dest_path.name[:2])
    conflicts = find_index_conflicts(dest_path.parent, index, dest_path.suffix.upper())
    if conflicts and not force:
        names = ', '.join(f.name for f in conflicts)
        return False, f"Index {index:02d} already used by {names} (use --force to replace)"

    try:
        for f in conflicts:
            if f.name != dest_path.name:
                f.unlink()
        shutil.copy2(src_path, dest_path)
        replaced = [f.name for f in conflicts if f.name != dest_path.name]
        suffix = f" (replaced {', '.join(replaced)})" if replaced else ""
        return True, f"Copied to {dest_path.name}{suffix}"
    except Exception as e:
        return False, f"Failed to copy: {e}"


def main():
    parser = argparse.ArgumentParser(
        description='Copy files to LXR-02 SD card',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Copy a single kit
  %(prog)s mykit.SND --project 0 --index 10 --name KICK

  # Copy multiple kits starting at index 20
  %(prog)s kit1.SND kit2.SND --project 0 --start-index 20

  # Copy all SND files to project 1
  %(prog)s *.SND --project 1 --start-index 0

  # Force overwrite existing files
  %(prog)s mykit.SND --project 0 --index 10 --force

Filename format:
  NN-XXXXX.SND (kits)
  NN-XXXXX.PAT (patterns)
  NN-XXXXX.SNG (songs)

  Where NN is 00-63 and XXXXX is up to 5 characters.

Notes:
  - Project must exist on SD card (PROJ00-PROJ63)
  - Index must be 0-63
  - Name is truncated to 5 characters and uppercased
  - An existing file with the same index is a conflict, whatever its name
  - Files appear on the LXR after loading the project; at power-on it restores
    its working state from /TMP instead
        """
    )

    parser.add_argument('files', nargs='+', help='Files to copy (.SND, .PAT or .SNG)')
    parser.add_argument('--project', type=int, required=True,
                        help='Project number (0-63)')
    parser.add_argument('--index', type=int,
                        help='File index (0-63) for single file')
    parser.add_argument('--start-index', type=int, default=0,
                        help='Starting index for multiple files (default: 0)')
    parser.add_argument('--name', help='Name for the file (5 chars max)')
    parser.add_argument('--sd-path', default=DEFAULT_SD_PATH,
                        help=f'SD card mount point (default: {DEFAULT_SD_PATH})')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite existing files')

    args = parser.parse_args()

    try:
        print("LXR-02 File Copy")
        print("=" * 70)
        print(f"SD card path: {args.sd_path}")
        print(f"Target project: PROJ{args.project:02d}")
        print()

        # Validate project number
        if not 0 <= args.project <= 63:
            print(f"Error: Project must be 0-63, got {args.project}")
            return 1

        # Check SD card is mounted
        if not check_sd_card_mounted(args.sd_path):
            print(f"Error: SD card not found at {args.sd_path}")
            print(f"Please ensure the LXR-02 SD card is mounted.")
            return 1

        # Check project exists
        project_path = get_project_path(args.sd_path, args.project)
        if not project_path.exists():
            print(f"Error: Project PROJ{args.project:02d} does not exist")
            print(f"Available projects:")
            for i in range(64):
                p = get_project_path(args.sd_path, i)
                if p.exists():
                    print(f"  PROJ{i:02d}")
            return 1

        print(f"Project found: {project_path}")
        if not (project_path / 'PRJ.NFO').exists():
            print("Warning: PRJ.NFO missing; the LXR will refuse to load this project")
        print()

        # Process files
        files = [Path(f) for f in args.files]
        current_index = args.index if args.index is not None else args.start_index

        copied = 0
        failed = 0

        for src_file in files:
            if not src_file.exists():
                print(f"  Skip: {src_file.name} (not found)")
                failed += 1
                continue

            # Determine file type
            ext = src_file.suffix.upper()
            if ext not in ['.SND', '.PAT', '.SNG']:
                print(f"  Skip: {src_file.name} (unsupported type)")
                failed += 1
                continue

            # Determine name
            if args.name and len(files) == 1:
                name = args.name
            else:
                # Extract name from source filename (NN-NAME.EXT or just NAME.EXT)
                stem = src_file.stem
                if '-' in stem and stem.split('-')[0].isdigit():
                    name = stem.split('-', 1)[1]
                else:
                    name = stem

            # Format destination filename
            dest_name = format_filename(current_index, name, ext)
            dest_path = project_path / dest_name

            # Copy file
            success, message = copy_file(src_file, dest_path, args.force)
            if success:
                print(f"  OK: {src_file.name} - {message}")
                copied += 1
            else:
                print(f"  FAIL: {src_file.name} - {message}")
                failed += 1

            current_index += 1
            if current_index > 63:
                print(f"  Warning: Index exceeded 63, stopping")
                break

        # Summary
        print()
        print("-" * 70)
        print(f"Copied: {copied}, Failed: {failed}")

        return 0 if failed == 0 else 1

    except KeyboardInterrupt:
        print(f"\n\nAborted by user.")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

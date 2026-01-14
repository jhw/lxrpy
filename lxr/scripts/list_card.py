#!/usr/bin/env python3
"""
List all projects and their contents on the LXR-02 SD card.

This script scans the SD card and displays all projects with their kits
and patterns, showing file counts in a compact format.

Output format:
  PROJ00: N kits, M patterns

Usage:
    # List all projects on SD card
    lxr-list

    # Use custom SD card path
    lxr-list --sd-path /Volumes/LXR

    # Show detailed information
    lxr-list --detailed
"""

import argparse
import os
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


def get_project_files(sd_path, project_num):
    """
    Get information about files in a project.

    Returns:
        Dictionary with 'kits', 'patterns', 'songs' lists of (index, name) tuples
    """
    project_path = get_project_path(sd_path, project_num)

    if not project_path.exists():
        return None

    result = {'kits': [], 'patterns': [], 'songs': []}

    for f in project_path.iterdir():
        if not f.is_file():
            continue

        name = f.name
        if name.endswith('.SND'):
            # Parse NN-NAME.SND
            parts = name[:-4].split('-', 1)
            if len(parts) >= 1 and parts[0].isdigit():
                idx = int(parts[0])
                kit_name = parts[1] if len(parts) > 1 else ""
                result['kits'].append((idx, kit_name))

        elif name.endswith('.PAT'):
            # Parse NN-NAME.PAT
            parts = name[:-4].split('-', 1)
            if len(parts) >= 1 and parts[0].isdigit():
                idx = int(parts[0])
                pat_name = parts[1] if len(parts) > 1 else ""
                result['patterns'].append((idx, pat_name))

        elif name.endswith('.SNG'):
            # Parse NN-NAME.SNG
            parts = name[:-4].split('-', 1)
            if len(parts) >= 1 and parts[0].isdigit():
                idx = int(parts[0])
                song_name = parts[1] if len(parts) > 1 else ""
                result['songs'].append((idx, song_name))

    # Sort by index
    result['kits'].sort(key=lambda x: x[0])
    result['patterns'].sort(key=lambda x: x[0])
    result['songs'].sort(key=lambda x: x[0])

    return result


def format_index_ranges(items):
    """
    Format list of (index, name) tuples as compact ranges.

    Examples:
        [(0, 'A'), (1, 'B'), (2, 'C')] -> "0..2"
        [(0, 'A'), (2, 'B'), (5, 'C')] -> "0, 2, 5"
    """
    if not items:
        return ""

    indices = [item[0] for item in items]

    ranges = []
    start = indices[0]
    end = indices[0]

    for idx in indices[1:]:
        if idx == end + 1:
            end = idx
        else:
            if start == end:
                ranges.append(f"{start:02d}")
            else:
                ranges.append(f"{start:02d}..{end:02d}")
            start = idx
            end = idx

    # Add final range
    if start == end:
        ranges.append(f"{start:02d}")
    else:
        ranges.append(f"{start:02d}..{end:02d}")

    return ", ".join(ranges)


def scan_projects(sd_path):
    """
    Scan all projects on the SD card.

    Returns:
        Dictionary mapping project_num -> project_files dict
    """
    projects = {}

    for project_num in range(64):
        project_path = get_project_path(sd_path, project_num)
        if project_path.exists() and project_path.is_dir():
            files = get_project_files(sd_path, project_num)
            if files and (files['kits'] or files['patterns']):
                projects[project_num] = files

    return projects


def main():
    parser = argparse.ArgumentParser(
        description='List projects on LXR-02 SD card',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all projects on SD card
  %(prog)s

  # Use custom SD card path
  %(prog)s --sd-path /Volumes/LXR

  # Show detailed information
  %(prog)s --detailed

Output format:
  PROJXX: N kits, M patterns

Notes:
  - Only shows projects that contain kits or patterns
  - Scans projects 00-63
        """
    )

    parser.add_argument('--sd-path', default=DEFAULT_SD_PATH,
                        help=f'SD card mount point (default: {DEFAULT_SD_PATH})')
    parser.add_argument('--detailed', action='store_true',
                        help='Show detailed information (kit/pattern names)')

    args = parser.parse_args()

    try:
        print("LXR-02 SD Card Contents")
        print("=" * 70)
        print(f"SD card path: {args.sd_path}")
        print()

        # Check SD card is mounted
        if not check_sd_card_mounted(args.sd_path):
            print(f"Error: SD card not found at {args.sd_path}")
            print(f"Please ensure the LXR-02 SD card is mounted.")
            print(f"\nAvailable volumes:")
            volumes = Path('/Volumes').iterdir() if Path('/Volumes').exists() else []
            for vol in volumes:
                if vol.is_dir():
                    print(f"  - {vol}")
            return 1

        print(f"SD card found")
        print()

        # Scan projects
        print("Scanning projects...")
        projects = scan_projects(args.sd_path)

        if not projects:
            print("\nNo projects with content found on SD card.")
            return 0

        print(f"\nFound {len(projects)} project(s) with content:")
        print("-" * 70)

        total_kits = 0
        total_patterns = 0

        for project_num in sorted(projects.keys()):
            files = projects[project_num]
            kit_count = len(files['kits'])
            pat_count = len(files['patterns'])
            total_kits += kit_count
            total_patterns += pat_count

            if args.detailed:
                print(f"\nPROJ{project_num:02d}:")
                print(f"  Kits ({kit_count}):")
                for idx, name in files['kits']:
                    print(f"    {idx:02d}-{name}")
                print(f"  Patterns ({pat_count}):")
                for idx, name in files['patterns']:
                    print(f"    {idx:02d}-{name}")
            else:
                kit_ranges = format_index_ranges(files['kits'])
                pat_ranges = format_index_ranges(files['patterns'])
                print(f"PROJ{project_num:02d}: {kit_count:2d} kits ({kit_ranges}), {pat_count:2d} patterns ({pat_ranges})")

        # Summary
        print()
        print("-" * 70)
        print(f"Total: {len(projects)} projects, {total_kits} kits, {total_patterns} patterns")

    except KeyboardInterrupt:
        print(f"\n\nAborted by user.")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
Clean projects on the LXR-02 SD card.

This script removes kits and patterns from a project, with options to
clean all files or specific index ranges.

Safety features:
- Requires confirmation before deletion
- Shows what will be deleted before confirming
- Can selectively delete by index range

Usage:
    # Clean all kits and patterns from project 05
    lxr-clean --project 5

    # Clean only kits 10-20 from project 05
    lxr-clean --project 5 --kits-only --start 10 --end 20

    # Clean only patterns from project 05
    lxr-clean --project 5 --patterns-only
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


def get_files_in_range(project_path, extension, start_idx=0, end_idx=63):
    """
    Get list of files in the specified index range.

    Returns:
        List of Path objects for matching files
    """
    files = []
    for f in project_path.iterdir():
        if not f.is_file() or not f.name.endswith(extension):
            continue
        # Parse index from filename (NN-NAME.EXT)
        parts = f.name[:-len(extension)].split('-', 1)
        if parts[0].isdigit():
            idx = int(parts[0])
            if start_idx <= idx <= end_idx:
                files.append(f)
    return sorted(files, key=lambda x: x.name)


def delete_files(files, dry_run=False):
    """
    Delete a list of files.

    Returns:
        Tuple of (deleted_count, error_count)
    """
    deleted = 0
    errors = 0
    for f in files:
        if dry_run:
            print(f"  Would delete: {f.name}")
            deleted += 1
        else:
            try:
                f.unlink()
                print(f"  Deleted: {f.name}")
                deleted += 1
            except Exception as e:
                print(f"  Error deleting {f.name}: {e}")
                errors += 1
    return deleted, errors


def main():
    parser = argparse.ArgumentParser(
        description='Clean LXR-02 SD card projects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean all kits and patterns from project 05
  %(prog)s --project 5

  # Clean only kits from project 05
  %(prog)s --project 5 --kits-only

  # Clean only patterns from project 05
  %(prog)s --project 5 --patterns-only

  # Clean kits 10-20 from project 05
  %(prog)s --project 5 --kits-only --start 10 --end 20

  # Dry run (show what would be deleted)
  %(prog)s --project 5 --dry-run

Safety:
  - Requires typing "clean project XX" to confirm
  - Use --dry-run to preview without deleting
  - Only deletes .SND and .PAT files

Notes:
  - Does not delete GLO.CFG, PRJ.NFO, or .SNG files
  - Use --start and --end to limit which indices are cleaned
        """
    )

    parser.add_argument('--project', type=int, required=True,
                        help='Project number to clean (0-63)')
    parser.add_argument('--sd-path', default=DEFAULT_SD_PATH,
                        help=f'SD card mount point (default: {DEFAULT_SD_PATH})')
    parser.add_argument('--kits-only', action='store_true',
                        help='Only clean kit files (.SND)')
    parser.add_argument('--patterns-only', action='store_true',
                        help='Only clean pattern files (.PAT)')
    parser.add_argument('--start', type=int, default=0,
                        help='Start index for cleaning (default: 0)')
    parser.add_argument('--end', type=int, default=63,
                        help='End index for cleaning (default: 63)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be deleted without deleting')
    parser.add_argument('--force', action='store_true',
                        help='Skip confirmation prompt')

    args = parser.parse_args()

    try:
        print("LXR-02 Project Cleaner")
        print("=" * 70)
        print(f"SD card path: {args.sd_path}")
        print(f"Target project: PROJ{args.project:02d}")
        print(f"Index range: {args.start:02d} - {args.end:02d}")
        print()

        # Validate project number
        if not 0 <= args.project <= 63:
            print(f"Error: Project must be 0-63, got {args.project}")
            return 1

        # Validate index range
        if not 0 <= args.start <= 63:
            print(f"Error: Start index must be 0-63, got {args.start}")
            return 1
        if not 0 <= args.end <= 63:
            print(f"Error: End index must be 0-63, got {args.end}")
            return 1
        if args.start > args.end:
            print(f"Error: Start index must be <= end index")
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
            return 1

        print(f"Project found: {project_path}")
        print()

        # Determine what to clean
        clean_kits = not args.patterns_only
        clean_patterns = not args.kits_only

        # Get files to delete
        kits_to_delete = []
        patterns_to_delete = []

        if clean_kits:
            kits_to_delete = get_files_in_range(project_path, '.SND', args.start, args.end)
        if clean_patterns:
            patterns_to_delete = get_files_in_range(project_path, '.PAT', args.start, args.end)

        total_files = len(kits_to_delete) + len(patterns_to_delete)

        if total_files == 0:
            print("No files to clean in the specified range.")
            return 0

        # Show what will be deleted
        print("Files to be deleted:")
        if kits_to_delete:
            print(f"\n  Kits ({len(kits_to_delete)}):")
            for f in kits_to_delete:
                print(f"    {f.name}")
        if patterns_to_delete:
            print(f"\n  Patterns ({len(patterns_to_delete)}):")
            for f in patterns_to_delete:
                print(f"    {f.name}")

        print(f"\nTotal: {total_files} file(s)")

        if args.dry_run:
            print("\n[DRY RUN - no files deleted]")
            return 0

        # Confirm deletion
        if not args.force:
            confirmation_text = f"clean project {args.project:02d}"
            print(f"\nTo confirm, type exactly: {confirmation_text}")
            user_input = input("Confirmation: ").strip()

            if user_input != confirmation_text:
                print(f"\nConfirmation text does not match. Operation aborted.")
                print(f"  Expected: '{confirmation_text}'")
                print(f"  Got: '{user_input}'")
                return 1

        # Delete files
        print("\nDeleting files...")
        total_deleted = 0
        total_errors = 0

        if kits_to_delete:
            deleted, errors = delete_files(kits_to_delete)
            total_deleted += deleted
            total_errors += errors

        if patterns_to_delete:
            deleted, errors = delete_files(patterns_to_delete)
            total_deleted += deleted
            total_errors += errors

        # Summary
        print()
        print("-" * 70)
        print(f"Deleted: {total_deleted}, Errors: {total_errors}")

        return 0 if total_errors == 0 else 1

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

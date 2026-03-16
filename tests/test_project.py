#!/usr/bin/env python3
"""Tests for LXR-02 SD card project utilities."""

import os
import sys
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lxr import (
    Kit, format_kit_filename,
    note_name, read_project_name, write_project_name,
    load_kit, load_kits, is_populated, find_empty_slot,
)


class TestNoteName(unittest.TestCase):
    """Tests for note_name function."""

    def test_middle_c(self):
        self.assertEqual(note_name(60), "C4")

    def test_c_minus_1(self):
        self.assertEqual(note_name(0), "C-1")

    def test_sharps(self):
        self.assertEqual(note_name(61), "C#4")
        self.assertEqual(note_name(66), "F#4")

    def test_octave_boundaries(self):
        self.assertEqual(note_name(12), "C0")
        self.assertEqual(note_name(24), "C1")
        self.assertEqual(note_name(48), "C3")

    def test_high_note(self):
        self.assertEqual(note_name(127), "G9")


class TestProjectName(unittest.TestCase):
    """Tests for read/write project name."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_write_and_read(self):
        write_project_name(self.tmpdir, "MYPROJ")
        name = read_project_name(self.tmpdir)
        self.assertEqual(name, "MYPROJ")

    def test_truncation(self):
        write_project_name(self.tmpdir, "VERYLONGNAME")
        name = read_project_name(self.tmpdir)
        self.assertEqual(name, "VERYLONG")

    def test_read_missing(self):
        name = read_project_name(self.tmpdir)
        self.assertEqual(name, '')

    def test_nfo_is_8_bytes(self):
        write_project_name(self.tmpdir, "AB")
        nfo_path = os.path.join(self.tmpdir, 'PRJ.NFO')
        with open(nfo_path, 'rb') as f:
            data = f.read()
        self.assertEqual(len(data), 8)


class TestLoadKit(unittest.TestCase):
    """Tests for loading kits from project directories."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create some kit files
        for i, name in [(0, "KICK"), (1, "SNARE"), (5, "HAT")]:
            kit = Kit.init()
            kit.name = name
            filename = format_kit_filename(i, name)
            kit.save(os.path.join(self.tmpdir, filename))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_load_by_index(self):
        kit = load_kit(self.tmpdir, 0)
        self.assertIsNotNone(kit)
        self.assertEqual(kit.name, "KICK")

    def test_load_by_index_middle(self):
        kit = load_kit(self.tmpdir, 5)
        self.assertIsNotNone(kit)
        self.assertEqual(kit.name, "HAT")

    def test_load_missing_index(self):
        kit = load_kit(self.tmpdir, 99)
        self.assertIsNone(kit)

    def test_load_all_kits(self):
        kits = load_kits(self.tmpdir, exclude_defaults=False)
        self.assertEqual(len(kits), 3)

    def test_load_kits_exclude_defaults(self):
        # Add a kit with default name
        kit = Kit.init()
        kit.name = "Initkit"
        kit.save(os.path.join(self.tmpdir, format_kit_filename(10, "INITK")))

        kits = load_kits(self.tmpdir, exclude_defaults=True)
        self.assertEqual(len(kits), 3)  # Initkit excluded

        kits = load_kits(self.tmpdir, exclude_defaults=False)
        self.assertEqual(len(kits), 4)  # Initkit included


class TestIsPopulated(unittest.TestCase):
    """Tests for is_populated function."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_empty_dir(self):
        self.assertFalse(is_populated(self.tmpdir))

    def test_with_kits(self):
        kit = Kit.init()
        kit.save(os.path.join(self.tmpdir, "00-TEST.SND"))
        self.assertTrue(is_populated(self.tmpdir))

    def test_with_non_kit_files(self):
        with open(os.path.join(self.tmpdir, "GLO.CFG"), 'wb') as f:
            f.write(b'\x00' * 30)
        self.assertFalse(is_populated(self.tmpdir))


class TestFindEmptySlot(unittest.TestCase):
    """Tests for find_empty_slot function."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_all_empty(self):
        slot = find_empty_slot(self.tmpdir, start=0)
        self.assertEqual(slot, 0)

    def test_skips_populated(self):
        # Create PROJ00 with a kit
        proj_dir = os.path.join(self.tmpdir, 'PROJ00')
        os.makedirs(proj_dir)
        kit = Kit.init()
        kit.save(os.path.join(proj_dir, "00-TEST.SND"))

        slot = find_empty_slot(self.tmpdir, start=0)
        self.assertEqual(slot, 1)

    def test_empty_dir_counts_as_empty(self):
        # Create PROJ06 with no kits
        proj_dir = os.path.join(self.tmpdir, 'PROJ06')
        os.makedirs(proj_dir)

        slot = find_empty_slot(self.tmpdir, start=6)
        self.assertEqual(slot, 6)

    def test_respects_start(self):
        slot = find_empty_slot(self.tmpdir, start=10)
        self.assertEqual(slot, 10)

    def test_default_start(self):
        slot = find_empty_slot(self.tmpdir)
        self.assertEqual(slot, 6)

    def test_all_full(self):
        # Create all 64 project dirs with kits
        for i in range(64):
            proj_dir = os.path.join(self.tmpdir, f'PROJ{i:02d}')
            os.makedirs(proj_dir)
            kit = Kit.init()
            kit.save(os.path.join(proj_dir, "00-TEST.SND"))

        slot = find_empty_slot(self.tmpdir, start=0)
        self.assertIsNone(slot)


if __name__ == '__main__':
    unittest.main()

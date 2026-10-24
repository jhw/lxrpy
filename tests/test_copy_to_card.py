#!/usr/bin/env python3
"""Tests for the copy_to_card script's file handling."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lxr.scripts.copy_to_card import copy_file, find_index_conflicts


class TestCopyFile(unittest.TestCase):
    """The LXR loads NN-*.EXT, so one file per index must be enforced."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / 'PROJ00'
        self.project.mkdir()
        self.src = self.root / 'new.SND'
        self.src.write_bytes(b'new')

    def tearDown(self):
        self.tmp.cleanup()

    def test_copy_to_empty_slot(self):
        """Copying into an unused index succeeds."""
        ok, _ = copy_file(self.src, self.project / '10-NEW.SND')
        self.assertTrue(ok)
        self.assertEqual((self.project / '10-NEW.SND').read_bytes(), b'new')

    def test_differently_named_file_is_conflict(self):
        """A file with the same index but another name blocks the copy."""
        (self.project / '10-OLD.SND').write_bytes(b'old')
        ok, message = copy_file(self.src, self.project / '10-NEW.SND')
        self.assertFalse(ok)
        self.assertIn('10-OLD.SND', message)
        self.assertFalse((self.project / '10-NEW.SND').exists())

    def test_force_replaces_differently_named_file(self):
        """--force removes the old file so only one index-10 kit remains."""
        (self.project / '10-OLD.SND').write_bytes(b'old')
        ok, _ = copy_file(self.src, self.project / '10-NEW.SND', force=True)
        self.assertTrue(ok)
        self.assertEqual([f.name for f in find_index_conflicts(self.project, 10, '.SND')],
                         ['10-NEW.SND'])

    def test_force_overwrites_same_name(self):
        """--force overwrites a file with the identical name."""
        (self.project / '10-NEW.SND').write_bytes(b'old')
        ok, _ = copy_file(self.src, self.project / '10-NEW.SND', force=True)
        self.assertTrue(ok)
        self.assertEqual((self.project / '10-NEW.SND').read_bytes(), b'new')

    def test_other_types_and_indices_untouched(self):
        """Only same-index files of the same type conflict."""
        (self.project / '10-OLD.PAT').write_bytes(b'pat')
        (self.project / '11-OLD.SND').write_bytes(b'kit')
        ok, _ = copy_file(self.src, self.project / '10-NEW.SND')
        self.assertTrue(ok)
        self.assertTrue((self.project / '10-OLD.PAT').exists())
        self.assertTrue((self.project / '11-OLD.SND').exists())


if __name__ == '__main__':
    unittest.main()

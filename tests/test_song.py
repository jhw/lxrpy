#!/usr/bin/env python3
"""Tests for LXR-02 Song file handling."""

import os
import sys
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lxr import Song, format_song_filename
from lxr.song import SONG_END, SONG_LOOP


class TestSong(unittest.TestCase):
    """Tests for Song class."""

    def test_empty_song(self):
        """A new song is 72 bytes of name plus SONG_END markers."""
        song = Song()
        self.assertEqual(len(song.to_bytes()), 72)
        self.assertEqual(song.name, '')
        self.assertEqual(song.patterns, [])
        self.assertFalse(song.loop)
        self.assertEqual(song.positions, [SONG_END] * 64)

    def test_invalid_size(self):
        """Wrong-sized data raises."""
        with self.assertRaises(ValueError):
            Song(bytes(71))

    def test_name(self):
        """Name is the first 8 bytes."""
        song = Song()
        song.name = "MYSONGNAME"
        self.assertEqual(song.name, "MYSONGNA")
        self.assertEqual(song.to_bytes()[:8], b"MYSONGNA")

    def test_set_patterns_stop(self):
        """Patterns are followed by SONG_END."""
        song = Song()
        song.set_patterns([0, 0, 3, 63])
        self.assertEqual(song.positions[:5], [0, 0, 3, 63, SONG_END])
        self.assertEqual(song.patterns, [0, 0, 3, 63])
        self.assertFalse(song.loop)

    def test_set_patterns_loop(self):
        """Looping songs end with SONG_LOOP."""
        song = Song()
        song.set_patterns([1, 2], loop=True)
        self.assertEqual(song.positions[:4], [1, 2, SONG_LOOP, SONG_END])
        self.assertEqual(song.patterns, [1, 2])
        self.assertTrue(song.loop)

    def test_set_patterns_replaces(self):
        """Setting a shorter list clears the old tail."""
        song = Song()
        song.set_patterns(list(range(10)))
        song.set_patterns([5])
        self.assertEqual(song.positions[1:], [SONG_END] * 63)

    def test_full_song(self):
        """64 patterns fit without a loop marker; 63 with one."""
        song = Song()
        song.set_patterns([0] * 64)
        self.assertEqual(len(song.patterns), 64)
        with self.assertRaises(ValueError):
            song.set_patterns([0] * 64, loop=True)
        song.set_patterns([0] * 63, loop=True)
        self.assertTrue(song.loop)

    def test_invalid_pattern(self):
        """Pattern indices must be 0-63."""
        with self.assertRaises(ValueError):
            Song().set_patterns([64])

    def test_save_and_load(self):
        """Songs round-trip through a file."""
        song = Song()
        song.name = "SET1"
        song.set_patterns([4, 5, 6], loop=True)
        with tempfile.NamedTemporaryFile(suffix='.SNG', delete=False) as tmp:
            try:
                song.save(tmp.name)
                loaded = Song.from_file(tmp.name)
                self.assertEqual(loaded.name, "SET1")
                self.assertEqual(loaded.patterns, [4, 5, 6])
                self.assertTrue(loaded.loop)
            finally:
                os.unlink(tmp.name)

    def test_clone(self):
        """Clones are independent."""
        song = Song()
        song.set_patterns([1])
        clone = song.clone()
        clone.set_patterns([2])
        self.assertEqual(song.patterns, [1])

    def test_to_dict(self):
        """to_dict exports name, patterns and loop."""
        song = Song()
        song.set_patterns([7], loop=True)
        self.assertEqual(song.to_dict(), {'name': '', 'patterns': [7], 'loop': True})


class TestFormatSongFilename(unittest.TestCase):
    """Tests for format_song_filename."""

    def test_format(self):
        """Filenames follow NN-XXXXX.SNG."""
        self.assertEqual(format_song_filename(0, "mysong"), "00-MYSON.SNG")
        self.assertEqual(format_song_filename(12), "12-.SNG")

    def test_invalid_index(self):
        """Index must be 0-63."""
        with self.assertRaises(ValueError):
            format_song_filename(64)


if __name__ == '__main__':
    unittest.main()

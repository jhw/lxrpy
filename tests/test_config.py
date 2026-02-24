#!/usr/bin/env python3
"""Tests for LXR-02 GlobalConfig file handling."""

import os
import sys
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lxr import GlobalConfig


class TestGlobalConfig(unittest.TestCase):
    """Tests for GlobalConfig class."""

    def test_init_from_template(self):
        """Test initializing config from template."""
        config = GlobalConfig.init()
        self.assertIsNotNone(config._data)
        self.assertEqual(len(config._data), 30)

    def test_bpm(self):
        """Test getting and setting BPM."""
        config = GlobalConfig.init()

        config.bpm = 120
        self.assertEqual(config.bpm, 120)

        config.bpm = 1
        self.assertEqual(config.bpm, 1)

        config.bpm = 255
        self.assertEqual(config.bpm, 255)

    def test_bpm_invalid(self):
        """Test invalid BPM raises error."""
        config = GlobalConfig.init()

        with self.assertRaises(ValueError):
            config.bpm = -1
        with self.assertRaises(ValueError):
            config.bpm = 256

    def test_midi_channel(self):
        """Test getting and setting MIDI channel."""
        config = GlobalConfig.init()

        for voice in range(1, 7):
            config.set_midi_channel(voice, voice)
            self.assertEqual(config.get_midi_channel(voice), voice)

        # Test channel range
        config.set_midi_channel(1, 1)
        self.assertEqual(config.get_midi_channel(1), 1)

        config.set_midi_channel(1, 16)
        self.assertEqual(config.get_midi_channel(1), 16)

    def test_midi_channel_invalid(self):
        """Test invalid MIDI channel raises error."""
        config = GlobalConfig.init()

        with self.assertRaises(ValueError):
            config.set_midi_channel(0, 1)  # Invalid voice
        with self.assertRaises(ValueError):
            config.set_midi_channel(7, 1)  # Invalid voice
        with self.assertRaises(ValueError):
            config.set_midi_channel(1, 0)  # Invalid channel
        with self.assertRaises(ValueError):
            config.set_midi_channel(1, 17)  # Invalid channel

    def test_midi_note(self):
        """Test getting and setting MIDI note."""
        config = GlobalConfig.init()

        for voice in range(1, 7):
            note = 36 + voice  # C2 + offset
            config.set_midi_note(voice, note)
            self.assertEqual(config.get_midi_note(voice), note)

        # Test note range
        config.set_midi_note(1, 0)
        self.assertEqual(config.get_midi_note(1), 0)

        config.set_midi_note(1, 127)
        self.assertEqual(config.get_midi_note(1), 127)

    def test_midi_note_invalid(self):
        """Test invalid MIDI note raises error."""
        config = GlobalConfig.init()

        with self.assertRaises(ValueError):
            config.set_midi_note(0, 36)  # Invalid voice
        with self.assertRaises(ValueError):
            config.set_midi_note(7, 36)  # Invalid voice
        with self.assertRaises(ValueError):
            config.set_midi_note(1, -1)  # Invalid note
        with self.assertRaises(ValueError):
            config.set_midi_note(1, 128)  # Invalid note

    def test_clone(self):
        """Test cloning a config."""
        config = GlobalConfig.init()
        config.bpm = 140
        config.set_midi_channel(1, 10)

        clone = config.clone()
        self.assertEqual(clone.bpm, 140)
        self.assertEqual(clone.get_midi_channel(1), 10)

        # Modify clone, original should be unchanged
        clone.bpm = 100
        clone.set_midi_channel(1, 5)
        self.assertEqual(config.bpm, 140)
        self.assertEqual(config.get_midi_channel(1), 10)

    def test_save_and_load(self):
        """Test saving and loading config files."""
        config = GlobalConfig.init()
        config.bpm = 128
        config.set_midi_channel(1, 3)
        config.set_midi_note(1, 48)  # C3

        with tempfile.NamedTemporaryFile(suffix='.CFG', delete=False) as tmp:
            try:
                config.save(tmp.name)

                loaded = GlobalConfig.from_file(tmp.name)
                self.assertEqual(loaded.bpm, 128)
                self.assertEqual(loaded.get_midi_channel(1), 3)
                self.assertEqual(loaded.get_midi_note(1), 48)
            finally:
                os.unlink(tmp.name)

    def test_to_dict(self):
        """Test exporting config to dictionary."""
        config = GlobalConfig.init()
        config.bpm = 120

        d = config.to_dict()
        self.assertEqual(d['bpm'], 120)
        self.assertEqual(len(d['midi_channels']), 6)
        self.assertEqual(len(d['midi_notes']), 6)

    def test_repr(self):
        """Test string representation."""
        config = GlobalConfig.init()
        config.bpm = 120
        self.assertIn('120', repr(config))


if __name__ == '__main__':
    unittest.main()

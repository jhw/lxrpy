#!/usr/bin/env python3
"""Tests for LXR-02 GlobalConfig file handling."""

import os
import sys
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lxr import GlobalConfig
from lxr import MidiRouting, MidiFilter, ClockInPpq, ClockOutPpq, PatternMode


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

    def test_global_midi_channel(self):
        """Test getting and setting global MIDI channel."""
        config = GlobalConfig.init()

        config.global_midi_channel = 1
        self.assertEqual(config.global_midi_channel, 1)

        config.global_midi_channel = 15
        self.assertEqual(config.global_midi_channel, 15)

        config.global_midi_channel = 16
        self.assertEqual(config.global_midi_channel, 16)

    def test_global_midi_channel_invalid(self):
        """Test invalid global MIDI channel raises error."""
        config = GlobalConfig.init()

        with self.assertRaises(ValueError):
            config.global_midi_channel = -1
        with self.assertRaises(ValueError):
            config.global_midi_channel = 17

    def test_global_midi_channel_save_and_load(self):
        """Test global MIDI channel persists through save/load."""
        config = GlobalConfig.init()
        config.global_midi_channel = 10

        with tempfile.NamedTemporaryFile(suffix='.CFG', delete=False) as tmp:
            try:
                config.save(tmp.name)
                loaded = GlobalConfig.from_file(tmp.name)
                self.assertEqual(loaded.global_midi_channel, 10)
            finally:
                os.unlink(tmp.name)

    def test_midi_channel(self):
        """Test getting and setting MIDI channel for voices 1-7."""
        config = GlobalConfig.init()

        for voice in range(1, 8):
            config.set_midi_channel(voice, voice)
            self.assertEqual(config.get_midi_channel(voice), voice)

        # Test channel range
        config.set_midi_channel(1, 1)
        self.assertEqual(config.get_midi_channel(1), 1)

        config.set_midi_channel(1, 16)
        self.assertEqual(config.get_midi_channel(1), 16)

    def test_midi_channel_voice_7(self):
        """Test voice 7 MIDI channel uses separate offset."""
        config = GlobalConfig.init()

        config.set_midi_channel(7, 13)
        self.assertEqual(config.get_midi_channel(7), 13)

        # Ensure voice 7 doesn't interfere with voices 1-6
        for voice in range(1, 7):
            config.set_midi_channel(voice, 1)
        self.assertEqual(config.get_midi_channel(7), 13)

    def test_midi_channel_invalid(self):
        """Test invalid MIDI channel raises error."""
        config = GlobalConfig.init()

        with self.assertRaises(ValueError):
            config.set_midi_channel(0, 1)  # Invalid voice
        with self.assertRaises(ValueError):
            config.set_midi_channel(8, 1)  # Invalid voice
        with self.assertRaises(ValueError):
            config.set_midi_channel(1, 0)  # Invalid channel
        with self.assertRaises(ValueError):
            config.set_midi_channel(1, 17)  # Invalid channel

    def test_midi_note(self):
        """Test getting and setting MIDI note for voices 1-7."""
        config = GlobalConfig.init()

        for voice in range(1, 8):
            note = 36 + voice  # C2 + offset
            config.set_midi_note(voice, note)
            self.assertEqual(config.get_midi_note(voice), note)

        # Test note range
        config.set_midi_note(1, 0)
        self.assertEqual(config.get_midi_note(1), 0)

        config.set_midi_note(1, 127)
        self.assertEqual(config.get_midi_note(1), 127)

    def test_midi_note_voice_7(self):
        """Test voice 7 MIDI note uses separate offset."""
        config = GlobalConfig.init()

        config.set_midi_note(7, 38)
        self.assertEqual(config.get_midi_note(7), 38)

        # Ensure voice 7 doesn't interfere with voices 1-6
        for voice in range(1, 7):
            config.set_midi_note(voice, 60)
        self.assertEqual(config.get_midi_note(7), 38)

    def test_midi_note_invalid(self):
        """Test invalid MIDI note raises error."""
        config = GlobalConfig.init()

        with self.assertRaises(ValueError):
            config.set_midi_note(0, 36)  # Invalid voice
        with self.assertRaises(ValueError):
            config.set_midi_note(8, 36)  # Invalid voice
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
        config.set_midi_note(1, 48)  # C4 (LXR labelling)

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

        config.global_midi_channel = 5

        d = config.to_dict()
        self.assertEqual(d['bpm'], 120)
        self.assertEqual(d['global_midi_channel'], 5)
        self.assertEqual(len(d['midi_channels']), 7)
        self.assertEqual(len(d['midi_notes']), 7)

    def test_repr(self):
        """Test string representation."""
        config = GlobalConfig.init()
        config.bpm = 120
        self.assertIn('120', repr(config))


class TestGlobalSettings(unittest.TestCase):
    """Tests for the remaining GLO.CFG settings mapped from the firmware."""

    def setUp(self):
        self.config = GlobalConfig.init()

    def test_global_midi_channel_all(self):
        """0 means all channels (firmware default)."""
        self.config.global_midi_channel = 0
        self.assertEqual(self.config.global_midi_channel, 0)

    def test_offsets(self):
        """Each setting writes its firmware byte."""
        c = self.config
        c.follow = True
        c.screensaver = False
        c.midi_routing = MidiRouting.M2U
        c.midi_tx_filter = MidiFilter.NOTES | MidiFilter.CC
        c.midi_rx_filter = MidiFilter.NONE
        c.clock_in_ppq = ClockInPpq.PPQ_24
        c.clock_out_ppq = ClockOutPpq.PPQ_48
        c.bar_reset = False
        c.pattern_mode = PatternMode.OFF
        d = c.to_bytes()
        self.assertEqual([d[i] for i in (8, 10, 13, 14, 15, 16, 17, 20, 29)],
                         [1, 0, 4, 5, 0, 1, 5, 0, 0])

    def test_read_back(self):
        """Settings read back as their enum types."""
        c = self.config
        c.midi_routing = MidiRouting.A2M
        c.midi_rx_filter = MidiFilter.SYSTEM
        c.clock_out_ppq = ClockOutPpq.PPQ_16
        self.assertEqual(c.midi_routing, MidiRouting.A2M)
        self.assertEqual(c.midi_rx_filter, MidiFilter.SYSTEM)
        self.assertEqual(c.clock_out_ppq, ClockOutPpq.PPQ_16)

    def test_template_defaults(self):
        """Template matches firmware defaults for these settings."""
        c = self.config
        self.assertEqual(c.midi_tx_filter, MidiFilter.ALL)
        self.assertEqual(c.midi_rx_filter, MidiFilter.ALL)
        self.assertTrue(c.screensaver)
        self.assertTrue(c.bar_reset)
        self.assertEqual(c.pattern_mode, PatternMode.AUTO)
        self.assertEqual(c.to_bytes()[29], 1)

    def test_pattern_mode_transient_value(self):
        """The firmware's internal value 2 reads as AUTO."""
        data = bytearray(self.config.to_bytes())
        data[29] = 2
        self.assertEqual(GlobalConfig(bytes(data)).pattern_mode, PatternMode.AUTO)

    def test_invalid(self):
        """Out-of-range values raise."""
        with self.assertRaises(ValueError):
            self.config.midi_routing = 6
        with self.assertRaises(ValueError):
            self.config.midi_tx_filter = 16
        with self.assertRaises(ValueError):
            self.config.clock_in_ppq = 2

    def test_to_dict(self):
        """to_dict exports the new settings."""
        d = self.config.to_dict()
        for key in ('follow', 'screensaver', 'midi_routing', 'midi_tx_filter',
                    'midi_rx_filter', 'clock_in_ppq', 'clock_out_ppq',
                    'bar_reset', 'pattern_mode'):
            self.assertIn(key, d)


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Tests for LXR-02 Pattern file handling."""

import os
import sys
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lxr import Pattern, VoicePattern, Step, FlamAmount
from lxr import format_pattern_filename


class TestPattern(unittest.TestCase):
    """Tests for Pattern class."""

    def test_init_from_template(self):
        """Test initializing pattern from template."""
        pattern = Pattern.init()
        self.assertIsNotNone(pattern._data)
        self.assertEqual(len(pattern._data), 3663)

    def test_kit_index(self):
        """Test getting and setting kit index."""
        pattern = Pattern.init()

        pattern.kit_index = 10
        self.assertEqual(pattern.kit_index, 10)

        pattern.kit_index = 0
        self.assertEqual(pattern.kit_index, 0)

        pattern.kit_index = 63
        self.assertEqual(pattern.kit_index, 63)

    def test_kit_index_invalid(self):
        """Test invalid kit index raises error."""
        pattern = Pattern.init()

        with self.assertRaises(ValueError):
            pattern.kit_index = -1
        with self.assertRaises(ValueError):
            pattern.kit_index = 64

    def test_voice_access(self):
        """Test accessing voice patterns."""
        pattern = Pattern.init()

        for i in range(1, 7):
            voice = pattern.voice(i)
            self.assertIsInstance(voice, VoicePattern)
            self.assertEqual(voice.voice_num, i)

    def test_clone(self):
        """Test cloning a pattern."""
        pattern = Pattern.init()
        pattern.kit_index = 10
        pattern.voice(1).length = 16

        clone = pattern.clone()
        self.assertEqual(clone.kit_index, 10)
        self.assertEqual(clone.voice(1).length, 16)

        # Modify clone, original should be unchanged
        clone.kit_index = 20
        clone.voice(1).length = 32
        self.assertEqual(pattern.kit_index, 10)
        self.assertEqual(pattern.voice(1).length, 16)

    def test_save_and_load(self):
        """Test saving and loading pattern files."""
        pattern = Pattern.init()
        pattern.kit_index = 5
        pattern.voice(1).set_triggers([1, 5, 9, 13])
        pattern.voice(1).length = 16

        with tempfile.NamedTemporaryFile(suffix='.PAT', delete=False) as tmp:
            try:
                pattern.save(tmp.name)

                loaded = Pattern.from_file(tmp.name)
                self.assertEqual(loaded.kit_index, 5)
                self.assertEqual(loaded.voice(1).get_triggers(), [1, 5, 9, 13])
                self.assertEqual(loaded.voice(1).length, 16)
            finally:
                os.unlink(tmp.name)

    def test_to_dict(self):
        """Test exporting pattern to dictionary."""
        pattern = Pattern.init()
        pattern.kit_index = 5

        d = pattern.to_dict()
        self.assertEqual(d['kit_index'], 5)
        self.assertEqual(len(d['voices']), 6)


class TestVoicePattern(unittest.TestCase):
    """Tests for VoicePattern class."""

    def setUp(self):
        """Set up test pattern."""
        self.pattern = Pattern.init()

    def test_length(self):
        """Test pattern length."""
        v = self.pattern.voice(1)

        v.length = 16
        self.assertEqual(v.length, 16)

        v.length = 32
        self.assertEqual(v.length, 32)

        v.length = 64
        self.assertEqual(v.length, 64)

    def test_length_invalid(self):
        """Test invalid length raises error."""
        v = self.pattern.voice(1)

        with self.assertRaises(ValueError):
            v.length = 0
        with self.assertRaises(ValueError):
            v.length = 65

    def test_set_triggers(self):
        """Test setting step triggers."""
        v = self.pattern.voice(1)

        # 4-on-the-floor
        v.set_triggers([1, 5, 9, 13])
        self.assertEqual(v.get_triggers(), [1, 5, 9, 13])

        # Clear all
        v.set_triggers([])
        self.assertEqual(v.get_triggers(), [])

        # All steps
        all_steps = list(range(1, 17))
        v.set_triggers(all_steps)
        self.assertEqual(v.get_triggers()[:16], all_steps)

    def test_set_trigger_single(self):
        """Test setting individual triggers."""
        v = self.pattern.voice(1)
        v.clear_all_triggers()

        v.set_trigger(1, True)
        self.assertTrue(v.is_triggered(1))
        self.assertFalse(v.is_triggered(2))

        v.set_trigger(5, True)
        self.assertTrue(v.is_triggered(5))

        v.set_trigger(1, False)
        self.assertFalse(v.is_triggered(1))
        self.assertTrue(v.is_triggered(5))

    def test_is_triggered(self):
        """Test checking trigger state."""
        v = self.pattern.voice(1)
        v.set_triggers([1, 3, 5])

        self.assertTrue(v.is_triggered(1))
        self.assertFalse(v.is_triggered(2))
        self.assertTrue(v.is_triggered(3))
        self.assertFalse(v.is_triggered(4))
        self.assertTrue(v.is_triggered(5))

    def test_clear_all_triggers(self):
        """Test clearing all triggers."""
        v = self.pattern.voice(1)
        v.set_triggers([1, 2, 3, 4, 5])
        self.assertEqual(len(v.get_triggers()), 5)

        v.clear_all_triggers()
        self.assertEqual(v.get_triggers(), [])

    def test_step_access(self):
        """Test accessing steps."""
        v = self.pattern.voice(1)

        for i in range(1, 65):
            step = v.step(i)
            self.assertIsInstance(step, Step)
            self.assertEqual(step.step_num, i)

    def test_to_dict(self):
        """Test voice pattern to_dict."""
        v = self.pattern.voice(1)
        v.length = 16
        v.set_triggers([1, 5])

        d = v.to_dict()
        self.assertEqual(d['voice_num'], 1)
        self.assertEqual(d['length'], 16)
        self.assertEqual(d['triggers'], [1, 5])


class TestStep(unittest.TestCase):
    """Tests for Step class."""

    def setUp(self):
        """Set up test pattern."""
        self.pattern = Pattern.init()
        self.step = self.pattern.voice(1).step(1)

    def test_velocity(self):
        """Test step velocity."""
        self.step.velocity = 127
        self.assertEqual(self.step.velocity, 127)

        self.step.velocity = 64
        self.assertEqual(self.step.velocity, 64)

        self.step.velocity = 0
        self.assertEqual(self.step.velocity, 0)

    def test_velocity_invalid(self):
        """Test invalid velocity raises error."""
        with self.assertRaises(ValueError):
            self.step.velocity = -1
        with self.assertRaises(ValueError):
            self.step.velocity = 128

    def test_probability(self):
        """Test step probability."""
        self.step.probability = 100
        self.assertEqual(self.step.probability, 100)

        self.step.probability = 50
        self.assertEqual(self.step.probability, 50)

        self.step.probability = 0
        self.assertEqual(self.step.probability, 0)

    def test_probability_invalid(self):
        """Test invalid probability raises error."""
        with self.assertRaises(ValueError):
            self.step.probability = -1
        with self.assertRaises(ValueError):
            self.step.probability = 101

    def test_note(self):
        """Test step note."""
        self.step.note = 36  # C2
        self.assertEqual(self.step.note, 36)

        self.step.note = 60  # C4
        self.assertEqual(self.step.note, 60)

        self.step.note = 0
        self.assertEqual(self.step.note, 0)

        self.step.note = 127
        self.assertEqual(self.step.note, 127)

    def test_note_invalid(self):
        """Test invalid note raises error."""
        with self.assertRaises(ValueError):
            self.step.note = -1
        with self.assertRaises(ValueError):
            self.step.note = 128

    def test_flam(self):
        """Test step flam."""
        self.step.flam = FlamAmount.OFF
        self.assertEqual(self.step.flam, FlamAmount.OFF)

        self.step.flam = FlamAmount.X2
        self.assertEqual(self.step.flam, FlamAmount.X2)

        self.step.flam = FlamAmount.X8
        self.assertEqual(self.step.flam, FlamAmount.X8)

        # Test setting by int
        self.step.flam = 3
        self.assertEqual(self.step.flam, FlamAmount.X4)

    def test_shift(self):
        """Test step shift."""
        self.step.shift = 0
        self.assertEqual(self.step.shift, 0)

        self.step.shift = -7
        self.assertEqual(self.step.shift, -7)

        self.step.shift = 7
        self.assertEqual(self.step.shift, 7)

    def test_shift_invalid(self):
        """Test invalid shift raises error."""
        with self.assertRaises(ValueError):
            self.step.shift = -8
        with self.assertRaises(ValueError):
            self.step.shift = 8

    def test_flam_shift_independence(self):
        """Test flam and shift are independent (packed byte)."""
        self.step.flam = FlamAmount.X3
        self.step.shift = 5

        self.assertEqual(self.step.flam, FlamAmount.X3)
        self.assertEqual(self.step.shift, 5)

        # Change flam, shift should stay
        self.step.flam = FlamAmount.OFF
        self.assertEqual(self.step.flam, FlamAmount.OFF)
        self.assertEqual(self.step.shift, 5)

        # Change shift, flam should stay
        self.step.shift = -3
        self.assertEqual(self.step.flam, FlamAmount.OFF)
        self.assertEqual(self.step.shift, -3)

    def test_to_dict(self):
        """Test step to_dict."""
        self.step.velocity = 100
        self.step.probability = 80
        self.step.note = 36
        self.step.flam = FlamAmount.X2
        self.step.shift = 3

        d = self.step.to_dict()
        self.assertEqual(d['step_num'], 1)
        self.assertEqual(d['velocity'], 100)
        self.assertEqual(d['probability'], 80)
        self.assertEqual(d['note'], 36)
        self.assertEqual(d['flam'], 'X2')
        self.assertEqual(d['shift'], 3)


class TestCopyVoicePattern(unittest.TestCase):
    """Tests for copying voice patterns between patterns."""

    def test_copy_voice_pattern(self):
        """Test copying voice pattern data."""
        pat1 = Pattern.init()
        pat2 = Pattern.init()

        # Set up source
        pat1.voice(1).length = 16
        pat1.voice(1).set_triggers([1, 5, 9, 13])
        pat1.voice(1).step(1).velocity = 127
        pat1.voice(1).step(1).note = 36

        # Copy to dest
        pat2.copy_voice_from(pat1, 1, 1)

        self.assertEqual(pat2.voice(1).length, 16)
        self.assertEqual(pat2.voice(1).get_triggers(), [1, 5, 9, 13])
        self.assertEqual(pat2.voice(1).step(1).velocity, 127)
        self.assertEqual(pat2.voice(1).step(1).note, 36)

    def test_copy_voice_pattern_different_positions(self):
        """Test copying to different voice position."""
        pat1 = Pattern.init()
        pat2 = Pattern.init()

        pat1.voice(2).length = 32
        pat1.voice(2).set_triggers([1, 3, 5, 7])

        pat2.copy_voice_from(pat1, 2, 4)

        self.assertEqual(pat2.voice(4).length, 32)
        self.assertEqual(pat2.voice(4).get_triggers(), [1, 3, 5, 7])


class TestFormatPatternFilename(unittest.TestCase):
    """Tests for pattern filename formatting."""

    def test_format_basic(self):
        """Test basic filename formatting."""
        self.assertEqual(format_pattern_filename(0, "KICK"), "00-KICK.PAT")
        self.assertEqual(format_pattern_filename(10, "ROCK"), "10-ROCK.PAT")
        self.assertEqual(format_pattern_filename(63, "HI"), "63-HI.PAT")

    def test_format_no_name(self):
        """Test formatting without name."""
        self.assertEqual(format_pattern_filename(0, ""), "00-.PAT")
        self.assertEqual(format_pattern_filename(5), "05-.PAT")

    def test_format_truncation(self):
        """Test name truncation to 5 chars."""
        self.assertEqual(format_pattern_filename(0, "VERYLONGNAME"), "00-VERYL.PAT")

    def test_format_uppercase(self):
        """Test name is uppercased."""
        self.assertEqual(format_pattern_filename(0, "kick"), "00-KICK.PAT")

    def test_format_invalid_index(self):
        """Test invalid index raises error."""
        with self.assertRaises(ValueError):
            format_pattern_filename(-1, "TEST")
        with self.assertRaises(ValueError):
            format_pattern_filename(64, "TEST")


if __name__ == '__main__':
    unittest.main()

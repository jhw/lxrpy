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
from lxr import param_number, param_from_number


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

        for i in range(1, 8):
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
        self.assertEqual(len(d['voices']), 7)


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
        self.step.note = 36  # C3 (LXR labelling)
        self.assertEqual(self.step.note, 36)

        self.step.note = 60  # C5 (LXR labelling)
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


class TestVoice7Pattern(unittest.TestCase):
    """Tests for voice 7 pattern access."""

    def test_voice_7_triggers(self):
        """Test setting and getting triggers for voice 7."""
        pattern = Pattern.init()
        v7 = pattern.voice(7)

        v7.set_triggers([1, 2, 3, 7, 8, 9, 13, 14, 15])
        self.assertEqual(v7.get_triggers(), [1, 2, 3, 7, 8, 9, 13, 14, 15])

    def test_voice_7_clear_triggers(self):
        """Test clearing voice 7 triggers."""
        pattern = Pattern.init()
        v7 = pattern.voice(7)

        v7.set_triggers([1, 5, 9])
        v7.clear_all_triggers()
        self.assertEqual(v7.get_triggers(), [])

    def test_voice_7_length(self):
        """Test voice 7 pattern length."""
        pattern = Pattern.init()
        v7 = pattern.voice(7)

        v7.length = 16
        self.assertEqual(v7.length, 16)

    def test_voice_7_independence(self):
        """Test voice 7 triggers don't interfere with voices 1-6."""
        pattern = Pattern.init()

        pattern.voice(6).set_triggers([1, 5, 9, 13])
        pattern.voice(7).set_triggers([2, 4, 6, 8])

        self.assertEqual(pattern.voice(6).get_triggers(), [1, 5, 9, 13])
        self.assertEqual(pattern.voice(7).get_triggers(), [2, 4, 6, 8])

    def test_voice_7_step_data(self):
        """Test voice 7 step data access."""
        pattern = Pattern.init()
        step = pattern.voice(7).step(1)

        step.velocity = 100
        step.note = 38
        self.assertEqual(step.velocity, 100)
        self.assertEqual(step.note, 38)

    def test_copy_voice_to_7(self):
        """Test copying voice pattern to voice 7."""
        pat1 = Pattern.init()
        pat2 = Pattern.init()

        pat1.voice(1).length = 16
        pat1.voice(1).set_triggers([1, 5, 9, 13])

        pat2.copy_voice_from(pat1, 1, 7)
        self.assertEqual(pat2.voice(7).length, 16)
        self.assertEqual(pat2.voice(7).get_triggers(), [1, 5, 9, 13])


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


class TestTemplatePattern(unittest.TestCase):
    """The template must be a cleared pattern (firmware seq_clearTrack)."""

    def test_template_is_blank(self):
        """No triggers, 16 steps, neutral step data on every track."""
        pattern = Pattern.init()
        self.assertEqual(pattern.name, '')
        self.assertEqual(pattern.shuffle, 0)
        self.assertEqual(pattern.kit_index, 0)
        for v in range(1, 8):
            vp = pattern.voice(v)
            self.assertEqual(vp.get_triggers(), [])
            self.assertEqual(vp.length, 16)
            for n in range(1, 65):
                step = vp.step(n)
                self.assertEqual(step.velocity, 127)
                self.assertEqual(step.probability, 100)
                self.assertEqual(step.note, 60)
                self.assertEqual(step.flam, FlamAmount.OFF)
                self.assertEqual(step.shift, 0)
                self.assertIsNone(step.get_automation(1))
                self.assertIsNone(step.get_automation(2))


class TestPatternHeader(unittest.TestCase):
    """Tests for pattern name and shuffle."""

    def test_name(self):
        """Name occupies the first 8 bytes and leaves the magic intact."""
        pattern = Pattern.init()
        pattern.name = "GROOVE"
        self.assertEqual(pattern.name, "GROOVE")
        pattern.name = "VERYLONGNAME"
        self.assertEqual(pattern.name, "VERYLONG")
        self.assertEqual(bytes(pattern._data[8:14]), b"PatV03")

    def test_shuffle(self):
        """Shuffle is stored per pattern at 0x0E46."""
        pattern = Pattern.init()
        pattern.shuffle = 42
        self.assertEqual(pattern._data[0x0E46], 42)
        self.assertEqual(pattern.shuffle, 42)
        with self.assertRaises(ValueError):
            pattern.shuffle = 128

    def test_to_dict(self):
        """to_dict exports name and shuffle."""
        pattern = Pattern.init()
        pattern.name = "AB"
        pattern.shuffle = 9
        d = pattern.to_dict()
        self.assertEqual(d['name'], 'AB')
        self.assertEqual(d['shuffle'], 9)


class TestStepAutomation(unittest.TestCase):
    """Tests for the two per-step automation slots (step bytes 3-6)."""

    def setUp(self):
        self.pattern = Pattern.init()
        self.step = self.pattern.voice(2).step(5)

    def test_set_by_number(self):
        """Parameters below 128 are stored as CC number (param + 1); higher ones as-is."""
        self.step.set_automation(1, 38, 100)
        self.step.set_automation(2, 236, 7)
        offset = self.step._step_offset
        self.assertEqual(list(self.pattern._data[offset + 3:offset + 7]), [39, 100, 236, 7])
        self.assertEqual(self.step.get_automation(1), (38, 100))
        self.assertEqual(self.step.get_automation(2), (236, 7))

    def test_set_by_name(self):
        """Named parameters default to the step's own voice."""
        self.step.set_automation(1, 'flt_frq', 64)
        self.assertEqual(self.step.get_automation(1), (param_number('flt_frq', 2), 64))
        self.step.set_automation(2, 'flt_frq', 10, voice=4)
        self.assertEqual(self.step.get_automation(2), (param_number('flt_frq', 4), 10))

    def test_voice7_maps_to_v6(self):
        """Track 7 plays V6, so named parameters resolve to V6."""
        step = self.pattern.voice(7).step(1)
        step.set_automation(1, 'aeg_dec_open', 50)
        self.assertEqual(step.get_automation(1), (param_number('aeg_dec_open', 6), 50))

    def test_encoding_boundaries(self):
        """The 7-bit wrap and the CC/CC2 boundary round-trip."""
        offset = self.step._step_offset + 3
        for number, stored in [(0, 1), (126, 127), (127, 0), (128, 128), (246, 246)]:
            self.step.set_automation(1, number, 1)
            self.assertEqual(self.pattern._data[offset], stored, number)
            self.assertEqual(self.step.get_automation(1), (number, 1))

    def test_decodes_device_recording(self):
        """Bytes recorded on the device decode to the expected parameters."""
        offset = self.step._step_offset + 3
        # V1 track recording seen in a real file: global sample rate and V1 fine tune
        self.pattern._data[offset:offset + 4] = bytes([115, 2, 10, 4])
        self.assertEqual(param_from_number(self.step.get_automation(1)[0]), ('srt_all', None))
        self.assertEqual(param_from_number(self.step.get_automation(2)[0]), ('osc_fin', 1))

    def test_clear(self):
        """Clearing writes the firmware's NO_AUTOMATION marker."""
        self.step.set_automation(1, 38, 100)
        self.step.set_automation(2, 39, 100)
        self.step.clear_automation(1)
        self.assertIsNone(self.step.get_automation(1))
        self.assertIsNotNone(self.step.get_automation(2))
        self.step.clear_automation()
        self.assertIsNone(self.step.get_automation(2))
        self.assertEqual(self.pattern._data[self.step._step_offset + 3], 0xFF)

    def test_invalid(self):
        """Bad slot, parameter number or value raise."""
        with self.assertRaises(ValueError):
            self.step.set_automation(3, 38, 1)
        with self.assertRaises(ValueError):
            self.step.set_automation(1, 247, 1)
        with self.assertRaises(ValueError):
            self.step.set_automation(1, 38, 128)

    def test_does_not_touch_other_fields(self):
        """Automation leaves velocity, probability and note alone."""
        self.step.velocity = 90
        self.step.probability = 50
        self.step.note = 62
        self.step.set_automation(1, 38, 100)
        self.step.set_automation(2, 39, 101)
        self.assertEqual((self.step.velocity, self.step.probability, self.step.note), (90, 50, 62))


if __name__ == '__main__':
    unittest.main()

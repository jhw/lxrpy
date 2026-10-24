#!/usr/bin/env python3
"""Tests for LXR-02 Kit/Sound file handling."""

import os
import sys
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lxr import Kit, Voice, Waveform, FmMode, ClickWave, FilterType
from lxr import LfoWave, LfoSync, LfoRetrig, OutputRouting
from lxr import format_kit_filename
from lxr import FxType, FxDistType, FxRatio, FxReverbType, FxDelayType
from lxr import param_number, param_from_number, mod_target, mod_target_index, MOD_TARGETS


class TestKit(unittest.TestCase):
    """Tests for Kit class."""

    def test_init_from_template(self):
        """Test initializing kit from template."""
        kit = Kit.init()
        self.assertIsNotNone(kit._data)
        self.assertEqual(len(kit._data), 255)

    def test_kit_name(self):
        """Test getting and setting kit name."""
        kit = Kit.init()
        original_name = kit.name

        kit.name = "MYKIT"
        self.assertEqual(kit.name, "MYKIT")

        # Test truncation
        kit.name = "VERYLONGNAME"
        self.assertEqual(kit.name, "VERYLONG")  # 8 char max

    def test_voice_access(self):
        """Test accessing voices."""
        kit = Kit.init()

        for i in range(1, 7):
            voice = kit.voice(i)
            self.assertIsInstance(voice, Voice)
            self.assertEqual(voice.voice_num, i)

    def test_voice_invalid_number(self):
        """Test that invalid voice numbers raise errors."""
        kit = Kit.init()

        with self.assertRaises(ValueError):
            kit.voice(0)
        with self.assertRaises(ValueError):
            kit.voice(7)

    def test_clone(self):
        """Test cloning a kit."""
        kit = Kit.init()
        kit.name = "ORIG"
        kit.voice(1).mix_vol = 100

        clone = kit.clone()
        self.assertEqual(clone.name, "ORIG")
        self.assertEqual(clone.voice(1).mix_vol, 100)

        # Modify clone, original should be unchanged
        clone.name = "CLONE"
        clone.voice(1).mix_vol = 50
        self.assertEqual(kit.name, "ORIG")
        self.assertEqual(kit.voice(1).mix_vol, 100)

    def test_save_and_load(self):
        """Test saving and loading kit files."""
        kit = Kit.init()
        kit.name = "TEST"
        kit.voice(1).osc_wav = Waveform.SAW
        kit.voice(1).mix_vol = 100

        with tempfile.NamedTemporaryFile(suffix='.SND', delete=False) as tmp:
            try:
                kit.save(tmp.name)

                loaded = Kit.from_file(tmp.name)
                self.assertEqual(loaded.name, "TEST")
                self.assertEqual(loaded.voice(1).osc_wav, Waveform.SAW)
                self.assertEqual(loaded.voice(1).mix_vol, 100)
            finally:
                os.unlink(tmp.name)

    def test_to_dict(self):
        """Test exporting kit to dictionary."""
        kit = Kit.init()
        kit.name = "DICT"

        d = kit.to_dict()
        self.assertEqual(d['name'], "DICT")
        self.assertEqual(len(d['voices']), 6)


class TestVoice(unittest.TestCase):
    """Tests for Voice class."""

    def setUp(self):
        """Set up test kit."""
        self.kit = Kit.init()

    def test_osc_params(self):
        """Test oscillator parameters."""
        v = self.kit.voice(1)

        # Waveform (enum)
        v.osc_wav = Waveform.SAW
        self.assertEqual(v.osc_wav, Waveform.SAW)

        v.osc_wav = Waveform.PWM
        self.assertEqual(v.osc_wav, Waveform.PWM)

        # Coarse tune (centered, -60 to +67)
        v.osc_coa = 0
        self.assertEqual(v.osc_coa, 0)

        v.osc_coa = -30
        self.assertEqual(v.osc_coa, -30)

        v.osc_coa = 67
        self.assertEqual(v.osc_coa, 67)

        # Fine tune (centered, -63 to +64)
        v.osc_fin = 0
        self.assertEqual(v.osc_fin, 0)

        # PWM
        v.osc_pwm = 64
        self.assertEqual(v.osc_pwm, 64)

    def test_osc_noi_mix_v4_only(self):
        """Test osc.noi and osc.mix are V4 only."""
        v4 = self.kit.voice(4)

        # Should work for V4
        v4.osc_noi = 100
        self.assertEqual(v4.osc_noi, 100)

        v4.osc_mix = 50
        self.assertEqual(v4.osc_mix, 50)

        # Should raise for other voices
        v1 = self.kit.voice(1)
        with self.assertRaises(ValueError):
            _ = v1.osc_noi
        with self.assertRaises(ValueError):
            _ = v1.osc_mix

    def test_aeg_params(self):
        """Test amplitude envelope parameters."""
        v = self.kit.voice(1)

        v.aeg_atk = 10
        self.assertEqual(v.aeg_atk, 10)

        v.aeg_dec = 50
        self.assertEqual(v.aeg_dec, 50)

        v.aeg_slp = 30
        self.assertEqual(v.aeg_slp, 30)

    def test_aeg_rpt_v4_v5_only(self):
        """Test aeg.rpt is V4-V5 only."""
        v4 = self.kit.voice(4)
        v5 = self.kit.voice(5)

        v4.aeg_rpt = 5
        self.assertEqual(v4.aeg_rpt, 5)

        v5.aeg_rpt = 3
        self.assertEqual(v5.aeg_rpt, 3)

        v1 = self.kit.voice(1)
        with self.assertRaises(ValueError):
            _ = v1.aeg_rpt

    def test_fm_params_v1_v3(self):
        """Test FM parameters for V1-V3."""
        for i in [1, 2, 3]:
            v = self.kit.voice(i)

            v.fm_wav = Waveform.TRI
            self.assertEqual(v.fm_wav, Waveform.TRI)

            v.fm_amt = 64
            self.assertEqual(v.fm_amt, 64)

            v.fm_frq = -30  # centered
            self.assertEqual(v.fm_frq, -30)

            v.fm_mod = FmMode.MIX
            self.assertEqual(v.fm_mod, FmMode.MIX)

    def test_fm_params_v5_v6(self):
        """Test FM parameters for V5-V6 (alternate model)."""
        for i in [5, 6]:
            v = self.kit.voice(i)

            v.fm_wav = Waveform.SIN
            self.assertEqual(v.fm_wav, Waveform.SIN)

            v.fm_wav2 = Waveform.TRI
            self.assertEqual(v.fm_wav2, Waveform.TRI)

            v.fm_f1 = 10  # centered
            self.assertEqual(v.fm_f1, 10)

            v.fm_f2 = -20
            self.assertEqual(v.fm_f2, -20)

            v.fm_g1 = 100
            self.assertEqual(v.fm_g1, 100)

            v.fm_g2 = 80
            self.assertEqual(v.fm_g2, 80)

    def test_fm_v4_no_fm(self):
        """Test V4 has no FM parameters."""
        v4 = self.kit.voice(4)

        with self.assertRaises(ValueError):
            _ = v4.fm_wav
        with self.assertRaises(ValueError):
            _ = v4.fm_amt

    def test_mod_params(self):
        """Test modulator parameters (V1-V4)."""
        for i in [1, 2, 3, 4]:
            v = self.kit.voice(i)

            v.mod_dec = 50
            self.assertEqual(v.mod_dec, 50)

            v.mod_slp = 30
            self.assertEqual(v.mod_slp, 30)

            v.mod_mod = 100
            self.assertEqual(v.mod_mod, 100)

            v.mod_amt = 64
            self.assertEqual(v.mod_amt, 64)

    def test_mod_vol_all_voices(self):
        """Test mod.vol is available for all voices."""
        for i in range(1, 7):
            v = self.kit.voice(i)
            v.mod_vol = 1
            self.assertEqual(v.mod_vol, 1)

    def test_click_params(self):
        """Test click parameters."""
        v = self.kit.voice(1)

        v.click_wav = ClickWave.KIK
        self.assertEqual(v.click_wav, ClickWave.KIK)

        v.click_vol = 80
        self.assertEqual(v.click_vol, 80)

        v.click_frq = 40
        self.assertEqual(v.click_frq, 40)

    def test_filter_params(self):
        """Test filter parameters."""
        v = self.kit.voice(1)

        v.flt_frq = 100
        self.assertEqual(v.flt_frq, 100)

        v.flt_res = 50
        self.assertEqual(v.flt_res, 50)

        v.flt_drv = 30
        self.assertEqual(v.flt_drv, 30)

        v.flt_typ = FilterType.HP
        self.assertEqual(v.flt_typ, FilterType.HP)

    def test_lfo_params(self):
        """Test LFO parameters."""
        v = self.kit.voice(1)

        v.lfo_frq = 64
        self.assertEqual(v.lfo_frq, 64)

        v.lfo_mod = 50
        self.assertEqual(v.lfo_mod, 50)

        v.lfo_wav = LfoWave.SQR
        self.assertEqual(v.lfo_wav, LfoWave.SQR)

        v.lfo_snc = LfoSync.DIV_1_4
        self.assertEqual(v.lfo_snc, LfoSync.DIV_1_4)

        v.lfo_rtg = LfoRetrig.V1
        self.assertEqual(v.lfo_rtg, LfoRetrig.V1)

        v.lfo_ofs = 30
        self.assertEqual(v.lfo_ofs, 30)

    def test_mix_params(self):
        """Test mix parameters."""
        v = self.kit.voice(1)

        v.mix_vol = 100
        self.assertEqual(v.mix_vol, 100)

        v.mix_pan = -30  # centered
        self.assertEqual(v.mix_pan, -30)

        v.mix_drv = 50
        self.assertEqual(v.mix_drv, 50)

        v.mix_srt = 127
        self.assertEqual(v.mix_srt, 127)

        v.mix_out = OutputRouting.FX
        self.assertEqual(v.mix_out, OutputRouting.FX)

    def test_has_param(self):
        """Test has_param method."""
        v1 = self.kit.voice(1)
        v4 = self.kit.voice(4)
        v5 = self.kit.voice(5)

        # All voices have mix_vol
        self.assertTrue(v1.has_param('mix_vol'))
        self.assertTrue(v4.has_param('mix_vol'))
        self.assertTrue(v5.has_param('mix_vol'))

        # Only V4 has osc_noi
        self.assertFalse(v1.has_param('osc_noi'))
        self.assertTrue(v4.has_param('osc_noi'))
        self.assertFalse(v5.has_param('osc_noi'))

        # Only V5-V6 have fm_wav2
        self.assertFalse(v1.has_param('fm_wav2'))
        self.assertFalse(v4.has_param('fm_wav2'))
        self.assertTrue(v5.has_param('fm_wav2'))

    def test_to_dict(self):
        """Test voice to_dict."""
        v = self.kit.voice(1)
        v.mix_vol = 100
        v.osc_wav = Waveform.SAW

        d = v.to_dict()
        self.assertEqual(d['voice_num'], 1)
        self.assertEqual(d['mix_vol'], 100)
        self.assertEqual(d['osc_wav'], 'SAW')


class TestCopyVoice(unittest.TestCase):
    """Tests for copying voice data between kits."""

    def test_copy_voice_same_type(self):
        """Test copying voice between same voice types."""
        kit1 = Kit.init()
        kit2 = Kit.init()

        # Set up source voice
        kit1.voice(1).osc_wav = Waveform.SAW
        kit1.voice(1).mix_vol = 100
        kit1.voice(1).aeg_dec = 50

        # Copy to dest
        kit2.copy_voice_from(kit1, 1, 1)

        self.assertEqual(kit2.voice(1).osc_wav, Waveform.SAW)
        self.assertEqual(kit2.voice(1).mix_vol, 100)
        self.assertEqual(kit2.voice(1).aeg_dec, 50)

    def test_copy_voice_different_positions(self):
        """Test copying to different voice position."""
        kit1 = Kit.init()
        kit2 = Kit.init()

        kit1.voice(2).osc_wav = Waveform.TRI
        kit1.voice(2).mix_vol = 80

        kit2.copy_voice_from(kit1, 2, 3)

        self.assertEqual(kit2.voice(3).osc_wav, Waveform.TRI)
        self.assertEqual(kit2.voice(3).mix_vol, 80)


class TestFormatKitFilename(unittest.TestCase):
    """Tests for kit filename formatting."""

    def test_format_basic(self):
        """Test basic filename formatting."""
        self.assertEqual(format_kit_filename(0, "KICK"), "00-KICK.SND")
        self.assertEqual(format_kit_filename(10, "SNARE"), "10-SNARE.SND")
        self.assertEqual(format_kit_filename(63, "HI"), "63-HI.SND")

    def test_format_truncation(self):
        """Test name truncation to 5 chars."""
        self.assertEqual(format_kit_filename(0, "VERYLONGNAME"), "00-VERYL.SND")

    def test_format_uppercase(self):
        """Test name is uppercased."""
        self.assertEqual(format_kit_filename(0, "kick"), "00-KICK.SND")

    def test_format_empty_name(self):
        """Test empty name."""
        self.assertEqual(format_kit_filename(0, ""), "00-.SND")

    def test_format_invalid_index(self):
        """Test invalid index raises error."""
        with self.assertRaises(ValueError):
            format_kit_filename(-1, "KICK")
        with self.assertRaises(ValueError):
            format_kit_filename(64, "KICK")


class TestFirmwareParams(unittest.TestCase):
    """Tests for parameters mapped from the LXR firmware (Parameters.h)."""

    def setUp(self):
        self.kit = Kit.init()

    def test_aeg_dec_open_v6_only(self):
        """Open hi-hat decay is byte 69 and only exists on V6."""
        self.kit.voice(6).aeg_dec_open = 99
        self.assertEqual(self.kit._data[69], 99)
        self.assertEqual(self.kit.voice(6).aeg_dec_open, 99)
        for v in range(1, 6):
            self.assertFalse(self.kit.voice(v).has_param('aeg_dec_open'))

    def test_velocity_mod_all_voices(self):
        """Velocity mod amount/destination exist on V5 and V6."""
        self.kit.voice(5).mod_amt = 11
        self.kit.voice(6).mod_amt = 12
        self.kit.voice(5).mod_dst = 160
        self.kit.voice(6).mod_dst = 200
        self.assertEqual(list(self.kit._data[155:157]), [11, 12])
        self.assertEqual(list(self.kit._data[161:163]), [160, 200])

    def test_mod_dst_range(self):
        """Mod destinations are indices into MOD_TARGETS (0-228), not 0-127."""
        self.kit.voice(1).lfo_dst = 228
        self.assertEqual(self.kit.voice(1).lfo_dst, 228)
        self.kit.voice(1).lfo_dst = 300
        self.assertEqual(self.kit.voice(1).lfo_dst, 228)

    def test_lfo_voi_range(self):
        """LFO target voice is clamped to 1-6."""
        self.kit.voice(1).lfo_voi = 0
        self.assertEqual(self.kit.voice(1).lfo_voi, 1)
        self.kit.voice(1).lfo_voi = 9
        self.assertEqual(self.kit.voice(1).lfo_voi, 6)

    def test_fx_offsets(self):
        """Kit-level FX parameters live at bytes 242-253."""
        k = self.kit
        k.fx_typ = FxType.CMP
        k.fx_out = OutputRouting.L2
        k.fx_dw = 50
        k.fx_dis = FxDistType.CLP
        k.fx_p1, k.fx_p2, k.fx_p3, k.fx_p4 = 1, 2, 3, 4
        k.fx_rat = FxRatio.R8_1
        k.fx_wav = Waveform.SAW
        k.fx_rev = FxReverbType.PLT
        k.fx_del = FxDelayType.PP
        self.assertEqual(list(k._data[242:254]), [3, 4, 50, 2, 1, 2, 3, 4, 5, 2, 0, 1])
        self.assertEqual(k.fx_typ, FxType.CMP)
        self.assertEqual(k.fx_rat, FxRatio.R8_1)

    def test_fx_ranges(self):
        """Dry/wet clamps to 0-100 and FX routing can't target the FX bus."""
        self.kit.fx_dw = 200
        self.assertEqual(self.kit.fx_dw, 100)
        self.kit.fx_out = OutputRouting.FX
        self.assertEqual(self.kit.fx_out, OutputRouting.R2)

    def test_morph_kit_and_srt_all(self):
        """Morph destination is byte 254, global sample rate byte 122."""
        self.kit.morph_kit = 12
        self.kit.srt_all = 40
        self.assertEqual(self.kit._data[254], 12)
        self.assertEqual(self.kit._data[122], 40)

    def test_kit_params_survive_save(self):
        """Kit-level parameters round-trip through a file."""
        self.kit.fx_typ = FxType.DEL
        self.kit.fx_p2 = 77
        with tempfile.NamedTemporaryFile(suffix='.SND', delete=False) as tmp:
            try:
                self.kit.save(tmp.name)
                loaded = Kit.from_file(tmp.name)
                self.assertEqual(loaded.fx_typ, FxType.DEL)
                self.assertEqual(loaded.fx_p2, 77)
            finally:
                os.unlink(tmp.name)

    def test_to_dict_includes_kit_params(self):
        """to_dict exports kit-level parameters."""
        self.kit.fx_typ = FxType.RNG
        self.assertEqual(self.kit.to_dict()['kit']['fx_typ'], 'RNG')

    def test_copy_voice_includes_new_params(self):
        """Copying V5 to V6 carries velocity mod settings."""
        source = Kit.init()
        source.voice(5).mod_amt = 90
        self.kit.copy_voice_from(source, 5, 6)
        self.assertEqual(self.kit.voice(6).mod_amt, 90)


class TestParamNumbers(unittest.TestCase):
    """Tests for firmware parameter number lookups."""

    def test_param_number(self):
        """Parameter number is file offset minus the 8-byte name."""
        self.assertEqual(param_number('osc_wav', 1), 1)
        self.assertEqual(param_number('flt_frq', 2), 46 - 8)
        self.assertEqual(param_number('fx_dw'), 244 - 8)

    def test_param_number_errors(self):
        """Per-voice parameters need a valid voice that has them."""
        with self.assertRaises(ValueError):
            param_number('flt_frq')
        with self.assertRaises(ValueError):
            param_number('osc_noi', 1)
        with self.assertRaises(ValueError):
            param_number('nope', 1)

    def test_param_from_number(self):
        """Lookup is the inverse of param_number."""
        self.assertEqual(param_from_number(46 - 8), ('flt_frq', 2))
        self.assertEqual(param_from_number(244 - 8), ('fx_dw', None))
        self.assertIsNone(param_from_number(0))  # PAR_NONE

    def test_mod_targets_decode(self):
        """Every mod target decodes, and per-voice targets belong to their block."""
        self.assertEqual(len(MOD_TARGETS), 229)
        self.assertIsNone(mod_target(0))
        self.assertEqual(mod_target(1), ('srt_all', None))
        self.assertEqual(mod_target(2), ('osc_coa', 1))
        self.assertEqual(mod_target(191), ('osc_coa', 6))
        for i in range(1, len(MOD_TARGETS)):
            self.assertIsNotNone(mod_target(i), i)

    def test_mod_target_index_round_trip(self):
        """Encoding then decoding a target returns it unchanged."""
        for voice in range(1, 7):
            i = mod_target_index('flt_frq', voice)
            self.assertEqual(mod_target(i), ('flt_frq', voice))
        self.assertEqual(mod_target_index('srt_all'), 1)

    def test_mod_target_index_invalid(self):
        """Parameters that can't be modulated raise."""
        with self.assertRaises(ValueError):
            mod_target_index('lfo_voi', 1)


if __name__ == '__main__':
    unittest.main()

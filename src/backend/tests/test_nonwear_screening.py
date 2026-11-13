"""Synthetic QC checks; not validation against real GGIR recording output."""
import unittest
import numpy as np
import pandas as pd
from backend.nonwear import TriaxialNonwear, wear_mask_from_intervals
from backend.data_quality import inspect_initial_data_coverage, apply_data_quality_control


class FakeRaw:
    def __init__(self,series):
        self.data=series
        self.frequency=pd.Timedelta('1min')
        self.format='Pandas'
    @property
    def raw_data(self):
        return self.data


class NonwearScreeningTest(unittest.TestCase):
    def test_stationary_device_generates_intervals_and_valid_qc(self):
        screen=TriaxialNonwear()
        x=np.tile([0.0,0.0,1.0],(7200,1))
        start=pd.Timestamp('2026-05-01 00:00:00').timestamp()
        # Stream the same file as two chunks, verify stable moments across boundaries.
        screen.add(x[:3600],start,1)
        screen.add(x[3600:],start+3600,1)
        summary=screen.finish()
        self.assertEqual(summary['native_sample_rate_hz'],1)
        self.assertEqual(summary['windows_checked'],5)
        self.assertTrue(summary['nonwear_intervals'])
        dates=pd.date_range('2026-05-01',periods=120,freq='1min')
        wear=wear_mask_from_intervals(dates,summary['nonwear_intervals'])
        self.assertTrue((~wear).any())
        self.assertTrue(wear.iloc[0])
        raw=FakeRaw(pd.Series(10.0,index=pd.date_range('2026-05-01',periods=24*60,freq='1min')))
        raw._ui_nonwear_summary=summary
        raw._ui_nonwear_intervals=summary['nonwear_intervals']
        initial=inspect_initial_data_coverage(raw)
        self.assertEqual(initial['nonwear_detection']['method'],'triaxial_sd_range_60m_15m_ggir_inspired')
        self.assertGreater(initial['modes']['calendar_day']['windows'][0]['detected_nonwear_hours'],0)
        _,qc=apply_data_quality_control(raw,{'masking':{'minimumValidHoursPerDay':16}})
        self.assertTrue(qc['nonwear_applied'])
        self.assertGreater(qc['detected_nonwear_hours'],0)

    def test_moving_device_does_not_count_as_nonwear(self):
        screen=TriaxialNonwear()
        n=7200
        t=np.arange(n)
        xyz=np.column_stack([np.sin(t*.4)*.15,np.cos(t*.5)*.2,1+np.sin(t*.2)*.14])
        screen.add(xyz,pd.Timestamp('2026-05-01').timestamp(),1)
        results=screen.finish()
        self.assertEqual(results['nonwear_intervals'],[])
        self.assertGreater(results['windows_checked'],0)

    def test_inadequate_coverage_is_unavailable_not_nonwear(self):
        screen=TriaxialNonwear()
        screen.add(np.tile([0,0,1],(120,1)),pd.Timestamp('2026-05-01').timestamp(),1)
        self.assertEqual(screen.finish()['windows_checked'],0)

if __name__=='__main__':unittest.main()

import unittest
from live_pilot import evidence_status, guard_reasons, remote_program, validate_output


class PilotControls(unittest.TestCase):
    def test_remote_helper_compiles_and_invokes_collection(self):
        program = remote_program({'port': 18094})
        compile(program, 'test-helper', 'exec')
        self.assertTrue(program.endswith("remote_run({'port': 18094})\n"))

    def test_empty_or_partial_evidence_cannot_pass(self):
        with self.assertRaisesRegex(ValueError, 'empty'):
            evidence_status([])
        with self.assertRaisesRegex(ValueError, 'terminal'):
            evidence_status([{'event': 'baseline_sample'}])
        self.assertEqual(evidence_status([{'event': 'stop'}]), 'stop')

    def good(self):
        return {'cpu_idle_pct': 50, 'memory_pressure_free_pct': 40,
                'wired_compressor_pct': 60, 'swap_used_MiB': 0,
                'thermal_warning': False, 'disk_free_GiB': 20}

    def test_missing_sensor_is_not_spare_capacity(self):
        s = self.good(); del s['cpu_idle_pct']
        self.assertEqual(guard_reasons(s), ['missing_guard_sensor'])

    def test_threshold_and_violation_reason(self):
        s = self.good(); s['cpu_idle_pct'] = 25
        self.assertEqual(guard_reasons(s), [])
        s['cpu_idle_pct'] = 24.99
        self.assertEqual(guard_reasons(s), ['cpu_idle_below_25pct'])

    def test_nonfinite_sensor_is_not_headroom(self):
        s = self.good(); s['cpu_idle_pct'] = float('nan')
        self.assertEqual(guard_reasons(s), ['missing_guard_sensor'])

    def test_memory_thermal_and_swap_stop(self):
        s = self.good(); s.update(memory_pressure_free_pct=29, thermal_warning=True, swap_used_MiB=65)
        self.assertEqual(guard_reasons(s), ['memory_pressure_free_below_30pct',
                                           'swap_growth_above_64MiB', 'thermal_warning'])

    def test_quality_is_more_than_http_success(self):
        self.assertFalse(validate_output('{}'))
        self.assertFalse(validate_output('not JSON'))
        self.assertTrue(validate_output('{"cpu_reserve_pct":25,"memory_reserve_pct":25,'
                                        '"gpu_busy":"unmeasured","energy_per_job":"unmeasured"}'))


if __name__ == '__main__':
    unittest.main()

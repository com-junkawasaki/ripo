"""Controls for allocation safety, optimization, and evidence boundaries."""
import copy
import itertools
import json
from pathlib import Path
import unittest

from market import (UNITS, allocate, budgets, communities, contrast, fits,
                    literature, observed_snapshot, reason, validate)

ROOT = Path(__file__).resolve().parent


def fixture():
    return json.loads((ROOT / 'examples/awai-market.json').read_text())


class MarketTests(unittest.TestCase):
    def test_solver_against_independent_small_enumeration(self):
        d = fixture()
        d['jobs'] = d['jobs'][:3]
        for j in d['jobs']:
            j['offers']['sim-gpu-a']['cost_points'] = 9
        cap = budgets(d)
        best = 0
        node_map = {n['id']: n for n in d['nodes']}
        for assignment in itertools.product([None] + list(node_map), repeat=3):
            usage = {n: {k: 0 for k in UNITS} for n in node_map}
            value, feasible = 0, True
            for j, nid in zip(d['jobs'], assignment):
                if nid is None:
                    continue
                if reason(d, j, node_map[nid]):
                    feasible = False; break
                value += j['value_points'] - j['offers'][nid]['cost_points']
                for k in UNITS:
                    usage[nid][k] += j['demand'][k]
                    if usage[nid][k] > cap[nid][k]:
                        feasible = False
            if feasible:
                best = max(best, value)
        self.assertEqual(allocate(d, 'optimized')['net_value_points'], best)

    def test_optimizer_dominates_greedy_under_same_constraints(self):
        d = fixture()
        for shift in range(len(d['jobs'])):
            d['jobs'] = d['jobs'][1:] + d['jobs'][:1]
            self.assertGreaterEqual(allocate(d, 'optimized')['net_value_points'],
                                    allocate(d, 'fresh_fifo')['net_value_points'])

    def test_order_changes_do_not_change_optimal_value(self):
        d = fixture()
        before = allocate(d, 'optimized')['net_value_points']
        d['nodes'].reverse(); d['jobs'].reverse()
        self.assertEqual(before, allocate(d, 'optimized')['net_value_points'])

    def test_freshness_boundary_and_unknown_qualification(self):
        d = fixture(); j, n = d['jobs'][0], d['nodes'][0]
        n['observed_seconds'] = d['now_seconds'] - d['freshness_seconds']
        self.assertIsNone(reason(d, j, n))
        n['observed_seconds'] -= 1
        self.assertEqual(reason(d, j, n), 'stale_observation')
        n['observed_seconds'] = d['now_seconds']; n['qualified'] = False
        self.assertEqual(reason(d, j, n), 'unqualified')
        n['qualified'] = None
        with self.assertRaisesRegex(ValueError, 'explicit booleans'):
            validate(d)

    def test_denial_does_not_become_approval_or_a_request(self):
        d = fixture()
        for j in d['jobs']:
            for o in j['offers'].values():
                o['consent'] = False
        self.assertEqual(allocate(d, 'optimized')['assigned_jobs'], 0)
        d['jobs'][0]['offers']['sim-gpu-a']['consent'] = 'yes'
        with self.assertRaisesRegex(ValueError, 'explicit boolean'):
            validate(d)

    def test_reserves_and_memory_bind_even_with_cpu_idle(self):
        d = fixture()
        for n in d['nodes']:
            n['reserve']['memory'] = 1
        self.assertEqual(allocate(d, 'optimized')['assigned_jobs'], 0)
        d['nodes'][0]['reserve']['memory'] = 1.1
        with self.assertRaisesRegex(ValueError, 'reserve'):
            validate(d)

    def test_negative_value_and_unsupported_runtime_are_refused(self):
        d = fixture()
        d['jobs'] = [d['jobs'][-1]]
        self.assertEqual(allocate(d, 'optimized')['assigned_jobs'], 0)
        d = fixture()
        for j in d['jobs']:
            for o in j['offers'].values():
                o['cost_points'] = j['value_points'] + 1
        self.assertEqual(allocate(d, 'optimized')['assigned_jobs'], 0)

    def test_ripo_boundary_is_not_an_authority_or_capacity_boundary(self):
        d = fixture(); groups, _ = communities(d)
        d['jobs'] = [d['jobs'][4]]
        d['nodes'][0]['available'] = False
        self.assertEqual(allocate(d, 'optimized', groups)['assigned_jobs'], 1)
        self.assertEqual(allocate(d, 'ripo_hard_boundary', groups)['assigned_jobs'], 0)

    def test_no_demand_is_explicit_and_missing_demand_is_error(self):
        d = fixture(); d['jobs'] = []
        r = allocate(d, 'optimized')
        self.assertEqual(r['assigned_jobs'], 0)
        self.assertIsNone(r['assigned_fraction'])
        self.assertEqual(r['demand_status'], 'explicit_empty_synthetic_demand')
        del d['jobs']
        with self.assertRaises(KeyError):
            allocate(d, 'optimized')

    def test_units_direction_and_nonfinite_refusals(self):
        d = fixture(); d['units']['memory'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'units'):
            validate(d)
        d = fixture(); d['exchange_snapshots']['directed'] = True
        with self.assertRaisesRegex(ValueError, 'undirected'):
            communities(d)
        d = fixture(); d['jobs'][0]['demand']['cpu'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite'):
            validate(d)
        d = fixture(); d['jobs'][0]['demand'] = dict.fromkeys(UNITS, 0)
        with self.assertRaisesRegex(ValueError, 'positive resource'):
            validate(d)

    def test_published_percentage_points_and_relative_change_are_distinct(self):
        r = literature(json.loads((ROOT / 'data/market-evidence.json').read_text()))
        boston = r['uber_time_utilization'][0]
        self.assertEqual(boston['utilization']['difference'], 14.1)
        self.assertAlmostEqual(boston['utilization']['relative_change_pct'], 44.0625)
        host = r['airbnb_search_counterfactuals'][-1]
        self.assertEqual(host['difference'], 3.0)
        self.assertAlmostEqual(host['relative_change_pct'], 9.80392157)
        self.assertIsNone(contrast(0, 1)['relative_change_pct'])

    def test_snapshot_does_not_certify_offer_or_improvement(self):
        r = observed_snapshot(json.loads((ROOT / 'data/awai-snapshot-20261031.json').read_text()))
        self.assertEqual(r['sampled_nodes'], 5)
        self.assertEqual(r['noncontemporaneous_idle_core_equivalent'], 31.465)
        self.assertIsNone(r['qualified_offered_capacity'])
        self.assertIsNone(r['real_job_improvement'])


if __name__ == '__main__':
    unittest.main()

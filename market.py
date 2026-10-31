"""JUN-727: bounded, typed allocation experiment; never a host scheduler.

All jobs occupy one simultaneous window. Resource vectors are reservations,
not measured service times, success probabilities, prices or energy estimates.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from ripo import canonical_bytes, extract

PROFILE = 'ripo.awai-market.v1'
UNITS = {'cpu': 'logical_core', 'memory': 'GiB', 'gpu': 'qualified_slot',
         'storage': 'GiB_peak', 'network': 'Mbps_reserved'}
POLICIES = ('directory_once', 'fresh_once', 'fresh_fifo', 'optimized', 'ripo_hard_boundary')


def number(value, name, low=0, high=1e9):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name}: finite number in [{low}, {high}] required')


def validate(data):
    if data.get('schema') != PROFILE or data.get('evidence_kind') != 'synthetic':
        raise ValueError('explicit synthetic ripo.awai-market.v1 required')
    if data.get('units') != UNITS:
        raise ValueError('explicit resource units required')
    number(data['window_seconds'], 'window_seconds', 1)
    number(data['now_seconds'], 'now_seconds')
    number(data['freshness_seconds'], 'freshness_seconds')
    nodes, jobs = data['nodes'], data['jobs']
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 8:
        raise ValueError('one to eight nodes required')
    if not isinstance(jobs, list) or len(jobs) > 40:
        raise ValueError('explicit job list of at most 40 required')
    for items, label in ((nodes, 'node'), (jobs, 'job')):
        ids = [v['id'] for v in items]
        if any(not isinstance(v, str) or not v for v in ids) or len(set(ids)) != len(ids):
            raise ValueError(f'unique {label} IDs required')
    node_ids = {v['id'] for v in nodes}
    for n in nodes:
        if any(type(n[k]) is not bool for k in ('available', 'qualified')):
            raise ValueError('availability and qualification must be explicit booleans')
        number(n['observed_seconds'], 'observed_seconds', 0, data['now_seconds'])
        if set(n['capacity']) != set(UNITS) or set(n['reserve']) != set(UNITS):
            raise ValueError('complete capacity and reserve vectors required')
        for k in UNITS:
            number(n['capacity'][k], k)
            number(n['reserve'][k], 'reserve', 0, 1)
        if not isinstance(n['kinds'], list) or any(not isinstance(k, str) or not k for k in n['kinds']):
            raise ValueError('node kind allowlist required')
    for j in jobs:
        if not isinstance(j['kind'], str) or not j['kind']:
            raise ValueError('explicit job kind required')
        if set(j['demand']) != set(UNITS):
            raise ValueError('complete demand vector required')
        for k in UNITS:
            number(j['demand'][k], k)
        if not any(j['demand'].values()):
            raise ValueError('positive resource demand required')
        number(j['value_points'], 'value_points')
        number(j['deadline_seconds'], 'deadline_seconds')
        if j['origin'] not in node_ids:
            raise ValueError('known job origin required')
        if set(j['offers']) != node_ids or set(j['directory_order']) != node_ids or len(j['directory_order']) != len(nodes):
            raise ValueError('complete offers and unique directory order required')
        for offer in j['offers'].values():
            if type(offer['consent']) is not bool:
                raise ValueError('consent must be an explicit boolean')
            number(offer['cost_points'], 'cost_points')
    canonical_bytes(data)  # reject nonfinite JSON; these hashes are not CIDs
    return data


def budgets(data):
    return {n['id']: {k: n['capacity'][k] * (1 - n['reserve'][k]) for k in UNITS}
            for n in data['nodes']}


def reason(data, job, node):
    """A synthetic eligibility record is not permission to call an external API."""
    if not node['available']:
        return 'unavailable'
    if data['now_seconds'] - node['observed_seconds'] > data['freshness_seconds']:
        return 'stale_observation'
    if not node['qualified']:
        return 'unqualified'
    if job['kind'] not in node['kinds']:
        return 'incompatible_kind'
    if not job['offers'][node['id']]['consent']:
        return 'consent_denied'
    if job['deadline_seconds'] < data['window_seconds']:
        return 'deadline_outside_profile'
    if job['value_points'] <= job['offers'][node['id']]['cost_points']:
        return 'nonpositive_net_value'
    if any(job['demand'][k] > budgets(data)[node['id']][k] + 1e-8 for k in UNITS):
        return 'insufficient_single_job_capacity'
    return None


def fits(job, remaining):
    return all(job['demand'][k] <= remaining[k] + 1e-8 for k in UNITS)


def communities(data):
    """Run the existing RIPO extractor on a separately typed undirected fixture."""
    snapshots = data['exchange_snapshots']
    if len(snapshots.get('frames', [])) != 1:
        raise ValueError('one exchange snapshot for this single-window profile required')
    if snapshots['relation_kind'] != 'exchange':
        raise ValueError('explicit exchange observations required')
    out = extract(snapshots, tau=1.0)
    ids = set(out['frames'][0]['ids'])
    if ids != {n['id'] for n in data['nodes']}:
        raise ValueError('exchange/node observation IDs must agree')
    groups = out['frames'][0]['groups']
    return {node: i for i, group in enumerate(groups) for node in group}, out


def allocate(data, policy, groups=None):
    validate(data)
    if policy not in POLICIES:
        raise ValueError('unknown allocation policy')
    if groups is None:
        groups, _ = communities(data)
    nodes = {n['id']: n for n in data['nodes']}
    cap = budgets(data)
    remaining = copy.deepcopy(cap)
    selected, refusals = [], []
    if policy in ('directory_once', 'fresh_once', 'fresh_fifo'):
        for j in data['jobs']:
            order = j['directory_order']
            if policy == 'directory_once':
                order = order[:1]
            elif policy == 'fresh_once':
                order = [nid for nid in order if reason(data, j, nodes[nid]) is None][:1]
            for nid in order:
                why = reason(data, j, nodes[nid])
                if why is None and not fits(j, remaining[nid]):
                    why = 'concurrent_capacity'
                if why:
                    refusals.append({'job': j['id'], 'node': nid, 'reason': why})
                    continue
                selected.append((j['id'], nid))
                for k in UNITS:
                    remaining[nid][k] -= j['demand'][k]
                break
    else:
        edges = [(j, n) for j in data['jobs'] for n in data['nodes']
                 if reason(data, j, n) is None and
                 (policy != 'ripo_hard_boundary' or groups[j['origin']] == groups[n['id']])]
        if edges:
            rows, limits = [], []
            for j in data['jobs']:
                rows.append([int(ej['id'] == j['id']) for ej, _ in edges]); limits.append(1)
            for n in data['nodes']:
                for k in UNITS:
                    rows.append([j['demand'][k] if en['id'] == n['id'] else 0 for j, en in edges])
                    limits.append(cap[n['id']][k])
            costs = [-j['value_points'] + j['offers'][n['id']]['cost_points'] for j, n in edges]
            result = milp(costs, integrality=np.ones(len(edges)), bounds=Bounds(0, 1),
                          constraints=LinearConstraint(np.asarray(rows), -np.inf, limits),
                          options={'time_limit': 10, 'mip_rel_gap': 0.0})
            if not result.success or result.status != 0:
                raise RuntimeError(f'MILP not optimal: {result.message}')
            selected = [(j['id'], n['id']) for (j, n), take in zip(edges, result.x) if take > .5]
    jobs = {j['id']: j for j in data['jobs']}
    usage = {n: {k: 0 for k in UNITS} for n in nodes}
    value = 0
    for jid, nid in selected:
        j = jobs[jid]
        value += j['value_points'] - j['offers'][nid]['cost_points']
        if reason(data, j, nodes[nid]):
            raise RuntimeError('selected ineligible edge')
        for k in UNITS:
            usage[nid][k] += j['demand'][k]
            if usage[nid][k] > cap[nid][k] + 1e-7:
                raise RuntimeError('selected capacity violation')
    if len({j for j, _ in selected}) != len(selected):
        raise RuntimeError('duplicate job allocation')
    # Only fresh, available, qualified supply is in the offered denominator.
    eligible = [n for n in data['nodes'] if n['available'] and n['qualified'] and
                data['now_seconds'] - n['observed_seconds'] <= data['freshness_seconds']]
    util = {}
    for k in UNITS:
        denominator = sum(cap[n['id']][k] for n in eligible)
        util[k] = sum(v[k] for v in usage.values()) / denominator if denominator else None
    return {'policy': policy, 'assigned_jobs': len(selected), 'demand_jobs': len(jobs),
            'assigned_fraction': len(selected) / len(jobs) if jobs else None,
            'demand_status': 'explicit_empty_synthetic_demand' if not jobs else 'synthetic_jobs_supplied',
            'net_value_points': round(value, 8), 'assignments': sorted(selected),
            'usage': usage, 'offered_budget_utilization': util, 'attempt_refusals': refusals,
            'unassigned_jobs': sorted(set(jobs) - {j for j, _ in selected}),
            'interpretation': 'modeled reservations; no jobs executed or outcomes accepted'}


def contrast(before, after):
    return {'before': before, 'after': after, 'difference': round(after - before, 8),
            'relative_change_pct': round(100 * (after / before - 1), 8) if before else None}


def literature(evidence):
    result = {'uber_time_utilization': [], 'airbnb_search_counterfactuals': [],
              'reported_airbnb_online_experiment': evidence['airbnb_reported_online_experiment']}
    for row in evidence['uber_table1_aggregate_F']:
        taxi, uber = row['taxi_pct'], row['uber_pct']
        result['uber_time_utilization'].append({**row, 'utilization': contrast(taxi, uber),
            'online_hours_for_100_passenger_hours': contrast(10000 / taxi, 10000 / uber)})
    table = evidence['airbnb_search_table6']
    for a, b, name, metric in [
        ('random_order', 'random_available', 'availability_only', 'accepted'),
        ('random_order', 'status_quo', 'search_feature_bundle', 'accepted'),
        ('random_order', 'status_quo', 'search_feature_bundle_rejection', 'reject_given_contact'),
        ('personalized_available', 'rejection_weighted', 'host_preference_ranking', 'accepted')]:
        result['airbnb_search_counterfactuals'].append({'comparison': name, 'metric': metric,
            **contrast(100 * table[a][metric], 100 * table[b][metric])})
    return result


def observed_snapshot(data):
    nodes = data['nodes']
    idle = sum(n['logicalCPU'] * (1 - n['cpuBusyPctLastShortSample'] / 100) for n in nodes)
    return {'date_jst': data['date'], 'sampled_nodes': len(nodes),
            'logical_cpu_installed': sum(n['logicalCPU'] for n in nodes),
            'installed_ram_GiB': sum(n['ramGiB'] for n in nodes),
            'noncontemporaneous_idle_core_equivalent': round(idle, 4),
            'data_volumes_at_least_90pct': sum(n['dataVolumeCapacityPct'] >= 90 for n in nodes),
            'qualified_offered_capacity': None, 'real_job_improvement': None,
            'limitations': ['short samples at different times; not a fleet utilization average',
                            'GPU, power, offered schedule, accepted job outcomes missing',
                            'CPU idle does not qualify memory, GPU, storage or network availability']}


def run(data, evidence, snapshot):
    validate(data)
    groups, extraction = communities(data)
    policies = [allocate(data, p, groups) for p in POLICIES]
    sensitivity = []
    # Predetermined grid, not calibrated to Awai or to Uber/Airbnb effect sizes.
    for reserve in (0, .1, .25, .4, .6):
        for seed in range(20):
            case = copy.deepcopy(data)
            for node in case['nodes']:
                for resource in ('cpu', 'memory', 'network'):
                    node['reserve'][resource] = reserve
            np.random.default_rng(seed).shuffle(case['jobs'])
            for p in ('fresh_fifo', 'optimized'):
                r = allocate(case, p, groups)
                sensitivity.append({'reserve_fraction': reserve, 'order_seed': seed,
                                    'policy': p, 'assigned_jobs': r['assigned_jobs'],
                                    'net_value_points': r['net_value_points']})
    empty = copy.deepcopy(data); empty['jobs'] = []
    # A preserved exchange community can lose a provider. It must not become
    # a hard eligibility boundary: a compatible external provider may remain.
    failure_control = []
    probe_job = next((j for j in data['jobs'] if j['kind'] == 'gpu'), None)
    if probe_job is not None and 'sim-gpu-a' in groups:
        failure = copy.deepcopy(data)
        failure['jobs'] = [copy.deepcopy(probe_job)]
        for node in failure['nodes']:
            if node['id'] == 'sim-gpu-a':
                node['available'] = False
        failure_control = [allocate(failure, p, groups) for p in ('optimized', 'ripo_hard_boundary')]
    return {'schema': PROFILE + '.result', 'input_sha256': hashlib.sha256(canonical_bytes(data)).hexdigest(),
            'evidence_sha256': hashlib.sha256(canonical_bytes(evidence)).hexdigest(),
            'snapshot_sha256': hashlib.sha256(canonical_bytes(snapshot)).hexdigest(),
            'literature_recalculation': literature(evidence), 'observed_snapshot': observed_snapshot(snapshot),
            'ripo_exchange_extraction': extraction, 'synthetic_policies': policies,
            'order_and_reserve_sensitivity': sensitivity,
            'boundary_failure_control': failure_control,
            'boundary_probe_status': 'computed' if failure_control else 'not_applicable_to_supplied_fixture',
            'empty_demand_control': allocate(empty, 'optimized', groups),
            'qualifications': {'real_jobs_executed': 0, 'causal_awai_improvement_estimated': False,
                               'kotoba_native_qualified': False, 'cid_persistence': False}}


def plot(result, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout='constrained')
    rows = result['literature_recalculation']['uber_time_utilization']
    x = np.arange(len(rows))
    axes[0].bar(x - .18, [r['taxi_pct'] for r in rows], .36, label='Taxi')
    axes[0].bar(x + .18, [r['uber_pct'] for r in rows], .36, label='UberX')
    axes[0].set(xticks=x, xticklabels=[r['city'] for r in rows], ylim=(0, 65),
                ylabel='Passenger hours / online hours (%)', title='Published observations (2013 vs 2015)')
    axes[0].legend()
    rows = result['synthetic_policies']
    axes[1].bar(range(len(rows)), [r['net_value_points'] for r in rows], color=['#888', '#a0b5c9', '#7099bb', '#21886f', '#b58759'])
    axes[1].set(xticks=range(len(rows)), xticklabels=['Directory\nonce', 'Fresh\nonce', 'Fresh\nFIFO', 'Global\nMILP', 'RIPO hard\nboundary'],
                ylabel='Net value (assumed points)', title='Synthetic allocation; not Awai measured gains')
    axes[1].set_ylim(0, max(1, max(r['net_value_points'] for r in rows)) * 1.2)
    for i, r in enumerate(rows):
        axes[1].annotate(f"{r['assigned_jobs']}/{r['demand_jobs']} assigned", (i, r['net_value_points']),
                         xytext=(0, 5), textcoords='offset points', ha='center', fontsize=8)
    fig.savefig(path, dpi=160, metadata={'Software': PROFILE})
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture', type=Path, default=Path('examples/awai-market.json'))
    p.add_argument('--evidence', type=Path, default=Path('data/market-evidence.json'))
    p.add_argument('--snapshot', type=Path, default=Path('data/awai-snapshot-20261031.json'))
    p.add_argument('--output', type=Path, default=Path('results/awai-market'))
    args = p.parse_args()
    try:
        result = run(*(json.loads(path.read_text()) for path in (args.fixture, args.evidence, args.snapshot)))
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        plot(result, args.output / 'comparison.png')
        print(json.dumps({'policies': [{k: r[k] for k in ('policy', 'assigned_jobs', 'net_value_points')} for r in result['synthetic_policies']],
                          'snapshot': result['observed_snapshot']}, indent=2))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as e:
        p.exit(2, f'market: {e}\n')


if __name__ == '__main__':
    main()

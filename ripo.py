"""Portable snapshot interface around the bounded v0.2 research engine."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from engine import groups, lineage, optimize, scenarios

PROFILE = 'ripo.snapshot-extraction.v0.3'


def canonical_bytes(value):
    """Canonical JSON for this profile, not DAG-CBOR or a CID encoding."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def validate_dataset(data):
    if not isinstance(data, dict) or data.get('schema') != 'ripo.snapshots.v1':
        raise ValueError('ripo.snapshots.v1 input required')
    required = {'schema', 'directed', 'signed', 'arity', 'relation_kind', 'frames'}
    if set(data) != required:
        raise ValueError('unexpected or missing dataset fields')
    if data['directed'] is not False or data['signed'] is not False or data['arity'] != 2:
        raise ValueError('only undirected, unsigned, binary snapshots; no silent projection')
    if data['relation_kind'] not in ('exchange', 'similarity', 'correlation'):
        raise ValueError('choose one declared relation kind; authority and causation are not inferred')
    frames = data['frames']
    if not isinstance(frames, list) or not frames:
        raise ValueError('nonempty snapshot sequence required')
    previous_step = -1
    previous_ids = set()
    for frame in frames:
        if not isinstance(frame, dict) or set(frame) != {'step', 'ids', 'adjacency', 'handoffs'}:
            raise ValueError('unexpected or missing snapshot fields')
        step = frame['step']
        if type(step) is not int or step < 0 or step <= previous_step:
            raise ValueError('strictly increasing nonnegative observation steps required')
        ids = frame['ids']
        if (not isinstance(ids, list) or not 1 <= len(ids) <= 8 or
                any(not isinstance(v, str) or not v for v in ids) or len(set(ids)) != len(ids)):
            raise ValueError('one to eight unique nonempty observation IDs required')
        matrix = frame['adjacency']
        if not isinstance(matrix, list) or len(matrix) != len(ids):
            raise ValueError('one adjacency row per observation')
        for i, row in enumerate(matrix):
            if not isinstance(row, list) or len(row) != len(ids):
                raise ValueError('square adjacency required')
            if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in row):
                raise ValueError('finite nonnegative numeric weights required')
            if row[i] != 0:
                raise ValueError('self loops are outside this profile')
        if any(matrix[i][j] != matrix[j][i] for i in range(len(ids)) for j in range(len(ids))):
            raise ValueError('exact symmetric input required; no automatic symmetrization')
        handoffs = frame['handoffs']
        if not isinstance(handoffs, list):
            raise ValueError('handoffs must be an explicit list')
        for pair in handoffs:
            if (not isinstance(pair, list) or len(pair) != 2 or
                    any(not isinstance(v, str) for v in pair) or
                    pair[0] not in previous_ids or pair[1] not in ids):
                raise ValueError('handoff must connect previous/current observed IDs')
        previous_step, previous_ids = step, set(ids)
    # Enforce finite JSON even in fields not inspected numerically.
    canonical_bytes(data)
    return data


def extract(data, tau=1.0):
    validate_dataset(data)
    if type(tau) not in (int, float) or not math.isfinite(tau) or tau < 0:
        raise ValueError('finite nonnegative Markov time required')
    tau = float(tau)
    input_sha = hashlib.sha256(canonical_bytes(data)).hexdigest()
    identity = {'input_sha256': input_sha, 'profile': PROFILE, 'tau': tau}
    run_sha = hashlib.sha256(canonical_bytes(identity)).hexdigest()
    frames, correspondences = [], []
    for frame in data['frames']:
        # Unknown intermediate observations are not bridged across a gap.
        result = optimize(frame['adjacency'], tau)
        result.pop('seconds')
        candidate_groups = groups(frame['ids'], result['labels'])
        if frames:
            gap = frame['step'] != frames[-1]['step'] + 1
            if gap:
                # Evidence across missing steps needs a different profile.
                links = {'links': [], 'unlinked_after': list(range(len(candidate_groups))),
                         'status': 'observation_gap_unresolved'}
            else:
                links = lineage(frames[-1]['groups'], candidate_groups, frame['handoffs'])
                links['status'] = 'evidence_correspondence_only'
            correspondences.append({'before_step': frames[-1]['step'],
                                    'after_step': frame['step'], **links})
        frames.append({'step': frame['step'], 'ids': frame['ids'], 'groups': candidate_groups,
                       'assessment': result})
    return {'schema': PROFILE, 'run_sha256': run_sha, **identity,
            'time_semantics': 'ordered observation steps; physical windows not supplied',
            'relation_kind': data['relation_kind'], 'frames': frames,
            'correspondences': correspondences,
            'interpretation': 'candidate partitions and supplied correspondence evidence, not numerical identity',
            'persistence': 'canonical JSON + SHA-256 in this reference profile; not IPLD/CID',
            'qualification': {'input_origin': 'caller_supplied_not_independently_verified', 'empirical_validation': False,
                              'causal_autonomy_inferred': False, 'kotoba_runtime_integrated': False}}


def fixture(name='stable'):
    scenario = next(s for s in scenarios() if s['key'] == name)
    return {'schema': 'ripo.snapshots.v1', 'directed': False, 'signed': False,
            'arity': 2, 'relation_kind': 'correlation' if name == 'common_driver' else 'exchange',
            'frames': [{'step': f['t'], 'ids': f['ids'], 'adjacency': f['adjacency'],
                        'handoffs': f['handoffs']} for f in scenario['frames']]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    f = commands.add_parser('fixture'); f.add_argument('--scenario', default='stable',
        choices=[s['key'] for s in scenarios()]); f.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('extract'); p.add_argument('input', type=Path)
    p.add_argument('--tau', type=float, default=1.0); p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = fixture(args.scenario) if args.command == 'fixture' else extract(
            json.loads(args.input.read_text(encoding='utf-8')), args.tau)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    except (ValueError, TypeError, OSError) as error:
        parser.exit(2, f'ripo: {error}\n')


if __name__ == '__main__':
    main()

"""Descriptive live-pilot summary; incomplete runs cannot certify improvement."""
import statistics


def summarize_trials(trials, planned=8):
    completed = []
    for row in trials:
        results = row.get('results', [])
        if row.get('terminal', {}).get('event') != 'complete':
            continue
        if len(results) != 1 or results[0].get('quality_pass') is not True:
            raise ValueError('completed trial lacks one quality-accepted result')
        if results[0].get('violations'):
            raise ValueError('guard violation cannot be accepted')
        completed.append(results[0])
    arms = {}
    for mode, label in ((None, 'current_default'), (True, 'explicit_cache_true')):
        seconds = [r['seconds'] for r in completed if r.get('cache_prompt') is mode]
        arms[label] = {'n': len(seconds), 'seconds': seconds,
                       'mean_seconds': statistics.mean(seconds) if seconds else None}
    complete = len(completed) == planned
    baseline = arms['current_default']['mean_seconds']
    candidate = arms['explicit_cache_true']['mean_seconds']
    return {'planned_trials': planned, 'completed_trials': len(completed),
            'status': 'complete_exploratory_pilot' if complete else 'stopped_early',
            'arms': arms,
            'descriptive_latency_reduction_pct': 100 * (1 - candidate / baseline)
                if baseline is not None and candidate is not None else None,
            'qualified_awai_improvement_pct': None,
            'interpretation': 'small technical replay; no natural-demand or fleet causal estimate',
            'customer_accepted_outcomes': None}


def plot_summary(summary, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.5))
    fig.subplots_adjust(bottom=.23, left=.12, right=.98, top=.88)
    for i, key in enumerate(('current_default', 'explicit_cache_true')):
        arm = summary['arms'][key]
        if arm['mean_seconds'] is None:
            continue
        ax.bar(i, arm['mean_seconds'], width=.5, color=['#617d98', '#608a83'][i], alpha=.6)
        ax.scatter([i + (j - (arm['n'] - 1) / 2) * .12 for j in range(arm['n'])],
                   arm['seconds'], color='black', s=30, zorder=3)
        ax.text(i, arm['mean_seconds'] + .22, f"{arm['mean_seconds']:.4f}s; n={arm['n']}", ha='center')
    ax.set(xticks=[0, 1], xticklabels=['Current default', 'Explicit cache=true'],
           ylabel='Localhost HTTP completion seconds', ylim=(0, 6.6),
           title='Native Mishima: no additional improvement established')
    ax.title.set_fontsize(11)
    fig.text(.5, .04, 'Planned 8, completed 4; stopped before next request when backend was busy.\n'
             '709 input / 49 output tokens. Replay; no fleet or customer-effect estimate.', ha='center', fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=Path('results/awai-live/summary.json'))
    parser.add_argument('--figure', type=Path, default=Path('results/awai-live/latency.png'))
    args = parser.parse_args()
    plot_summary(json.loads(args.summary.read_text()), args.figure)

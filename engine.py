"""Finite, auditable RIPO individuation experiment. No ontology-of-reality claim."""
from functools import lru_cache
import hashlib
import json
import math
import time
import numpy as np
from scipy.linalg import expm

VERSION = '0.2.0'
SCALES = [0.1, 0.3, 1.0, 3.0, 10.0]


@lru_cache(None)
def partitions(n):
    """Restricted growth strings: every set partition exactly once, n <= 8."""
    if not 1 <= n <= 8:
        raise ValueError('exact prototype requires 1 <= n <= 8')
    out = []
    def rec(p, largest):
        if len(p) == n:
            out.append(p)
            return
        for k in range(largest + 2):
            rec(p + [k], max(k, largest))
    rec([0], 0)
    return np.asarray(out, dtype=np.int8)


@lru_cache(None)
def masks(n):
    p = partitions(n)
    return (p[:, :, None] == p[:, None, :]).reshape(len(p), -1)


def validate(a):
    try:
        a = np.asarray(a, dtype=float)
    except (OverflowError, TypeError) as error:
        raise ValueError('weights must fit finite floating-point arithmetic') from error
    if a.ndim != 2 or a.shape[0] != a.shape[1] or not 1 <= len(a) <= 8:
        raise ValueError('square 1..8 adjacency required')
    if not np.isfinite(a).all() or (a < 0).any():
        raise ValueError('finite nonnegative weights required')
    if not np.allclose(a, a.T) or not np.allclose(np.diag(a), 0):
        raise ValueError('this prototype accepts undirected graphs without self loops')
    try:
        math.fsum(a.flat)
    except OverflowError as error:
        raise ValueError('total weight exceeds finite floating-point range; rescale input') from error
    return a


def kernel(a, tau):
    a = validate(a)
    if not np.isfinite(tau) or tau < 0:
        raise ValueError('finite nonnegative Markov time required')
    d = a.sum(axis=1)
    if (d == 0).any():
        raise ValueError('kernel undefined for isolated observations: abstain instead')
    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            p = expm(tau * (a / d[:, None] - np.eye(len(a))))
    except (FloatingPointError, OverflowError) as error:
        raise ValueError('Markov time exceeds the numerical range of this solver') from error
    if not np.isfinite(p).all():
        raise ValueError('Markov time produced a nonfinite transition kernel')
    pi = d / d.sum()
    return np.diag(pi) @ p - np.outer(pi, pi), p, pi


def optimize(a, tau=1.0, method='stability'):
    """Globally optimize the *fixed-tau* objective, not minimum over 0..tau."""
    started = time.perf_counter()
    a = validate(a)
    if method not in ('stability','modularity'):
        raise ValueError('unknown method')
    if method=='stability' and (not np.isfinite(tau) or tau<0):
        raise ValueError('finite nonnegative Markov time required')
    d = a.sum(axis=1)
    active = np.flatnonzero(d > 0)
    isolated = np.flatnonzero(d == 0)
    if not len(active):
        return dict(labels=list(range(len(a))), score=None, gap=None, ties=None,
                    status='no_relational_evidence', evaluated=0,
                    seconds=time.perf_counter()-started, isolated=isolated.tolist())
    aa = a[np.ix_(active, active)]
    if method == 'stability':
        b, _, _ = kernel(aa, tau)
    elif method == 'modularity':
        dd = aa.sum(axis=1)
        b = aa / dd.sum() - np.outer(dd, dd) / dd.sum()**2
    else:
        raise ValueError('unknown method')
    scores = np.einsum('ij,j->i', masks(len(active)), b.ravel(), optimize=False)
    if not np.isfinite(scores).all():
        raise ValueError('objective exceeds finite floating-point range')
    best = float(scores.max())
    tied = np.flatnonzero(np.abs(scores-best) <= 1e-10)
    chosen = partitions(len(active))[tied[0]].astype(int)
    labels = np.empty(len(a), dtype=int)
    labels[active] = chosen
    labels[isolated] = np.arange(len(isolated)) + chosen.max() + 1
    lower = scores[scores < best - 1e-10]
    return dict(labels=labels.tolist(), score=best,
                gap=best-float(lower.max()) if len(lower) else None,
                ties=len(tied), status='tied_optima' if len(tied)>1 else 'candidate',
                evaluated=len(scores), seconds=time.perf_counter()-started,
                isolated=isolated.tolist())


def groups(ids, labels):
    return [[ids[i] for i, x in enumerate(labels) if x == c] for c in sorted(set(labels))]


def lineage(before, after, handoffs=()):
    """Evidence-supported correspondence only. Never numerical identity."""
    previous = set().union(*map(set, before))
    current = set().union(*map(set, after))
    for a,b in handoffs:
        if a not in previous or b not in current:
            raise ValueError('handoff endpoint absent from adjacent observations')
    links=[]
    for i,left in enumerate(before):
        for j,right in enumerate(after):
            overlap=sorted(set(left)&set(right))
            evidence=[list(h) for h in handoffs if h[0] in left and h[1] in right]
            if overlap or evidence:
                links.append(dict(source=i,target=j,overlap=overlap,handoffs=evidence))
    for link in links:
        out=sum(e['source']==link['source'] for e in links)
        inc=sum(e['target']==link['target'] for e in links)
        link['kind']=('split_merge' if out>1 and inc>1 else 'split' if out>1 else
                      'merge' if inc>1 else 'handoff' if link['handoffs'] else 'member_continuity')
    return dict(links=links,unlinked_after=[j for j in range(len(after))
               if not any(e['target']==j for e in links)])


def two_blocks(bridge=0.025):
    a = np.full((8,8), bridge)
    a[:4,:4]=1.0; a[4:,4:]=1.0
    np.fill_diagonal(a,0)
    return a


def scenarios(seed=654):
    rng=np.random.default_rng(seed)
    out=[]
    titles={
      'stable':'弱結合の二つの集団',
      'replacement':'全成員交代・引継ぎ証拠あり',
      'copy':'同型コピー・引継ぎ証拠なし',
      'split_merge':'分岐と合流',
      'common_driver':'共通原因による見かけの同期',
      'open_system':'強い外部交換を持つ開放系'}
    notes={
      'stable':'関係の弱い切れ目が尺度に応じて抽出される。',
      'replacement':'t=3でa→rへ全面交代。継承の根拠は入力した引継ぎ記録。',
      'copy':'t=3でb→cへ交代。同型であるだけでは継承を結ばない。',
      'split_merge':'一群→二群→一群。分岐・合流は同一性の断言ではない。',
      'common_driver':'共通の外因Zが8変数を駆動。相関グラフ上の集団を主体と誤認しない。',
      'open_system':'内部0..3と環境4..7の交換が強い。既知の領域区分は推定器に渡さない。'}
    for key,title in titles.items():
        frames=[]
        for t in range(6):
            ids=[f'a{i}' for i in range(4)]+[f'b{i}' for i in range(4)]
            a=two_blocks()
            handoffs=[]
            if key=='replacement' and t>=3:
                ids=[f'r{i}' for i in range(4)]+[f'b{i}' for i in range(4)]
                if t==3: handoffs=[[f'a{i}',f'r{i}'] for i in range(4)]
            if key=='copy' and t>=3:
                ids=[f'a{i}' for i in range(4)]+[f'c{i}' for i in range(4)]
            if key=='split_merge' and t in [2,3]:
                # Each four-member process splits into two pairs; no labels are
                # passed to inference. Whole system is 2 -> 4 -> 2 candidates.
                a=np.full((8,8),0.002)
                a[:4,:4]=0.025;a[4:,4:]=0.025
                for j in range(0,8,2):a[j:j+2,j:j+2]=1
                np.fill_diagonal(a,0)
            extra={}
            if key=='common_driver':
                z=rng.normal(size=(512,1))
                x=z+0.2*rng.normal(size=(512,8))
                a=np.corrcoef(x,rowvar=False)
                np.fill_diagonal(a,0)
                a=np.maximum(a,0)
                extra={'known_mechanism':'Z -> each observation; no internal causal edges',
                       'mechanism_adjacency':np.zeros((8,8)).tolist()}
            if key=='open_system':
                a=two_blocks(2.0)
            frames.append(dict(t=t,ids=ids,adjacency=a.tolist(),handoffs=handoffs,**extra))
        if key=='split_merge':notes[key]='二群→四群→二群。各集団の分岐・合流を追跡する。'
        out.append(dict(key=key,title=title,note=notes[key],frames=frames))
    return out


def perturbation(a, tau, draws=20):
    """Weight perturbation sensitivity; NOT posterior or sampling confidence."""
    rng=np.random.default_rng(654)
    a=np.asarray(a)
    records=[]; co=np.zeros(a.shape)
    for _ in range(draws):
        noise=np.exp(0.15*rng.normal(size=a.shape))
        noise=np.triu(noise,1);noise=noise+noise.T
        labels=optimize(a*noise,tau)['labels']
        arr=np.asarray(labels)
        co += arr[:,None]==arr[None,:]
        records.append(labels)
    return dict(draws=draws,seed=654,lognormal_sigma=0.15,
                coassignment=(co/draws).tolist(),partitions=records,
                interpretation='perturbation robustness, not probability of existence')


def run():
    started=time.perf_counter()
    data=scenarios()
    inputs=json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    for scenario in data:
        for frame in scenario['frames']:
            frame['results']={str(tau):optimize(frame['adjacency'],tau) for tau in SCALES}
            frame['modularity']=optimize(frame['adjacency'],method='modularity')
            if 'mechanism_adjacency' in frame:
                frame['mechanism_result']=optimize(frame['mechanism_adjacency'])
        scenario['lineages']={}
        for tau in SCALES:
            histories=[]
            for left,right in zip(scenario['frames'],scenario['frames'][1:]):
                l=groups(left['ids'],left['results'][str(tau)]['labels'])
                r=groups(right['ids'],right['results'][str(tau)]['labels'])
                histories.append(lineage(l,r,right['handoffs']))
            scenario['lineages'][str(tau)]=histories
    sensitivity=perturbation(two_blocks(),1.0)
    return dict(version=VERSION,seed=654,scales=SCALES,scenarios=data,
                input_sha256=hashlib.sha256(inputs).hexdigest(),
                sensitivity=sensitivity,interventions=intervention_experiment(),
                seconds=time.perf_counter()-started,
                scope='synthetic undirected nonnegative binary relations, at most 8 observations',
                method='fixed-time continuous-time Markov Stability, exact enumeration',
                limitations=['no causal autonomy inference','no BFO alignment proof',
                  'no SBM/coherent-set/blanket implementation','no empirical validation',
                  'lineage uses explicit member and handoff evidence, not identity'])


def intervention_experiment():
    """Known linear structural model, not causality inferred from correlations.

    x1'=0.45*x1+0.45*x2+0.1*u; x2'=0.45*x2+0.45*x1+0.1*u.
    u=1; x(0)=0. Baseline equilibrium is (1,1). Removing both internal
    cross-links yields (2/11,2/11); removing both inputs yields (0,0).
    Intervention magnitudes differ; no normalized causal-score comparison.
    """
    rows=[]
    for name,coupling,drive in [('baseline',.45,.1),('cut_internal',0,.1),
                                ('cut_external',.45,0)]:
        x=np.zeros(2);states=[x.tolist()]
        for _ in range(100):
            x=np.array([[.45,coupling],[coupling,.45]])@x+drive
            states.append(x.tolist())
        rows.append(dict(name=name,states=states,final_mean=float(x.mean()),
                         analytic_equilibrium=drive/(1-.45-coupling)))
    return dict(model="x1'=0.45*x1+0.45*x2+0.1*u; x2'=0.45*x2+0.45*x1+0.1*u; u=1",
                interpretation='Recovery to an input-supported equilibrium in a known toy SCM; not biological autonomy.',
                results=rows)


if __name__=='__main__':
    from pathlib import Path
    dest=Path(__file__).parent/'results';dest.mkdir(exist_ok=True)
    result=run()
    (dest/'experiment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'seconds':result['seconds'],'scenarios':len(result['scenarios']),
          'optimizations':6*6*(len(SCALES)+1)+6+20,'sha256':result['input_sha256']}))


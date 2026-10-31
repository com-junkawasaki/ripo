"""Render exact outputs, export JSON-LD, and embed measured results in a viewer."""
from pathlib import Path
import argparse
import json, platform, sys
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT=Path(__file__).parent
parser=argparse.ArgumentParser()
parser.add_argument('--inline-path',type=Path,help='Optional conversation fragment output')
args=parser.parse_args()
OUT=ROOT/'results'
data=json.loads((OUT/'experiment.json').read_text())
positions={
 'grid':[[.20,.30],[.34,.30],[.20,.64],[.34,.64],
         [.66,.30],[.80,.30],[.66,.64],[.80,.64]],
 'circle':[[.5+.32*np.cos(i*np.pi/4),.5+.32*np.sin(i*np.pi/4)] for i in range(8)]}
cache={}
for s in data['scenarios']:
    for frame in s['frames']:
        for res in frame['results'].values():
            key=','.join(map(str,res['labels']))
            if key in cache:continue
            cache[key]={}
            for layout,coords in positions.items():
                grid=np.linspace(-.4,1.4,100)
                xx,yy=np.meshgrid(grid,grid)
                paths=[]
                for c in sorted(set(res['labels'])):
                    field=np.zeros(xx.shape)
                    for i,(x,y) in enumerate(coords):
                        if res['labels'][i]==c:
                            field+=np.exp(-((xx-x)**2+(yy-y)**2)/(2*.10**2))
                    field/=field.max()
                    fig,ax=plt.subplots()
                    cs=ax.contour(xx,yy,field,levels=[.35])
                    segments=[np.round(seg,4).tolist() for seg in cs.allsegs[0] if len(seg)>3]
                    if any(np.linalg.norm(np.asarray(seg[0])-np.asarray(seg[-1]))>.001 for seg in segments):
                        raise AssertionError('contour clipped; expand rendering grid')
                    paths.append({'group':c,'segments':segments})
                    plt.close(fig)
                cache[key][layout]=paths
data['rendering']={'positions':positions,'contours':cache,'sigma':.10,'level':.35}

# Save data separate from the HTML so all visual claims can be audited.
(OUT/'viewer-data.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
fragment=(ROOT/'viewer.fragment.html').read_text().replace('__EXPERIMENT_JSON__',
    json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
if args.inline_path:
    args.inline_path.write_text(fragment)
css='''html{color-scheme:light dark}body{font:15px system-ui;max-width:960px;margin:32px auto;padding:0 18px;--foreground:light-dark(#17212b,#e5edf2);--background:light-dark(#fff,#10151c);--border:light-dark(#c3ccd5,#495765);--muted-foreground:light-dark(#556473,#b4c0cb);--viz-series-1:light-dark(#216aa5,#73baff);--viz-series-2:light-dark(#b85c13,#ffb36e);--viz-series-3:light-dark(#337f51,#7edfa0);--viz-series-4:light-dark(#884ca8,#d6a1ee);--viz-series-5:light-dark(#a4415c,#f397b1);--viz-series-6:light-dark(#3c7d85,#88d2dc);color:var(--foreground);background:var(--background)}select,input,button{font:inherit}select,button{padding:7px;margin:4px} .viz-controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.form-label{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.form-range{width:100%}.text-small{font-size:13px}.text-muted{color:var(--muted-foreground)}h3{font-size:20px;font-weight:500}'''
(ROOT/'viewer.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RIPO Computation Lab</title><style>'+css+'</style>'+fragment+'</html>')

names=['Two weakly linked blocks','Complete member replacement','Copy without handoff',
       'Split and merge','Common external driver','Strong external exchange']
palette=plt.get_cmap('tab10').colors
fig,axs=plt.subplots(3,2,figsize=(12,11),layout='constrained')
for ax,s,name in zip(axs.flat,data['scenarios'],names):
    for f in s['frames']:
        labs=f['results']['1.0']['labels']
        for c in sorted(set(labs)):
            members=np.flatnonzero(np.asarray(labs)==c)
            ax.add_patch(FancyBboxPatch((f['t']-.14,members.min()-.30),.28,
                members.max()-members.min()+.6,boxstyle='round,pad=0.03',
                facecolor=palette[c%10],edgecolor='none',alpha=.22))
        for i,l in enumerate(labs):ax.scatter(f['t'],i,color=palette[l%10],s=13)
    for t,lin in enumerate(s['lineages']['1.0']):
        left=s['frames'][t]['results']['1.0']['labels']
        right=s['frames'][t+1]['results']['1.0']['labels']
        for e in lin['links']:
            y1=np.flatnonzero(np.asarray(left)==e['source']).mean()
            y2=np.flatnonzero(np.asarray(right)==e['target']).mean()
            ax.plot([t+.17,t+.83],[y1,y2],color='#54616e',lw=1,
                    ls='--' if e['kind']=='handoff' else '-',alpha=.65)
    ax.set(title=name,xlabel='Observation step t',ylabel='Display slot (not physical space)',
           xticks=range(6),ylim=(-.6,7.6),yticks=[0,3,4,7])
    ax.spines[['top','right']].set_visible(False)
fig.suptitle('Computed candidate memberships and evidence-backed correspondence | Markov time = 1\nSynthetic data; solid: member overlap; dashed: supplied handoff; no identity claim',fontsize=14)
fig.savefig(OUT/'lineage-cases.png',dpi=160);plt.close(fig)

fig,ax=plt.subplots(figsize=(8,4.2),layout='constrained')
for r,color,label in zip(data['interventions']['results'],palette,
 ['Baseline: input + internal coupling','Remove internal cross-links','Remove external inputs']):
    ax.plot(np.mean(r['states'],axis=1),label=label,color=color,lw=2)
ax.set(xlabel='Simulation step',ylabel='Mean state (dimensionless)',
       title='Known toy structural model: recovery depends on internal AND external relations')
ax.legend(frameon=False);ax.spines[['top','right']].set_visible(False)
fig.savefig(OUT/'interventions.png',dpi=160);plt.close(fig)

fig=plt.figure(figsize=(9,6),layout='constrained')
ax=fig.add_subplot(projection='3d')
s=next(s for s in data['scenarios'] if s['key']=='split_merge')
for f in s['frames']:
    labs=f['results']['1.0']['labels']
    for c in cache[','.join(map(str,labs))]['grid']:
        for seg in c['segments']:
            pts=np.asarray(seg)
            ax.plot(pts[:,0],np.full(len(pts),f['t']),pts[:,1],
                    color=palette[c['group']],alpha=.8,lw=1.5)
ax.set(xlabel='Relational display x',ylabel='Observation step t',
       zlabel='Relational display y',yticks=range(6),
       title='Computed contour slices through time: 2 blocks -> 4 -> 2\nDisplay coordinates, not physical spacetime; no interpolated surface')
ax.view_init(elev=22,azim=-55)
fig.savefig(OUT/'temporal-contours-3d.png',dpi=160);plt.close(fig)

ctx={'ripo':'https://example.org/ripo-experimental/0.2#',
     'prov':'http://www.w3.org/ns/prov#',
     'members':{'@id':'ripo:member','@type':'@id'},
     'generatedBy':{'@id':'prov:wasGeneratedBy','@type':'@id'},
     'hypothesis':{'@id':'ripo:aboutHypothesis','@type':'@id'},
     'from':{'@id':'ripo:sourceHypothesis','@type':'@id'},
     'to':{'@id':'ripo:targetHypothesis','@type':'@id'}}
graph=[{'@id':'urn:ripo:run:654-v02','@type':['ripo:ExtractionRun','prov:Activity'],
        'ripo:inputSHA256':data['input_sha256'],'ripo:algorithmVersion':data['version'],
        'ripo:markovTime':1.0,'ripo:synthetic':True}]
for s in data['scenarios']:
    for f in s['frames']:
        labs=f['results']['1.0']['labels']
        for c in sorted(set(labs)):
            hid=f"urn:ripo:{s['key']}:t{f['t']}:c{c}"
            members=[f'urn:ripo:observation:{s["key"]}:{v}' for i,v in enumerate(f['ids']) if labs[i]==c]
            graph.append({'@id':hid,'@type':'ripo:IndividuationHypothesis','members':members,
                          'ripo:observationStep':f['t'],'generatedBy':'urn:ripo:run:654-v02'})
            graph.append({'@id':hid+':boundary','@type':'ripo:BoundaryRepresentation',
                          'hypothesis':hid,'ripo:displayLayout':'grid','ripo:sigma':.10,'ripo:level':.35})
            for m in members:
                graph.append({'@type':'ripo:MembershipAssessment','hypothesis':hid,
                              'members':m,'ripo:membershipValue':1.0})
    for t,lin in enumerate(s['lineages']['1.0']):
        for i,e in enumerate(lin['links']):
            graph.append({'@id':f'urn:ripo:{s["key"]}:lineage:{t}:{i}',
                 '@type':'ripo:LineageAssertion','from':f'urn:ripo:{s["key"]}:t{t}:c{e["source"]}',
                 'to':f'urn:ripo:{s["key"]}:t{t+1}:c{e["target"]}',
                 'ripo:correspondenceKind':e['kind'],'ripo:evidenceJSON':json.dumps(e),
                 'generatedBy':'urn:ripo:run:654-v02'})
(OUT/'hypotheses.jsonld').write_text(json.dumps({'@context':ctx,'@graph':graph},ensure_ascii=False,indent=2))
(OUT/'runtime.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),
 'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__},indent=2))
print(json.dumps({'contour_patterns':len(cache),'jsonld_records':len(graph),
                  'viewer_bytes':len(fragment.encode()),'experiment_seconds':data['seconds']}))


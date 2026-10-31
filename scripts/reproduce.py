"""Regenerate measured artifacts, failing immediately on any failed check."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT/'results'
RESULTS.mkdir(exist_ok=True)
env = dict(os.environ, OPENBLAS_NUM_THREADS='1')


def run(command, log=None):
    if log:
        with (RESULTS/log).open('w', encoding='utf-8') as stream:
            subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                           stderr=subprocess.STDOUT, check=True)
    else:
        subprocess.run(command, cwd=ROOT, env=env, check=True)


run([sys.executable,'-m','unittest','discover','-v'], 'tests.txt')
run([sys.executable,'engine.py'])
run([sys.executable,'build.py'])
run([sys.executable,'scripts/validate_rdf.py'], 'rdf-validation.json')
run(['node','test_viewer.cjs'], 'viewer-test.json')
run([sys.executable,'ripo.py','fixture','--scenario','replacement','--output','examples/replacement.json'])
run([sys.executable,'ripo.py','extract','examples/replacement.json','--tau','1',
     '--output','results/replacement-profile.json'])
print('Python tests, RDF/SHACL controls, SPARQL, viewer logic and CLI reproduction passed.')

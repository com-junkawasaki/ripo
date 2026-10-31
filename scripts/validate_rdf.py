"""Bounded RDF/SHACL checks; no network, OWL consistency or truth inference."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
from rdflib import Graph, Literal, Namespace, RDF, XSD, OWL
from pyshacl import validate

ROOT = Path(__file__).resolve().parents[1]
R = Namespace('https://example.org/ripo-experimental/0.2#')
SH = Namespace('http://www.w3.org/ns/shacl#')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def verify():
    vocabulary = Graph().parse(ROOT/'vocabulary.jsonld', format='json-ld')
    graph = Graph().parse(ROOT/'results/hypotheses.jsonld', format='json-ld')
    shapes = Graph().parse(ROOT/'ontology/individuation-shapes.ttl')
    conforms, _, text = validate(graph, shacl_graph=shapes, ont_graph=vocabulary, inference='none')
    require(conforms, text)
    require(not list(graph.triples((None, OWL.sameAs, None))), 'Lineage asserted numerical identity')
    for evidence in graph.objects(None, R.evidenceJSON):
        value = json.loads(str(evidence))
        require(value['overlap'] or value['handoffs'], 'Unsupported lineage assertion')
    # Mutate actual generated records, not a second hand-authored fixture.
    membership = next(graph.subjects(RDF.type, R.MembershipAssessment))
    boundary = next(graph.subjects(RDF.type, R.BoundaryRepresentation))
    lineage = next(graph.subjects(RDF.type, R.LineageAssertion))
    changes = [
        (membership, R.membershipValue, Literal(2.0), SH.MaxInclusiveConstraintComponent),
        (boundary, R.aboutHypothesis, None, SH.MinCountConstraintComponent),
        (lineage, R.evidenceJSON, None, SH.MinCountConstraintComponent),
    ]
    for node, predicate, value, expected in changes:
        bad = deepcopy(graph); bad.remove((node,predicate,None))
        if value is not None: bad.add((node,predicate,value))
        ok, report, _ = validate(bad, shacl_graph=shapes, ont_graph=vocabulary, inference='none')
        require(not ok and any((n,SH.focusNode,node) in report for n in
                report.subjects(SH.sourceConstraintComponent,expected)), 'Negative control failed')
    # The article's original transition example is a distinct namespace/profile.
    core = Graph().parse(ROOT/'ontology/core.ttl')
    example = Graph().parse(ROOT/'ontology/example.ttl')
    transition_shapes = Graph().parse(ROOT/'ontology/shapes.ttl')
    ok, _, text = validate(example, shacl_graph=transition_shapes, ont_graph=core, inference='none')
    require(ok,text)
    rows=list(example.query((ROOT/'ontology/changes.rq').read_text()))
    require(len(rows)==1 and rows[0].delta.toPython()==Decimal('1.0'), 'Wrong transition delta')
    print(json.dumps({'hypothesis_triples':len(graph),'hypothesis_records':len(json.loads(
        (ROOT/'results/hypotheses.jsonld').read_text())['@graph']),
        'shacl_conforms':True,'negative_controls':len(changes),
        'lineage_sameAs':False,'transition_query_delta':'1.0',
        'limits':'bounded RDF/SHACL; not OWL consistency, empirical truth or BFO/Inc conformance'}))


if __name__ == '__main__': verify()

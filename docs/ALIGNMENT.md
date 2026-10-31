# Alignment policy

The illustrative article vocabulary (`https://example.org/ripo/0.1#`) and experimental individuation vocabulary (`https://example.org/ripo-experimental/0.2#`) are separate profiles. Their differing version numbers do not make one a validated semantic extension of the other. No production IRI service is deployed.

| RIPO record or referent | Candidate target | Conditions before an executable axiom |
|---|---|---|
| ExtractionRun | PROV Activity | A concrete run uses versioned inputs and generates records |
| IndividuationHypothesis / MembershipAssessment | PROV Entity; possible CCO information content entity | Distinguish content, physical bearer and represented process; pin CCO release |
| BoundaryRepresentation | Information representation | Do not equate it with an Inc boundary or physical interface |
| LineageAssertion | Evidence-backed claim/record | No implication of owl:sameAs or unique personal continuity |
| Observation occurrence | BFO process / PROV Activity | Specify temporal extent and observation interpretation |
| Physical instrument | BFO material entity | Separate instrument from output and modeled state |

PROV reuse is a record-level choice, not a guarantee of authenticity. BFO/CCO candidate mappings remain prose annotations; there are no imports or equivalence axioms. A future alignment needs pinned artifacts, satisfiability/entailment regression tests and competency questions. SHACL validates only the selected recorded-data constraints.

Primary references: [BFO artifacts](https://github.com/BFO-ontology/BFO-2020), [CCO](https://github.com/CommonCoreOntology/CommonCoreOntologies), [PROV-O](https://www.w3.org/TR/prov-o/), [SHACL 2017](https://www.w3.org/TR/2017/REC-shacl-20170720/).

# RIPO: from process ontology to a bounded calculation

RIPO treats relation, realized information, becoming and inheritance as explanatory commitments. The calculations here are operational hypotheses about observations. There is no deduction from a dense graph to life, a subject, selfhood or a physical boundary.

## Four questions, five recorded objects

| Question | Formal/computational responsibility | Output |
|---|---|---|
| Constitution: what becomes an individual? | Choose variables, relation kind, observation window and a model | IndividuationHypothesis |
| Interaction: which relations matter? | Retain typed/role-bearing observations; reject unsupported projections | Input snapshot and declared model scope |
| Evolution: what persists or is inherited? | Compare independent snapshots using member and explicit handoff evidence | LineageAssertion with support or unresolved gaps |
| Epistemology: how is it known? | Separate computation, claim, observation and assessment | ExtractionRun and MembershipAssessment |
| How should it be shown? | Derive a contour from membership and layout | BoundaryRepresentation |

Inc Boundary, a physical interface, a statistical blanket, an authorization boundary and a display contour have different meanings. Inc bisimulation is observation equivalence, not numerical identity. Resonance specifies admissible modes; a dated occurrence needs dynamics and evidence. The independent Inc source remains at revision `1bb368dc35827133cf42f7e4191f41cbfc754b1f`; no Inc/OWL/BFO equivalence theorem is claimed here.

## Implemented pipeline

1. Supply explicit snapshots, each with up to eight distinct observation IDs and a symmetric nonnegative adjacency. Physical windows and edge construction belong to the supplying study; the current CLI does not infer them from an event stream.
2. Compute `P(tau)=exp[tau(D^-1 A-I)]`, `B=diag(pi)P-pi pi^T`, and maximize `sum B_ij` within blocks over all set partitions. Isolates are reported separately; no relationships means abstention. `tau` is diffusion resolution, not physical time.
3. Retain score, tolerance ties, gap and partition. The exact finite search is conditional on the objective, the input and floating point. It does not optimize the choice of ontology.
4. Emit a many-to-many correspondence when observed IDs overlap or supplied handoffs support it. Copy resemblance gives no lineage. A missing step remains unresolved.
5. Render Gaussian-sum level sets in a declared display layout. The current membership is hard 0/1; contours are smooth display fields, not soft membership or calibrated uncertainty. Layout changes do not change extraction or lineage.
6. Export records and validate their shape. RDF reasoning cannot validate a sensor or establish a claim's truth. Hashes preserve byte identity under a stated recipe, not provenance authenticity.

## Six approaches and their current status

| Approach | What it could test | Status here |
|---|---|---|
| Degree-corrected/hierarchical SBM | Connection-generating roles/blocks and model selection | Planned; modularity is the implemented structural baseline, not an SBM substitute |
| Markov Stability | Retention/recurrence under a specified diffusion at multiple resolutions | Implemented finite fixed-time objective; no physical persistence claim |
| Coherent sets | Finite-time material/state-space transport coherence | Planned; trajectory/transfer data needed |
| Markov blanket | Conditional statistical separation of selected variables | Planned; no membrane, subjecthood or causal autonomy implied |
| Causal maintenance | Recovery/organization under interventions | Only a separate specified two-variable toy SCM, not causal discovery or a normalized autonomy score |
| Alpha shape / density contour | A representation of candidates in coordinates | Gaussian-sum level-set display implemented; alpha shapes not implemented |

The six methods ask different questions. They must not be collapsed into a weighted “existence score.” The Markov method implemented here is the fixed-time trace objective; it does not minimize the trace over every diffusion time from zero to tau.

## Counterexamples and evaluation obligations

The stable two-block fixture, all-member replacement, copy without handoff, split/merge, common external driver and strong external exchange are implemented. The complete-graph formula is `exp[-n tau/(n-1)] * (1 - sum_C(|C|/n)^2)`: finite-time maximization yields singletons; the one-block trace is always zero. This algebraic observation is not a Lean proof and shows why the method cannot decide whether the entire observed universe is one individual.

Twenty seeded weight perturbations report coassignment robustness only. They are not time-block bootstrap, posterior uncertainty or missingness calibration. Missing-step refusal is implemented at the CLI; broad missing-data performance is not measured. Bipartite roles, weak transient contacts, observation noise, variable windows, alternative seeds and predictive holdout performance still need systematic comparison. The external-exchange fixture fails to recover the prespecified internal/environment distinction; retain this failure in reports.

Before a causal maintenance claim, fix the intervention semantics, magnitude-matched control and outcome in advance. The current internal-coupling and external-input interventions have different magnitudes and cannot rank causal importance. Before empirical use, supply observation licensing/consent, measurement provenance, independent ground truth where meaningful and a study-specific uncertainty model.

## Persistence and interoperability

The proposed Kotoba adapter's authoritative object is a verified IPLD/DAG-CBOR block and its CID; RDF and Datom indexes are declared projections. The current Python implementation has canonical JSON/SHA-256 identifiers only. It neither implements an IPLD codec nor invokes a Kotoba runtime. Datom interfaces can remain at the database/projection layer without defining all code and actor state as Datoms.

BFO/CCO/PROV mappings are candidate alignments in `docs/ALIGNMENT.md`; do not introduce `owl:sameAs` for lineage or observational equivalence. Definitions, formal proof, runnable finite-model checks, real-world validity and production qualification are separate acceptance gates.

## Primary sources

- Delvenne, Yaliraki, Barahona: [Stability of graph communities across time scales](https://arxiv.org/abs/0812.1811).
- Peixoto: [Nonparametric Bayesian inference of the microcanonical stochastic block model](https://doi.org/10.1103/PhysRevE.95.012317).
- Froyland: [Finite-time coherent sets](https://arxiv.org/abs/1210.7418).
- Friston et al.: [Stochastic Chaos and Markov Blankets](https://doi.org/10.3390/e23091220).
- Hoel, Albantakis, Tononi: [Quantifying causal emergence](https://doi.org/10.1073/pnas.1314922110).
- Edelsbrunner, Mücke: [Three-Dimensional Alpha Shapes](https://graphics.stanford.edu/courses/cs268-11-spring/handouts/AlphaShapes/edelsbrunner94.pdf).

Combining these approaches into RIPO is this research proposal; the cited papers do not validate RIPO.

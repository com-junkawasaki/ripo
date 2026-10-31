# RIPO executable individuation profile 0.2

This is an experimental operational profile, not a complete upper ontology,
an Inc implementation, or an assertion of BFO/CCO equivalence.

## 1. Observation, hypothesis, and reality

At each observation step t the input is G_t=(V_t,A_t), with 1–8 observation
identifiers and a symmetric, finite, nonnegative weighted adjacency matrix.
Diagonal entries are zero. Each snapshot is supplied explicitly; this version
does not estimate time windows from an event stream. Edges denote the selected
relation type, not necessarily causation. Directed/signed/higher-arity relations
are rejected rather than silently projected.

An individuation hypothesis is (input hash, t, model version, tau, partition H).
It is a partition of observations under a model; it is not a proof that each
block is an independently existing object. Current memberships are hard 0/1,
non-overlapping. Overlapping, nested, typed hypergraph models remain future work.

## 2. Executed objective

For positive-degree observations, let d_i=sum_j A_ij, D=diag(d), pi_i=d_i/sum d.

    P(tau) = exp[tau (D^-1 A - I)]
    B(tau) = diag(pi) P(tau) - pi pi^T
    r(H,tau) = sum_(i,j in the same block of H) B_ij(tau)
    H* = argmax_H r(H,tau)

We optimize the fixed-time continuous-time Markov Stability trace objective.
The chain is reversible for the accepted graph class. For disconnected graphs,
degree-normalized pi is a selected stationary distribution, not the unique one.
Isolated observations are excluded from the objective and returned separately
as singleton observations with no evidence for relational individuation.
An all-zero input returns status=no_relational_evidence and score=null.

Every set partition is enumerated using restricted growth strings. For n=8,
there are Bell(8)=4,140 partitions. The result is globally optimal for this
finite objective, subject to floating-point tolerance 1e-10. This guarantee
does not extend to ontological truth, choice of variables, relation weights,
resolution, or large graphs. Equal optima are counted; the first canonical
enumeration is used for display only. Gap is the difference to the best score
outside tolerance, not statistical confidence.

tau is dimensionless diffusion time / resolution. t is an observation index,
not seconds. No identity smoothing is applied across snapshots. A standard
weighted modularity objective, A/sum(A)-d d^T/sum(A)^2, is optimized over the
same partitions as a baseline. SBM is not implemented in this version.

## 3. Correspondence and inheritance

For adjacent hypotheses C at t and D at t+1, we emit a correspondence only if
their observed identifiers overlap OR an explicit input handoff connects an
identifier in C to one in D. The complete supporting overlap/handoff is kept.
One-to-many is labelled split; many-to-one merge. No numerical identity or
owl:sameAs follows. A new matching structure without evidence remains unlinked.
Input handoffs are assumptions of this synthetic experiment, not independently
verified historical facts. Persistent member identifiers are also input evidence.
This profile does not infer ancestry from visual or structural similarity.
Split and merge labels characterize correspondence topology, not a biological
or organizational event proven by the algorithm.

## 4. Rendering contours

Two display layouts z_v are offered: paired grid and circle. Neither is a
physical location nor an input to partition inference. For each candidate C:

    f_C(x) = sum_(v in C) exp(-||x-z_v||^2 / (2 sigma^2))
    g_C(x) = f_C(x) / max_on_grid f_C(x)
    displayed boundary = {x : g_C(x)=0.35}

sigma=0.10 in normalized display units; contours are sampled on a 100x100 grid
over [-0.4,1.4]^2 and extracted with Matplotlib's contour generator. All closed
components are retained. Threshold and sigma are rendering choices, not existence
thresholds. g_C is neither membership probability nor uncertainty. Changing
layout changes contours while leaving partitions and lineage exactly unchanged.
This is a Gaussian-sum level-set renderer, not a 3D Gaussian-splat reconstruction
and not alpha-shape implementation.

## 5. Sensitivity and known causal model

Twenty deterministic-seed lognormal edge-weight perturbations (sigma=0.15)
measure coassignment robustness of the stable two-block example at tau=1.
Symmetric perturbations are applied to existing edges. No iid resampling,
posterior, calibrated uncertainty, missingness robustness, or existence
probability is claimed. Five resolutions and six snapshots are evaluated for
six synthetic scenarios; this is not an empirical benchmark.

An additional known structural model is simulated:

    x1(t+1)=0.45*x1(t)+0.45*x2(t)+0.1*u(t)
    x2(t+1)=0.45*x2(t)+0.45*x1(t)+0.1*u(t)
    u(t)=1; x1(0)=x2(0)=0

Baseline recovers toward (1,1). Removing both internal cross-couplings changes
equilibrium to (2/11,2/11). Removing both external input terms changes it to
(0,0). The two interventions have unequal magnitudes; do not rank them as a
normalized measure of causal importance. This illustrates input-supported
recovery, not autopoiesis, life, consciousness, or causal autonomy. The SCM is
specified, not learned from correlations, and is separate from graph inference.

## 6. Machine-readable records

results/experiment.json includes inputs, parameters, partitions, objective values,
tie counts, correspondence evidence, perturbations, interventions and elapsed
time. Input SHA-256 hashes canonical synthetic snapshot data, excluding results.
It is an integrity identifier, not a CID, signature, or truth guarantee.
results/hypotheses.jsonld maps ExtractionRun, IndividuationHypothesis,
MembershipAssessment, BoundaryRepresentation and LineageAssertion into an
experimental example.org namespace with PROV provenance. It is valid JSON;
RDF expansion/OWL consistency/SHACL conformance are not validated in this runtime.
The records are not aligned by equivalence with Inc or BFO.

## 7. Findings that must not be hidden

Analytic counterexample (algebraic derivation, not a Lean proof): for an
unweighted complete graph K_n and finite tau,

    r(H,tau) = exp(-n*tau/(n-1)) * [1 - sum_C (|C|/n)^2].

The maximizing partition is therefore all singletons. More generally, the
one-block partition always has score zero under this centered objective. Thus
one cannot use this objective alone to determine whether the whole observed
universe is one individual. The reference population/environment is a substantive
model choice. This is not an implementation failure to be hidden by drawing a
single enclosing contour.

- Stable weakly connected blocks are recoverable at the selected scales.
- Entire membership replacement is trackable only because handoff evidence is
  supplied. Same shape alone cannot establish lineage or numerical identity.
- In a homogeneous complete graph, fixed-time Markov Stability returns
  singletons for the tested finite scales. Modularity instead returns one block.
  A method's optimum is not a universal definition of an individual.
- Strong exchange with an environment can erase the low-escape grouping of an
  a priori internal set. This is a limitation, not evidence that open systems
  do not exist.
- In the common-driver generator Z causes all eight observations; there are no
  internal causal edges. The correlation graph and the known causal mechanism
  are different inputs. Graph inference cannot decide causation from correlation.

## 8. Reproduction and scope

    python -m pip install -r requirements.txt
    OPENBLAS_NUM_THREADS=1 python -m unittest -v test_engine.py
    OPENBLAS_NUM_THREADS=1 python engine.py
    python build.py

No network is used by the engine, tests, rendering, or exported viewer.
This prototype is standalone research work. It neither edits nor publishes
junkawasaki.com and does not finish JUN-653's article/PR task.

Source for Markov Stability: Delvenne, Yaliraki & Barahona (2010),
https://doi.org/10.1073/pnas.0903215107.
The integration with RIPO and the evidence policy above are design proposals.


## 9. Standalone consolidation (v0.3 interface)

`ripo.py` validates explicit `ripo.snapshots.v1` input before invoking this
numeric model. It rejects duplicate IDs, undeclared fields, directed/signed/
higher-arity data, asymmetric matrices, nonfinite weights and invalid handoffs.
A missing observation step yields `observation_gap_unresolved`; continuity is
not silently filled in. Physical observation windows are not reconstructed.
This interface uses canonical JSON and SHA-256 with the exact algorithm version
and Markov time bound into its run identifier. It is not a CID codec or a
Kotoba/Kotobase integration. An ID collision between separate recordings must
be prevented by the supplying observation system; names alone are not evidence
of continuity of real subjects.

The consolidated repository parses `vocabulary.jsonld` and the generated
hypothesis graph as RDF and checks `ontology/individuation-shapes.ttl` with
positive and negative controls. This supersedes only the earlier statement
that RDF parsing/SHACL was untested. No equivalence axiom maps the experimental
0.2 vocabulary to the article's illustrative 0.1 vocabulary or to Inc/BFO.
A signed block adapter, calibrated uncertainty, real-data comparison, SBM,
finite-time coherent sets and Markov blankets remain future work.

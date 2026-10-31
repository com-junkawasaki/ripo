# Merge review — JUN-654, 2026-10-31

Reviewed source: initial PR head `49d5aa56673e29b9ac8c9c840521fd360f73a3a5`, followed by the scoped corrections in this commit.

Two correctness findings were reproduced and fixed before merge:

- `fixture --scenario common_driver` generated correlation matrices whose last-bit asymmetry made the strict extractor reject its own fixture. The CLI fixture adapter now explicitly mirrors the generated upper triangle. External matrices are not symmetrized, and even a 1e-15 discrepancy remains rejected.
- Finite weights of 1e308 or Markov time 1e308 reached nonfinite arithmetic and failed with IndexError; an oversized JSON integer raised OverflowError. Range guards now report ValueError / CLI exit 2 without a traceback or output file. The estimator and the recovered synthetic generator were not changed to fit expected results.

The fixed-time trace, partition enumeration, isolate policy, tolerance ties, evidence-backed correspondence and display-only contours were inspected against their definitions. No additional merge-blocking defect was found within this bounded research scope. Numerical conditioning for arbitrary magnitudes, empirical validity, formal alignment and broad research acceptance remain unqualified.

Validation: 26 Python tests; full local `scripts/reproduce.py` pipeline; six fixtures extractable; RDF/SHACL positive and three negative controls (710 records / 3380 triples); transition query delta 1.0; 720 DOM states. Existing scientific results and figure bytes are checked against the initial reviewed commit. No hosted CI workflow is present. The DOM check is not pixel QA; prior browser/plot inspection remains recorded in the PR.

The owner authorized review and main merge of ripo #1 and webmaster #27, followed by removal of only their clean verified-merged task worktrees. Website deployment is a separate delivery surface; its existing main-push workflow is tracked on JUN-653.

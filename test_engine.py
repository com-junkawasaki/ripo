import unittest
import numpy as np
from engine import partitions, kernel, optimize, lineage, groups, two_blocks, scenarios, intervention_experiment

class EngineTests(unittest.TestCase):
    def test_partition_enumeration(self):
        self.assertEqual([len(partitions(n)) for n in range(1,9)],
                         [1,2,5,15,52,203,877,4140])
        self.assertEqual(len(np.unique(partitions(8),axis=0)),4140)

    def test_probability_kernel(self):
        b,p,pi=kernel(two_blocks(),1)
        np.testing.assert_allclose(p.sum(axis=1),1,atol=1e-12)
        np.testing.assert_allclose(pi@p,pi,atol=1e-12)
        np.testing.assert_allclose(b,b.T,atol=1e-12)
        self.assertGreaterEqual(p.min(),-1e-12)

    def test_zero_time(self):
        r=optimize(two_blocks(),0)
        self.assertEqual(len(set(r['labels'])),8)
        self.assertAlmostEqual(r['score'],1-8*(1/8)**2)

    def test_two_blocks(self):
        labels=optimize(two_blocks(),1)['labels']
        self.assertEqual(labels,[0,0,0,0,1,1,1,1])

    def test_global_optimum_independent_loop(self):
        a=two_blocks()[:5,:5]
        b,_,_=kernel(a,.7)
        expected=max(sum(b[i,j] for i in range(5) for j in range(5) if p[i]==p[j])
                     for p in partitions(5))
        self.assertAlmostEqual(optimize(a,.7)['score'],expected,places=12)

    def test_permutation_equivariance(self):
        a=two_blocks();perm=np.array([6,1,4,0,7,3,2,5])
        original=np.asarray(optimize(a,1)['labels'])
        changed=np.asarray(optimize(a[np.ix_(perm,perm)],1)['labels'])
        np.testing.assert_array_equal(original[perm,None]==original[None,perm],
                                     changed[:,None]==changed[None,:])

    def test_weight_scale_invariance(self):
        a=two_blocks()
        self.assertEqual(optimize(a)['labels'],optimize(a*17)['labels'])
        self.assertAlmostEqual(optimize(a)['score'],optimize(a*17)['score'])

    def test_no_evidence_abstention(self):
        r=optimize(np.zeros((8,8)))
        self.assertIsNone(r['score']);self.assertEqual(r['status'],'no_relational_evidence')

    def test_isolated_observation(self):
        a=two_blocks();a[7,:]=0;a[:,7]=0
        r=optimize(a)
        self.assertEqual(r['isolated'],[7])
        self.assertEqual(r['labels'].count(r['labels'][7]),1)

    def test_replacement_needs_evidence(self):
        old=[['a','b']];new=[['x','y']]
        self.assertEqual(lineage(old,new)['links'],[])
        evidence=lineage(old,new,[['a','x'],['b','y']])
        self.assertEqual(evidence['links'][0]['kind'],'handoff')
        self.assertEqual(evidence['links'][0]['overlap'],[])

    def test_copy_is_not_identity(self):
        r=lineage([['a','b']],[['a','b'],['copy-a','copy-b']])
        self.assertEqual(r['unlinked_after'],[1])

    def test_split_and_merge(self):
        r=lineage([['a','b','c','d']],[['a','b'],['c','d']])
        self.assertEqual([e['kind'] for e in r['links']],['split','split'])
        r=lineage([['a','b'],['c','d']],[['a','b','c','d']])
        self.assertEqual([e['kind'] for e in r['links']],['merge','merge'])

    def test_invalid_inputs(self):
        for a in [np.array([[0,-1],[-1,0]]),np.array([[0,1],[0,0]]),
                  np.array([[0,np.nan],[np.nan,0]]),np.ones((9,9))]:
            with self.assertRaises(ValueError):optimize(a)
        with self.assertRaises(ValueError):optimize(two_blocks(),-1)
        with self.assertRaises(ValueError):lineage([['a']],[['b']],[['z','b']])

    def test_computed_split_merge(self):
        s=next(s for s in scenarios() if s['key']=='split_merge')
        counts=[len(set(optimize(f['adjacency'],1)['labels'])) for f in s['frames']]
        self.assertEqual(counts,[2,2,4,4,2,2])

    def test_homogeneous_graph_is_not_automatically_one(self):
        a=np.ones((8,8))-np.eye(8)
        self.assertEqual(len(set(optimize(a,1)['labels'])),8)
        self.assertEqual(len(set(optimize(a,method='modularity')['labels'])),1)

    def test_interventions_match_analytic_equilibria(self):
        for r in intervention_experiment()['results']:
            self.assertAlmostEqual(r['final_mean'],r['analytic_equilibrium'],places=4)

if __name__=='__main__':unittest.main(verbosity=2)


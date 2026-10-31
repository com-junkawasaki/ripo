from copy import deepcopy
import json
import unittest
from ripo import extract, fixture, validate_dataset


class SnapshotProfileTests(unittest.TestCase):
    def test_stable_fixture_and_deterministic_identity(self):
        a = extract(fixture())
        self.assertEqual(a, extract(json.loads(json.dumps(fixture()))))
        self.assertEqual([len(f['groups']) for f in a['frames']], [2]*6)
        self.assertNotEqual(a['run_sha256'], extract(fixture(), 3)['run_sha256'])

    def test_replacement_with_and_without_handoff(self):
        data = fixture('replacement')
        found = extract(data)['correspondences'][2]['links']
        self.assertTrue(any(e['kind']=='handoff' and not e['overlap'] for e in found))
        data['frames'][3]['handoffs'] = []
        self.assertTrue(extract(data)['correspondences'][2]['unlinked_after'])

    def test_copy_has_no_automatic_lineage(self):
        self.assertTrue(extract(fixture('copy'))['correspondences'][2]['unlinked_after'])

    def test_missing_step_remains_unresolved(self):
        data=fixture(); del data['frames'][2]
        link=extract(data)['correspondences'][1]
        self.assertEqual(link['links'], [])
        self.assertEqual(link['status'], 'observation_gap_unresolved')

    def test_reject_lossy_or_mixed_inputs(self):
        for key,value in [('directed',True),('signed',True),('arity',3),('relation_kind','authority')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                data=fixture();data[key]=value;extract(data)

    def test_invalid_observation_and_weights(self):
        for problem in ('ids','nan','asymmetry','boolean','step','handoff','unknown'):
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                d=fixture(); f=d['frames'][0]
                if problem=='ids':f['ids'][1]=f['ids'][0]
                if problem=='nan':f['adjacency'][0][1]=float('nan')
                if problem=='asymmetry':f['adjacency'][0][1]+=.1
                if problem=='boolean':f['adjacency'][0][1]=True
                if problem=='step':d['frames'][1]['step']=0
                if problem=='handoff':f['handoffs']=[['unknown','a0']]
                if problem=='unknown':d['undeclared_projection']='clique'
                extract(d)

    def test_isolated_data_abstains(self):
        d=fixture();d['frames']=d['frames'][:1]
        d['frames'][0]['adjacency']=[[0]*8 for _ in range(8)]
        r=extract(d)['frames'][0]['assessment']
        self.assertIsNone(r['score']);self.assertEqual(r['status'],'no_relational_evidence')

    def test_tau_refusals(self):
        for tau in (True,-1,float('inf'),float('nan')):
            with self.assertRaises(ValueError):extract(fixture(),tau)

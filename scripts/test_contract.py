import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from check_contract import inspect_plan

class ContractTests(unittest.TestCase):
    def plan(self):
        return json.loads((Path(__file__).resolve().parents[1]/'examples/contract.json').read_text(encoding='utf-8'))
    def test_valid_example_is_not_modified(self):
        d=self.plan();before=copy.deepcopy(d)
        self.assertTrue(inspect_plan(d)['contract_valid'])
        self.assertEqual(d,before)
    def test_foreign_role_and_malformed_input_are_rejected(self):
        d=self.plan();d['skill']='foreign-skill'
        self.assertFalse(inspect_plan(d)['contract_valid'])
        for bad in [None,[],{},'text',{'skill':self.plan()['skill']}]:
            self.assertFalse(inspect_plan(bad)['contract_valid'])

    def test_short_footage_does_not_cover_long_narration(self):
        d=self.plan();d['output_duration']=180;d['narration'][0]['end']=180
        self.assertFalse(inspect_plan(d)['contract_valid'])
    def test_generated_footage_cannot_prove_mechanics_but_can_be_labeled_intro(self):
        d=self.plan();d['shots'][0]['kind']='generated_atmosphere'
        self.assertFalse(inspect_plan(d)['contract_valid'])
        d['narration'][0]['claim_kind']='intro'
        self.assertTrue(inspect_plan(d)['contract_valid'])
        d=self.plan();d['shots'][0]['game_version']='different-patch'
        self.assertFalse(inspect_plan(d)['contract_valid'])


    def test_labeled_source_checked_diagram_is_illustration_not_fake_gameplay(self):
        d=self.plan();d['shots'][0].update(kind='diagram',verified_against_source=True,illustration_label='示意图，非实机')
        self.assertTrue(inspect_plan(d)['contract_valid'])
        d['shots'][0]['illustration_label']=''
        self.assertFalse(inspect_plan(d)['contract_valid'])

if __name__=='__main__': unittest.main()

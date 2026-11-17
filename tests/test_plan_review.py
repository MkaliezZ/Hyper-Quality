"""Synthetic behavior specifications, not real plan quality or human labels."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from harness import evaluate, read_json, export_report, Invalid, gates_for, calibrate
from plan_review import policy_for
from templates import new_dossier, three
from test_harness import synthetic_fixture


def plan_fixture(root,p):
    old=synthetic_fixture(root,p)
    d=new_dossier(p,'synthetic-plan','合成开发方案（非真实业务）','agent','2026-11-12',review_object='development_plan')
    d.update(purpose='synthetic')
    d['product']['version']='fixture-1'
    d['plan'].update(version='plan-fixture-1',baseline_product_version='baseline-0',scope_in=['核实单一检索任务'],scope_out=['不开发支付和多校平台'],
        assumptions=[dict(id='A1',kind='demand',statement='合成需求待核',critical=True,status='unknown',validation='交叉任务比较并保存失败分母',evidence_refs=[])],
        dependencies=[dict(id='D1',description='合成资料接口',critical=True,status='unverified',owner='合成执行人',fallback='拿不到则停止，保留本地样本结果',evidence_refs=[])],
        stop_conditions=['一次严重错误或超出确认额度即停止该轮并保留证据'])
    m=d['plan']['milestones'][0]
    m.update(owner='合成执行人',due='2026-11-20',deliverable='冻结任务对照与资源日志',
             stop_conditions=['正确结果低于预注册线即停止扩展'],validates_assumptions=['A1'],resolves_dependencies=['D1'],bom_line_ids=['inference','human_delivery'])
    m['acceptance']={'method':'用冻结正确答案比对并计算完成率','pass':'合成探索线6/8独立完成且不低于基线','fail':'低于6/8或发生严重错误','evidence_required':'原始输入、结果、计量日志及失败分母'}
    pp=policy_for(p,'development_plan')
    targets=[m['id'] for m in pp['metrics']]+[g['id'] for g in pp['gates']]+['C1','BOM','BUDGET','assumption:A1','dependency:D1']+['phase:'+x for x in d['plan']['phase_coverage']]+['review:'+x for x in d['reviews']]
    d['evidence']=old['evidence']
    for e in d['evidence']:e.update(review_object='development_plan',plan_version='plan-fixture-1',supports=targets)
    refs=[e['id'] for e in d['evidence']]
    for a in d['plan']['assumptions']:a['evidence_refs']=refs
    for x in d['plan']['dependencies']:x['evidence_refs']=refs
    for r in d['ratings'].values():r.update(score=4,reason='合成规则测试的预设证据，非现实评价',evidence_refs=refs)
    d['gates']={g['id']:dict(status='met',reason='合成适用条件',evidence_refs=refs) for g in pp['gates']}
    d['reviews']=old['reviews']
    d['claims']=[dict(id='C1',text='预期改善检索任务，待验证',claim_scope='planned',status='candidate',proof_kind='outcome',boundary='合成案例；不对外承诺',evidence_refs=[],counterevidence_refs=[])]
    d['bom']=old['bom']
    for line in d['bom']['lines']:
        line['phase']='operation' if line['id']=='infrastructure' else 'validation'
        if line['phase']=='validation':line['basis']='one_off'
    for phase,c in d['plan']['phase_coverage'].items():
        c.update(status='included' if phase in ('validation','operation') else 'not_applicable',reason='合成场景该阶段已计或无额外投入',evidence_refs=refs)
    return d


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.p=read_json(ROOT/'policy.json');self.d=plan_fixture(self.root,self.p)
    def tearDown(self):self.temp.cleanup()
    def run_case(self):return evaluate(self.d,self.p,self.root)
    def test_plan_has_independent_score_and_no_product_pass(self):
        r=self.run_case()
        self.assertEqual(r['scorecards'],{'product':None,'development_plan':100})
        self.assertEqual(r['verdict'],'PLAN_ELIGIBLE_FOR_OWNER_REVIEW')
        self.assertEqual(r['resource_status'],'BLOCKED')
        self.assertTrue(all(x is None for x in self.d['budget']['caps'].values()))
    def test_empty_plan_remains_unknown(self):
        self.d=new_dossier(self.p,'empty','empty','course','2026-11-12',review_object='development_plan')
        r=self.run_case();self.assertEqual((r['score'],r['coverage'],r['verdict']),(0,0,'NEEDS_EVIDENCE'))
    def test_next_action_comes_from_selected_milestone(self):
        self.d['next_experiment']['deliverable']='擅自扩大到整个产品上线'
        r=self.run_case()
        self.assertEqual(r['next_experiment']['deliverable'],self.d['plan']['milestones'][0]['deliverable'])
        self.assertEqual(r['next_experiment']['scope'],'milestone:M1')
    def test_product_and_plan_metrics_cannot_mix(self):
        self.d['ratings']['J1']=self.d['ratings'].pop('PJ1')
        with self.assertRaises(Invalid):self.run_case()
    def test_plan_cannot_request_launch(self):
        self.d['stage']='launch'
        with self.assertRaises(Invalid):self.run_case()
    def test_unknown_critical_assumption_requires_next_validation(self):
        self.d['plan']['milestones'][0]['validates_assumptions']=[]
        self.assertEqual(self.run_case()['verdict'],'NEEDS_EVIDENCE')
    def test_refuted_assumption_blocks_even_perfect_score(self):
        self.d['plan']['assumptions'][0]['status']='refuted'
        r=self.run_case();self.assertEqual((r['score'],r['verdict']),(100,'DOES_NOT_MEET'))
    def test_development_cannot_treat_hypothesis_as_fact(self):
        self.d['stage']='development'
        self.assertEqual(self.run_case()['verdict'],'NEEDS_EVIDENCE')
    def test_technical_evidence_cannot_support_demand(self):
        self.d['stage']='development';a=self.d['plan']['assumptions'][0]
        a.update(status='supported',evidence_refs=['test_run-a','test_run-b'])
        r=self.run_case();self.assertEqual(r['plan']['assumptions'][0]['status'],'unknown')
    def test_available_dependency_requires_proof(self):
        self.d['plan']['dependencies'][0].update(status='available',evidence_refs=[])
        self.d['plan']['milestones'][0]['resolves_dependencies']=[]
        self.assertEqual(self.run_case()['verdict'],'NEEDS_EVIDENCE')
    def test_unavailable_dependency_blocks(self):
        self.d['plan']['dependencies'][0]['status']='unavailable'
        self.assertEqual(self.run_case()['verdict'],'DOES_NOT_MEET')
    def test_missing_owner_date_and_acceptance_block(self):
        for key in ('owner','due','deliverable'):
            with self.subTest(key=key):
                original=self.d['plan']['milestones'][0][key]
                self.d['plan']['milestones'][0][key]=None if key!='deliverable' else ''
                self.assertEqual(self.run_case()['verdict'],'NEEDS_EVIDENCE')
                self.d['plan']['milestones'][0][key]=original
        self.d['plan']['milestones'][0]['acceptance']['fail']=''
        self.assertEqual(self.run_case()['verdict'],'NEEDS_EVIDENCE')
    def test_expired_requested_deadline_blocks(self):
        self.d['plan']['milestones'][0]['due']='2026-11-01'
        self.assertEqual(self.run_case()['verdict'],'DOES_NOT_MEET')
    def test_missing_stop_blocks(self):
        self.d['plan']['stop_conditions']=[]
        self.assertEqual(self.run_case()['verdict'],'NEEDS_EVIDENCE')
    def test_cycle_or_dangling_milestones_rejected(self):
        self.d['plan']['milestones'][0]['depends_on']=['M1']
        with self.assertRaises(Invalid):self.run_case()
        self.d['plan']['milestones'][0]['depends_on']=['missing']
        with self.assertRaises(Invalid):self.run_case()
    def test_cannot_fund_dependent_future_milestone(self):
        m=copy.deepcopy(self.d['plan']['milestones'][0]);m.update(id='M2',depends_on=['M1'],bom_line_ids=[])
        self.d['plan']['milestones'].append(m);self.d['plan']['requested_milestone']='M2';self.d['budget']['scope']='milestone:M2'
        self.assertEqual(self.run_case()['verdict'],'NEEDS_EVIDENCE')
    def test_planned_claim_is_not_supported_product(self):
        self.d['claims'][0].update(status='supported',proof_kind='capability',evidence_refs=['source-a','source-b'])
        r=self.run_case();self.assertEqual(r['claims'][0]['status'],'candidate')
        self.assertEqual(r['verdict'],'NEEDS_EVIDENCE')
    def test_existing_claim_cannot_use_plan_document(self):
        self.d['claims'][0].update(claim_scope='existing',status='supported',proof_kind='capability',evidence_refs=['source-a'])
        self.assertEqual(self.run_case()['claims'][0]['status'],'candidate')
    def test_plan_evidence_cannot_be_laundered_as_product(self):
        product=synthetic_fixture(self.root,self.p)
        for e in product['evidence']:e.update(review_object='development_plan',plan_version='p1')
        r=evaluate(product,self.p,self.root)
        self.assertEqual(r['coverage'],0)
    def test_shared_test_evidence_rejected(self):
        for e in self.d['evidence']:e['review_object']='shared'
        r=self.run_case();self.assertFalse(r['evidence_checks']['test_run-a']['usable'])
    def test_shared_version_cannot_launder_old_product_test(self):
        for schema in ('1.0','1.1'):
            with self.subTest(schema=schema):
                product=synthetic_fixture(self.root,self.p)
                if schema=='1.1':product.update(schema_version='1.1',review_object='product')
                for e in product['evidence']:e.update(review_object='product',product_version='shared')
                r=evaluate(product,self.p,self.root)
                self.assertFalse(r['evidence_checks']['test_run-a']['usable'])
    def test_source_can_define_need_but_not_prove_demand(self):
        self.d['ratings']['PJ1'].update(score=4,evidence_refs=['source-a','source-b'])
        r=self.run_case();self.assertEqual(r['metrics']['PJ1']['score'],1)
        self.d['stage']='development';self.d['gates']['PG_DEMAND']['evidence_refs']=['source-a','source-b']
        r=self.run_case();self.assertEqual(next(g['status'] for g in r['gates'] if g['id']=='PG_DEMAND'),'unknown')
    def test_low_cap_source_cannot_supply_second_top_score_group(self):
        self.d['ratings']['PJ1']['evidence_refs']=['customer-a','source-b']
        r=self.run_case();self.assertEqual(r['metrics']['PJ1']['score'],3)
    def test_phase_totals_reconcile_without_unknown_as_zero(self):
        r=self.run_case()
        for dim in self.p['resource_dimensions']:
            for scenario in ('low','base','high'):
                self.assertAlmostEqual(sum(x['totals'][scenario][dim] for x in r['plan']['phases'].values()),r['costs']['totals'][scenario][dim])
        self.d['plan']['phase_coverage']['exit']['status']='unknown'
        r=self.run_case();self.assertIsNone(r['plan']['phases']['exit']['totals']['base']['cash'])
    def test_wrong_plan_version_rejected_as_evidence(self):
        self.d['plan']['version']='new-plan'
        self.assertEqual(self.run_case()['coverage'],0)
    def test_phase_cost_omission_and_conflict_block(self):
        self.d['plan']['phase_coverage']['operation']['status']='unknown'
        self.assertEqual(self.run_case()['verdict'],'NEEDS_EVIDENCE')
        self.d['plan']['phase_coverage']['operation']['status']='not_applicable'
        self.assertEqual(self.run_case()['verdict'],'DOES_NOT_MEET')
    def test_next_milestone_costs_exclude_future_operation(self):
        r=self.run_case()
        self.assertEqual(r['plan']['requested_costs']['totals']['high']['cash'],3)
        self.assertEqual(r['costs']['totals']['high']['cash'],63)
        self.d['budget'].update(status='confirmed',caps=dict.fromkeys(self.p['resource_dimensions'],1000000),evidence_refs=['human_review-a'])
        self.d['budget']['caps']['cash']=3
        r=self.run_case();self.assertFalse(any('超过额度' in s for s in r['resource_reasons']))
        self.assertEqual(r['resource_status'],'BLOCKED') # synthetic, never a real authorization
    def test_missing_current_bom_not_free(self):
        self.d['plan']['milestones'][0]['bom_line_ids']=[]
        r=self.run_case();self.assertIsNone(r['plan']['requested_costs']['totals']['high']['cash'])
        self.assertEqual(r['verdict'],'NEEDS_EVIDENCE')
    def test_unscoped_budget_rejected(self):
        self.d['budget']['scope']='entire-roadmap'
        with self.assertRaises(Invalid):self.run_case()
    def test_paused_plan_cannot_restart(self):
        self.d['product']['lifecycle']='paused'
        self.assertEqual(self.run_case()['verdict'],'STOP_EXISTING_DECISION')
    def test_plan_frozen_replay_includes_implementation(self):
        out=self.root/'report';r=export_report(self.d,self.p,out,self.root)
        self.assertTrue((out/'implementation/plan_review.py').is_file())
        replay=evaluate(read_json(out/'replay-dossier.json'),read_json(out/'policy.json'),out)
        for key in ('scorecards','plan','verdict','resource_status'):self.assertEqual(r[key],replay[key])
        spec=importlib.util.spec_from_file_location('plan_protocol_validator',ROOT/'vendor/hyper-protocol/tools/validate_bundle.py')
        validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
        self.assertEqual(validator.validate_bundle(read_json(out/'task-bundle.json')),[])
    def test_plan_product_calibration_cannot_mix(self):
        row=dict(case_id='a',trial_id='1',model='m',prompt_version='p',policy_version=self.p['version'],human_label_ref='synthetic',human_gate='pass',ai_gate='pass',human_score=3,ai_score=3)
        with self.assertRaises(Invalid):calibrate([row,{**row,'case_id':'b','score_kind':'development_plan'}],self.p)


if __name__=='__main__':unittest.main()

"""Frozen plan behavior cases plus product-score compatibility. No business gold labels."""
import argparse
import copy
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from harness import Invalid, VERSION, evaluate, export_report, read_json, write_json, digest, calibrate
from templates import new_dossier
from test_plan_review import plan_fixture, document_only


def run(out):
    out=Path(out)
    if out.exists():raise ValueError('输出已存在；历史eval不可覆盖')
    out.mkdir(parents=True)
    inputs=out/'inputs';inputs.mkdir()
    p=read_json(ROOT/'policy.json')
    base=plan_fixture(inputs,p)
    spec=importlib.util.spec_from_file_location('protocol_validator',ROOT/'vendor/hyper-protocol/tools/validate_bundle.py')
    validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
    cases=[]
    def add(name, mutate, expected):
        d=copy.deepcopy(base);mutate(d)
        write_json(inputs/(name+'.json'),d)
        try:
            result=export_report(d,p,out/'results'/name,inputs)
            actual=result['verdict'];errors=validator.validate_bundle(read_json(out/'results'/name/'task-bundle.json'))
            portable=evaluate(read_json(out/'results'/name/'replay-dossier.json'),p,out/'results'/name)
            replay_equal=all(portable[k]==result[k] for k in ('scorecards','plan','gates','costs','verdict','resource_status'))
            row=dict(id=name,expected=expected,actual=actual,matched=expected==actual,
                scorecards=result['scorecards'],resource_status=result['resource_status'],
                score_basis=result['score_basis'],evidence_bonus=result['plan'].get('evidence_bonus'),
                protocol_errors=errors,replay_equal=replay_equal,
                budget_caps=d['budget']['caps'])
            assert result['scorecards']['product'] is None
            assert result['resource_status']=='BLOCKED'
        except (Invalid, ValueError) as e:
            row=dict(id=name,expected=expected,actual='INVALID',matched=expected=='INVALID',reason=str(e),protocol_errors=[],replay_equal=None)
        cases.append(row)
    add('complete-validation-budget-unset',lambda d:None,'PLAN_ELIGIBLE_FOR_OWNER_REVIEW')
    add('missing-owner',lambda d:d['plan']['milestones'][0].update(owner=None),'PLAN_ELIGIBLE_FOR_OWNER_REVIEW')
    add('missing-pass-line',lambda d:d['plan']['milestones'][0]['acceptance'].update({'pass':''}),'NEEDS_EVIDENCE')
    add('missing-global-stop',lambda d:d['plan'].update(stop_conditions=[]),'NEEDS_EVIDENCE')
    add('missing-milestone-stop',lambda d:d['plan']['milestones'][0].update(stop_conditions=[]),'NEEDS_EVIDENCE')
    add('critical-unknown-not-assigned',lambda d:d['plan']['milestones'][0].update(validates_assumptions=[]),'NEEDS_EVIDENCE')
    add('refuted-demand-perfect-score',lambda d:d['plan']['assumptions'][0].update(status='refuted'),'DOES_NOT_MEET')
    add('unavailable-dependency',lambda d:d['plan']['dependencies'][0].update(status='unavailable'),'DOES_NOT_MEET')
    add('development-with-unverified-critical-items',lambda d:d.update(stage='development'),'PLAN_ELIGIBLE_FOR_OWNER_REVIEW')
    def ready(d):
        d['stage']='development';d['plan']['assumptions'][0]['status']='supported';d['plan']['dependencies'][0]['status']='available'
    add('complete-development-single-milestone',ready,'PLAN_ELIGIBLE_FOR_OWNER_REVIEW')
    add('claimed-future-feature-as-existing',lambda d:d['claims'][0].update(status='supported',claim_scope='existing',proof_kind='capability',evidence_refs=['source-a']),'NEEDS_EVIDENCE')
    add('planned-feature-overclaim',lambda d:d['claims'][0].update(status='supported',proof_kind='capability',evidence_refs=['source-a']),'NEEDS_EVIDENCE')
    add('missing-operation-bom',lambda d:d['plan']['phase_coverage']['operation'].update(status='unknown'),'NEEDS_EVIDENCE')
    add('unknown-cash',lambda d:d['bom']['lines'][0]['per_quantity']['cash'].update(high=None),'PLAN_ELIGIBLE_FOR_OWNER_REVIEW')
    add('operation-cost-hidden-as-na',lambda d:d['plan']['phase_coverage']['operation'].update(status='not_applicable'),'DOES_NOT_MEET')
    add('no-current-milestone-costs',lambda d:d['plan']['milestones'][0].update(bom_line_ids=[]),'NEEDS_EVIDENCE')
    add('obsolete-plan-evidence',lambda d:d['plan'].update(version='changed'),'NEEDS_EVIDENCE')
    add('perfect-score-paused',lambda d:d['product'].update(lifecycle='paused'),'STOP_EXISTING_DECISION')
    add('perfect-score-closed',lambda d:d['product'].update(lifecycle='closed'),'STOP_EXISTING_DECISION')
    add('known-zero-cannot-average',lambda d:d['ratings']['PF3'].update(score=0),'DOES_NOT_MEET')
    add('only-self-attested-plan',lambda d:[e.update(provenance='attested') for e in d['evidence']],'REWORK')
    add('empty-plan',lambda d:(d.clear(),d.update(new_dossier(p,'empty','空方案','agent','2026-11-12',review_object='development_plan'))),'NEEDS_EVIDENCE')
    add('product-stage-in-plan',lambda d:d.update(stage='launch'),'INVALID')
    add('cycle',lambda d:d['plan']['milestones'][0].update(depends_on=['M1']),'INVALID')
    add('budget-wrong-scope',lambda d:d['budget'].update(scope='whole-roadmap'),'INVALID')
    add('metric-mixing',lambda d:d['ratings'].update(J1=d['ratings']['PJ1']),'INVALID')
    add('duplicate-cost-assignment',lambda d:d['plan']['milestones'].append({**copy.deepcopy(d['plan']['milestones'][0]),'id':'M2'}),'INVALID')
    add('document-only-development-no-trials',document_only,'PLAN_ELIGIBLE_FOR_OWNER_REVIEW')
    add('document-only-vague-design',lambda d:(document_only(d),[r.update(score=1) for r in d['ratings'].values()]),'REWORK')
    add('document-only-no-acceptance',lambda d:(document_only(d),d['plan']['milestones'][0]['acceptance'].update({'pass':''})),'NEEDS_EVIDENCE')
    add('document-only-known-scope-error',lambda d:(document_only(d),d['gates']['PG_SCOPE'].update(status='not_met',reason='设计未覆盖承诺的业务终态')),'DOES_NOT_MEET')
    add('document-only-future-outcome-overclaim',lambda d:(document_only(d),d['claims'][0].update(status='supported',evidence_refs=['source-a'])),'NEEDS_EVIDENCE')
    add('cost-category-conflicts-with-lines',lambda d:d['bom']['coverage']['inference'].update(status='not_applicable'),'DOES_NOT_MEET')
    add('critical-evidence-earns-bonus',lambda d:d['plan']['assumptions'][0].update(status='supported'),'PLAN_ELIGIBLE_FOR_OWNER_REVIEW')
    add('critical-evidence-wrong-kind-no-bonus',lambda d:d['plan']['assumptions'][0].update(status='supported',evidence_refs=['test_run-a','test_run-b']),'PLAN_ELIGIBLE_FOR_OWNER_REVIEW')
    add('critical-evidence-cannot-rescue-design',lambda d:(d['plan']['assumptions'][0].update(status='supported'),d['gates']['PG_EVAL'].update(status='not_met')),'DOES_NOT_MEET')
    historical=[]  # Private historical compatibility records are not distributed.
    passed=all(x['matched'] and not x['protocol_errors'] and x['replay_equal'] is not False for x in cases) and all(x['matched'] for x in historical)
    summary=dict(version=VERSION,checked_at_utc=datetime.now(timezone.utc).isoformat(),passed=passed,
        plan_behavior_cases=len(cases),expected_rejections=sum(c['expected']=='INVALID' for c in cases),
        protocol_bundles=sum(c['actual']!='INVALID' for c in cases),cases=cases,product_compatibility=historical,
        all_nonempty_plan_fixture_budgets_unset=True,ai_judge_calibration='NOT_CALIBRATED',
        human_acceptance='not_run',real_world='not_run',
        limits=['合成行为预期不是人工金标','回放不重新执行历史产品','公开回归不含内部独立AI历史记录','没有发起付费、部署或外联'],
        implementation_sha256={f:digest((ROOT/f).read_bytes()) for f in ('harness.py','plan_review.py','templates.py','protocol_adapter.py','policy.json')})
    write_json(out/'verification.json',summary)
    write_json(out/'calibration.json',calibrate([],p))
    lines=['# 开发方案路径 eval · '+VERSION,'',f"结果：{'通过' if passed else '失败'}。{len(cases)}个行为案例，{summary['protocol_bundles']}份协议包，{len(historical)}份产品档案兼容回放。",'',
           '所有生成案例仅为synthetic，额度为空；通过的方案也没有现实资源资格。','',
           '| 案例 | 预期 | 实际 | 一致 |','|---|---|---|---|']
    lines += [f"| {c['id']} | {c['expected']} | {c['actual']} | {c['matched']} |" for c in cases]
    lines += ['','## 产品兼容','']+[f"- {r['path']}：{r['score_before']} → {r['score_after']}；差异字段 {r['changed_fields']}" for r in historical]
    lines += ['','程序回归证明规则执行和分离边界；没有独立人工金标和经营校准，不声称方案分能预测商业成功。']
    (out/'report.md').write_text('\n'.join(lines)+'\n','utf-8')
    print(json.dumps({'passed':passed,'plan_cases':len(cases),'protocol_bundles':summary['protocol_bundles'],'product_compatibility':len(historical),'failures':[x['id'] for x in cases if not x['matched']]},ensure_ascii=False))
    return 0 if passed else 1


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    raise SystemExit(run(ap.parse_args().out))

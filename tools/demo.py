"""Generate explicitly synthetic product and plan demonstrations with empty budgets."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from harness import read_json, write_json, export_report
from test_harness import synthetic_fixture
from test_plan_review import plan_fixture


def run(out):
    out=Path(out)
    if out.exists():
        raise ValueError('Use a new output directory; prior records are never overwritten.')
    out.mkdir(parents=True)
    policy=read_json(ROOT/'policy.json')
    summary={}
    for name,factory in [('product',synthetic_fixture),('plan',plan_fixture)]:
        inputs=out/(name+'-inputs');inputs.mkdir()
        dossier=factory(inputs,policy)
        dossier['budget'].update(status='unset',caps=dict.fromkeys(policy['resource_dimensions']),evidence_refs=[])
        write_json(inputs/'dossier.json',dossier)
        result=export_report(dossier,policy,out/name,inputs)
        assert dossier['purpose']=='synthetic'
        assert result['resource_status']=='BLOCKED'
        summary[name]={'verdict':result['verdict'],'score':result['score'],'resource_status':result['resource_status'],'synthetic':True}
    write_json(out/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    run(parser.parse_args().out)

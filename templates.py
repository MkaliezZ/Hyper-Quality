"""Explicit unknowns: a new dossier can be scored, but cannot pass release gates."""


def three(value=None):
    return dict.fromkeys(("low", "base", "high"), value)


def new_dossier(policy, product_id, name, profile, as_of, review_object=None):
    from plan_review import policy_for, PHASES
    policy = policy_for(policy, review_object or 'product')
    if profile not in policy["profiles"]:
        raise ValueError("未知产品类型")
    d = {
        "schema_version": "1.0", "as_of": as_of, "purpose": "live_review", "stage": "discovery",
        "product": {"id": product_id, "name": name, "version": "unversioned", "profile": profile,
                    "lifecycle": "active", "user": "待明确", "buyer": "待明确", "job": "待明确", "alternative": "待比较：不做/人工/通用AI/直接替代"},
        "evidence": [],
        "ratings": {m["id"]: {"score": None, "reason": "未取得适用证据", "evidence_refs": []} for m in policy["metrics"]},
        "gates": {},
        "reviews": {k: {"status": "not_run", "reviewer_kind": "not_recorded", "reason": "尚未取得评议", "evidence_refs": []}
                    for k in ("engineering", "domain", "aesthetic", "human_acceptance", "real_world")},
        "claims": [],
        "layer_findings": {k: {"value": "待识别可交付价值", "problems": "证据尚缺", "next_action": "取得本层直接证据"}
                           for k in ("judgment", "function", "asset")},
        "bom": {"currency": "CNY", "horizon_months": 1, "monthly_units": three(), "price_per_unit": three(),
                "coverage": {k: {"status": "unknown", "reason": "尚未盘点", "evidence_refs": []} for k in policy["bom_categories"]}, "lines": []},
        "budget": {"status": "unset", "caps": dict.fromkeys(policy["resource_dimensions"]), "evidence_refs": []},
        "next_experiment": {"hypothesis": "待明确", "deliverable": "待明确", "success": "待预注册", "stop": "待预注册", "owner": "待指定", "deadline": "待排期", "resource_cap": "待填"}
    }
    # Existing Python callers and archived schema-1.0 dossiers remain product-only.
    if review_object is not None:
        d.update(schema_version='1.1', review_object=review_object)
    if review_object == 'development_plan':
        d['stage']='validation'
        d['plan']={
            'version':'plan-0.1-draft', 'baseline_product_version':None,
            'scope_in':[], 'scope_out':[], 'requested_milestone':'M1',
            'assumptions':[], 'dependencies':[],
            'milestones':[{'id':'M1','title':'首个验证里程碑','owner':None,'due':None,'depends_on':[],
                'deliverable':'','acceptance':dict.fromkeys(('method','pass','fail','evidence_required'),''),
                'stop_conditions':[],'validates_assumptions':[],'resolves_dependencies':[],'bom_line_ids':[]}],
            'stop_conditions':[],
            'phase_coverage':{k:{'status':'unknown','reason':'尚未盘点','evidence_refs':[]} for k in PHASES}}
        d['budget']['scope']='milestone:M1'
    return d

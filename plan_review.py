"""Development-plan contracts and gates. No execution or spending side effects."""
import copy
from datetime import date

PHASES = ('validation', 'development', 'operation', 'exit')
OBJECTS = ('product', 'development_plan')
ASSUMPTION_KINDS = {
    'demand': ['customer', 'transaction', 'raw_data'],
    'feasibility': ['test_run', 'raw_data'],
    'economics': ['cost', 'transaction', 'raw_data'],
    'rights': ['rights', 'human_review'],
}


def policy_for(policy, review_object):
    if review_object not in OBJECTS:
        raise ValueError('未知评审对象；仅支持product/development_plan')
    if review_object == 'product':
        return policy
    if 'plan_review' not in policy:
        raise ValueError('当前规则没有开发方案评审路径')
    return {**policy, **policy['plan_review']}


def validate_plan(d, p, require, refs):
    plan = d['plan']
    require(isinstance(plan, dict), 'plan须为对象')
    required = {'version', 'baseline_product_version', 'scope_in', 'scope_out', 'requested_milestone',
                'assumptions', 'dependencies', 'milestones', 'stop_conditions', 'phase_coverage'}
    require(set(plan) == required, 'plan字段缺失或多余')
    text = lambda v: isinstance(v, str) and bool(v.strip())
    require(text(plan['version']), '方案版本必填')
    require(plan['baseline_product_version'] is None or text(plan['baseline_product_version']), '基线版本非法')
    for key in ('scope_in', 'scope_out', 'stop_conditions'):
        require(isinstance(plan[key], list) and all(text(x) for x in plan[key]), key+'须为文字数组；待补用空数组')
    for key in ('assumptions', 'dependencies', 'milestones'):
        require(isinstance(plan[key], list), key+'须为数组')
        ids = [x['id'] for x in plan[key]]
        require(all(text(x) for x in ids) and len(ids)==len(set(ids)), key+'编号非法或重复')
    aids = {x['id'] for x in plan['assumptions']}
    deps = {x['id'] for x in plan['dependencies']}
    mids = {x['id'] for x in plan['milestones']}
    require(plan['requested_milestone'] is None or plan['requested_milestone'] in mids, '请求里程碑悬空')
    require(d['budget'].get('scope') == ('milestone:'+plan['requested_milestone'] if plan['requested_milestone'] else None), '预算必须绑定当前请求里程碑')
    for a in plan['assumptions']:
        require(set(a)=={'id','kind','statement','critical','status','validation','evidence_refs'}, '假设字段非法')
        require(a['kind'] in ASSUMPTION_KINDS and type(a['critical']) is bool, '假设类别/critical非法')
        require(a['status'] in ('unknown','supported','refuted'), '假设状态非法')
        require(text(a['statement']) and isinstance(a['validation'], str), '假设及验证方法必填')
        refs(a['evidence_refs'])
    for x in plan['dependencies']:
        require(set(x)=={'id','description','critical','status','owner','fallback','evidence_refs'}, '依赖字段非法')
        require(type(x['critical']) is bool and text(x['description']), '依赖说明/critical非法')
        require(x['status'] in ('available','unverified','unavailable'), '依赖状态非法')
        require(x['owner'] is None or text(x['owner']), '依赖负责人非法')
        require(isinstance(x['fallback'], str), '依赖备选须为文字')
        refs(x['evidence_refs'])
    line_by_id = {x['id']:x for x in d['bom']['lines']}
    assigned = []
    for m in plan['milestones']:
        require(set(m)=={'id','title','owner','due','depends_on','deliverable','acceptance','stop_conditions',
                          'validates_assumptions','resolves_dependencies','bom_line_ids'}, '里程碑字段非法')
        require(text(m['title']) and isinstance(m['deliverable'], str), '里程碑名称和交付物非法')
        require(m['owner'] is None or text(m['owner']), '里程碑负责人非法')
        if m['due'] is not None: date.fromisoformat(m['due'])
        for key, allowed in (('depends_on',mids),('validates_assumptions',aids),('resolves_dependencies',deps),('bom_line_ids',set(line_by_id))):
            v=m[key]
            require(isinstance(v,list) and len(v)==len(set(v)) and all(x in allowed for x in v), '里程碑存在重复/悬空引用:'+key)
        require(m['id'] not in m['depends_on'], '里程碑不能依赖自身')
        require(set(m['acceptance'])=={'method','pass','fail','evidence_required'} and all(isinstance(v,str) for v in m['acceptance'].values()), '验收须有方法、成功线、失败线和证据')
        require(isinstance(m['stop_conditions'],list) and all(text(x) for x in m['stop_conditions']), '里程碑停止条件非法')
        for lid in m['bom_line_ids']:
            require(line_by_id[lid]['phase'] in ('validation','development') and line_by_id[lid]['basis']!='sunk', '里程碑只能绑定本轮验证/开发增量成本')
        assigned += m['bom_line_ids']
    require(len(assigned)==len(set(assigned)), '同一开发成本行不能被多个里程碑重复归属')
    graph={m['id']:m['depends_on'] for m in plan['milestones']}
    def visit(mid, active, done):
        require(mid not in active, '里程碑依赖成环')
        if mid not in done:
            for child in graph[mid]: visit(child,active|{mid},done)
            done.add(mid)
    done=set()
    for mid in graph: visit(mid,set(),done)
    require(set(plan['phase_coverage'])==set(PHASES), '需盘点验证/开发/运营/退出四阶段BOM')
    for c in plan['phase_coverage'].values():
        require(c['status'] in ('included','not_applicable','unknown') and text(c['reason']), '阶段BOM状态/理由非法')
        refs(c['evidence_refs'])
    for line in d['bom']['lines']:
        require(line.get('phase') in PHASES, '方案BOM行须标phase')
        if line['phase'] in ('validation','development'):
            require(line['basis'] in ('one_off','sunk'), '开发/验证成本按里程碑一次性计，重复次数写quantity')
    for c in d['claims']:
        require(c.get('claim_scope') in ('planned','existing'), '方案卖点须标planned/existing')


def assess_plan(d, p, ev, select, cost_model):
    plan=d['plan']; gates=[]
    def add(gid, name, status, reason, refs=()):
        gates.append(dict(id=gid,name=name,status=status,reason=reason,evidence_refs=list(refs),computed=True))
    def proof(refs,target,kinds=None,cap=2): return select(ev,refs,target,kinds,cap)
    def content(x): return isinstance(x,str) and bool(x.strip())
    milestones=plan['milestones']
    requested=next((m for m in milestones if m['id']==plan['requested_milestone']),None)
    missing=[]
    if not plan['scope_in'] or not plan['scope_out']:missing.append('做与不做的范围')
    if not requested:missing.append('本次请求里程碑')
    if not plan['assumptions']:missing.append('关键假设清单')
    if not plan['dependencies']:missing.append('关键依赖清单')
    if not d['claims']:missing.append('候选卖点')
    add('PLAN_STRUCTURE','方案范围、假设、依赖和卖点','unknown' if missing else 'met','缺少：'+','.join(missing) if missing else '已明确对象；实质有效性另按证据评分')
    assigned={lid for m in milestones for lid in m['bom_line_ids']}
    orphans=[x['id'] for x in d['bom']['lines'] if x['phase'] in ('validation','development') and x['basis']!='sunk' and x['id'] not in assigned]
    if orphans:add('PLAN_COST_ASSIGNMENT','开发资源归属','unknown','未绑定里程碑：'+','.join(orphans))
    for m in milestones:
        gaps=[k for k in ('owner','due','deliverable') if not content(m[k])]
        gaps += ['acceptance.'+k for k,v in m['acceptance'].items() if not content(v)]
        if not m['stop_conditions']:gaps.append('stop_conditions')
        if not m['bom_line_ids']:gaps.append('bom_line_ids')
        add('PLAN_MILESTONE_'+m['id'],'里程碑 '+m['title'],'unknown' if gaps else 'met',
            '缺少：'+','.join(gaps) if gaps else '交付/负责人/日期/验收/停止/成本已列；不代表里程碑已完成')
    if requested and requested['depends_on']:
        add('PLAN_REQUEST_READY','本次里程碑的前置完成','unknown','当前仍依赖计划内前置里程碑；先完成前置，再用实际产物更新方案版本，不能一次放行整条路线')
    if requested and requested['due'] and requested['due'] < d['as_of']:
        add('PLAN_DEADLINE','请求里程碑截止日期','not_met','请求执行的截止日期早于评审日期；应更新计划而非假定已完成')
    add('PLAN_STOP','全局停止条件','met' if plan['stop_conditions'] else 'unknown','已列全局停止线' if plan['stop_conditions'] else '缺少全局停止线')
    checked_assumptions=[]
    for a in plan['assumptions']:
        target='assumption:'+a['id']
        kinds=ASSUMPTION_KINDS[a['kind']]
        available=proof(a['evidence_refs'],target,kinds if a['status']=='supported' else kinds+['source','counterevidence'],3 if a['status']=='supported' else 2)
        status=a['status'] if a['status']=='unknown' or available else 'unknown'
        checked_assumptions.append({**a,'status':status,'usable_evidence_refs':[e['id'] for e in available]})
        if a['critical']:
            validation_allowed=(d['stage']=='validation' and requested and a['id'] in requested['validates_assumptions'] and content(a['validation']))
            condition='not_met' if status=='refuted' else ('met' if status=='supported' or validation_allowed else 'unknown')
            add('PLAN_ASSUMPTION_'+a['id'],'关键假设 '+a['statement'],condition,
                '已被反证，须改方案' if status=='refuted' else ('有适用支持证据' if status=='supported' else '仅限下一里程碑验证此未知假设' if validation_allowed else '关键假设未知/缺支持证据'),[e['id'] for e in available])
    checked_dependencies=[]
    for x in plan['dependencies']:
        available=proof(x['evidence_refs'],'dependency:'+x['id'],None,3 if x['status']=='available' else 2)
        status=x['status'] if x['status']=='unverified' or available else 'unverified'
        checked_dependencies.append({**x,'status':status,'usable_evidence_refs':[e['id'] for e in available]})
        if x['critical']:
            investigation=(d['stage']=='validation' and requested and x['id'] in requested['resolves_dependencies'] and content(x['fallback']) and x['owner'])
            condition='not_met' if status=='unavailable' else ('met' if status=='available' and x['owner'] else 'met' if investigation else 'unknown')
            add('PLAN_DEPENDENCY_'+x['id'],'关键依赖 '+x['description'],condition,
                '已知无法取得，当前方案不能执行' if status=='unavailable' else '依赖有可核对可用依据和负责人' if status=='available' and x['owner'] else '仅限下一里程碑核实依赖' if investigation else '可用性/负责人未确认',[e['id'] for e in available])
    def subset_costs(lines, covered, gap):
        subset=copy.deepcopy(d)
        subset['bom']['lines']=lines
        # Category coverage was checked on the full plan; this calculation only
        # partitions its declared rows and must not invent absent phase costs.
        costs=cost_model(subset,p,ev,check_coverage=False)
        if not covered:
            costs['complete']=False;costs['gaps'].append(gap)
            costs['totals']={s:dict.fromkeys(p['resource_dimensions']) for s in ('low','base','high')}
        costs['economics']=None;costs['pressure_cash_balance']=None
        costs['note']='分组增量需求；非已批准额度或独立利润预测。完整方案缺项仍阻断放行。'
        return costs
    phases={}
    for phase,c in plan['phase_coverage'].items():
        lines=[x for x in d['bom']['lines'] if x['phase']==phase and x['basis']!='sunk']
        supported=proof(c['evidence_refs'],'phase:'+phase)
        good=(c['status']=='included' and bool(lines)) or (c['status']=='not_applicable' and bool(supported) and not lines)
        conflict=c['status']=='not_applicable' and bool(lines)
        add('PLAN_PHASE_'+phase,phase+'成本盘点','not_met' if conflict else 'met' if good else 'unknown',
            '声明不适用但存在该阶段成本行' if conflict else '阶段已列成本/有据不适用' if good else '阶段成本缺项或不适用无证据',[e['id'] for e in supported])
        costs=subset_costs(lines,good and not conflict,'阶段成本范围未知/冲突')
        phases[phase]={'status':c['status'],'line_ids':[x['id'] for x in lines],
                       'totals':costs['totals'],'complete':costs['complete'],'gaps':costs['gaps']}
    # A separate cost window for the one requested milestone, not the entire roadmap.
    ids=set(requested['bom_line_ids']) if requested else set()
    requested_costs=subset_costs([x for x in d['bom']['lines'] if x['id'] in ids],bool(ids),'本次里程碑没有成本行')
    return gates, {'version':plan['version'],'requested_milestone':plan['requested_milestone'],
        'milestones':milestones,'stop_conditions':plan['stop_conditions'],'assumptions':checked_assumptions,
        'dependencies':checked_dependencies,'phases':phases,'requested_costs':requested_costs,
        'scope_in':plan['scope_in'],'scope_out':plan['scope_out']}

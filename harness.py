"""Evidence-bounded product review. Python 3.11+, standard library only.

No network, subprocess, model calls, publication or funding side effects.
Semantic relevance remains a recorded reviewer judgment, not a hash property.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import math
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from plan_review import policy_for, validate_plan, assess_plan

ROOT = Path(__file__).resolve().parent
VERSION = "0.3.0"
getcontext().prec = 40
LAYERS = ("judgment", "function", "asset")
REVIEWS = ("engineering", "domain", "aesthetic", "human_acceptance", "real_world")
SCENARIOS = ("low", "base", "high")
KINDS = {"source", "test_run", "raw_data", "customer", "transaction", "human_review", "rights", "cost", "counterevidence"}


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def read_json(path):
    def pairs(items):
        d = {}
        for k, v in items:
            require(k not in d, f"重复 JSON 字段: {k}")
            d[k] = v
        return d
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(Invalid(f"非法数值 {x}")))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def validate_policy(p):
    require(p.get("version") and p.get("status") in ("provisional", "calibrated"), "规则版本/状态非法")
    require(set(p["layer_weights"]) == set(LAYERS), "三层权重缺项")
    require(all(number(x) and x > 0 for x in p["layer_weights"].values()), "权重必须为正")
    require(sum(p["layer_weights"].values()) == 100, "三层权重之和须为100")
    if p.get('score_basis')=='design_quality':
        bonus=p.get('evidence_bonus',{})
        require(number(bonus.get('max_points')) and 0<=bonus['max_points']<=100, '方案证据加分上限非法')
        require(set(bonus.get('kind_weights',{}))=={'demand','feasibility','economics','rights'} and
                all(number(v) and v>0 for v in bonus['kind_weights'].values()), '方案证据加分类别权重非法')
        require(set(bonus.get('strength_factors',{}))=={'observed','replicated'} and
                all(number(v) and 0<=v<=1 for v in bonus['strength_factors'].values()) and
                bonus['strength_factors']['observed']<=bonus['strength_factors']['replicated'], '方案证据加分强度非法')
    ids = [m["id"] for m in p["metrics"]]
    require(len(set(ids)) == len(ids), "指标编号重复")
    require(set(p["zero_score_blocks"]) <= set(ids), "零分阻断规则含未知指标")
    for layer in LAYERS:
        ms = [m for m in p["metrics"] if m["layer"] == layer]
        require(ms and all(number(m["weight"]) and m["weight"] > 0 for m in ms), "指标权重非法")
        require(sum(m["weight"] for m in ms) == 100, "层内权重之和须为100")
    for m in p['metrics']:
        require(all(k in m['kinds'] and type(v) is int and 0<=v<=4 for k,v in m.get('kind_caps',{}).items()), '指标证据类别上限非法')
    for stage, cfg in p["stages"].items():
        for value in [cfg["total_min"], cfg["coverage_min"], *cfg["layer_min"].values()]:
            require(number(value) and 0 <= value <= 100, f"{stage} 阈值非法")
    if "plan_review" in p:
        branch = {k:v for k,v in policy_for(p, "development_plan").items() if k != "plan_review"}
        validate_policy(branch)
        require(not set(ids) & {m['id'] for m in branch['metrics']}, "方案和产品指标编号必须分离")
    return p


def range_check(v, name, allow_null=True):
    require(isinstance(v, dict) and set(v) == set(SCENARIOS), f"{name} 需要 low/base/high")
    for x in v.values():
        require((x is None and allow_null) or (number(x) and x >= 0), f"{name} 必须为非负有限数或null")
    known = [v[k] for k in SCENARIOS if v[k] is not None]
    require(known == sorted(known), f"{name} 需 low <= base <= high")


def gates_for(p, profile, stage):
    return [g for g in p["gates"] + p["profiles"][profile]["extra_gates"] if stage in g["stages"]]


def validate(d, p):
    require(isinstance(d, dict), "档案须为对象")
    required = {"schema_version", "product", "as_of", "purpose", "stage", "evidence", "ratings", "gates", "reviews", "claims", "layer_findings", "bom", "budget", "next_experiment"}
    obj = d.get("review_object", "product")
    if d.get("schema_version") == "1.1":
        required.add("review_object")
        require(obj in ("product", "development_plan"), "评审对象非法")
        if obj == "development_plan": required.add("plan")
    else:
        require("review_object" not in d, "旧档案只支持产品路径；方案须使用schema 1.1")
    require(set(d) == required, f"档案字段差异: {set(d) ^ required}")
    require(d["schema_version"] in ("1.0", "1.1"), "不支持的档案版本")
    p = policy_for(p, obj)
    require(d["purpose"] in ("live_review", "retrospective", "synthetic"), "purpose非法")
    date.fromisoformat(d["as_of"])
    prod = d["product"]
    for key in ("id", "name", "version", "profile", "lifecycle", "user", "buyer", "job", "alternative"):
        require(isinstance(prod.get(key), str) and prod[key].strip(), f"product.{key} 必填")
    require(prod["profile"] in p["profiles"], "未知产品类型")
    require(prod["lifecycle"] in ("active", "paused", "closed"), "生命周期非法")
    require(d["stage"] in p["stages"], "阶段非法")
    mids = {m["id"] for m in p["metrics"]}
    require(set(d["ratings"]) == mids, "评分指标缺失或多余")
    eids = [e["id"] for e in d["evidence"]]
    require(len(eids) == len(set(eids)), "证据编号重复")
    for e in d["evidence"]:
        for key in ("id", "path", "sha256", "quote", "locator", "product_version", "independence_group", "reviewer"):
            require(isinstance(e.get(key), str) and e[key].strip(), f"证据 {e.get('id')} 缺 {key}")
        require(e["kind"] in KINDS, "证据类型非法")
        require(e["strength"] in p["strength_caps"], "证据强度非法")
        require(e["provenance"] in ("direct", "attested", "synthetic"), "证据性质非法")
        require(e["semantic_status"] in ("checked", "unreviewed", "conflicted"), "语义核查状态非法")
        require(isinstance(e["supports"], list) and e["supports"], "证据需绑定支持对象")
        require(isinstance(e["valid_days"], int) and not isinstance(e["valid_days"], bool) and e["valid_days"] >= 0, "证据有效期非法")
        date.fromisoformat(e["observed_on"])
        if d["schema_version"] == "1.1":
            require(e.get("review_object") in ("product", "development_plan", "shared"), "新证据须标明适用评审对象")
            if e['review_object'] == 'development_plan':
                require(isinstance(e.get('plan_version'),str) and e['plan_version'].strip(), '方案证据须绑定plan_version')
    def refs(v):
        require(isinstance(v, list) and all(x in eids for x in v), "悬空或非法证据引用")
    for mid, r in d["ratings"].items():
        require(set(r) == {"score", "reason", "evidence_refs"}, f"评分字段非法 {mid}")
        require(r["score"] is None or (type(r["score"]) is int and 0 <= r["score"] <= 4), "分值只能0..4整数或null")
        require(isinstance(r["reason"], str) and r["reason"].strip(), f"{mid} 需理由")
        refs(r["evidence_refs"])
    allowed_gates = {g["id"] for g in p["gates"] + p["profiles"][prod["profile"]]["extra_gates"]}
    require(set(d["gates"]) <= allowed_gates, "门槛编号未知")
    for gid, g in d["gates"].items():
        require(g["status"] in ("met", "not_met", "unknown"), f"门槛 {gid} 状态非法；门槛不可自行豁免")
        require(isinstance(g["reason"], str) and g["reason"].strip(), "门槛须有理由")
        refs(g["evidence_refs"])
    require(set(d["reviews"]) == set(REVIEWS), "五类评议缺项")
    for name, r in d["reviews"].items():
        require(r["status"] in ("not_run", "passed", "failed", "not_applicable"), "评议状态非法")
        require(r["reviewer_kind"] in ("human", "agent", "code", "model", "not_recorded"), "评议者类型非法")
        require(isinstance(r["reason"], str) and r["reason"], "评议理由缺失")
        refs(r["evidence_refs"])
        if r["status"] == "passed" and name == "human_acceptance":
            require(r["reviewer_kind"] == "human", "AI不得自填人工认可")
    cids = [c["id"] for c in d["claims"]]
    require(len(cids) == len(set(cids)), "卖点编号重复")
    for c in d["claims"]:
        require(c["status"] in ("candidate", "supported", "withdrawn"), "卖点状态非法")
        require(c["text"] and c["boundary"], "卖点及适用边界必填")
        require(c["proof_kind"] in ("capability", "outcome", "commercial"), "卖点证据类别非法")
        refs(c["evidence_refs"])
        refs(c["counterevidence_refs"])
    require(set(d["layer_findings"]) == set(LAYERS), "每层都须总结")
    for layer, f in d["layer_findings"].items():
        for k in ("value", "problems", "next_action"):
            require(isinstance(f.get(k), str) and f[k].strip(), f"{layer}.{k} 必填")
    bom = d["bom"]
    require(bom["currency"] == "CNY", "首版仅支持单一CNY；外币须先单列汇率证据换算")
    require(type(bom["horizon_months"]) is int and bom["horizon_months"] > 0, "成本窗口需正整数月")
    range_check(bom["monthly_units"], "monthly_units")
    range_check(bom["price_per_unit"], "price_per_unit")
    require(set(bom["coverage"]) == set(p["bom_categories"]), "BOM类别覆盖不完整")
    for cat, c in bom["coverage"].items():
        require(c["status"] in ("included", "not_applicable", "unknown"), "BOM覆盖状态非法")
        require(c["reason"], "BOM覆盖须说明")
        refs(c["evidence_refs"])
    line_ids = [x["id"] for x in bom["lines"]]
    require(len(line_ids) == len(set(line_ids)), "BOM行重复")
    for line in bom["lines"]:
        require(line["category"] in p["bom_categories"], "BOM类别未知")
        require(line["basis"] in ("one_off", "monthly", "per_unit", "sunk"), "BOM计算基准非法")
        require(line["status"] in ("estimated", "quoted", "measured", "unknown"), "BOM证据状态非法")
        require(line["reason"] and line["unit"], "成本行需单位和口径")
        range_check(line["quantity"], "quantity")
        require(set(line["per_quantity"]) == set(p["resource_dimensions"]), "资源维度不得省略；未知填null")
        for dim, rr in line["per_quantity"].items():
            range_check(rr, dim)
        refs(line["evidence_refs"])
    require(set(d["budget"]["caps"]) == set(p["resource_dimensions"]), "预算维度缺项")
    for v in d["budget"]["caps"].values():
        require(v is None or (number(v) and v >= 0), "预算上限非法")
    require(d["budget"]["status"] in ("unset", "proposed", "confirmed"), "预算状态非法")
    refs(d["budget"]["evidence_refs"])
    if obj == "development_plan": validate_plan(d, p, require, refs)
    return d


def inspect_evidence(d, p, root):
    checked = {}
    as_of = date.fromisoformat(d["as_of"])
    for e in d["evidence"]:
        errors = []
        path = (root / e["path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            errors.append("证据路径越出档案目录")
        elif not path.is_file():
            errors.append("证据快照缺失")
        else:
            raw = path.read_bytes()
            if digest(raw) != e["sha256"]:
                errors.append("证据SHA256不匹配")
            try:
                content = raw.decode("utf-8-sig")
                if e["quote"] not in content:
                    errors.append("引用原文未在快照中找到")
            except UnicodeDecodeError:
                errors.append("本版需UTF-8证据摘录或文本原件")
        age = (as_of - date.fromisoformat(e["observed_on"])).days
        if age < 0 or age > e["valid_days"]:
            errors.append("证据过期或来自未来")
        versions = (d["product"]["version"], "shared")
        obj = d.get('review_object', 'product')
        if obj == 'development_plan':
            versions += (d['plan']['baseline_product_version'],)
        if e["product_version"] not in versions:
            errors.append("产品版本不匹配")
        if obj == 'product' and e.get('review_object') == 'development_plan':
            errors.append('方案证据不能支持产品验收')
        if e.get('review_object') == 'development_plan' and obj == 'development_plan' and e['plan_version'] != d['plan']['version']:
            errors.append('方案版本不匹配')
        if e.get('review_object') == 'shared' and e['kind'] not in ('source','rights','cost'):
            errors.append('实测/用户/交易证据不可伪装为跨对象shared')
        # Either sharing field must preserve version-sensitive evidence boundaries,
        # including legacy input attempting to reuse an old run as "shared".
        if e['product_version']=='shared' and e['kind'] not in ('source','rights','cost'):
            errors.append('实测/用户/交易证据必须绑定明确产品版本，不能使用shared版本')
        if d['schema_version']=='1.1' and ((e.get('review_object')=='shared') != (e['product_version']=='shared')):
            errors.append('共享证据的review_object与product_version必须同时为shared')
        if e["semantic_status"] != "checked":
            errors.append("语义未核查或存在冲突")
        if e["provenance"] == "synthetic" and d["purpose"] != "synthetic":
            errors.append("合成证据不能支持真实评审")
        cap = p["strength_caps"][e["strength"]]
        if e["provenance"] == "attested":
            cap = min(cap, 2)
        checked[e["id"]] = {**e, "usable": not errors, "errors": errors, "cap": cap}
    return checked


def select_evidence(evidence, refs, target, kinds=None, min_cap=0):
    return [evidence[r] for r in refs if evidence[r]["usable"] and target in evidence[r]["supports"]
            and (kinds is None or evidence[r]["kind"] in kinds) and evidence[r]["cap"] >= min_cap]


def cost_model(d, p, evidence, *, check_coverage=True):
    b = d["bom"]
    gaps = []
    for cat, c in (b["coverage"].items() if check_coverage else ()):
        if c["status"] == "unknown":
            gaps.append(f"BOM:{cat}:缺项")
        elif c["status"] == "not_applicable" and not select_evidence(evidence, c["evidence_refs"], "BOM"):
            gaps.append(f"BOM:{cat}:不适用无证据")
        elif c["status"] == "included" and not any(x["category"] == cat and x["basis"] != "sunk" for x in b["lines"]):
            gaps.append(f"BOM:{cat}:未列成本行")
    totals, economics = {}, {}
    for s in SCENARIOS:
        dims = {dim: Decimal(0) for dim in p["resource_dimensions"]}
        unit_cash = Decimal(0)
        fixed_cash = Decimal(0)
        horizon = Decimal(b["horizon_months"])
        for line in b["lines"]:
            if line["basis"] == "sunk":
                continue
            supported = select_evidence(evidence, line["evidence_refs"], "BOM")
            if line["status"] == "unknown" or not supported:
                gaps.append(f"BOM:{line['id']}:未核查估计/报价依据")
            mult = {"one_off": Decimal(1), "monthly": horizon, "per_unit": None if b["monthly_units"][s] is None else horizon * Decimal(str(b["monthly_units"][s]))}[line["basis"]]
            q = None if line["quantity"][s] is None else Decimal(str(line["quantity"][s]))
            for dim in dims:
                rate = None if line["per_quantity"][dim][s] is None else Decimal(str(line["per_quantity"][dim][s]))
                if q is None or rate is None or mult is None:
                    dims[dim] = None
                    gaps.append(f"BOM:{line['id']}:{dim}:{s}:未知")
                elif dims[dim] is not None:
                    dims[dim] += q * rate * mult
            rate = None if line["per_quantity"]["cash"][s] is None else Decimal(str(line["per_quantity"]["cash"][s]))
            value = None if q is None or rate is None else q * rate
            if line["basis"] == "per_unit":
                unit_cash = None if value is None or unit_cash is None else unit_cash + value
            else:
                fixed_cash = None if value is None or fixed_cash is None else fixed_cash + value * mult
        coverage_unknown = any(x.startswith("BOM:") and ("缺项" in x or "无证据" in x or "未列" in x) for x in gaps)
        if coverage_unknown:
            dims = {k: None for k in dims}
            unit_cash = fixed_cash = None
        total_units = None if b["monthly_units"][s] is None else Decimal(str(b["monthly_units"][s])) * horizon
        price = None if b["price_per_unit"][s] is None else Decimal(str(b["price_per_unit"][s]))
        contribution = None if price is None or unit_cash is None else price - unit_cash
        revenue = None if price is None or total_units is None else price * total_units
        economics[s] = {"total_units": total_units, "unit_cash_cost": unit_cash,
                        "unit_cash_contribution": contribution,
                        "cash_margin": None if contribution is None or not price else contribution / price,
                        "fixed_cash": fixed_cash, "revenue": revenue,
                        "cash_balance": None if revenue is None or dims["cash"] is None else revenue - dims["cash"],
                        "break_even_units": None if contribution is None or contribution <= 0 or fixed_cash is None else math.ceil(fixed_cash / contribution)}
        totals[s] = dims
    # Pressure combines high costs with low volume/revenue. It does not multiply by an invented probability.
    worst = economics["high"]
    low_units = economics["low"]["total_units"]
    price_low = None if b["price_per_unit"]["low"] is None else Decimal(str(b["price_per_unit"]["low"]))
    pressure_balance = None
    if all(x is not None for x in (low_units, price_low, worst["unit_cash_cost"], worst["fixed_cash"])):
        pressure_balance = low_units * (price_low - worst["unit_cash_cost"]) - worst["fixed_cash"]
    def serialized(value):
        if isinstance(value, Decimal):
            out = float(value)
            require(math.isfinite(out), "成本计算超出有限数范围")
            return out
        if isinstance(value, dict):
            return {k: serialized(v) for k, v in value.items()}
        if isinstance(value, list):
            return [serialized(v) for v in value]
        return value
    return serialized({"currency": b["currency"], "horizon_months": b["horizon_months"], "totals": totals,
            "economics": economics, "pressure_cash_balance": pressure_balance,
            "gaps": sorted(set(gaps)), "complete": not gaps,
            "note": "现金贡献不是净利润；十进制计算；工时/token/关系另列；现金已含API费用时token不得二次折现；sunk不进入增量决策。"})


def evaluate(d, p, root=ROOT):
    validate_policy(p)
    validate(d, p)
    original_policy_hash = digest(canonical(p))
    obj = d.get('review_object', 'product')
    p = policy_for(p, obj)
    design = obj == 'development_plan' and p.get('score_basis') == 'design_quality'
    ev = inspect_evidence(d, p, Path(root))
    metrics, layer_scores = {}, {}
    for m in p["metrics"]:
        r = d["ratings"][m["id"]]
        eligible = select_evidence(ev, r["evidence_refs"], m["id"], m["kinds"])
        design_sources = {e['id'] for e in eligible if design and e['kind']=='source' and e['cap']>=2
                          and e['provenance']!='attested' and e.get('review_object')=='development_plan'
                          and e.get('plan_version')==d['plan']['version']}
        bounded_caps = {e['id']: 4 if e['id'] in design_sources else min(e['cap'],m.get('kind_caps',{}).get(e['kind'],4)) for e in eligible}
        cap = max(bounded_caps.values(), default=None)
        # Top score needs at least two independent evidence groups, not duplicate documents.
        if cap == 4 and not design_sources and len({e["independence_group"] for e in eligible if bounded_caps[e['id']] >= 3}) < 2:
            cap = 3
        score = None if r["score"] is None or cap is None else min(r["score"], cap)
        metrics[m["id"]] = {**m, "proposed_score": r["score"], "score": score, "evidence_cap": cap,
                             "reason": r["reason"], "evidence_refs": [e["id"] for e in eligible]}
    for layer in LAYERS:
        ms = [m for m in metrics.values() if m["layer"] == layer]
        floor = sum(m["weight"] * m["score"] / 4 for m in ms if m["score"] is not None)
        unknown_weight = sum(m["weight"] for m in ms if m["score"] is None)
        layer_scores[layer] = {"score": round(floor, 2), "ceiling": round(floor + unknown_weight, 2),
                               "coverage": 100 - unknown_weight, **d["layer_findings"][layer]}
    total = sum(layer_scores[k]["score"] * p["layer_weights"][k] / 100 for k in LAYERS)
    ceiling = sum(layer_scores[k]["ceiling"] * p["layer_weights"][k] / 100 for k in LAYERS)
    coverage = sum(layer_scores[k]["coverage"] * p["layer_weights"][k] / 100 for k in LAYERS)
    gates = []
    for g in gates_for(p, d["product"]["profile"], d["stage"]):
        submitted = d["gates"].get(g["id"], {"status": "unknown", "reason": "未提交门槛证据", "evidence_refs": []})
        # Negative primary evidence may disprove a gate before an observed trial exists.
        negative = submitted["status"] == "not_met"
        eligible = select_evidence(ev, submitted["evidence_refs"], g["id"],
                                   g["kinds"] + (["source", "counterevidence"] if negative else []),
                                   2 if negative else g["min_strength"])
        status = submitted["status"] if submitted["status"] == "unknown" or eligible else "unknown"
        gates.append({"id": g["id"], "name": g["name"], "status": status, "reason": submitted["reason"],
                      "evidence_refs": [e["id"] for e in eligible]})
    for mid in p["zero_score_blocks"]:
        m = metrics[mid]
        if m["score"] == 0:
            gates.append({"id": "KNOWN_FAILURE_" + mid, "name": m["name"] + "存在已知失败", "status": "not_met",
                          "reason": m["reason"] + "；与任何同范围met声明冲突时按未解决失败处理", "evidence_refs": m["evidence_refs"]})
    claims = []
    for c in d["claims"]:
        kinds = {"capability": ["source", "test_run", "raw_data"], "outcome": ["customer", "raw_data", "human_review"],
                 "commercial": ["transaction", "customer"]}[c["proof_kind"]]
        eligible = select_evidence(ev, c["evidence_refs"], c["id"], kinds, 2 if c["proof_kind"] == "capability" else 3)
        if obj == 'development_plan':
            # Planned capability is a hypothesis. Only original product evidence can
            # support an existing capability/outcome, never a plan's own prose.
            eligible = [e for e in eligible if c['claim_scope']=='existing' and e.get('review_object')=='product']
        counter = select_evidence(ev, c["counterevidence_refs"], c["id"])
        status = c["status"]
        if status == "supported" and (not eligible or counter):
            status = "withdrawn" if counter else "candidate"
            gates.append({"id": "CLAIM_" + c["id"], "name": "声明证据不符", "status": "not_met" if counter else "unknown",
                          "reason": c["text"], "evidence_refs": [e["id"] for e in counter]})
        claims.append({**c, "status": status, "usable_evidence_refs": [e["id"] for e in eligible]})
    if not any(c["status"] == "supported" for c in claims) and d["stage"] in ("launch", "scale"):
        gates.append({"id": "SELLING_POINT", "name": "有证据支持的购买/采用理由", "status": "unknown", "reason": "尚无可核对卖点", "evidence_refs": []})
    reviews = copy.deepcopy(d["reviews"])
    for name, r in reviews.items():
        kinds = {"human_acceptance": ["human_review"], "real_world": ["customer", "raw_data", "transaction"],
                 "engineering": ["test_run", "raw_data"], "domain": ["human_review", "raw_data", "test_run"],
                 "aesthetic": ["human_review", "customer"]}[name]
        eligible = select_evidence(ev, r["evidence_refs"], "review:" + name, kinds, 3)
        if r["status"] == "passed" and not eligible:
            r["status"] = "not_run"
            r["reason"] += "；本档案缺少适用的已核查证据"
        if r["status"] == "failed" and not select_evidence(ev, r["evidence_refs"], "review:" + name, kinds + ["source", "counterevidence"], 2):
            r["status"] = "not_run"
            r["reason"] += "；失败声明缺少适用证据，保留待核而非已知失败"
        # Required reviews cannot be waived by the submitter.
        if name in p["stages"][d["stage"]]["required_reviews"] and r["status"] != "passed":
            gates.append({"id": "REVIEW_" + name, "name": name, "status": "not_met" if r["status"] == "failed" else "unknown", "reason": r["reason"], "evidence_refs": r["evidence_refs"]})
    costs = cost_model(d, p, ev)
    plan_result = None
    if obj == 'development_plan':
        plan_gates, plan_result = assess_plan(d, p, ev, select_evidence, cost_model)
        gates.extend(plan_gates)
        if design:
            plan_result['evidence_bonus']['reference_total']=round(total+plan_result['evidence_bonus']['points'],2)
    if (d["stage"] in ("launch", "scale") or (obj == 'development_plan' and not design)) and not costs["complete"]:
        gates.append({"id": "BOM_COMPLETE", "name": "完整BOM", "status": "unknown", "reason": "成本缺项，不能给出完整成本或资源资格", "evidence_refs": []})
    cfg = p["stages"][d["stage"]]
    score_ok = total >= cfg["total_min"] and all(layer_scores[k]["score"] >= cfg["layer_min"][k] for k in LAYERS)
    if d["product"]["lifecycle"] in ("closed", "paused"):
        verdict = "STOP_EXISTING_DECISION"
    elif any(g["status"] == "not_met" for g in gates):
        verdict = "DOES_NOT_MEET"
    elif any(g["status"] == "unknown" for g in gates) or coverage < cfg["coverage_min"]:
        verdict = "NEEDS_EVIDENCE"
    elif not score_ok:
        verdict = "REWORK"
    else:
        verdict = "PLAN_ELIGIBLE_FOR_OWNER_REVIEW" if obj == 'development_plan' else "ELIGIBLE_FOR_OWNER_REVIEW"
    resource_reasons = []
    budget = d["budget"]
    if budget["status"] != "confirmed" or not select_evidence(ev, budget["evidence_refs"], "BUDGET", ["human_review"], 3):
        resource_reasons.append("尚无用户确认的预算依据")
    if any(v is None for v in budget["caps"].values()):
        resource_reasons.append("资源额度未填全")
    if not costs["complete"]:
        resource_reasons.append("BOM未完整核查")
    resource_costs = plan_result['requested_costs'] if plan_result else costs
    if plan_result and not resource_costs['complete']:
        resource_reasons.append('本次请求范围的BOM未完整核查')
    if design and plan_result['execution_readiness']['status']=='NOT_READY':
        resource_reasons.append('执行准备条件未满足：'+'；'.join(x['reason'] for x in plan_result['execution_readiness']['checks']))
    for dim, limit in budget["caps"].items():
        high = resource_costs["totals"]["high"][dim]
        if high is None:
            resource_reasons.append(f"{dim}:需求未知")
        elif limit is not None and high > limit:
            resource_reasons.append(f"{dim}:高情景需求 {high:g} 超过额度 {limit:g}")
    if verdict not in ("ELIGIBLE_FOR_OWNER_REVIEW", "PLAN_ELIGIBLE_FOR_OWNER_REVIEW"):
        resource_reasons.append("当前阶段尚未满足评审条件")
    if d["purpose"] != "live_review":
        resource_reasons.append("历史回放/合成样例不获得现实资源资格")
    sensitivity = []
    for layer in LAYERS:
        for factor in (0.8, 1.2):
            ws = {k: p["layer_weights"][k] * (factor if k == layer else 1) for k in LAYERS}
            s = sum(layer_scores[k]["score"] * ws[k] / sum(ws.values()) for k in LAYERS)
            sensitivity.append({"layer": layer, "factor": factor, "total": round(s, 2), "total_threshold_met": s >= cfg["total_min"]})
    next_experiment = d['next_experiment']
    if plan_result:
        milestone = next((m for m in plan_result['milestones'] if m['id']==plan_result['requested_milestone']), None)
        next_experiment = {'hypothesis': [a['statement'] for a in plan_result['assumptions'] if a['critical']],
            'deliverable': milestone['deliverable'] if milestone else None,
            'success': milestone['acceptance']['pass'] if milestone else None,
            'stop': plan_result['stop_conditions'] + (milestone['stop_conditions'] if milestone else []),
            'owner': milestone['owner'] if milestone else None, 'deadline': milestone['due'] if milestone else None,
            'resource_cap': budget['caps'], 'scope': budget['scope']}
    return {"harness_version": VERSION, "policy_version": p["version"], "policy_sha256": original_policy_hash,
            "dossier_sha256": digest(canonical(d)), "as_of": d["as_of"], "purpose": d["purpose"],
            "review_object": obj, "score_kind": obj,
            "score_basis": 'design_quality' if design else 'evidence_maturity',
            "scorecards": {"product": round(total,2) if obj=='product' else None, "development_plan": round(total,2) if obj=='development_plan' else None},
            "decision_scope": 'milestone:'+str(d['plan']['requested_milestone']) if plan_result else 'product:'+d['stage'],
            "plan": plan_result,
            "product": d["product"], "stage": d["stage"], "verdict": verdict,
            "score": round(total, 2), "ceiling": round(ceiling, 2), "coverage": round(coverage, 2),
            "layers": layer_scores, "metrics": metrics, "gates": gates, "reviews": reviews, "claims": claims,
            "bom": d['bom'],
            "costs": costs, "resource_status": "BLOCKED" if resource_reasons else "WITHIN_CAPS_PENDING_OWNER_DECISION",
            "resource_reasons": resource_reasons, "evidence_checks": ev, "sensitivity": sensitivity,
            "next_experiment": next_experiment, "calibration": p["calibration"],
            "limits": [("方案分衡量设计质量；原始PRD可支持0—4分，实证成熟度另列。覆盖率只表示评分有可回查材料，不是验证完成率。" if design else "评分为试行证据下限，未知未被判为产品失败；上界不是预测或置信区间。"),
                       "程序校验引用完整性和声明关系，不能独立证明语义、真实性或市场效果。",
                       "填写者可伪造声明；需要有出处的评议记录与抽查，本版没有身份签名或权限服务器。",
                       "质量资格不构成上线、拨款、联系他人或消耗关系资源的授权。"]}


def render_markdown(r):
    title = '开发方案' if r['review_object']=='development_plan' else '产品'
    design = r.get('score_basis') == 'design_quality'
    label = '方案设计质量分' if design else '证据约束分'
    lines = [f"# {r['product']['name']} · {title}三层评审", "", f"版本：{r['product']['version']}；阶段：{r['stage']}；截至：{r['as_of']}；性质：{r['purpose']}", "",
             f"**结论：{r['verdict']}**；资源：{r['resource_status']}", "",
             f"分数类型：{title}；决定范围：{r['decision_scope']}。方案分与产品分分别记录，不合并或直接排名。", "",
             f"{label} **{r['score']}/100**；未评分项补齐上界 {r['ceiling']}；评分材料覆盖 {r['coverage']}%。参数版本 {r['policy_version']}，{r['calibration']}。", "",
             ("PRD原文可充分支持高设计分；实际试用和市场效果单列，未实施不扣设计分。" if design else "分数用于比较当前证据支持的程度；缺证不等于产品没有价值。"), "",
             "| 层 | 分数下限 | 未知补齐上界 | 覆盖 |", "|---|---:|---:|---:|"]
    for layer, v in r["layers"].items():
        lines.append(f"| {layer} | {v['score']} | {v['ceiling']} | {v['coverage']}% |")
    if design:
        plan=r['plan']
        bonus=plan['evidence_bonus']
        lines += ['', f"**设计质量 {r['score']}/100 ＋ 关键假设证据加分 {bonus['points']}/{bonus['max_points']}**；附加参考总分 {bonus['reference_total']}。资格阈值只看设计分；缺证仅为+0。", '',
                  '证据加分明细：', '', '```json',json.dumps(bonus,ensure_ascii=False,indent=2),'```']
        lines += ['', '## 实证与执行准备（不计入设计分）', '',
                  f"实际验证：{plan['validation_maturity']['status']}；执行准备：{plan['execution_readiness']['status']}；资源：{r['resource_status']}。", '',
                  '```json', json.dumps({'validation_maturity':plan['validation_maturity'], 'execution_readiness':plan['execution_readiness'],
                                        'actual_reviews':r['reviews']},ensure_ascii=False,indent=2), '```', '']
    for layer, v in r["layers"].items():
        lines += ["", f"## {layer}", "", f"价值：{v['value']}", "", f"问题：{v['problems']}", "", f"下一动作：{v['next_action']}"]
    lines += ["", "## 卖点与证据", ""]
    for c in r["claims"]:
        lines += [f"- [{c['status']}] {c['text']}。边界：{c['boundary']}。证据：{', '.join(c['usable_evidence_refs']) or '缺失'}"]
    lines += ["", "## 逐项评分", "", "| 指标 | 提议→约束后 | 理由 | 引用 |", "|---|---|---|---|"]
    for m in r["metrics"].values():
        lines.append(f"| {m['id']} {m['name']} | {m['proposed_score']} → {m['score']} | {m['reason'].replace('|','/')} | {', '.join(m['evidence_refs'])} |")
    lines += ["", "## 门槛", "", "| 门槛 | 状态 | 原因 |", "|---|---|---|"]
    for g in r["gates"]:
        lines.append(f"| {g['id']} {g['name']} | {g['status']} | {g['reason'].replace('|','/')} |")
    lines += ["", "## BOM 与现实资源", "", "窗口内合计；low/base/high为成本和用量情景，另有高成本×低销量压力情景。", "",
              "| 资源 | low | base | high |", "|---|---:|---:|---:|"]
    for dim in r["costs"]["totals"]["base"]:
        vals = [r["costs"]["totals"][s][dim] for s in SCENARIOS]
        lines.append("| " + dim + " | " + " | ".join("待补" if v is None else f"{v:,.2f}" for v in vals) + " |")
    if r['plan']:
        lines += ['', '### 四阶段资源汇总', '', '每格为low/base/high；未知保留未知。阶段总账不代表本次获批额度。', '',
                  '| 阶段 | 现金CNY | 本人小时 | 团队小时 | token | 关系次数 |', '|---|---|---|---|---|---|']
        for phase,phase_result in r['plan']['phases'].items():
            vals=['/'.join('未知' if phase_result['totals'][s][dim] is None else f"{phase_result['totals'][s][dim]:g}" for s in SCENARIOS) for dim in ('cash','owner_hours','team_hours','tokens','relationship_uses')]
            lines.append('| '+phase+' | '+' | '.join(vals)+' |')
        lines += ['', '### BOM组成与估计依据', '', '| 行/阶段 | 类别与基准 | 数量low/base/high | 单位资源low/base/high | 状态与依据 |', '|---|---|---|---|---|']
        for line in r['bom']['lines']:
            qty='/'.join('未知' if line['quantity'][s] is None else str(line['quantity'][s]) for s in SCENARIOS)
            rates='；'.join(dim+': '+ '/'.join('未知' if rr[s] is None else str(rr[s]) for s in SCENARIOS) for dim,rr in line['per_quantity'].items())
            lines.append(f"| {line['id']} / {line['phase']} | {line['category']} / {line['basis']} / {line['unit']} | {qty} | {rates} | {line['status']}；{line['reason'].replace('|','/')}；{','.join(line['evidence_refs'])} |")
    gap_summary='；'.join(r['costs']['gaps'])
    if r['plan'] and r['costs']['gaps']:
        affected=sorted({x.split(':')[1] for x in r['costs']['gaps'] if x.startswith('BOM:')})
        gap_summary=f"共{len(r['costs']['gaps'])}条机器缺项，涉及{len(affected)}个成本行/类别；先补："+'、'.join(affected[:8])+('等' if len(affected)>8 else '')+'。逐行组成和未知维度见上表，全部细项见result.json的costs.gaps。'
    lines += ["", r["costs"]["note"], "", f"压力情景现金余额：{r['costs']['pressure_cash_balance']}", "",
              "成本缺项：" + (gap_summary or "无结构缺项，仍须核对估计的现实准确性"), "",
              "资源限制：" + ("；".join(r["resource_reasons"]) or "额度内，待用户最终决定"), "",
              "## 下一最小试验", "", json.dumps(r["next_experiment"], ensure_ascii=False, indent=2), ""]
    if r['plan']:
        plan=r['plan']
        lines += ["## 方案里程碑与停止条件", "", f"方案版本：{plan['version']}；本次只评请求里程碑：{plan['requested_milestone']}。通过不代表功能已实现、产品可上线或资源获批。", "",
                  "| 里程碑 | 负责人/日期 | 交付与验收 | 前置/成本行 | 停止条件 |", "|---|---|---|---|---|"]
        for m in plan['milestones']:
            acceptance='；'.join(k+': '+str(v) for k,v in m['acceptance'].items())
            lines.append(f"| {m['id']} {m['title']} | {m['owner']} / {m['due']} | {m['deliverable']}；{acceptance} | {m['depends_on']} / {m['bom_line_ids']} | {'；'.join(m['stop_conditions'])} |")
        lines += ["", "全局停止线："+'；'.join(plan['stop_conditions']), "", "### 本次里程碑资源需求", "",
                  "以下为估计需求，不是额度；开发/运营/退出总账仍单列保留。", "", "```json",json.dumps(plan['requested_costs']['totals'],ensure_ascii=False,indent=2),"```", "",
                  "### 假设与依赖", "", "```json",json.dumps({'assumptions':plan['assumptions'],'dependencies':plan['dependencies'],'phases':plan['phases']},ensure_ascii=False,indent=2),"```", ""]
    lines += [
              "## 证据登记", "", "| ID | 状态 | 来源定位 | 本地快照 |", "|---|---|---|---|"]
    for eid, e in r["evidence_checks"].items():
        lines.append(f"| {eid} | {'可用' if e['usable'] else '; '.join(e['errors'])} | {e['locator']} | {e['path']} |")
    lines += ["", "## 限制", ""] + ["- " + x for x in r["limits"]]
    return "\n".join(lines) + "\n"


def export_report(d, p, out, root=ROOT):
    started = datetime.now(timezone.utc).isoformat()
    r = evaluate(d, p, root)
    out = Path(out)
    require(not out.exists(), "输出目录已存在；请用新运行目录，历史报告不可覆盖")
    out.mkdir(parents=True)
    implementation = out / "implementation"
    implementation.mkdir()
    for name in ("harness.py", "templates.py", "protocol_adapter.py", "plan_review.py"):
        (implementation / name).write_bytes((ROOT / name).read_bytes())
    write_json(out / "dossier.json", d)
    replay = copy.deepcopy(d)
    source_locations = {}
    for e in replay["evidence"]:
        source = (Path(root) / e["path"]).resolve()
        if source.is_relative_to(Path(root).resolve()) and source.is_file():
            raw = source.read_bytes()
            relative = "source-snapshots/" + digest(raw) + ".txt"
            target = out / relative
            target.parent.mkdir(exist_ok=True)
            if not target.exists():
                target.write_bytes(raw)
            e["path"] = relative
            source_locations[e["id"]] = relative
        else:
            # An unavailable source must never bind to a newly generated report file.
            relative = "missing-source/" + digest(canonical({"id": e["id"], "path": e["path"]})) + ".missing"
            e["path"] = relative
            source_locations[e["id"]] = relative
    write_json(out / "replay-dossier.json", replay)
    write_json(out / "policy.json", p)
    write_json(out / "result.json", r)
    (out / "report.md").write_text(render_markdown(r), encoding="utf-8")
    ended = datetime.now(timezone.utc).isoformat()
    receipt = {"execution_status": "succeeded", "started_at": started, "ended_at": ended,
               "harness_version": VERSION, "harness_sha256": digest(Path(__file__).read_bytes()),
               "dossier_sha256": r["dossier_sha256"], "policy_sha256": r["policy_sha256"],
               "scope": "本地确定性评分与成本核算；未运行被评产品，未调用外部模型", "source_locations": source_locations,
               "artifacts": {str(f.relative_to(out)).replace('\\', '/'): digest(f.read_bytes()) for f in out.rglob('*') if f.is_file()}}
    write_json(out / "receipt.json", receipt)
    from protocol_adapter import export_bundle
    write_json(out / "task-bundle.json", export_bundle(d, p, r, receipt, out))
    return r


def calibrate(rows, p):
    require(isinstance(rows, list), "校准输入须为数组")
    errors, agreement, false_release = [], [], 0
    groups = {}
    frozen_labels = {}
    variants = {(row.get("model"), row.get("prompt_version")) for row in rows}
    require(len(variants) <= 1, "不同模型/提示版本需分别校准，不得混合统计")
    score_kinds = {row.get('score_kind','product') for row in rows}
    require(score_kinds <= {'product','development_plan'} and len(score_kinds)<=1, '方案与产品必须分别校准')
    for row in rows:
        for k in ("case_id", "trial_id", "model", "prompt_version", "policy_version", "human_label_ref"):
            require(isinstance(row.get(k), str) and row[k], f"校准缺 {k}")
        require(row["policy_version"] == p["version"], "校准不得混合规则版本")
        require(row["human_gate"] in ("pass", "fail") and row["ai_gate"] in ("pass", "fail"), "校准标签非法")
        for x in (row["human_score"], row["ai_score"]):
            require(number(x) and 0 <= x <= 4, "校准指标分必须0..4")
        label = (row["human_gate"], row["human_score"], row["human_label_ref"])
        require(row["case_id"] not in frozen_labels or frozen_labels[row["case_id"]] == label,
                "同一案例的人工标签或标签引用冲突；需先裁决并冻结")
        frozen_labels[row["case_id"]] = label
        key = (row["case_id"], row["trial_id"])
        require(key not in groups, "重复校准试次")
        groups[key] = row
        errors.append(abs(row["human_score"] - row["ai_score"]))
        agreement.append(row["human_gate"] == row["ai_gate"])
        false_release += row["human_gate"] == "fail" and row["ai_gate"] == "pass"
    unique = {r["case_id"] for r in rows}
    reps = min((sum(r["case_id"] == c for r in rows) for c in unique), default=0)
    cfg = p["calibration_requirements"]
    mae = sum(errors) / len(errors) if errors else None
    agree = sum(agreement) / len(agreement) if agreement else None
    enough = len(unique) >= cfg["min_human_cases"] and reps >= cfg["min_repeats"]
    passed = enough and mae <= cfg["max_mae"] and agree >= cfg["min_gate_agreement"] and false_release <= cfg["max_false_release"]
    return {"score_kind": next(iter(score_kinds), None), "cases": len(unique), "trials": len(rows), "minimum_repeats": reps, "mae": mae,
            "gate_agreement": agree, "false_release_count": false_release,
            "status": "CANDIDATE_FOR_HUMAN_AUDIT" if passed else "NOT_CALIBRATED",
            "limits": "程序仅核算已提交的独立人工标签；未验证标签来源、盲法或代表性；不自动调整参数或批准模型。"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy", type=Path, default=ROOT / "policy.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init")
    init.add_argument("--id", required=True)
    init.add_argument("--name", required=True)
    init.add_argument("--profile", required=True)
    init.add_argument("--review-object", choices=("product", "development_plan"), default="product")
    init.add_argument("--as-of", required=True)
    init.add_argument("--out", type=Path, required=True)
    for command in ("validate", "review"):
        cp = sub.add_parser(command)
        cp.add_argument("--input", type=Path, required=True)
        cp.add_argument("--evidence-root", type=Path, default=ROOT)
        if command == "review":
            cp.add_argument("--out", type=Path, required=True)
    cp = sub.add_parser("calibrate")
    cp.add_argument("--input", type=Path, required=True)
    cp.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    try:
        p = validate_policy(read_json(args.policy))
        if args.cmd == "init":
            from templates import new_dossier
            d = new_dossier(p, args.id, args.name, args.profile, args.as_of, review_object=args.review_object)
            require(not args.out.exists(), "输出文件已存在")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.out, d)
            print("已创建待补档案；未知项保留null。")
        elif args.cmd == "calibrate":
            require(not args.out.exists(), "校准输出已存在")
            r = calibrate(read_json(args.input), p)
            write_json(args.out, r)
            print(r["status"])
        else:
            d = read_json(args.input)
            if args.cmd == "validate":
                validate(d, p)
                print("结构通过；不表示产品质量、证据真实性或预算通过。")
            else:
                r = export_report(d, p, args.out, args.evidence_root)
                print(json.dumps({k: r[k] for k in ("verdict", "score", "coverage", "resource_status")}, ensure_ascii=False))
    except (Invalid, KeyError, TypeError, ValueError, OSError) as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

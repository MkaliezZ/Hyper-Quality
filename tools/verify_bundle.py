import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hpvalidator", ROOT / "vendor/hyper-protocol/tools/validate_bundle.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
errors = module.validate_bundle(data)
print(json.dumps({"valid": not errors, "errors": errors, "scope": "结构与声明一致性，不核实外部真实性/权限/语义"}, ensure_ascii=False))
raise SystemExit(1 if errors else 0)

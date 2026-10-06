"""Cloud configuration: Checkov on TerraGoat (Terraform, AWS/Azure/GCP), CfnGoat (CloudFormation) and ingress-nginx
(a real Helm chart), against ours on the same copies (benchmark section 20). The three live in the extended cache
(`~/.cache/aix/extended/<name>-<sha>`, cloned by hand, not in projects.json) and Checkov needs `helm` on PATH
(BENCH_DIR/helm-bin). Prints, per project, ours' infra findings by title and Checkov's failed checks by id. Not part of
the test suite. Usage: BENCH_DIR=... python3 tests/benchmark/cloudinfra.py"""
import json, os, sys, collections
from pathlib import Path
sys.path.insert(0, "tests/benchmark"); import engines, infrastyle
S = Path(os.environ["BENCH_DIR"])
os.environ["PATH"] = str(S) + os.pathsep + os.environ["PATH"]   # helm-bin -> checkov needs `helm`
(S / "helm").exists() or (S / "helm").symlink_to(S / "helm-bin")
for name, frameworks in (("terragoat", "terraform,cloudformation"), ("cfngoat", "cloudformation"), ("ingress-nginx", "helm,kubernetes")):
    tmp = engines.prepare(dict(name=name))
    ours = infrastyle.run_ours(tmp)
    out, secs = engines.timed([str(S / "venv" / "bin" / "checkov"), "-d", ".", "--framework", frameworks, "-o", "json", "--quiet", "--compact", "--skip-path", ".aix", "--skip-path", "node_modules"], tmp, 3600)
    try:
        data = json.loads(out)
    except ValueError:
        print(name, "checkov gave no JSON:", out[-300:]); continue
    fails = [(r.get("check_type"), f["check_id"], f["file_path"].lstrip("/"), int(f["file_line_range"][0]), str(f.get("check_name", ""))[:70]) for r in (data if isinstance(data, list) else [data]) for f in r.get("results", {}).get("failed_checks", [])]
    by_id = collections.Counter((t, c, n) for t, c, _, _, n in fails)
    print(f"== {name}: ours {len(ours)} infra findings, Checkov {len(fails)} failed checks in {secs} s; ours by title: {dict(collections.Counter(o[3] for o in ours).most_common(6))}")
    for (t, c, n), k in by_id.most_common(40):
        print(f"   {k:3d} {t:15s} {c:16s} {n}")
    json.dump(dict(ours=ours, checkov=fails), open(S.parent / f"cloudinfra-{name}.json", "w"))

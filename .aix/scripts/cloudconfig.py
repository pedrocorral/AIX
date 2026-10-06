"""Leaf: the cloud configuration a project carries that `aix code security` does not read: Terraform, CloudFormation
and Helm (benchmark section 20: Checkov reports hundreds of findings on such files, ours none). The report counts
them and names the command that reads them, so the scan is never silent about what it looked away from."""
import re
from pathlib import Path

from codefiles import ROOT, SKIP

CFN = re.compile(r"^AWSTemplateFormatVersion\s*:|^Resources\s*:\s*\n(?:.*\n)*?\s+Type\s*:\s*['\"]?AWS::", re.M)
KINDS = [("Terraform file", "Terraform files", "checkov -d . --framework terraform"), ("CloudFormation template", "CloudFormation templates", "checkov -d . --framework cloudformation"),
         ("Helm chart", "Helm charts", "checkov -d . --framework helm`, needs `helm")]


def _files(root: Path):
    for f in root.rglob("*"):
        if f.is_file() and not any(s in f.relative_to(root).parts for s in SKIP):
            yield f


def counts(root: Path = ROOT) -> list:
    """[terraform, cloudformation, helm] file counts under the project."""
    tf = cfn = helm = 0
    for f in _files(root):
        if f.suffix in (".tf", ".tfvars"):
            tf += 1
        elif f.name == "Chart.yaml":
            helm += 1
        elif f.suffix in (".yaml", ".yml", ".json", ".template") and f.stat().st_size < 2_000_000 and CFN.search(f.read_text(encoding="utf-8", errors="replace")):
            cfn += 1
    return [tf, cfn, helm]


def unread_lines(root: Path = ROOT) -> list:
    """The report lines for what the scan does not read, none when the project carries none of it."""
    parts = [f"{n} {plural if n > 1 else singular} (run `{cmd}`)" for n, (singular, plural, cmd) in zip(counts(root), KINDS) if n]
    return [f"  not read by this scan: {'; '.join(parts)}"] if parts else []

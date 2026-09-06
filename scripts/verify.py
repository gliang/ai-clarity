#!/usr/bin/env python3
"""Run offline project checks and keep real output in ignored local storage."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / ".local" / "verification"
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    files = [ROOT / "README.md", ROOT / "README.zh-CN.md", ROOT / "AGENTS.md"]
    for name in ("skills", "adapters", "evals", "docs", "tests", "scripts"):
        files.extend(p for p in (ROOT / name).rglob("*") if p.is_file() and p.suffix in (".md", ".py", ".json"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        try:
            if path.suffix == ".py":
                ast.parse(text, filename=str(path))
            elif path.suffix == ".json":
                json.loads(text)
            elif path.suffix == ".md":
                for target in re.findall(r"\]\(([^\s)]+)\)", text):
                    if "://" in target or target.startswith(("#", "mailto:")):
                        continue
                    if not (path.parent / target.split("#", 1)[0]).exists():
                        errors.append(str(path.relative_to(ROOT)) + ": missing link " + target)
        except (ValueError, SyntaxError) as error:
            errors.append(str(path.relative_to(ROOT)) + ": " + str(error))

    skill = (ROOT / "skills/ai-clarity/SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\n") or "\n---\n" not in skill[4:]:
        errors.append("Invalid skill frontmatter boundary")
    else:
        frontmatter = skill.split("---", 2)[1]
        for key in ("name", "description", "version", "author", "license", "platforms"):
            if not re.search(r"^" + key + ": .+", frontmatter, re.M):
                errors.append("Missing frontmatter field " + key)
        description = re.search(r"^description: (.+)$", frontmatter, re.M)
        if description and (len(description[1]) > 60 or not description[1].endswith(".")):
            errors.append("Skill description must be <=60 characters and end in a period")

    run = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    log = run.stdout + run.stderr
    (output / "unittest.log").write_text(log, encoding="utf-8")
    print(log, end="")
    summary = {
        "python": sys.version,
        "test_command": "python3 -m unittest discover -s tests -v",
        "test_exit_code": run.returncode,
        "test_executions": int(re.search(r"Ran (\d+) tests?", log)[1]) if re.search(r"Ran (\d+) tests?", log) else None,
        "static_files_checked": len(files),
        "static_errors": errors,
        "limits": ["No live-host, browser, semantic, or human-comprehension validation"],
    }
    (output / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if errors or run.returncode else 0


if __name__ == "__main__":
    sys.exit(main())

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

LEVEL_MAP = {
    "CRITICAL": "error",
    "HIGH": "error",
    "MEDIUM": "warning",
    "LOW": "note",
}

SECURITY_SEVERITY_MAP = {
    "CRITICAL": "9.5",
    "HIGH": "7.5",
    "MEDIUM": "5.0",
    "LOW": "3.0",
}


def findings_to_sarif(findings: list, repo: str = "") -> dict:
    rules = {}
    results = []

    for finding in findings:
        rule_id = finding.get("category", "unknown").lower().replace(" ", "_")
        severity = (finding.get("severity") or "MEDIUM").upper()
        file_path = finding.get("file", "unknown")
        line = int(finding.get("line") or 1)
        description = finding.get("description", "")
        recommendation = finding.get("recommendation", "")
        exploit = finding.get("exploit_scenario", "")

        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": finding.get("category", rule_id),
                "shortDescription": {"text": finding.get("category", rule_id)},
                "fullDescription": {"text": description},
                "defaultConfiguration": {
                    "level": LEVEL_MAP.get(severity, "warning")
                },
                "properties": {
                    "security-severity": SECURITY_SEVERITY_MAP.get(severity, "5.0"),
                    "tags": ["security"],
                },
            }

        message_parts = [description]
        if exploit:
            message_parts.append(f"Exploit scenario: {exploit}")
        if recommendation:
            message_parts.append(f"Recommendation: {recommendation}")

        results.append({
            "ruleId": rule_id,
            "level": LEVEL_MAP.get(severity, "warning"),
            "message": {"text": "\n\n".join(message_parts)},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": file_path,
                        "uriBaseId": "%SRCROOT%",
                    },
                    "region": {"startLine": max(1, line)},
                }
            }],
            "properties": {"severity": severity},
        })

    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    return {
        "$schema": (
            "https://raw.githubusercontent.com/oasis-tcs/sarif-spec"
            "/master/Schemata/sarif-schema-2.1.0.json"
        ),
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "claude-code-security-review",
                    "version": "1.0.0",
                    "informationUri": (
                        "https://github.com/anthropics/claude-code-security-review"
                    ),
                    "rules": list(rules.values()),
                }
            },
            "results": results,
            "automationDetails": {
                "id": f"claude-security/{date_str}",
            },
        }],
    }


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <results.json> <output.sarif>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    with input_path.open(encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        findings = data
        repo = ""
    else:
        findings = data.get("findings", [])
        repo = data.get("repo", "")

    sarif = findings_to_sarif(findings, repo)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(sarif, f, indent=2)

    print(f"Converted {len(findings)} findings -> {output_path}")


if __name__ == "__main__":
    main()

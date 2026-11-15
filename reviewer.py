#!/usr/bin/env python3
"""Deterministic quality checks for AI-generated Amharic and Afaan Oromo."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


LANGUAGES = {
    "am": "Amharic",
    "om": "Afaan Oromo",
}
ETHIOPIC = re.compile(r"[\u1200-\u137f]")
LATIN = re.compile(r"[A-Za-z]")
PLACEHOLDER = re.compile(
    r"\{\{[^{}]+\}\}|\[[A-Z][A-Z0-9_ -]{1,}\]|<[^>]+>|\b(?:TODO|TBD|FIXME)\b",
    re.IGNORECASE,
)
REPEATED_SPACE = re.compile(r"[ \t]{2,}")
SPACE_BEFORE_PUNCTUATION = re.compile(r"[ \t]+[,.!?;:]")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    line: int = 1
    column: int = 1


def _position(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    last_newline = text.rfind("\n", 0, index)
    return line, index - last_newline


def _finding(
    text: str, severity: str, code: str, message: str, index: int = 0
) -> Finding:
    line, column = _position(text, index)
    return Finding(severity, code, message, line, column)


def review(text: str, language: str) -> dict:
    """Review text and return a JSON-serializable report."""
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")

    findings: list[Finding] = []
    stripped = text.strip()
    if not stripped:
        findings.append(
            _finding(text, "error", "empty_text", "Text is empty.")
        )
    else:
        if language == "am" and not ETHIOPIC.search(text):
            findings.append(
                _finding(
                    text,
                    "error",
                    "missing_target_script",
                    "No Ethiopic-script characters were found; verify the text is Amharic.",
                )
            )
        if language == "om" and not LATIN.search(text):
            findings.append(
                _finding(
                    text,
                    "error",
                    "missing_target_script",
                    "No Latin-script characters were found; verify the text is Afaan Oromo.",
                )
            )

    for match in PLACEHOLDER.finditer(text):
        findings.append(
            _finding(
                text,
                "error",
                "placeholder",
                f"Unresolved placeholder: {match.group(0)!r}.",
                match.start(),
            )
        )
    for pattern, code, message in (
        (
            REPEATED_SPACE,
            "repeated_whitespace",
            "Repeated spaces or tabs should be reduced to one space.",
        ),
        (
            SPACE_BEFORE_PUNCTUATION,
            "space_before_punctuation",
            "Remove the space before punctuation.",
        ),
    ):
        for match in pattern.finditer(text):
            findings.append(
                _finding(text, "warning", code, message, match.start())
            )

    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    score = max(0, 100 - (errors * 25) - (warnings * 5))
    return {
        "language": language,
        "language_name": LANGUAGES[language],
        "score": score,
        "passed": errors == 0,
        "findings": [asdict(item) for item in findings],
    }


def _read_input(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.file is not None:
        return Path(args.file).read_text(encoding="utf-8")
    raise ValueError("Provide exactly one of --text or --file.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review AI-generated Amharic and Afaan Oromo text."
    )
    parser.add_argument(
        "--language", choices=sorted(LANGUAGES), required=True,
        help="Target language: am (Amharic) or om (Afaan Oromo).",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Text to review.")
    source.add_argument("--file", help="UTF-8 file to review.")
    parser.add_argument(
        "--json", action="store_true", dest="as_json",
        help="Print a machine-readable JSON report.",
    )
    return parser


def _render(report: dict) -> str:
    lines = [
        f"{report['language_name']} review: "
        f"{'PASS' if report['passed'] else 'FAIL'} (score {report['score']}/100)"
    ]
    if not report["findings"]:
        return "\n".join(lines + ["No findings."])
    for finding in report["findings"]:
        lines.append(
            f"- {finding['severity'].upper()} {finding['code']} "
            f"(line {finding['line']}, column {finding['column']}): "
            f"{finding['message']}"
        )
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = review(_read_input(args), args.language)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.as_json else _render(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

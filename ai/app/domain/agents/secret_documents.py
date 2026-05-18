from __future__ import annotations

from dataclasses import dataclass
import re


SECRETS_DOCUMENT_KEY = "SECRETS.md"
MASKED_SECRET_VALUE = "<stored>"

_SECTION_PATTERN = re.compile(r"^##\s+(?P<section>.+?)\s*$")
_ASSIGNMENT_PATTERN = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)$")


@dataclass(frozen=True, slots=True)
class SecretAssignment:
    section: str
    key: str
    value: str


def is_secrets_document(document_key: str) -> bool:
    return document_key.strip().lower() == SECRETS_DOCUMENT_KEY.lower()


def sanitize_secret_document(content: str) -> tuple[str, list[SecretAssignment]]:
    current_section = "default"
    assignments: list[SecretAssignment] = []
    sanitized_lines: list[str] = []

    for line in content.splitlines(keepends=True):
        line_body = line.rstrip("\r\n")
        newline = line[len(line_body) :]
        section_match = _SECTION_PATTERN.match(line_body.strip())
        if section_match:
            current_section = section_match.group("section").strip()
            sanitized_lines.append(line)
            continue

        assignment_match = _ASSIGNMENT_PATTERN.match(line_body)
        if assignment_match is None:
            sanitized_lines.append(line)
            continue

        key = assignment_match.group("key")
        value = assignment_match.group("value").strip()
        if not value or value == MASKED_SECRET_VALUE:
            sanitized_lines.append(line)
            continue

        assignments.append(SecretAssignment(section=current_section, key=key, value=value))
        sanitized_lines.append(f"{key}={MASKED_SECRET_VALUE}{newline}")

    return "".join(sanitized_lines), assignments

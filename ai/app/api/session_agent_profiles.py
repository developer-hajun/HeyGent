from __future__ import annotations

from typing import Any


def agent_profile_prompt_payload(profile: dict[str, Any], *, skill_registry: Any | None = None) -> dict[str, Any]:
    payload = {
        "profileId": profile.get("profile_id"),
        "profileKey": profile.get("profile_key"),
        "agentType": profile.get("agent_type"),
        "templateKey": profile.get("template_key"),
        "configSnapshot": profile.get("config_snapshot") or {},
    }
    skill_descriptions = _profile_skill_descriptions(payload, skill_registry=skill_registry)
    if skill_descriptions:
        payload["skillDescriptions"] = skill_descriptions
    return payload


def instruction_bundle_prompt_payload(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "bundleId": bundle.get("bundle_id"),
        "entryDocumentKey": bundle.get("entry_document_key") or "AGENTS.md",
        "documents": [
            {
                "documentKey": document.get("document_key") or document.get("documentKey"),
                "displayName": document.get("display_name") or document.get("displayName"),
                "content": document.get("content") or "",
            }
            for document in list(bundle.get("documents") or [])
            if isinstance(document, dict)
        ],
    }


def profile_model(profile: dict[str, Any] | None) -> str | None:
    if profile is None:
        return None
    config = profile.get("config_snapshot") if isinstance(profile.get("config_snapshot"), dict) else {}
    value = config.get("model") or profile.get("model_name")
    text = str(value or "").strip()
    return text or None


def _profile_skill_descriptions(profile_payload: dict[str, Any], *, skill_registry: Any | None) -> list[dict[str, str]]:
    skills = getattr(skill_registry, "_skills", {}) if skill_registry is not None else {}
    if not isinstance(skills, dict):
        return []
    config = profile_payload.get("configSnapshot")
    if not isinstance(config, dict):
        return []
    descriptions: list[dict[str, str]] = []
    for skill_name in [str(skill).strip() for skill in list(config.get("skills") or []) if str(skill).strip()]:
        skill = skills.get(skill_name)
        if not isinstance(skill, dict):
            continue
        descriptions.append(
            {
                "name": skill_name,
                "description": str(skill.get("description") or "").strip(),
                "usage": _skill_usage_excerpt(str(skill.get("body") or "")),
            }
        )
    return descriptions


def _skill_usage_excerpt(body: str) -> str:
    if not body:
        return ""
    marker = "## When to use"
    start = body.find(marker)
    if start < 0:
        return ""
    section = body[start + len(marker) :]
    next_heading = section.find("\n## ")
    if next_heading >= 0:
        section = section[:next_heading]
    lines = [line.strip(" -\t") for line in section.splitlines()]
    return " / ".join(line for line in lines if line)[:400].strip()

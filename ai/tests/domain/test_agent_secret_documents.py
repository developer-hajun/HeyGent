from app.domain.agents.secret_documents import (
    MASKED_SECRET_VALUE,
    sanitize_secret_document,
)


def test_sanitize_secret_document_masks_raw_values_and_returns_assignments():
    content = """# SECRETS

## srt-booking

KSKILL_SRT_ID=my-srt-id
KSKILL_SRT_PASSWORD=my-srt-password
"""

    sanitized, assignments = sanitize_secret_document(content)

    assert "my-srt-id" not in sanitized
    assert "my-srt-password" not in sanitized
    assert f"KSKILL_SRT_ID={MASKED_SECRET_VALUE}" in sanitized
    assert f"KSKILL_SRT_PASSWORD={MASKED_SECRET_VALUE}" in sanitized
    assert [(item.section, item.key, item.value) for item in assignments] == [
        ("srt-booking", "KSKILL_SRT_ID", "my-srt-id"),
        ("srt-booking", "KSKILL_SRT_PASSWORD", "my-srt-password"),
    ]


def test_sanitize_secret_document_keeps_existing_masked_values_without_rewriting_secret():
    content = """## srt-booking
KSKILL_SRT_ID=<stored>
KSKILL_SRT_PASSWORD=
"""

    sanitized, assignments = sanitize_secret_document(content)

    assert sanitized == content
    assert assignments == []

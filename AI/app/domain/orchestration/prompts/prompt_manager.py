from __future__ import annotations


class PromptManager:
    """capability 가 직접 문자열을 조립하지 않게 프롬프트 구성을 모은다."""

    def __init__(self, skill_prompt_builder) -> None:
        self.skill_prompt_builder = skill_prompt_builder

    def build_model_prompt(self, *, input_payload: dict) -> str:
        base_prompt = str(input_payload.get("prompt", "")).strip() or "안녕하세요. 현재 연결 상태를 짧게 요약해 주세요."
        return self._merge_skill_context(base_prompt=base_prompt, input_payload=input_payload)

    def build_notion_page_summary_prompt(self, *, input_payload: dict) -> str:
        title = str(input_payload.get("title", "Untitled")).strip() or "Untitled"
        base_prompt = f"Notion page created: {title}"
        return self._merge_skill_context(base_prompt=base_prompt, input_payload=input_payload)

    def build_notion_database_summary_prompt(self, *, input_payload: dict) -> str:
        database_id = str(input_payload.get("database_id", "local-database")).strip() or "local-database"
        base_prompt = f"Append notion database item: {database_id}"
        return self._merge_skill_context(base_prompt=base_prompt, input_payload=input_payload)

    def _merge_skill_context(self, *, base_prompt: str, input_payload: dict) -> str:
        skill_context = self.skill_prompt_builder.build(input_payload=input_payload)
        if not skill_context:
            return base_prompt
        return f"{skill_context}\n\n{base_prompt}"

# Skills Assets

이 디렉터리는 실행 코드가 아니라 agent prompt 에 주입할 skill 자산 저장소다.

- 각 skill 은 하위 디렉터리에 `SKILL.md`를 둔다.
- loader 는 `domain/orchestration/prompts/skill_prompt.py`에서 이 디렉터리를 읽는다.
- Hermes 레포의 skill 자산을 이후 그대로 이 구조에 옮길 수 있다.

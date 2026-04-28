from __future__ import annotations

from pathlib import Path
from typing import Sequence
import importlib.metadata
import re
import subprocess
import sys

# 이 파일은 app/cli/launcher/dependencies.py 아래에 있으므로,
# editable install 과 pyproject.toml 을 찾으려면 ai 프로젝트 루트까지 올라가야 한다.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def parse_version(value: str) -> tuple[int, ...]:
    """의존성 버전 비교용으로 숫자 구간만 보수적으로 비교한다."""

    parts = re.findall(r"\d+", value)
    return tuple(int(part) for part in parts) or (0,)


def compare_versions(left: str, right: str) -> int:
    left_parts = list(parse_version(left))
    right_parts = list(parse_version(right))
    width = max(len(left_parts), len(right_parts))
    left_parts.extend([0] * (width - len(left_parts)))
    right_parts.extend([0] * (width - len(right_parts)))
    if left_parts == right_parts:
        return 0
    return 1 if left_parts > right_parts else -1


def package_name_from_requirement(requirement: str) -> str:
    return re.split(r"\s*(?:\[|<=|>=|==|!=|~=|<|>|;)", requirement, maxsplit=1)[0].strip()


def specifier_satisfied(installed: str, requirement: str) -> bool:
    """pyproject 의 단순 비교 specifier 를 현재 설치 버전과 비교한다."""

    for operator, expected in re.findall(r"(<=|>=|==|<|>)\s*([A-Za-z0-9.*+!-]+)", requirement):
        if "*" in expected:
            continue
        comparison = compare_versions(installed, expected)
        if operator == ">=" and comparison < 0:
            return False
        if operator == ">" and comparison <= 0:
            return False
        if operator == "<=" and comparison > 0:
            return False
        if operator == "<" and comparison >= 0:
            return False
        if operator == "==" and comparison != 0:
            return False
    return True


def read_runtime_dependencies() -> list[str]:
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    try:
        import tomllib

        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    dependencies = pyproject.get("project", {}).get("dependencies", [])
    return [dependency for dependency in dependencies if isinstance(dependency, str)]


def installed_package_version(package_name: str) -> str | None:
    candidates = {package_name, package_name.replace("_", "-"), package_name.replace("-", "_")}
    for candidate in candidates:
        try:
            return importlib.metadata.version(candidate)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


def find_dependency_issues(dependencies: Sequence[str] | None = None) -> list[str]:
    """현재 Python 환경이 HeyGent CLI 실행에 필요한 runtime dependency 를 만족하는지 확인한다."""

    issues: list[str] = []
    for requirement in dependencies or read_runtime_dependencies():
        package_name = package_name_from_requirement(requirement)
        if not package_name:
            continue
        installed = installed_package_version(package_name)
        if installed is None:
            issues.append(f"{package_name}: 설치 안 됨 (필요: {requirement})")
            continue
        if not specifier_satisfied(installed, requirement):
            issues.append(f"{package_name}: 현재 {installed}, 필요: {requirement}")
    return issues


def confirm_dependency_update(issues: Sequence[str]) -> bool:
    print("\n[HeyGent] CLI 실행 전에 의존성 상태를 확인했어.")
    print("[HeyGent] 빠진 패키지나 버전 차이가 있어서 셸 기능이 제한될 수 있어.")
    for issue in issues:
        print(f"- {issue}")
    print("\n1. 업데이트")
    print("2. No")
    try:
        answer = input("> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n[HeyGent] 업데이트를 건너뛸게.")
        return False
    return answer in {"1", "y", "yes", "update", "u", "업데이트"}


def install_project_dependencies() -> bool:
    """현재 interpreter 에 프로젝트를 editable 모드로 재설치한다."""

    command = [sys.executable, "-m", "pip", "install", "--upgrade", "-e", str(PROJECT_ROOT)]
    print(f"[HeyGent] {' '.join(command)}")
    result = subprocess.run(command, check=False)
    if result.returncode == 0:
        print("[HeyGent] 업데이트 완료. CLI 셸로 들어갈게.")
        return True
    print("[HeyGent] 업데이트가 실패했어. 위 pip 출력을 확인해 줘.")
    return False


def ensure_cli_dependencies() -> bool:
    issues = find_dependency_issues()
    if not issues:
        return True
    if not confirm_dependency_update(issues):
        print("[HeyGent] 업데이트 없이 계속 진행할게. 일부 UI 기능은 fallback 으로 동작할 수 있어.")
        return True
    return install_project_dependencies()

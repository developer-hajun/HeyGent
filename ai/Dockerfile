# syntax=docker/dockerfile:1.6

FROM python:3.11-slim

WORKDIR /app

# 1) 의존성 메타데이터만 먼저 복사한다.
#    pyproject.toml / README.md 가 안 바뀌면 다음 RUN 단계가 캐시되어 재실행되지 않는다.
COPY pyproject.toml README.md ./

# 2) 의존성 설치는 BuildKit cache mount 로 pip 다운로드 캐시를 재사용한다.
#    `pip install -e .` (editable install) 로 설치하면 이후 코드만 바뀌어도 재설치가 필요 없다.
#    프로젝트 패키지는 다음 COPY 단계에서 들어오므로, 의존성만 먼저 받게 하기 위해 임시 app/ 디렉터리를 만들어 둔다.
RUN mkdir -p app \
    && touch app/__init__.py
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e .

# 3) 실제 애플리케이션 코드를 복사한다. 코드만 바뀌면 위 의존성 단계는 캐시 사용.
COPY app ./app

EXPOSE 8000

# 실무 사용 흐름과 맞추기 위해 uvicorn 직접 실행보다 CLI serve 를 기본 진입점으로 둔다.
CMD ["python", "-m", "app.cli", "serve"]

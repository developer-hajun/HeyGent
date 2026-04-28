FROM python:3.11-slim

WORKDIR /app

# 의존성 캐시 효율을 위해 먼저 프로젝트 메타데이터를 복사한다.
COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --no-cache-dir .

EXPOSE 8000

# 실무 사용 흐름과 맞추기 위해 uvicorn 직접 실행보다 CLI serve 를 기본 진입점으로 둔다.
CMD ["python", "-m", "app.cli", "serve"]

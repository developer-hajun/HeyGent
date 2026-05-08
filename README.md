# HeyGent

웹·모바일·IoT·갤럭시 워치로 이어지는 AI 오케스트레이션 서비스

## Docker 실행

전체 서비스를 실행합니다.

```powershell
docker compose up -d --build
```

볼륨까지 삭제하고 다시 빌드합니다.

```powershell
docker compose down -v
docker compose up -d --build
```

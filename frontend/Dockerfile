# 로컬 개발용 Vite dev 서버 컨테이너.
# 운영용 정적 빌드 + nginx 흐름은 별도 Dockerfile로 분리한다.

FROM node:20-alpine

WORKDIR /app

# 의존성 캐시 효율을 위해 lock 파일 먼저 복사한다.
# package-lock.json 이 package.json 과 어긋날 수 있어 npm install 로 자동 동기화한다.
COPY package.json package-lock.json ./
RUN npm install

# 소스 복사. dev 모드에서는 compose volume 마운트로 핫 리로드를 활용한다.
COPY . .

EXPOSE 3000

# Vite dev 서버를 0.0.0.0 바인딩으로 띄워야 컨테이너 외부에서 접속할 수 있다.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

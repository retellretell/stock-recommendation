FROM node:18-alpine

WORKDIR /app

# 의존성 설치
COPY package*.json ./
RUN npm ci

# 애플리케이션 복사
COPY . .

# 빌드
RUN npm run build

# 포트 노출
EXPOSE 3000

# 실행 명령
CMD ["npm", "start"]

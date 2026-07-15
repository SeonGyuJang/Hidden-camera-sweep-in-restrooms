# 고려대학교 세종캠퍼스 불법촬영 전수조사 점검 시스템

> **고려대학교 세종캠퍼스 제38대 총학생회 '비범' 산하 시설TF팀** 공약 사업  
> 디지털성범죄피해자지원센터 · 세종북부경찰서 협력

---

## 사업 개요

2025년 7월 16일, 고려대학교 세종캠퍼스 내 모든 건물의 화장실을 대상으로 **불법촬영 카메라 전수조사**를 시행합니다.  
총 4개 조로 나뉘어 캠퍼스 전 건물을 동시에 점검하며, 본 시스템은 점검 과정의 기록·인증·관리를 지원합니다.

### 협력 기관

| 기관 | 역할 |
|------|------|
| 세종북부경찰서 | 불법촬영 탐지 장비 지원 및 합동 점검 |
| 디지털성범죄피해자지원센터 | 피해 예방 교육 및 점검 기준 제공 |

---

## 시설TF팀 구성

### 팀 운영진

| 직책 | 성명 |
|------|------|
| 팀장 (부총학생회장) | 장선규 |
| 부팀장 (학생복지위원장) | 서홍욱 |

### 팀원

| 소속 | 직책 | 성명 |
|------|------|------|
| 총학생회 산하 인권복지위원회 | 사무재정국장 | 김다연 |
| 총학생회 산하 인권복지위원회 | 사무재정차장 | 문재준 |
| 총학생회 산하 교육복지위원회 | 기획차장 | 정승훈 |
| 총학생회 본부 기획정책위원회 | 문화기획국장 | 성지연 |
| 총학생회 본부 중앙집행위원회 | 미디어소통차장 | 김바다 |
| 총학생회 산하 인권복지위원회 | 기획국장 | 민서현 |
| 총학생회 산하 인권복지위원회 | 기획차장 | 김종욱 |
| 총학생회 산하 인권복지위원회 | 홍보국장 | 백서영 |
| 총학생회 본부 기획정책위원회 | 정책차장 | 정다연 |

### 사업 참석 인원

장선규 · 서홍욱 · 민서현 · 오미령 · 김바다 · 김종욱 · 백서영 · 문재준 · 정승훈

---

## 시스템 주요 기능

| 기능 | 설명 |
|------|------|
| **지도 기반 위치 확인** | Leaflet.js + OpenStreetMap으로 세종캠퍼스 건물 마커 표시, 클릭 시 화장실 목록 이동 |
| **조별 점검 기록** | 1~4조 구분, 점검자 이름·완료 여부 기록 |
| **카메라 촬영** | 브라우저 내장 카메라로 점검 전·후 사진 직접 촬영 (모바일 최적화) |
| **사진 파일 업로드** | 카메라 미지원 환경에서 파일로 업로드 가능 |
| **특이사항 기록** | 조치 여부·조치 내용·자유 특이사항 텍스트 입력 |
| **현황 요약** | 조별·건물별 진행률 대시보드 |
| **데이터 내보내기** | JSON 형태로 전체 점검 기록 다운로드 |

### 점검 기록 항목

```
화장실 위치 (건물 + 층)
성별 (남 / 여 / 공용)
담당 조 (1~4조)
점검자 이름
점검 전 사진
점검 후 사진
조치 여부 + 조치 내용
특이사항 메모
점검 완료 여부
```

---

## 기술 스택

- **백엔드**: Python 3.12 + Flask 3.0 + Flask-SQLAlchemy + Flask-Migrate
- **데이터베이스**: SQLite (개발) / PostgreSQL (운영, fly.io Postgres)
- **프론트엔드**: Bootstrap 5 + Leaflet.js + Vanilla JS
- **배포**: fly.io (Docker 기반)

---

## 로컬 개발 환경 설정

```bash
# 1. 저장소 클론
git clone <repo-url>
cd Hidden-camera-sweep-in-restrooms

# 2. 가상환경 생성 및 패키지 설치
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env             # 필요 시 SECRET_KEY 수정

# 4. DB 초기화 및 건물 데이터 시딩
flask db init
flask db migrate -m "init"
flask db upgrade
flask init-db

# 5. 개발 서버 실행
flask run --host=0.0.0.0 --port=5000
```

브라우저에서 `http://localhost:5000` 접속

---

## fly.io 배포

```bash
# fly CLI 설치: https://fly.io/docs/hands-on/install-flyctl/

# 1. 로그인
fly auth login

# 2. 앱 생성 (fly.toml 참조)
fly launch --no-deploy

# 3. PostgreSQL 연결
fly postgres create --name ku-sejong-db
fly postgres attach --app ku-sejong-restroom-inspection ku-sejong-db

# 4. 시크릿 설정
fly secrets set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# 5. 배포
fly deploy
```

배포 후 URL: `https://ku-sejong-restroom-inspection.fly.dev`

---

## 디렉터리 구조

```
├── app.py                  # Flask 앱 메인 (라우트·모델)
├── requirements.txt
├── Dockerfile
├── entrypoint.sh           # DB 마이그레이션 + gunicorn 실행
├── fly.toml                # fly.io 배포 설정
├── .env.example
├── templates/
│   ├── base.html           # 공통 레이아웃 (navbar·footer)
│   ├── index.html          # 메인 지도 + 통계 대시보드
│   ├── restrooms.html      # 화장실 목록
│   ├── restroom_new.html   # 화장실 추가
│   ├── inspections.html    # 점검 기록 목록
│   ├── inspection_new.html # 점검 등록 (카메라 포함)
│   ├── inspection_edit.html
│   ├── inspection_detail.html
│   └── summary.html        # 현황 요약
└── static/
    ├── css/style.css
    └── js/camera.js        # 카메라 촬영 유틸리티
```

---

*본 시스템은 고려대학교 세종캠퍼스 구성원의 안전한 캠퍼스 환경 조성을 위해 제작되었습니다.*

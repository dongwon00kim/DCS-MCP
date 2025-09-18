# DCS MCP Server

[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![DCS](https://img.shields.io/badge/DCS%20World-Compatible-green.svg)](https://www.digitalcombatsimulator.com/)

DCS World의 DCS-BIOS를 활용하여 항공기 정보를 실시간으로 수집하고, MCP(Model Context Protocol) 서버를 통해 대규모 언어 모델(LLM)과 연동할 수 있는 서버 프로젝트입니다.

## ⚡ 빠른 시작

```bash
# 1. 저장소 클론
git clone https://github.com/your-username/dcs-mcp-server.git
cd dcs-mcp-server

# 2. uv로 환경 설정 (Python 3.10+ 필요)
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync

# 3. 서버 실행
python src/main.py
```

## 🎯 프로젝트 개요

이 프로젝트는 DCS World 시뮬레이터에서 실행 중인 항공기의 다양한 정보(계기판 데이터, 무기 시스템 상태, 엔진 상태 등)를 DCS-BIOS를 통해 실시간으로 수집하고, MCP 프로토콜을 사용하여 Claude, ChatGPT 등의 LLM에서 활용할 수 있도록 제공합니다.

## 📁 프로젝트 구조

```
dcs-mcp/
├── src/                    # 소스 코드
│   ├── main.py            # 메인 엔트리포인트
│   ├── mcp_server.py      # MCP 서버 구현
│   ├── dcs_bios_receiver.py  # UDP 데이터 수신
│   ├── dcs_bios_sender.py    # TCP 제어 전송
│   ├── data_parser.py     # 데이터 파싱
│   ├── config.py          # 설정 관리
│   └── logging_config.py  # 로깅 설정
├── dcs-bios/              # DCS-BIOS 라이브러리
├── tests/                 # 테스트 코드
├── config.json            # 서버 설정
├── pyproject.toml         # 프로젝트 메타데이터 및 의존성
├── pytest.ini            # 테스트 설정
└── README.md             # 문서
```

## ✨ 주요 기능

- **실시간 항공기 데이터 수집**: dcs-mcp를 통한 항공기 계기판 및 시스템 정보 실시간 모니터링
- **MCP 프로토콜 지원**: 표준 MCP 인터페이스를 통한 LLM 연동
- **다중 항공기 지원**: F/A-18C, F-16C, A-10C II, AV-8B 등 dcs-mcp 지원 항공기
- **RESTful API**: HTTP 기반 데이터 접근 인터페이스 제공
- **실시간 스트리밍**: WebSocket을 통한 실시간 데이터 스트리밍
- **데이터 필터링**: 사용자 정의 데이터 필터링 및 포맷팅

## 🛠️ 시스템 요구사항

### 필수 요구사항
- **Python**: 3.10 이상 (MCP 패키지 요구사항)
- **DCS World**: 최신 버전
- **DCS-BIOS**: 최신 버전 설치 및 설정
- **운영체제**: Windows 10/11 (DCS World 호환)

### 권장 요구사항
- **RAM**: 8GB 이상
- **네트워크**: 로컬 네트워크 연결
- **저장공간**: 500MB 이상

## 📦 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/dcs-mcp-server.git
cd dcs-mcp-server
```

### 2. Python 환경 설정

#### uv 사용 (권장)
[uv](https://github.com/astral-sh/uv)는 빠른 Python 패키지 관리자입니다.

```bash
# uv 설치 (아직 설치하지 않은 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# 또는
brew install uv  # macOS with Homebrew
# 또는
pip install uv  # 기존 Python 환경

# 가상환경 생성 및 의존성 설치
uv venv  # 가상환경 생성
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync  # 기본 의존성 설치

# 개발 환경 설정 (선택사항)
uv sync --extra dev  # 개발 도구 포함 설치
```

#### pip 사용 (대안)
```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -e .

# 개발 도구 설치 (선택사항)
pip install -e ".[dev]"
```

### 3. dcs-mcp 설정 확인
dcs-mcp가 올바르게 설치되어 있고, UDP 포트 5010에서 데이터를 전송하도록 설정되어 있는지 확인하세요.

### 4. 설정 파일 구성
```bash
# 기본 설정 파일이 이미 제공됨
# 필요시 수정
vi config.json  # 또는 선호하는 편집기 사용
```

## 🚀 사용법

### 서버 시작
```bash
python src/main.py
```

### MCP 클라이언트로 연결
```bash
# Claude Desktop에서 MCP 서버 설정
# config 파일에 서버 정보 추가
```

### API 엔드포인트 예시
```bash
# 현재 항공기 정보 조회
curl http://localhost:8080/api/aircraft/current

# 특정 시스템 상태 조회
curl http://localhost:8080/api/aircraft/systems/engine

# 무기 시스템 정보 조회
curl http://localhost:8080/api/aircraft/weapons
```

## 📊 지원되는 데이터 타입

### 항공기 시스템
- **엔진**: RPM, 온도, 연료량, 추력 설정
- **전자전**: RWR, ECM, 채프/플레어 상태
- **항법**: GPS, INS, TACAN 정보
- **통신**: 라디오 주파수, 설정 상태

### 무기 시스템
- **미사일**: 종류, 수량, 락온 상태
- **폭탄**: 종류, 수량, 투하 모드
- **기총**: 탄약량, 선택 상태

### 계기판 정보
- **기본 비행 계기**: 고도, 속도, 자세
- **항법 계기**: 헤딩, 경로, 웨이포인트
- **경고등**: 마스터 캐우션, 경고 상태

## 🔧 설정

### config.json 예시
```json
{
  "dcs_bios": {
    "host": "127.0.0.1",
    "port": 5010,
    "multicast": false
  },
  "mcp_server": {
    "host": "127.0.0.1",
    "port": 8080,
    "enable_websocket": true
  },
  "aircraft_filter": [
    "FA-18C_hornet",
    "F-16C_50",
    "A-10C_2"
  ],
  "data_update_rate": 10,
  "logging": {
    "level": "INFO",
    "file": "logs/dcs_mcp_server.log"
  }
}
```

## 🤝 MCP 프로토콜 연동

### Claude Desktop 설정
```json
{
  "mcpServers": {
    "dcs-mcp": {
      "command": "python",
      "args": ["/path/to/dcs-mcp-server/src/main.py"],
      "env": {
        "DCS_BIOS_HOST": "127.0.0.1",
        "DCS_BIOS_PORT": "5010"
      }
    }
  }
}
```

### 사용 가능한 MCP 도구
- `get_aircraft_status`: 현재 항공기의 전체 상태 정보
- `get_engine_data`: 엔진 시스템 상세 정보
- `get_weapons_status`: 무기 시스템 현황
- `get_navigation_data`: 항법 시스템 정보
- `monitor_warnings`: 경고 및 캐우션 모니터링

## 📚 API 문서

상세한 API 문서는 서버 실행 후 `http://localhost:8080/docs`에서 확인할 수 있습니다.

## 🛠️ 개발 환경

### 개발 도구 설치
```bash
# uv 사용
uv sync --extra dev

# 또는 pip 사용
pip install -e ".[dev]"
```

### 코드 품질 도구

#### 코드 포맷팅
```bash
# Black으로 코드 포맷팅
black src/

# 포맷 체크만 수행
black --check src/
```

#### 린팅
```bash
# Ruff로 린팅
ruff check src/

# 자동 수정 가능한 이슈 수정
ruff check --fix src/
```

#### 타입 체킹
```bash
# MyPy로 타입 체킹
mypy src/
```

### 테스트

```bash
# 단위 테스트 실행
pytest tests/

# 커버리지 포함 테스트
pytest --cov=src tests/

# 특정 테스트만 실행
pytest tests/test_specific.py::test_function

# 통합 테스트 (DCS World 실행 필요)
pytest tests/integration/
```

## 📦 빌드 및 배포

### 패키지 빌드
```bash
# wheel 패키지 빌드
uv build

# 또는 pip 사용
pip install build
python -m build
```

### Windows 실행 파일 생성 (Windows 전용)
```bash
# Windows 의존성 설치
uv sync --extra windows

# PyInstaller로 실행 파일 생성
pyinstaller --onefile --name dcs-mcp-server src/main.py

# 또는 spec 파일 사용 (고급)
pyinstaller dcs-mcp-server.spec
```

### Docker 이미지 빌드 (선택사항)
```bash
# Docker 이미지 빌드
docker build -t dcs-mcp-server .

# 컨테이너 실행
docker run -p 8080:8080 dcs-mcp-server
```

## 🧪 테스트

```bash
# 단위 테스트 실행
python -m pytest tests/

# 통합 테스트 (DCS World 실행 필요)
python -m pytest tests/integration/
```

## 🤝 기여 방법

1. 이 저장소를 포크합니다
2. 새로운 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 📋 로드맵

- [ ] 추가 항공기 모듈 지원 (F-14, AH-64D)
- [ ] 웹 기반 모니터링 대시보드
- [ ] 데이터 기록 및 재생 기능
- [ ] 클러스터 모드 지원
- [ ] 성능 최적화

## ⚠️ 알려진 이슈

- DCS World 업데이트 시 dcs-mcp 호환성 확인 필요
- 일부 항공기에서 특정 데이터 포인트 누락 가능
- 고해상도 모니터링 시 CPU 사용량 증가

## 📄 라이선스

이 프로젝트는 GPL 3.0 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

- [dcs-mcp](https://github.com/dcs-mcp/dcs-mcp) 개발팀
- DCS World 커뮤니티
- MCP 프로토콜 개발팀

## 📞 연락처 및 지원

- **이슈 트래커**: [GitHub Issues](https://github.com/your-username/dcs-mcp-server/issues)
- **이메일**: your-email@example.com
- **디스코드**: DCS 한국 커뮤니티

---

**⚡ 빠른 시작**: DCS World를 실행하고 원하는 항공기에 탑승한 후, 서버를 시작하여 즉시 실시간 데이터를 확인할 수 있습니다!
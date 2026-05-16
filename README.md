# Agri Info Hub

농업 뉴스, 식물 리뷰, 정부와 지자체 지원사업 정보를 모아 웹 대시보드로 보여주는 첫 번째 MVP입니다.

## 구조

```text
collector.py             # 정보 수집, 분류, 중복 제거, JSON/SQLite 저장
config.json              # 수집 출처, 키워드, 실행 조건
data/items.json          # 웹 대시보드가 읽는 데이터
data/agri_items.sqlite3  # 수집 원본 저장소, 실행 후 생성
web/                     # 정적 웹 대시보드
launchd/                 # macOS 자동 실행 예시
scripts/                 # 실행 스크립트
```

## 로컬 실행

```bash
cd /Users/oh/Documents/Codex/2026-05-16/new-chat/agri-info-hub
python3 collector.py --once --ignore-display
python3 -m http.server 4173
```

브라우저에서 `http://localhost:4173/web/`를 열면 됩니다.

## 화면 켜짐 조건

기본 실행은 macOS에서 `IODisplayWrangler` 전원 상태를 확인합니다. 화면이 꺼져 있으면 수집을 건너뛰고, 노트북이 잠자기 상태에 들어가면 macOS가 작업 자체를 멈춥니다.

```bash
python3 collector.py --once
```

수동 테스트처럼 화면 상태를 무시하고 싶을 때만 `--ignore-display`를 붙입니다.

## HTTPS 인증서

`config.json`의 `allow_insecure_ssl_fallback`은 로컬 개발 환경에서 인증서 체인이 막힐 때만 쓰는 우회 옵션입니다. 공개 서비스로 배포할 때는 정상 인증서가 설정된 서버 환경에서 `false`로 바꾸는 편이 좋습니다.

## 자동 실행

현재 기본 업데이트 주기는 `config.json`의 `collection_interval_minutes` 값입니다. 지금은 `30`으로 설정되어 있으므로 30분마다, 즉 0.5시간마다 한 번 수집을 시도합니다.

macOS 자동 실행은 `launchd`로 등록합니다. 수집기는 실행될 때마다 화면이 켜져 있는지 확인하고, 화면이 꺼져 있으면 수집하지 않습니다. 노트북이 잠자기 상태면 macOS가 작업을 실행하지 않습니다.

macOS 백그라운드 작업은 `Documents` 폴더 접근이 막힐 수 있으므로, 설치 스크립트는 실행본을 `~/Library/Application Support/AgriInfoHub`로 복사한 뒤 그 위치에서 수집기를 실행합니다.

설치:

```bash
cd /Users/oh/Documents/Codex/2026-05-16/new-chat/agri-info-hub
chmod +x scripts/*.sh
./scripts/install_launchd.sh
```

로컬 사이트 실행:

```bash
./scripts/run_site.sh 4173
```

상태 확인:

```bash
./scripts/status_launchd.sh
```

자동 실행 해제:

```bash
./scripts/uninstall_launchd.sh
```

주기를 바꾸려면 `config.json`의 `collection_interval_minutes`를 수정한 뒤 `./scripts/install_launchd.sh`를 다시 실행합니다.

```json
{
  "collection_interval_minutes": 60
}
```

## 공개 사이트 자동 업데이트

Cloudflare Pages는 GitHub 저장소가 바뀌면 자동으로 다시 배포합니다. 이 프로젝트는 수집이 끝난 뒤 GitHub API로 다음 파일을 업데이트할 수 있습니다.

```text
data/items.json
data/summary.json
public/data/items.json
public/data/summary.json
```

먼저 GitHub fine-grained token을 만들고 `Contents: Read and write` 권한을 `oheus/agri-info-hub` 저장소에 부여합니다. 그 다음 토큰을 로컬에 저장합니다.

```bash
./scripts/setup_github_token.sh
```

토큰 설정 후 자동 실행을 다시 설치합니다.

```bash
./scripts/install_launchd.sh
```

수동으로 한 번 테스트하려면:

```bash
./scripts/run_collect_and_publish.sh
```

## 다음 확장

- 공개 배포 절차는 `DEPLOY.md` 참고
- Supabase나 PostgreSQL로 클라우드 DB 연결
- Vercel, GitHub Pages, Cloudflare Pages 배포
- OpenAI API를 붙여 요약, 중요도, 키워드 품질 개선
- 관심 지역과 작물별 페이지 추가
- 지자체 농업기술센터별 직접 감시 출처 확대

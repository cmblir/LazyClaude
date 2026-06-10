"""v3.99.x — runtime Korean-residue sweep coverage (scripts/e2e-i18n-residue.mjs).

Auto-generated from the live-DOM sweep of all tabs in en/zh: full literals
and >=5-char composed segments found in repo sources but missing from the
locale dicts. See docs in CLAUDE.md (i18n pipeline).
"""

NEW_EN: dict[str, str] = {
    "서버는 순수 stdlib이라 바이너리 PDF를 직접 생성하지 않습니다 — 인쇄용 HTML을 연 뒤 브라우저의 인쇄 → PDF로 저장을 사용하세요.":
        "The server is pure stdlib and does not generate binary PDFs directly — open the print-ready HTML, then use the browser's Print → Save as PDF.",
    "output styles 기능 자체는 정상입니다. 폐기·제거된 것은 standalone 슬래시 커맨드뿐입니다.":
        "The output styles feature itself works fine. Only the standalone slash command was deprecated and removed.",
    "/deep-interview — 소크라테스식 명확화 → 설계 (bt-deep-interview)":
        "/deep-interview — Socratic clarification → design (bt-deep-interview)",
    "아래 파일은 해당 범위의 모든 대화에 주입되어 컨텍스트를 부풀립니다. 분할·요약을 권장합니다.":
        "The files below are injected into every conversation in their scope, bloating the context. Splitting or summarizing them is recommended.",
    ".omx/wiki 영구 저장소 (LazyClaude는 Prompt Library 로 대체)":
        ".omx/wiki persistent store (LazyClaude replaces it with the Prompt Library)",
    "의존성 누락 등으로 샌드박스를 시작할 수 없으면 경고 후 비격리 실행하는 대신":
        "if the sandbox cannot start due to missing dependencies, instead of warning and then running unsandboxed",
    "$tasks — 입력에서 actionable TODO/FIXME/BUG 추출":
        "$tasks — extract actionable TODO/FIXME/BUG items from the input",
    "아래 파일은 해당 범위의 모든 대화에 주입되어 컨텍스트를 부풀립니다":
        "The files below are injected into every conversation in their scope, bloating the context",
    "claude-agent-sdk (Python) · uv 권장.":
        "claude-agent-sdk (Python) · uv recommended.",
    "외부 CLI 전용 기능 (LazyClaude 흡수 안 됨)":
        "External CLI-only features (not absorbed into LazyClaude)",
    "비용에서 통계적으로 비정상적인 지점을 로컬에서 탐지합니다":
        "Detects statistically anomalous points in costs locally",
    "tool_use / tool_result 라운드 트립.":
        "tool_use / tool_result round trip.",
    "Edit — 포맷 검사 + console.log 경고":
        "Edit — format check + console.log warning",
    "Anthropic 호스팅 Python sandbox.":
        "Anthropic-hosted Python sandbox.",
    "를 소스별로 설정하고 임계치 도달 시 알림을 받습니다":
        "set per source, with alerts when the threshold is reached",
    "핵심 엔드포인트 · content block 구조.":
        "Core endpoints · content block structure.",
    "Python / TypeScript SDK 진입점.":
        "Python / TypeScript SDK entry points.",
    "기술 내용·코드·에러는 보존)로 답하도록 강제하는":
        "technical content, code, and errors preserved) that forces responses in that style",
    "저장된 베이스라인과 비교해 회귀를 강조 표시합니다":
        "Compares against the saved baseline and highlights regressions",
    "코드에 대해 보안·성능·가독성 관점에서 리뷰해줘":
        "Review this code from a security, performance, and readability perspective",
    "SessionStart — 컨텍스트 자동 로드":
        "SessionStart — auto-load context",
    "는 전용 탭에서 더 자세히 설정할 수 있어요":
        "can be configured in more detail in its dedicated tab",
    "필요하며 개인 계정에서는 사용할 수 없습니다":
        "is required and is not available on personal accounts",
    "으로 저장되며 화면에는 마스킹되어 표시됩니다":
        "is saved as such and shown masked on screen",
    "로그의 한도 도달 메시지에서 추출한 값이며":
        "is a value extracted from limit-reached messages in the logs, and",
    "관련 없는 설정은 절대 건드리지 않습니다":
        "Unrelated settings are never touched",
    "최고 추론 (deep reasoning)":
        "Highest reasoning (deep reasoning)",
    "배수가 낮을수록 더 민감하게 탐지합니다":
        "Lower multipliers detect more sensitively",
    "주간 한도에 부딪힌 적이 없거나 관련":
        "has never hit the weekly limit, or the related",
    "빨간 점은 이상으로 표시된 날입니다.":
        "Red dots are days flagged as anomalies.",
    "프로세스와 스레드의 차이를 1줄로.":
        "The difference between a process and a thread, in one line.",
    "빨간 점은 이상으로 표시된 날입니다":
        "Red dots are days flagged as anomalies",
    "추정 비용을 가져와 순위를 매깁니다":
        "Fetches estimated costs and ranks them",
    "도구는 트랜스크립트에 저장되지 않아":
        "tools are not stored in the transcript, so",
    "히트를 깨뜨렸는지 정확히 짚어냅니다":
        "pinpoints exactly what broke the hits",
    "영역 안에서 특정 경로만 다시 읽기":
        "Re-read only specific paths within the area",
    "코드·에러·기술 내용은 그대로 보존":
        "Code, errors, and technical content are preserved as-is",
    "프록시로 아웃바운드 트래픽 라우팅":
        "Route outbound traffic through a proxy",
    "데이터에 없어 표시할 수 없습니다":
        "Not present in the data, so it cannot be displayed",
    "일일 지출 시계열 (이상 강조)":
        "Daily spend time series (anomalies highlighted)",
    "시각을 추출할 데이터가 없습니다":
        "No data to extract timestamps from",
    "샌드박스 제약으로 실패한 명령을":
        "commands that failed due to sandbox restrictions",
    "으로 호출하는 팀 오케스트레이션":
        "team orchestration invoked via",
    "자격증명 디렉토리를 여기 추가해":
        "add the credentials directory here",
    "프레임워크·리소스 큐레이션 목록":
        "Curated list of frameworks and resources",
    "컨텍스트에 주입하는 부하를 측정":
        "Measure the load injected into the context",
    "여기 추가하면 그 경로도 쓰기":
        "adding it here makes that path writable too",
    "에 메트릭이 여기에 나타납니다":
        "metrics will appear here",
    "저장소를 확인한 뒤 진행하세요":
        "Check the repository before proceeding",
    "은 외부 스크립트를 실행합니다":
        "runs external scripts",
    "일일 지출 시계열 (이상 강조":
        "daily spend time series (anomalies highlighted",
    "재작성 방안을 단계별로 제시해":
        "present the rewrite plan step by step",
    "윈도우 · 주간 쿼터 · 주간":
        "window · weekly quota · weekly",
    "이 명령들은 샌드박스 밖에서":
        "these commands run outside the sandbox",
    "대화 컨텍스트에 이미 등장한":
        "already present in the conversation context",
    "명령을 매번 묻지 않고 자동":
        "commands automatically without asking each time",
    "는 파싱할 수 없으니 반드시":
        "cannot be parsed, so be sure to",
    "관리형 배포의 보안 게이트용":
        "for security gating in managed deployments",
    "후 자동으로 다시 계산됩니다":
        "is recalculated automatically afterwards",
    "대시보드에 전용 탭이 있어요":
        "the dashboard has a dedicated tab",
    "을 연 뒤 브라우저의 인쇄":
        "after opening it, the browser's print",
    "명령을 정적 매핑으로 노출":
        "exposes commands as a static mapping",
    "를 직접 생성하지 않습니다":
        "is not generated directly",
    "기능은 폐기되지 않았습니다":
        "the feature has not been deprecated",
    "최신 · 최강 (현재 기본":
        "newest · most powerful (current default",
    "한도 도달 기록이 없습니다":
        "no limit-reached records",
    "프로세스와 스레드의 차이를":
        "the difference between processes and threads",
    "백업이 디스크에 존재하여":
        "a backup exists on disk, so",
    "코드·에러·기술내용 보존":
        "preserves code, errors, and technical content",
    "매번 권한을 묻지 않고도":
        "without asking for permission every time",
    "버튼은 큐레이션된 명령만":
        "the button covers curated commands only",
    "등 호환되지 않는 도구용":
        "for incompatible tools such as",
    "블록을 분류 시각화합니다":
        "visualizes blocks by category",
    "삭제는 여전히 프롬프트됨":
        "deletion is still prompted",
    "샌드박스가 접근 가능한":
        "accessible to the sandbox",
    "일자 × 시간대 히트맵":
        "date × hour heatmap",
    "셋을 만들어 시작하세요":
        "create a set to get started",
    "새 도메인 첫 접근 시":
        "on first access to a new domain",
    "관리형 설정에서만 의미":
        "only meaningful in managed settings",
    "분할 데이터가 없습니다":
        "no breakdown data",
    "외부 CLI 전용 기능":
        "external CLI-only feature",
    "기능 자체는 정상입니다":
        "the feature itself works fine",
    "에서 검증된 형식입니다":
        "is a format validated in",
    "시간대별 (0–23시)":
        "by hour (0–23h)",
    "접근 경계를 강제합니다":
        "enforces access boundaries",
    "전일 대비 급등 (%)":
        "spike vs. previous day (%)",
    "샌드박스가 조회 가능한":
        "readable by the sandbox",
    "분할·요약을 권장합니다":
        "splitting and summarizing are recommended",
    "등 강력한 서비스 노출":
        "exposing powerful services such as",
    "마이그레이션 어드바이저":
        "Migration Advisor",
    "위 환경변수를 설정하고":
        "set the environment variables above and",
    "톤/포맷 커스터마이즈":
        "tone/format customization",
    "없으면 오프라인 구조":
        "if unavailable, an offline structure",
    "를 제공하지 않습니다":
        "is not provided",
    "프로토콜로 설정하세요":
        "set it as the protocol",
    "로 저장을 사용하세요":
        "use Save as",
    "샌드박스 안에서 모든":
        "all within the sandbox",
    "서버가 직접 실행하는":
        "executed directly by the server",
    "리소스 큐레이션 목록":
        "curated resource list",
    "압축 코드리뷰 코멘트":
        "Compressed code review comments",
    "와일드카드 서브도메인":
        "Wildcard subdomain",
    "셀에 마우스를 올리면":
        "when you hover over a cell",
    "변경은 추적되지 않음":
        "changes are not tracked",
    "페이지에서 발급합니다":
        "issued from the page",
    "슬래시 커맨드뿐입니다":
        "is slash commands only",
    "주간 Opus 윈도우":
        "Weekly Opus window",
    "으로 시작하며 콘솔의":
        "starts with, and the console's",
    "디렉토리만 쓰기 가능":
        "only the directory is writable",
    "샌드박스는 셸 명령을":
        "the sandbox handles shell commands",
    "렌더링 사이트 미지원":
        "rendered sites not supported",
    "포트에 바인딩하도록":
        "to bind to the port",
    "고전 중국어 스타일":
        "Classical Chinese style",
    "소크라테스식 명확화":
        "Socratic clarification",
    "백업을 먼저 만들고":
        "create a backup first, then",
    "유형별로 더 저렴한":
        "cheaper per type",
    "에 타임스탬프 주입":
        "inject a timestamp into",
    "유출 경로가 될 수":
        "could become a leak vector",
    "를 추가로 설치하면":
        "if you additionally install",
    "추정치와 비교합니다":
        "compares against the estimate",
    "쿼터의 실시간 잔량":
        "real-time remaining quota",
    "컨텍스트 자동 로드":
        "auto-load context",
    "면 모든 프로젝트에":
        "then to all projects",
    "자동화하면 좋습니다":
        "is worth automating",
    "최신 턴 usage":
        "latest turn usage",
    "σ 배수 (민감도)":
        "σ multiplier (sensitivity)",
    "흡수 기능만 쓰려면":
        "to use only the absorb feature",
    "알림 임계치 퍼센트":
        "notification threshold percent",
    "레이트리밋 · 쿼터":
        "Rate limit · Quota",
    "하위 프로세스 포함":
        "including child processes",
    "세션별로 분석하는":
        "analyzed per session",
    "페이지 레퍼런스로":
        "as a page reference",
    "이 위젯에 대하여":
        "About this widget",
    "런 센터에서 임의":
        "ad hoc from the Run Center",
    "샌드박스 불가 시":
        "when sandboxing is unavailable",
    "여기 미리 넣으면":
        "if you put it here in advance",
    "날씨를 조회합니다":
        "looks up the weather",
    "순위별 이상 목록":
        "ranked anomaly list",
    "윈도우 · 임계값":
        "Window · Threshold",
    "런 센터에서 즉시":
        "immediately from the Run Center",
    "검사/필터링/로깅":
        "inspection/filtering/logging",
    "에서 실제 청구된":
        "actually billed in",
    "모드를 이미 흡수":
        "already absorbs the mode",
    "폐기·제거된 것은":
        "what was deprecated·removed",
    "스타일 어드바이저":
        "Style Advisor",
    "가능 (보완 관계":
        "possible (complementary relationship",
    "키워드로 호출하는":
        "invoked by keyword",
    "캡처되지 않는 것":
        "what is not captured",
    "베이스라인 윈도우":
        "baseline window",
    "으로 보낸 메트릭":
        "metrics sent to",
    "목록은 좁게 유지":
        "keep the list narrow",
    "공식 용어 정의.":
        "Official term definitions.",
    "번 반복되었습니다":
        "times repeated",
    "에 교차 실행하고":
        "cross-run on, and",
    "포맷으로 압축해":
        "compress into the format",
    "샌드박스 OFF":
        "Sandbox OFF",
    "로그가 오래되어":
        "logs are stale, so",
    "공식 용어 정의":
        "official term definitions",
    "코드 라인·커밋":
        "code lines·commits",
    "에 적합한 것은":
        "what is suited for",
    "에서 관리됩니다":
        "is managed in",
    "로 답하게 하는":
        "that makes it answer with",
    "어서션)을 여러":
        "assertions) across multiple",
    "키가 필요합니다":
        "key is required",
    "핵심 엔드포인트":
        "core endpoints",
    "리스트/사용량은":
        "the list/usage",
    "컨텍스트 윈도우":
        "context window",
    "스위트 컴포넌트":
        "suite components",
    "창에서 진행돼요":
        "happens in the window",
    "주간 쿼터 한도":
        "weekly quota limit",
    "을 분리 시각화":
        "visualized separately",
    "으로 집계됩니다":
        "is aggregated as",
    "알림이 없습니다":
        "No notifications",
    "로드 경계 초과":
        "load boundary exceeded",
    "전일 대비 급등":
        "spike vs. previous day",
    "절감 (군더더기":
        "savings (fluff",
    "일일 지출 급증":
        "daily spend spike",
    "로 격리 밖에서":
        "outside isolation",
    "기간별 사용량을":
        "usage by period",
    "샌드박스 명령이":
        "sandbox commands",
    "한국의 수도는?":
        "What is the capital of Korea?",
    "브레이크포인트가":
        "breakpoints",
    "큐레이션 목록":
        "curated list",
    "시간대 히트맵":
        "time-of-day heatmap",
    "결과를 압축해":
        "compress the results",
    "쿼리를 분석해":
        "analyze the query",
    "두 개의 연속":
        "two consecutive",
    "기본은 일자별":
        "defaults to daily",
    "컨텍스트 절약":
        "context savings",
    "한 줄에 하나":
        "one per line",
    "내부에서 직접":
        "directly from inside",
    "셋이 없습니다":
        "set does not exist",
    "이라 바이너리":
        "so the binary",
    "이 대시보드는":
        "this dashboard",
    "마우스 올리면":
        "on hover",
    "로 폴백합니다":
        "falls back to",
    "윈도우 근접도":
        "window proximity",
    "등)로 라우팅":
        "etc.) routing",
    "한국의 수도는":
        "The capital of Korea is",
    "팀 리더보드는":
        "The team leaderboard",
    "를 사용합니다":
        "uses",
    "키만 안전하게":
        "only the keys, securely",
    "로 내보냅니다":
        "exports to",
    "안에서 실행해":
        "run inside",
    "메트릭 수신처":
        "metrics destination",
    "최신 · 최강":
        "latest · strongest",
    "까지 읽을 수":
        "can read up to",
    "설정을 망라한":
        "covering all settings",
    "커스터마이즈용":
        "for customization",
    "예산 · 알림":
        "budget · alerts",
    "자동 실행해줘":
        "run it automatically",
    "을 보내 어느":
        "send it and see which",
    "컨텍스트 관리":
        "context management",
    "을 활성화하고":
        "enable it and",
    "에서 사용자별":
        "per user in",
    "데이터에 없어":
        "not in the data",
    "배수 (민감도":
        "multiplier (sensitivity",
    "노이즈 숨김":
        "hide noise",
    "개선 제안은":
        "improvement suggestions",
    "워크스페이스":
        "workspace",
    "런 센터에서":
        "in the Run Center",
    "팀 리더보드":
        "team leaderboard",
    "특정 도시의":
        "of a specific city",
    "급증했습니다":
        "surged",
    "접미사 지원":
        "suffix support",
    "핵심 차이는":
        "the key difference is",
    "스타일 서브":
        "style sub",
    "키워드 직접":
        "keywords directly",
    "액션 아이템":
        "action items",
    "서버는 순수":
        "the server is pure",
    "자체를 막음":
        "blocks it entirely",
    "기본은 사전":
        "the default is pre-",
    "모든 수치는":
        "all figures",
    "되감기 가능":
        "rewind available",
    "되감기 불가":
        "rewind unavailable",
    "임의 생성한":
        "randomly generated",
    "반드시 격리":
        "must be isolated",
    "직접 편집된":
        "directly edited",
    "도구를 바로":
        "the tool right away",
    "샌드박스란?":
        "What is a sandbox?",
    "급등 (임계":
        "spike (threshold",
    "원시인 말투":
        "caveman speech",
    "읽기 정책은":
        "the read policy",
    "되감기 옵션":
        "rewind option",
    "긴 컨텍스트":
        "long context",
    "도메인 소켓":
        "domain socket",
    "추정 절감액":
        "estimated savings",
    "를 실행하면":
        "when you run",
    "영구 저장소":
        "persistent storage",
    "범위별 추정":
        "Per-range estimate",
    "고성능 추론":
        "High-performance reasoning",
    "탐지된 이상":
        "Detected anomalies",
    "에이전트에서":
        "in the agent",
    "필드로 흡수":
        "absorbed into a field",
    "활동 한눈에":
        "activity at a glance",
    "탭으로 대체":
        "replaced by the tab",
    "로 정직하게":
        "honestly as",
    "읽기 재허용":
        "re-allow reads",
    "만 적용되고":
        "only applies, and",
    "라운드 트립":
        "round trip",
    "최고 심각도":
        "Highest severity",
    "줄로 요약해":
        "summarize in lines",
    "는 브라우저":
        "the browser",
    "커맨드 폐기":
        "Command deprecation",
    "흡수 안 됨":
        "Not absorbed",
    "아직 수신된":
        "received yet",
    "넓은 허용은":
        "broad permissions",
    "저장소 ↗":
        "Repository ↗",
    "미설정이면":
        "if unset",
    "지출 한도":
        "Spending limit",
    "은퇴 일정":
        "Retirement schedule",
    "쓰기 금지":
        "No writes",
    "탭 헤더의":
        "in the tab header",
    "상대 로드":
        "Relative load",
    "예산 가드":
        "Budget guard",
    "캡처 대상":
        "Capture target",
    "비샌드박스":
        "Non-sandbox",
    "프로젝트가":
        "the project",
    "에이전트가":
        "the agent",
    "압축 커밋":
        "Squash commit",
    "포맷 검사":
        "Format check",
    "체크리스트":
        "Checklist",
    "압축 레벨":
        "Compression level",
    "최고 추론":
        "Maximum reasoning",
    "절감 통계":
        "Savings stats",
    "컨텍스트를":
        "the context",
    "기반입니다":
        "is based on",
    "필요합니다":
        "is required",
    "없이 즉시":
        "immediately without",
    "에 흡수된":
        "absorbed into",
    "간 병합됨":
        "merged across",
    "스크립트는":
        "the script",
    "를 가져와":
        "fetches and",
    "경계 초과":
        "Out of bounds",
    "샌드박스로":
        "via sandbox",
    "체크포인트":
        "Checkpoint",
    "복구 절차":
        "Recovery procedure",
    "런 센터의":
        "in the Run Center",
    "읽기 금지":
        "No reads",
    "결제 관리":
        "Billing management",
    "일일 지출":
        "Daily spend",
    "위 (임계":
        "above (threshold",
    "실행합니다":
        "runs",
    "다시 계산":
        "Recalculate",
    "상시 로드":
        "Always loaded",
    "툴킷 모음":
        "Toolkit collection",
    "임계치 %":
        "Threshold %",
    "샌드박스란":
        "What is a sandbox",
    "과 인쇄용":
        "and print-ready",
    "전용 기능":
        "Dedicated feature",
    "함께 쓰면":
        "When used together",
    "기록합니다":
        "records",
    "으로 흡수":
        "absorbed into",
    "인덱스에서":
        "from the index",
    "표시됩니다":
        "is displayed",
    "남은 공간":
        "Remaining space",
    "수준 격리":
        "level isolation",
    "정의 순서":
        "Definition order",
    "이상 탐지":
        "Anomaly detection",
    "한도 도달":
        "Limit reached",
    "핵심 결정":
        "Key decisions",
    "권장 대체":
        "Recommended replacement",
    "는 미지원":
        "is not supported",
    "는 무시됨":
        "is ignored",
    "레지스트리":
        "Registry",
    "알림 센터":
        "Notification center",
    "셋(케이스":
        "set (case",
    "절대 한도":
        "Absolute limit",
    "리셋까지":
        "until reset",
    "자율모드":
        "Autonomous mode",
    "형식:":
        "Format:",
    "분리)":
        "separated)",
    "통과.":
        "passed.",
    "추정값":
        "Estimate",
    "플래그":
        "Flag",
    "스타일":
        "Style",
    "히트율":
        "Hit rate",
    "중간":
        "Medium",
    "절감":
        "Savings",
    "심각":
        "Critical",
    "대신":
        "instead",
    "높음":
        "High",
    "신규":
        "New",
    "제약":
        "Constraints",
    "영역":
        "Area",
    "영문":
        "English",
    "경고":
        "Warning",
    "형식":
        "Format",
    "정상":
        "Normal",
}

NEW_ZH: dict[str, str] = {
    "서버는 순수 stdlib이라 바이너리 PDF를 직접 생성하지 않습니다 — 인쇄용 HTML을 연 뒤 브라우저의 인쇄 → PDF로 저장을 사용하세요.":
        "服务器是纯 stdlib 实现，不会直接生成二进制 PDF — 请打开打印用 HTML，然后使用浏览器的打印 → 另存为 PDF。",
    "output styles 기능 자체는 정상입니다. 폐기·제거된 것은 standalone 슬래시 커맨드뿐입니다.":
        "output styles 功能本身正常。被弃用并移除的只是 standalone 斜杠命令。",
    "/deep-interview — 소크라테스식 명확화 → 설계 (bt-deep-interview)":
        "/deep-interview — 苏格拉底式澄清 → 设计 (bt-deep-interview)",
    "아래 파일은 해당 범위의 모든 대화에 주입되어 컨텍스트를 부풀립니다. 분할·요약을 권장합니다.":
        "下方文件会被注入到其作用范围内的所有对话中，导致上下文膨胀。建议进行拆分或摘要。",
    ".omx/wiki 영구 저장소 (LazyClaude는 Prompt Library 로 대체)":
        ".omx/wiki 持久存储（LazyClaude 以 Prompt Library 替代）",
    "의존성 누락 등으로 샌드박스를 시작할 수 없으면 경고 후 비격리 실행하는 대신":
        "若因依赖缺失等原因无法启动沙箱，不是发出警告后以非隔离方式运行，而是",
    "$tasks — 입력에서 actionable TODO/FIXME/BUG 추출":
        "$tasks — 从输入中提取可执行的 TODO/FIXME/BUG",
    "아래 파일은 해당 범위의 모든 대화에 주입되어 컨텍스트를 부풀립니다":
        "下方文件会被注入到其作用范围内的所有对话中，导致上下文膨胀",
    "claude-agent-sdk (Python) · uv 권장.":
        "claude-agent-sdk (Python) · 推荐使用 uv。",
    "외부 CLI 전용 기능 (LazyClaude 흡수 안 됨)":
        "外部 CLI 专属功能（未被 LazyClaude 吸收）",
    "비용에서 통계적으로 비정상적인 지점을 로컬에서 탐지합니다":
        "在本地检测成本中统计上异常的点",
    "tool_use / tool_result 라운드 트립.":
        "tool_use / tool_result 往返。",
    "Edit — 포맷 검사 + console.log 경고":
        "Edit — 格式检查 + console.log 警告",
    "Anthropic 호스팅 Python sandbox.":
        "Anthropic 托管的 Python sandbox。",
    "를 소스별로 설정하고 임계치 도달 시 알림을 받습니다":
        "按来源设置，并在达到阈值时接收通知",
    "핵심 엔드포인트 · content block 구조.":
        "核心端点 · content block 结构。",
    "Python / TypeScript SDK 진입점.":
        "Python / TypeScript SDK 入口。",
    "기술 내용·코드·에러는 보존)로 답하도록 강제하는":
        "保留技术内容、代码与错误）并强制以该方式回答的",
    "저장된 베이스라인과 비교해 회귀를 강조 표시합니다":
        "与已保存的基线比较并高亮显示回归",
    "코드에 대해 보안·성능·가독성 관점에서 리뷰해줘":
        "请从安全、性能和可读性角度审查这段代码",
    "SessionStart — 컨텍스트 자동 로드":
        "SessionStart — 自动加载上下文",
    "는 전용 탭에서 더 자세히 설정할 수 있어요":
        "可在专属标签页中进行更详细的设置",
    "필요하며 개인 계정에서는 사용할 수 없습니다":
        "为必需项，且个人账户无法使用",
    "으로 저장되며 화면에는 마스킹되어 표시됩니다":
        "保存，并在屏幕上以掩码形式显示",
    "로그의 한도 도달 메시지에서 추출한 값이며":
        "是从日志中的达到限额消息提取的值，",
    "관련 없는 설정은 절대 건드리지 않습니다":
        "绝不会改动无关的设置",
    "최고 추론 (deep reasoning)":
        "最高推理 (deep reasoning)",
    "배수가 낮을수록 더 민감하게 탐지합니다":
        "倍数越低，检测越灵敏",
    "주간 한도에 부딪힌 적이 없거나 관련":
        "从未触及每周限额，或相关",
    "빨간 점은 이상으로 표시된 날입니다.":
        "红点表示被标记为异常的日期。",
    "프로세스와 스레드의 차이를 1줄로.":
        "用一行说明进程与线程的区别。",
    "빨간 점은 이상으로 표시된 날입니다":
        "红点表示被标记为异常的日期",
    "추정 비용을 가져와 순위를 매깁니다":
        "获取估算成本并进行排名",
    "도구는 트랜스크립트에 저장되지 않아":
        "工具不会保存到转录中，因此",
    "히트를 깨뜨렸는지 정확히 짚어냅니다":
        "精确指出是什么破坏了命中",
    "영역 안에서 특정 경로만 다시 읽기":
        "仅重新读取该区域内的特定路径",
    "코드·에러·기술 내용은 그대로 보존":
        "代码、错误与技术内容原样保留",
    "프록시로 아웃바운드 트래픽 라우팅":
        "通过代理路由出站流量",
    "데이터에 없어 표시할 수 없습니다":
        "数据中不存在，无法显示",
    "일일 지출 시계열 (이상 강조)":
        "每日支出时间序列（异常高亮）",
    "시각을 추출할 데이터가 없습니다":
        "没有可提取时间的数据",
    "샌드박스 제약으로 실패한 명령을":
        "因沙箱限制而失败的命令",
    "으로 호출하는 팀 오케스트레이션":
        "来调用的团队编排",
    "자격증명 디렉토리를 여기 추가해":
        "将凭证目录添加到此处",
    "프레임워크·리소스 큐레이션 목록":
        "框架与资源的精选列表",
    "컨텍스트에 주입하는 부하를 측정":
        "测量注入上下文的负载",
    "여기 추가하면 그 경로도 쓰기":
        "添加到此处后，该路径也可写入",
    "에 메트릭이 여기에 나타납니다":
        "的指标会显示在这里",
    "저장소를 확인한 뒤 진행하세요":
        "请先确认存储库再继续",
    "은 외부 스크립트를 실행합니다":
        "会运行外部脚本",
    "일일 지출 시계열 (이상 강조":
        "每日支出时间序列 (异常高亮",
    "재작성 방안을 단계별로 제시해":
        "分步提出重写方案",
    "윈도우 · 주간 쿼터 · 주간":
        "窗口 · 每周配额 · 每周",
    "이 명령들은 샌드박스 밖에서":
        "这些命令在沙箱之外",
    "대화 컨텍스트에 이미 등장한":
        "已出现在对话上下文中的",
    "명령을 매번 묻지 않고 자동":
        "无需每次询问即自动执行命令",
    "는 파싱할 수 없으니 반드시":
        "无法解析，因此务必",
    "관리형 배포의 보안 게이트용":
        "用于托管部署的安全门控",
    "후 자동으로 다시 계산됩니다":
        "之后会自动重新计算",
    "대시보드에 전용 탭이 있어요":
        "仪表板中有专用标签页",
    "을 연 뒤 브라우저의 인쇄":
        "打开后使用浏览器的打印",
    "명령을 정적 매핑으로 노출":
        "以静态映射方式公开命令",
    "를 직접 생성하지 않습니다":
        "不会直接生成",
    "기능은 폐기되지 않았습니다":
        "该功能并未废弃",
    "최신 · 최강 (현재 기본":
        "最新 · 最强 (当前默认",
    "한도 도달 기록이 없습니다":
        "没有达到限额的记录",
    "프로세스와 스레드의 차이를":
        "进程与线程的区别",
    "백업이 디스크에 존재하여":
        "备份存在于磁盘上，因此",
    "코드·에러·기술내용 보존":
        "保留代码·错误·技术内容",
    "매번 권한을 묻지 않고도":
        "无需每次请求权限",
    "버튼은 큐레이션된 명령만":
        "该按钮仅限精选命令",
    "등 호환되지 않는 도구용":
        "等不兼容工具专用",
    "블록을 분류 시각화합니다":
        "对块进行分类可视化",
    "삭제는 여전히 프롬프트됨":
        "删除仍会提示",
    "샌드박스가 접근 가능한":
        "沙箱可访问的",
    "일자 × 시간대 히트맵":
        "日期 × 时段热力图",
    "셋을 만들어 시작하세요":
        "创建一个集合以开始",
    "새 도메인 첫 접근 시":
        "首次访问新域名时",
    "관리형 설정에서만 의미":
        "仅在托管设置中有意义",
    "분할 데이터가 없습니다":
        "没有细分数据",
    "외부 CLI 전용 기능":
        "外部 CLI 专用功能",
    "기능 자체는 정상입니다":
        "功能本身正常",
    "에서 검증된 형식입니다":
        "中经过验证的格式",
    "시간대별 (0–23시)":
        "按时段 (0–23时)",
    "접근 경계를 강제합니다":
        "强制执行访问边界",
    "전일 대비 급등 (%)":
        "较前一日激增 (%)",
    "샌드박스가 조회 가능한":
        "沙箱可查询的",
    "분할·요약을 권장합니다":
        "建议拆分·摘要",
    "등 강력한 서비스 노출":
        "等强大服务的暴露",
    "마이그레이션 어드바이저":
        "迁移顾问",
    "위 환경변수를 설정하고":
        "设置上述环境变量并",
    "톤/포맷 커스터마이즈":
        "语气/格式自定义",
    "없으면 오프라인 구조":
        "若无则为离线结构",
    "를 제공하지 않습니다":
        "不提供",
    "프로토콜로 설정하세요":
        "请设置为协议",
    "로 저장을 사용하세요":
        "请使用另存为",
    "샌드박스 안에서 모든":
        "在沙箱内所有",
    "서버가 직접 실행하는":
        "由服务器直接执行的",
    "리소스 큐레이션 목록":
        "资源精选列表",
    "압축 코드리뷰 코멘트":
        "压缩的代码审查评论",
    "와일드카드 서브도메인":
        "通配符子域名",
    "셀에 마우스를 올리면":
        "将鼠标悬停在单元格上时",
    "변경은 추적되지 않음":
        "更改不会被跟踪",
    "페이지에서 발급합니다":
        "在页面中签发",
    "슬래시 커맨드뿐입니다":
        "仅限斜杠命令",
    "주간 Opus 윈도우":
        "每周 Opus 窗口",
    "으로 시작하며 콘솔의":
        "开头，且控制台的",
    "디렉토리만 쓰기 가능":
        "仅该目录可写",
    "샌드박스는 셸 명령을":
        "沙箱对 shell 命令",
    "렌더링 사이트 미지원":
        "不支持渲染型网站",
    "포트에 바인딩하도록":
        "以绑定到端口",
    "고전 중국어 스타일":
        "文言文风格",
    "소크라테스식 명확화":
        "苏格拉底式澄清",
    "백업을 먼저 만들고":
        "先创建备份，再",
    "유형별로 더 저렴한":
        "按类型更便宜的",
    "에 타임스탬프 주입":
        "注入时间戳到",
    "유출 경로가 될 수":
        "可能成为泄露途径",
    "를 추가로 설치하면":
        "如果额外安装",
    "추정치와 비교합니다":
        "与估算值进行比较",
    "쿼터의 실시간 잔량":
        "配额的实时余量",
    "컨텍스트 자동 로드":
        "自动加载上下文",
    "면 모든 프로젝트에":
        "则对所有项目",
    "자동화하면 좋습니다":
        "建议自动化",
    "최신 턴 usage":
        "最新轮次的 usage",
    "σ 배수 (민감도)":
        "σ 倍数 (敏感度)",
    "흡수 기능만 쓰려면":
        "若只想使用吸收功能",
    "알림 임계치 퍼센트":
        "通知阈值百分比",
    "레이트리밋 · 쿼터":
        "速率限制 · 配额",
    "하위 프로세스 포함":
        "包括子进程",
    "세션별로 분석하는":
        "按会话分析的",
    "페이지 레퍼런스로":
        "作为页面参考",
    "이 위젯에 대하여":
        "关于此小部件",
    "런 센터에서 임의":
        "在运行中心任意",
    "샌드박스 불가 시":
        "无法使用沙箱时",
    "여기 미리 넣으면":
        "如果提前放在这里",
    "날씨를 조회합니다":
        "查询天气",
    "순위별 이상 목록":
        "按排名的异常列表",
    "윈도우 · 임계값":
        "窗口 · 阈值",
    "런 센터에서 즉시":
        "在运行中心立即",
    "검사/필터링/로깅":
        "检查/过滤/日志记录",
    "에서 실제 청구된":
        "中实际计费的",
    "모드를 이미 흡수":
        "已经吸收了该模式",
    "폐기·제거된 것은":
        "已废弃·移除的内容",
    "스타일 어드바이저":
        "风格顾问",
    "가능 (보완 관계":
        "可以 (互补关系",
    "키워드로 호출하는":
        "通过关键词调用的",
    "캡처되지 않는 것":
        "未被捕获的内容",
    "베이스라인 윈도우":
        "基线窗口",
    "으로 보낸 메트릭":
        "发送的指标",
    "목록은 좁게 유지":
        "保持列表精简",
    "공식 용어 정의.":
        "官方术语定义。",
    "번 반복되었습니다":
        "次重复",
    "에 교차 실행하고":
        "上交叉运行，并",
    "포맷으로 압축해":
        "压缩为该格式",
    "샌드박스 OFF":
        "沙箱 OFF",
    "로그가 오래되어":
        "日志过旧，因此",
    "공식 용어 정의":
        "官方术语定义",
    "코드 라인·커밋":
        "代码行·提交",
    "에 적합한 것은":
        "适合的是",
    "에서 관리됩니다":
        "中管理",
    "로 답하게 하는":
        "使其回答的",
    "어서션)을 여러":
        "断言)在多个",
    "키가 필요합니다":
        "需要密钥",
    "핵심 엔드포인트":
        "核心端点",
    "리스트/사용량은":
        "列表/用量",
    "컨텍스트 윈도우":
        "上下文窗口",
    "스위트 컴포넌트":
        "套件组件",
    "창에서 진행돼요":
        "在窗口中进行",
    "주간 쿼터 한도":
        "每周配额上限",
    "을 분리 시각화":
        "分开可视化",
    "으로 집계됩니다":
        "进行汇总",
    "알림이 없습니다":
        "暂无通知",
    "로드 경계 초과":
        "超出负载边界",
    "전일 대비 급등":
        "较前日激增",
    "절감 (군더더기":
        "节省 (冗余",
    "일일 지출 급증":
        "每日支出激增",
    "로 격리 밖에서":
        "在隔离之外",
    "기간별 사용량을":
        "按时间段的用量",
    "샌드박스 명령이":
        "沙箱命令",
    "한국의 수도는?":
        "韩国的首都是？",
    "브레이크포인트가":
        "断点",
    "큐레이션 목록":
        "精选列表",
    "시간대 히트맵":
        "时段热力图",
    "결과를 압축해":
        "压缩结果",
    "쿼리를 분석해":
        "分析查询",
    "두 개의 연속":
        "两个连续",
    "기본은 일자별":
        "默认按日",
    "컨텍스트 절약":
        "上下文节省",
    "한 줄에 하나":
        "每行一个",
    "내부에서 직접":
        "在内部直接",
    "셋이 없습니다":
        "集不存在",
    "이라 바이너리":
        "因此二进制",
    "이 대시보드는":
        "此仪表盘",
    "마우스 올리면":
        "鼠标悬停时",
    "로 폴백합니다":
        "回退",
    "윈도우 근접도":
        "窗口接近度",
    "등)로 라우팅":
        "等)路由",
    "한국의 수도는":
        "韩国的首都是",
    "팀 리더보드는":
        "团队排行榜",
    "를 사용합니다":
        "使用",
    "키만 안전하게":
        "仅密钥安全地",
    "로 내보냅니다":
        "导出到",
    "안에서 실행해":
        "在其中运行",
    "메트릭 수신처":
        "指标接收端",
    "최신 · 최강":
        "最新 · 最强",
    "까지 읽을 수":
        "可以读取到",
    "설정을 망라한":
        "涵盖所有设置的",
    "커스터마이즈용":
        "用于自定义",
    "예산 · 알림":
        "预算 · 提醒",
    "자동 실행해줘":
        "自动执行",
    "을 보내 어느":
        "发送后看哪个",
    "컨텍스트 관리":
        "上下文管理",
    "을 활성화하고":
        "启用并",
    "에서 사용자별":
        "中按用户",
    "데이터에 없어":
        "不在数据中",
    "배수 (민감도":
        "倍数 (灵敏度",
    "노이즈 숨김":
        "隐藏噪音",
    "개선 제안은":
        "改进建议",
    "워크스페이스":
        "工作区",
    "런 센터에서":
        "在运行中心",
    "팀 리더보드":
        "团队排行榜",
    "특정 도시의":
        "特定城市的",
    "급증했습니다":
        "激增",
    "접미사 지원":
        "后缀支持",
    "핵심 차이는":
        "核心区别是",
    "스타일 서브":
        "风格子",
    "키워드 직접":
        "直接关键词",
    "액션 아이템":
        "行动项",
    "서버는 순수":
        "服务器是纯",
    "자체를 막음":
        "完全阻止",
    "기본은 사전":
        "默认为预",
    "모든 수치는":
        "所有数值",
    "되감기 가능":
        "可回退",
    "되감기 불가":
        "不可回退",
    "임의 생성한":
        "随机生成的",
    "반드시 격리":
        "必须隔离",
    "직접 편집된":
        "被直接编辑的",
    "도구를 바로":
        "直接将工具",
    "샌드박스란?":
        "什么是沙箱?",
    "급등 (임계":
        "激增 (阈值",
    "원시인 말투":
        "原始人语气",
    "읽기 정책은":
        "读取策略",
    "되감기 옵션":
        "回退选项",
    "긴 컨텍스트":
        "长上下文",
    "도메인 소켓":
        "域套接字",
    "추정 절감액":
        "预估节省额",
    "를 실행하면":
        "运行时",
    "영구 저장소":
        "持久存储",
    "범위별 추정":
        "按范围估算",
    "고성능 추론":
        "高性能推理",
    "탐지된 이상":
        "检测到的异常",
    "에이전트에서":
        "在代理中",
    "필드로 흡수":
        "并入字段",
    "활동 한눈에":
        "活动一目了然",
    "탭으로 대체":
        "由标签页替代",
    "로 정직하게":
        "如实地",
    "읽기 재허용":
        "重新允许读取",
    "만 적용되고":
        "仅生效，且",
    "라운드 트립":
        "往返",
    "최고 심각도":
        "最高严重级别",
    "줄로 요약해":
        "行内总结",
    "는 브라우저":
        "浏览器",
    "커맨드 폐기":
        "命令废弃",
    "흡수 안 됨":
        "未被吸收",
    "아직 수신된":
        "尚未收到",
    "넓은 허용은":
        "宽泛的允许",
    "저장소 ↗":
        "仓库 ↗",
    "미설정이면":
        "若未设置",
    "지출 한도":
        "支出上限",
    "은퇴 일정":
        "退役时间表",
    "쓰기 금지":
        "禁止写入",
    "탭 헤더의":
        "标签页头部的",
    "상대 로드":
        "相对加载",
    "예산 가드":
        "预算防护",
    "캡처 대상":
        "捕获目标",
    "비샌드박스":
        "非沙箱",
    "프로젝트가":
        "项目",
    "에이전트가":
        "代理",
    "압축 커밋":
        "压缩提交",
    "포맷 검사":
        "格式检查",
    "체크리스트":
        "检查清单",
    "압축 레벨":
        "压缩级别",
    "최고 추론":
        "最高推理",
    "절감 통계":
        "节省统计",
    "컨텍스트를":
        "上下文",
    "기반입니다":
        "为基础",
    "필요합니다":
        "需要",
    "없이 즉시":
        "无需即可立即",
    "에 흡수된":
        "被吸收进",
    "간 병합됨":
        "之间已合并",
    "스크립트는":
        "脚本",
    "를 가져와":
        "获取并",
    "경계 초과":
        "超出边界",
    "샌드박스로":
        "通过沙箱",
    "체크포인트":
        "检查点",
    "복구 절차":
        "恢复流程",
    "런 센터의":
        "运行中心的",
    "읽기 금지":
        "禁止读取",
    "결제 관리":
        "结算管理",
    "일일 지출":
        "每日支出",
    "위 (임계":
        "以上（阈值",
    "실행합니다":
        "执行",
    "다시 계산":
        "重新计算",
    "상시 로드":
        "常驻加载",
    "툴킷 모음":
        "工具包合集",
    "임계치 %":
        "阈值 %",
    "샌드박스란":
        "什么是沙箱",
    "과 인쇄용":
        "及打印用",
    "전용 기능":
        "专用功能",
    "함께 쓰면":
        "搭配使用时",
    "기록합니다":
        "记录",
    "으로 흡수":
        "吸收为",
    "인덱스에서":
        "从索引中",
    "표시됩니다":
        "显示",
    "남은 공간":
        "剩余空间",
    "수준 격리":
        "级隔离",
    "정의 순서":
        "定义顺序",
    "이상 탐지":
        "异常检测",
    "한도 도달":
        "达到限额",
    "핵심 결정":
        "关键决策",
    "권장 대체":
        "推荐替代",
    "는 미지원":
        "不支持",
    "는 무시됨":
        "被忽略",
    "레지스트리":
        "注册表",
    "알림 센터":
        "通知中心",
    "셋(케이스":
        "集（用例",
    "절대 한도":
        "绝对限额",
    "리셋까지":
        "距重置",
    "자율모드":
        "自主模式",
    "형식:":
        "格式：",
    "분리)":
        "分离）",
    "통과.":
        "通过。",
    "추정값":
        "估算值",
    "플래그":
        "标志",
    "스타일":
        "样式",
    "히트율":
        "命中率",
    "중간":
        "中等",
    "절감":
        "节省",
    "심각":
        "严重",
    "대신":
        "代替",
    "높음":
        "高",
    "신규":
        "新增",
    "제약":
        "约束",
    "영역":
        "区域",
    "영문":
        "英文",
    "경고":
        "警告",
    "형식":
        "格式",
    "정상":
        "正常",
}

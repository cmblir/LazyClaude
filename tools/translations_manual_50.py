"""v3.99.x — source-side i18n gap closure, round 2.

All t() keys in dist/app.js + dist/index.html and static Korean literals
in server/*.py that were missing from the locale dicts (found by diffing
sources against en.json after the runtime residue sweep).
"""

NEW_EN: dict[str, str] = {
    "Claude Code의 Bash 샌드박스는 셸 명령을 OS 수준 격리(macOS Seatbelt / Linux·WSL2 bubblewrap) 안에서 실행해, 매번 권한을 묻지 않고도 파일·네트워크 접근 경계를 강제합니다. native Windows는 미지원(WSL2 사용).":
        "Claude Code's Bash sandbox runs shell commands inside OS-level isolation (macOS Seatbelt / Linux·WSL2 bubblewrap), enforcing file/network access boundaries without prompting for permission every time. Native Windows is not supported (use WSL2).",
    "thinking block 과 최종 응답을 분리 시각화. Opus 4.8/4.7·Sonnet 4.6 = adaptive thinking + effort(low~max) 로 추론/비용 조절. legacy 모델은 budget_tokens.":
        "Visualizes thinking blocks and the final response separately. Opus 4.8/4.7·Sonnet 4.6 = adaptive thinking + effort (low~max) to control reasoning/cost. Legacy models use budget_tokens.",
    "기본은 사전 허용 도메인 없음 — 새 도메인 첫 접근 시 프롬프트. 여기 미리 넣으면 프롬프트 생략. 와일드카드 서브도메인(*.npmjs.org) 지원. github.com 같은 넓은 허용은 데이터 유출 경로가 될 수 있음.":
        "By default no domains are pre-allowed — the first access to a new domain triggers a prompt. Adding domains here skips the prompt. Wildcard subdomains (*.npmjs.org) are supported. Broad allows like github.com can become a data exfiltration path.",
    "샌드박스 제약으로 실패한 명령을 dangerouslyDisableSandbox로 격리 밖에서 재시도(권한 프롬프트 경유). false면 Strict 모드 — 반드시 격리 또는 excludedCommands 안에서만 실행.":
        "Retry commands that failed due to sandbox restrictions outside isolation via dangerouslyDisableSandbox (going through a permission prompt). If false, Strict mode — commands must run only inside isolation or within excludedCommands.",
    "🎯 LazyClaude는 OMC의 4 모드를 이미 흡수 — 별도 설치 없이 워크플로우 탭의 빌트인 템플릿(bt-autopilot/ralph/ultrawork/deep-interview) 또는 런 센터에서 즉시 사용 가능":
        "🎯 LazyClaude has already absorbed OMC's 4 modes — no separate install needed; use them right away via the workflow tab's built-in templates (bt-autopilot/ralph/ultrawork/deep-interview) or the Run Center",
    "이 대시보드는 Claude Code 의 OpenTelemetry 메트릭 수신처(OTLP 백엔드)입니다. 순수 stdlib 서버라 protobuf 는 파싱할 수 없으니 반드시 http/json 프로토콜로 설정하세요.":
        "This dashboard is an OpenTelemetry metrics receiver (OTLP backend) for Claude Code. It's a pure-stdlib server and cannot parse protobuf, so be sure to set the protocol to http/json.",
    "조직 Admin API(Claude Code Analytics)에서 사용자별 세션·코드 라인·커밋·PR·토큰·추정 비용을 가져와 순위를 매깁니다. 조직 Admin 키(sk-ant-admin...)가 필요합니다.":
        "Fetches per-user sessions, lines of code, commits, PRs, tokens, and estimated cost from the org Admin API (Claude Code Analytics) and ranks them. Requires an org Admin key (sk-ant-admin...).",
    "팀 리더보드는 Claude Code Analytics Admin API를 사용합니다. 표준 API 키가 아닌 조직 Admin 키(sk-ant-admin...)가 필요하며 개인 계정에서는 사용할 수 없습니다.":
        "The team leaderboard uses the Claude Code Analytics Admin API. It requires an org Admin key (sk-ant-admin...) rather than a standard API key, and is not available on personal accounts.",
    "OMC /team 스타일 5단계: 계획(Opus)→요구사항명세(Sonnet)→3-병렬 실행(Sonnet)→취합→검증(Haiku)→실패 시 수정. Repeat 3회까지 자동 verify-fix 루프.":
        "OMC /team-style 5 stages: plan (Opus) → requirements spec (Sonnet) → 3-parallel execution (Sonnet) → aggregate → verify (Haiku) → fix on failure. Automatic verify-fix loop up to 3 repeats.",
    "소규모 팀(5명)이 매일 10만 이벤트를 처리하는 실시간 알림 시스템을 만들려고 한다. SQS vs Kafka vs Redis Streams 중 어떤 선택이 적합한지 트레이드오프를 설계해서 답해줘.":
        "A small team (5 people) wants to build a real-time notification system handling 100k events per day. Lay out the trade-offs and answer which of SQS vs Kafka vs Redis Streams is the right choice.",
    "CLAUDE.md 또는 .claude/agents/<name>.md 또는 .claude/skills/<name>/SKILL.md 또는 .claude/settings.local.json":
        "CLAUDE.md or .claude/agents/<name>.md or .claude/skills/<name>/SKILL.md or .claude/settings.local.json",
    "Anthropic 서버가 직접 실행하는 hosted tool (web_search · code_execution · web_fetch) 을 활성화하고 응답 블록을 분류 시각화합니다.":
        "Enables hosted tools executed directly on Anthropic's servers (web_search · code_execution · web_fetch) and visualizes response blocks by category.",
    "관리형 설정에서만 의미. true면 managed settings의 filesystem.allowRead만 적용되고 user/project/local의 allowRead는 무시됨.":
        "Only meaningful in managed settings. If true, only filesystem.allowRead from managed settings applies; allowRead from user/project/local is ignored.",
    "denyRead 영역 안에서 특정 경로만 다시 읽기 허용. 예: denyRead [~/] + allowRead [.] (project settings에서 . 은 프로젝트 루트).":
        "Re-allow reading only specific paths inside a denyRead area. Example: denyRead [~/] + allowRead [.] (in project settings, . is the project root).",
    "Bash 명령을 OS 수준 격리(macOS Seatbelt / Linux·WSL2 bubblewrap) 안에서 실행. user settings에 true면 모든 프로젝트에 적용.":
        "Runs Bash commands inside OS-level isolation (macOS Seatbelt / Linux·WSL2 bubblewrap). If true in user settings, it applies to all projects.",
    "claude CLI가 설치되어 있지 않습니다. `brew install claude` 또는 https://docs.claude.com/en/docs/claude-code 참고":
        "The claude CLI is not installed. See `brew install claude` or https://docs.claude.com/en/docs/claude-code",
    "프로젝트 도메인에 특화된 에이전트를 `.claude/agents/<name>.md`에 두면 Agent 툴로 위임 가능. 위임(delegation) 축 점수가 직접 오릅니다.":
        "Put agents specialized for your project domain in `.claude/agents/<name>.md` to delegate via the Agent tool. This directly raises your delegation axis score.",
    "최근 3년간 Anthropic, OpenAI, Google DeepMind 의 논문 편수를 웹에서 찾아보고, 그 수치로 막대 그래프의 값 배열 [A, O, G] 을 출력해.":
        "Search the web for the number of papers published by Anthropic, OpenAI, and Google DeepMind over the last 3 years, and output a bar chart value array [A, O, G] from those figures.",
    "Claude Design 공식 API 는 아직 미공개. claude.ai/design 에서 PDF/PPTX/HTML 로 export 한 파일을 기본 경로에서 스캔합니다.":
        "The official Claude Design API is not yet public. Scans files exported as PDF/PPTX/HTML from claude.ai/design in the default path.",
    "아직 5시간/주간 한도에 부딪힌 적이 없거나 관련 세션 로그가 오래되어, 정확한 리셋 시각을 추출할 데이터가 없습니다. 아래 사용량 근사치는 세션 토큰 합계 기반입니다.":
        "You haven't hit the 5-hour/weekly limit yet, or the relevant session logs are too old, so there is no data to extract an exact reset time. The usage approximation below is based on session token totals.",
    "저장 시 settings.json.bak.<시각> 백업을 먼저 만들고, 검증된 sandbox 키만 안전하게 병합 기록합니다. 관련 없는 설정은 절대 건드리지 않습니다.":
        "On save, a settings.json.bak.<timestamp> backup is created first, and only validated sandbox keys are safely merged in. Unrelated settings are never touched.",
    "터미널에서: claude mcp add context7 npx -y @upstash/context7-mcp  (MCP는 대시보드에서 직접 편집하지 않고 CLI로 추가)":
        "In the terminal: claude mcp add context7 npx -y @upstash/context7-mcp  (MCP is added via the CLI, not edited directly in the dashboard)",
    "기본 읽기 정책은 ~/.aws/credentials, ~/.ssh 까지 읽을 수 있음 — 자격증명 디렉토리를 여기 추가해 차단 권장. 예: ~/.aws, ~/.ssh.":
        "The default read policy can read even ~/.aws/credentials and ~/.ssh — adding credential directories here to block them is recommended. Example: ~/.aws, ~/.ssh.",
    "Claude Code 세션 안에서 슬래시 명령으로 호출하는 팀 오케스트레이션 (autopilot · ralph · ultrawork · deep-interview)":
        "Team orchestration invoked via slash commands inside a Claude Code session (autopilot · ralph · ultrawork · deep-interview)",
    "Anthropic 조직 Admin API에서 실제 청구된 토큰/USD를 가져와 로컬 추정치와 비교합니다. Admin 키(sk-ant-admin...)가 필요합니다.":
        "Fetches actually billed tokens/USD from the Anthropic org Admin API and compares them with local estimates. Requires an Admin key (sk-ant-admin...).",
    "🎯 LazyClaude는 OMX의 4 명령을 정적 매핑으로 노출 — 런 센터에서 임의 프로바이더(Claude/GPT/Gemini/Ollama)로 dispatch":
        "🎯 LazyClaude exposes OMX's 4 commands as static mappings — dispatch to any provider (Claude/GPT/Gemini/Ollama) from the Run Center",
    "CLAUDE.md 는 세션 시작 시 자동 로드됩니다. 프로젝트 맥락(스택·규칙·도메인용어)을 여기 적으면 매 세션 설명 반복이 사라져 참여도·안정성 모두 상승.":
        "CLAUDE.md is auto-loaded at session start. Write your project context (stack, rules, domain terms) here to stop repeating explanations every session — boosting both engagement and stability.",
    "기본은 작업 디렉토리만 쓰기 가능. 여기 추가하면 그 경로도 쓰기 허용(하위 프로세스 포함). 예: ~/.kube, /tmp/build. 스코프 간 병합됨.":
        "By default only the working directory is writable. Paths added here are also write-allowed (including child processes). Example: ~/.kube, /tmp/build. Merged across scopes.",
    "~/.claude/settings.json 의 statusLine 설정을 추천하세요. 쉘 명령으로 current branch, model, cost 표시.":
        "Recommend a statusLine setting for ~/.claude/settings.json. Show current branch, model, and cost via a shell command.",
    "🛣️ Claude Code Router — Claude Code를 GLM/Z.AI/DeepSeek 등 다른 LLM으로 라우팅하고 zclaude 별칭 안내":
        "🛣️ Claude Code Router — route Claude Code to other LLMs like GLM/Z.AI/DeepSeek, with zclaude alias guidance",
    "의존성 누락 등으로 샌드박스를 시작할 수 없으면 경고 후 비격리 실행하는 대신 Claude Code 시작 자체를 막음. 관리형 배포의 보안 게이트용.":
        "If the sandbox cannot start due to missing dependencies etc., this blocks Claude Code from starting at all instead of warning and running unisolated. For security gating in managed deployments.",
    "LIVE 실행에는 ANTHROPIC_API_KEY 또는 설치된 claude CLI 가 필요합니다. 없으면 각 셀이 ⚠️ 로 정직하게 실패 표시됩니다.":
        "LIVE execution requires ANTHROPIC_API_KEY or an installed claude CLI. Without one, each cell is honestly marked as failed with ⚠️.",
    "조직 Admin API 키는 표준 API 키와 다릅니다. sk-ant-admin... 으로 시작하며 콘솔의 admin-keys 페이지에서 발급합니다.":
        "An org Admin API key differs from a standard API key. It starts with sk-ant-admin... and is issued from the console's admin-keys page.",
    "로컬 JSONL 에서 Claude Code(및 Codex/Gemini 등) 토큰·비용을 일/주/월/세션별로 분석하는 CLI. 설치 없이 즉시 실행.":
        "A CLI that analyzes Claude Code (and Codex/Gemini etc.) tokens and costs by day/week/month/session from local JSONL. Runs instantly without installation.",
    "> 비용은 입력/출력 토큰 × 모델 요금으로 **추정**한 값입니다. 캐시 토큰은 합계에는 포함하지만 비용 추정에는 별도 단가를 적용하지 않습니다.":
        "> Cost is an **estimate** of input/output tokens × model rates. Cache tokens are included in totals but no separate rate is applied to them in the cost estimate.",
    "Anthropic은 주간/5시간 쿼터의 실시간 잔량 API를 제공하지 않습니다. 이 위젯은 로컬 세션 로그 기반 best-effort 추정입니다.":
        "Anthropic does not provide a real-time remaining-quota API for the weekly/5-hour quotas. This widget is a best-effort estimate based on local session logs.",
    "Opus / Sonnet / Haiku 3 티어로 제공된다. Anthropic 은 2024년 Amazon 으로부터 40억 달러 투자를 유치했고, ":
        "Offered in 3 tiers: Opus / Sonnet / Haiku. Anthropic raised a $4 billion investment from Amazon in 2024, and ",
    "두 개의 연속 요청(base → modified)을 보내 어느 캐시 브레이크포인트가 prompt-cache 히트를 깨뜨렸는지 정확히 짚어냅니다.":
        "Sends two consecutive requests (base → modified) to pinpoint exactly which cache breakpoint broke the prompt-cache hit.",
    "Smart routing — Haiku/Opus 자동 선택 (LazyClaude는 modelHint 'auto/fast/deep' 으로 흡수)":
        "Smart routing — automatic Haiku/Opus selection (LazyClaude absorbs this via modelHint 'auto/fast/deep')",
    "caveman 스타일 서브에이전트 위임 가이드 (investigator·builder·reviewer) — 결과를 압축해 메인 컨텍스트 절약":
        "caveman-style subagent delegation guide (investigator·builder·reviewer) — compresses results to save main context",
    "어서션 기반 회귀 테스트. 테스트 셋(케이스+어서션)을 여러 프로바이더에 교차 실행하고, 저장된 베이스라인과 비교해 회귀를 강조 표시합니다.":
        "Assertion-based regression testing. Cross-runs a test set (cases + assertions) against multiple providers and highlights regressions against the saved baseline.",
    "settings.json이 올바른 JSON이 아닙니다. 손상을 막기 위해 편집을 비활성화했습니다. 파일을 수동으로 고친 뒤 새로고침하세요.":
        "settings.json is not valid JSON. Editing has been disabled to prevent corruption. Fix the file manually and refresh.",
    "최신 `web_search_20260209` 은 dynamic filtering 지원 (code_execution 동시 활성화 필요). ":
        "The latest `web_search_20260209` supports dynamic filtering (requires code_execution to be enabled simultaneously). ",
    "CLAUDE_CODE_ENABLE_TELEMETRY=1 + OTEL_EXPORTER_OTLP_PROTOCOL=http/json 로 연결.":
        "Connect with CLAUDE_CODE_ENABLE_TELEMETRY=1 + OTEL_EXPORTER_OTLP_PROTOCOL=http/json.",
    "Stop-callback — Slack/Discord/Telegram 알림 (LazyClaude는 워크플로우 notify 필드로 흡수)":
        "Stop-callback — Slack/Discord/Telegram notifications (LazyClaude absorbs this via the workflow notify field)",
    "상세 멤버 리스트/사용량은 claude.ai/settings/organization 에서 관리됩니다. 로컬에는 조직 식별자만 저장됨.":
        "Detailed member lists/usage are managed at claude.ai/settings/organization. Only the org identifier is stored locally.",
    "https://www.anthropic.com/news 의 내용을 가져와서 핵심 발표 3가지를 요약해줘. 출처 citation 포함.":
        "Fetch the content of https://www.anthropic.com/news and summarize the 3 key announcements. Include source citations.",
    "permissions.allow / permissions.deny 는 set-union, 나머지는 top-level override.":
        "permissions.allow / permissions.deny are set-union; everything else is top-level override.",
    "사용자 확인 없이 요구사항 → 실행 → 검증까지 단일 흐름으로 끝까지 돌리는 자율 파이프라인 (OMC /autopilot 에 대응).":
        "An autonomous pipeline that runs requirements → execution → verification end-to-end in a single flow without user confirmation (corresponds to OMC /autopilot).",
    "Wiki 시스템 — 세션 내 지식 베이스 (LazyClaude는 Claude Docs Hub + Prompt Library 로 대체)":
        "Wiki system — in-session knowledge base (LazyClaude replaces this with Claude Docs Hub + Prompt Library)",
    "깨뜨렸는지 진단. Anthropic cache-diagnosis 베타(헤더 cache-diagnosis-2026-04-07) 사용, ":
        "diagnoses what broke it. Uses the Anthropic cache-diagnosis beta (header cache-diagnosis-2026-04-07), ",
    "요청을 작업 유형별로 더 저렴한 모델/프로바이더(Haiku·DeepSeek·Ollama 등)로 라우팅. 대시보드에 전용 탭이 있어요.":
        "Routes requests to cheaper models/providers (Haiku·DeepSeek·Ollama, etc.) by task type. There's a dedicated tab in the dashboard.",
    "샌드박스 안에서 모든 Unix 도메인 소켓 연결 허용. /var/run/docker.sock 등 강력한 서비스 노출 위험 — 신중히.":
        "Allows all Unix domain socket connections inside the sandbox. Risk of exposing powerful services like /var/run/docker.sock — use with caution.",
    "system 블록에 매 요청마다 바뀌는 값(타임스탬프)을 넣어 캐시가 깨지는 전형적 사례. 예상 진단: system_changed.":
        "A classic case of cache busting: putting a value that changes every request (a timestamp) in the system block. Expected diagnosis: system_changed.",
    "완료 기준 통과할 때까지 verify → fix 루프를 반복 (OMC /ralph 에 대응). 최대 5회 반복, 피드백 자동 주입.":
        "Repeats the verify → fix loop until the completion criteria pass (corresponds to OMC /ralph). Up to 5 iterations, with automatic feedback injection.",
    "Claude Code 가 OTLP/HTTP JSON 으로 보낸 메트릭(비용·토큰·도구 결정·코드 라인·커밋)을 실시간 집계합니다.":
        "Aggregates metrics sent by Claude Code via OTLP/HTTP JSON (cost·tokens·tool decisions·lines of code·commits) in real time.",
    "활성 CLI 세션 — Claude Code CLI 세션의 PID·RSS·CPU·idle 시간 + 터미널 포커스 / SIGTERM":
        "Active CLI sessions — PID·RSS·CPU·idle time of Claude Code CLI sessions + terminal focus / SIGTERM",
    "workflows store 의 costs 배열을 병합 (각 노드 실행 시 _record_workflow_cost 로 쌓임).":
        "Merges the costs array from the workflows store (accumulated via _record_workflow_cost on each node execution).",
    "열린 포트 모니터 — TCP/UDP listening 소켓 + PID/Command/User · 한 번 클릭으로 프로세스 종료":
        "Open port monitor — TCP/UDP listening sockets + PID/Command/User · kill a process with one click",
    "외부 OMC CLI를 추가로 설치하면 Claude Code 세션 안에서도 슬래시 명령으로 호출 가능 (보완 관계, 충돌 없음)":
        "If you additionally install the external OMC CLI, it can also be invoked via slash commands inside Claude Code sessions (complementary, no conflicts)",
    "키는 ~/.claude-dashboard-admin.json 에 파일 권한 600으로 저장되며 화면에는 마스킹되어 표시됩니다.":
        "The key is stored in ~/.claude-dashboard-admin.json with file permission 600 and displayed masked on screen.",
    "사용자를 위한 새 output style (~/.claude/output-styles/<name>.md) 초안을 작성하세요.":
        "Draft a new output style (~/.claude/output-styles/<name>.md) for the user.",
    "서버 재시작: lsof -iTCP:$PORT (default 19500) kill 후 python3 server.py 재실행":
        "Server restart: lsof -iTCP:$PORT (default 19500), kill it, then rerun python3 server.py",
    "~/.claude/file-history 에 남긴 백업을 읽어 프롬프트마다 변경 파일·복원 가능 여부를 표시. 읽기 전용.":
        "Reads backups kept in ~/.claude/file-history and shows changed files·restorability per prompt. Read-only.",
    "위 환경변수를 설정하고 Claude Code 를 실행하면, 다음 내보내기 주기(기본 60초)에 메트릭이 여기에 나타납니다.":
        "Set the environment variables above and run Claude Code, and metrics will appear here on the next export cycle (default 60s).",
    "web_search/web_fetch 와 함께 쓰면 무료, 아니면 월 1,550 시간 무료 후 컨테이너당 $0.05/시간.":
        "Free when used with web_search/web_fetch; otherwise 1,550 free hours per month, then $0.05/hour per container.",
    "팀 리더보드 — 조직 Admin Analytics API(usage_report/claude_code)에서 사용자/액터별 ":
        "Team leaderboard — per user/actor from the org Admin Analytics API(usage_report/claude_code) ",
    "매 세션 시작 시 로드되어 토큰을 소모합니다. 필요 섹션만 유지하거나 skill/prompt library 로 분리 고려.":
        "Loaded at the start of every session, consuming tokens. Consider keeping only the needed sections or splitting into a skill/prompt library.",
    "샌드박스로 실행 가능한 Bash 명령을 매번 묻지 않고 자동 승인. deny 규칙과 위험 경로 삭제는 여전히 프롬프트됨.":
        "Auto-approves Bash commands that can run in the sandbox without asking each time. Deny rules and dangerous path deletions are still prompted.",
    "max-iter / completion-promise / 예산 USD / 수동 cancel 4중 안전장치 안에서 반복. ":
        "Iterates within a 4-layer safety net: max-iter / completion-promise / USD budget / manual cancel. ",
    "CLAUDE.md·메모리 파일을 caveman 포맷으로 압축해 입력 토큰 절감. /caveman-compress <파일>":
        "Compresses CLAUDE.md·memory files into caveman format to save input tokens. /caveman-compress <file>",
    "Security Scan — ~/.claude 전체(settings/CLAUDE.md/hooks/agents/mcp)를 ":
        "Security Scan — scans all of ~/.claude (settings/CLAUDE.md/hooks/agents/mcp) ",
    "세션 처음→끝 진행 타임라인. user 프롬프트 / Agent 위임 / 큰 도구 호출만 추려서 그래프 노드/엣지 형태로.":
        "Session start→end progress timeline. Picks out only user prompts / Agent delegations / large tool calls, rendered as graph nodes/edges.",
    "동일 작업을 5개 병렬 에이전트로 분할 실행 후 취합 (OMC /ultrawork 에 대응). 속도 우선, 비용 5배.":
        "Splits the same task across 5 parallel agents and aggregates the results (corresponds to OMC /ultrawork). Speed first, 5x the cost.",
    "Opus/Sonnet 은 1024 토큰, Haiku 는 2048 토큰이다. TTL 은 기본 5분, 1시간 옵션도 있다.":
        "Opus/Sonnet is 1024 tokens, Haiku is 2048 tokens. TTL defaults to 5 minutes, with a 1-hour option.",
    "Anthropic 호스팅 sandbox — Bash + 파일 연산 (stdout/stderr/return_code). ":
        "Anthropic-hosted sandbox — Bash + file operations (stdout/stderr/return_code). ",
    "기간별 사용량을 Markdown과 인쇄용 HTML로 내보냅니다. 모든 수치는 세션 인덱스에서 읽기 전용으로 집계됩니다.":
        "Exports usage by period as Markdown and print-ready HTML. All figures are aggregated read-only from the session index.",
    "Claude API 전용(Bedrock/Vertex 미지원). API 키가 없으면 오프라인 구조 diff로 폴백합니다.":
        "Claude API only (Bedrock/Vertex not supported). Falls back to an offline structural diff if there is no API key.",
    "취합된 결과물을 PRD 수용 조건과 대조. 통과면 'PASS', 아니면 'FAIL — <실패 항목 목록>' 으로 시작":
        "Compares the aggregated output against the PRD acceptance criteria. Starts with 'PASS' if passing, otherwise 'FAIL — <list of failed items>'",
    "Claude Code CLI 가 설치되어 있지 않아 설치 명령을 실행할 수 없습니다. 명령을 복사해 직접 실행하세요.":
        "Claude Code CLI is not installed, so the install command cannot be run. Copy the command and run it yourself.",
    "보안상 **대화 컨텍스트에 이미 등장한 URL** 만 fetch 가능 (Claude 가 임의 생성한 URL 불가). ":
        "For security, only **URLs that already appeared in the conversation context** can be fetched (URLs Claude generates on its own are not allowed). ",
    "SessionStart 훅으로 이전 세션 요약/체크리스트를 자동 주입하면 모든 프로젝트에서 맥락 로딩이 안정화됩니다.":
        "Auto-injecting the previous session's summary/checklist via a SessionStart hook stabilizes context loading across all projects.",
    "메모리 관리 — vm_stat 기반 시스템 메모리 + 상위 30 프로세스 + idle Claude Code 일괄 종료":
        "Memory management — vm_stat-based system memory + top 30 processes + bulk-kill idle Claude Code",
    "Claude Docs Hub — docs.anthropic.com 주요 페이지(Claude Code / API / ":
        "Claude Docs Hub — key docs.anthropic.com pages (Claude Code / API / ",
    "Prompt caching 은 반복되는 긴 컨텍스트(시스템 프롬프트, 도구 정의, 참조 문서)를 서버 측에 캐시해 ":
        "Prompt caching caches repeated long context (system prompts, tool definitions, reference docs) on the server side to ",
    "🦞 Ralph 루프 — Geoffrey Huntley의 'Ralph Wiggum' 패턴. 같은 PROMPT.md를 ":
        "🦞 Ralph loop — Geoffrey Huntley's 'Ralph Wiggum' pattern. The same PROMPT.md is ",
    "echo '# ANTHROPIC_API_KEY=sk-... 를 설정한 후: uv run python main.py'":
        "echo '# After setting ANTHROPIC_API_KEY=sk-...: uv run python main.py'",
    "[이미지 첨부됨 — claude-cli 는 vision 미지원, claude-api 또는 vision 모델 사용]":
        "[Image attached — claude-cli does not support vision; use claude-api or a vision model]",
    "출력 스타일 점검 — /output-style 명령 폐기(v2.1.91 제거, /config 로 대체) 진단 + ":
        "Output style check — diagnoses the deprecated /output-style command (removed in v2.1.91, replaced by /config) + ",
    "Agent SDK 스캐폴드 — claude-agent-sdk Python(uv) / TypeScript(bun) ":
        "Agent SDK scaffold — claude-agent-sdk Python(uv) / TypeScript(bun) ",
    "Claude CLI 로 최신 Anthropic 발표 조회 → 기존 카탈로그에 없는 항목만 dynamic 에 저장.":
        "Fetches the latest Anthropic announcements via the Claude CLI → saves only items missing from the existing catalog to dynamic.",
    "사용자의 Claude Code 를 위한 ~/.claude/settings.json 'hooks' 섹션을 만드세요.":
        "Create the ~/.claude/settings.json 'hooks' section for the user's Claude Code.",
    "모호한 요구사항을 Socratic 질문으로 명확화한 후 설계까지 (OMC /deep-interview 에 대응).":
        "Clarifies ambiguous requirements with Socratic questions, then proceeds through design (corresponds to OMC /deep-interview).",
    "Extended Thinking 실험실 — Opus/Sonnet 의 thinking block 을 분리 시각화. ":
        "Extended Thinking lab — visualizes Opus/Sonnet thinking blocks separately. ",
    "오케스트레이터 — Slack/Telegram/Discord 채널에 멘션하면 Claude(플래너)가 작업을 분해해 ":
        "Orchestrator — mention it in a Slack/Telegram/Discord channel and Claude (the planner) decomposes the task and ",
    "반복 작업(배포/마이그레이션/PR 만들기 등)을 스킬로 정의하면 Claude가 자동 활용. 다양성 축을 올립니다.":
        "Define repetitive tasks (deploys/migrations/creating PRs, etc.) as skills and Claude uses them automatically. Raises the diversity axis.",
    "고급: 사용자 정의 프록시로 아웃바운드 트래픽 라우팅(TLS 검사/필터링/로깅). 미설정이면 내장 프록시 사용.":
        "Advanced: route outbound traffic through a custom proxy (TLS inspection/filtering/logging). Uses the built-in proxy if unset.",
    "이미 활성화된 플러그인은 제외하고, candidates 안에서만 골라 최대 5개까지 우선순위 매겨 추천하세요. ":
        "Excluding already-enabled plugins, pick only from candidates and recommend up to 5, ranked by priority. ",
    "OpenClaw Gateway 외부 연동 (LazyClaude는 Event Forwarder 탭으로 부분 대체)":
        "OpenClaw Gateway external integration (LazyClaude partially replaces it with the Event Forwarder tab)",
    "사용자가 자주 호출하는 도구(top_tools)를 보고 어떤 MCP 가 워크플로우를 더 효율적으로 만들지 판단.":
        "Looks at the user's frequently called tools (top_tools) to determine which MCP would make the workflow more efficient.",
    "Anthropic 서버 측 URL 본문 fetch + citation. GA — beta header 불필요. ":
        "Anthropic server-side URL body fetch + citation. GA — no beta header required. ",
    "플러그인 마켓 — 설치된 마켓플레이스(.claude-plugin/marketplace.json)의 플러그인을 ":
        "Plugin Market — plugins from installed marketplaces (.claude-plugin/marketplace.json) ",
    "Doctor 진단 — 설치 무결성 (LazyClaude는 Security Scan + AI 평가 탭으로 대체)":
        "Doctor diagnostics — install integrity (LazyClaude replaces this with the Security Scan + AI evaluation tabs)",
    "Admin 사용량·비용 — Anthropic Admin Usage/Cost API 로 조직 단위 실제 청구된 ":
        "Admin usage·cost — organization-level actually billed data via the Anthropic Admin Usage/Cost API ",
    "이전 사이클 보고를 검토하고 미해결 항목과 새 리스크를 반영해 다음 단계 업무를 페르소나별로 다시 분배하세요.":
        "Review the previous cycle's report, factor in unresolved items and new risks, and redistribute next-phase tasks per persona.",
    "실시간 텔레메트리 — Claude Code 의 OpenTelemetry(OTLP/HTTP JSON) 메트릭을 ":
        "Real-time telemetry — Claude Code's OpenTelemetry(OTLP/HTTP JSON) metrics ",
    "AppleScript 로 Terminal 새 창에 cd + 명령 붙여넣기 (실제 실행은 사용자 Enter).":
        "Pastes cd + command into a new Terminal window via AppleScript (actual execution is the user's Enter).",
    "파이썬 dict 의 키 순서 보존은 어느 버전부터 공식 보증되는지, 그리고 왜 이전에는 안 됐는지 설명해줘.":
        "Explain from which version Python dict key-order preservation is officially guaranteed, and why it wasn't before.",
    "활성화하고 응답 블록(server_tool_use / *_tool_result / text)을 분류 시각화.":
        "enable it and visualize response blocks (server_tool_use / *_tool_result / text) by category.",
    "라이브 진행 SSE, iteration 비용 추적, CLI(tools/ralph_loop.py) 동시 지원.":
        "Live progress SSE, iteration cost tracking, and simultaneous CLI(tools/ralph_loop.py) support.",
    "모델은 이 스키마에 맞는 JSON 만 반환합니다. 후속 노드는 검증된 JSON 문자열을 입력으로 받습니다.":
        "The model returns only JSON matching this schema. Downstream nodes receive the validated JSON string as input.",
    "pluginKey ('<plugin>@<market>') → hooks.json 경로 (없으면 None).":
        "pluginKey ('<plugin>@<market>') → hooks.json path (None if absent).",
    "PDF는 서버에서 직접 생성하지 않습니다 (순수 stdlib 한계 — 바이너리 PDF 라이브러리 없음). ":
        "PDFs are not generated directly on the server (pure-stdlib limitation — no binary PDF library). ",
    "echo '# ANTHROPIC_API_KEY=sk-... 를 설정한 후: bun run index.ts'":
        "echo '# After setting ANTHROPIC_API_KEY=sk-...: bun run index.ts'",
    "- **데이터 출처**: `~/.claude-dashboard.db` sessions 인덱스 (읽기 전용)":
        "- **Data source**: `~/.claude-dashboard.db` sessions index (read-only)",
    "계획을 받아 각 모듈별 세부 요구사항·수용 조건(Acceptance Criteria)·테스트 포인트 작성":
        "Takes the plan and writes per-module detailed requirements·acceptance conditions (Acceptance Criteria)·test points",
    "claude-code-router·awesome-claude-code 등 인기 Claude 하네스 도구 ":
        "Popular Claude harness tools such as claude-code-router·awesome-claude-code ",
    "프로젝트별 추천 PROMPT.md 자동 생성 (CLAUDE.md + git log + TODO 합성). ":
        "Auto-generates a recommended per-project PROMPT.md (synthesized from CLAUDE.md + git log + TODO). ",
    "Extended Thinking 은 Haiku 에서 지원되지 않습니다. Opus 또는 Sonnet 사용.":
        "Extended Thinking is not supported on Haiku. Use Opus or Sonnet.",
    "frontmatter 의 `tools:` 필드를 list 로 — JSON 배열 또는 쉼표 구분 문자열.":
        "The frontmatter `tools:` field as a list — JSON array or comma-separated string.",
    "$hud — 현재 상태 1-2줄 요약 (phase · last action · next blocker)":
        "$hud — 1-2 line summary of current state (phase · last action · next blocker)",
    "프로젝트·모델별·상위 세션)를 Markdown + 자체완결형 인쇄용 HTML 로 내보낸다. 읽기 전용.":
        "by project·by model·top sessions) to Markdown + self-contained printable HTML. Read-only.",
    "MCP 서버 env 에 시크릿이 평문. 외부 env var 참조 또는 secret manager 사용.":
        "Secrets in plaintext in MCP server env. Use external env var references or a secret manager.",
    "Claude Code 규칙: ':*' 는 패턴 맨 끝에만 올 수 있음. 중간에 쓰려면 '*' 사용. ":
        "Claude Code rule: ':*' may only appear at the very end of a pattern. Use '*' for mid-pattern wildcards. ",
    "카테고리별(시스템 프롬프트·도구 정의·MCP 도구·CLAUDE.md/메모리·대화 기록·남은 공간)로 ":
        "by category (system prompt·tool definitions·MCP tools·CLAUDE.md/memory·conversation history·remaining space) ",
    "$doctor — 설치/헬스 진단 (의존성 · lockfile · env mismatch 체크리스트)":
        "$doctor — install/health diagnostics (dependencies · lockfile · env mismatch checklist)",
    "caveman-commit/compress/help/review/stats) 설치 상태·재설치·압축 ":
        "caveman-commit/compress/help/review/stats) install status·reinstall·compression ",
    "세션 사용량·비용에서 통계적으로 비정상적인 지점을 로컬에서 탐지합니다 (ML 없음, 요청 시 계산).":
        "Detects statistically anomalous points in session usage·cost locally (no ML, computed on demand).",
    "터미널에서 `claude auth login` 을 실행. 인터랙티브 명령이므로 터미널 앱을 열어준다.":
        "Runs `claude auth login` in the terminal. Opens a terminal app since it's an interactive command.",
    "v2.33.5 — timeout 5s → 2s (병렬 프로빙에서 한 도구가 5s 걸리면 전체 느림).":
        "v2.33.5 — timeout 5s → 2s (in parallel probing, one tool taking 5s slows everything down).",
    "Event Forwarder — Claude Code hooks 이벤트(PostToolUse 등)를 ":
        "Event Forwarder — Claude Code hooks events (PostToolUse, etc.) ",
    "공동 창업자에는 전 OpenAI 연구진 다수가 포함됐다. 회사의 플래그십 모델은 Claude 이며, ":
        "The co-founders include many former OpenAI researchers. The company's flagship model is Claude, ",
    "프롬프트에 URL 을 직접 포함해야 fetch 가능 (컨텍스트에 없는 URL 은 fetch 불가).":
        "URLs must be included directly in the prompt to be fetchable (URLs not in context cannot be fetched).",
    "Vision / PDF 실험실 — 이미지(PNG/JPG/WebP/GIF) 또는 PDF 를 업로드해 ":
        "Vision / PDF Lab — upload an image (PNG/JPG/WebP/GIF) or a PDF to ",
    "프롬프트 캐시 실험실 — Anthropic Messages API 의 cache_control 을 ":
        "Prompt Cache Lab — the Anthropic Messages API's cache_control ",
    "CHANGELOG.md 에서 최근 max_entries 개 릴리스 섹션만 반환. 챗봇 프롬프트 용.":
        "Returns only the latest max_entries release sections from CHANGELOG.md. For chatbot prompts.",
    "HTML/SVG 내 위험 요소 제거. img 는 허용 (img-src data: 로 CSP 제한).":
        "Removes dangerous elements from HTML/SVG. img is allowed (CSP restricted via img-src data:).",
    "macOS: 기본 Terminal.app 에서 cmd 실행. 그 외 플랫폼: Popen 백그라운드.":
        "macOS: runs cmd in the default Terminal.app. Other platforms: Popen in the background.",
    "stdlib 로 multipart/form-data POST. single field 'file'.":
        "multipart/form-data POST via stdlib. Single field 'file'.",
    "AI 프로바이더 — Claude/GPT/Gemini/Ollama/Codex 멀티 AI 오케스트라. ":
        "AI Providers — Claude/GPT/Gemini/Ollama/Codex multi-AI orchestra. ",
    "플러그인 자체는 Claude Code 에서 `/plugin uninstall ...` 로 별도 제거":
        "The plugin itself is removed separately in Claude Code via `/plugin uninstall ...`",
    "ollama CLI 가 설치되어 있지 않습니다. https://ollama.com 에서 설치하세요.":
        "The ollama CLI is not installed. Install it from https://ollama.com.",
    "채널별 fallback 체인 + 일일 예산 cap, 에이전트 간 라이브 보고(Agent Bus).":
        "Per-channel fallback chain + daily budget cap, live inter-agent reporting (Agent Bus).",
    "Anthropic 서버 측 웹 검색 + citation. GA — beta header 불필요. ":
        "Anthropic server-side web search + citation. GA — no beta header required. ",
    "체크포인트 — 세션별 프롬프트 단위 파일 스냅샷 타임라인. /rewind·Esc Esc 되감기가 ":
        "Checkpoints — per-prompt file snapshot timeline per session. /rewind·Esc Esc rewinding ",
    "이전 메시지를 덧붙이지 않고 수정하면 캐시가 깨진다. 예상 진단: messages_changed.":
        "Editing previous messages instead of appending breaks the cache. Expected diagnosis: messages_changed.",
    "훅 항목이 rtk 를 참조하는지 재귀 판별 (command 필드 포함 · 중첩 hooks 지원).":
        "Recursively determines whether a hook entry references rtk (including the command field · nested hooks supported).",
    "skill / prompt library / workflow template 으로 만드시겠습니까?":
        "Create it as a skill / prompt library / workflow template?",
    "신뢰할 수 없는 패키지면 임의 코드 실행 위험. github 레포의 signature 확인 권장.":
        "Untrusted packages risk arbitrary code execution. Verifying the github repo's signature is recommended.",
    "SQLite 세션 인덱스의 flat cache_creation_tokens 로는 분리 불가합니다.":
        "Cannot be separated using the flat cache_creation_tokens in the SQLite session index.",
    "기본 도구 3종 (get_weather / calculator / web_search mock).":
        "3 built-in tools (get_weather / calculator / web_search mock).",
    "추천 프로파일(혹은 임의 패치)을 현재 settings와 병합한 preview + diff 반환.":
        "Returns a preview + diff of the recommended profile (or an arbitrary patch) merged into the current settings.",
    "알림 webhook URL sanitize. Slack/Discord 화이트리스트 호스트만 허용.":
        "Sanitizes notification webhook URLs. Only Slack/Discord whitelisted hosts are allowed.",
    "Tool Use 플레이그라운드 — tool schema 정의 → Messages API 호출 → ":
        "Tool Use playground — define a tool schema → call the Messages API → ",
    "프로젝트의 모든 세션을 시간순으로 묶어 그래프 데이터로. 세션 단위 노드 + 도구·에이전트 요약.":
        "Groups all sessions of a project chronologically into graph data. Session-level nodes + tool·agent summary.",
    "Session Replay — Claude Code JSONL 세션 로그를 타임라인으로 재생 · ":
        "Session Replay — replay Claude Code JSONL session logs as a timeline · ",
    "Artifacts Viewer — 워크플로우 출력물(HTML/SVG/Markdown/JSON)을 ":
        "Artifacts Viewer — workflow outputs (HTML/SVG/Markdown/JSON) ",
    "구조화 출력은 Anthropic 모델에서만 스키마가 강제됩니다. 다른 프로바이더는 베스트에포트.":
        "Structured output schema enforcement applies only to Anthropic models. Other providers are best-effort.",
    "ANTHROPIC_API_KEY 미설정 — aiProviders 탭에서 저장하거나 환경변수 설정":
        "ANTHROPIC_API_KEY not set — save it in the aiProviders tab or set the environment variable",
    "에이전트에서 /caveman (lite·full·ultra·wenyan), Node ≥18 필요":
        "/caveman in agents (lite·full·ultra·wenyan), requires Node ≥18",
    "세션·코드 라인·커밋·PR·토큰·추정 비용을 기간별로 집계해 순위. 조직 admin 키 필요, ":
        "Ranks sessions·lines of code·commits·PRs·tokens·estimated cost aggregated by period. Requires an org admin key, ",
    "프롬프트 Eval — 어서션 기반 회귀 테스트. 테스트 셋(케이스+어서션)을 여러 프로바이더에 ":
        "Prompt Eval — assertion-based regression tests. Runs a test set (cases+assertions) against multiple providers ",
    "캐시 진단 — 두 연속 요청을 비교해 어느 캐시 브레이크포인트가 prompt-cache 히트를 ":
        "Cache diagnostics — compares two consecutive requests to see which cache breakpoint gets prompt-cache hits ",
    "tools 배열의 순서가 바뀌면 prefix 가 깨진다. 예상 진단: tools_changed.":
        "Reordering the tools array breaks the prefix. Expected diagnosis: tools_changed.",
    "복잡한 리뷰는 ecc:code-reviewer, ecc:security-reviewer 로 위임":
        "Delegate complex reviews to ecc:code-reviewer, ecc:security-reviewer",
    "모델 다운로드 진행 상태. GET /api/ollama/pull-status?pullId=...":
        "Model download progress. GET /api/ollama/pull-status?pullId=...",
    "Ollama 세 프로바이더에 돌려 cosine similarity + rank 매트릭스 비교. ":
        "Ollama — runs across the three providers and compares cosine similarity + rank matrices. ",
    "1시간 캐시(cache_control ttl='1h') 사용 시에만 cache_creation.":
        "cache_creation only when using the 1-hour cache (cache_control ttl='1h').",
    "대시보드 UI 용 — LazyClaude MCP 서버 진입점 스크립트 경로 + 노출 도구 목록.":
        "For the dashboard UI — LazyClaude MCP server entrypoint script path + list of exposed tools.",
    "절대 한도(limit)는 로컬 데이터에 없어 알 수 없음 · 사용량은 토큰 합계 기반 proxy":
        "Absolute limit is unknown (not in local data) · usage is a proxy based on token totals",
    "/autopilot — 요구사항 → 계획 → 실행 → 검증 단일 흐름 (bt-autopilot)":
        "/autopilot — requirements → plan → execute → verify in a single flow (bt-autopilot)",
    "레이트리밋 · 쿼터 — 롤링 5시간 윈도우 · 주간 쿼터 · 주간 Opus 윈도우의 리셋 시각/":
        "Rate limits · quotas — reset times of the rolling 5-hour window · weekly quota · weekly Opus window/",
    "이 스킬을 삭제할까요? <cwd>/.claude/skills/<id>/ 디렉터리가 제거됩니다.":
        "Delete this skill? The <cwd>/.claude/skills/<id>/ directory will be removed.",
    "추정값 (시스템 프롬프트 · 도구 정의 · MCP 도구는 트랜스크립트에 저장되지 않아 추정).":
        "Estimated values (system prompt · tool definitions · MCP tools are not stored in the transcript, so estimated).",
    "압축 커밋 메시지 생성 (Conventional Commits). /caveman-commit":
        "Generate compressed commit messages (Conventional Commits). /caveman-commit",
    "도달 시 알림을 기록·조회·해제. 지출은 세션 토큰을 cost_timeline 요금으로 추정.":
        "Record·view·dismiss alerts when reached. Spend is estimated from session tokens at cost_timeline rates.",
    "사용자의 ~/.claude/settings.json 'permissions' 를 최적화하세요.":
        "Optimize the user's ~/.claude/settings.json 'permissions'.",
    "_(승인 :white_check_mark: / 거부 :x: / 자유답장으로 다음 지시 입력)_":
        "_(approve :white_check_mark: / reject :x: / reply freely to enter the next instruction)_",
    "완료 후에는 (1) 무엇을 했는지 (2) 한계/막힌 지점 (3) 기획자에게 권하는 다음 단계를":
        "After completion, report (1) what was done (2) limitations/blockers (3) next steps recommended to the planner",
    "relpath 가 base 하위 경로인지 검증하고 실제 경로 반환. 바깥으로 나가면 None.":
        "Validates that relpath is under base and returns the real path. Returns None if it escapes.",
    "(팀 개발/리서치/병렬 3) + 커스텀 템플릿 저장·🖥️ Terminal 새 세션 spawn·":
        "(team dev/research/parallel 3) + save custom templates·🖥️ Terminal spawn new session·",
    "Ollama HTTP API (/api/generate) 로 실행 — 인터랙티브 문제 없음.":
        "Runs via the Ollama HTTP API (/api/generate) — no interactivity issues.",
    "근접도. ~/.claude 세션 로그에서 한도 메시지를 추출하는 best-effort 위젯.":
        "Proximity. A best-effort widget that extracts limit messages from ~/.claude session logs.",
    "Model Benchmark — 사전 정의 프롬프트 셋(기본 Q&A / 코드 / 추론) × ":
        "Model Benchmark — predefined prompt sets (basic Q&A / code / reasoning) × ",
    "시스템/도구/메시지 블록에 적용해 cache_creation / cache_read 토큰과 ":
        "applied to system/tool/message blocks to inspect cache_creation / cache_read tokens and ",
    "결과물이 요구사항을 만족하면 'PASS' 로 시작, 아니면 'FAIL — <이유>' 로 시작":
        "Start with 'PASS' if the output meets the requirements, otherwise start with 'FAIL — <reason>'",
    "이상 탐지 — 세션 사용량·비용의 통계적 이상치(일별 스파이크·프로젝트 급증·대형 세션)를 ":
        "Anomaly detection — statistical outliers in session usage·cost (daily spikes·project surges·large sessions) ",
    "Bash 샌드박스 — Bash 도구의 OS 수준 격리(파일·네트워크) 설정을 읽고 안전하게 ":
        "Bash sandbox — read the Bash tool's OS-level isolation (file·network) settings and safely ",
    "Batch API 관리 — 대용량 프롬프트 배치 제출·상태 폴링·결과 JSONL 다운로드. ":
        "Batch API management — submit large prompt batches·poll status·download result JSONL. ",
    "에이전트·스킬·명령·플러그인·훅·MCP 설정을 망라한 대형 Claude Code 툴킷 모음.":
        "A large Claude Code toolkit collection covering agents·skills·commands·plugins·hooks·MCP configs.",
    "settings.json이 올바른 JSON이 아닙니다. 손상 방지를 위해 저장을 거부합니다.":
        "settings.json is not valid JSON. Refusing to save to prevent corruption.",
    "cron 표현식이 현재 시각과 매칭되는지. 형식: min hour dom month dow.":
        "Whether the cron expression matches the current time. Format: min hour dom month dow.",
    "Agent SDK / Models / Account) 를 카테고리별 카드로 색인 + 검색. ":
        "Agent SDK / Models / Account) indexed + searchable as cards by category. ",
    "Files API — Anthropic 파일 업로드 · 목록 · 삭제 + 업로드한 파일을 ":
        "Files API — Anthropic file upload · list · delete + uploaded files ",
    "slack token not configured (see Wizard → Slack 설정)":
        "slack token not configured (see Wizard → Slack settings)",
    "터미널 status bar HUD (LazyClaude는 브라우저 대시보드 자체가 HUD)":
        "Terminal status bar HUD (in LazyClaude the browser dashboard itself is the HUD)",
    "OMC 의 Codex 버전 — Codex 세션 안에서 $ 키워드로 호출하는 워크플로우 도구":
        "The Codex version of OMC — a workflow tool invoked with the $ keyword inside a Codex session",
    "프롬프트 + cache_control 로 Messages API 호출 → usage 반환.":
        "Calls the Messages API with prompt + cache_control → returns usage.",
    "리포트 · 내보내기 — 기간별(7/30일) 사용량 리포트(토큰·추정 비용·일별 추이·상위 ":
        "Reports · export — usage reports by period (7/30 days) (tokens·estimated cost·daily trend·top ",
    "메모리 감사 — CLAUDE.md·프로젝트 메모리가 모든 대화에 주입하는 컨텍스트 부하를 ":
        "Memory audit — the context load that CLAUDE.md·project memory injects into every conversation ",
    "프로젝트 뼈대를 UI 로 생성. 템플릿 3종(basic/tool-use/memory) + ":
        "Generate a project skeleton via the UI. 3 templates (basic/tool-use/memory) + ",
    "잘못된 규칙을 자동 교정 — ':*' 가 중간이면 '*' 로 치환. 변경 내역 함께 반환.":
        "Auto-corrects invalid rules — replaces ':*' with '*' when it appears mid-string. Returns the change log as well.",
    "tool_use 블록 수신 시 tool_result 를 수동 입력해 멀티 턴 체인 실행. ":
        "When a tool_use block is received, manually enter the tool_result to run a multi-turn chain. ",
    "content 를 1줄 요약 문자열로. content 는 list[dict] 또는 str.":
        "Summarize content into a one-line string. content is list[dict] or str.",
    "컨텍스트 인스펙터 — 대시보드 자체 /context. 최신 턴의 컨텍스트 윈도우 점유율을 ":
        "Context Inspector — the dashboard's own /context. Shows the latest turn's context window occupancy ",
    "🧪 code_execution. Anthropic 서버가 직접 실행하는 도구를 체크박스로 ":
        "🧪 code_execution. Toggle tools executed directly on Anthropic servers via checkboxes ",
    "Embedding 비교 실험실 — 같은 쿼리/문서 집합을 Voyage / OpenAI / ":
        "Embedding comparison lab — run the same query/document set across Voyage / OpenAI / ",
    "macOS 전용. 샌드박스가 조회 가능한 XPC/Mach 서비스 이름. * 접미사 지원.":
        "macOS only. XPC/Mach service names the sandbox may look up. Supports * suffix.",
    "사용량 수치는 세션 토큰 합계 기반 근사치(proxy)입니다. 절대 한도(limit)는 ":
        "Usage figures are approximations (proxy) based on session token totals. The absolute limit is ",
    "Citations 플레이그라운드 — 문서를 제공하고 citations.enabled 로 ":
        "Citations playground — provide documents and use citations.enabled to ",
    "echo '📋 이전 세션 요약은 $HOME/.claude/session-data/ 참조'":
        "echo '📋 See $HOME/.claude/session-data/ for previous session summaries'",
    "오늘 — 오늘 하루 토큰·비용·세션·상위 프로젝트·최근 활동을 한 화면에 요약한 코크핏.":
        "Today — a cockpit summarizing today's tokens, cost, sessions, top projects, and recent activity on one screen.",
    "/ralph — verify → fix 루프 (bt-ralph, max 5 cycles)":
        "/ralph — verify → fix loop (bt-ralph, max 5 cycles)",
    "전체 셋업을 Claude 에게 평가받음. 비싸므로 force=true 시에만 새로 호출.":
        "Have Claude evaluate the full setup. Expensive, so only re-invoked when force=true.",
    "Claude Code 의 프로젝트 슬러그 규칙: '/' → '-', 선두에 '-' 추가.":
        "Claude Code's project slug rule: '/' → '-', with a leading '-' prepended.",
    "선택한 프롬프트로 start → session → output 3 노드 워크플로우 생성.":
        "Create a 3-node start → session → output workflow from the selected prompt.",
    "flat cache_creation_tokens 만 보존하므로 여기엔 포함되지 않습니다.":
        "Only flat cache_creation_tokens are preserved, so it is not included here.",
    "랩 히스토리 / API usage 객체 → 표준화된 토큰 dict + TTL split.":
        "Lab history / API usage object → normalized token dict + TTL split.",
    "ANTHROPIC_ADMIN_KEY 환경변수가 설정되어 있어 여기서 관리할 수 없습니다.":
        "The ANTHROPIC_ADMIN_KEY environment variable is set, so it cannot be managed here.",
    "Anthropic Messages API — claude CLI 없이 직접 API 호출.":
        "Anthropic Messages API — direct API calls without the claude CLI.",
    "5분 vs 1시간 TTL 분할 데이터가 없습니다. Anthropic usage 객체는 ":
        "No 5-minute vs 1-hour TTL split data. The Anthropic usage object ",
    "~/.claude.json 의 mcpServers 수를 합산 (프로젝트 스코프 포함).":
        "Sums the mcpServers count in ~/.claude.json (including project scope).",
    "워크플로우 버전 히스토리. GET /api/workflows/history?id=...":
        "Workflow version history. GET /api/workflows/history?id=...",
    "사용자가 새 마켓플레이스를 추가해야 하는 경우 marketplaceUrl 필드도 함께.":
        "If the user needs to add a new marketplace, include the marketplaceUrl field as well.",
    "이 스킬을 삭제할까요? ~/.claude/skills/<id>/ 디렉터리가 제거됩니다.":
        "Delete this skill? The ~/.claude/skills/<id>/ directory will be removed.",
    "MCP 탭의 카탈로그에서 Context7, GitHub, Memory 등 원클릭 설치.":
        "One-click install of Context7, GitHub, Memory, and more from the MCP tab catalog.",
    "공장 A 가 B 보다 2배 빠르다. A 가 단독으로 만드는 데 6시간이면 둘이 함께는?":
        "Factory A is twice as fast as B. If A takes 6 hours alone, how long do they take together?",
    "budget_tokens 슬라이더, 예시 3종(수학/디버깅/플래닝), 히스토리 20건.":
        "budget_tokens slider, 3 examples (math/debugging/planning), 20-entry history.",
    "candidates 안에서만 고르고, 이미 설치된 것(installed) 은 제외. ":
        "Choose only from candidates, excluding ones already installed. ",
    "편집(타임스탬프 백업 + 값 검증). settings.json 의 sandbox 키.":
        "Edit (timestamped backup + value validation). The sandbox key in settings.json.",
    "SSE 스트리밍 챗 — claude CLI stream-json 을 SSE 로 중계.":
        "SSE streaming chat — relays claude CLI stream-json over SSE.",
    "stdin 에서 newline-delimited JSON-RPC 메시지를 읽어 처리.":
        "Reads and processes newline-delimited JSON-RPC messages from stdin.",
    "Best-effort 설치 감지. None = 감지 불가(설치 불필요/즉시 실행형).":
        "Best-effort install detection. None = undetectable (no install needed / runs immediately).",
    "Claude 는 Anthropic 에서 만든 대규모 언어 모델이다. 그래서 뭘 잘해?":
        "Claude is a large language model made by Anthropic. So what is it good at?",
    "sandbox iframe + CSP + 정적 필터 4중 보안으로 안전하게 미리보기.":
        "Preview safely with quadruple security: sandbox iframe + CSP + static filters.",
    "OpenAI API — HTTP 직접 호출 (requests 미사용, urllib).":
        "OpenAI API — direct HTTP calls (no requests, uses urllib).",
    "cache_read 토큰을 1x input 단가로 청구했을 때 대비 절감액(USD).":
        "Savings (USD) compared to billing cache_read tokens at the 1x input rate.",
    "범위 내 세션 데이터가 없습니다. Claude Code 세션이 인덱싱되면 표시됩니다.":
        "No session data in range. It will appear once Claude Code sessions are indexed.",
    "CLAUDE.md · 프로젝트 메모리가 컨텍스트에 주입하는 부하를 측정 (읽기 전용)":
        "Measures the load CLAUDE.md and project memory inject into the context (read-only)",
    "deny 규칙 늘리면 안전도 ↑. 자주 쓰는 명령을 allow 해 승인 프롬프트 ↓.":
        "More deny rules → safety ↑. Allow frequently used commands → approval prompts ↓.",
    "Claude 공식 hosted tool 플레이그라운드 — 🌐 web_search + ":
        "Claude's official hosted tool playground — 🌐 web_search + ",
    "일·월 지출 한도(USD/토큰)를 소스별로 설정하고 임계치 도달 시 알림을 받습니다.":
        "Set daily/monthly spend limits (USD/tokens) per source and get alerts when thresholds are reached.",
    "TTL 분할은 1시간 캐시를 사용한 랩 호출의 usage.cache_creation ":
        "TTL split comes from usage.cache_creation of lab calls using the 1-hour cache ",
    "이번 세션 실제 토큰 사용·절감 통계 (세션 로그 기반). /caveman-stats":
        "Actual token usage and savings stats for this session (based on session logs). /caveman-stats",
    "워크플로우 — n8n 스타일 DAG 에디터. 세션 노드 생성·포트 드래그 연결·실행·":
        "Workflows — an n8n-style DAG editor. Create session nodes, drag-connect ports, run, ",
    "사용자의 작업 패턴에 맞는 Claude Code 플러그인 활성화/추가를 추천하세요. ":
        "Recommend Claude Code plugins to enable/add based on the user's work patterns. ",
    "소스별/모델별/일별 집계 + 최근 30건. Claude Code 내부 + 대시보드 ":
        "Aggregation by source/model/day + last 30 entries. Claude Code internal + dashboard ",
    "추정 비용은 Anthropic이 제공하는 추정치이며 실제 청구와 다를 수 있습니다.":
        "Estimated cost is an estimate provided by Anthropic and may differ from actual billing.",
    "추정. 총 사용량은 message.usage 실측, 정적 항목은 추정. 읽기 전용.":
        "Estimated. Total usage is measured from message.usage; static items are estimated. Read-only.",
    "오늘 AI 업계에서 주목할 만한 뉴스 3개를 요약해줘. 각 항목에 출처 링크 포함.":
        "Summarize 3 noteworthy AI industry news stories from today. Include a source link for each item.",
    "ECC marketplace · ECC plugin · CCB repo 설치 상태.":
        "ECC marketplace · ECC plugin · CCB repo installation status.",
    "allowedTools: * 는 모든 도구를 허용합니다. 필요한 도구만 나열하세요.":
        "allowedTools: * allows all tools. List only the tools you need.",
    "Claude API 는 Anthropic 의 고성능 LLM 접근 인터페이스입니다. ":
        "The Claude API is Anthropic's interface for accessing high-performance LLMs. ",
    "3명이 5분에 사과 3개를 먹는다. 10명이 사과 10개를 먹는 데 몇 분 걸리나?":
        "3 people eat 3 apples in 5 minutes. How many minutes does it take 10 people to eat 10 apples?",
    "세션 하네스(페르소나/허용 도구/resume)·🔁 Repeat 자동 반복·📋 템플릿":
        "Session harness (persona/allowed tools/resume)·🔁 Repeat auto-loop·📋 templates",
    "`code_execution_20250825` 는 모든 지원 모델에서 사용 가능. ":
        "`code_execution_20250825` is available on all supported models. ",
    "`.env` 파일을 읽어 현재 프로세스 환경 변수에 반영. 이미 설정된 키는 유지.":
        "Reads the `.env` file and applies it to the current process environment variables. Keys already set are kept.",
    "외부 OMX CLI를 추가로 설치하면 Codex 세션 안에서 $ 키워드로 호출 가능":
        "Installing the external OMX CLI additionally lets you invoke it with the $ keyword inside a Codex session",
    "Constitutional AI 접근법을 통해 유해 출력을 줄이는 방법을 연구한다.":
        "Researches how to reduce harmful outputs via the Constitutional AI approach.",
    "Ollama: 모델 허브(23종 카탈로그/다운로드/삭제), serve 자동 시작, ":
        "Ollama: model hub (catalog of 23 models/download/delete), auto-start serve, ",
    "Opus / Sonnet / Haiku 3 모델에 병렬 질문 → 응답 나란히 비교.":
        "Query the 3 models Opus / Sonnet / Haiku in parallel → compare responses side by side.",
    "명확화된 요구사항을 기반으로 기술 설계 문서 작성 (섹션: 목표/제약/아키/리스크)":
        "Write a technical design doc based on the clarified requirements (sections: goals/constraints/architecture/risks)",
    "Read/Grep/Edit 같은 도구를 적극 쓸수록 실제 작업이 일어났다는 신호.":
        "Heavy use of tools like Read/Grep/Edit signals that real work actually happened.",
    "비용 절감을 실측. 예시 3종(시스템/문서/도구) 원클릭 실행, 히스토리 20건.":
        "Measures actual cost savings. One-click run of 3 examples (system/docs/tools), 20-entry history.",
    "/ultrawork — 5 병렬 에이전트 → merge (bt-ultrawork)":
        "/ultrawork — 5 parallel agents → merge (bt-ultrawork)",
    "8개 빌트인 프로바이더 + 커스텀 무제한. API 키 설정, CLI 자동 감지, ":
        "8 built-in providers + unlimited custom ones. API key setup, CLI auto-detection, ",
    "| 시작 | 프로젝트 | 모델 | 토큰 | 추정 비용 | 점수 | 첫 프롬프트 |":
        "| Started | Project | Model | Tokens | Est. Cost | Score | First Prompt |",
    "Prompt Library — 자주 쓰는 프롬프트를 태그와 함께 저장/검색/복제/":
        "Prompt Library — keep frequently used prompts with tags; save/search/clone/",
    "전체 아키텍처 · 범위 · 리스크를 5섹션으로 설계 (목표/제약/접근/모듈/순서)":
        "Design overall architecture · scope · risks in 5 sections (goals/constraints/approach/modules/order)",
    "기본 채팅/임베딩 모델 설정. 비용 분석 차트, 사용량 알림, 멀티 AI 비교, ":
        "Set default chat/embedding models. Cost analysis charts, usage alerts, multi-AI comparison, ",
    "Anthropic 은 2021년 샌프란시스코에서 설립된 AI 안전 연구 회사다. ":
        "Anthropic is an AI safety research company founded in San Francisco in 2021. ",
    "Learner — 최근 세션 JSONL 에서 반복되는 tool 시퀀스·프롬프트를 ":
        "Learner — extracts recurring tool sequences·prompts from recent session JSONL ",
    "Messages API 호출. (status_code, json_body) 반환.":
        "Calls the Messages API. Returns (status_code, json_body).",
    "1부터 100 까지 소수의 합을 계산해서 보여줘. Python 으로 직접 계산해.":
        "Compute and show the sum of primes from 1 to 100. Calculate it directly with Python.",
    "Anthropic은 주간/5시간 쿼터의 실시간 잔량 API를 제공하지 않습니다. ":
        "Anthropic does not provide a real-time remaining-quota API for the weekly/5-hour quotas. ",
    "모든 프로바이더 health check 병렬 실행 — 포트/엔드포인트 정보 포함.":
        "Run health checks for all providers in parallel — includes port/endpoint info.",
    "경로가 사용자 홈 디렉터리 아래인지 (symlink traversal 차단용).":
        "Whether the path is under the user's home directory (to block symlink traversal).",
    "Kubernetes 의 Deployment 와 StatefulSet 의 차이는?":
        "What is the difference between a Deployment and a StatefulSet in Kubernetes?",
    "~/.claude.json 이 없습니다 — Claude Code에 로그인하세요.":
        "~/.claude.json not found — log in to Claude Code.",
    "σ 배수가 낮을수록 더 민감하게 탐지합니다. 변경 후 자동으로 다시 계산됩니다.":
        "A lower σ multiplier makes detection more sensitive. Recalculated automatically after changes.",
    "상대 시간 문자열 — '3초 전', '5분 전', '2시간 전', '1일 전'.":
        "Relative time string — '3 seconds ago', '5 minutes ago', '2 hours ago', '1 day ago'.",
    "Claude 응답에서 recommendations JSON 을 찾지 못했습니다.":
        "Could not find recommendations JSON in the Claude response.",
    "프로젝트 상태 + 점수 약점을 보고 '이 파일을 이렇게 추가/편집하세요' 추천.":
        "Looks at project state + score weaknesses and recommends 'add/edit this file like this'.",
    "환경 변수 설정: envConfig 탭에서 ANTHROPIC_MODEL 등 수정":
        "Set environment variables: edit ANTHROPIC_MODEL etc. in the envConfig tab",
    "동일 프롬프트를 Claude, GPT, Gemini에 동시 전송하여 결과 비교":
        "Send the same prompt to Claude, GPT, and Gemini simultaneously and compare results",
    "settings.json이 올바른 JSON이 아닙니다. 저장이 비활성화됩니다.":
        "settings.json is not valid JSON. Saving is disabled.",
    "macOS 전용. 샌드박스 명령이 localhost 포트에 바인딩하도록 허용.":
        "macOS only. Allows sandboxed commands to bind to localhost ports.",
    "객체에서만 제공됩니다 (Anthropic 공식). SQLite 세션 인덱스는 ":
        "is only provided in the object (official Anthropic). The SQLite session index ",
    "settings.json 내용 반환. 파일 없거나 파싱 실패 시 빈 dict.":
        "Returns settings.json contents. Empty dict if the file is missing or parsing fails.",
    "존재 여부·읽기 실패를 흡수하고 빈 문자열 반환. 필요 시 앞 N 문자 제한.":
        "Absorbs missing-file·read failures and returns an empty string. Optionally limited to the first N characters.",
    "토큰/USD 를 가져와 로컬 추정치와 drift 비교 (admin 키 필요).":
        "Fetches tokens/USD and compares drift against local estimates (admin key required).",
    "예: 'Bash(curl:* | sh)' → 'Bash(curl* | sh)'":
        "e.g. 'Bash(curl:* | sh)' → 'Bash(curl* | sh)'",
    "문자열 경로를 절대화하고 ~/ 하위면 abs path 반환, 아니면 None.":
        "Absolutizes a string path; returns the abs path if under ~/, otherwise None.",
    "`---` 블록을 key/value dict 로. 파싱 불가 시 빈 dict.":
        "Parses the `---` block into a key/value dict. Empty dict if unparsable.",
    "이 마켓플레이스의 매니페스트가 로컬에 캐시되어 있지 않습니다. 새로고침하세요.":
        "This marketplace's manifest is not cached locally. Please refresh.",
    "교차 실행하고 저장된 베이스라인과 비교해 회귀(이전 통과→현재 실패)를 강조.":
        "Cross-runs and compares against the saved baseline, highlighting regressions (previously passing→now failing).",
    "하네스 도구 — caveman(출력 토큰 압축)·ccusage(사용량 분석)·":
        "Harness tools — caveman(output token compression)·ccusage(usage analytics)·",
    "압축 코드리뷰 코멘트 (위치·문제·수정 한 줄). /caveman-review":
        "Compressed code review comments (location·problem·fix in one line). /caveman-review",
    "→ 워크플로우 탭 헤더의 Quick Actions 또는 런 센터의 OMC 카드":
        "→ Quick Actions in the workflow tab header, or the OMC card in the Run Center",
    "SessionStart 훅 추가 (~/.claude/settings.json)":
        "Add a SessionStart hook (~/.claude/settings.json)",
    "Claude Code 플러그인 설치: 마켓플레이스 URL 추가 → toggle":
        "Install Claude Code plugins: add a marketplace URL → toggle",
    "claude auth login 이 실행되었습니다. 완료 후 새로고침하세요.":
        "claude auth login has been launched. Refresh after it completes.",
    "글로벌 CLAUDE.md는 모든 프로젝트의 모든 대화에 주입되며, 프로젝트 ":
        "The global CLAUDE.md is injected into every conversation in every project, while project ",
    "이전 검증에서 FAIL 로 판정된 항목을 해결하도록 수정 방향을 제시하세요.":
        "Suggest fixes that resolve the items judged FAIL in the previous verification.",
    "워크플로우 완료 시 호출. 설정된 채널만 전송. 실패해도 예외 발생 안 함.":
        "Called when a workflow completes. Sends only to configured channels. Never raises on failure.",
    "‘인쇄용 HTML 열기’ 후 브라우저의 인쇄 → PDF로 저장을 사용하세요.":
        "After ‘Open print HTML’, use the browser's Print → Save as PDF.",
    "Reliability — Auto-Resume · 자동 복구 · 바인딩 관리":
        "Reliability — Auto-Resume · auto recovery · binding management",
    "버전 + CHANGELOG 로딩 — 프론트 사이드바, 챗봇 프롬프트가 공유.":
        "Loads version + CHANGELOG — shared by the frontend sidebar and the chatbot prompt.",
    "JSONL 파일 최근 50건 — (경로, 크기, mtime, 줄 수 근사).":
        "Latest 50 JSONL files — (path, size, mtime, approximate line count).",
    "ANTHROPIC_API_KEY 미설정 — aiProviders 탭에서 저장":
        "ANTHROPIC_API_KEY not set — save it in the aiProviders tab",
    "이벤트 훅 (PreToolUse / PostToolUse / Stop …).":
        "Event hooks (PreToolUse / PostToolUse / Stop …).",
    "원자적 쓰기 — tmp 파일에 쓰고 rename. 부모 디렉토리 자동 생성.":
        "Atomic write — write to a tmp file then rename. Parent directories are created automatically.",
    "의도된 호출이면 노드 설정에서 'allowInternal: true' 체크.":
        "If the call is intentional, check 'allowInternal: true' in the node settings.",
    "DAG 검증. cycle 이 있으면 설명 리스트 반환, 없으면 빈 리스트.":
        "Validates the DAG. Returns a list of descriptions if there is a cycle, otherwise an empty list.",
    "이전 Fix 결과를 반영해 Exec 단계에서 실패 항목을 우선 처리하세요.":
        "Apply the previous Fix results and prioritize failed items in the Exec stage.",
    "환경 변수에 경로가 설정되어 있으면 확장·절대화해서 반환, 아니면 기본값.":
        "If a path is set in the env var, expands and absolutizes it before returning; otherwise the default.",
    "estTokens는 문자수/4 추정치 (영어 기준 휴리스틱). 한국어 등 ":
        "estTokens is a chars/4 estimate (an English-based heuristic). For Korean and other ",
    "Slack 어드민 승인 → Obsidian 기록 → 다음 사이클로 루프. ":
        "Slack admin approval → Obsidian logging → loop to the next cycle. ",
    "카탈로그. 저장소·설치 명령을 보고 Terminal 에서 바로 설치·실행.":
        "Catalog. View the repo and install command, then install and run right from the Terminal.",
    "두 요청의 prefix 가 일치합니다 (append-only 또는 동일).":
        "The two requests' prefixes match (append-only or identical).",
    "특정 JSONL 파싱 — query 는 relative path 를 받음.":
        "Parses a specific JSONL — query takes a relative path.",
    "SQL 로 user 테이블의 id, email 을 email 기준 정렬.":
        "Sort the user table's id, email by email using SQL.",
    "tool 정의를 캐시하면 같은 tools 세트를 반복 호출할 때 재활용.":
        "Caching tool definitions lets repeated calls with the same tools set reuse them.",
    "npx ccusage / bunx ccusage — 기본은 일자별 리포트":
        "npx ccusage / bunx ccusage — daily report by default",
    "Claude Code 도구·IDE 통합·프레임워크·리소스 큐레이션 목록.":
        "A curated list of Claude Code tools, IDE integrations, frameworks, and resources.",
    "커스텀 프로바이더 임베딩 — embedCommand 가 설정된 경우에만.":
        "Custom provider embeddings — only when embedCommand is set.",
    "이 회사의 핵심 특징과 투자 내역을 불릿 3개로 요약해줘. 인용을 활용.":
        "Summarize this company's key traits and funding history in 3 bullets. Use citations.",
    "결과물이 요구사항을 만족하는지 검증 — PASS/FAIL 과 근거 리포트":
        "Verify the output meets the requirements — PASS/FAIL with a rationale report",
    "수신해 비용·토큰·도구 수락/거절·코드 라인·커밋·세션을 실시간 집계. ":
        "Receives them and aggregates cost, tokens, tool accept/reject, code lines, commits, and sessions in real time. ",
    "mDNSResponder/identitysd 등 시스템 노이즈 표시 토글":
        "Toggle showing system noise such as mDNSResponder/identitysd",
    "query 먼저, docs N 개 embed. 실패하면 error 반환.":
        "query first, then embed N docs. Returns error on failure.",
    "캐시 hit 과 write 의 비용 차이, 그리고 최소 크기를 정리해줘.":
        "Summarize the cost difference between cache hits and writes, plus the minimum size.",
    "`#`/`##`/`###` 헤더 기준으로 섹션 분리 — 에디터 프리뷰용.":
        "Splits sections by `#`/`##`/`###` headers — for the editor preview.",
    "정확한 인용 span 이 포함된 답변을 받아 원문 하이라이트로 시각화. ":
        "Gets answers with exact citation spans and visualizes them as highlights in the source text. ",
    "예시 2종 (Q&A 10건 / 요약 5건), 최대 1000건/batch.":
        "2 example sets (10 Q&A / 5 summaries), up to 1000 items/batch.",
    "OAuth 계정 없음 — `claude auth login` 실행 필요.":
        "No OAuth account — run `claude auth login`.",
    "정적 검사해 시크릿 노출·위험 훅·과도한 권한·신뢰 불가 MCP 감지. ":
        "Statically scans to detect exposed secrets, risky hooks, excessive permissions, and untrusted MCP. ",
    "터미널에서 로그인 창이 열렸습니다. 브라우저 인증 완료 후 돌아오세요.":
        "A login prompt opened in the terminal. Come back after completing browser authentication.",
    "uvx 자동 설치는 PyPI 에서 패키지를 받습니다. 신뢰 범위 확인.":
        "uvx auto-install downloads packages from PyPI. Verify your trust boundary.",
    "caveman 모드·스킬·명령 레퍼런스 카드. /caveman-help":
        "Reference card for caveman modes, skills, and commands. /caveman-help",
    "기획자가 전달한 지시 블록 중 본인 역할에 해당하는 부분만 수행하세요.":
        "From the planner's instruction blocks, execute only the part matching your role.",
    "각 페르소나별 지시 블록을 '### <role>' 헤딩으로 구분하세요.":
        "Separate each persona's instruction block with a '### <role>' heading.",
    "빌트인 신기능 + 사용자가 '최신 정보 로딩' 으로 발견한 동적 항목.":
        "Built-in new features + dynamic items the user discovered via 'Load latest info'.",
    "마켓플레이스 매니페스트가 캐시되어 있지 않습니다 — 먼저 새로고침하세요":
        "Marketplace manifest is not cached — refresh first",
    "워크플로우를 백그라운드 스레드로 실행 시작. runId 를 즉시 반환.":
        "Starts running the workflow on a background thread. Returns the runId immediately.",
    "Claude Design export 를 저장하는 추가 디렉토리 등록.":
        "Register an extra directory for storing Claude Design exports.",
    "VERSION 파일에서 현재 버전 문자열 반환. 없으면 '0.0.0'.":
        "Returns the current version string from the VERSION file, or '0.0.0' if missing.",
    "토큰 1개 획득. 가능하면 True, 타임아웃 내 불가하면 False.":
        "Acquire one token. True if available, False if not within the timeout.",
    "prompt 길이(char) / 4 를 input 토큰 근사치로 사용.":
        "Uses prompt length(char) / 4 as an approximation of input tokens.",
    "기획자(Planner) → 페르소나 3명 병렬 작업 → 보고 취합 → ":
        "Planner → 3 personas working in parallel → consolidate reports → ",
    "PreCommit — 시크릿 패턴 (sk-, ghp_, AKIA) 감지":
        "PreCommit — detect secret patterns (sk-, ghp_, AKIA)",
    "ISO 8601 문자열을 epoch ms 로. 파싱 실패 시 None.":
        "ISO 8601 string to epoch ms. None on parse failure.",
    "모델 상세 정보. GET /api/ollama/info?name=...":
        "Model details. GET /api/ollama/info?name=...",
    "Gemini CLI (gemini) — Google 의 CLI 도구.":
        "Gemini CLI (gemini) — Google's CLI tool.",
    "이전 사이클의 보고를 검토하고, 미해결 항목과 새로 발견된 리스크를 ":
        "Review the previous cycle's report, and factor unresolved items and newly discovered risks ",
    "자동 추출 → Prompt Library / 워크플로우 템플릿 제안.":
        "Auto-extract → suggest Prompt Library / workflow templates.",
    "세션 안에서 충분히 대화를 이어가면 맥락이 누적되어 품질이 오릅니다.":
        "Continuing the conversation within a session accumulates context and improves quality.",
    "설치된 마켓플레이스의 모든 plugins 리스트 + 설치/활성 상태.":
        "List all plugins from installed marketplaces + install/enable status.",
    "긴 문서를 user 메시지로 첨부하고 캐시 → 추가 질문 시 재사용.":
        "Attach a long document as a user message and cache it → reuse for follow-up questions.",
    "최근 run 중 output 이 있는 것들을 meta 리스트로 반환.":
        "Return recent runs that have output as a meta list.",
    "외부 HTTP endpoint 로 포워딩. 호스트 화이트리스트 적용.":
        "Forward to an external HTTP endpoint. Host whitelist enforced.",
    "멀티바이트 문자는 실제 토큰이 더 많을 수 있어 보수적 하한입니다. ":
        "Multibyte characters may use more actual tokens, so this is a conservative lower bound. ",
    "리셋 시각은 로컬 세션 로그의 한도 도달 메시지에서 추출한 값이며, ":
        "The reset time is extracted from the limit-reached message in local session logs, ",
    "서울의 현재 기온을 get_weather 로 확인하고 한 줄로 요약.":
        "Check Seoul's current temperature with get_weather and summarize in one line.",
    "caveman 스위트 설치 상태 + 컴포넌트별 감지 + 사용 가이드.":
        "caveman suite install status + per-component detection + usage guide.",
    "선택한 모델들을 교차 실행 → 모델별 평균 지연·토큰·비용 집계 + ":
        "Cross-run the selected models → aggregate per-model average latency, tokens, and cost + ",
    "Playground — Claude API 실험 12종 + 프로바이더":
        "Playground — 12 Claude API experiments + providers",
    "turn2 캐시 READ 0 — 캐시 미스(브레이크포인트가 깨짐).":
        "turn2 cache READ 0 — cache miss (breakpoint broken).",
    "Claude CLI 시간 초과 (240초) — 다시 시도해 주세요.":
        "Claude CLI timed out (240s) — please try again.",
    "PRD 의 모듈 1/3 담당 — 코드/문서 결과물과 실행 결과 보고":
        "Owns module 1/3 of the PRD — reports code/doc deliverables and execution results",
    "macOS Finder 에서 CCB 디렉터리 열기 (보너스 편의).":
        "Open the CCB directory in macOS Finder (bonus convenience).",
    "프로바이더 사용 가능 여부 (CLI 설치됨 / API 키 설정됨).":
        "Provider availability (CLI installed / API key configured).",
    "💾 백업 & 복원 — 워크플로우/AR/AI 키/설정 스냅샷 + 복원":
        "💾 Backup & Restore — workflow/AR/AI key/settings snapshot + restore",
    "이미 종료된 세션이라도 강제로 바인딩 — 재개 시 새 세션이 시작됨":
        "Force-bind even an already-ended session — resuming starts a new session",
    "JS 렌더링 사이트 미지원. 추가 비용 없음 (표준 토큰 비용만).":
        "JS-rendered sites not supported. No extra cost (standard token cost only).",
    "~/.claude/projects/*/*.jsonl 전부 재인덱스.":
        "Re-index all ~/.claude/projects/*/*.jsonl.",
    "🔄 Auto-Resume 관리 — 활성 바인딩 리스트 + 일괄 취소":
        "🔄 Auto-Resume management — active binding list + bulk cancel",
    "자주 쓰는 Bash 명령을 allow에 pattern으로 미리 등록":
        "Pre-register frequently used Bash commands as patterns in allow",
    "WebFetch/WebSearch 허용해서 최신 정보 참조 가능하게":
        "Allow WebFetch/WebSearch so the latest information can be referenced",
    "세션 행 리스트 → 평균 5축 점수. 짧은 세션(도구<기준) 제외.":
        "Session row list → average 5-axis score. Excludes short sessions (tools < threshold).",
    "SOCKS 프록시 포트 (network.socksProxyPort)":
        "SOCKS proxy port (network.socksProxyPort)",
    "PRD 의 모듈 2/3 담당 — 코드/문서 결과물과 실행 결과 보고":
        "Owns module 2/3 of the PRD — reports code/doc deliverables and execution results",
    "워크플로우 생성: workflows 탭 → 새 워크플로우 + 템플릿":
        "Create a workflow: workflows tab → new workflow + templates",
    "프로바이더 레지스트리 싱글턴. 첫 호출 시 빌트인 프로바이더 등록.":
        "Provider registry singleton. Registers built-in providers on first call.",
    "PRD 의 모듈 3/3 담당 — 코드/문서 결과물과 실행 결과 보고":
        "Owns module 3/3 of the PRD — reports code/doc deliverables and execution results",
    "파이썬 3.13 은 GIL 비활성화 옵션을 제공한다. 의미가 뭐야?":
        "Python 3.13 offers an option to disable the GIL. What does that mean?",
    "macOS 전용. 샌드박스가 접근 가능한 Unix 소켓 경로 목록.":
        "macOS only. List of Unix socket paths the sandbox can access.",
    "매우 단순한 Markdown → HTML (외부 라이브러리 없음).":
        "Very simple Markdown → HTML (no external libraries).",
    "반복 실행 설정 sanitize. enabled 기본 False.":
        "Sanitize repeat-run settings. enabled defaults to False.",
    "레거시 — 시도 횟수 캡 (시간 데드라인보다 먼저 적중하면 발동)":
        "Legacy — attempt count cap (fires if hit before the time deadline)",
    "메시지에 document 로 reference 해서 질문 테스트.":
        "Test asking questions by referencing it as a document in the message.",
    "~/.claude/output-styles/<id>.md 로 저장":
        "Save as ~/.claude/output-styles/<id>.md",
    "둘러보고 설치 상태 확인 + 설치 명령 안내 (Discover).":
        "Browse, check install status + show install commands (Discover).",
    "| 모델 | 세션 | 입력 | 출력 | 총 토큰 | 추정 비용 |":
        "| Model | Sessions | Input | Output | Total tokens | Est. cost |",
    "권한 allow 목록을 늘려 매 도구 호출마다 승인 프롬프트 제거":
        "Expand the permission allow list to remove approval prompts on every tool call",
    "텍스트 임베딩 생성. 지원하지 않는 프로바이더는 기본 에러 반환.":
        "Generate text embeddings. Unsupported providers return an error by default.",
    "PATH 기반 탐지 → 실패 시 통상 설치 경로 fallback.":
        "PATH-based detection → fallback to common install paths on failure.",
    "우선순위에 반영해 다음 단계 업무를 페르소나별로 다시 분배하세요.":
        "into the priorities, then redistribute next-phase tasks per persona.",
    "hosted tool 활성화 상태로 Messages API 호출.":
        "Call the Messages API with the hosted tool enabled.",
    "UI 테스트 버튼용 — 지정된 채널에 test 메시지 1건 전송.":
        "For the UI test button — sends one test message to the specified channel.",
    "프로젝트 전용 에이전트(.claude/agents/*.md) 추가":
        "Add project-scoped agents (.claude/agents/*.md)",
    "세션의 토큰 사용량 분해 — 도구별 / 서브에이전트별 / 시간순.":
        "Session tokens usage breakdown — by tool / by subagent / over time.",
    "위험한 명령을 deny 목록에 등록 (rm -rf, sudo 등)":
        "Register dangerous commands in the deny list (rm -rf, sudo, etc.)",
    "질문에 대해 합리적인 기본값/권장 답변을 제시하고 각각 근거 표기":
        "Suggest sensible defaults/recommended answers for each question, with rationale noted for each",
    "조직/워크스페이스/팀 정보 (claude.ai team 기능용).":
        "Organization/workspace/team info (for claude.ai team features).",
    "Claude 워크플로우 커스터마이즈용 스킬·리소스 큐레이션 목록.":
        "Curated list of skills and resources for customizing Claude workflows.",
    "위임을 더 활용해보세요 — 정의된 에이전트가 30일간 적게 호출됨":
        "Try delegating more — defined agents were rarely invoked over the last 30 days",
    "Claude CLI 가 설치되어 있지 않습니다. 먼저 설치하세요.":
        "Claude CLI is not installed. Install it first.",
    "빌드/테스트 훅을 PostToolUse에 연결해 조기 실패 감지":
        "Attach build/test hooks to PostToolUse for early failure detection",
    "API 키 저장: aiProviders 탭에서 저장-key 버튼":
        "Save API key: use the save-key button in the aiProviders tab",
    "base / modified 모두 messages 가 필요합니다":
        "Both base and modified require messages",
    "HTTP 프록시 포트 (network.httpProxyPort)":
        "HTTP proxy port (network.httpProxyPort)",
    "설치된 첫 번째 chat 모델 반환 (embedding 제외).":
        "Return the first installed chat model (excluding embedding).",
    "도구 오류 없이 깔끔하게 실행될수록 높음. 오류 1회당 -4점.":
        "Higher when execution is clean with no tool errors. -4 points per error.",
    "현재 임계값 기준으로 사용량과 비용이 평소 범위 안에 있습니다.":
        "Usage and cost are within the normal range based on current thresholds.",
    "정적 보안 스캔 실행. 이슈 리스트 + 카테고리별 카운트 반환.":
        "Run static security scan. Returns issue list + per-category counts.",
    "추가 쓰기 허용 경로 (filesystem.allowWrite)":
        "Additional write-allowed paths (filesystem.allowWrite)",
    "서브에이전트에게 위임하면 메인 컨텍스트를 절약하고 병렬화 가능.":
        "Delegating to subagents saves main context and enables parallelization.",
    "플래닝 → 실행 → 리뷰 3-라운드 대화를 한 세션에서 끝내기":
        "Finish the planning → execution → review 3-round conversation in one session",
    "`~/.claude/settings.json` 전체 레퍼런스.":
        "Full reference for `~/.claude/settings.json`.",
    "비용 타임라인 통합 — 모든 플레이그라운드/워크플로우 비용을 ":
        "Unified cost timeline — all playground/workflow costs ",
    "settings.json 의 enabledPlugins 토글.":
        "Toggle enabledPlugins in settings.json.",
    "60초 간격으로 cron 매칭 검사 + 워크플로우 자동 실행.":
        "Check cron matches every 60 seconds + auto-run workflows.",
    "챗봇 API — 사용자 질문을 받아 대시보드 안내 답변 반환.":
        "Chatbot API — takes user questions and returns dashboard guidance answers.",
    "대형 시스템 프롬프트를 캐시해 동일 대화 반복 시 비용 절감.":
        "Cache large system prompts to cut costs on repeated conversations.",
    "플러그인 에이전트는 마켓플레이스에서 관리 — 삭제는 비활성화로":
        "Plugin agents are managed in the marketplace — delete by disabling",
    "(rtk-ai/rtk) 를 한 탭에서 설치·활성화·통계 조회.":
        "Install, enable, and view stats for (rtk-ai/rtk) in one tab.",
    "CLAUDE.md에 '작업 시작 전 요구사항 확인' 지침 추가":
        "Add a 'confirm requirements before starting work' directive to CLAUDE.md",
    "Config — 훅 · 권한 · MCP · 플러그인 · 설정":
        "Config — hooks · permissions · MCP · plugins · settings",
    "Wizard 탭에서 폼만 채우면 더 쉽게 만들 수 있습니다.":
        "You can build it more easily by just filling out the form in the Wizard tab.",
    "요구사항에서 모호한 부분을 찾아 3~5개의 구체적 질문 생성":
        "Find ambiguous parts of the requirements and generate 3-5 specific questions",
    "Ollama 시작 중... 잠시 후 연결을 다시 확인하세요.":
        "Starting Ollama... check the connection again shortly.",
    "usage dict → 비용 상세 (캐시 절감 계산 포함).":
        "usage dict → cost details (including cache savings calculation).",
    "폴백 체인 편집, 연결 테스트, 프로바이더 헬스 대시보드. ":
        "Edit fallback chain, test connections, provider health dashboard. ",
    "Delay 노드 — 지정 시간 대기 후 입력을 그대로 통과.":
        "Delay node — waits the specified time, then passes input through unchanged.",
    "측정·플래그하고 로드 경계 초과 파일을 표시 (읽기 전용).":
        "Measure, flag, and mark files exceeding the load boundary (read-only).",
    "특정 capability 를 가진 프로바이더 + 모델 목록.":
        "List of providers + models with a specific capability.",
    "CLAUDE.md는 해당 프로젝트의 모든 대화에 주입됩니다.":
        "CLAUDE.md is injected into every conversation in that project.",
    "BAAI 다국어 임베딩. 1024 dims. 한국어 우수.":
        "BAAI multilingual embedding. 1024 dims. Strong for Korean.",
    "사용자 작업 패턴에 맞는 MCP 서버 추가를 추천하세요. ":
        "Recommend adding MCP servers that match the user's work patterns. ",
    "읽기 재허용 경로 (filesystem.allowRead)":
        "Re-allowed read paths (filesystem.allowRead)",
    "이전 노드의 session_id 수집 (resume 용).":
        "Collect the previous node's session_id (for resume).",
    "요구사항을 받아 실행 계획 수립 — 단계별 체크리스트 생성":
        "Take requirements and build an execution plan — generate a step-by-step checklist",
    "감지된 Ollama 호스트를 프로바이더 레지스트리에 반영.":
        "Apply the detected Ollama host to the provider registry.",
    "파일 백업이 디스크에 존재하여 /rewind 로 복원 가능":
        "File backup exists on disk, restorable via /rewind",
    "n8n 워크플로 수정 시 mcp__n8n-mcp 우선 사용":
        "Prefer mcp__n8n-mcp when editing n8n workflows",
    "API 데이터 수집 → 변환 → AI 분석 → 리포트 생성":
        "Collect API data → transform → AI analysis → generate report",
    "LazyClaude에 흡수된 4 모드 (별도 설치 불필요)":
        "4 modes absorbed into LazyClaude (no separate install required)",
    "한 도구에만 의존하지 않고 올바른 도구를 골라 쓰는 패턴.":
        "A pattern of picking the right tool rather than relying on a single one.",
    "복잡한 수식 단계를 thinking block 으로 확인.":
        "Verify complex formula steps via thinking block.",
    "워크플로우 embedding 노드에서 호출하는 편의 함수.":
        "Convenience function called by the workflow embedding node.",
    "Claude Code 세션 내부에서 직접 슬래시 명령 호출":
        "Invoke slash commands directly inside a Claude Code session",
    "외부 툴/가이드 카탈로그 + 베스트 프랙티스 + 치트시트.":
        "External tool/guide catalog + best practices + cheat sheets.",
    "repeat 설정에 따라 iteration 을 반복 실행.":
        "Run iterations repeatedly according to the repeat setting.",
    "~/.claude/settings.json 이 없습니다.":
        "~/.claude/settings.json does not exist.",
    "JavaScript 로 debounce 함수를 작성해줘.":
        "Write a debounce function in JavaScript.",
    "scores[i] 에 대응하는 rank (1=가장 큼).":
        "Rank corresponding to scores[i] (1 = largest).",
    "REST 와 GraphQL 중 CRUD 에 적합한 것은?":
        "Between REST and GraphQL, which is better suited for CRUD?",
    "Anthropic cache-diagnosis 베타 사용":
        "Use the Anthropic cache-diagnosis beta",
    "파이썬으로 1~N 까지 더하는 함수를 5줄 이내로 써줘.":
        "Write a Python function that sums 1 to N in 5 lines or fewer.",
    "이 프로바이더가 특정 capability 를 지원하는지.":
        "Whether this provider supports a given capability.",
    "0.1 + 0.2 == 0.3 이 false 인 이유는?":
        "Why is 0.1 + 0.2 == 0.3 false?",
    "지출은 세션 토큰 × cost_timeline 요금 추정":
        "Spend is estimated as session tokens × cost_timeline rates",
    "데이터는 약 1시간 지연되며 오늘은 집계에서 제외됩니다.":
        "Data is delayed by about 1 hour; today is excluded from aggregation.",
    "최근 30일치 사용 패턴 → 품질 가중치 계산용 데이터.":
        "Last 30 days of usage patterns → data for computing quality weights.",
    "코드는 ```로 감싸고 설명은 3줄 이내로 요약합니다. ":
        "Wrap code in ``` and keep explanations to 3 lines or fewer. ",
    "쓰기 금지 경로 (filesystem.denyWrite)":
        "Write-denied paths (filesystem.denyWrite)",
    "현재 설정된 Event Forwarder 훅 목록 반환.":
        "Return the list of currently configured Event Forwarder hooks.",
    "로그아웃 — `claude auth logout` 실행.":
        "Log out — runs `claude auth logout`.",
    "레벨(lite·full·ultra·wenyan) 가이드.":
        "Level guide (lite·full·ultra·wenyan).",
    "Google Gemini API — HTTP 직접 호출.":
        "Google Gemini API — direct HTTP calls.",
    "CLAUDE.md 가 100자 이상 내용을 담고 있으면 ":
        "If CLAUDE.md contains 100 or more characters ",
    "서버 시작 시 호출 — 스케줄러 백그라운드 스레드 시작.":
        "Called at server startup — starts the scheduler background thread.",
    "Ollama 기본 채팅 모델 + 임베딩 모델 설정 조회.":
        "Get the Ollama default chat model + embedding model settings.",
    "Learn — 신기능 · 온보딩 · 공식 문서 · 가이드":
        "Learn — new features · onboarding · official docs · guides",
    "세션별 프롬프트 단위 파일 스냅샷 타임라인 (읽기 전용)":
        "Per-session, per-prompt file snapshot timeline (read-only)",
    "대시보드가 관리하는 Ollama 프로세스가 이미 실행 중":
        "The dashboard-managed Ollama process is already running",
    "허용 도메인 (network.allowedDomains)":
        "Allowed domains (network.allowedDomains)",
    "직접 편집된 파일 없음 (bash 변경은 추적되지 않음)":
        "No directly edited files (bash changes are not tracked)",
    "읽기 금지 경로 (filesystem.denyRead)":
        "Read-denied paths (filesystem.denyRead)",
    "연결 설정 — Claude Code 텔레메트리 내보내기":
        "Connection settings — Claude Code telemetry export",
    "cache_control 로 반복 프롬프트 비용 절감.":
        "Cut costs on repeated prompts with cache_control.",
    "settings.json.permissions 에 병합":
        "Merge into settings.json.permissions",
    "프로젝트 목표를 단계별 작업으로 쪼개고 페르소나에 분배":
        "Break project goals into step-by-step tasks and assign them to personas",
    "$wiki — 작업 컨텍스트를 1페이지 레퍼런스로 요약":
        "$wiki — summarize the work context into a 1-page reference",
    "파일 로드. 없거나 파싱 실패 시 빈 store 반환.":
        "Load the file. Returns an empty store if missing or parsing fails.",
    "Terminal 새 창에서 초기화 명령 자동 붙여넣기.":
        "Auto-paste the init command into a new Terminal window.",
    "여러 모델에 병렬 분배하고 결과를 합쳐 채널에 회신. ":
        "Fan out to multiple models in parallel, then merge results and reply to the channel. ",
    "플레이그라운드 10종 + 워크플로우 비용을 한 화면에.":
        "10 playgrounds + workflow costs on a single screen.",
    "LazyClaude 흡수 기능만 쓰려면 (설치 불필요)":
        "To use only the LazyClaude absorbed features (no install required)",
    "Claude Code CLI 가 설치되어 있지 않습니다":
        "Claude Code CLI is not installed",
    "규칙이 유효하면 None, 잘못이면 에러 메시지 반환.":
        "Returns None if the rule is valid, or an error message if invalid.",
    "카탈로그 + 도구별 설치 상태 + 카테고리 라벨 반환.":
        "Returns the catalog + per-tool install status + category labels.",
    "Model Context Protocol 커넥터 설정.":
        "Model Context Protocol connector settings.",
    "Opus / Sonnet / Haiku 세대별 비교.":
        "Opus / Sonnet / Haiku comparison by generation.",
    "활성·비활성 모든 마켓플레이스 플러그인의 스킬 수집.":
        "Collect skills from all marketplace plugins, active and inactive.",
    "프로바이더 설정 파일 로드. 없으면 기본 구조 반환.":
        "Load the provider config file. Returns the default structure if missing.",
    "로컬 ollama 모델을 시도해보세요 (비용 $0).":
        "Try a local ollama model (cost $0).",
    "Claude CLI 시간 초과 — 다시 시도해 주세요":
        "Claude CLI timed out — please try again",
    "프롬프트 첫 60자 정규화 — 공백 축약 + 소문자.":
        "Normalize the first 60 characters of the prompt — collapse whitespace + lowercase.",
    "UI 초기화용 — 이벤트 타입 + 허용 호스트 목록.":
        "For UI initialization — event types + allowed host list.",
    "초경량 임베딩. 384 dims. 빠른 프로토타이핑.":
        "Ultra-lightweight embeddings. 384 dims. Fast prototyping.",
    "프로바이더별 요청 빈도 제한 (토큰 버킷 알고리즘).":
        "Per-provider request rate limiting (token bucket algorithm).",
    "실패한 항목만 선택적으로 수정. 변경점과 근거 명시.":
        "Selectively fix only failed items. State changes and rationale.",
    "챗봇 시스템 프롬프트에 삽입할 탭 목록 문자열 생성.":
        "Generate the tab list string to insert into the chatbot system prompt.",
    "피드백이 있으면 반영해 수정, 없으면 초기 작업 수행":
        "Apply feedback and revise if present, otherwise perform the initial task",
    "설치 버튼은 큐레이션된 명령만 터미널에서 실행합니다.":
        "The install button runs only curated commands in the terminal.",
    "settings.json.statusLine 덮어쓰기":
        "Overwrite settings.json.statusLine",
    "Anthropic 서버 측 hosted 검색 도구.":
        "Anthropic server-side hosted search tool.",
    "프로세스 시작 시 한 번 호출. 중복 호출은 무시.":
        "Called once at process start. Duplicate calls are ignored.",
    "공식 요금표 (per-million-tokens).":
        "Official pricing table (per-million-tokens).",
    "폐기 진단 · 마이그레이션 어드바이저 (읽기 전용)":
        "Deprecation diagnostics · migration advisor (read-only)",
    "Claude Code 가이드 (한국어 · 위키독스)":
        "Claude Code guide (Korean · Wikidocs)",
    "이 세션에는 디스크에 저장된 체크포인트가 없습니다.":
        "This session has no checkpoints saved on disk.",
    "turn2 에서 캐시 READ 발생 — 히트 성공.":
        "Cache READ occurred at turn2 — hit succeeded.",
    "문서 임베딩 → 검색 → AI 응답 생성 파이프라인":
        "Document embedding → search → AI response generation pipeline",
    "PATH + 통상 설치 경로 fallback 탐지.":
        "Detection via PATH + common install path fallback.",
    "파일 업로드 + document reference.":
        "File upload + document reference.",
    ">캐시 읽기 / 생성</div><div class=":
        ">Cache read / creation</div><div class=",
    "API 키 + 추가 설정(baseUrl 등) 저장.":
        "Save API key + additional settings (baseUrl, etc.).",
    "OpenAI Codex CLI — 코드 생성 특화.":
        "OpenAI Codex CLI — specialized for code generation.",
    "Meta의 오픈소스 LLM. 범용 대화·코드·추론.":
        "Meta's open-source LLM. General-purpose chat·code·reasoning.",
    "검색: security, design, lsp...":
        "Search: security, design, lsp...",
    "`rtk session` — 현재 세션 사용 내역.":
        "`rtk session` — current session usage history.",
    "사이클 없다고 가정. Kahn's 결과 순서 반환.":
        "Assumes no cycles. Returns Kahn's result order.",
    "web_fetch 로 URL 본문을 가져와 요약. ":
        "Fetch the URL body via web_fetch and summarize. ",
    "이미 등록된 이름입니다 — 다른 이름으로 시도하세요":
        "Name already registered — try a different name",
    "터미널에서 마켓플레이스를 추가하면 여기에 나타납니다":
        "Marketplaces added from the terminal appear here",
    "격리 제외 명령 (excludedCommands)":
        "Commands excluded from isolation (excludedCommands)",
    "비샌드박스 재시도 허용 (escape hatch)":
        "Allow non-sandboxed retry (escape hatch)",
    "타임아웃 — 관리자 응답을 받지 못해 흐름 중단.":
        "Timeout — flow stopped because no manager response was received.",
    "설치된 Ollama 모델 목록 + 카탈로그 매칭.":
        "Installed Ollama model list + catalog matching.",
    "Wizard로 생성된 페르소나 크루 워크플로우. ":
        "Persona crew workflow generated by the Wizard. ",
    "MCP 서버 추가해서 사용 가능한 도구 범위 확장":
        "Add MCP servers to expand the range of available tools",
    "프로젝트 settings.local.json 보강":
        "Augment project settings.local.json",
    "file-history 저장소가 존재하지 않습니다":
        "file-history store does not exist",
    "file://, ftp:// 등은 보안상 차단됨.":
        "file://, ftp://, etc. are blocked for security.",
    "Transform 노드 — 텍스트/JSON 변환.":
        "Transform node — text/JSON transformation.",
    "탭 설명을 요청 언어로 반환. 없으면 한글 기본.":
        "Return tab descriptions in the requested language. Defaults to Korean if missing.",
    "Claude 응답에서 JSON 을 찾지 못했습니다":
        "No JSON found in the Claude response",
    "min(25, floor(도구호출수 × 1.2))":
        "min(25, floor(tool calls × 1.2))",
    "LazyClaude에 흡수된 4 명령 (런 센터)":
        "4 commands absorbed into LazyClaude (Run Center)",
    "matcher 없이 모든 도구 호출에 적용됩니다.":
        "Without a matcher, it applies to all tool calls.",
    "단일 cron 필드가 현재 값과 매칭되는지 확인.":
        "Check whether a single cron field matches the current value.",
    "계획에 따라 작업 수행 — 코드/문서 결과물 출력":
        "Perform the task per the plan — output code/document deliverables",
    "이 시스템 프롬프트는 테스트용 고정 블록입니다. ":
        "This system prompt is a fixed block for testing. ",
    "Observe — 비용 · 메트릭 · 시스템 관측":
        "Observe — costs · metrics · system observation",
    "Build — 워크플로우 · 에이전트 · 프롬프트":
        "Build — workflows · agents · prompts",
    "노드의 입력 텍스트 수집 (이전 노드 결과에서).":
        "Collect the node's input text (from previous node results).",
    "관리형 allowRead만 허용 (managed)":
        "Allow managed allowRead only (managed)",
    "omx hud --watch 터미널 라이브 갱신":
        "omx hud --watch live terminal refresh",
    "플러그인 스킬은 편집 불가 (read-only)":
        "Plugin skills are not editable (read-only)",
    "CLI 설치 · 기본 사용 · 프로젝트 초기화.":
        "CLI installation · basic usage · project initialization.",
    "MixedBread 임베딩. 1024 dims.":
        "MixedBread embeddings. 1024 dims.",
    "출력 스타일 점검 데이터를 불러오지 못했습니다.":
        "Failed to load output style inspection data.",
    "커스텀 CLI 프로바이더 인스턴스 리스트 반환.":
        "Returns the list of custom CLI provider instances.",
    "| 프로젝트 | 세션 | 토큰 | 추정 비용 |":
        "| Project | Sessions | Tokens | Est. cost |",
    "키워드로 웹을 검색하고 상위 5건을 반환합니다.":
        "Searches the web by keyword and returns the top 5 results.",
    "임베딩 프로바이더가 반환하는 통일된 응답 형식.":
        "Unified response format returned by embedding providers.",
    "Llama 3.1 대형 모델. 높은 추론 능력.":
        "Llama 3.1 large model. Strong reasoning capability.",
    "키워드 → 탭 id 매핑을 자연어 지시로 반환.":
        "Returns keyword → tab id mappings as natural-language instructions.",
    "실행 중인 ollama serve 가 없습니다.":
        "No running ollama serve instance.",
    "아키텍처 결정 과정을 thinking 에 노출.":
        "Expose the architecture decision process in thinking.",
    "특정 capability 를 가진 모델만 필터.":
        "Filter to models with a specific capability.",
    "id 는 소문자/숫자/-/_ 만 (2~41자)":
        "id allows lowercase/digits/-/_ only (2~41 chars)",
    "OpenAI Embeddings API 호출.":
        "Calls the OpenAI Embeddings API.",
    "팝업이 차단되었습니다 — 팝업을 허용해 주세요":
        "Popup blocked — please allow popups",
    "Mistral AI 범용 모델. 빠르고 정확.":
        "Mistral AI general-purpose model. Fast and accurate.",
    "Ollama HTTP API로 모델 pull.":
        "Pull models via the Ollama HTTP API.",
    "`rtk gain` — 누적 토큰 절감 통계.":
        "`rtk gain` — cumulative token savings stats.",
    "프로젝트별 서브에이전트 정의 · 역할 프리셋.":
        "Per-project subagent definitions · role presets.",
    "프로바이더 설정 위자드(초보자 3단계 가이드)":
        "Provider setup wizard (3-step beginner guide)",
    "모든 프로바이더가 반환하는 통일된 응답 형식.":
        "Unified response format returned by all providers.",
    "대화 이력 수정 (append-only 위반)":
        "Modifying conversation history (append-only violation)",
    "provider:model 형식으로 입력하세요":
        "Enter in provider:model format",
    "로컬에서 탐지 (ML 없음, 요청 시 계산).":
        "Detected locally (no ML, computed on request).",
    "Snowflake 임베딩. 1024 dims.":
        "Snowflake embeddings. 1024 dims.",
    "당신은 Claude 대시보드의 도우미입니다. ":
        "You are the Claude dashboard assistant. ",
    "Codex 세션 내부에서 $ 키워드 직접 호출":
        "Invoke $ keywords directly inside a Codex session",
    "이 프로젝트만 비정상적으로 비용이 늘었습니다.":
        "Only this project's cost increased abnormally.",
    "검색당 $10/1,000 + 표준 토큰 비용.":
        "$10/1,000 searches + standard token costs.",
    "개별 응답 매트릭스. 결과 JSON 다운로드.":
        "Per-response matrix. Download results as JSON.",
    "claude CLI가 설치되어 있지 않습니다.":
        "claude CLI is not installed.",
    "버그 분석 과정 · 가설 검증 과정을 시각화.":
        "Visualize the bug analysis · hypothesis verification process.",
    "세션 하나에서 지표 추출. 실패 시 빈 결과.":
        "Extract metrics from a single session. Empty result on failure.",
    "📜 실행 이력·🎬 14장면 인터랙티브 튜토리얼":
        "📜 Run history·🎬 14-scene interactive tutorial",
    ">입력 / 출력</div><div class=":
        ">Input / Output</div><div class=",
    "모든 AI 프로바이더의 추상 베이스 클래스.":
        "Abstract base class for all AI providers.",
    "이 프로젝트 맥락에서 왜 필요한지 2~3문장":
        "2~3 sentences on why it's needed in this project's context",
    "모델 카탈로그 — 내장 목록 + 설치 상태.":
        "Model catalog — built-in list + install status.",
    "localhost 바인딩 허용 (macOS)":
        "Allow localhost binding (macOS)",
    "| 날짜 | 세션 | 토큰 | 추정 비용 |":
        "| Date | Sessions | Tokens | Est. cost |",
    "캐시 토큰 델타 (turn1 → turn2)":
        "Cache token delta (turn1 → turn2)",
    "Python 의 GIL 을 1문장으로 설명.":
        "Explain Python's GIL in one sentence.",
    "Finder 열기 + Documents 클릭":
        "Open Finder + click Documents",
    "SessionEnd — 상태/요약 자동 저장":
        "SessionEnd — auto-save state/summary",
    "allow / deny 규칙 · 권한 정책.":
        "allow / deny rules · permission policy.",
    "min(25, floor(메시지수 / 4))":
        "min(25, floor(message count / 4))",
    "문서의 핵심 주장을 2문장으로 요약해주세요.":
        "Summarize the document's key claims in two sentences.",
    "ts(초) → YYYY-MM-DD 별 합산.":
        "ts (seconds) → aggregated by YYYY-MM-DD.",
    "Claude 구독 활성 (세부 플랜 미지정)":
        "Claude subscription active (plan not specified)",
    "예시 2종 (회사 소개문 / 기술 아티클).":
        "2 examples (company intro / tech article).",
    "frontmatter 를 제거한 본문 반환.":
        "Returns the body with frontmatter removed.",
    "CORS preflight 는 언제 발생해?":
        "When does a CORS preflight occur?",
    "/autopilot 다음 작업 자동 실행해줘":
        "/autopilot run the next task automatically",
    "캐시 무시하고 강제 조회 (분당 1회 권장)":
        "Force fetch, bypassing cache (recommended once per minute)",
    "레지스트리 재초기화 (설정 변경 후 호출).":
        "Reinitialize the registry (call after config changes).",
    "settings.json을 읽을 수 없습니다":
        "Cannot read settings.json",
    "Nomic 텍스트 임베딩. 768 dims.":
        "Nomic text embeddings. 768 dims.",
    "고급: 사용자 정의 SOCKS 프록시 포트.":
        "Advanced: custom SOCKS proxy port.",
    "설정 파일 저장 (atomic write).":
        "Save config file (atomic write).",
    "키 없으면 오프라인 구조 diff 로 폴백.":
        "Falls back to offline structural diff if no key.",
    "settings.json.hooks 에 병합":
        "Merge into settings.json.hooks",
    "설치 명령은 공식 문서에서 검증된 형식입니다":
        "Install commands follow the format verified in official docs",
    "오늘 하루 Claude Code 활동 한눈에":
        "Today's Claude Code activity at a glance",
    "사용자 레벨 출력 스타일 파일이 없습니다.":
        "No user-level output style files found.",
    "유효하지 않은 플러그인/마켓플레이스 식별자":
        "Invalid plugin/marketplace identifier",
    "Claude CLI 시간 초과 (240초)":
        "Claude CLI timed out (240s)",
    "CLAUDE.md 로 프로젝트 지식 고정.":
        "Pin project knowledge with CLAUDE.md.",
    "탐색 작업은 Explore 에이전트로 위임":
        "Delegate exploration tasks to the Explore agent",
    "이번 실행을 새 베이스라인으로 저장했습니다":
        "Saved this run as the new baseline",
    "복사 실패 — 미리보기에서 직접 선택하세요":
        "Copy failed — select directly in the preview",
    "부팅 시 호출 — 변경된 세션만 재인덱싱.":
        "Called at boot — reindexes only changed sessions.",
    "플러그인 마켓플레이스 · 설치 · 활성화.":
        "Plugin marketplace · install · enable.",
    "워크플로우 노드 실행 비용을 DB에 기록.":
        "Records workflow node execution costs to the DB.",
    "사용 패턴에서 발견한 흥미로운 점 2-3개":
        "2-3 interesting findings from usage patterns",
    ">추정 비용</div><div class=":
        ">Estimated cost</div><div class=",
    "해당 플러그인이 이 마켓플레이스에 없습니다":
        "That plugin is not in this marketplace",
    "min(15, Agent툴_호출수 × 3)":
        "min(15, Agent_tool_calls × 3)",
    "동시 수정 감지 — 새로고침 후 다시 시도":
        "Concurrent edit detected — refresh and try again",
    "Google DeepMind 오픈 모델.":
        "Google DeepMind open model.",
    "_해당 기간에 기록된 세션이 없습니다._":
        "_No sessions recorded in this period._",
    "프로바이더별 rank 차이를 하이라이트.":
        "Highlights rank differences per provider.",
    "벡터 DB 가 RAG 에 쓰이는 이유는?":
        "Why are vector DBs used for RAG?",
    ">총 토큰</div><div class=":
        ">Total tokens</div><div class=",
    "툴 호출 하이라이트 · 누적 토큰 차트.":
        "Tool call highlights · cumulative tokens chart.",
    "대시보드 서버를 어떻게 다시 시작하나요?":
        "How do I restart the dashboard server?",
    "재사용 가능한 스킬 생성 · 호출 규칙.":
        "Reusable skill creation · invocation rules.",
    "Markdown을 클립보드에 복사했습니다":
        "Copied Markdown to clipboard",
    "이 테스트 셋과 베이스라인을 삭제할까요?":
        "Delete this test set and baseline?",
    "로컬 데이터에 없어 표시할 수 없습니다.":
        "Not in local data — cannot display.",
    "기간을 선택하고 리포트 생성을 누르세요.":
        "Select a period and click Generate Report.",
    "Claude CLI 를 찾을 수 없습니다":
        "Claude CLI not found",
    "환경별 의존성을 CLAUDE.md에 명시":
        "Document per-environment dependencies in CLAUDE.md",
    "`/` 명령 구조 · 커스텀 명령 등록.":
        "`/` command structure · custom command registration.",
    "min(15, 사용된_고유도구수 × 2)":
        "min(15, unique_tools_used × 2)",
    "당신은 여러 도구를 잘 쓰는 비서입니다.":
        "You are an assistant skilled at using multiple tools.",
    "단일 노드 실행 (병렬 워커에서 호출).":
        "Execute a single node (called from parallel workers).",
    "이상 탐지 계산 중 오류가 발생했습니다.":
        "An error occurred while computing anomaly detection.",
    "위임 프롬프트를 CLAUDE.md에 추가":
        "Add delegation prompts to CLAUDE.md",
    "각 카드는 관련 대시보드 탭으로도 연결.":
        "Each card also links to its related dashboard tab.",
    "`approve`/`reject` 답장_":
        "`approve`/`reject` reply_",
    "10개 질문을 Haiku 로 병렬 처리.":
        "Process 10 questions in parallel with Haiku.",
    "오늘의 핵심 개념을 한 줄로 요약해줘.":
        "Summarize today's key concept in one line.",
    "Microsoft 소형 모델. 효율적.":
        "Microsoft small model. Efficient.",
    "마이그레이션 어드바이저 (읽기 전용).":
        "Migration advisor (read-only).",
    "마켓플레이스 정보를 불러오지 못했습니다":
        "Failed to load marketplace info",
    "Ollama API가 응답하는지 확인.":
        "Check whether the Ollama API responds.",
    "Alibaba Qwen. 다국어 강점.":
        "Alibaba Qwen. Strong at multilingual.",
    "이 기간에 기록된 팀 활동이 없습니다.":
        "No team activity recorded in this period.",
    "Voyage AI 기반 임베딩 API.":
        "Embedding API powered by Voyage AI.",
    "ANTHROPIC_API_KEY 미설정":
        "ANTHROPIC_API_KEY not set",
    "Claude Code 세션 안에서 사용":
        "Use inside a Claude Code session",
    "되감기(rewind)는 어떻게 동작하나":
        "How does rewind work",
    "출력 스타일 기능은 폐기되지 않았습니다":
        "The output styles feature is not deprecated",
    "Claude 계정 연결이 필요합니다: ":
        "Claude account connection required: ",
    "스크린샷만 (planning only)":
        "Screenshots only (planning only)",
    "ollama serve 프로세스 종료.":
        "Kill the ollama serve process.",
    "경계를 초과하는 메모리 파일이 없습니다":
        "No memory files exceed the boundary",
    "도시 이름으로 날씨 조회 (mock).":
        "Look up weather by city name (mock).",
    "Fast mode 기본 · legacy":
        "Fast mode default · legacy",
    "수정 요청 (modified · 턴2)":
        "Revision request (modified · turn 2)",
    "HTTP API 로 설치된 모델 조회.":
        "List installed models via the HTTP API.",
    "보안 검사 → 코드 리뷰 → 결과 취합":
        "Security check → code review → aggregate results",
    "작업의 1/5 담당 — 섹션 A 처리":
        "Handles 1/5 of the work — processes section A",
    "(설정 없음 — Default 사용)":
        "(No config — using Default)",
    "Mistral MoE. 전문가 혼합.":
        "Mistral MoE. Mixture of experts.",
    "빌트인 에이전트는 삭제할 수 없습니다":
        "Built-in agents cannot be deleted",
    "도시의 현재 기온을 섭씨로 반환한다.":
        "Returns the city's current temperature in Celsius.",
    "에러 시 자동 재시도 + 실패 핸들링":
        "Auto retry on error + failure handling",
    "RTK 설정 파일 경로 (OS 별).":
        "RTK config file path (per OS).",
    "작업의 3/5 담당 — 섹션 C 처리":
        "Handles 3/5 of the work — processes section C",
    "작업의 2/5 담당 — 섹션 B 처리":
        "Handles 2/5 of the work — processes section B",
    "Claude 계정 연결이 필요합니다.":
        "Claude account connection required.",
    "인쇄용 HTML을 생성하지 못했습니다":
        "Failed to generate printable HTML",
    "특정 도시의 현재 날씨를 조회합니다.":
        "Looks up the current weather for a given city.",
    "워크스페이스 · 멤버 · 결제 관리.":
        "Manage workspace · members · billing.",
    "작업의 4/5 담당 — 섹션 D 처리":
        "Handles 4/5 of the work — processes section D",
    "워크플로우로 변환. 시드 3종 포함.":
        "Convert to a workflow. Includes 3 seeds.",
    "레이트리밋 상태를 불러오지 못했습니다":
        "Failed to load rate limit status",
    "백업 생성 실패 — 저장을 중단합니다":
        "Backup creation failed — aborting save",
    "이름은 영숫자/밑줄/하이픈 2~64자":
        "Name must be 2~64 alphanumeric/underscore/hyphen characters",
    "타임아웃 — 자율 판단으로 계속 진행":
        "Timeout — continuing autonomously",
    "max(0, 20 - 오류수 × 4)":
        "max(0, 20 - errors × 4)",
    ">세션</div><div class=":
        ">Session</div><div class=",
    "빌트인 프로바이더 — 다른 id 사용":
        "Built-in provider — use a different id",
    "작업의 5/5 담당 — 섹션 E 처리":
        "Handles 5/5 of the work — processes section E",
    "다단계 작업 — 파일 닫고 새로 열기":
        "Multi-step task — close the file and reopen",
    "단일 프로바이더의 API 키 저장.":
        "Save a single provider's API key.",
    "settings.json 쓰기 실패":
        "Failed to write settings.json",
    "이번 실행을 새 베이스라인으로 저장":
        "Save this run as the new baseline",
    "워크플로우 프로바이더별 비용 집계.":
        "Cost aggregation per workflow provider.",
    "TCP 와 UDP 의 핵심 차이는?":
        "What are the key differences between TCP and UDP?",
    "prompts 최대 1000 건까지":
        "Up to 1000 prompts",
    "ollama serve 현재 상태.":
        "Current status of ollama serve.",
    "API 키 없음 — 권위 진단 아님":
        "No API key — not an authoritative diagnosis",
    "Admin 키가 설정되지 않았습니다":
        "Admin key is not configured",
    "디렉토리가 아님 또는 존재하지 않음":
        "Not a directory or does not exist",
    "허용 Mach 서비스 (macOS)":
        "Allowed Mach services (macOS)",
    "name 과 modelfile 필수":
        "name and modelfile are required",
    "Qwen 2.5 대형. 코드+추론.":
        "Qwen 2.5 large. Code+reasoning.",
    "시스템 프롬프트에 타임스탬프 주입":
        "Inject timestamp into system prompt",
    "터미널에서 다음 명령을 실행합니다":
        "Run the following command in your terminal",
    "스케줄이 설정된 워크플로우 목록.":
        "List of workflows with schedules configured.",
    "DeepSeek 추론 특화 모델.":
        "DeepSeek reasoning-focused model.",
    "오늘 요약을 불러오지 못했습니다.":
        "Failed to load today's summary.",
    "외부 OMC CLI 설치 (선택)":
        "Install external OMC CLI (optional)",
    "아직 수신된 텔레메트리가 없습니다":
        "No telemetry received yet",
    "Admin 사용량 탭에서 키 설정":
        "Set the key in the Admin usage tab",
    "외부 OMX CLI 설치 (선택)":
        "Install external OMX CLI (optional)",
    "각기 다른 짧은 문단 5개 요약.":
        "Summarize 5 different short paragraphs.",
    "AI 호출 없음, 로컬 휴리스틱.":
        "No AI calls, local heuristics.",
    "실패 시 시도할 프로바이더 순서.":
        "Provider order to try on failure.",
    "수식을 계산해 결과를 반환합니다.":
        "Evaluates an expression and returns the result.",
    "출력 스타일 기능이 폐기되었습니다":
        "The output styles feature has been deprecated",
    "스캔된 프로젝트 메모리가 없습니다":
        "No scanned project memories",
    "프로바이더를 1개 이상 선택하세요":
        "Select at least 1 provider",
    "하단 상태라인 · 컨텍스트 표시.":
        "Bottom status line · context display.",
    "→ 런 센터에서 OMX 카드 클릭":
        "→ Click the OMX card in the Run Center",
    "전체 워크플로우 실행 통계 집계.":
        "Aggregate execution stats across all workflows.",
    "플러그인 훅 파일을 찾을 수 없음":
        "Plugin hook file not found",
    "이름은 영숫자/-/_/. 만 허용":
        "Name allows only alphanumeric/-/_/.",
    "이상 징후가 발견되지 않았습니다.":
        "No anomalies detected.",
    "허용 Unix 소켓 (macOS)":
        "Allowed Unix sockets (macOS)",
    "복사 실패 — 수동으로 선택하세요":
        "Copy failed — select manually",
    "VOYAGE_API_KEY 미설정":
        "VOYAGE_API_KEY not set",
    "번역 JSON 을 찾지 못했습니다":
        "Translation JSON not found",
    "조직 Admin 키가 필요합니다":
        "Organization Admin key required",
    "프로젝트 CLAUDE.md 생성":
        "Create project CLAUDE.md",
    "기준 요청 (base · 턴1)":
        "Baseline request (base · turn 1)",
    "마켓플레이스를 찾을 수 없습니다":
        "Marketplace not found",
    "<공식 문서 또는 발표 URL>":
        "<official docs or announcement URL>",
    "컨텍스트를 불러오지 못했습니다.":
        "Failed to load context.",
    "체크포인트를 불러오지 못했습니다":
        "Failed to load checkpoints",
    "응답은 항상 한국어로 합니다. ":
        "Always respond in Korean. ",
    "세션 단축키 · 컨텍스트 관리.":
        "Session shortcuts · context management.",
    "파일에 저장될 완전한 전체 내용":
        "The complete full content to be saved to the file",
    "최근 한도 도달 기록이 없습니다":
        "No recent limit-reached records",
    "Prompt Caching 기초":
        "Prompt Caching basics",
    "크기 추정치 — 과금 수치 아님":
        "Size estimate — not a billing figure",
    "Cohere RAG 특화 모델.":
        "Cohere RAG-specialized model.",
    "경로는 홈 디렉터리 내부만 허용":
        "Paths must be inside the home directory",
    "샌드박스 내 Bash 자동 허용":
        "Auto-allow Bash inside sandbox",
    "현재 rate limit 상태.":
        "Current rate limit status.",
    "예: 이메일에서 핵심 정보 추출":
        "e.g. extract key info from emails",
    "<CLAUDE.md 전체 내용>":
        "<full CLAUDE.md contents>",
    "계산할 수식 (예: 2+3*5)":
        "Expression to calculate (e.g. 2+3*5)",
    "각 추천을 클릭해 한 번에 설치":
        "Click each recommendation to install in one go",
    "세션 스캔 후 패턴 카드 반환.":
        "Scans sessions and returns pattern cards.",
    "모델별 비용 추정 (USD).":
        "Estimated cost per model (USD).",
    "활성 알림을 모두 해제할까요?":
        "Dismiss all active notifications?",
    "구성된 마켓플레이스가 없습니다":
        "No marketplaces configured",
    "편집 도구 결정 (수락/거절)":
        "Edit tool decision (accept/reject)",
    "테스트 셋을 만들어 시작하세요":
        "Create a test set to get started",
    "hooks.json 파싱 실패":
        "Failed to parse hooks.json",
    "이미지 / PDF 입력 처리.":
        "Handles image / PDF input.",
    ":memo: 사이클 보고 도착":
        ":memo: Cycle report received",
    "등록된 MCP 서버가 아닙니다":
        "Not a registered MCP server",
    "구체적으로 무엇을 해야 하는지":
        "Specifically what needs to be done",
    "등록된 마켓플레이스가 아닙니다":
        "Not a registered marketplace",
    "3072 dims, 최고 품질":
        "3072 dims, highest quality",
    "유효하지 않은 워크플로우 구조":
        "Invalid workflow structure",
    "프로바이더별 기본 모델 매핑.":
        "Default model mapping per provider.",
    "서버 종료 시 스케줄러 정지.":
        "Stops the scheduler on server shutdown.",
    "## 상위 세션 (토큰 기준)":
        "## Top sessions (by tokens)",
    "설정을 클립보드에 복사했습니다":
        "Settings copied to clipboard",
    "Claude CLI 실행 실패":
        "Failed to run Claude CLI",
    "프로바이더별 모델 메타데이터.":
        "Model metadata per provider.",
    "Claude CLI 설치 필요":
        "Claude CLI installation required",
    "유효하지 않은 cron 표현식":
        "Invalid cron expression",
    "작업 실패 — 관리자에게 알림":
        "Task failed — notify the admin",
    "프롬프트 실행 → 응답 반환.":
        "Runs the prompt → returns the response.",
    "리더보드를 가져오지 못했습니다":
        "Failed to load leaderboard",
    "경량 Llama. 빠른 응답.":
        "Lightweight Llama. Fast responses.",
    "프론트엔드 표시용 메타데이터.":
        "Metadata for frontend display.",
    "CLAUDE.md 스니펫 복사":
        "Copy CLAUDE.md snippet",
    "특정 도시의 날씨를 조회한다.":
        "Looks up the weather for a given city.",
    "워크플로우를 찾을 수 없습니다":
        "Workflow not found",
    "개인 계정 불가, 읽기 전용.":
        "Personal accounts not supported, read-only.",
    " 명확히 정리해 보고하세요.":
        " Summarize clearly and report.",
    "CCB 레포 디렉터리 제거.":
        "Removes the CCB repo directory.",
    "최대 로드 파일 Top 10":
        "Top 10 most-loaded files",
    "대용량 프롬프트 병렬 제출.":
        "Submits large prompts in parallel.",
    "유효하지 않은 권한 규칙: ":
        "Invalid permission rule: ",
    "개선이 필요한 점 3개 이내":
        "Up to 3 areas for improvement",
    "Admin 키를 삭제할까요?":
        "Delete the Admin key?",
    "샌드박스 불가 시 시작 실패":
        "Fail to start if sandbox is unavailable",
    "Ultrawork (5병렬)":
        "Ultrawork (5 parallel)",
    "전체 프로바이더 상태 요약.":
        "Status summary for all providers.",
    "표시할 체크포인트가 없습니다":
        "No checkpoints to display",
    "prompts 최대 20 건":
        "prompts: up to 20 entries",
    "Codex 세션 안에서 사용":
        "Use inside a Codex session",
    "워크플로우 JSON 내보내기":
        "Export workflow JSON",
    "각 추천을 클릭해 토글/설치":
        "Click each recommendation to toggle/install",
    "모델 목록 sanitize.":
        "Sanitize the model list.",
    "터미널에서 설치를 진행하세요":
        "Proceed with the installation in your terminal",
    "DeepSeek 코드 생성.":
        "DeepSeek code generation.",
    "CLAUDE.md / 메모리":
        "CLAUDE.md / Memory",
    "프로젝트 전용 에이전트 추가":
        "Add a project-specific agent",
    "리포트를 생성하지 못했습니다":
        "Failed to generate report",
    "답변 톤/포맷 커스터마이즈.":
        "Customize response tone/format.",
    "워크플로우에 순환이 있습니다":
        "The workflow contains a cycle",
    "Pass/Fail 매트릭스":
        "Pass/Fail matrix",
    "tab_id 또는 null":
        "tab_id or null",
    "백업 존재 — 되감기 가능":
        "Backup exists — rewind available",
    "캐시 분석 (랩 + 세션)":
        "Cache analysis (lab + session)",
    "시스템 프롬프트 (문자열)":
        "System prompt (string)",
    "너는 한국어 전문 비서다.":
        "You are an assistant specializing in Korean.",
    "프로젝트 CLAUDE.md":
        "Project CLAUDE.md",
    "Claude Code 세션":
        "Claude Code session",
    "분당 최대 요청 수 설정.":
        "Set max requests per minute.",
    "응답 시간 초과 (30초)":
        "Response timed out (30s)",
    "백업 없음 — 되감기 불가":
        "No backup — rewind unavailable",
    "잘하고 있는 점 3개 이내":
        "Up to 3 things going well",
    "Gemma 2 경량 버전.":
        "Lightweight version of Gemma 2.",
    "베이스라인 대비 회귀 없음":
        "No regression vs baseline",
    "Claude Code 개요":
        "Claude Code overview",
    "흔한 오류 · 복구 절차.":
        "Common errors · recovery steps.",
    "Meta 코드 생성 특화.":
        "Meta, specialized in code generation.",
    "아직 테스트 셋이 없습니다":
        "No test sets yet",
    "docs 유효한 항목 없음":
        "docs: no valid entries",
    "BigCode 코드 생성.":
        "BigCode code generation.",
    "TTL 분할 데이터 없음":
        "No TTL breakdown data",
    "2시간 뒤 / 3시간 뒤":
        "in 2 hours / in 3 hours",
    "도시 이름 (예: 서울)":
        "City name (e.g. Seoul)",
    "rate limit 있음":
        "Has rate limit",
    "사용자 스타일 어드바이저":
        "User style advisor",
    "Researcher 작업":
        "Researcher task",
    "고양이가 쥐를 쫓고 있다":
        "A cat is chasing a mouse",
    "커스텀 프로바이더 저장.":
        "Save custom provider.",
    "가장 최근 세션 (자동)":
        "Most recent session (auto)",
    "모델에 전달할 추가 지시":
        "Additional instructions for the model",
    "커스텀 프로바이더 삭제.":
        "Delete custom provider.",
    "먼저 리포트를 생성하세요":
        "Generate a report first",
    "경로가 존재하지 않습니다":
        "Path does not exist",
    "1536 dims, 저렴":
        "1536 dims, low cost",
    "MCP 커넥터 추가 제안":
        "Suggest additional MCP connectors",
    "비활성 세션 강제 바인딩":
        "Force-bind inactive session",
    "유효하지 않은 권한 규칙":
        "Invalid permission rule",
    "복사할 내용이 없습니다.":
        "Nothing to copy.",
    "Markdown 미리보기":
        "Markdown preview",
    "사용 가능한 모델 목록.":
        "List of available models.",
    "유효하지 않은 모델 이름":
        "Invalid model name",
    "<한 문장 한국어 설명>":
        "<one-sentence description>",
    "베이스라인 윈도우 (일)":
        "Baseline window (days)",
    "모든 Unix 소켓 허용":
        "Allow all Unix sockets",
    "프로젝트 전용 스킬 추가":
        "Add project-specific skill",
    "코드 라인 / 활성 시간":
        "Lines of code / active time",
    "이미지+텍스트 멀티모달.":
        "Image+text multimodal.",
    "JSON 배열 파싱 실패":
        "Failed to parse JSON array",
    "업그레이드를 권장합니다.":
        "Upgrade is recommended.",
    "표시할 세션이 없습니다.":
        "No sessions to display.",
    "지정 경로 쓰기 차단.":
        "Block writes to specified paths.",
    "최근 14일 토큰 추이":
        "Token trend over last 14 days",
    "테스트 셋을 선택하세요":
        "Select a test set",
    " (벡터 JSON), ":
        " (vector JSON), ",
    "변경할 항목이 없습니다":
        "Nothing to change",
    "문서 인용 응답 모드.":
        "Document citation response mode.",
    "메시지가 비어있습니다.":
        "Message is empty.",
    "오프라인 구조 diff":
        "Offline structure diff",
    "폴백 체인 순서 설정.":
        "Configure fallback chain order.",
    "Anthropic 발표":
        "Anthropic announcement",
    "이상 탐지 로드 실패:":
        "Failed to load anomaly detection:",
    "범위별 추정 토큰 로드":
        "Load estimated tokens by range",
    "이벤트 타입 + URL":
        "Event type + URL",
    "프로바이더 상태 확인.":
        "Check provider status.",
    "브라우저 주소창에 검색":
        "Search in browser address bar",
    "분석 불러오는 중...":
        "Loading analysis...",
    "프로젝트별 메모리 로드":
        "Load per-project memory",
    "Admin 사용량·비용":
        "Admin usage & cost",
    "Uncached 입력":
        "Uncached input",
    "백업 없음 (GC됨)":
        "No backup (GC'd)",
    "이상 탐지 계산 중…":
        "Computing anomaly detection…",
    "Ollama (로컬)":
        "Ollama (local)",
    "구 모델 은퇴 일정.":
        "Legacy model retirement schedule.",
    "세션 ID가 없습니다":
        "No session ID",
    " → Slack 승인":
        " → Slack approval",
    "Reviewer 작업":
        "Reviewer task",
    "이전 대화를 기억해?":
        "Do you remember our previous conversation?",
    "추정 vs 실제 청구":
        "Estimated vs actual billing",
    "TODO 리스트 구축":
        "Build TODO list",
    "<사용/시작 URL>":
        "<usage/getting-started URL>",
    "검색 결과 기반 답변":
        "Answers based on search results",
    "Admin API 키":
        "Admin API key",
    "활성 알림이 없습니다":
        "No active alerts",
    "<한국어 짧은 이름>":
        "<short name>",
    "Markdown 복사":
        "Copy Markdown",
    "표시할 플러그인 없음":
        "No plugins to display",
    "저장된 Admin 키":
        "Saved Admin key",
    "비용 유형별 (실제)":
        "By cost type (actual)",
    "새 워크플로우 만들기":
        "Create new workflow",
    "Claude (메인)":
        "Claude (main)",
    "로그아웃 되었습니다.":
        "You have been logged out.",
    "인쇄용 HTML 열기":
        "Open printable HTML",
    "모델별 토큰 (오늘)":
        "Tokens by model (today)",
    "샌드박스 설정 저장됨":
        "Sandbox settings saved",
    "코드 라인 (+/-)":
        "Code lines (+/-)",
    "한도 도달 기록 없음":
        "No limit-hit records",
    "로드 경계 초과 파일":
        "Files over load boundary",
    "인쇄용 HTML 오류":
        "Printable HTML error",
    "코드 리뷰 파이프라인":
        "Code review pipeline",
    "도구 정의 순서 변경":
        "Reorder tool definitions",
    "프로바이더 목록 필수":
        "Provider list required",
    "웹 검색 시뮬레이션.":
        "Web search simulation.",
    "지금 (이미 리셋됨)":
        "Now (already reset)",
    "Qwen 코드 특화.":
        "Qwen specialized for code.",
    "샌드박스 공식 문서":
        "Sandbox official docs",
    "시스템 노이즈 숨김":
        "Hide system noise",
    "근접도 알 수 없음":
        "Proximity unknown",
    "유효하지 않은 ID":
        "Invalid ID",
    "프로젝트 스킬 삭제":
        "Delete project skill",
    "최근 활동 프로젝트":
        "Recently active projects",
    "리더보드 조회 실패":
        "Failed to load leaderboard",
    "Ollama 종료됨":
        "Ollama stopped",
    "- (데이터 없음)":
        "- (no data)",
    "간단한 수식 계산.":
        "Simple formula calculation.",
    "선택 노드 잘라내기":
        "Cut selected nodes",
    "컨텍스트 구성 막대":
        "Context composition bar",
    "시스템 포트 숨기기":
        "Hide system ports",
    "## 상위 프로젝트":
        "## Top projects",
    "이탈리아의 수도는?":
        "What is the capital of Italy?",
    " (차원 수만), ":
        " (dimension count only), ",
    "롤링 5시간 윈도우":
        "Rolling 5-hour window",
    "git URL 필요":
        "git URL required",
    "Builder 작업":
        "Builder task",
    "두 요청 전송 중…":
        "Sending both requests…",
    "오늘 상위 프로젝트":
        "Top projects today",
    "Batch 가드: ":
        "Batch guard: ",
    "Eval 실행 확인":
        "Confirm eval run",
    "SQL 쿼리 최적화":
        "SQL query optimization",
    "Admin 키 설정":
        "Set admin key",
    "JSON 파싱 오류":
        "JSON parsing error",
    "리포트 · 내보내기":
        "Reports · Export",
    "자기소개 한 줄로.":
        "Introduce yourself in one line.",
    "토큰 합계 (실제)":
        "Token total (actual)",
    "| 항목 | 값 |":
        "| Item | Value |",
    "노드 잘라내기 완료":
        "Nodes cut",
    "CLI 실행 오류":
        "CLI execution error",
    "예산 가드 활성화":
        "Enable budget guard",
    "분석 기간 (일)":
        "Analysis period (days)",
    "Google 최강":
        "Google is the best",
    "서울 날씨 어때?":
        "How's the weather in Seoul?",
    "— 직접 입력 —":
        "— Enter manually —",
    "캐시가 깨진 위치":
        "Where the cache breaks",
    "Bash 샌드박스":
        "Bash sandbox",
    "prod에 올리기":
        "Deploy to prod",
    "엣지 케이스 열거":
        "Enumerate edge cases",
    "개 새로고침 필요":
        " items need refresh",
    "_데이터 없음._":
        "_No data._",
    " 이름으로 생성.":
        " created with this name.",
    "출력 스타일 점검":
        "Output style check",
    "+ 시도 횟수 캡":
        "+ attempt cap",
    "1시간 캐시 쓰기":
        "1-hour cache write",
    "시스템 포트 표시":
        "Show system ports",
    "보안 취약점 검사":
        "Security vulnerability scan",
    "스페인의 수도는?":
        "What is the capital of Spain?",
    "- (샘플 없음)":
        "- (no samples)",
    "프롬프트 eval":
        "Prompt eval",
    "글로벌 상시 로드":
        "Always loaded globally",
    "범위 내 총 지출":
        "Total spend in range",
    "실제 청구 USD":
        "Actual billed USD",
    "최우선 개선 항목":
        "Top priority improvement",
    "일일 지출 ($)":
        "Daily spend ($)",
    "마이그레이션 보기":
        "View migration",
    "배열이어야 합니다":
        "Must be an array",
    "찾을 수 없습니다":
        "Not found",
    "스킬 스니펫 복사":
        "Copy skill snippet",
    "유효한 모델 없음":
        "No valid model",
    "프랑스의 수도는?":
        "What is the capital of France?",
    "무료 (Free)":
        "Free",
    "비용 데이터 없음":
        "No cost data",
    "수집 데이터 분석":
        "Analyze collected data",
    "한 줄 종합 평가":
        "One-line overall assessment",
    "캐시 미사용 가정":
        "Assuming no cache",
    "인덱스 범위 오류":
        "Index out of range",
    "URL 본문 요약":
        "Summarize URL content",
    "메모리 모두 삭제":
        "Delete all memories",
    "케이스가 없습니다":
        "No cases",
    "## 모델별 분포":
        "## Distribution by model",
    "📝 옵시디언 기록":
        "📝 Obsidian log",
    "API 키 삭제.":
        "Delete API key.",
    "RAG 파이프라인":
        "RAG pipeline",
    "알 수 없는 오류":
        "Unknown error",
    "실시간 텔레메트리":
        "Real-time telemetry",
    "캐나다의 수도는?":
        "What is the capital of Canada?",
    "분석 데이터 없음":
        "No analysis data",
    "프롬프트 Eval":
        "Prompt Eval",
    "재시도 워크플로우":
        "Retry workflow",
    "코드 라인 (+)":
        "Code lines (+)",
    "불러오는 중...":
        "Loading...",
    "리셋 시각 감지됨":
        "Reset time detected",
    "MCP 서버 도구":
        "MCP server tools",
    "테스트 셋 편집":
        "Edit test set",
    "경량 멀티모달.":
        "Lightweight multimodal.",
    "경계 초과 파일":
        "Files outside boundary",
    "키를 입력하세요":
        "Enter a key",
    "백업 사용 가능":
        "Backup available",
    "일별 토큰 추이":
        "Daily token trend",
    "API 키 액터":
        "API key actor",
    "중국의 수도는?":
        "What is the capital of China?",
    " 것으로 간주.":
        " is assumed.",
    "터미널에서 실행":
        "Run in terminal",
    "분석 로드 실패":
        "Failed to load analysis",
    "일별 Drift":
        "Daily Drift",
    "총 메모리 로드":
        "Total memory loaded",
    "개 마켓플레이스":
        " marketplaces",
    " (기본) | ":
        " (default) | ",
    "파일 복원 가능":
        "Files can be restored",
    "샌드박스 활성화":
        "Enable sandbox",
    "이번 달 USD":
        "USD this month",
    "## 일별 추이":
        "## Daily trend",
    "캐시 읽기 토큰":
        "Cache read tokens",
    "오늘 활동 없음":
        "No activity today",
    "5분 캐시 쓰기":
        "5-min cache write",
    "독일의 수도는?":
        "What is the capital of Germany?",
    "프롬프트 템플릿":
        "Prompt template",
    "모델별 (추정)":
        "By model (estimated)",
    "추론 (CoT)":
        "Reasoning (CoT)",
    "일본의 수도는?":
        "What is the capital of Japan?",
    "가장 빠른 리셋":
        "Earliest reset",
    "5 + 2 메모":
        "5 + 2 note",
    "팀 워크스페이스":
        "Team workspace",
    "언제까지 재시도":
        "Retry deadline",
    "테스트 셋 삭제":
        "Delete test set",
    "코드 품질 리뷰":
        "Code quality review",
    "응답 시간 초과":
        "Response timed out",
    "베스트 프랙티스":
        "Best practices",
    "미국의 수도는?":
        "What is the capital of the United States?",
    "API 키 전용":
        "API key only",
    "영국의 수도는?":
        "What is the capital of the UK?",
    "상태 조회 실패":
        "Failed to fetch status",
    "통계 전체 보기":
        "View all stats",
    "출력 토큰 절감":
        "Output token savings",
    "지금부터 N시간":
        "N hours from now",
    "코드 리뷰 요청":
        "Request code review",
    "무료 / 미확인":
        "Free / unverified",
    "최근 세션 없음":
        "No recent sessions",
    "모든 알림 해제":
        "Clear all notifications",
    "기본 빠른 모델":
        "Default fast model",
    "상호작용 그래프":
        "Interaction graph",
    "## 기간 합계":
        "## Period Total",
    "생성 중...":
        "Generating...",
    "도구 카탈로그":
        "Tool Catalog",
    "오케스트레이터":
        "Orchestrator",
    "🧩 보고 취합":
        "🧩 Report Aggregation",
    "스프린트 요청":
        "Sprint Request",
    "최신 플래그십":
        "Latest Flagship",
    "이벤트 포워더":
        "Event Forwarder",
    "컨텍스트 구성":
        "Context Composition",
    "컨텍스트 부하":
        "Context Load",
    "이번 달 토큰":
        "Tokens This Month",
    "최대 결과 수":
        "Max Results",
    "강제 새로고침":
        "Force Refresh",
    "프롬프트 저장":
        "Save Prompt",
    "멀티 에이전트":
        "Multi-Agent",
    "데이터 ETL":
        "Data ETL",
    "Eval 실행":
        "Run Eval",
    "빌트인 스타일":
        "Built-in Styles",
    "사용량 근사치":
        "Approximate Usage",
    "분석 세션 수":
        "Analyzed Sessions",
    "rank 비교":
        "rank comparison",
    "샌드박스 ON":
        "Sandbox ON",
    "플러그인 마켓":
        "Plugin Marketplace",
    "저렴 + 빠름":
        "Cheap + Fast",
    "작업 디렉터리":
        "Working Directory",
    "Opus 한도":
        "Opus Limit",
    "입력 / 출력":
        "Input / Output",
    "예시 불러오기":
        "Load Example",
    "새 테스트 셋":
        "New Test Set",
    "페르소나 크루":
        "Persona Crew",
    "커밋 / PR":
        "Commit / PR",
    "세션 리플레이":
        "Session Replay",
    "프로젝트 생성":
        "Create Project",
    "프롬프트 캐시":
        "Prompt Cache",
    "웹 검색 요청":
        "Web Search Requests",
    "스캔한 파일":
        "Scanned Files",
    "한 줄 제목":
        "One-line Title",
    "잘못된 요청":
        "Bad Request",
    "사용량 관측":
        "Usage Observability",
    "현재 사용량":
        "Current Usage",
    "사용량 한도":
        "Usage Limit",
    "첫 프롬프트":
        "First Prompt",
    "텔레그램 봇":
        "Telegram Bot",
    "어제와 동일":
        "Same as Yesterday",
    "예산 저장됨":
        "Budget Saved",
    "이미지 인식":
        "Image Recognition",
    "개 플러그인":
        "plugins",
    "오늘 USD":
        "Today USD",
    "토큰 최적화":
        "Token Optimization",
    "캐시 히트율":
        "Cache Hit Rate",
    "케이스 없음":
        "No cases",
    "REG=회귀":
        "REG=regression",
    "cli 세션":
        "cli session",
    "추정 USD":
        "Est. USD",
    "케이스 삭제":
        "Delete case",
    "메모리 파일":
        "Memory file",
    "$100/월":
        "$100/mo",
    "어서션 없음":
        "No assertions",
    "설계 보고서":
        "Design report",
    "도구 수락률":
        "Tool acceptance rate",
    "마지막 출력":
        "Last output",
    "메모리 요약":
        "Memory summary",
    "- (없음)":
        "- (none)",
    "토큰 종류별":
        "By token type",
    "한도 미설정":
        "No limit set",
    "알림 해제됨":
        "Notifications off",
    "$200/월":
        "$200/mo",
    "오래된 캐시":
        "Stale cache",
    "다단계 추론":
        "Multi-step reasoning",
    "메시지 배치":
        "Message batch",
    "답변 텍스트":
        "Answer text",
    "모델별 비용":
        "Cost by model",
    "마이그레이션":
        "Migration",
    "저렴한 대안":
        "Cheaper alternative",
    "엔터프라이즈":
        "Enterprise",
    "메모리 감사":
        "Memory audit",
    "API 오류":
        "API error",
    "베이스라인":
        "Baseline",
    "월 USD":
        "USD/mo",
    "예상 답변":
        "Expected answer",
    "$20/월":
        "$20/mo",
    "최근 활동":
        "Recent activity",
    "토큰 절감":
        "Token savings",
    "회귀 없음":
        "No regressions",
    "세션 선택":
        "Select session",
    "캐시 절감":
        "Cache savings",
    "추정 비용":
        "Estimated cost",
    "🧭 기획자":
        "🧭 Planner",
    "AR 중단":
        "Stop AR",
    "코드 라인":
        "Lines of code",
    "값 불필요":
        "No value needed",
    "범용 강력":
        "General-purpose, powerful",
    "설계 문서":
        "Design doc",
    "복원 불가":
        "Cannot be restored",
    "오늘 세션":
        "Today's sessions",
    "최신 기능":
        "Latest features",
    "공식 도구":
        "Official tools",
    "진단 실행":
        "Run diagnostics",
    "세션 종료":
        "End session",
    "호출 실패":
        "Call failed",
    "최근 7일":
        "Last 7 days",
    "최근 수신":
        "Recently received",
    "세션 시작":
        "Session start",
    "기간(일)":
        "Period (days)",
    "정렬 기준":
        "Sort by",
    "작업 입력":
        "Task input",
    "사용 불가":
        "Unavailable",
    "캐시 진단":
        "Cache diagnostics",
    "개 설치됨":
        "installed",
    "추정 토큰":
        "Estimated tokens",
    "작업/수정":
        "Tasks/Edits",
    "대화 기록":
        "Conversation history",
    "일괄 처리":
        "Batch processing",
    "보안 스캔":
        "Security scan",
    "저장 중…":
        "Saving…",
    "도구 정의":
        "Tool definitions",
    "캐시 생성":
        "Cache creation",
    "보존 기간":
        "Retention period",
    "일일 요약":
        "Daily summary",
    "추적 파일":
        "Tracked files",
    "주간 한도":
        "Weekly limit",
    "일 USD":
        "USD/day",
    "파일 조회":
        "File lookup",
    "세션 로그":
        "Session logs",
    "계획 수립":
        "Planning",
    "이름 회상":
        "Name recall",
    "이름 기억":
        "Name memory",
    "결과 합류":
        "Result join",
    "폼 채우기":
        "Form filling",
    "진단 중…":
        "Diagnosing…",
    "파일 변경":
        "File changes",
    "오늘 토큰":
        "Today's tokens",
    "외부 전송":
        "External delivery",
    "모델 비교":
        "Model comparison",
    "설계 결정":
        "Design decisions",
    "추론 경량":
        "Lightweight reasoning",
    "작업 지시":
        "Task instructions",
    "스킬 삭제":
        "Delete skill",
    "(글로벌)":
        "(global)",
    "설정 복사":
        "Copy settings",
    "초기 요청":
        "Initial request",
    "대량 요청":
        "Bulk requests",
    "토큰 압축":
        "Token compression",
    "모델 허브":
        "Model hub",
    "1차 질문":
        "First question",
    "비용 절감":
        "Cost savings",
    "활성 시간":
        "Active time",
    "분석 요청":
        "Analysis request",
    "도시 이름":
        "City name",
    "통합 결과":
        "Combined results",
    "화면 맞춤":
        "Fit to screen",
    "조회 실패":
        "Lookup failed",
    "온도 단위":
        "Temperature unit",
    "가장 저렴":
        "Cheapest",
    "레이트리밋":
        "Rate limit",
    "회의 요약":
        "Meeting summary",
    "모두 해제":
        "Deselect all",
    "추론 모델":
        "Reasoning model",
    "요약 검증":
        "Summary validation",
    "테스트 셋":
        "Test set",
    "편집 결정":
        "Edit decision",
    "파일시스템":
        "Filesystem",
    "회귀 감지":
        "Regression detection",
    "vs 어제":
        "vs yesterday",
    "지연 비교":
        "Latency comparison",
    "수신 중":
        "Receiving",
    "일 토큰":
        "Daily tokens",
    "월 토큰":
        "Monthly tokens",
    "키 삭제":
        "Delete key",
    "홈페이지":
        "Homepage",
    "첫 분기":
        "First branch",
    "새 알림":
        "New alert",
    "케이스":
        "Case",
    "순증감":
        "Net change",
    "수락률":
        "Acceptance rate",
    "폐기됨":
        "Discarded",
    "기댓값":
        "Expected value",
    "실시간":
        "Live",
    "새 셋":
        "New set",
    "메트릭":
        "Metrics",
    "윈도우":
        "Window",
    "레코드":
        "Records",
    "어서션":
        "Assertions",
    "해결":
        "Resolve",
    "권장":
        "Recommended",
    "실제":
        "Actual",
    "유형":
        "Type",
    "경계":
        "Boundary",
    "이상":
        "Anomaly",
    "원인":
        "Cause",
    "숫자":
        "Number",
    "폐기":
        "Discard",
    "속성":
        "Attributes",
    "마감":
        "Deadline",
    "해제":
        "Clear",
    "커밋":
        "Commit",
    "거절":
        "Reject",
    "초과":
        "Exceeded",
    "수락":
        "Accept",
    "추정":
        "Estimated",
    "남음":
        "remaining",
    "비정상": "Abnormal",
    "단일": "Single",
    "전용": "dedicated",
    "감지": "detected",
    "스레드": "threads",
    "공유": "shared",
    "레벨": "level",
    "압축": "compression",
    "핵심": "key",
    "포인트": "points",
    "페이지": "page",
    "순수": "pure",
    "개별": "individual",
    "직전": "previous",
    "군더더기": "fluff",
    "평소보다": "than usual",
    "시퀀스가": "sequence",
    "줄로": "lines",
    "줄": "lines",
    "커넥터와": "connectors and",
    "설치형": "installable",
    "패키지": "package",
}

NEW_ZH: dict[str, str] = {
    "Claude Code의 Bash 샌드박스는 셸 명령을 OS 수준 격리(macOS Seatbelt / Linux·WSL2 bubblewrap) 안에서 실행해, 매번 권한을 묻지 않고도 파일·네트워크 접근 경계를 강제합니다. native Windows는 미지원(WSL2 사용).":
        "Claude Code 的 Bash 沙箱在操作系统级隔离(macOS Seatbelt / Linux·WSL2 bubblewrap)中执行 shell 命令，无需每次询问权限即可强制实施文件/网络访问边界。不支持原生 Windows(请使用 WSL2)。",
    "thinking block 과 최종 응답을 분리 시각화. Opus 4.8/4.7·Sonnet 4.6 = adaptive thinking + effort(low~max) 로 추론/비용 조절. legacy 모델은 budget_tokens.":
        "将 thinking block 与最终响应分离可视化。Opus 4.8/4.7·Sonnet 4.6 = adaptive thinking + effort(low~max)调节推理/成本。旧版模型使用 budget_tokens。",
    "기본은 사전 허용 도메인 없음 — 새 도메인 첫 접근 시 프롬프트. 여기 미리 넣으면 프롬프트 생략. 와일드카드 서브도메인(*.npmjs.org) 지원. github.com 같은 넓은 허용은 데이터 유출 경로가 될 수 있음.":
        "默认没有预先允许的域名——首次访问新域名时会弹出提示。在此预先添加可跳过提示。支持通配符子域名(*.npmjs.org)。像 github.com 这样的宽泛允许可能成为数据外泄途径。",
    "샌드박스 제약으로 실패한 명령을 dangerouslyDisableSandbox로 격리 밖에서 재시도(권한 프롬프트 경유). false면 Strict 모드 — 반드시 격리 또는 excludedCommands 안에서만 실행.":
        "通过 dangerouslyDisableSandbox 在隔离外重试因沙箱限制失败的命令(经由权限提示)。若为 false 则为 Strict 模式——命令必须在隔离内或 excludedCommands 中执行。",
    "🎯 LazyClaude는 OMC의 4 모드를 이미 흡수 — 별도 설치 없이 워크플로우 탭의 빌트인 템플릿(bt-autopilot/ralph/ultrawork/deep-interview) 또는 런 센터에서 즉시 사용 가능":
        "🎯 LazyClaude 已吸收 OMC 的 4 种模式——无需单独安装，可通过工作流标签页的内置模板(bt-autopilot/ralph/ultrawork/deep-interview)或运行中心立即使用",
    "이 대시보드는 Claude Code 의 OpenTelemetry 메트릭 수신처(OTLP 백엔드)입니다. 순수 stdlib 서버라 protobuf 는 파싱할 수 없으니 반드시 http/json 프로토콜로 설정하세요.":
        "此仪表板是 Claude Code 的 OpenTelemetry 指标接收端(OTLP 后端)。由于是纯 stdlib 服务器，无法解析 protobuf，请务必将协议设置为 http/json。",
    "조직 Admin API(Claude Code Analytics)에서 사용자별 세션·코드 라인·커밋·PR·토큰·추정 비용을 가져와 순위를 매깁니다. 조직 Admin 키(sk-ant-admin...)가 필요합니다.":
        "从组织 Admin API(Claude Code Analytics)获取每位用户的会话、代码行数、提交、PR、令牌和估算成本并进行排名。需要组织 Admin 密钥(sk-ant-admin...)。",
    "팀 리더보드는 Claude Code Analytics Admin API를 사용합니다. 표준 API 키가 아닌 조직 Admin 키(sk-ant-admin...)가 필요하며 개인 계정에서는 사용할 수 없습니다.":
        "团队排行榜使用 Claude Code Analytics Admin API。需要组织 Admin 密钥(sk-ant-admin...)而非标准 API 密钥，个人账户无法使用。",
    "OMC /team 스타일 5단계: 계획(Opus)→요구사항명세(Sonnet)→3-병렬 실행(Sonnet)→취합→검증(Haiku)→실패 시 수정. Repeat 3회까지 자동 verify-fix 루프.":
        "OMC /team 风格 5 阶段：计划(Opus)→需求规格(Sonnet)→3 路并行执行(Sonnet)→汇总→验证(Haiku)→失败时修复。自动 verify-fix 循环最多 Repeat 3 次。",
    "소규모 팀(5명)이 매일 10만 이벤트를 처리하는 실시간 알림 시스템을 만들려고 한다. SQS vs Kafka vs Redis Streams 중 어떤 선택이 적합한지 트레이드오프를 설계해서 답해줘.":
        "一个小团队(5 人)想构建一个每天处理 10 万事件的实时通知系统。请设计 SQS vs Kafka vs Redis Streams 之间的权衡并回答哪种选择更合适。",
    "CLAUDE.md 또는 .claude/agents/<name>.md 또는 .claude/skills/<name>/SKILL.md 또는 .claude/settings.local.json":
        "CLAUDE.md 或 .claude/agents/<name>.md 或 .claude/skills/<name>/SKILL.md 或 .claude/settings.local.json",
    "Anthropic 서버가 직접 실행하는 hosted tool (web_search · code_execution · web_fetch) 을 활성화하고 응답 블록을 분류 시각화합니다.":
        "启用由 Anthropic 服务器直接执行的 hosted tool(web_search · code_execution · web_fetch)，并对响应块进行分类可视化。",
    "관리형 설정에서만 의미. true면 managed settings의 filesystem.allowRead만 적용되고 user/project/local의 allowRead는 무시됨.":
        "仅在托管设置中有意义。若为 true，仅应用 managed settings 的 filesystem.allowRead，user/project/local 的 allowRead 将被忽略。",
    "denyRead 영역 안에서 특정 경로만 다시 읽기 허용. 예: denyRead [~/] + allowRead [.] (project settings에서 . 은 프로젝트 루트).":
        "在 denyRead 区域内仅重新允许读取特定路径。例如：denyRead [~/] + allowRead [.](在 project settings 中 . 为项目根目录)。",
    "Bash 명령을 OS 수준 격리(macOS Seatbelt / Linux·WSL2 bubblewrap) 안에서 실행. user settings에 true면 모든 프로젝트에 적용.":
        "在操作系统级隔离(macOS Seatbelt / Linux·WSL2 bubblewrap)中执行 Bash 命令。在 user settings 中设为 true 则适用于所有项目。",
    "claude CLI가 설치되어 있지 않습니다. `brew install claude` 또는 https://docs.claude.com/en/docs/claude-code 참고":
        "未安装 claude CLI。请使用 `brew install claude` 或参考 https://docs.claude.com/en/docs/claude-code",
    "프로젝트 도메인에 특화된 에이전트를 `.claude/agents/<name>.md`에 두면 Agent 툴로 위임 가능. 위임(delegation) 축 점수가 직접 오릅니다.":
        "将专精于项目领域的代理放在 `.claude/agents/<name>.md` 中，即可通过 Agent 工具进行委派。委派(delegation)维度的分数会直接提升。",
    "최근 3년간 Anthropic, OpenAI, Google DeepMind 의 논문 편수를 웹에서 찾아보고, 그 수치로 막대 그래프의 값 배열 [A, O, G] 을 출력해.":
        "在网上查找 Anthropic、OpenAI、Google DeepMind 近 3 年的论文数量，并用这些数值输出柱状图的值数组 [A, O, G]。",
    "Claude Design 공식 API 는 아직 미공개. claude.ai/design 에서 PDF/PPTX/HTML 로 export 한 파일을 기본 경로에서 스캔합니다.":
        "Claude Design 官方 API 尚未公开。在默认路径中扫描从 claude.ai/design 导出为 PDF/PPTX/HTML 的文件。",
    "아직 5시간/주간 한도에 부딪힌 적이 없거나 관련 세션 로그가 오래되어, 정확한 리셋 시각을 추출할 데이터가 없습니다. 아래 사용량 근사치는 세션 토큰 합계 기반입니다.":
        "您尚未触及 5 小时/每周限额，或相关会话日志过旧，没有可提取准确重置时间的数据。以下用量近似值基于会话令牌总和。",
    "저장 시 settings.json.bak.<시각> 백업을 먼저 만들고, 검증된 sandbox 키만 안전하게 병합 기록합니다. 관련 없는 설정은 절대 건드리지 않습니다.":
        "保存时先创建 settings.json.bak.<时间> 备份，然后仅安全地合并写入经过验证的 sandbox 键。绝不触碰无关设置。",
    "터미널에서: claude mcp add context7 npx -y @upstash/context7-mcp  (MCP는 대시보드에서 직접 편집하지 않고 CLI로 추가)":
        "在终端中：claude mcp add context7 npx -y @upstash/context7-mcp  (MCP 通过 CLI 添加，而非在仪表板中直接编辑)",
    "기본 읽기 정책은 ~/.aws/credentials, ~/.ssh 까지 읽을 수 있음 — 자격증명 디렉토리를 여기 추가해 차단 권장. 예: ~/.aws, ~/.ssh.":
        "默认读取策略可读取 ~/.aws/credentials、~/.ssh——建议将凭证目录添加到此处以进行阻止。例如：~/.aws、~/.ssh。",
    "Claude Code 세션 안에서 슬래시 명령으로 호출하는 팀 오케스트레이션 (autopilot · ralph · ultrawork · deep-interview)":
        "在 Claude Code 会话内通过斜杠命令调用的团队编排(autopilot · ralph · ultrawork · deep-interview)",
    "Anthropic 조직 Admin API에서 실제 청구된 토큰/USD를 가져와 로컬 추정치와 비교합니다. Admin 키(sk-ant-admin...)가 필요합니다.":
        "从 Anthropic 组织 Admin API 获取实际计费的令牌/USD，并与本地估算值进行比较。需要 Admin 密钥(sk-ant-admin...)。",
    "🎯 LazyClaude는 OMX의 4 명령을 정적 매핑으로 노출 — 런 센터에서 임의 프로바이더(Claude/GPT/Gemini/Ollama)로 dispatch":
        "🎯 LazyClaude 以静态映射暴露 OMX 的 4 个命令——可在运行中心 dispatch 到任意提供商(Claude/GPT/Gemini/Ollama)",
    "CLAUDE.md 는 세션 시작 시 자동 로드됩니다. 프로젝트 맥락(스택·규칙·도메인용어)을 여기 적으면 매 세션 설명 반복이 사라져 참여도·안정성 모두 상승.":
        "CLAUDE.md 在会话开始时自动加载。将项目上下文(技术栈、规则、领域术语)写在这里，就无需每个会话重复说明，参与度与稳定性都会提升。",
    "기본은 작업 디렉토리만 쓰기 가능. 여기 추가하면 그 경로도 쓰기 허용(하위 프로세스 포함). 예: ~/.kube, /tmp/build. 스코프 간 병합됨.":
        "默认仅工作目录可写。添加到此处的路径也允许写入(包括子进程)。例如：~/.kube、/tmp/build。跨作用域合并。",
    "~/.claude/settings.json 의 statusLine 설정을 추천하세요. 쉘 명령으로 current branch, model, cost 표시.":
        "请推荐 ~/.claude/settings.json 的 statusLine 设置。通过 shell 命令显示 current branch、model、cost。",
    "🛣️ Claude Code Router — Claude Code를 GLM/Z.AI/DeepSeek 등 다른 LLM으로 라우팅하고 zclaude 별칭 안내":
        "🛣️ Claude Code Router——将 Claude Code 路由到 GLM/Z.AI/DeepSeek 等其他 LLM，并提供 zclaude 别名指引",
    "의존성 누락 등으로 샌드박스를 시작할 수 없으면 경고 후 비격리 실행하는 대신 Claude Code 시작 자체를 막음. 관리형 배포의 보안 게이트용.":
        "如果因缺少依赖等原因无法启动沙箱，则直接阻止 Claude Code 启动，而不是警告后以非隔离方式运行。用于托管部署的安全门控。",
    "LIVE 실행에는 ANTHROPIC_API_KEY 또는 설치된 claude CLI 가 필요합니다. 없으면 각 셀이 ⚠️ 로 정직하게 실패 표시됩니다.":
        "LIVE 执行需要 ANTHROPIC_API_KEY 或已安装的 claude CLI。若没有，每个单元格会以 ⚠️ 诚实地标记为失败。",
    "조직 Admin API 키는 표준 API 키와 다릅니다. sk-ant-admin... 으로 시작하며 콘솔의 admin-keys 페이지에서 발급합니다.":
        "组织 Admin API 密钥与标准 API 密钥不同。以 sk-ant-admin... 开头，在控制台的 admin-keys 页面签发。",
    "로컬 JSONL 에서 Claude Code(및 Codex/Gemini 등) 토큰·비용을 일/주/월/세션별로 분석하는 CLI. 설치 없이 즉시 실행.":
        "从本地 JSONL 按日/周/月/会话分析 Claude Code(及 Codex/Gemini 等)令牌与成本的 CLI。无需安装即可立即运行。",
    "> 비용은 입력/출력 토큰 × 모델 요금으로 **추정**한 값입니다. 캐시 토큰은 합계에는 포함하지만 비용 추정에는 별도 단가를 적용하지 않습니다.":
        "> 成本是按输入/输出令牌 × 模型费率**估算**的值。缓存令牌计入总和，但成本估算中不另行应用单独单价。",
    "Anthropic은 주간/5시간 쿼터의 실시간 잔량 API를 제공하지 않습니다. 이 위젯은 로컬 세션 로그 기반 best-effort 추정입니다.":
        "Anthropic 不提供每周/5 小时配额的实时余量 API。此小组件是基于本地会话日志的 best-effort 估算。",
    "Opus / Sonnet / Haiku 3 티어로 제공된다. Anthropic 은 2024년 Amazon 으로부터 40억 달러 투자를 유치했고, ":
        "以 Opus / Sonnet / Haiku 3 个层级提供。Anthropic 在 2024 年获得了 Amazon 的 40 亿美元投资，",
    "두 개의 연속 요청(base → modified)을 보내 어느 캐시 브레이크포인트가 prompt-cache 히트를 깨뜨렸는지 정확히 짚어냅니다.":
        "发送两个连续请求(base → modified)，精确定位是哪个缓存断点破坏了 prompt-cache 命中。",
    "Smart routing — Haiku/Opus 자동 선택 (LazyClaude는 modelHint 'auto/fast/deep' 으로 흡수)":
        "Smart routing——自动选择 Haiku/Opus(LazyClaude 通过 modelHint 'auto/fast/deep' 吸收)",
    "caveman 스타일 서브에이전트 위임 가이드 (investigator·builder·reviewer) — 결과를 압축해 메인 컨텍스트 절약":
        "caveman 风格子代理委派指南(investigator·builder·reviewer)——压缩结果以节省主上下文",
    "어서션 기반 회귀 테스트. 테스트 셋(케이스+어서션)을 여러 프로바이더에 교차 실행하고, 저장된 베이스라인과 비교해 회귀를 강조 표시합니다.":
        "基于断言的回归测试。将测试集(用例+断言)交叉运行于多个提供商，并与保存的基线比较，突出显示回归。",
    "settings.json이 올바른 JSON이 아닙니다. 손상을 막기 위해 편집을 비활성화했습니다. 파일을 수동으로 고친 뒤 새로고침하세요.":
        "settings.json 不是有效的 JSON。为防止损坏已禁用编辑。请手动修复文件后刷新。",
    "최신 `web_search_20260209` 은 dynamic filtering 지원 (code_execution 동시 활성화 필요). ":
        "最新的 `web_search_20260209` 支持 dynamic filtering(需同时启用 code_execution)。",
    "CLAUDE_CODE_ENABLE_TELEMETRY=1 + OTEL_EXPORTER_OTLP_PROTOCOL=http/json 로 연결.":
        "通过 CLAUDE_CODE_ENABLE_TELEMETRY=1 + OTEL_EXPORTER_OTLP_PROTOCOL=http/json 连接。",
    "Stop-callback — Slack/Discord/Telegram 알림 (LazyClaude는 워크플로우 notify 필드로 흡수)":
        "Stop-callback——Slack/Discord/Telegram 通知(LazyClaude 通过工作流 notify 字段吸收)",
    "상세 멤버 리스트/사용량은 claude.ai/settings/organization 에서 관리됩니다. 로컬에는 조직 식별자만 저장됨.":
        "详细成员列表/用量在 claude.ai/settings/organization 管理。本地仅存储组织标识符。",
    "https://www.anthropic.com/news 의 내용을 가져와서 핵심 발표 3가지를 요약해줘. 출처 citation 포함.":
        "获取 https://www.anthropic.com/news 的内容并总结 3 项核心公告。包含来源 citation。",
    "permissions.allow / permissions.deny 는 set-union, 나머지는 top-level override.":
        "permissions.allow / permissions.deny 为 set-union，其余为 top-level override。",
    "사용자 확인 없이 요구사항 → 실행 → 검증까지 단일 흐름으로 끝까지 돌리는 자율 파이프라인 (OMC /autopilot 에 대응).":
        "无需用户确认，以单一流程从需求 → 执行 → 验证一路跑到底的自主管道(对应 OMC /autopilot)。",
    "Wiki 시스템 — 세션 내 지식 베이스 (LazyClaude는 Claude Docs Hub + Prompt Library 로 대체)":
        "Wiki 系统——会话内知识库(LazyClaude 以 Claude Docs Hub + Prompt Library 替代)",
    "깨뜨렸는지 진단. Anthropic cache-diagnosis 베타(헤더 cache-diagnosis-2026-04-07) 사용, ":
        "诊断是什么破坏了它。使用 Anthropic cache-diagnosis 测试版(头部 cache-diagnosis-2026-04-07)，",
    "요청을 작업 유형별로 더 저렴한 모델/프로바이더(Haiku·DeepSeek·Ollama 등)로 라우팅. 대시보드에 전용 탭이 있어요.":
        "按任务类型将请求路由到更便宜的模型/提供商(Haiku·DeepSeek·Ollama 等)。仪表板中有专用标签页。",
    "샌드박스 안에서 모든 Unix 도메인 소켓 연결 허용. /var/run/docker.sock 등 강력한 서비스 노출 위험 — 신중히.":
        "允许在沙箱内连接所有 Unix 域套接字。存在暴露 /var/run/docker.sock 等强大服务的风险 — 请谨慎。",
    "system 블록에 매 요청마다 바뀌는 값(타임스탬프)을 넣어 캐시가 깨지는 전형적 사례. 예상 진단: system_changed.":
        "在 system 块中放入每次请求都会变化的值(时间戳)导致缓存失效的典型案例。预期诊断: system_changed。",
    "완료 기준 통과할 때까지 verify → fix 루프를 반복 (OMC /ralph 에 대응). 최대 5회 반복, 피드백 자동 주입.":
        "重复 verify → fix 循环直到通过完成标准 (对应 OMC /ralph)。最多重复 5 次，自动注入反馈。",
    "Claude Code 가 OTLP/HTTP JSON 으로 보낸 메트릭(비용·토큰·도구 결정·코드 라인·커밋)을 실시간 집계합니다.":
        "实时聚合 Claude Code 通过 OTLP/HTTP JSON 发送的指标(成本·令牌·工具决策·代码行数·提交)。",
    "활성 CLI 세션 — Claude Code CLI 세션의 PID·RSS·CPU·idle 시간 + 터미널 포커스 / SIGTERM":
        "活动 CLI 会话 — Claude Code CLI 会话的 PID·RSS·CPU·idle 时间 + 终端聚焦 / SIGTERM",
    "workflows store 의 costs 배열을 병합 (각 노드 실행 시 _record_workflow_cost 로 쌓임).":
        "合并 workflows store 的 costs 数组 (每次节点执行时通过 _record_workflow_cost 累积)。",
    "열린 포트 모니터 — TCP/UDP listening 소켓 + PID/Command/User · 한 번 클릭으로 프로세스 종료":
        "开放端口监视器 — TCP/UDP listening 套接字 + PID/Command/User · 一键终止进程",
    "외부 OMC CLI를 추가로 설치하면 Claude Code 세션 안에서도 슬래시 명령으로 호출 가능 (보완 관계, 충돌 없음)":
        "额外安装外部 OMC CLI 后，也可以在 Claude Code 会话内通过斜杠命令调用 (互补关系，无冲突)",
    "키는 ~/.claude-dashboard-admin.json 에 파일 권한 600으로 저장되며 화면에는 마스킹되어 표시됩니다.":
        "密钥以文件权限 600 保存在 ~/.claude-dashboard-admin.json 中，并在屏幕上以掩码形式显示。",
    "사용자를 위한 새 output style (~/.claude/output-styles/<name>.md) 초안을 작성하세요.":
        "为用户起草一个新的 output style (~/.claude/output-styles/<name>.md)。",
    "서버 재시작: lsof -iTCP:$PORT (default 19500) kill 후 python3 server.py 재실행":
        "重启服务器: lsof -iTCP:$PORT (default 19500) kill 后重新运行 python3 server.py",
    "~/.claude/file-history 에 남긴 백업을 읽어 프롬프트마다 변경 파일·복원 가능 여부를 표시. 읽기 전용.":
        "读取 ~/.claude/file-history 中留下的备份，按提示显示变更文件·可否恢复。只读。",
    "위 환경변수를 설정하고 Claude Code 를 실행하면, 다음 내보내기 주기(기본 60초)에 메트릭이 여기에 나타납니다.":
        "设置上述环境变量并运行 Claude Code 后，指标将在下一个导出周期(默认 60 秒)显示在这里。",
    "web_search/web_fetch 와 함께 쓰면 무료, 아니면 월 1,550 시간 무료 후 컨테이너당 $0.05/시간.":
        "与 web_search/web_fetch 一起使用时免费，否则每月免费 1,550 小时，之后每个容器 $0.05/小时。",
    "팀 리더보드 — 조직 Admin Analytics API(usage_report/claude_code)에서 사용자/액터별 ":
        "团队排行榜 — 从组织 Admin Analytics API(usage_report/claude_code) 按用户/执行者 ",
    "매 세션 시작 시 로드되어 토큰을 소모합니다. 필요 섹션만 유지하거나 skill/prompt library 로 분리 고려.":
        "每次会话开始时加载并消耗令牌。考虑只保留所需部分，或拆分到 skill/prompt library。",
    "샌드박스로 실행 가능한 Bash 명령을 매번 묻지 않고 자동 승인. deny 규칙과 위험 경로 삭제는 여전히 프롬프트됨.":
        "自动批准可在沙箱中运行的 Bash 命令，无需每次询问。deny 规则和危险路径删除仍会提示。",
    "max-iter / completion-promise / 예산 USD / 수동 cancel 4중 안전장치 안에서 반복. ":
        "在 max-iter / completion-promise / 预算 USD / 手动 cancel 四重安全机制内循环。 ",
    "CLAUDE.md·메모리 파일을 caveman 포맷으로 압축해 입력 토큰 절감. /caveman-compress <파일>":
        "将 CLAUDE.md·记忆文件压缩为 caveman 格式以节省输入令牌。/caveman-compress <文件>",
    "Security Scan — ~/.claude 전체(settings/CLAUDE.md/hooks/agents/mcp)를 ":
        "Security Scan — 对整个 ~/.claude(settings/CLAUDE.md/hooks/agents/mcp) ",
    "세션 처음→끝 진행 타임라인. user 프롬프트 / Agent 위임 / 큰 도구 호출만 추려서 그래프 노드/엣지 형태로.":
        "会话从头→尾的进度时间线。仅挑选 user 提示 / Agent 委派 / 大型工具调用，以图节点/边的形式呈现。",
    "동일 작업을 5개 병렬 에이전트로 분할 실행 후 취합 (OMC /ultrawork 에 대응). 속도 우선, 비용 5배.":
        "将同一任务拆分给 5 个并行代理执行后汇总 (对应 OMC /ultrawork)。速度优先，成本 5 倍。",
    "Opus/Sonnet 은 1024 토큰, Haiku 는 2048 토큰이다. TTL 은 기본 5분, 1시간 옵션도 있다.":
        "Opus/Sonnet 为 1024 令牌，Haiku 为 2048 令牌。TTL 默认 5 分钟，也有 1 小时选项。",
    "Anthropic 호스팅 sandbox — Bash + 파일 연산 (stdout/stderr/return_code). ":
        "Anthropic 托管 sandbox — Bash + 文件操作 (stdout/stderr/return_code)。 ",
    "기간별 사용량을 Markdown과 인쇄용 HTML로 내보냅니다. 모든 수치는 세션 인덱스에서 읽기 전용으로 집계됩니다.":
        "将按时间段的用量导出为 Markdown 和打印用 HTML。所有数字均从会话索引以只读方式聚合。",
    "Claude API 전용(Bedrock/Vertex 미지원). API 키가 없으면 오프라인 구조 diff로 폴백합니다.":
        "仅限 Claude API(不支持 Bedrock/Vertex)。没有 API 密钥时回退到离线结构 diff。",
    "취합된 결과물을 PRD 수용 조건과 대조. 통과면 'PASS', 아니면 'FAIL — <실패 항목 목록>' 으로 시작":
        "将汇总结果与 PRD 验收条件对照。通过则以 'PASS' 开头，否则以 'FAIL — <失败项列表>' 开头",
    "Claude Code CLI 가 설치되어 있지 않아 설치 명령을 실행할 수 없습니다. 명령을 복사해 직접 실행하세요.":
        "未安装 Claude Code CLI，无法运行安装命令。请复制命令后自行运行。",
    "보안상 **대화 컨텍스트에 이미 등장한 URL** 만 fetch 가능 (Claude 가 임의 생성한 URL 불가). ":
        "出于安全考虑，只能 fetch **已在对话上下文中出现过的 URL** (不允许 Claude 任意生成的 URL)。 ",
    "SessionStart 훅으로 이전 세션 요약/체크리스트를 자동 주입하면 모든 프로젝트에서 맥락 로딩이 안정화됩니다.":
        "通过 SessionStart 钩子自动注入上一会话的摘要/清单，可让所有项目的上下文加载更稳定。",
    "메모리 관리 — vm_stat 기반 시스템 메모리 + 상위 30 프로세스 + idle Claude Code 일괄 종료":
        "内存管理 — 基于 vm_stat 的系统内存 + 前 30 个进程 + 批量终止 idle Claude Code",
    "Claude Docs Hub — docs.anthropic.com 주요 페이지(Claude Code / API / ":
        "Claude Docs Hub — docs.anthropic.com 主要页面(Claude Code / API / ",
    "Prompt caching 은 반복되는 긴 컨텍스트(시스템 프롬프트, 도구 정의, 참조 문서)를 서버 측에 캐시해 ":
        "Prompt caching 将重复的长上下文(系统提示、工具定义、参考文档)缓存在服务器端，从而 ",
    "🦞 Ralph 루프 — Geoffrey Huntley의 'Ralph Wiggum' 패턴. 같은 PROMPT.md를 ":
        "🦞 Ralph 循环 — Geoffrey Huntley 的 'Ralph Wiggum' 模式。将同一个 PROMPT.md ",
    "echo '# ANTHROPIC_API_KEY=sk-... 를 설정한 후: uv run python main.py'":
        "echo '# 设置 ANTHROPIC_API_KEY=sk-... 后: uv run python main.py'",
    "[이미지 첨부됨 — claude-cli 는 vision 미지원, claude-api 또는 vision 모델 사용]":
        "[已附加图像 — claude-cli 不支持 vision，请使用 claude-api 或 vision 模型]",
    "출력 스타일 점검 — /output-style 명령 폐기(v2.1.91 제거, /config 로 대체) 진단 + ":
        "输出样式检查 — 诊断已废弃的 /output-style 命令(v2.1.91 移除，由 /config 替代) + ",
    "Agent SDK 스캐폴드 — claude-agent-sdk Python(uv) / TypeScript(bun) ":
        "Agent SDK 脚手架 — claude-agent-sdk Python(uv) / TypeScript(bun) ",
    "Claude CLI 로 최신 Anthropic 발표 조회 → 기존 카탈로그에 없는 항목만 dynamic 에 저장.":
        "通过 Claude CLI 查询最新 Anthropic 公告 → 仅将现有目录中没有的条目保存到 dynamic。",
    "사용자의 Claude Code 를 위한 ~/.claude/settings.json 'hooks' 섹션을 만드세요.":
        "为用户的 Claude Code 创建 ~/.claude/settings.json 的 'hooks' 部分。",
    "모호한 요구사항을 Socratic 질문으로 명확화한 후 설계까지 (OMC /deep-interview 에 대응).":
        "通过 Socratic 提问澄清模糊需求后直至完成设计 (对应 OMC /deep-interview)。",
    "Extended Thinking 실험실 — Opus/Sonnet 의 thinking block 을 분리 시각화. ":
        "Extended Thinking 实验室 — 将 Opus/Sonnet 的 thinking block 分离可视化。 ",
    "오케스트레이터 — Slack/Telegram/Discord 채널에 멘션하면 Claude(플래너)가 작업을 분해해 ":
        "编排器 — 在 Slack/Telegram/Discord 频道中提及后，Claude(规划器)会分解任务并 ",
    "반복 작업(배포/마이그레이션/PR 만들기 등)을 스킬로 정의하면 Claude가 자동 활용. 다양성 축을 올립니다.":
        "将重复性任务(部署/迁移/创建 PR 等)定义为技能后，Claude 会自动使用。提升多样性维度。",
    "고급: 사용자 정의 프록시로 아웃바운드 트래픽 라우팅(TLS 검사/필터링/로깅). 미설정이면 내장 프록시 사용.":
        "高级: 通过自定义代理路由出站流量(TLS 检查/过滤/日志)。未设置时使用内置代理。",
    "이미 활성화된 플러그인은 제외하고, candidates 안에서만 골라 최대 5개까지 우선순위 매겨 추천하세요. ":
        "排除已启用的插件，仅从 candidates 中挑选，按优先级推荐最多 5 个。 ",
    "OpenClaw Gateway 외부 연동 (LazyClaude는 Event Forwarder 탭으로 부분 대체)":
        "OpenClaw Gateway 外部集成 (LazyClaude 以 Event Forwarder 标签页部分替代)",
    "사용자가 자주 호출하는 도구(top_tools)를 보고 어떤 MCP 가 워크플로우를 더 효율적으로 만들지 판단.":
        "查看用户经常调用的工具(top_tools)，判断哪个 MCP 能让工作流更高效。",
    "Anthropic 서버 측 URL 본문 fetch + citation. GA — beta header 불필요. ":
        "Anthropic 服务器端 URL 正文 fetch + citation。GA — 无需 beta header。 ",
    "플러그인 마켓 — 설치된 마켓플레이스(.claude-plugin/marketplace.json)의 플러그인을 ":
        "插件市场 — 将已安装市场(.claude-plugin/marketplace.json)中的插件 ",
    "Doctor 진단 — 설치 무결성 (LazyClaude는 Security Scan + AI 평가 탭으로 대체)":
        "Doctor 诊断 — 安装完整性 (LazyClaude 以 Security Scan + AI 评估标签页替代)",
    "Admin 사용량·비용 — Anthropic Admin Usage/Cost API 로 조직 단위 실제 청구된 ":
        "Admin 用量·费用 — 通过 Anthropic Admin Usage/Cost API 获取组织级实际计费 ",
    "이전 사이클 보고를 검토하고 미해결 항목과 새 리스크를 반영해 다음 단계 업무를 페르소나별로 다시 분배하세요.":
        "审查上一周期的报告，结合未解决项与新风险，按 persona 重新分配下一阶段的任务。",
    "실시간 텔레메트리 — Claude Code 의 OpenTelemetry(OTLP/HTTP JSON) 메트릭을 ":
        "实时遥测 — 将 Claude Code 的 OpenTelemetry(OTLP/HTTP JSON) 指标 ",
    "AppleScript 로 Terminal 새 창에 cd + 명령 붙여넣기 (실제 실행은 사용자 Enter).":
        "通过 AppleScript 在新的 Terminal 窗口中粘贴 cd + 命令 (实际执行由用户按 Enter)。",
    "파이썬 dict 의 키 순서 보존은 어느 버전부터 공식 보증되는지, 그리고 왜 이전에는 안 됐는지 설명해줘.":
        "请说明 Python dict 的键顺序保留从哪个版本起获得正式保证，以及为什么之前不行。",
    "활성화하고 응답 블록(server_tool_use / *_tool_result / text)을 분류 시각화.":
        "启用并对响应块(server_tool_use / *_tool_result / text)进行分类可视化。",
    "라이브 진행 SSE, iteration 비용 추적, CLI(tools/ralph_loop.py) 동시 지원.":
        "支持实时进度 SSE、iteration 费用跟踪，并同时支持 CLI(tools/ralph_loop.py)。",
    "모델은 이 스키마에 맞는 JSON 만 반환합니다. 후속 노드는 검증된 JSON 문자열을 입력으로 받습니다.":
        "模型只返回符合此 schema 的 JSON。后续节点以经过验证的 JSON 字符串作为输入。",
    "pluginKey ('<plugin>@<market>') → hooks.json 경로 (없으면 None).":
        "pluginKey ('<plugin>@<market>') → hooks.json 路径 (不存在则为 None)。",
    "PDF는 서버에서 직접 생성하지 않습니다 (순수 stdlib 한계 — 바이너리 PDF 라이브러리 없음). ":
        "PDF 不在服务器上直接生成 (纯 stdlib 限制 — 无二进制 PDF 库)。 ",
    "echo '# ANTHROPIC_API_KEY=sk-... 를 설정한 후: bun run index.ts'":
        "echo '# 设置 ANTHROPIC_API_KEY=sk-... 后: bun run index.ts'",
    "- **데이터 출처**: `~/.claude-dashboard.db` sessions 인덱스 (읽기 전용)":
        "- **数据来源**: `~/.claude-dashboard.db` sessions 索引 (只读)",
    "계획을 받아 각 모듈별 세부 요구사항·수용 조건(Acceptance Criteria)·테스트 포인트 작성":
        "接收计划，为每个模块编写详细需求·验收条件(Acceptance Criteria)·测试点",
    "claude-code-router·awesome-claude-code 등 인기 Claude 하네스 도구 ":
        "claude-code-router·awesome-claude-code 等热门 Claude harness 工具 ",
    "프로젝트별 추천 PROMPT.md 자동 생성 (CLAUDE.md + git log + TODO 합성). ":
        "按项目自动生成推荐的 PROMPT.md (综合 CLAUDE.md + git log + TODO)。 ",
    "Extended Thinking 은 Haiku 에서 지원되지 않습니다. Opus 또는 Sonnet 사용.":
        "Haiku 不支持 Extended Thinking。请使用 Opus 或 Sonnet。",
    "frontmatter 의 `tools:` 필드를 list 로 — JSON 배열 또는 쉼표 구분 문자열.":
        "将 frontmatter 的 `tools:` 字段解析为 list — JSON 数组或逗号分隔的字符串。",
    "$hud — 현재 상태 1-2줄 요약 (phase · last action · next blocker)":
        "$hud — 当前状态 1-2 行摘要 (phase · last action · next blocker)",
    "프로젝트·모델별·상위 세션)를 Markdown + 자체완결형 인쇄용 HTML 로 내보낸다. 읽기 전용.":
        "按项目·按模型·Top 会话)导出为 Markdown + 自包含可打印 HTML。只读。",
    "MCP 서버 env 에 시크릿이 평문. 외부 env var 참조 또는 secret manager 사용.":
        "MCP 服务器 env 中的密钥为明文。请使用外部 env var 引用或 secret manager。",
    "Claude Code 규칙: ':*' 는 패턴 맨 끝에만 올 수 있음. 중간에 쓰려면 '*' 사용. ":
        "Claude Code 规则: ':*' 只能出现在模式的最末尾。要在中间使用，请改用 '*'。 ",
    "카테고리별(시스템 프롬프트·도구 정의·MCP 도구·CLAUDE.md/메모리·대화 기록·남은 공간)로 ":
        "按类别(系统提示·工具定义·MCP 工具·CLAUDE.md/记忆·对话记录·剩余空间) ",
    "$doctor — 설치/헬스 진단 (의존성 · lockfile · env mismatch 체크리스트)":
        "$doctor — 安装/健康诊断 (依赖 · lockfile · env mismatch 检查清单)",
    "caveman-commit/compress/help/review/stats) 설치 상태·재설치·압축 ":
        "caveman-commit/compress/help/review/stats) 安装状态·重新安装·压缩 ",
    "세션 사용량·비용에서 통계적으로 비정상적인 지점을 로컬에서 탐지합니다 (ML 없음, 요청 시 계산).":
        "在本地检测会话用量·费用中的统计异常点 (无 ML，按请求计算)。",
    "터미널에서 `claude auth login` 을 실행. 인터랙티브 명령이므로 터미널 앱을 열어준다.":
        "在终端中运行 `claude auth login`。由于是交互式命令，会为你打开终端应用。",
    "v2.33.5 — timeout 5s → 2s (병렬 프로빙에서 한 도구가 5s 걸리면 전체 느림).":
        "v2.33.5 — timeout 5s → 2s (并行探测中若某个工具耗时 5s，整体就会变慢)。",
    "Event Forwarder — Claude Code hooks 이벤트(PostToolUse 등)를 ":
        "Event Forwarder — 将 Claude Code hooks 事件(PostToolUse 等) ",
    "공동 창업자에는 전 OpenAI 연구진 다수가 포함됐다. 회사의 플래그십 모델은 Claude 이며, ":
        "联合创始人中包括多名前 OpenAI 研究人员。公司的旗舰模型是 Claude， ",
    "프롬프트에 URL 을 직접 포함해야 fetch 가능 (컨텍스트에 없는 URL 은 fetch 불가).":
        "URL 必须直接包含在提示中才能 fetch (不在上下文中的 URL 无法 fetch)。",
    "Vision / PDF 실험실 — 이미지(PNG/JPG/WebP/GIF) 또는 PDF 를 업로드해 ":
        "Vision / PDF 实验室 — 上传图像(PNG/JPG/WebP/GIF)或 PDF 以 ",
    "프롬프트 캐시 실험실 — Anthropic Messages API 의 cache_control 을 ":
        "提示缓存实验室 — 将 Anthropic Messages API 的 cache_control ",
    "CHANGELOG.md 에서 최근 max_entries 개 릴리스 섹션만 반환. 챗봇 프롬프트 용.":
        "仅返回 CHANGELOG.md 中最近 max_entries 个发布版块。用于聊天机器人提示。",
    "HTML/SVG 내 위험 요소 제거. img 는 허용 (img-src data: 로 CSP 제한).":
        "移除 HTML/SVG 中的危险元素。允许 img (通过 img-src data: 进行 CSP 限制)。",
    "macOS: 기본 Terminal.app 에서 cmd 실행. 그 외 플랫폼: Popen 백그라운드.":
        "macOS: 在默认 Terminal.app 中运行 cmd。其他平台: Popen 后台运行。",
    "stdlib 로 multipart/form-data POST. single field 'file'.":
        "使用 stdlib 进行 multipart/form-data POST。单一字段 'file'。",
    "AI 프로바이더 — Claude/GPT/Gemini/Ollama/Codex 멀티 AI 오케스트라. ":
        "AI 提供商 — Claude/GPT/Gemini/Ollama/Codex 多 AI 编排。 ",
    "플러그인 자체는 Claude Code 에서 `/plugin uninstall ...` 로 별도 제거":
        "插件本身需在 Claude Code 中通过 `/plugin uninstall ...` 单独移除",
    "ollama CLI 가 설치되어 있지 않습니다. https://ollama.com 에서 설치하세요.":
        "未安装 ollama CLI。请从 https://ollama.com 安装。",
    "채널별 fallback 체인 + 일일 예산 cap, 에이전트 간 라이브 보고(Agent Bus).":
        "按通道的 fallback 链 + 每日预算 cap，代理间实时汇报(Agent Bus)。",
    "Anthropic 서버 측 웹 검색 + citation. GA — beta header 불필요. ":
        "Anthropic 服务器端网页搜索 + citation。GA — 无需 beta header。 ",
    "체크포인트 — 세션별 프롬프트 단위 파일 스냅샷 타임라인. /rewind·Esc Esc 되감기가 ":
        "检查点 — 按会话、按提示的文件快照时间线。/rewind·Esc Esc 回退 ",
    "이전 메시지를 덧붙이지 않고 수정하면 캐시가 깨진다. 예상 진단: messages_changed.":
        "若修改而非追加之前的消息，缓存会失效。预期诊断: messages_changed。",
    "훅 항목이 rtk 를 참조하는지 재귀 판별 (command 필드 포함 · 중첩 hooks 지원).":
        "递归判断钩子条目是否引用 rtk (含 command 字段 · 支持嵌套 hooks)。",
    "skill / prompt library / workflow template 으로 만드시겠습니까?":
        "要将其创建为 skill / prompt library / workflow template 吗？",
    "신뢰할 수 없는 패키지면 임의 코드 실행 위험. github 레포의 signature 확인 권장.":
        "若是不可信的包，存在任意代码执行风险。建议核实 github 仓库的 signature。",
    "SQLite 세션 인덱스의 flat cache_creation_tokens 로는 분리 불가합니다.":
        "无法通过 SQLite 会话索引中的扁平 cache_creation_tokens 进行拆分。",
    "기본 도구 3종 (get_weather / calculator / web_search mock).":
        "3 种基础工具 (get_weather / calculator / web_search mock).",
    "추천 프로파일(혹은 임의 패치)을 현재 settings와 병합한 preview + diff 반환.":
        "返回将推荐配置文件(或任意补丁)与当前 settings 合并后的 preview + diff.",
    "알림 webhook URL sanitize. Slack/Discord 화이트리스트 호스트만 허용.":
        "对通知 webhook URL 做 sanitize. 仅允许 Slack/Discord 白名单主机.",
    "Tool Use 플레이그라운드 — tool schema 정의 → Messages API 호출 → ":
        "Tool Use 演练场 — 定义 tool schema → 调用 Messages API → ",
    "프로젝트의 모든 세션을 시간순으로 묶어 그래프 데이터로. 세션 단위 노드 + 도구·에이전트 요약.":
        "将项目的所有会话按时间顺序聚合为图数据. 会话级节点 + 工具·代理摘要.",
    "Session Replay — Claude Code JSONL 세션 로그를 타임라인으로 재생 · ":
        "Session Replay — 将 Claude Code JSONL 会话日志以时间线形式回放 · ",
    "Artifacts Viewer — 워크플로우 출력물(HTML/SVG/Markdown/JSON)을 ":
        "Artifacts Viewer — 将工作流输出物(HTML/SVG/Markdown/JSON) ",
    "구조화 출력은 Anthropic 모델에서만 스키마가 강제됩니다. 다른 프로바이더는 베스트에포트.":
        "结构化输出仅在 Anthropic 模型上强制执行 schema. 其他提供商为尽力而为.",
    "ANTHROPIC_API_KEY 미설정 — aiProviders 탭에서 저장하거나 환경변수 설정":
        "未设置 ANTHROPIC_API_KEY — 请在 aiProviders 标签页保存或设置环境变量",
    "에이전트에서 /caveman (lite·full·ultra·wenyan), Node ≥18 필요":
        "在代理中使用 /caveman (lite·full·ultra·wenyan), 需要 Node ≥18",
    "세션·코드 라인·커밋·PR·토큰·추정 비용을 기간별로 집계해 순위. 조직 admin 키 필요, ":
        "按时间段汇总会话·代码行·提交·PR·令牌·估算成本并排名. 需要组织 admin 密钥, ",
    "프롬프트 Eval — 어서션 기반 회귀 테스트. 테스트 셋(케이스+어서션)을 여러 프로바이더에 ":
        "提示词 Eval — 基于断言的回归测试. 将测试集(用例+断言)在多个提供商上 ",
    "캐시 진단 — 두 연속 요청을 비교해 어느 캐시 브레이크포인트가 prompt-cache 히트를 ":
        "缓存诊断 — 比较两个连续请求, 判断哪个缓存断点使 prompt-cache 命中 ",
    "tools 배열의 순서가 바뀌면 prefix 가 깨진다. 예상 진단: tools_changed.":
        "tools 数组顺序变化会破坏 prefix. 预期诊断: tools_changed.",
    "복잡한 리뷰는 ecc:code-reviewer, ecc:security-reviewer 로 위임":
        "复杂评审委托给 ecc:code-reviewer, ecc:security-reviewer",
    "모델 다운로드 진행 상태. GET /api/ollama/pull-status?pullId=...":
        "模型下载进度. GET /api/ollama/pull-status?pullId=...",
    "Ollama 세 프로바이더에 돌려 cosine similarity + rank 매트릭스 비교. ":
        "Ollama 三个提供商上运行, 比较 cosine similarity + rank 矩阵. ",
    "1시간 캐시(cache_control ttl='1h') 사용 시에만 cache_creation.":
        "仅在使用 1 小时缓存(cache_control ttl='1h')时才有 cache_creation.",
    "대시보드 UI 용 — LazyClaude MCP 서버 진입점 스크립트 경로 + 노출 도구 목록.":
        "用于仪表盘 UI — LazyClaude MCP 服务器入口脚本路径 + 暴露的工具列表.",
    "절대 한도(limit)는 로컬 데이터에 없어 알 수 없음 · 사용량은 토큰 합계 기반 proxy":
        "绝对上限(limit)不在本地数据中, 无法得知 · 用量为基于令牌总和的 proxy",
    "/autopilot — 요구사항 → 계획 → 실행 → 검증 단일 흐름 (bt-autopilot)":
        "/autopilot — 需求 → 计划 → 执行 → 验证单一流程 (bt-autopilot)",
    "레이트리밋 · 쿼터 — 롤링 5시간 윈도우 · 주간 쿼터 · 주간 Opus 윈도우의 리셋 시각/":
        "速率限制 · 配额 — 滚动 5 小时窗口 · 每周配额 · 每周 Opus 窗口的重置时间/",
    "이 스킬을 삭제할까요? <cwd>/.claude/skills/<id>/ 디렉터리가 제거됩니다.":
        "要删除此技能吗? <cwd>/.claude/skills/<id>/ 目录将被移除.",
    "추정값 (시스템 프롬프트 · 도구 정의 · MCP 도구는 트랜스크립트에 저장되지 않아 추정).":
        "估算值 (系统提示 · 工具定义 · MCP 工具未保存在转录中, 因此为估算).",
    "압축 커밋 메시지 생성 (Conventional Commits). /caveman-commit":
        "生成压缩提交信息 (Conventional Commits). /caveman-commit",
    "도달 시 알림을 기록·조회·해제. 지출은 세션 토큰을 cost_timeline 요금으로 추정.":
        "达到时记录·查看·解除告警. 支出按 cost_timeline 费率从会话令牌估算.",
    "사용자의 ~/.claude/settings.json 'permissions' 를 최적화하세요.":
        "请优化用户的 ~/.claude/settings.json 'permissions'.",
    "_(승인 :white_check_mark: / 거부 :x: / 자유답장으로 다음 지시 입력)_":
        "_(批准 :white_check_mark: / 拒绝 :x: / 自由回复以输入下一条指令)_",
    "완료 후에는 (1) 무엇을 했는지 (2) 한계/막힌 지점 (3) 기획자에게 권하는 다음 단계를":
        "完成后请说明 (1) 做了什么 (2) 限制/受阻之处 (3) 向规划者建议的下一步",
    "relpath 가 base 하위 경로인지 검증하고 실제 경로 반환. 바깥으로 나가면 None.":
        "验证 relpath 是否在 base 之下并返回实际路径. 越界则返回 None.",
    "(팀 개발/리서치/병렬 3) + 커스텀 템플릿 저장·🖥️ Terminal 새 세션 spawn·":
        "(团队开发/调研/并行 3) + 保存自定义模板·🖥️ Terminal 新会话 spawn·",
    "Ollama HTTP API (/api/generate) 로 실행 — 인터랙티브 문제 없음.":
        "通过 Ollama HTTP API (/api/generate) 执行 — 无交互问题.",
    "근접도. ~/.claude 세션 로그에서 한도 메시지를 추출하는 best-effort 위젯.":
        "接近程度. 从 ~/.claude 会话日志提取限额消息的 best-effort 小组件.",
    "Model Benchmark — 사전 정의 프롬프트 셋(기본 Q&A / 코드 / 추론) × ":
        "Model Benchmark — 预定义提示词集(基础 Q&A / 代码 / 推理) × ",
    "시스템/도구/메시지 블록에 적용해 cache_creation / cache_read 토큰과 ":
        "应用于系统/工具/消息块, 查看 cache_creation / cache_read 令牌与 ",
    "결과물이 요구사항을 만족하면 'PASS' 로 시작, 아니면 'FAIL — <이유>' 로 시작":
        "若结果满足需求则以 'PASS' 开头, 否则以 'FAIL — <原因>' 开头",
    "이상 탐지 — 세션 사용량·비용의 통계적 이상치(일별 스파이크·프로젝트 급증·대형 세션)를 ":
        "异常检测 — 将会话用量·成本的统计异常值(每日尖峰·项目激增·大型会话) ",
    "Bash 샌드박스 — Bash 도구의 OS 수준 격리(파일·네트워크) 설정을 읽고 안전하게 ":
        "Bash 沙箱 — 读取 Bash 工具的 OS 级隔离(文件·网络)设置并安全地 ",
    "Batch API 관리 — 대용량 프롬프트 배치 제출·상태 폴링·결과 JSONL 다운로드. ":
        "Batch API 管理 — 提交大批量提示词·轮询状态·下载结果 JSONL. ",
    "에이전트·스킬·명령·플러그인·훅·MCP 설정을 망라한 대형 Claude Code 툴킷 모음.":
        "涵盖代理·技能·命令·插件·钩子·MCP 配置的大型 Claude Code 工具包合集.",
    "settings.json이 올바른 JSON이 아닙니다. 손상 방지를 위해 저장을 거부합니다.":
        "settings.json 不是有效的 JSON. 为防止损坏, 拒绝保存.",
    "cron 표현식이 현재 시각과 매칭되는지. 형식: min hour dom month dow.":
        "cron 表达式是否匹配当前时间. 格式: min hour dom month dow.",
    "Agent SDK / Models / Account) 를 카테고리별 카드로 색인 + 검색. ":
        "Agent SDK / Models / Account) 按类别以卡片形式索引 + 搜索. ",
    "Files API — Anthropic 파일 업로드 · 목록 · 삭제 + 업로드한 파일을 ":
        "Files API — Anthropic 文件上传 · 列表 · 删除 + 将已上传的文件 ",
    "slack token not configured (see Wizard → Slack 설정)":
        "slack token not configured (参见 Wizard → Slack 设置)",
    "터미널 status bar HUD (LazyClaude는 브라우저 대시보드 자체가 HUD)":
        "终端 status bar HUD (LazyClaude 的浏览器仪表盘本身就是 HUD)",
    "OMC 의 Codex 버전 — Codex 세션 안에서 $ 키워드로 호출하는 워크플로우 도구":
        "OMC 的 Codex 版本 — 在 Codex 会话内通过 $ 关键字调用的工作流工具",
    "프롬프트 + cache_control 로 Messages API 호출 → usage 반환.":
        "以提示词 + cache_control 调用 Messages API → 返回 usage.",
    "리포트 · 내보내기 — 기간별(7/30일) 사용량 리포트(토큰·추정 비용·일별 추이·상위 ":
        "报告 · 导出 — 按时间段(7/30天)的用量报告(令牌·估算成本·每日趋势·排名靠前 ",
    "메모리 감사 — CLAUDE.md·프로젝트 메모리가 모든 대화에 주입하는 컨텍스트 부하를 ":
        "记忆审计 — 将 CLAUDE.md·项目记忆注入每次对话的上下文负载 ",
    "프로젝트 뼈대를 UI 로 생성. 템플릿 3종(basic/tool-use/memory) + ":
        "通过 UI 生成项目骨架。3 种模板（basic/tool-use/memory）+ ",
    "잘못된 규칙을 자동 교정 — ':*' 가 중간이면 '*' 로 치환. 변경 내역 함께 반환.":
        "自动修正错误规则 — ':*' 出现在中间时替换为 '*'。同时返回变更记录。",
    "tool_use 블록 수신 시 tool_result 를 수동 입력해 멀티 턴 체인 실행. ":
        "收到 tool_use 块时手动输入 tool_result 以执行多轮链。 ",
    "content 를 1줄 요약 문자열로. content 는 list[dict] 또는 str.":
        "将 content 概括为一行字符串。content 为 list[dict] 或 str。",
    "컨텍스트 인스펙터 — 대시보드 자체 /context. 최신 턴의 컨텍스트 윈도우 점유율을 ":
        "上下文检查器 — 仪表盘自带的 /context。显示最新一轮的上下文窗口占用率 ",
    "🧪 code_execution. Anthropic 서버가 직접 실행하는 도구를 체크박스로 ":
        "🧪 code_execution。通过复选框选择由 Anthropic 服务器直接执行的工具 ",
    "Embedding 비교 실험실 — 같은 쿼리/문서 집합을 Voyage / OpenAI / ":
        "Embedding 对比实验室 — 将同一查询/文档集合用于 Voyage / OpenAI / ",
    "macOS 전용. 샌드박스가 조회 가능한 XPC/Mach 서비스 이름. * 접미사 지원.":
        "仅限 macOS。沙箱可查询的 XPC/Mach 服务名称。支持 * 后缀。",
    "사용량 수치는 세션 토큰 합계 기반 근사치(proxy)입니다. 절대 한도(limit)는 ":
        "用量数值是基于会话令牌总和的近似值（proxy）。绝对限额（limit）为 ",
    "Citations 플레이그라운드 — 문서를 제공하고 citations.enabled 로 ":
        "Citations 演练场 — 提供文档并通过 citations.enabled ",
    "echo '📋 이전 세션 요약은 $HOME/.claude/session-data/ 참조'":
        "echo '📋 上一会话摘要请参阅 $HOME/.claude/session-data/'",
    "오늘 — 오늘 하루 토큰·비용·세션·상위 프로젝트·최근 활동을 한 화면에 요약한 코크핏.":
        "今日 — 在一个页面汇总当天令牌、费用、会话、热门项目和最近活动的驾驶舱。",
    "/ralph — verify → fix 루프 (bt-ralph, max 5 cycles)":
        "/ralph — verify → fix 循环（bt-ralph，max 5 cycles）",
    "전체 셋업을 Claude 에게 평가받음. 비싸므로 force=true 시에만 새로 호출.":
        "由 Claude 评估整体设置。开销较大，仅在 force=true 时重新调用。",
    "Claude Code 의 프로젝트 슬러그 규칙: '/' → '-', 선두에 '-' 추가.":
        "Claude Code 的项目 slug 规则：'/' → '-'，并在开头添加 '-'。",
    "선택한 프롬프트로 start → session → output 3 노드 워크플로우 생성.":
        "用所选提示词创建 start → session → output 3 节点工作流。",
    "flat cache_creation_tokens 만 보존하므로 여기엔 포함되지 않습니다.":
        "仅保留扁平的 cache_creation_tokens，因此不包含在此处。",
    "랩 히스토리 / API usage 객체 → 표준화된 토큰 dict + TTL split.":
        "实验室历史 / API usage 对象 → 标准化令牌 dict + TTL split。",
    "ANTHROPIC_ADMIN_KEY 환경변수가 설정되어 있어 여기서 관리할 수 없습니다.":
        "已设置 ANTHROPIC_ADMIN_KEY 环境变量，无法在此处管理。",
    "Anthropic Messages API — claude CLI 없이 직접 API 호출.":
        "Anthropic Messages API — 不经 claude CLI 直接调用 API。",
    "5분 vs 1시간 TTL 분할 데이터가 없습니다. Anthropic usage 객체는 ":
        "没有 5 分钟 vs 1 小时 TTL 拆分数据。Anthropic usage 对象 ",
    "~/.claude.json 의 mcpServers 수를 합산 (프로젝트 스코프 포함).":
        "汇总 ~/.claude.json 中的 mcpServers 数量（包含项目作用域）。",
    "워크플로우 버전 히스토리. GET /api/workflows/history?id=...":
        "工作流版本历史。GET /api/workflows/history?id=...",
    "사용자가 새 마켓플레이스를 추가해야 하는 경우 marketplaceUrl 필드도 함께.":
        "若用户需要添加新市场，请同时附上 marketplaceUrl 字段。",
    "이 스킬을 삭제할까요? ~/.claude/skills/<id>/ 디렉터리가 제거됩니다.":
        "要删除此技能吗？将移除 ~/.claude/skills/<id>/ 目录。",
    "MCP 탭의 카탈로그에서 Context7, GitHub, Memory 등 원클릭 설치.":
        "在 MCP 标签页的目录中一键安装 Context7、GitHub、Memory 等。",
    "공장 A 가 B 보다 2배 빠르다. A 가 단독으로 만드는 데 6시간이면 둘이 함께는?":
        "工厂 A 比 B 快 2 倍。A 单独需要 6 小时，那么两者一起需要多久？",
    "budget_tokens 슬라이더, 예시 3종(수학/디버깅/플래닝), 히스토리 20건.":
        "budget_tokens 滑块、3 个示例（数学/调试/规划）、20 条历史记录。",
    "candidates 안에서만 고르고, 이미 설치된 것(installed) 은 제외. ":
        "仅从 candidates 中选择，排除已安装（installed）的项。 ",
    "편집(타임스탬프 백업 + 값 검증). settings.json 의 sandbox 키.":
        "编辑（时间戳备份 + 值校验）。settings.json 中的 sandbox 键。",
    "SSE 스트리밍 챗 — claude CLI stream-json 을 SSE 로 중계.":
        "SSE 流式聊天 — 将 claude CLI stream-json 中继为 SSE。",
    "stdin 에서 newline-delimited JSON-RPC 메시지를 읽어 처리.":
        "从 stdin 读取并处理以换行符分隔的 JSON-RPC 消息。",
    "Best-effort 설치 감지. None = 감지 불가(설치 불필요/즉시 실행형).":
        "尽力而为的安装检测。None = 无法检测（无需安装/即开即用）。",
    "Claude 는 Anthropic 에서 만든 대규모 언어 모델이다. 그래서 뭘 잘해?":
        "Claude 是 Anthropic 打造的大型语言模型。那么它擅长什么？",
    "sandbox iframe + CSP + 정적 필터 4중 보안으로 안전하게 미리보기.":
        "通过 sandbox iframe + CSP + 静态过滤四重防护安全预览。",
    "OpenAI API — HTTP 직접 호출 (requests 미사용, urllib).":
        "OpenAI API — 直接 HTTP 调用（不使用 requests，用 urllib）。",
    "cache_read 토큰을 1x input 단가로 청구했을 때 대비 절감액(USD).":
        "相对于以 1x input 单价计费 cache_read 令牌的节省额（USD）。",
    "범위 내 세션 데이터가 없습니다. Claude Code 세션이 인덱싱되면 표시됩니다.":
        "范围内没有会话数据。Claude Code 会话被索引后将显示。",
    "CLAUDE.md · 프로젝트 메모리가 컨텍스트에 주입하는 부하를 측정 (읽기 전용)":
        "测量 CLAUDE.md · 项目记忆注入上下文的负载（只读）",
    "deny 규칙 늘리면 안전도 ↑. 자주 쓰는 명령을 allow 해 승인 프롬프트 ↓.":
        "增加 deny 规则可提升安全性 ↑。将常用命令加入 allow 可减少批准提示 ↓。",
    "Claude 공식 hosted tool 플레이그라운드 — 🌐 web_search + ":
        "Claude 官方 hosted tool 演练场 — 🌐 web_search + ",
    "일·월 지출 한도(USD/토큰)를 소스별로 설정하고 임계치 도달 시 알림을 받습니다.":
        "按来源设置每日·每月支出限额（USD/令牌），达到阈值时收到通知。",
    "TTL 분할은 1시간 캐시를 사용한 랩 호출의 usage.cache_creation ":
        "TTL 拆分来自使用 1 小时缓存的实验室调用的 usage.cache_creation ",
    "이번 세션 실제 토큰 사용·절감 통계 (세션 로그 기반). /caveman-stats":
        "本会话的实际令牌使用·节省统计（基于会话日志）。/caveman-stats",
    "워크플로우 — n8n 스타일 DAG 에디터. 세션 노드 생성·포트 드래그 연결·실행·":
        "工作流 — n8n 风格的 DAG 编辑器。创建会话节点·拖拽端口连接·运行·",
    "사용자의 작업 패턴에 맞는 Claude Code 플러그인 활성화/추가를 추천하세요. ":
        "根据用户的工作模式推荐要启用/添加的 Claude Code 插件。 ",
    "소스별/모델별/일별 집계 + 최근 30건. Claude Code 내부 + 대시보드 ":
        "按来源/模型/日聚合 + 最近 30 条。Claude Code 内部 + 仪表盘 ",
    "추정 비용은 Anthropic이 제공하는 추정치이며 실제 청구와 다를 수 있습니다.":
        "预估费用为 Anthropic 提供的估算值，可能与实际账单不同。",
    "추정. 총 사용량은 message.usage 실측, 정적 항목은 추정. 읽기 전용.":
        "估算。总用量为 message.usage 实测，静态项为估算。只读。",
    "오늘 AI 업계에서 주목할 만한 뉴스 3개를 요약해줘. 각 항목에 출처 링크 포함.":
        "请总结今天 AI 行业值得关注的 3 条新闻。每条附上来源链接。",
    "ECC marketplace · ECC plugin · CCB repo 설치 상태.":
        "ECC marketplace · ECC plugin · CCB repo 安装状态。",
    "allowedTools: * 는 모든 도구를 허용합니다. 필요한 도구만 나열하세요.":
        "allowedTools: * 允许所有工具。请仅列出需要的工具。",
    "Claude API 는 Anthropic 의 고성능 LLM 접근 인터페이스입니다. ":
        "Claude API 是 Anthropic 的高性能 LLM 访问接口。 ",
    "3명이 5분에 사과 3개를 먹는다. 10명이 사과 10개를 먹는 데 몇 분 걸리나?":
        "3 个人 5 分钟吃 3 个苹果。10 个人吃 10 个苹果需要几分钟？",
    "세션 하네스(페르소나/허용 도구/resume)·🔁 Repeat 자동 반복·📋 템플릿":
        "会话 harness(人设/允许的工具/resume)·🔁 Repeat 自动循环·📋 模板",
    "`code_execution_20250825` 는 모든 지원 모델에서 사용 가능. ":
        "`code_execution_20250825` 可在所有受支持的模型上使用。 ",
    "`.env` 파일을 읽어 현재 프로세스 환경 변수에 반영. 이미 설정된 키는 유지.":
        "读取 `.env` 文件并应用到当前进程的环境变量。已设置的键保持不变。",
    "외부 OMX CLI를 추가로 설치하면 Codex 세션 안에서 $ 키워드로 호출 가능":
        "额外安装外部 OMX CLI 后，可在 Codex 会话内通过 $ 关键字调用",
    "Constitutional AI 접근법을 통해 유해 출력을 줄이는 방법을 연구한다.":
        "研究如何通过 Constitutional AI 方法减少有害输出。",
    "Ollama: 모델 허브(23종 카탈로그/다운로드/삭제), serve 자동 시작, ":
        "Ollama: 模型中心(23 种目录/下载/删除)、serve 自动启动、",
    "Opus / Sonnet / Haiku 3 모델에 병렬 질문 → 응답 나란히 비교.":
        "向 Opus / Sonnet / Haiku 这 3 个模型并行提问 → 并排比较响应。",
    "명확화된 요구사항을 기반으로 기술 설계 문서 작성 (섹션: 목표/제약/아키/리스크)":
        "基于已澄清的需求撰写技术设计文档 (章节: 目标/约束/架构/风险)",
    "Read/Grep/Edit 같은 도구를 적극 쓸수록 실제 작업이 일어났다는 신호.":
        "越频繁使用 Read/Grep/Edit 等工具，越说明确实发生了实际工作。",
    "비용 절감을 실측. 예시 3종(시스템/문서/도구) 원클릭 실행, 히스토리 20건.":
        "实测成本节省。一键运行 3 种示例(系统/文档/工具)，保留 20 条历史记录。",
    "/ultrawork — 5 병렬 에이전트 → merge (bt-ultrawork)":
        "/ultrawork — 5 个并行代理 → merge (bt-ultrawork)",
    "8개 빌트인 프로바이더 + 커스텀 무제한. API 키 설정, CLI 자동 감지, ":
        "8 个内置提供商 + 不限数量的自定义提供商。API 密钥设置、CLI 自动检测、",
    "| 시작 | 프로젝트 | 모델 | 토큰 | 추정 비용 | 점수 | 첫 프롬프트 |":
        "| 开始 | 项目 | 模型 | 令牌 | 估算成本 | 评分 | 首个提示词 |",
    "Prompt Library — 자주 쓰는 프롬프트를 태그와 함께 저장/검색/복제/":
        "Prompt Library — 将常用提示词连同标签一起保存/搜索/克隆/",
    "전체 아키텍처 · 범위 · 리스크를 5섹션으로 설계 (목표/제약/접근/모듈/순서)":
        "以 5 个章节设计整体架构 · 范围 · 风险 (目标/约束/方法/模块/顺序)",
    "기본 채팅/임베딩 모델 설정. 비용 분석 차트, 사용량 알림, 멀티 AI 비교, ":
        "设置默认聊天/嵌入模型。成本分析图表、用量提醒、多 AI 比较、",
    "Anthropic 은 2021년 샌프란시스코에서 설립된 AI 안전 연구 회사다. ":
        "Anthropic 是一家于 2021 年在旧金山成立的 AI 安全研究公司。 ",
    "Learner — 최근 세션 JSONL 에서 반복되는 tool 시퀀스·프롬프트를 ":
        "Learner — 从最近的会话 JSONL 中提取反复出现的 tool 序列·提示词 ",
    "Messages API 호출. (status_code, json_body) 반환.":
        "调用 Messages API。返回 (status_code, json_body)。",
    "1부터 100 까지 소수의 합을 계산해서 보여줘. Python 으로 직접 계산해.":
        "计算并展示 1 到 100 之间素数的和。用 Python 直接计算。",
    "Anthropic은 주간/5시간 쿼터의 실시간 잔량 API를 제공하지 않습니다. ":
        "Anthropic 不提供周/5 小时配额的实时剩余量 API。 ",
    "모든 프로바이더 health check 병렬 실행 — 포트/엔드포인트 정보 포함.":
        "并行执行所有提供商的 health check — 包含端口/端点信息。",
    "경로가 사용자 홈 디렉터리 아래인지 (symlink traversal 차단용).":
        "路径是否位于用户主目录之下 (用于阻止 symlink traversal)。",
    "Kubernetes 의 Deployment 와 StatefulSet 의 차이는?":
        "Kubernetes 中 Deployment 与 StatefulSet 有何区别？",
    "~/.claude.json 이 없습니다 — Claude Code에 로그인하세요.":
        "未找到 ~/.claude.json — 请登录 Claude Code。",
    "σ 배수가 낮을수록 더 민감하게 탐지합니다. 변경 후 자동으로 다시 계산됩니다.":
        "σ 倍数越低，检测越灵敏。更改后会自动重新计算。",
    "상대 시간 문자열 — '3초 전', '5분 전', '2시간 전', '1일 전'.":
        "相对时间字符串 — '3秒前'、'5分钟前'、'2小时前'、'1天前'。",
    "Claude 응답에서 recommendations JSON 을 찾지 못했습니다.":
        "未能在 Claude 响应中找到 recommendations JSON。",
    "프로젝트 상태 + 점수 약점을 보고 '이 파일을 이렇게 추가/편집하세요' 추천.":
        "根据项目状态 + 评分弱点，给出 '这样添加/编辑此文件' 的建议。",
    "환경 변수 설정: envConfig 탭에서 ANTHROPIC_MODEL 등 수정":
        "设置环境变量: 在 envConfig 标签页中修改 ANTHROPIC_MODEL 等",
    "동일 프롬프트를 Claude, GPT, Gemini에 동시 전송하여 결과 비교":
        "将同一提示词同时发送给 Claude、GPT、Gemini 并比较结果",
    "settings.json이 올바른 JSON이 아닙니다. 저장이 비활성화됩니다.":
        "settings.json 不是有效的 JSON。保存功能已禁用。",
    "macOS 전용. 샌드박스 명령이 localhost 포트에 바인딩하도록 허용.":
        "仅限 macOS。允许沙箱命令绑定到 localhost 端口。",
    "객체에서만 제공됩니다 (Anthropic 공식). SQLite 세션 인덱스는 ":
        "仅在对象中提供 (Anthropic 官方)。SQLite 会话索引 ",
    "settings.json 내용 반환. 파일 없거나 파싱 실패 시 빈 dict.":
        "返回 settings.json 的内容。文件不存在或解析失败时返回空 dict。",
    "존재 여부·읽기 실패를 흡수하고 빈 문자열 반환. 필요 시 앞 N 문자 제한.":
        "吸收文件不存在·读取失败的情况并返回空字符串。必要时限制为前 N 个字符。",
    "토큰/USD 를 가져와 로컬 추정치와 drift 비교 (admin 키 필요).":
        "获取令牌/USD 并与本地估算值比较 drift (需要 admin 密钥)。",
    "예: 'Bash(curl:* | sh)' → 'Bash(curl* | sh)'":
        "例如: 'Bash(curl:* | sh)' → 'Bash(curl* | sh)'",
    "문자열 경로를 절대화하고 ~/ 하위면 abs path 반환, 아니면 None.":
        "将字符串路径转为绝对路径；若位于 ~/ 之下则返回 abs path，否则返回 None。",
    "`---` 블록을 key/value dict 로. 파싱 불가 시 빈 dict.":
        "将 `---` 块解析为 key/value dict。无法解析时返回空 dict。",
    "이 마켓플레이스의 매니페스트가 로컬에 캐시되어 있지 않습니다. 새로고침하세요.":
        "此市场的清单尚未缓存到本地。请刷新。",
    "교차 실행하고 저장된 베이스라인과 비교해 회귀(이전 통과→현재 실패)를 강조.":
        "交叉执行并与已保存的基线比较，突出显示回归(之前通过→现在失败)。",
    "하네스 도구 — caveman(출력 토큰 압축)·ccusage(사용량 분석)·":
        "Harness 工具 — caveman(输出令牌压缩)·ccusage(用量分析)·",
    "압축 코드리뷰 코멘트 (위치·문제·수정 한 줄). /caveman-review":
        "压缩的代码审查评论 (位置·问题·修复一行搞定)。/caveman-review",
    "→ 워크플로우 탭 헤더의 Quick Actions 또는 런 센터의 OMC 카드":
        "→ 工作流标签页标题中的 Quick Actions，或运行中心的 OMC 卡片",
    "SessionStart 훅 추가 (~/.claude/settings.json)":
        "添加 SessionStart 钩子 (~/.claude/settings.json)",
    "Claude Code 플러그인 설치: 마켓플레이스 URL 추가 → toggle":
        "安装 Claude Code 插件: 添加市场 URL → toggle",
    "claude auth login 이 실행되었습니다. 완료 후 새로고침하세요.":
        "claude auth login 已启动。完成后请刷新。",
    "글로벌 CLAUDE.md는 모든 프로젝트의 모든 대화에 주입되며, 프로젝트 ":
        "全局 CLAUDE.md 会注入所有项目的所有对话，而项目 ",
    "이전 검증에서 FAIL 로 판정된 항목을 해결하도록 수정 방향을 제시하세요.":
        "请针对上次验证中判定为 FAIL 的项目给出修改方向。",
    "워크플로우 완료 시 호출. 설정된 채널만 전송. 실패해도 예외 발생 안 함.":
        "工作流完成时调用。仅发送到已配置的频道。即使失败也不会抛出异常。",
    "‘인쇄용 HTML 열기’ 후 브라우저의 인쇄 → PDF로 저장을 사용하세요.":
        "点击‘打开打印用 HTML’后，使用浏览器的打印 → 另存为 PDF。",
    "Reliability — Auto-Resume · 자동 복구 · 바인딩 관리":
        "Reliability — Auto-Resume · 自动恢复 · 绑定管理",
    "버전 + CHANGELOG 로딩 — 프론트 사이드바, 챗봇 프롬프트가 공유.":
        "加载版本 + CHANGELOG — 由前端侧边栏和聊天机器人提示词共享。",
    "JSONL 파일 최근 50건 — (경로, 크기, mtime, 줄 수 근사).":
        "最近 50 个 JSONL 文件 — (路径、大小、mtime、近似行数)。",
    "ANTHROPIC_API_KEY 미설정 — aiProviders 탭에서 저장":
        "未设置 ANTHROPIC_API_KEY — 请在 aiProviders 标签页中保存",
    "이벤트 훅 (PreToolUse / PostToolUse / Stop …).":
        "事件钩子 (PreToolUse / PostToolUse / Stop …)。",
    "원자적 쓰기 — tmp 파일에 쓰고 rename. 부모 디렉토리 자동 생성.":
        "原子写入 — 先写入 tmp 文件再 rename。自动创建父目录。",
    "의도된 호출이면 노드 설정에서 'allowInternal: true' 체크.":
        "如果是有意调用，请在节点设置中勾选 'allowInternal: true'。",
    "DAG 검증. cycle 이 있으면 설명 리스트 반환, 없으면 빈 리스트.":
        "DAG 校验。存在 cycle 时返回说明列表，否则返回空列表。",
    "이전 Fix 결과를 반영해 Exec 단계에서 실패 항목을 우선 처리하세요.":
        "请参考上次 Fix 的结果，在 Exec 阶段优先处理失败项。",
    "환경 변수에 경로가 설정되어 있으면 확장·절대화해서 반환, 아니면 기본값.":
        "如果环境变量中设置了路径，则展开并转为绝对路径后返回，否则返回默认值。",
    "estTokens는 문자수/4 추정치 (영어 기준 휴리스틱). 한국어 등 ":
        "estTokens 是字符数/4 的估算值 (基于英文的启发式)。对于韩语等 ",
    "Slack 어드민 승인 → Obsidian 기록 → 다음 사이클로 루프. ":
        "Slack 管理员审批 → 记录到 Obsidian → 循环进入下一周期。 ",
    "카탈로그. 저장소·설치 명령을 보고 Terminal 에서 바로 설치·실행.":
        "目录。查看仓库·安装命令，直接在 Terminal 中安装·运行。",
    "두 요청의 prefix 가 일치합니다 (append-only 또는 동일).":
        "两个请求的 prefix 一致 (append-only 或相同)。",
    "특정 JSONL 파싱 — query 는 relative path 를 받음.":
        "解析特定 JSONL — query 接收 relative path。",
    "SQL 로 user 테이블의 id, email 을 email 기준 정렬.":
        "用 SQL 将 user 表的 id、email 按 email 排序。",
    "tool 정의를 캐시하면 같은 tools 세트를 반복 호출할 때 재활용.":
        "缓存 tool 定义后，重复调用相同的 tools 集时可复用。",
    "npx ccusage / bunx ccusage — 기본은 일자별 리포트":
        "npx ccusage / bunx ccusage — 默认是按日报告",
    "Claude Code 도구·IDE 통합·프레임워크·리소스 큐레이션 목록.":
        "Claude Code 工具·IDE 集成·框架·资源的精选列表。",
    "커스텀 프로바이더 임베딩 — embedCommand 가 설정된 경우에만.":
        "自定义提供商嵌入 — 仅在设置了 embedCommand 时。",
    "이 회사의 핵심 특징과 투자 내역을 불릿 3개로 요약해줘. 인용을 활용.":
        "请用 3 个要点总结这家公司的核心特点和投资记录。使用引用。",
    "결과물이 요구사항을 만족하는지 검증 — PASS/FAIL 과 근거 리포트":
        "验证产出是否满足需求 — 输出 PASS/FAIL 及依据报告",
    "수신해 비용·토큰·도구 수락/거절·코드 라인·커밋·세션을 실시간 집계. ":
        "接收后实时统计成本·令牌·工具接受/拒绝·代码行数·提交·会话。 ",
    "mDNSResponder/identitysd 등 시스템 노이즈 표시 토글":
        "切换是否显示 mDNSResponder/identitysd 等系统噪音",
    "query 먼저, docs N 개 embed. 실패하면 error 반환.":
        "先 query，再 embed N 个 docs。失败时返回 error。",
    "캐시 hit 과 write 의 비용 차이, 그리고 최소 크기를 정리해줘.":
        "请整理缓存 hit 与 write 的成本差异，以及最小大小。",
    "`#`/`##`/`###` 헤더 기준으로 섹션 분리 — 에디터 프리뷰용.":
        "按 `#`/`##`/`###` 标题拆分章节 — 用于编辑器预览。",
    "정확한 인용 span 이 포함된 답변을 받아 원문 하이라이트로 시각화. ":
        "获取包含精确引用 span 的回答，并以原文高亮的方式可视化。 ",
    "예시 2종 (Q&A 10건 / 요약 5건), 최대 1000건/batch.":
        "2 种示例 (10 条 Q&A / 5 条摘要)，最多 1000 条/batch。",
    "OAuth 계정 없음 — `claude auth login` 실행 필요.":
        "没有 OAuth 账户 — 需要运行 `claude auth login`。",
    "정적 검사해 시크릿 노출·위험 훅·과도한 권한·신뢰 불가 MCP 감지. ":
        "通过静态检查检测泄露的密钥·危险钩子·过度权限·不可信 MCP。 ",
    "터미널에서 로그인 창이 열렸습니다. 브라우저 인증 완료 후 돌아오세요.":
        "终端中已打开登录窗口。完成浏览器认证后请返回。",
    "uvx 자동 설치는 PyPI 에서 패키지를 받습니다. 신뢰 범위 확인.":
        "uvx 自动安装会从 PyPI 下载包。请确认信任范围。",
    "caveman 모드·스킬·명령 레퍼런스 카드. /caveman-help":
        "caveman 模式·技能·命令参考卡片。/caveman-help",
    "기획자가 전달한 지시 블록 중 본인 역할에 해당하는 부분만 수행하세요.":
        "在规划者下达的指令块中，只执行属于自己角色的部分。",
    "각 페르소나별 지시 블록을 '### <role>' 헤딩으로 구분하세요.":
        "请用 '### <role>' 标题区分每个 persona 的指令块。",
    "빌트인 신기능 + 사용자가 '최신 정보 로딩' 으로 발견한 동적 항목.":
        "内置新功能 + 用户通过'加载最新信息'发现的动态条目。",
    "마켓플레이스 매니페스트가 캐시되어 있지 않습니다 — 먼저 새로고침하세요":
        "市场清单尚未缓存 — 请先刷新",
    "워크플로우를 백그라운드 스레드로 실행 시작. runId 를 즉시 반환.":
        "在后台线程中开始运行工作流。立即返回 runId。",
    "Claude Design export 를 저장하는 추가 디렉토리 등록.":
        "注册用于保存 Claude Design export 的额外目录。",
    "VERSION 파일에서 현재 버전 문자열 반환. 없으면 '0.0.0'.":
        "从 VERSION 文件返回当前版本字符串。不存在时为 '0.0.0'。",
    "토큰 1개 획득. 가능하면 True, 타임아웃 내 불가하면 False.":
        "获取 1 个令牌。可用时返回 True，超时内不可用则返回 False。",
    "prompt 길이(char) / 4 를 input 토큰 근사치로 사용.":
        "将 prompt 长度(char) / 4 作为 input 令牌的近似值。",
    "기획자(Planner) → 페르소나 3명 병렬 작업 → 보고 취합 → ":
        "规划者(Planner) → 3 个 persona 并行工作 → 汇总报告 → ",
    "PreCommit — 시크릿 패턴 (sk-, ghp_, AKIA) 감지":
        "PreCommit — 检测密钥模式 (sk-, ghp_, AKIA)",
    "ISO 8601 문자열을 epoch ms 로. 파싱 실패 시 None.":
        "将 ISO 8601 字符串转换为 epoch ms。解析失败时返回 None。",
    "모델 상세 정보. GET /api/ollama/info?name=...":
        "模型详细信息。GET /api/ollama/info?name=...",
    "Gemini CLI (gemini) — Google 의 CLI 도구.":
        "Gemini CLI (gemini) — Google 的 CLI 工具。",
    "이전 사이클의 보고를 검토하고, 미해결 항목과 새로 발견된 리스크를 ":
        "审查上一周期的报告，并将未解决事项与新发现的风险 ",
    "자동 추출 → Prompt Library / 워크플로우 템플릿 제안.":
        "自动提取 → 推荐 Prompt Library / 工作流模板。",
    "세션 안에서 충분히 대화를 이어가면 맥락이 누적되어 품질이 오릅니다.":
        "在会话内持续对话会积累上下文，从而提升质量。",
    "설치된 마켓플레이스의 모든 plugins 리스트 + 설치/활성 상태.":
        "列出已安装市场的所有 plugins + 安装/启用状态。",
    "긴 문서를 user 메시지로 첨부하고 캐시 → 추가 질문 시 재사용.":
        "将长文档作为 user 消息附加并缓存 → 后续提问时复用。",
    "최근 run 중 output 이 있는 것들을 meta 리스트로 반환.":
        "将近期含 output 的 run 以 meta 列表返回。",
    "외부 HTTP endpoint 로 포워딩. 호스트 화이트리스트 적용.":
        "转发到外部 HTTP endpoint。应用主机白名单。",
    "멀티바이트 문자는 실제 토큰이 더 많을 수 있어 보수적 하한입니다. ":
        "多字节字符的实际令牌数可能更多，因此这是保守下限。 ",
    "리셋 시각은 로컬 세션 로그의 한도 도달 메시지에서 추출한 값이며, ":
        "重置时间提取自本地会话日志中的限额到达消息， ",
    "서울의 현재 기온을 get_weather 로 확인하고 한 줄로 요약.":
        "用 get_weather 查询首尔当前气温并用一行总结。",
    "caveman 스위트 설치 상태 + 컴포넌트별 감지 + 사용 가이드.":
        "caveman 套件安装状态 + 各组件检测 + 使用指南。",
    "선택한 모델들을 교차 실행 → 모델별 평균 지연·토큰·비용 집계 + ":
        "交叉运行所选模型 → 汇总各模型的平均延迟·令牌·成本 + ",
    "Playground — Claude API 실험 12종 + 프로바이더":
        "Playground — 12 种 Claude API 实验 + 提供商",
    "turn2 캐시 READ 0 — 캐시 미스(브레이크포인트가 깨짐).":
        "turn2 缓存 READ 0 — 缓存未命中(断点失效)。",
    "Claude CLI 시간 초과 (240초) — 다시 시도해 주세요.":
        "Claude CLI 超时 (240 秒) — 请重试。",
    "PRD 의 모듈 1/3 담당 — 코드/문서 결과물과 실행 결과 보고":
        "负责 PRD 的模块 1/3 — 汇报代码/文档产出与执行结果",
    "macOS Finder 에서 CCB 디렉터리 열기 (보너스 편의).":
        "在 macOS Finder 中打开 CCB 目录 (额外便利)。",
    "프로바이더 사용 가능 여부 (CLI 설치됨 / API 키 설정됨).":
        "提供商可用性 (CLI 已安装 / API 密钥已配置)。",
    "💾 백업 & 복원 — 워크플로우/AR/AI 키/설정 스냅샷 + 복원":
        "💾 备份 & 恢复 — 工作流/AR/AI 密钥/设置快照 + 恢复",
    "이미 종료된 세션이라도 강제로 바인딩 — 재개 시 새 세션이 시작됨":
        "即使会话已结束也强制绑定 — 恢复时会启动新会话",
    "JS 렌더링 사이트 미지원. 추가 비용 없음 (표준 토큰 비용만).":
        "不支持 JS 渲染网站。无额外费用 (仅标准令牌费用)。",
    "~/.claude/projects/*/*.jsonl 전부 재인덱스.":
        "重新索引全部 ~/.claude/projects/*/*.jsonl。",
    "🔄 Auto-Resume 관리 — 활성 바인딩 리스트 + 일괄 취소":
        "🔄 Auto-Resume 管理 — 活动绑定列表 + 批量取消",
    "자주 쓰는 Bash 명령을 allow에 pattern으로 미리 등록":
        "将常用 Bash 命令以 pattern 形式预先登记到 allow",
    "WebFetch/WebSearch 허용해서 최신 정보 참조 가능하게":
        "允许 WebFetch/WebSearch 以便参考最新信息",
    "세션 행 리스트 → 평균 5축 점수. 짧은 세션(도구<기준) 제외.":
        "会话行列表 → 平均 5 轴评分。排除短会话(工具<阈值)。",
    "SOCKS 프록시 포트 (network.socksProxyPort)":
        "SOCKS 代理端口 (network.socksProxyPort)",
    "PRD 의 모듈 2/3 담당 — 코드/문서 결과물과 실행 결과 보고":
        "负责 PRD 的模块 2/3 — 汇报代码/文档产出与执行结果",
    "워크플로우 생성: workflows 탭 → 새 워크플로우 + 템플릿":
        "创建工作流: workflows 标签页 → 新建工作流 + 模板",
    "프로바이더 레지스트리 싱글턴. 첫 호출 시 빌트인 프로바이더 등록.":
        "提供商注册表单例。首次调用时注册内置提供商。",
    "PRD 의 모듈 3/3 담당 — 코드/문서 결과물과 실행 결과 보고":
        "负责 PRD 的模块 3/3 — 汇报代码/文档产出与执行结果",
    "파이썬 3.13 은 GIL 비활성화 옵션을 제공한다. 의미가 뭐야?":
        "Python 3.13 提供了禁用 GIL 的选项。这意味着什么？",
    "macOS 전용. 샌드박스가 접근 가능한 Unix 소켓 경로 목록.":
        "仅限 macOS。沙箱可访问的 Unix 套接字路径列表。",
    "매우 단순한 Markdown → HTML (외부 라이브러리 없음).":
        "极简的 Markdown → HTML (无外部库)。",
    "반복 실행 설정 sanitize. enabled 기본 False.":
        "对重复执行设置进行 sanitize。enabled 默认为 False。",
    "레거시 — 시도 횟수 캡 (시간 데드라인보다 먼저 적중하면 발동)":
        "旧版 — 尝试次数上限 (若早于时间截止达到则触发)",
    "메시지에 document 로 reference 해서 질문 테스트.":
        "在消息中以 document 方式 reference 并测试提问。",
    "~/.claude/output-styles/<id>.md 로 저장":
        "保存为 ~/.claude/output-styles/<id>.md",
    "둘러보고 설치 상태 확인 + 설치 명령 안내 (Discover).":
        "浏览并查看安装状态 + 提供安装命令 (Discover)。",
    "| 모델 | 세션 | 입력 | 출력 | 총 토큰 | 추정 비용 |":
        "| 模型 | 会话 | 输入 | 输出 | 总令牌 | 估算成本 |",
    "권한 allow 목록을 늘려 매 도구 호출마다 승인 프롬프트 제거":
        "扩充权限 allow 列表，免去每次工具调用的批准提示",
    "텍스트 임베딩 생성. 지원하지 않는 프로바이더는 기본 에러 반환.":
        "生成文本嵌入。不支持的提供商默认返回错误。",
    "PATH 기반 탐지 → 실패 시 통상 설치 경로 fallback.":
        "基于 PATH 探测 → 失败时 fallback 到常见安装路径。",
    "우선순위에 반영해 다음 단계 업무를 페르소나별로 다시 분배하세요.":
        "纳入优先级，并按 persona 重新分配下一阶段的任务。",
    "hosted tool 활성화 상태로 Messages API 호출.":
        "在启用 hosted tool 的状态下调用 Messages API。",
    "UI 테스트 버튼용 — 지정된 채널에 test 메시지 1건 전송.":
        "用于 UI 测试按钮 — 向指定频道发送 1 条 test 消息。",
    "프로젝트 전용 에이전트(.claude/agents/*.md) 추가":
        "添加项目专用代理（.claude/agents/*.md）",
    "세션의 토큰 사용량 분해 — 도구별 / 서브에이전트별 / 시간순.":
        "会话令牌用量拆解 — 按工具 / 按子代理 / 按时间顺序。",
    "위험한 명령을 deny 목록에 등록 (rm -rf, sudo 등)":
        "将危险命令登记到 deny 列表（rm -rf、sudo 等）",
    "질문에 대해 합리적인 기본값/권장 답변을 제시하고 각각 근거 표기":
        "为每个问题提供合理的默认值/推荐答案，并分别标注依据",
    "조직/워크스페이스/팀 정보 (claude.ai team 기능용).":
        "组织/工作区/团队信息（用于 claude.ai team 功能）。",
    "Claude 워크플로우 커스터마이즈용 스킬·리소스 큐레이션 목록.":
        "用于自定义 Claude 工作流的技能与资源精选列表。",
    "위임을 더 활용해보세요 — 정의된 에이전트가 30일간 적게 호출됨":
        "请多加利用委派 — 已定义的代理在 30 天内调用次数很少",
    "Claude CLI 가 설치되어 있지 않습니다. 먼저 설치하세요.":
        "未安装 Claude CLI。请先安装。",
    "빌드/테스트 훅을 PostToolUse에 연결해 조기 실패 감지":
        "将构建/测试钩子接入 PostToolUse 以尽早发现失败",
    "API 키 저장: aiProviders 탭에서 저장-key 버튼":
        "保存 API 密钥：在 aiProviders 标签页点击 save-key 按钮",
    "base / modified 모두 messages 가 필요합니다":
        "base / modified 均需要 messages",
    "HTTP 프록시 포트 (network.httpProxyPort)":
        "HTTP 代理服务器端口（network.httpProxyPort）",
    "설치된 첫 번째 chat 모델 반환 (embedding 제외).":
        "返回第一个已安装的 chat 模型（不含 embedding）。",
    "도구 오류 없이 깔끔하게 실행될수록 높음. 오류 1회당 -4점.":
        "工具执行越干净无错误，得分越高。每次错误 -4 分。",
    "현재 임계값 기준으로 사용량과 비용이 평소 범위 안에 있습니다.":
        "按当前阈值衡量，用量与费用均处于正常范围内。",
    "정적 보안 스캔 실행. 이슈 리스트 + 카테고리별 카운트 반환.":
        "运行静态安全扫描。返回问题列表 + 按类别计数。",
    "추가 쓰기 허용 경로 (filesystem.allowWrite)":
        "额外允许写入的路径（filesystem.allowWrite）",
    "서브에이전트에게 위임하면 메인 컨텍스트를 절약하고 병렬화 가능.":
        "委派给子代理可节省主上下文并实现并行化。",
    "플래닝 → 실행 → 리뷰 3-라운드 대화를 한 세션에서 끝내기":
        "在一个会话内完成规划 → 执行 → 评审的 3 轮对话",
    "`~/.claude/settings.json` 전체 레퍼런스.":
        "`~/.claude/settings.json` 完整参考。",
    "비용 타임라인 통합 — 모든 플레이그라운드/워크플로우 비용을 ":
        "费用时间线整合 — 将所有 Playground/工作流费用 ",
    "settings.json 의 enabledPlugins 토글.":
        "切换 settings.json 中的 enabledPlugins。",
    "60초 간격으로 cron 매칭 검사 + 워크플로우 자동 실행.":
        "每 60 秒检查 cron 匹配 + 自动执行工作流。",
    "챗봇 API — 사용자 질문을 받아 대시보드 안내 답변 반환.":
        "聊天机器人 API — 接收用户问题并返回仪表板指引答复。",
    "대형 시스템 프롬프트를 캐시해 동일 대화 반복 시 비용 절감.":
        "缓存大型系统提示词，在重复同一对话时节省费用。",
    "플러그인 에이전트는 마켓플레이스에서 관리 — 삭제는 비활성화로":
        "插件代理由市场管理 — 删除请改用停用",
    "(rtk-ai/rtk) 를 한 탭에서 설치·활성화·통계 조회.":
        "在一个标签页内完成 (rtk-ai/rtk) 的安装、启用与统计查看。",
    "CLAUDE.md에 '작업 시작 전 요구사항 확인' 지침 추가":
        "在 CLAUDE.md 中添加“开始工作前确认需求”指令",
    "Config — 훅 · 권한 · MCP · 플러그인 · 설정":
        "Config — 钩子 · 权限 · MCP · 插件 · 设置",
    "Wizard 탭에서 폼만 채우면 더 쉽게 만들 수 있습니다.":
        "在 Wizard 标签页只需填写表单即可更轻松地创建。",
    "요구사항에서 모호한 부분을 찾아 3~5개의 구체적 질문 생성":
        "找出需求中的模糊之处并生成 3~5 个具体问题",
    "Ollama 시작 중... 잠시 후 연결을 다시 확인하세요.":
        "正在启动 Ollama... 请稍后再次检查连接。",
    "usage dict → 비용 상세 (캐시 절감 계산 포함).":
        "usage dict → 费用明细（含缓存节省计算）。",
    "폴백 체인 편집, 연결 테스트, 프로바이더 헬스 대시보드. ":
        "编辑回退链、测试连接、提供商健康状态仪表板。 ",
    "Delay 노드 — 지정 시간 대기 후 입력을 그대로 통과.":
        "Delay 节点 — 等待指定时间后将输入原样传递。",
    "측정·플래그하고 로드 경계 초과 파일을 표시 (읽기 전용).":
        "测量、标记并显示超出加载边界的文件（只读）。",
    "특정 capability 를 가진 프로바이더 + 모델 목록.":
        "具有特定 capability 的提供商 + 模型列表。",
    "CLAUDE.md는 해당 프로젝트의 모든 대화에 주입됩니다.":
        "CLAUDE.md 会注入到该项目的所有对话中。",
    "BAAI 다국어 임베딩. 1024 dims. 한국어 우수.":
        "BAAI 多语言嵌入。1024 dims。韩语表现优秀。",
    "사용자 작업 패턴에 맞는 MCP 서버 추가를 추천하세요. ":
        "请推荐符合用户工作模式的 MCP 服务器。 ",
    "읽기 재허용 경로 (filesystem.allowRead)":
        "重新允许读取的路径（filesystem.allowRead）",
    "이전 노드의 session_id 수집 (resume 용).":
        "收集上一节点的 session_id（用于 resume）。",
    "요구사항을 받아 실행 계획 수립 — 단계별 체크리스트 생성":
        "接收需求并制定执行计划 — 生成分步检查清单",
    "감지된 Ollama 호스트를 프로바이더 레지스트리에 반영.":
        "将检测到的 Ollama 主机写入提供商注册表。",
    "파일 백업이 디스크에 존재하여 /rewind 로 복원 가능":
        "磁盘上存在文件备份，可通过 /rewind 恢复",
    "n8n 워크플로 수정 시 mcp__n8n-mcp 우선 사용":
        "修改 n8n 工作流时优先使用 mcp__n8n-mcp",
    "API 데이터 수집 → 변환 → AI 분석 → 리포트 생성":
        "采集 API 数据 → 转换 → AI 分析 → 生成报告",
    "LazyClaude에 흡수된 4 모드 (별도 설치 불필요)":
        "已并入 LazyClaude 的 4 种模式（无需单独安装）",
    "한 도구에만 의존하지 않고 올바른 도구를 골라 쓰는 패턴.":
        "不依赖单一工具、而是选用正确工具的模式。",
    "복잡한 수식 단계를 thinking block 으로 확인.":
        "通过 thinking block 检查复杂公式步骤。",
    "워크플로우 embedding 노드에서 호출하는 편의 함수.":
        "由工作流 embedding 节点调用的便捷函数。",
    "Claude Code 세션 내부에서 직접 슬래시 명령 호출":
        "在 Claude Code 会话内直接调用斜杠命令",
    "외부 툴/가이드 카탈로그 + 베스트 프랙티스 + 치트시트.":
        "外部工具/指南目录 + 最佳实践 + 速查表。",
    "repeat 설정에 따라 iteration 을 반복 실행.":
        "根据 repeat 设置重复执行 iteration。",
    "~/.claude/settings.json 이 없습니다.":
        "~/.claude/settings.json 不存在。",
    "JavaScript 로 debounce 함수를 작성해줘.":
        "用 JavaScript 编写一个 debounce 函数。",
    "scores[i] 에 대응하는 rank (1=가장 큼).":
        "与 scores[i] 对应的 rank（1=最大）。",
    "REST 와 GraphQL 중 CRUD 에 적합한 것은?":
        "REST 和 GraphQL 哪个更适合 CRUD？",
    "Anthropic cache-diagnosis 베타 사용":
        "使用 Anthropic cache-diagnosis 测试版",
    "파이썬으로 1~N 까지 더하는 함수를 5줄 이내로 써줘.":
        "用 Python 写一个对 1~N 求和的函数，不超过 5 行。",
    "이 프로바이더가 특정 capability 를 지원하는지.":
        "该提供商是否支持特定 capability。",
    "0.1 + 0.2 == 0.3 이 false 인 이유는?":
        "为什么 0.1 + 0.2 == 0.3 是 false？",
    "지출은 세션 토큰 × cost_timeline 요금 추정":
        "支出按会话令牌 × cost_timeline 费率估算",
    "데이터는 약 1시간 지연되며 오늘은 집계에서 제외됩니다.":
        "数据约延迟 1 小时，今天不计入汇总。",
    "최근 30일치 사용 패턴 → 품질 가중치 계산용 데이터.":
        "最近 30 天的使用模式 → 用于计算质量权重的数据。",
    "코드는 ```로 감싸고 설명은 3줄 이내로 요약합니다. ":
        "代码用 ``` 包裹，说明概括在 3 行以内。 ",
    "쓰기 금지 경로 (filesystem.denyWrite)":
        "禁止写入的路径 (filesystem.denyWrite)",
    "현재 설정된 Event Forwarder 훅 목록 반환.":
        "返回当前配置的 Event Forwarder 钩子列表。",
    "로그아웃 — `claude auth logout` 실행.":
        "登出 — 执行 `claude auth logout`。",
    "레벨(lite·full·ultra·wenyan) 가이드.":
        "级别（lite·full·ultra·wenyan）指南。",
    "Google Gemini API — HTTP 직접 호출.":
        "Google Gemini API — 直接 HTTP 调用。",
    "CLAUDE.md 가 100자 이상 내용을 담고 있으면 ":
        "如果 CLAUDE.md 内容达到 100 字以上 ",
    "서버 시작 시 호출 — 스케줄러 백그라운드 스레드 시작.":
        "服务器启动时调用 — 启动调度器后台线程。",
    "Ollama 기본 채팅 모델 + 임베딩 모델 설정 조회.":
        "查询 Ollama 默认聊天模型 + 嵌入模型设置。",
    "Learn — 신기능 · 온보딩 · 공식 문서 · 가이드":
        "Learn — 新功能 · 入门 · 官方文档 · 指南",
    "세션별 프롬프트 단위 파일 스냅샷 타임라인 (읽기 전용)":
        "按会话、按提示词的文件快照时间线（只读）",
    "대시보드가 관리하는 Ollama 프로세스가 이미 실행 중":
        "仪表盘管理的 Ollama 进程已在运行",
    "허용 도메인 (network.allowedDomains)":
        "允许的域名 (network.allowedDomains)",
    "직접 편집된 파일 없음 (bash 변경은 추적되지 않음)":
        "没有直接编辑的文件（bash 改动不被跟踪）",
    "읽기 금지 경로 (filesystem.denyRead)":
        "禁止读取的路径 (filesystem.denyRead)",
    "연결 설정 — Claude Code 텔레메트리 내보내기":
        "连接设置 — Claude Code 遥测导出",
    "cache_control 로 반복 프롬프트 비용 절감.":
        "通过 cache_control 降低重复提示词的成本。",
    "settings.json.permissions 에 병합":
        "合并到 settings.json.permissions",
    "프로젝트 목표를 단계별 작업으로 쪼개고 페르소나에 분배":
        "将项目目标拆分为分步任务并分配给各角色",
    "$wiki — 작업 컨텍스트를 1페이지 레퍼런스로 요약":
        "$wiki — 将工作上下文汇总为 1 页参考",
    "파일 로드. 없거나 파싱 실패 시 빈 store 반환.":
        "加载文件。文件缺失或解析失败时返回空 store。",
    "Terminal 새 창에서 초기화 명령 자동 붙여넣기.":
        "在新 Terminal 窗口中自动粘贴初始化命令。",
    "여러 모델에 병렬 분배하고 결과를 합쳐 채널에 회신. ":
        "并行分发到多个模型，合并结果后回复到频道。 ",
    "플레이그라운드 10종 + 워크플로우 비용을 한 화면에.":
        "10 种演练场 + 工作流成本，尽在一屏。",
    "LazyClaude 흡수 기능만 쓰려면 (설치 불필요)":
        "如只使用 LazyClaude 吸收的功能（无需安装）",
    "Claude Code CLI 가 설치되어 있지 않습니다":
        "未安装 Claude Code CLI",
    "규칙이 유효하면 None, 잘못이면 에러 메시지 반환.":
        "规则有效时返回 None，无效时返回错误信息。",
    "카탈로그 + 도구별 설치 상태 + 카테고리 라벨 반환.":
        "返回目录 + 各工具的安装状态 + 类别标签。",
    "Model Context Protocol 커넥터 설정.":
        "Model Context Protocol 连接器设置。",
    "Opus / Sonnet / Haiku 세대별 비교.":
        "Opus / Sonnet / Haiku 各代对比。",
    "활성·비활성 모든 마켓플레이스 플러그인의 스킬 수집.":
        "收集所有市场插件（启用与停用）的技能。",
    "프로바이더 설정 파일 로드. 없으면 기본 구조 반환.":
        "加载提供商配置文件。文件缺失时返回默认结构。",
    "로컬 ollama 모델을 시도해보세요 (비용 $0).":
        "试试本地 ollama 模型（成本 $0）。",
    "Claude CLI 시간 초과 — 다시 시도해 주세요":
        "Claude CLI 超时 — 请重试",
    "프롬프트 첫 60자 정규화 — 공백 축약 + 소문자.":
        "对提示词前 60 个字符进行规范化 — 压缩空白 + 转小写。",
    "UI 초기화용 — 이벤트 타입 + 허용 호스트 목록.":
        "用于 UI 初始化 — 事件类型 + 允许的主机列表.",
    "초경량 임베딩. 384 dims. 빠른 프로토타이핑.":
        "超轻量嵌入. 384 dims. 快速原型开发.",
    "프로바이더별 요청 빈도 제한 (토큰 버킷 알고리즘).":
        "按提供方限制请求频率 (令牌桶算法).",
    "실패한 항목만 선택적으로 수정. 변경점과 근거 명시.":
        "仅选择性修复失败项. 注明变更点与依据.",
    "챗봇 시스템 프롬프트에 삽입할 탭 목록 문자열 생성.":
        "生成插入聊天机器人系统提示的标签页列表字符串.",
    "피드백이 있으면 반영해 수정, 없으면 초기 작업 수행":
        "有反馈则据此修改, 没有则执行初始任务",
    "설치 버튼은 큐레이션된 명령만 터미널에서 실행합니다.":
        "安装按钮仅在终端中执行经过筛选的命令.",
    "settings.json.statusLine 덮어쓰기":
        "覆盖 settings.json.statusLine",
    "Anthropic 서버 측 hosted 검색 도구.":
        "Anthropic 服务器端 hosted 搜索工具.",
    "프로세스 시작 시 한 번 호출. 중복 호출은 무시.":
        "进程启动时调用一次. 重复调用将被忽略.",
    "공식 요금표 (per-million-tokens).":
        "官方价格表 (per-million-tokens).",
    "폐기 진단 · 마이그레이션 어드바이저 (읽기 전용)":
        "弃用诊断 · 迁移顾问 (只读)",
    "Claude Code 가이드 (한국어 · 위키독스)":
        "Claude Code 指南 (韩语 · Wikidocs)",
    "이 세션에는 디스크에 저장된 체크포인트가 없습니다.":
        "此会话没有保存在磁盘上的检查点.",
    "turn2 에서 캐시 READ 발생 — 히트 성공.":
        "turn2 发生缓存 READ — 命中成功.",
    "문서 임베딩 → 검색 → AI 응답 생성 파이프라인":
        "文档嵌入 → 检索 → AI 响应生成管道",
    "PATH + 통상 설치 경로 fallback 탐지.":
        "通过 PATH + 常见安装路径 fallback 检测.",
    "파일 업로드 + document reference.":
        "文件上传 + document reference.",
    ">캐시 읽기 / 생성</div><div class=":
        ">缓存读取 / 创建</div><div class=",
    "API 키 + 추가 설정(baseUrl 등) 저장.":
        "保存 API 密钥 + 附加设置(baseUrl 等).",
    "OpenAI Codex CLI — 코드 생성 특화.":
        "OpenAI Codex CLI — 专注代码生成.",
    "Meta의 오픈소스 LLM. 범용 대화·코드·추론.":
        "Meta 的开源 LLM. 通用对话·代码·推理.",
    "검색: security, design, lsp...":
        "搜索: security, design, lsp...",
    "`rtk session` — 현재 세션 사용 내역.":
        "`rtk session` — 当前会话使用记录.",
    "사이클 없다고 가정. Kahn's 결과 순서 반환.":
        "假定无环. 返回 Kahn's 结果顺序.",
    "web_fetch 로 URL 본문을 가져와 요약. ":
        "通过 web_fetch 获取 URL 正文并进行摘要. ",
    "이미 등록된 이름입니다 — 다른 이름으로 시도하세요":
        "该名称已被注册 — 请尝试其他名称",
    "터미널에서 마켓플레이스를 추가하면 여기에 나타납니다":
        "在终端中添加市场后会显示在这里",
    "격리 제외 명령 (excludedCommands)":
        "隔离排除命令 (excludedCommands)",
    "비샌드박스 재시도 허용 (escape hatch)":
        "允许非沙箱重试 (escape hatch)",
    "타임아웃 — 관리자 응답을 받지 못해 흐름 중단.":
        "超时 — 未收到管理者响应, 流程中断.",
    "설치된 Ollama 모델 목록 + 카탈로그 매칭.":
        "已安装的 Ollama 模型列表 + 目录匹配.",
    "Wizard로 생성된 페르소나 크루 워크플로우. ":
        "由 Wizard 生成的 Persona Crew 工作流. ",
    "MCP 서버 추가해서 사용 가능한 도구 범위 확장":
        "添加 MCP 服务器以扩展可用工具范围",
    "프로젝트 settings.local.json 보강":
        "补充项目 settings.local.json",
    "file-history 저장소가 존재하지 않습니다":
        "file-history 存储不存在",
    "file://, ftp:// 등은 보안상 차단됨.":
        "file://, ftp:// 等出于安全考虑被阻止.",
    "Transform 노드 — 텍스트/JSON 변환.":
        "Transform 节点 — 文本/JSON 转换.",
    "탭 설명을 요청 언어로 반환. 없으면 한글 기본.":
        "以请求的语言返回标签页描述. 缺失时默认韩语.",
    "Claude 응답에서 JSON 을 찾지 못했습니다":
        "未在 Claude 响应中找到 JSON",
    "min(25, floor(도구호출수 × 1.2))":
        "min(25, floor(工具调用数 × 1.2))",
    "LazyClaude에 흡수된 4 명령 (런 센터)":
        "已并入 LazyClaude 的 4 个命令 (运行中心)",
    "matcher 없이 모든 도구 호출에 적용됩니다.":
        "没有 matcher 时应用于所有工具调用.",
    "단일 cron 필드가 현재 값과 매칭되는지 확인.":
        "检查单个 cron 字段是否与当前值匹配.",
    "계획에 따라 작업 수행 — 코드/문서 결과물 출력":
        "按计划执行任务 — 输出代码/文档成果",
    "이 시스템 프롬프트는 테스트용 고정 블록입니다. ":
        "此系统提示是用于测试的固定块. ",
    "Observe — 비용 · 메트릭 · 시스템 관측":
        "Observe — 成本 · 指标 · 系统观测",
    "Build — 워크플로우 · 에이전트 · 프롬프트":
        "Build — 工作流 · 代理 · 提示词",
    "노드의 입력 텍스트 수집 (이전 노드 결과에서).":
        "收集节点的输入文本 (来自前置节点结果).",
    "관리형 allowRead만 허용 (managed)":
        "仅允许管理型 allowRead (managed)",
    "omx hud --watch 터미널 라이브 갱신":
        "omx hud --watch 终端实时刷新",
    "플러그인 스킬은 편집 불가 (read-only)":
        "插件技能不可编辑 (read-only)",
    "CLI 설치 · 기본 사용 · 프로젝트 초기화.":
        "CLI 安装 · 基本使用 · 项目初始化。",
    "MixedBread 임베딩. 1024 dims.":
        "MixedBread 嵌入。1024 dims。",
    "출력 스타일 점검 데이터를 불러오지 못했습니다.":
        "无法加载输出样式检查数据。",
    "커스텀 CLI 프로바이더 인스턴스 리스트 반환.":
        "返回自定义 CLI 提供商实例列表。",
    "| 프로젝트 | 세션 | 토큰 | 추정 비용 |":
        "| 项目 | 会话 | 令牌 | 估算成本 |",
    "키워드로 웹을 검색하고 상위 5건을 반환합니다.":
        "按关键词搜索网页并返回前 5 条结果。",
    "임베딩 프로바이더가 반환하는 통일된 응답 형식.":
        "嵌入提供商返回的统一响应格式。",
    "Llama 3.1 대형 모델. 높은 추론 능력.":
        "Llama 3.1 大型模型。推理能力强。",
    "키워드 → 탭 id 매핑을 자연어 지시로 반환.":
        "以自然语言指令返回关键词 → 标签页 id 映射。",
    "실행 중인 ollama serve 가 없습니다.":
        "没有正在运行的 ollama serve。",
    "아키텍처 결정 과정을 thinking 에 노출.":
        "将架构决策过程暴露在 thinking 中。",
    "특정 capability 를 가진 모델만 필터.":
        "仅筛选具有特定 capability 的模型。",
    "id 는 소문자/숫자/-/_ 만 (2~41자)":
        "id 仅允许小写字母/数字/-/_ (2~41 个字符)",
    "OpenAI Embeddings API 호출.":
        "调用 OpenAI Embeddings API。",
    "팝업이 차단되었습니다 — 팝업을 허용해 주세요":
        "弹窗已被拦截 — 请允许弹窗",
    "Mistral AI 범용 모델. 빠르고 정확.":
        "Mistral AI 通用模型。快速且准确。",
    "Ollama HTTP API로 모델 pull.":
        "通过 Ollama HTTP API 拉取模型。",
    "`rtk gain` — 누적 토큰 절감 통계.":
        "`rtk gain` — 累计令牌节省统计。",
    "프로젝트별 서브에이전트 정의 · 역할 프리셋.":
        "按项目的子代理定义 · 角色预设。",
    "프로바이더 설정 위자드(초보자 3단계 가이드)":
        "提供商设置向导(新手 3 步指南)",
    "모든 프로바이더가 반환하는 통일된 응답 형식.":
        "所有提供商返回的统一响应格式。",
    "대화 이력 수정 (append-only 위반)":
        "修改对话历史 (违反 append-only)",
    "provider:model 형식으로 입력하세요":
        "请以 provider:model 格式输入",
    "로컬에서 탐지 (ML 없음, 요청 시 계산).":
        "本地检测 (无 ML，按请求计算)。",
    "Snowflake 임베딩. 1024 dims.":
        "Snowflake 嵌入。1024 dims。",
    "당신은 Claude 대시보드의 도우미입니다. ":
        "你是 Claude 仪表盘的助手。 ",
    "Codex 세션 내부에서 $ 키워드 직접 호출":
        "在 Codex 会话内直接调用 $ 关键词",
    "이 프로젝트만 비정상적으로 비용이 늘었습니다.":
        "只有这个项目的成本异常增长。",
    "검색당 $10/1,000 + 표준 토큰 비용.":
        "每 1,000 次搜索 $10 + 标准令牌费用。",
    "개별 응답 매트릭스. 결과 JSON 다운로드.":
        "单条响应矩阵。下载结果 JSON。",
    "claude CLI가 설치되어 있지 않습니다.":
        "未安装 claude CLI。",
    "버그 분석 과정 · 가설 검증 과정을 시각화.":
        "可视化错误分析过程 · 假设验证过程。",
    "세션 하나에서 지표 추출. 실패 시 빈 결과.":
        "从单个会话提取指标。失败时返回空结果。",
    "📜 실행 이력·🎬 14장면 인터랙티브 튜토리얼":
        "📜 执行历史·🎬 14 场景交互式教程",
    ">입력 / 출력</div><div class=":
        ">输入 / 输出</div><div class=",
    "모든 AI 프로바이더의 추상 베이스 클래스.":
        "所有 AI 提供商的抽象基类。",
    "이 프로젝트 맥락에서 왜 필요한지 2~3문장":
        "用 2~3 句话说明为何在此项目上下文中需要它",
    "모델 카탈로그 — 내장 목록 + 설치 상태.":
        "模型目录 — 内置列表 + 安装状态。",
    "localhost 바인딩 허용 (macOS)":
        "允许 localhost 绑定 (macOS)",
    "| 날짜 | 세션 | 토큰 | 추정 비용 |":
        "| 日期 | 会话 | 令牌 | 估算成本 |",
    "캐시 토큰 델타 (turn1 → turn2)":
        "缓存令牌增量 (turn1 → turn2)",
    "Python 의 GIL 을 1문장으로 설명.":
        "用一句话解释 Python 的 GIL。",
    "Finder 열기 + Documents 클릭":
        "打开 Finder + 点击 Documents",
    "SessionEnd — 상태/요약 자동 저장":
        "SessionEnd — 自动保存状态/摘要",
    "allow / deny 규칙 · 권한 정책.":
        "allow / deny 规则 · 权限策略。",
    "min(25, floor(메시지수 / 4))":
        "min(25, floor(消息数 / 4))",
    "문서의 핵심 주장을 2문장으로 요약해주세요.":
        "请用两句话总结文档的核心主张。",
    "ts(초) → YYYY-MM-DD 별 합산.":
        "ts(秒) → 按 YYYY-MM-DD 汇总。",
    "Claude 구독 활성 (세부 플랜 미지정)":
        "Claude 订阅已激活（未指定具体套餐）",
    "예시 2종 (회사 소개문 / 기술 아티클).":
        "2 个示例（公司介绍 / 技术文章）。",
    "frontmatter 를 제거한 본문 반환.":
        "返回去除 frontmatter 的正文。",
    "CORS preflight 는 언제 발생해?":
        "CORS preflight 何时发生？",
    "/autopilot 다음 작업 자동 실행해줘":
        "/autopilot 自动执行下一个任务",
    "캐시 무시하고 강제 조회 (분당 1회 권장)":
        "忽略缓存强制查询（建议每分钟 1 次）",
    "레지스트리 재초기화 (설정 변경 후 호출).":
        "重新初始化注册表（更改设置后调用）。",
    "settings.json을 읽을 수 없습니다":
        "无法读取 settings.json",
    "Nomic 텍스트 임베딩. 768 dims.":
        "Nomic 文本嵌入。768 维。",
    "고급: 사용자 정의 SOCKS 프록시 포트.":
        "高级：自定义 SOCKS 代理端口。",
    "설정 파일 저장 (atomic write).":
        "保存配置文件（atomic write）。",
    "키 없으면 오프라인 구조 diff 로 폴백.":
        "无密钥时回退到离线结构 diff。",
    "settings.json.hooks 에 병합":
        "合并到 settings.json.hooks",
    "설치 명령은 공식 문서에서 검증된 형식입니다":
        "安装命令为官方文档验证过的格式",
    "오늘 하루 Claude Code 활동 한눈에":
        "一目了然查看今日 Claude Code 活动",
    "사용자 레벨 출력 스타일 파일이 없습니다.":
        "没有用户级输出样式文件。",
    "유효하지 않은 플러그인/마켓플레이스 식별자":
        "无效的插件/市场标识符",
    "Claude CLI 시간 초과 (240초)":
        "Claude CLI 超时（240 秒）",
    "CLAUDE.md 로 프로젝트 지식 고정.":
        "用 CLAUDE.md 固定项目知识。",
    "탐색 작업은 Explore 에이전트로 위임":
        "将探索任务委派给 Explore 代理",
    "이번 실행을 새 베이스라인으로 저장했습니다":
        "已将本次运行保存为新基线",
    "복사 실패 — 미리보기에서 직접 선택하세요":
        "复制失败 — 请在预览中直接选择",
    "부팅 시 호출 — 변경된 세션만 재인덱싱.":
        "启动时调用 — 仅重新索引已更改的会话。",
    "플러그인 마켓플레이스 · 설치 · 활성화.":
        "插件市场 · 安装 · 启用。",
    "워크플로우 노드 실행 비용을 DB에 기록.":
        "将工作流节点执行成本记录到数据库。",
    "사용 패턴에서 발견한 흥미로운 점 2-3개":
        "从使用模式中发现的 2-3 个有趣之处",
    ">추정 비용</div><div class=":
        ">估算成本</div><div class=",
    "해당 플러그인이 이 마켓플레이스에 없습니다":
        "该插件不在此市场中",
    "min(15, Agent툴_호출수 × 3)":
        "min(15, Agent工具调用数 × 3)",
    "동시 수정 감지 — 새로고침 후 다시 시도":
        "检测到并发修改 — 请刷新后重试",
    "Google DeepMind 오픈 모델.":
        "Google DeepMind 开放模型。",
    "_해당 기간에 기록된 세션이 없습니다._":
        "_该时段内没有记录的会话。_",
    "프로바이더별 rank 차이를 하이라이트.":
        "高亮显示各提供商的 rank 差异。",
    "벡터 DB 가 RAG 에 쓰이는 이유는?":
        "为什么向量数据库用于 RAG？",
    ">총 토큰</div><div class=":
        ">总令牌</div><div class=",
    "툴 호출 하이라이트 · 누적 토큰 차트.":
        "工具调用高亮 · 累计令牌图表。",
    "대시보드 서버를 어떻게 다시 시작하나요?":
        "如何重启仪表盘服务器？",
    "재사용 가능한 스킬 생성 · 호출 규칙.":
        "可复用技能创建 · 调用规则。",
    "Markdown을 클립보드에 복사했습니다":
        "已将 Markdown 复制到剪贴板",
    "이 테스트 셋과 베이스라인을 삭제할까요?":
        "删除此测试集和基线？",
    "로컬 데이터에 없어 표시할 수 없습니다.":
        "本地数据中不存在，无法显示。",
    "기간을 선택하고 리포트 생성을 누르세요.":
        "请选择时段并点击生成报告。",
    "Claude CLI 를 찾을 수 없습니다":
        "找不到 Claude CLI",
    "환경별 의존성을 CLAUDE.md에 명시":
        "在 CLAUDE.md 中注明各环境的依赖",
    "`/` 명령 구조 · 커스텀 명령 등록.":
        "`/` 命令结构 · 自定义命令注册。",
    "min(15, 사용된_고유도구수 × 2)":
        "min(15, 使用的唯一工具数 × 2)",
    "당신은 여러 도구를 잘 쓰는 비서입니다.":
        "你是一位善于使用多种工具的助手。",
    "단일 노드 실행 (병렬 워커에서 호출).":
        "执行单个节点（由并行工作线程调用）。",
    "이상 탐지 계산 중 오류가 발생했습니다.":
        "异常检测计算时发生错误。",
    "위임 프롬프트를 CLAUDE.md에 추가":
        "将委派提示添加到 CLAUDE.md",
    "각 카드는 관련 대시보드 탭으로도 연결.":
        "每张卡片还会链接到相关的仪表盘标签页。",
    "`approve`/`reject` 답장_":
        "`approve`/`reject` 回复_",
    "10개 질문을 Haiku 로 병렬 처리.":
        "使用 Haiku 并行处理 10 个问题。",
    "오늘의 핵심 개념을 한 줄로 요약해줘.":
        "请用一句话总结今天的核心概念。",
    "Microsoft 소형 모델. 효율적.":
        "Microsoft 小型模型。高效。",
    "마이그레이션 어드바이저 (읽기 전용).":
        "迁移顾问 (只读)。",
    "마켓플레이스 정보를 불러오지 못했습니다":
        "无法加载市场信息",
    "Ollama API가 응답하는지 확인.":
        "检查 Ollama API 是否有响应。",
    "Alibaba Qwen. 다국어 강점.":
        "Alibaba Qwen。多语言能力强。",
    "이 기간에 기록된 팀 활동이 없습니다.":
        "此期间没有记录的团队活动。",
    "Voyage AI 기반 임베딩 API.":
        "基于 Voyage AI 的嵌入 API。",
    "ANTHROPIC_API_KEY 미설정":
        "未设置 ANTHROPIC_API_KEY",
    "Claude Code 세션 안에서 사용":
        "在 Claude Code 会话内使用",
    "되감기(rewind)는 어떻게 동작하나":
        "回退(rewind)是如何工作的",
    "출력 스타일 기능은 폐기되지 않았습니다":
        "输出样式功能并未弃用",
    "Claude 계정 연결이 필요합니다: ":
        "需要连接 Claude 账户: ",
    "스크린샷만 (planning only)":
        "仅截图 (planning only)",
    "ollama serve 프로세스 종료.":
        "终止 ollama serve 进程。",
    "경계를 초과하는 메모리 파일이 없습니다":
        "没有超出边界的记忆文件",
    "도시 이름으로 날씨 조회 (mock).":
        "按城市名称查询天气 (mock)。",
    "Fast mode 기본 · legacy":
        "Fast mode 默认 · legacy",
    "수정 요청 (modified · 턴2)":
        "修改请求 (modified · 第2轮)",
    "HTTP API 로 설치된 모델 조회.":
        "通过 HTTP API 查询已安装的模型。",
    "보안 검사 → 코드 리뷰 → 결과 취합":
        "安全检查 → 代码审查 → 汇总结果",
    "작업의 1/5 담당 — 섹션 A 처리":
        "负责工作的 1/5 — 处理 A 部分",
    "(설정 없음 — Default 사용)":
        "(无配置 — 使用 Default)",
    "Mistral MoE. 전문가 혼합.":
        "Mistral MoE。专家混合。",
    "빌트인 에이전트는 삭제할 수 없습니다":
        "无法删除内置代理",
    "도시의 현재 기온을 섭씨로 반환한다.":
        "以摄氏度返回城市的当前气温。",
    "에러 시 자동 재시도 + 실패 핸들링":
        "出错时自动重试 + 失败处理",
    "RTK 설정 파일 경로 (OS 별).":
        "RTK 配置文件路径 (按操作系统)。",
    "작업의 3/5 담당 — 섹션 C 처리":
        "负责工作的 3/5 — 处理 C 部分",
    "작업의 2/5 담당 — 섹션 B 처리":
        "负责工作的 2/5 — 处理 B 部分",
    "Claude 계정 연결이 필요합니다.":
        "需要连接 Claude 账户。",
    "인쇄용 HTML을 생성하지 못했습니다":
        "无法生成打印用 HTML",
    "특정 도시의 현재 날씨를 조회합니다.":
        "查询指定城市的当前天气。",
    "워크스페이스 · 멤버 · 결제 관리.":
        "管理工作区 · 成员 · 账单。",
    "작업의 4/5 담당 — 섹션 D 처리":
        "负责工作的 4/5 — 处理 D 部分",
    "워크플로우로 변환. 시드 3종 포함.":
        "转换为工作流。包含 3 种种子。",
    "레이트리밋 상태를 불러오지 못했습니다":
        "无法加载速率限制状态",
    "백업 생성 실패 — 저장을 중단합니다":
        "备份创建失败 — 中止保存",
    "이름은 영숫자/밑줄/하이픈 2~64자":
        "名称须为 2~64 个字母数字/下划线/连字符",
    "타임아웃 — 자율 판단으로 계속 진행":
        "超时 — 自主判断继续进行",
    "max(0, 20 - 오류수 × 4)":
        "max(0, 20 - 错误数 × 4)",
    ">세션</div><div class=":
        ">会话</div><div class=",
    "빌트인 프로바이더 — 다른 id 사용":
        "内置提供商 — 请使用其他 id",
    "작업의 5/5 담당 — 섹션 E 처리":
        "负责工作的 5/5 — 处理 E 部分",
    "다단계 작업 — 파일 닫고 새로 열기":
        "多步骤任务 — 关闭文件后重新打开",
    "단일 프로바이더의 API 키 저장.":
        "保存单个提供商的 API 密钥。",
    "settings.json 쓰기 실패":
        "写入 settings.json 失败",
    "이번 실행을 새 베이스라인으로 저장":
        "将本次运行保存为新基线",
    "워크플로우 프로바이더별 비용 집계.":
        "按工作流提供商汇总成本。",
    "TCP 와 UDP 의 핵심 차이는?":
        "TCP 和 UDP 的核心区别是什么？",
    "prompts 최대 1000 건까지":
        "prompts 最多 1000 条",
    "ollama serve 현재 상태.":
        "ollama serve 当前状态。",
    "API 키 없음 — 권위 진단 아님":
        "无 API 密钥 — 非权威诊断",
    "Admin 키가 설정되지 않았습니다":
        "未配置 Admin 密钥",
    "디렉토리가 아님 또는 존재하지 않음":
        "不是目录或不存在",
    "허용 Mach 서비스 (macOS)":
        "允许的 Mach 服务 (macOS)",
    "name 과 modelfile 필수":
        "name 和 modelfile 为必填",
    "Qwen 2.5 대형. 코드+추론.":
        "Qwen 2.5 大型。代码+推理。",
    "시스템 프롬프트에 타임스탬프 주입":
        "向系统提示词注入时间戳",
    "터미널에서 다음 명령을 실행합니다":
        "在终端中运行以下命令",
    "스케줄이 설정된 워크플로우 목록.":
        "已配置计划的工作流列表。",
    "DeepSeek 추론 특화 모델.":
        "DeepSeek 推理专用模型。",
    "오늘 요약을 불러오지 못했습니다.":
        "无法加载今日摘要。",
    "외부 OMC CLI 설치 (선택)":
        "安装外部 OMC CLI (可选)",
    "아직 수신된 텔레메트리가 없습니다":
        "尚未收到遥测数据",
    "Admin 사용량 탭에서 키 설정":
        "在 Admin 用量标签页中设置密钥",
    "외부 OMX CLI 설치 (선택)":
        "安装外部 OMX CLI (可选)",
    "각기 다른 짧은 문단 5개 요약.":
        "总结 5 个不同的短段落。",
    "AI 호출 없음, 로컬 휴리스틱.":
        "无 AI 调用，本地启发式。",
    "실패 시 시도할 프로바이더 순서.":
        "失败时尝试的提供商顺序。",
    "수식을 계산해 결과를 반환합니다.":
        "计算表达式并返回结果。",
    "출력 스타일 기능이 폐기되었습니다":
        "输出样式功能已弃用",
    "스캔된 프로젝트 메모리가 없습니다":
        "没有已扫描的项目记忆",
    "프로바이더를 1개 이상 선택하세요":
        "请至少选择 1 个提供商",
    "하단 상태라인 · 컨텍스트 표시.":
        "底部状态栏 · 上下文显示。",
    "→ 런 센터에서 OMX 카드 클릭":
        "→ 在运行中心点击 OMX 卡片",
    "전체 워크플로우 실행 통계 집계.":
        "汇总所有工作流的执行统计。",
    "플러그인 훅 파일을 찾을 수 없음":
        "找不到插件钩子文件",
    "이름은 영숫자/-/_/. 만 허용":
        "名称仅允许字母数字/-/_/.",
    "이상 징후가 발견되지 않았습니다.":
        "未发现异常。",
    "허용 Unix 소켓 (macOS)":
        "允许的 Unix 套接字 (macOS)",
    "복사 실패 — 수동으로 선택하세요":
        "复制失败 — 请手动选择",
    "VOYAGE_API_KEY 미설정":
        "未设置 VOYAGE_API_KEY",
    "번역 JSON 을 찾지 못했습니다":
        "找不到翻译 JSON",
    "조직 Admin 키가 필요합니다":
        "需要组织 Admin 密钥",
    "프로젝트 CLAUDE.md 생성":
        "创建项目 CLAUDE.md",
    "기준 요청 (base · 턴1)":
        "基准请求 (base · 第1轮)",
    "마켓플레이스를 찾을 수 없습니다":
        "找不到市场",
    "<공식 문서 또는 발표 URL>":
        "<官方文档或公告 URL>",
    "컨텍스트를 불러오지 못했습니다.":
        "无法加载上下文。",
    "체크포인트를 불러오지 못했습니다":
        "无法加载检查点",
    "응답은 항상 한국어로 합니다. ":
        "回复始终使用韩语。 ",
    "세션 단축키 · 컨텍스트 관리.":
        "会话快捷键 · 上下文管理。",
    "파일에 저장될 완전한 전체 내용":
        "将保存到文件的完整全部内容",
    "최근 한도 도달 기록이 없습니다":
        "近期没有达到限额的记录",
    "Prompt Caching 기초":
        "Prompt Caching 基础",
    "크기 추정치 — 과금 수치 아님":
        "大小估算值 — 非计费数值",
    "Cohere RAG 특화 모델.":
        "Cohere RAG 专用模型。",
    "경로는 홈 디렉터리 내부만 허용":
        "路径仅允许在主目录内",
    "샌드박스 내 Bash 자동 허용":
        "沙盒内自动允许 Bash",
    "현재 rate limit 상태.":
        "当前 rate limit 状态。",
    "예: 이메일에서 핵심 정보 추출":
        "例如：从邮件中提取关键信息",
    "<CLAUDE.md 전체 내용>":
        "<CLAUDE.md 完整内容>",
    "계산할 수식 (예: 2+3*5)":
        "要计算的表达式（例如 2+3*5）",
    "각 추천을 클릭해 한 번에 설치":
        "点击每个推荐即可一键安装",
    "세션 스캔 후 패턴 카드 반환.":
        "扫描会话后返回模式卡片。",
    "모델별 비용 추정 (USD).":
        "按模型估算费用（USD）。",
    "활성 알림을 모두 해제할까요?":
        "要清除所有活动通知吗？",
    "구성된 마켓플레이스가 없습니다":
        "没有已配置的市场",
    "편집 도구 결정 (수락/거절)":
        "编辑工具决定（接受/拒绝）",
    "테스트 셋을 만들어 시작하세요":
        "创建测试集以开始",
    "hooks.json 파싱 실패":
        "hooks.json 解析失败",
    "이미지 / PDF 입력 처리.":
        "处理图片 / PDF 输入。",
    ":memo: 사이클 보고 도착":
        ":memo: 周期报告已送达",
    "등록된 MCP 서버가 아닙니다":
        "不是已注册的 MCP 服务器",
    "구체적으로 무엇을 해야 하는지":
        "具体需要做什么",
    "등록된 마켓플레이스가 아닙니다":
        "不是已注册的市场",
    "3072 dims, 최고 품질":
        "3072 维，最高质量",
    "유효하지 않은 워크플로우 구조":
        "无效的工作流结构",
    "프로바이더별 기본 모델 매핑.":
        "按提供商的默认模型映射。",
    "서버 종료 시 스케줄러 정지.":
        "服务器关闭时停止调度器。",
    "## 상위 세션 (토큰 기준)":
        "## 排名靠前的会话（按令牌计）",
    "설정을 클립보드에 복사했습니다":
        "已将设置复制到剪贴板",
    "Claude CLI 실행 실패":
        "Claude CLI 运行失败",
    "프로바이더별 모델 메타데이터.":
        "按提供商的模型元数据。",
    "Claude CLI 설치 필요":
        "需要安装 Claude CLI",
    "유효하지 않은 cron 표현식":
        "无效的 cron 表达式",
    "작업 실패 — 관리자에게 알림":
        "任务失败 — 通知管理员",
    "프롬프트 실행 → 응답 반환.":
        "运行提示词 → 返回响应。",
    "리더보드를 가져오지 못했습니다":
        "无法获取排行榜",
    "경량 Llama. 빠른 응답.":
        "轻量级 Llama。响应迅速。",
    "프론트엔드 표시용 메타데이터.":
        "用于前端显示的元数据。",
    "CLAUDE.md 스니펫 복사":
        "复制 CLAUDE.md 片段",
    "특정 도시의 날씨를 조회한다.":
        "查询特定城市的天气。",
    "워크플로우를 찾을 수 없습니다":
        "找不到工作流",
    "개인 계정 불가, 읽기 전용.":
        "不支持个人账户，只读。",
    " 명확히 정리해 보고하세요.":
        " 请清晰整理后汇报。",
    "CCB 레포 디렉터리 제거.":
        "删除 CCB 仓库目录。",
    "최대 로드 파일 Top 10":
        "加载量最高的文件 Top 10",
    "대용량 프롬프트 병렬 제출.":
        "并行提交大量提示词。",
    "유효하지 않은 권한 규칙: ":
        "无效的权限规则：",
    "개선이 필요한 점 3개 이내":
        "最多 3 个需要改进的地方",
    "Admin 키를 삭제할까요?":
        "要删除 Admin 密钥吗？",
    "샌드박스 불가 시 시작 실패":
        "沙盒不可用时启动失败",
    "Ultrawork (5병렬)":
        "Ultrawork（5 并行）",
    "전체 프로바이더 상태 요약.":
        "全部提供商状态摘要。",
    "표시할 체크포인트가 없습니다":
        "没有可显示的检查点",
    "prompts 최대 20 건":
        "prompts 最多 20 条",
    "Codex 세션 안에서 사용":
        "在 Codex 会话内使用",
    "워크플로우 JSON 내보내기":
        "导出工作流 JSON",
    "각 추천을 클릭해 토글/설치":
        "点击每条推荐以切换/安装",
    "모델 목록 sanitize.":
        "对模型列表进行 sanitize。",
    "터미널에서 설치를 진행하세요":
        "请在终端中完成安装",
    "DeepSeek 코드 생성.":
        "DeepSeek 代码生成。",
    "CLAUDE.md / 메모리":
        "CLAUDE.md / 记忆",
    "프로젝트 전용 에이전트 추가":
        "添加项目专属代理",
    "리포트를 생성하지 못했습니다":
        "报告生成失败",
    "답변 톤/포맷 커스터마이즈.":
        "自定义回答语气/格式。",
    "워크플로우에 순환이 있습니다":
        "工作流中存在循环",
    "Pass/Fail 매트릭스":
        "Pass/Fail 矩阵",
    "tab_id 또는 null":
        "tab_id 或 null",
    "백업 존재 — 되감기 가능":
        "存在备份 — 可回退",
    "캐시 분석 (랩 + 세션)":
        "缓存分析 (实验室 + 会话)",
    "시스템 프롬프트 (문자열)":
        "系统提示词 (字符串)",
    "너는 한국어 전문 비서다.":
        "你是一名韩语专业助手。",
    "프로젝트 CLAUDE.md":
        "项目 CLAUDE.md",
    "Claude Code 세션":
        "Claude Code 会话",
    "분당 최대 요청 수 설정.":
        "设置每分钟最大请求数。",
    "응답 시간 초과 (30초)":
        "响应超时 (30秒)",
    "백업 없음 — 되감기 불가":
        "无备份 — 无法回退",
    "잘하고 있는 점 3개 이내":
        "做得好的地方最多 3 个",
    "Gemma 2 경량 버전.":
        "Gemma 2 轻量版。",
    "베이스라인 대비 회귀 없음":
        "相对基线无回归",
    "Claude Code 개요":
        "Claude Code 概览",
    "흔한 오류 · 복구 절차.":
        "常见错误 · 恢复步骤。",
    "Meta 코드 생성 특화.":
        "Meta 出品，专注代码生成。",
    "아직 테스트 셋이 없습니다":
        "还没有测试集",
    "docs 유효한 항목 없음":
        "docs 无有效条目",
    "BigCode 코드 생성.":
        "BigCode 代码生成。",
    "TTL 분할 데이터 없음":
        "无 TTL 细分数据",
    "2시간 뒤 / 3시간 뒤":
        "2小时后 / 3小时后",
    "도시 이름 (예: 서울)":
        "城市名称 (例: 首尔)",
    "rate limit 있음":
        "有 rate limit",
    "사용자 스타일 어드바이저":
        "用户风格顾问",
    "Researcher 작업":
        "Researcher 任务",
    "고양이가 쥐를 쫓고 있다":
        "猫正在追老鼠",
    "커스텀 프로바이더 저장.":
        "保存自定义提供商。",
    "가장 최근 세션 (자동)":
        "最近的会话 (自动)",
    "모델에 전달할 추가 지시":
        "传给模型的附加指令",
    "커스텀 프로바이더 삭제.":
        "删除自定义提供商。",
    "먼저 리포트를 생성하세요":
        "请先生成报告",
    "경로가 존재하지 않습니다":
        "路径不存在",
    "1536 dims, 저렴":
        "1536 dims, 低成本",
    "MCP 커넥터 추가 제안":
        "建议添加 MCP 连接器",
    "비활성 세션 강제 바인딩":
        "强制绑定非活动会话",
    "유효하지 않은 권한 규칙":
        "无效的权限规则",
    "복사할 내용이 없습니다.":
        "没有可复制的内容。",
    "Markdown 미리보기":
        "Markdown 预览",
    "사용 가능한 모델 목록.":
        "可用模型列表。",
    "유효하지 않은 모델 이름":
        "无效的模型名称",
    "<한 문장 한국어 설명>":
        "<一句话描述>",
    "베이스라인 윈도우 (일)":
        "基线窗口（天）",
    "모든 Unix 소켓 허용":
        "允许所有 Unix 套接字",
    "프로젝트 전용 스킬 추가":
        "添加项目专用技能",
    "코드 라인 / 활성 시간":
        "代码行数 / 活跃时间",
    "이미지+텍스트 멀티모달.":
        "图像+文本多模态。",
    "JSON 배열 파싱 실패":
        "JSON 数组解析失败",
    "업그레이드를 권장합니다.":
        "建议升级。",
    "표시할 세션이 없습니다.":
        "没有可显示的会话。",
    "지정 경로 쓰기 차단.":
        "阻止写入指定路径。",
    "최근 14일 토큰 추이":
        "最近 14 天令牌趋势",
    "테스트 셋을 선택하세요":
        "请选择测试集",
    " (벡터 JSON), ":
        " （向量 JSON）, ",
    "변경할 항목이 없습니다":
        "没有可更改的项目",
    "문서 인용 응답 모드.":
        "文档引用回答模式。",
    "메시지가 비어있습니다.":
        "消息为空。",
    "오프라인 구조 diff":
        "离线结构 diff",
    "폴백 체인 순서 설정.":
        "设置回退链顺序。",
    "Anthropic 발표":
        "Anthropic 公告",
    "이상 탐지 로드 실패:":
        "异常检测加载失败：",
    "범위별 추정 토큰 로드":
        "按范围加载估算令牌",
    "이벤트 타입 + URL":
        "事件类型 + URL",
    "프로바이더 상태 확인.":
        "检查提供商状态。",
    "브라우저 주소창에 검색":
        "在浏览器地址栏中搜索",
    "분석 불러오는 중...":
        "正在加载分析...",
    "프로젝트별 메모리 로드":
        "按项目加载记忆",
    "Admin 사용량·비용":
        "Admin 用量·费用",
    "Uncached 입력":
        "未缓存输入",
    "백업 없음 (GC됨)":
        "无备份（已 GC）",
    "이상 탐지 계산 중…":
        "异常检测计算中…",
    "Ollama (로컬)":
        "Ollama（本地）",
    "구 모델 은퇴 일정.":
        "旧模型退役计划。",
    "세션 ID가 없습니다":
        "没有会话 ID",
    " → Slack 승인":
        " → Slack 审批",
    "Reviewer 작업":
        "Reviewer 任务",
    "이전 대화를 기억해?":
        "你记得之前的对话吗？",
    "추정 vs 실제 청구":
        "估算 vs 实际账单",
    "TODO 리스트 구축":
        "构建 TODO 列表",
    "<사용/시작 URL>":
        "<使用/入门 URL>",
    "검색 결과 기반 답변":
        "基于搜索结果的回答",
    "Admin API 키":
        "Admin API 密钥",
    "활성 알림이 없습니다":
        "没有活跃的提醒",
    "<한국어 짧은 이름>":
        "<简短名称>",
    "Markdown 복사":
        "复制 Markdown",
    "표시할 플러그인 없음":
        "没有可显示的插件",
    "저장된 Admin 키":
        "已保存的 Admin 密钥",
    "비용 유형별 (실제)":
        "按费用类型（实际）",
    "새 워크플로우 만들기":
        "创建新工作流",
    "Claude (메인)":
        "Claude（主）",
    "로그아웃 되었습니다.":
        "已退出登录。",
    "인쇄용 HTML 열기":
        "打开打印版 HTML",
    "모델별 토큰 (오늘)":
        "按模型令牌（今天）",
    "샌드박스 설정 저장됨":
        "沙箱设置已保存",
    "코드 라인 (+/-)":
        "代码行数 (+/-)",
    "한도 도달 기록 없음":
        "无达到限额记录",
    "로드 경계 초과 파일":
        "超出加载边界的文件",
    "인쇄용 HTML 오류":
        "打印版 HTML 错误",
    "코드 리뷰 파이프라인":
        "代码审查流水线",
    "도구 정의 순서 변경":
        "调整工具定义顺序",
    "프로바이더 목록 필수":
        "必须提供提供商列表",
    "웹 검색 시뮬레이션.":
        "网页搜索模拟。",
    "지금 (이미 리셋됨)":
        "现在（已重置）",
    "Qwen 코드 특화.":
        "Qwen 专注代码。",
    "샌드박스 공식 문서":
        "沙箱官方文档",
    "시스템 노이즈 숨김":
        "隐藏系统噪音",
    "근접도 알 수 없음":
        "接近度未知",
    "유효하지 않은 ID":
        "无效的 ID",
    "프로젝트 스킬 삭제":
        "删除项目技能",
    "최근 활동 프로젝트":
        "最近活跃的项目",
    "리더보드 조회 실패":
        "加载排行榜失败",
    "Ollama 종료됨":
        "Ollama 已停止",
    "- (데이터 없음)":
        "-（无数据）",
    "간단한 수식 계산.":
        "简单公式计算。",
    "선택 노드 잘라내기":
        "剪切所选节点",
    "컨텍스트 구성 막대":
        "上下文构成条",
    "시스템 포트 숨기기":
        "隐藏系统端口",
    "## 상위 프로젝트":
        "## 热门项目",
    "이탈리아의 수도는?":
        "意大利的首都是哪里？",
    " (차원 수만), ":
        "（仅维度数），",
    "롤링 5시간 윈도우":
        "滚动 5 小时窗口",
    "git URL 필요":
        "需要 git URL",
    "Builder 작업":
        "Builder 任务",
    "두 요청 전송 중…":
        "正在发送两个请求…",
    "오늘 상위 프로젝트":
        "今日热门项目",
    "Batch 가드: ":
        "Batch 守护： ",
    "Eval 실행 확인":
        "确认运行 Eval",
    "SQL 쿼리 최적화":
        "SQL 查询优化",
    "Admin 키 설정":
        "设置 Admin 密钥",
    "JSON 파싱 오류":
        "JSON 解析错误",
    "리포트 · 내보내기":
        "报告 · 导出",
    "자기소개 한 줄로.":
        "用一句话介绍自己。",
    "토큰 합계 (실제)":
        "令牌总计（实际）",
    "| 항목 | 값 |":
        "| 项目 | 值 |",
    "노드 잘라내기 완료":
        "节点剪切完成",
    "CLI 실행 오류":
        "CLI 执行错误",
    "예산 가드 활성화":
        "启用预算守护",
    "분석 기간 (일)":
        "分析周期（天）",
    "Google 최강":
        "Google 最强",
    "서울 날씨 어때?":
        "首尔天气怎么样?",
    "— 직접 입력 —":
        "— 手动输入 —",
    "캐시가 깨진 위치":
        "缓存失效的位置",
    "Bash 샌드박스":
        "Bash 沙箱",
    "prod에 올리기":
        "部署到 prod",
    "엣지 케이스 열거":
        "列举边缘情况",
    "개 새로고침 필요":
        "个需要刷新",
    "_데이터 없음._":
        "_无数据._",
    " 이름으로 생성.":
        " 以此名称创建.",
    "출력 스타일 점검":
        "输出风格检查",
    "+ 시도 횟수 캡":
        "+ 尝试次数上限",
    "1시간 캐시 쓰기":
        "1小时缓存写入",
    "시스템 포트 표시":
        "显示系统端口",
    "보안 취약점 검사":
        "安全漏洞扫描",
    "스페인의 수도는?":
        "西班牙的首都是?",
    "- (샘플 없음)":
        "- (无样本)",
    "프롬프트 eval":
        "提示词 eval",
    "글로벌 상시 로드":
        "全局始终加载",
    "범위 내 총 지출":
        "范围内总支出",
    "실제 청구 USD":
        "实际计费 USD",
    "최우선 개선 항목":
        "首要改进项",
    "일일 지출 ($)":
        "每日支出 ($)",
    "마이그레이션 보기":
        "查看迁移",
    "배열이어야 합니다":
        "必须是数组",
    "찾을 수 없습니다":
        "未找到",
    "스킬 스니펫 복사":
        "复制技能片段",
    "유효한 모델 없음":
        "无有效模型",
    "프랑스의 수도는?":
        "法国的首都是?",
    "무료 (Free)":
        "免费 (Free)",
    "비용 데이터 없음":
        "无费用数据",
    "수집 데이터 분석":
        "分析收集的数据",
    "한 줄 종합 평가":
        "一句话综合评价",
    "캐시 미사용 가정":
        "假设不使用缓存",
    "인덱스 범위 오류":
        "索引超出范围",
    "URL 본문 요약":
        "URL 正文摘要",
    "메모리 모두 삭제":
        "删除所有记忆",
    "케이스가 없습니다":
        "没有用例",
    "## 모델별 분포":
        "## 按模型分布",
    "📝 옵시디언 기록":
        "📝 Obsidian 记录",
    "API 키 삭제.":
        "删除 API 密钥.",
    "RAG 파이프라인":
        "RAG 流水线",
    "알 수 없는 오류":
        "未知错误",
    "실시간 텔레메트리":
        "实时遥测",
    "캐나다의 수도는?":
        "加拿大的首都是?",
    "분석 데이터 없음":
        "无分析数据",
    "프롬프트 Eval":
        "提示词 Eval",
    "재시도 워크플로우":
        "重试工作流",
    "코드 라인 (+)":
        "代码行数 (+)",
    "불러오는 중...":
        "加载中...",
    "리셋 시각 감지됨":
        "检测到重置时间",
    "MCP 서버 도구":
        "MCP 服务器工具",
    "테스트 셋 편집":
        "编辑测试集",
    "경량 멀티모달.":
        "轻量级多模态.",
    "경계 초과 파일":
        "越界文件",
    "키를 입력하세요":
        "请输入密钥",
    "백업 사용 가능":
        "备份可用",
    "일별 토큰 추이":
        "每日令牌趋势",
    "API 키 액터":
        "API 密钥操作者",
    "중국의 수도는?":
        "中国的首都是?",
    " 것으로 간주.":
        " 即视为.",
    "터미널에서 실행":
        "在终端中运行",
    "분석 로드 실패":
        "分析加载失败",
    "일별 Drift":
        "每日 Drift",
    "총 메모리 로드":
        "内存加载总量",
    "개 마켓플레이스":
        "个市场",
    " (기본) | ":
        " (默认) | ",
    "파일 복원 가능":
        "文件可恢复",
    "샌드박스 활성화":
        "启用沙箱",
    "이번 달 USD":
        "本月 USD",
    "## 일별 추이":
        "## 每日趋势",
    "캐시 읽기 토큰":
        "缓存读取令牌",
    "오늘 활동 없음":
        "今日无活动",
    "5분 캐시 쓰기":
        "5 分钟缓存写入",
    "독일의 수도는?":
        "德国的首都是?",
    "프롬프트 템플릿":
        "提示词模板",
    "모델별 (추정)":
        "按模型 (估算)",
    "추론 (CoT)":
        "推理 (CoT)",
    "일본의 수도는?":
        "日本的首都是?",
    "가장 빠른 리셋":
        "最早重置",
    "5 + 2 메모":
        "5 + 2 笔记",
    "팀 워크스페이스":
        "团队工作区",
    "언제까지 재시도":
        "重试截止时间",
    "테스트 셋 삭제":
        "删除测试集",
    "코드 품질 리뷰":
        "代码质量审查",
    "응답 시간 초과":
        "响应超时",
    "베스트 프랙티스":
        "最佳实践",
    "미국의 수도는?":
        "美国的首都是?",
    "API 키 전용":
        "仅 API 密钥",
    "영국의 수도는?":
        "英国的首都是?",
    "상태 조회 실패":
        "状态查询失败",
    "통계 전체 보기":
        "查看全部统计",
    "출력 토큰 절감":
        "输出令牌节省",
    "지금부터 N시간":
        "从现在起 N 小时",
    "코드 리뷰 요청":
        "请求代码审查",
    "무료 / 미확인":
        "免费 / 未确认",
    "최근 세션 없음":
        "无最近会话",
    "모든 알림 해제":
        "清除所有通知",
    "기본 빠른 모델":
        "默认快速模型",
    "상호작용 그래프":
        "交互图",
    "## 기간 합계":
        "## 期间合计",
    "생성 중...":
        "生成中...",
    "도구 카탈로그":
        "工具目录",
    "오케스트레이터":
        "编排器",
    "🧩 보고 취합":
        "🧩 报告汇总",
    "스프린트 요청":
        "冲刺请求",
    "최신 플래그십":
        "最新旗舰",
    "이벤트 포워더":
        "事件转发器",
    "컨텍스트 구성":
        "上下文构成",
    "컨텍스트 부하":
        "上下文负载",
    "이번 달 토큰":
        "本月令牌",
    "최대 결과 수":
        "最大结果数",
    "강제 새로고침":
        "强制刷新",
    "프롬프트 저장":
        "保存提示词",
    "멀티 에이전트":
        "多代理",
    "데이터 ETL":
        "数据 ETL",
    "Eval 실행":
        "运行 Eval",
    "빌트인 스타일":
        "内置样式",
    "사용량 근사치":
        "用量近似值",
    "분석 세션 수":
        "分析会话数",
    "rank 비교":
        "rank 比较",
    "샌드박스 ON":
        "沙盒 ON",
    "플러그인 마켓":
        "插件市场",
    "저렴 + 빠름":
        "便宜 + 快速",
    "작업 디렉터리":
        "工作目录",
    "Opus 한도":
        "Opus 限额",
    "입력 / 출력":
        "输入 / 输出",
    "예시 불러오기":
        "加载示例",
    "새 테스트 셋":
        "新测试集",
    "페르소나 크루":
        "角色团队",
    "커밋 / PR":
        "提交 / PR",
    "세션 리플레이":
        "会话回放",
    "프로젝트 생성":
        "创建项目",
    "프롬프트 캐시":
        "提示词缓存",
    "웹 검색 요청":
        "网页搜索请求",
    "스캔한 파일":
        "已扫描文件",
    "한 줄 제목":
        "单行标题",
    "잘못된 요청":
        "无效请求",
    "사용량 관측":
        "用量观测",
    "현재 사용량":
        "当前用量",
    "사용량 한도":
        "用量限额",
    "첫 프롬프트":
        "首个提示词",
    "텔레그램 봇":
        "Telegram 机器人",
    "어제와 동일":
        "与昨天相同",
    "예산 저장됨":
        "预算已保存",
    "이미지 인식":
        "图像识别",
    "개 플러그인":
        "个插件",
    "오늘 USD":
        "今日 USD",
    "토큰 최적화":
        "令牌优化",
    "캐시 히트율":
        "缓存命中率",
    "케이스 없음":
        "暂无用例",
    "REG=회귀":
        "REG=回归",
    "cli 세션":
        "cli 会话",
    "추정 USD":
        "预估 USD",
    "케이스 삭제":
        "删除用例",
    "메모리 파일":
        "记忆文件",
    "$100/월":
        "$100/月",
    "어서션 없음":
        "无断言",
    "설계 보고서":
        "设计报告",
    "도구 수락률":
        "工具接受率",
    "마지막 출력":
        "最后输出",
    "메모리 요약":
        "记忆摘要",
    "- (없음)":
        "-（无）",
    "토큰 종류별":
        "按令牌类型",
    "한도 미설정":
        "未设置限额",
    "알림 해제됨":
        "通知已关闭",
    "$200/월":
        "$200/月",
    "오래된 캐시":
        "过期缓存",
    "다단계 추론":
        "多步推理",
    "메시지 배치":
        "消息批处理",
    "답변 텍스트":
        "回答文本",
    "모델별 비용":
        "按模型成本",
    "마이그레이션":
        "迁移",
    "저렴한 대안":
        "更便宜的替代方案",
    "엔터프라이즈":
        "企业版",
    "메모리 감사":
        "记忆审计",
    "API 오류":
        "API 错误",
    "베이스라인":
        "基线",
    "월 USD":
        "每月 USD",
    "예상 답변":
        "预期回答",
    "$20/월":
        "$20/月",
    "최근 활동":
        "最近活动",
    "토큰 절감":
        "令牌节省",
    "회귀 없음":
        "无回归",
    "세션 선택":
        "选择会话",
    "캐시 절감":
        "缓存节省",
    "추정 비용":
        "预估成本",
    "🧭 기획자":
        "🧭 规划者",
    "AR 중단":
        "停止 AR",
    "코드 라인":
        "代码行数",
    "값 불필요":
        "无需值",
    "범용 강력":
        "通用且强大",
    "설계 문서":
        "设计文档",
    "복원 불가":
        "无法恢复",
    "오늘 세션":
        "今日会话",
    "최신 기능":
        "最新功能",
    "공식 도구":
        "官方工具",
    "진단 실행":
        "运行诊断",
    "세션 종료":
        "结束会话",
    "호출 실패":
        "调用失败",
    "최근 7일":
        "最近7天",
    "최근 수신":
        "最近接收",
    "세션 시작":
        "会话开始",
    "기간(일)":
        "周期（天）",
    "정렬 기준":
        "排序方式",
    "작업 입력":
        "任务输入",
    "사용 불가":
        "不可用",
    "캐시 진단":
        "缓存诊断",
    "개 설치됨":
        "个已安装",
    "추정 토큰":
        "估算令牌",
    "작업/수정":
        "任务/修改",
    "대화 기록":
        "对话记录",
    "일괄 처리":
        "批量处理",
    "보안 스캔":
        "安全扫描",
    "저장 중…":
        "保存中…",
    "도구 정의":
        "工具定义",
    "캐시 생성":
        "缓存创建",
    "보존 기간":
        "保留期限",
    "일일 요약":
        "每日摘要",
    "추적 파일":
        "跟踪文件",
    "주간 한도":
        "每周限额",
    "일 USD":
        "每日 USD",
    "파일 조회":
        "文件查询",
    "세션 로그":
        "会话日志",
    "계획 수립":
        "制定计划",
    "이름 회상":
        "名字回忆",
    "이름 기억":
        "名字记忆",
    "결과 합류":
        "结果汇合",
    "폼 채우기":
        "填写表单",
    "진단 중…":
        "诊断中…",
    "파일 변경":
        "文件变更",
    "오늘 토큰":
        "今日令牌",
    "외부 전송":
        "外部发送",
    "모델 비교":
        "模型比较",
    "설계 결정":
        "设计决策",
    "추론 경량":
        "轻量推理",
    "작업 지시":
        "任务指令",
    "스킬 삭제":
        "删除技能",
    "(글로벌)":
        "（全局）",
    "설정 복사":
        "复制设置",
    "초기 요청":
        "初始请求",
    "대량 요청":
        "批量请求",
    "토큰 압축":
        "令牌压缩",
    "모델 허브":
        "模型中心",
    "1차 질문":
        "第一轮提问",
    "비용 절감":
        "成本节省",
    "활성 시간":
        "活跃时间",
    "분석 요청":
        "分析请求",
    "도시 이름":
        "城市名称",
    "통합 결과":
        "汇总结果",
    "화면 맞춤":
        "适应屏幕",
    "조회 실패":
        "查询失败",
    "온도 단위":
        "温度单位",
    "가장 저렴":
        "最便宜",
    "레이트리밋":
        "速率限制",
    "회의 요약":
        "会议摘要",
    "모두 해제":
        "全部取消",
    "추론 모델":
        "推理模型",
    "요약 검증":
        "摘要验证",
    "테스트 셋":
        "测试集",
    "편집 결정":
        "编辑决定",
    "파일시스템":
        "文件系统",
    "회귀 감지":
        "回归检测",
    "vs 어제":
        "vs 昨天",
    "지연 비교":
        "延迟对比",
    "수신 중":
        "接收中",
    "일 토큰":
        "日令牌",
    "월 토큰":
        "月令牌",
    "키 삭제":
        "删除密钥",
    "홈페이지":
        "主页",
    "첫 분기":
        "首次分支",
    "새 알림":
        "新通知",
    "케이스":
        "用例",
    "순증감":
        "净增减",
    "수락률":
        "接受率",
    "폐기됨":
        "已废弃",
    "기댓값":
        "期望值",
    "실시간":
        "实时",
    "새 셋":
        "新建集",
    "메트릭":
        "指标",
    "윈도우":
        "窗口",
    "레코드":
        "记录",
    "어서션":
        "断言",
    "해결":
        "解决",
    "권장":
        "推荐",
    "실제":
        "实际",
    "유형":
        "类型",
    "경계":
        "边界",
    "이상":
        "异常",
    "원인":
        "原因",
    "숫자":
        "数字",
    "폐기":
        "废弃",
    "속성":
        "属性",
    "마감":
        "截止",
    "해제":
        "解除",
    "커밋":
        "提交",
    "거절":
        "拒绝",
    "초과":
        "超出",
    "수락":
        "接受",
    "추정":
        "估算",
    "남음":
        "剩余",
    "비정상": "异常",
    "단일": "单个",
    "전용": "专用",
    "감지": "检测到",
    "스레드": "线程",
    "공유": "共享",
    "레벨": "级别",
    "압축": "压缩",
    "핵심": "核心",
    "포인트": "要点",
    "페이지": "页面",
    "순수": "纯",
    "개별": "单独",
    "직전": "前一",
    "군더더기": "冗余",
    "평소보다": "比平时",
    "시퀀스가": "序列",
    "줄로": "行",
    "줄": "行",
    "커넥터와": "连接器和",
    "설치형": "安装型",
    "패키지": "包",
}

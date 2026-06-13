"""v3.99.x — Auto-Resume diagnose + Plugin Hub i18n.

New t() keys added to dist/app.js for:
  - the Auto-Resume "diagnose" modal (why-isn't-it-resuming signals)
  - the Plugin Hub tab (GitHub Claude Code plugin discovery + install)
Korean source → EN / ZH (Simplified). Wired into translations_manual.py.
"""

NEW_EN: dict[str, str] = {
    # ── Auto-Resume diagnose ──
    "진단": "Diagnose",
    "진단 실패": "Diagnosis failed",
    "워커 실행 중": "Worker running",
    "세션 라이브": "Session live",
    "jsonl 발견": "jsonl found",
    "유휴 시간": "Idle time",
    "한도 신호 감지": "Limit signal detected",
    "파싱된 리셋 시각": "Parsed reset time",
    "다음 시도": "Next attempt",
    "jsonl 꼬리": "jsonl tail",
    # ── Plugin Hub ──
    "플러그인 허브": "Plugin Hub",
    "GitHub에서 Claude Code 플러그인·마켓플레이스를 별점순으로 검색하고 바로 설치합니다.":
        "Search GitHub for Claude Code plugins & marketplaces by stars and install them directly.",
    "검색 (비우면 인기 플러그인)": "Search (empty = popular plugins)",
    "검색": "Search",
    "설치됨": "Installed",
    "검색 중": "Searching",
    "플러그인 설치는 서드파티 코드(훅·MCP·실행파일)를 사용자 권한으로 실행합니다. 저장소를 확인한 뒤 설치하세요.":
        "Installing a plugin runs third-party code (hooks/MCP/executables) at your user privilege. Review the repo before installing.",
    "공식": "Official",
    "검사 · 설치": "Inspect · Install",
    "저장소": "Repository",
    "검색 실패": "Search failed",
    "결과 없음": "No results",
    "결과": "Results",
    "비인증 (GitHub 속도 제한)": "Unauthenticated (GitHub rate limit)",
    "마켓플레이스 검사 중": "Inspecting marketplace",
    "검사 실패": "Inspection failed",
    "코드 실행": "Runs code",
    "설치": "Install",
    "개 더 있음 (표시 생략)": "more (not shown)",
    "플러그인 없음": "No plugins",
    "플러그인 설치": "Install plugin",
    "플러그인은 서드파티 코드(훅·MCP·실행파일)를 사용자 권한으로 실행할 수 있습니다. 신뢰하는 경우에만 설치하세요.":
        "Plugins can run third-party code (hooks/MCP/executables) at your user privilege. Install only if you trust the source.",
    "설치 중": "Installing",
    "설치 실패": "Install failed",
    "설치된 플러그인 조회 중": "Listing installed plugins",
    "설치된 플러그인 없음": "No installed plugins",
    "설치된 플러그인": "Installed plugins",
}

NEW_ZH: dict[str, str] = {
    # ── Auto-Resume diagnose ──
    "진단": "诊断",
    "진단 실패": "诊断失败",
    "워커 실행 중": "工作线程运行中",
    "세션 라이브": "会话在线",
    "jsonl 발견": "已找到 jsonl",
    "유휴 시간": "空闲时间",
    "한도 신호 감지": "检测到限额信号",
    "파싱된 리셋 시각": "解析的重置时间",
    "다음 시도": "下次尝试",
    "jsonl 꼬리": "jsonl 末尾",
    # ── Plugin Hub ──
    "플러그인 허브": "插件中心",
    "GitHub에서 Claude Code 플러그인·마켓플레이스를 별점순으로 검색하고 바로 설치합니다.":
        "按星标在 GitHub 上搜索 Claude Code 插件与市场并直接安装。",
    "검색 (비우면 인기 플러그인)": "搜索（留空 = 热门插件）",
    "검색": "搜索",
    "설치됨": "已安装",
    "검색 중": "搜索中",
    "플러그인 설치는 서드파티 코드(훅·MCP·실행파일)를 사용자 권한으로 실행합니다. 저장소를 확인한 뒤 설치하세요.":
        "安装插件会以你的用户权限运行第三方代码（钩子/MCP/可执行文件）。请先查看仓库再安装。",
    "공식": "官方",
    "검사 · 설치": "检查 · 安装",
    "저장소": "仓库",
    "검색 실패": "搜索失败",
    "결과 없음": "无结果",
    "결과": "结果",
    "비인증 (GitHub 속도 제한)": "未认证（GitHub 速率限制）",
    "마켓플레이스 검사 중": "正在检查市场",
    "검사 실패": "检查失败",
    "코드 실행": "运行代码",
    "설치": "安装",
    "개 더 있음 (표시 생략)": "项更多（未显示）",
    "플러그인 없음": "无插件",
    "플러그인 설치": "安装插件",
    "플러그인은 서드파티 코드(훅·MCP·실행파일)를 사용자 권한으로 실행할 수 있습니다. 신뢰하는 경우에만 설치하세요.":
        "插件可能以你的用户权限运行第三方代码（钩子/MCP/可执行文件）。仅在信任来源时安装。",
    "설치 중": "安装中",
    "설치 실패": "安装失败",
    "설치된 플러그인 조회 중": "正在列出已安装插件",
    "설치된 플러그인 없음": "没有已安装的插件",
    "설치된 플러그인": "已安装插件",
}

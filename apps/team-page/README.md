# apps/team-page — 발표 페이지 (정적 HTML)

8주차 발표용. 백엔드 없이도 열리고(`data/snapshot.json` 의 숫자), 배포 주소에서 열면 Render API 가 깨어 있을 때 실시간 값으로 덮어쓴다.

- 로컬 확인: `python3 -m http.server 5180 -d apps/team-page` → http://localhost:5180 (실시간을 보려면 `?live`)
- 숫자 갱신: `.venv/bin/python scripts/snapshot_deck.py` (로컬 서비스) 또는 `API_URL=https://… .venv/bin/python scripts/snapshot_deck.py`
- 주소 설정: `deck.js` 의 `CONFIG.api` · `CONFIG.web`
- 배포: Vercel — Root Directory `apps/team-page`, Framework `Other`. CLI: `cd apps/team-page && npx vercel --prod`
- 쇼릴(모션그래픽, 전체 1분 40초 · 발표용 짧은 컷 `?short` 1분 16초, 숫자는 `data/snapshot.json`): `showreel.html` → 배포 주소 `/showreel.html`. 발표 페이지 3장에 iframe 으로 들어가 자동 재생된다(`?once&short`). Space 재생·정지, ← → 장면 이동, R 처음, F 전체화면. `?once` 한 번만, `?start=N` N번 장면부터, `?still` 모션 없이 최종 장면만(스틸컷). 영상 파일이 필요하면 전체화면으로 열고 화면 녹화(QuickTime: ⌘⇧5).
- 키보드 ← → 로 넘긴다. 밝은 바탕·큰 글씨(강의실 조명 대비), 톤은 insung_introduction 과 같다.
- `index.legacy.html` · `style.legacy.css` 는 5주차 피칭 페이지(팀원 제작). 일러스트 `img/story-*.webp` 는 재사용.

# apps/team-page — 발표 페이지 (정적 HTML)

8주차 발표용. 백엔드 없이도 열리고(`data/snapshot.json` 의 숫자), 배포 주소에서 열면 Render API 가 깨어 있을 때 실시간 값으로 덮어쓴다.

- 로컬 확인: `python3 -m http.server 5180 -d apps/team-page` → http://localhost:5180 (실시간을 보려면 `?live`)
- 숫자 갱신: `.venv/bin/python scripts/snapshot_deck.py` (로컬 서비스) 또는 `API_URL=https://… .venv/bin/python scripts/snapshot_deck.py`
- 주소 설정: `deck.js` 의 `CONFIG.api` · `CONFIG.web`
- 배포: Vercel — Root Directory `apps/team-page`, Framework `Other`. CLI: `cd apps/team-page && npx vercel --prod`
- 쇼릴(모션그래픽, 전체 1분 40초 · 발표용 짧은 컷 `?short` 1분 16초, 숫자는 `data/snapshot.json`): `showreel.html` → 배포 주소 `/showreel.html`. 발표 페이지 3장에 iframe 으로 들어가 화면 가득 자동 재생된다(`?once&embed&short`). 발표 페이지에서 Space 멈춤·재생, R 처음부터, ← → 는 장 넘김(iframe 안에 포커스가 있어도), F 는 발표 페이지 전체화면. 따로 열면 Space 재생·정지, ← → 장면 이동, R 처음, F 전체화면. `?once` 한 번만, `?start=N` N번 장면부터, `?still` 모션 없이 최종 장면만(스틸컷). 영상 파일이 필요하면 전체화면으로 열고 화면 녹화(QuickTime: ⌘⇧5).
- 키보드 ← → 로 넘긴다(F 전체화면). Reveal.js 식 연출: 장 안의 단계 요소(`.fg`, `.fglist` 자식, `.steps` 안의 `.step` 은 현재 단계만 밝고 지나간 단계는 흐림)는 → 로 하나씩 등장하고 오른쪽 아래에 `2 / 6` 로 남은 단계가 보인다. 장 전환은 `data-transition="fade|slide|zoom"`. `?static` 이면 단계 없이 전부 보인다. 같은 내용의 Markdown 판은 `slides.md`(Slidev 형식, `npx slidev slides.md`). 밝은 바탕·큰 글씨(강의실 조명 대비). 글자는 최소, 숫자·그림 위주 — 설명은 대본(비공개)에. 20장 = 본편 17 + 부록 2(DB·API 문서, 18·19장) + 마무리(20장, 질의응답 내내 주소·QR 이 떠 있게 맨 뒤).
- `dataflow.html` + `dataflow.mp4`(7MB, 1080p, 1분 58초): 팀원이 만든 데이터 흐름 모션그래픽. README 와 발표 페이지 상단 바·18장에서 링크.
- `index.legacy.html` · `style.legacy.css` 는 5주차 피칭 페이지(팀원 제작). 일러스트 `img/story-*.webp` 는 재사용.

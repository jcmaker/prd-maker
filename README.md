# prd-maker

아이디어를 말하면, AI 코딩 에이전트가 그대로 실행할 수 있는 `PRD.md`를 만들어주는 Claude Code 플러그인.

비개발자도 쓸 수 있습니다 — 기술 수준을 감지해서 질문의 어휘와 깊이를 조절하고, 기술 결정이 필요하면 근거와 함께 합리적 기본값을 제안합니다.

## 설치

Claude Code에서:

```
/plugin marketplace add jcmaker/prd-maker
/plugin install prd-maker@prd-maker
```

## 사용법

```
/prd-maker
```

또는 아이디어를 바로 붙여서:

```
/prd-maker 동네 러닝 크루 모임 앱을 만들고 싶어
```

적응형 인터뷰(최대 10문항)가 진행되고, 끝나면 현재 디렉토리에 `PRD.md`가 생성됩니다. 이 파일을 새 Claude Code 세션(또는 다른 AI 코딩 도구)에 주고 "이 PRD대로 구현해줘"라고 하면 됩니다.

## 만들어지는 PRD의 구조

1. 개요 (문제·목표) · 2. 대상 사용자 & JTBD · 3. 핵심 기능 · 4. Non-Goals · 5. 기술 제약 & 기존 결정 · 6. 페이즈별 요구사항 (체크박스 수용기준) · 7. 성공 지표

에이전트용 best practice가 템플릿에 인코딩되어 있습니다: 명시적 non-goals, 기계 검증 가능한 수용기준, 페이즈 분할(no dead ends), `(가정)` 표시, living document 헤더.

## 라이선스

MIT

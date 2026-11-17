# mousex-curskin

[Mouse X](https://store.steampowered.com/app/4255580/) 커서 스킨 파일(`.curskin`)을 만들고 분석하는 Claude Code 스킬입니다.

- `SKILL.md`: 파일 형식, 편집기가 파일을 거부하는 원인, 검증 절차
- `scripts/curskin_tool.py`: 스킨 생성(`build`), 구조 출력(`dump`), 비교(`compare`)

## 설치

```bash
git clone https://github.com/miziyo/mousex-curskin-skill ~/.claude/skills/mousex-curskin
```

## 도구 사용법

```bash
python scripts/curskin_tool.py build spec.json out.curskin
python scripts/curskin_tool.py dump out.curskin
python scripts/curskin_tool.py compare ref.curskin out.curskin
```

`build`와 이미지 정보 출력에는 Pillow(AVIF 지원 버전)가 필요합니다.

## 핵심 규칙

- 루트에는 변형(`#1`)과 `#6 = 1`만 씁니다.
- `#4 = 1`(워크숍 배포본 표시)을 넣으면 편집기가 "편집할 수 없음"으로 거부합니다.
- `#6 = 1`을 빼면 "Failed to load any variants" 오류가 납니다.

Mouse X 1.5.5 기준으로 분석한 비공식 문서입니다.

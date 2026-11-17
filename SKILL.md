---
name: mousex-curskin
description: Mouse X(Steam 앱 4255580) 커서 스킨 파일(.curskin)을 만들거나 고치거나 분석할 때 반드시 먼저 읽는다. 마우스 커서 스킨, Mouse X 스킨 편집기, curskin, 커서 워크숍 업로드, 레이어 포인터, 반응형 포인터 작업이 해당된다. 파일 형식, 편집기가 파일을 거부하는 원인, 검증 절차, 생성 스크립트가 들어 있다.
---

# Mouse X 커서 스킨(.curskin)

Mouse X 1.5.5 기준으로 워크숍 스킨 7개와 편집기가 직접 저장한 파일을 분석해 확인한 내용이다.
추측으로 필드를 넣지 않는다. 모르는 필드는 편집기가 저장한 기준 파일로 확인한다.

## 위치

| 항목 | 경로 |
|---|---|
| 프로그램 | `D:\steamlibrary\steamapps\common\mousex\installed\cursorqt_core.exe` |
| 워크숍 스킨 | `D:\steamlibrary\steamapps\workshop\content\4255580\<아이템ID>\skin.curskin` |
| 설정 | `%APPDATA%\MouseX\settings.ini` (현재 스킨, 스킨별 Scale/Speed/Variant) |
| 로그 | `%APPDATA%\MouseX\log.txt` (스킨 로드 실패 원인이 `[WARN]`으로 남는다) |

`.curskin`은 Windows 파일 연결이 없다. 편집기의 파일 열기로만 연다.

## 파일 형식 (protobuf, 스키마 없음)

```
Root
  #1  Variant (반복)            #1 이름  #2 링크  #4 PointerEntry (반복)  #5 미리보기 상태 이름
  #2  스킨 제목   #3 작성자   #5 설명
  #4  int 1  = 워크숍 배포본 표시   ← 절대 넣지 않는다 (아래 함정 1)
  #6  int 1  = 편집기 저장 형식     ← 반드시 넣는다
  #7  float 기본 크기   #10 테마 색 {#1 색, #2 색, #3 PNG, #4 float}   #11 워크숍 ID
PointerEntry  #1 상태 이름(문자열)  #2 PointerData
PointerData   #1 이미지 바이트  #2 형식(PDT)  #3 Hotspot {#1 x(float32), #2 y(float32)}
              #6 레이어 목록 (PDT 6일 때)
```

- 핫스팟은 픽셀이 아니라 이미지 크기 대비 비율(0~1)이다. 칸 중심이면 `(칸+0.5)/격자수`.
- 핫스팟이 (0,0)이면 편집기는 `#3`을 빈 메시지로 쓰거나 생략한다.
- 편집기는 가져온 이미지 바이트를 다시 인코딩하지 않고 그대로 저장한다.

### 형식 번호(PDT)

| 값 | 이름 | 비고 |
|---|---|---|
| 1 | PDT_IMG | PNG 등 정지 이미지 |
| 2 | PDT_GIF | 반투명 없음. 가장자리가 거칠다 |
| 3 | PDT_SVG | |
| 4 | PDT_PROCEDURAL_BOUNCYBALL | 개발용 |
| 5 | PDT_AVIF | 애니메이션 AVIF(`ftypavis`). 워크숍 스킨 대부분이 사용 |
| 6 | PDT_COMPOSITE | 레이어 포인터. 레이어마다 이름, 이미지, 위치, 투명도, 크기, 혼합 모드(CM_MULTIPLY/SCREEN/OVERLAY) |
| 7 | PDT_REACTIVE | 반응형 포인터. 이벤트 EVT_IDLE, EVT_MOVE_{NORTH..NORTHWEST} 8방향, 마우스 버튼. Idle 이벤트의 Loop 단계 이미지가 필수 |

PDT 6, 7의 세부 필드는 아직 완전히 분석하지 않았다. 만들기 전에 편집기에서 하나를 저장받아 `dump`로 확인한다.

### 상태 이름 (편집기 한글 항목 ↔ 파일)

| 편집기 | 파일 | Windows 레지스트리 |
|---|---|---|
| 화살표 | ARROW | Arrow |
| 십자 | CROSS | Crosshair |
| 사용 중 | WAIT | Wait |
| I빔 | IBEAM | IBeam |
| 세로 크기 조정 | SIZE_VERTICAL | SizeNS |
| 가로 크기 조정 | SIZE_HORIZONTAL | SizeWE |
| 역대각선 크기 조정 (`\`) | SIZE_FDIAGONAL | SizeNWSE |
| 정대각선 크기 조정 (`/`) | SIZE_BDIAGONAL | SizeNESW |
| 모든 방향 크기 조정 | SIZE_ALL | SizeAll |
| 손 모양 | POINTING_HAND | Hand |
| 금지됨 | FORBIDDEN | No |
| 이것은 무엇입니까 | WHATSTHIS | Help |
| 작업 중 | BUSY | AppStarting |

WAIT와 BUSY를 바꾸지 않는다. Qt 기준으로 WAIT는 모래시계, BUSY는 화살표+대기 표시다.

## 함정 (실제로 겪은 실수)

1. **`#4 = 1`을 넣으면 편집기가 거부한다.** 메시지: "The chosen file cannot be edited." / "선택한 파일을 편집할 수 없음".
   워크숍에서 받은 파일에는 이 값이 있다. 워크숍 파일 구조를 그대로 따라 하면 이 실수가 생긴다.
2. **`#6 = 1`을 빼도 실패한다.** 로그: `Failed to load any variants from proto skin`.
   두 표시의 의미를 반대로 추측해서 두 번 실패했다. 추측하지 말고 기준 파일과 비교한다.
3. 워크숍 스킨을 복사해도 편집기에서 열리지 않는다. `#4` 때문이다. 다른 사람의 배포본은 편집 대상으로 쓰지 않는다.
4. 이미지 크기는 원인이 아니다. 32, 48, 64, 128, 181px이 모두 쓰인다. 128px 애니메이션 AVIF 16~24프레임도 정상이다.
5. Pillow AVIF 출력은 워크숍 AVIF와 박스 구조가 같다. `subsampling="4:4:4"`, `quality=95`를 쓴다.
6. Pillow로 다시 읽으면 AVIF `duration`이 None으로 나온다. 프레임 간격은 `stts` 박스와 `mdhd` timescale로 확인한다.

## 작업 절차

1. 상태별 이미지를 준비한다. 애니메이션은 AVIF로 저장한다.
2. 스펙 JSON을 쓴다. 형식은 `scripts/curskin_tool.py` 머리말을 본다.
3. 생성한다: `python scripts/curskin_tool.py build spec.json out.curskin`
4. 검증한다: `python scripts/curskin_tool.py dump out.curskin`
   - 루트에 `#1`(변형)과 `#6 int 1`만 있어야 한다. `#4`가 있으면 안 된다.
   - 13개 상태가 모두 있고, 형식 번호와 핫스팟이 맞아야 한다.
5. 새 기능(레이어, 반응형 등)이나 형식이 의심되면 기준 파일을 받는다.
   1. 사용자에게 편집기에서 새 빈 문서를 만들게 한다.
   2. 이미지 하나만 가져와 `ref.curskin`으로 저장하게 한다.
   3. `python scripts/curskin_tool.py compare ref.curskin mine.curskin`으로 비교한다.
      AVIF 안의 생성 시각(mvhd/tkhd/mdhd) 외에는 같아야 한다.
6. 사용자가 편집기에서 연다. 열리지 않으면 `log.txt` 끝부분의 `[WARN]`을 먼저 읽는다.

## 적용과 워크숍

- 편집기에서 연 스킨은 **워크숍에 등록해야 Mouse X에서 쓸 수 있다.**
- 혼자 쓰는 스킨은 등록할 때 공개 범위를 비공개로 한다. 사용자는 이 방식을 쓴다.
- 등록 조건: 썸네일 이미지가 있어야 한다. 완전히 투명한 상태 이미지가 있으면 거부된다.
- 등록 후 워크숍 폴더에 받은 파일에는 `#4 = 1`이 붙는다. 수정은 원본 파일(편집기 저장본)에서 한다.

## 관련 작업물

- Nothing Dot 스킨 프로젝트: `C:\Users\miziyo\Desktop\nothing-cursor-skin`
  - `nothing-cursor/build.py`: 도트 매트릭스 커서 렌더러 (Windows .ani도 생성)
  - `nothing-cursor/make_curskin.py`: Nothing Dot 전용 curskin 생성기
  - `ref.curskin`: 편집기가 저장한 기준 파일 (화살표 1개)
  - `nothing-dot.spec.json`: `curskin_tool.py build`용 스펙 예시 (13개 상태, hotspot_px)
  - 사용자는 이 스킨을 워크숍에 비공개로 등록해서 쓰고 있다 (2026-11-17)

## 도구 참고

- `compare`는 상태 순서를 무시한다. 순서는 의미가 없다.
- `dump` 끝의 [검사] 줄에서 `#6`, `#4`, 상태 개수를 바로 확인한다.
- PowerShell로 JSON을 쓰면 BOM이 붙는다. 도구는 BOM을 허용한다.

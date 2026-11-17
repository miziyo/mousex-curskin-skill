"""Mouse X .curskin 생성·분석 도구.

사용법
  python curskin_tool.py build spec.json out.curskin   스펙으로 스킨 생성
  python curskin_tool.py dump  file.curskin            구조 출력 (이미지는 크기·프레임만)
  python curskin_tool.py compare a.curskin b.curskin   두 파일의 구조 차이 출력

spec.json 예시 (경로는 spec.json 기준 상대 경로)
  {
    "variants": [
      {
        "name": "Default",
        "pointers": {
          "ARROW": {"image": "states/arrow.avif", "hotspot_px": [12, 12]},
          "IBEAM": {"image": "states/ibeam.avif", "hotspot": [0.47, 0.47]}
        }
      }
    ]
  }
- hotspot: 0~1 비율. hotspot_px: 픽셀 좌표 (이미지 크기로 비율 변환, Pillow 필요).
- 형식 번호는 확장자로 정한다: .png .bmp .jpg=1, .gif=2, .svg=3, .avif=5.
- 루트에는 변형(#1)과 #6=1만 쓴다. #4(워크숍 배포본 표시)는 쓰지 않는다.
"""
import io
import json
import struct
import sys
from pathlib import Path

STATES = ["ARROW", "IBEAM", "WAIT", "BUSY", "CROSS", "SIZE_VERTICAL", "SIZE_HORIZONTAL",
          "SIZE_FDIAGONAL", "SIZE_BDIAGONAL", "SIZE_ALL", "POINTING_HAND", "FORBIDDEN", "WHATSTHIS"]
PDT_BY_EXT = {".png": 1, ".bmp": 1, ".jpg": 1, ".jpeg": 1, ".gif": 2, ".svg": 3, ".avif": 5}
PDT_NAMES = {1: "IMG", 2: "GIF", 3: "SVG", 4: "BOUNCYBALL", 5: "AVIF", 6: "COMPOSITE", 7: "REACTIVE"}


# ---------- 인코더 ----------

def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def f_bytes(field, data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return varint(field << 3 | 2) + varint(len(data)) + data


def f_int(field, n):
    return varint(field << 3) + varint(n)


def f_float(field, x):
    return varint(field << 3 | 5) + struct.pack("<f", x)


def image_size(data):
    from PIL import Image
    return Image.open(io.BytesIO(data)).size


def build(spec_path, out_path):
    spec_path = Path(spec_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))  # PowerShell이 붙이는 BOM 허용
    root = b""
    for var in spec["variants"]:
        missing = [s for s in STATES if s not in var["pointers"]]
        unknown = [s for s in var["pointers"] if s not in STATES]
        if unknown:
            sys.exit(f"알 수 없는 상태 이름: {unknown}")
        if missing:
            print(f"경고: 변형 '{var['name']}'에 없는 상태: {missing}")
        body = f_bytes(1, var["name"])
        for state, p in var["pointers"].items():
            img_path = (spec_path.parent / p["image"]).resolve()
            data = img_path.read_bytes()
            pdt = PDT_BY_EXT.get(img_path.suffix.lower())
            if pdt is None:
                sys.exit(f"지원하지 않는 확장자: {img_path}")
            if "hotspot_px" in p:
                w, h = image_size(data)
                hx, hy = p["hotspot_px"][0] / w, p["hotspot_px"][1] / h
            else:
                hx, hy = p.get("hotspot", [0.0, 0.0])
            hotspot = (f_float(1, hx) if hx else b"") + (f_float(2, hy) if hy else b"")
            pdata = f_bytes(1, data) + f_int(2, pdt) + f_bytes(3, hotspot)
            body += f_bytes(4, f_bytes(1, state) + f_bytes(2, pdata))
        root += f_bytes(1, body)
    root += f_int(6, 1)
    Path(out_path).write_bytes(root)
    print(f"{out_path}: {len(root):,} bytes")


# ---------- 디코더 ----------

def read_varint(b, i):
    r = s = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        s += 7
        if c < 0x80:
            return r, i


def parse(b):
    """protobuf로 끝까지 읽히면 [(필드, 타입, 값)], 아니면 None."""
    try:
        i, out = 0, []
        while i < len(b):
            key, i = read_varint(b, i)
            f, wt = key >> 3, key & 7
            if f == 0 or f > 1000:
                return None
            if wt == 0:
                v, i = read_varint(b, i)
                out.append((f, "int", v))
            elif wt == 5:
                out.append((f, "float", struct.unpack("<f", b[i:i + 4])[0]))
                i += 4
            elif wt == 1:
                out.append((f, "double", struct.unpack("<d", b[i:i + 8])[0]))
                i += 8
            elif wt == 2:
                n, i = read_varint(b, i)
                if i + n > len(b):
                    return None
                out.append((f, "bytes", b[i:i + n]))
                i += n
            else:
                return None
        return out
    except (IndexError, struct.error):
        return None


def describe_image(v):
    kind = "AVIF" if v[4:8] == b"ftyp" else "PNG" if v[:4] == b"\x89PNG" else "GIF" if v[:3] == b"GIF" else None
    if not kind:
        return None
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(v))
        return f"{kind} {im.size[0]}x{im.size[1]} frames={getattr(im, 'n_frames', 1)} ({len(v):,} bytes)"
    except Exception as e:  # noqa: BLE001
        return f"{kind} ({len(v):,} bytes, 읽기 실패: {e})"


def lines(b, ind=0):
    out = []
    for f, t, v in parse(b) or []:
        p = "  " * ind + f"#{f} "
        if t != "bytes":
            out.append(p + f"{t} {v:.4g}" if t != "int" else p + f"int {v}")
            continue
        img = describe_image(v)
        if img:
            out.append(p + img)
            continue
        sub = parse(v) if len(v) > 1 else None
        try:
            text = v.decode("utf-8")
            text = text if text.isprintable() else None
        except UnicodeDecodeError:
            text = None
        if text is not None and (sub is None or len(v) < 40):
            out.append(p + repr(text))
        elif sub:
            out.append(p + "{")
            out += lines(v, ind + 1)
            out.append("  " * ind + "}")
        else:
            out.append(p + f"bytes {len(v)}")
    return out


def dump(path):
    b = Path(path).read_bytes()
    root = parse(b)
    if root is None:
        sys.exit("protobuf로 읽을 수 없는 파일이다.")
    print("\n".join(lines(b)))
    keys = {f: v for f, t, v in root if t == "int"}
    print("\n[검사]")
    print(" #6 = 1 :", "OK" if keys.get(6) == 1 else "없음 -> 편집기에서 'Failed to load any variants'")
    print(" #4     :", "없음 OK" if 4 not in keys else "있음 -> 편집기가 '편집할 수 없음'으로 거부")
    for f, t, v in root:
        if f != 1:
            continue
        var = parse(v)
        names = [parse(e)[0][2].decode() for ff, tt, e in var if ff == 4]
        vname = next((x[2].decode() for x in var if x[0] == 1), "?")
        miss = [s for s in STATES if s not in names]
        print(f" 변형 '{vname}': 상태 {len(names)}개" + (f", 없음 {miss}" if miss else ""))


def canonical(b):
    """상태 순서는 의미가 없으므로 상태 이름순으로 다시 배열한 바이트를 돌려준다."""
    out = b""
    for f, t, v in parse(b):
        if f == 1 and t == "bytes" and parse(v):
            var = parse(v)
            head = b"".join(f_bytes(ff, vv) for ff, tt, vv in var if ff != 4 and tt == "bytes")
            ents = sorted((vv for ff, tt, vv in var if ff == 4), key=lambda e: parse(e)[0][2])
            out += f_bytes(1, head + b"".join(f_bytes(4, e) for e in ents))
        elif t == "int":
            out += f_int(f, v)
        elif t == "float":
            out += f_float(f, v)
        elif t == "bytes":
            out += f_bytes(f, v)
    return out


def compare(a, b):
    la, lb = lines(canonical(Path(a).read_bytes())), lines(canonical(Path(b).read_bytes()))
    import difflib
    diff = list(difflib.unified_diff(la, lb, a, b, lineterm="", n=1))
    print("\n".join(diff) if diff else "구조가 같다 (이미지는 크기·프레임 수만 비교).")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "build" and len(sys.argv) == 4:
        build(sys.argv[2], sys.argv[3])
    elif cmd == "dump":
        dump(sys.argv[2])
    elif cmd == "compare" and len(sys.argv) == 4:
        compare(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)

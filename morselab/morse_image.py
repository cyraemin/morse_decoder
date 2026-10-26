"""Read Morse code symbols from an image (local, uses only Pillow and NumPy).

This is a simple shape detector, not general OCR. It works on clear,
high-contrast images of printed or neatly drawn Morse code: dots, dashes and
"/" (or "|") word separators on a plain background, in either dark-on-light
or light-on-dark colours.

Steps:
1. Load the image, convert to greyscale and scale large images down.
2. Separate marks from background with an automatic (Otsu) threshold.
3. Find each connected mark and measure its size and shape.
4. Classify marks: round/square = dot, wide = dash, tall diagonal = "/".
5. Read marks left to right, row by row. Small gaps join symbols of one
   letter, larger gaps separate letters (1 / 3 / 7 unit spacing rule).
6. Validate the result with the existing decoder in morse_logic.
"""
import io
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

import morse_logic as ml

MAX_FILE_BYTES = 5 * 1024 * 1024    # 5 MB
MAX_PIXELS = 40_000_000             # refuse extremely large images
WORK_SIDE = 1600                    # longest side used for analysis
MAX_MARKS = 800                     # more marks than this is not a Morse image
SUPPORTED_FORMATS = {"PNG", "JPEG"}


@dataclass
class ExtractResult:
    morse: str = ""                                  # extracted sequence ("" on failure)
    error: str = ""                                  # why extraction failed
    warnings: list = field(default_factory=list)     # problems the user should check
    symbols: int = 0                                 # number of dots and dashes found


@dataclass
class _Mark:
    x0: int
    y0: int
    x1: int
    y1: int
    area: int
    corr: float          # x-y correlation of the mark's pixels (slope direction)
    kind: str = ""       # "dot", "dash", "sep" or "other"

    @property
    def w(self):
        return self.x1 - self.x0 + 1

    @property
    def h(self):
        return self.y1 - self.y0 + 1

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2

    @property
    def fill(self):
        return self.area / (self.w * self.h)


# --------------------------------------------------------------------------
# 1. Loading
# --------------------------------------------------------------------------
def load_image(data):
    """Open uploaded bytes as an RGB image. Returns (image, error_message)."""
    if not data:
        return None, "The uploaded file is empty."
    if len(data) > MAX_FILE_BYTES:
        return None, f"The image is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB. Please upload a smaller file."
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in SUPPORTED_FORMATS:
            return None, "Unsupported image format. Please upload a PNG or JPG file."
        if img.width * img.height > MAX_PIXELS:
            return None, "The image has too many pixels. Please upload a smaller or cropped image."
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            # Put transparent images on a white background.
            rgba = img.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            img = Image.alpha_composite(background, rgba)
        return img.convert("RGB"), ""
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return None, "This file could not be read as an image. It may be damaged or not a real PNG/JPG."


# --------------------------------------------------------------------------
# 2. Thresholding
# --------------------------------------------------------------------------
def _otsu_threshold(gray):
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    weight = np.cumsum(hist) / gray.size
    mean = np.cumsum(hist * np.arange(256)) / gray.size
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (mean[-1] * weight - mean) ** 2 / (weight * (1 - weight))
    between[~np.isfinite(between)] = 0
    return int(np.argmax(between))


# --------------------------------------------------------------------------
# 3. Connected marks (run-length labelling, 8-connected)
# --------------------------------------------------------------------------
def _find_marks(mask):
    parent = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    run_y, run_s, run_e, run_label = [], [], [], []
    prev = []                                   # runs of the previous row: (start, end, label)
    for y in range(mask.shape[0]):
        edges = np.diff(np.concatenate(([0], mask[y].astype(np.int8), [0])))
        starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)   # end is exclusive
        current, k = [], 0
        for s, e in zip(starts.tolist(), ends.tolist()):
            while k < len(prev) and prev[k][1] < s:      # previous run ends before this one starts
                k += 1
            label = None
            j = k
            while j < len(prev) and prev[j][0] <= e:     # overlapping or diagonal neighbours
                other = find(prev[j][2])
                if label is None:
                    label = other
                elif other != label:
                    parent[other] = label
                j += 1
            if label is None:
                label = len(parent)
                parent.append(label)
            current.append((s, e, label))
            run_y.append(y); run_s.append(s); run_e.append(e); run_label.append(label)
        prev = current
        if len(parent) > MAX_MARKS * 20:
            return None                                  # far too many shapes: not a Morse image

    if not run_y:
        return []
    y = np.array(run_y, dtype=float)
    s = np.array(run_s, dtype=float)
    e = np.array(run_e, dtype=float)
    roots = np.array([find(l) for l in run_label])
    ids, inv = np.unique(roots, return_inverse=True)

    n = e - s                                            # pixels in each run
    sx = n * (s + e - 1) / 2                             # sum of x over the run
    sxx = ((e - 1) * e * (2 * e - 1) - (s - 1) * s * (2 * s - 1)) / 6
    total = lambda v: np.bincount(inv, weights=v, minlength=len(ids))
    area, sum_x, sum_y = total(n), total(sx), total(n * y)
    sum_xx, sum_yy, sum_xy = total(sxx), total(n * y * y), total(y * sx)
    mx, my = sum_x / area, sum_y / area
    var_x = sum_xx / area - mx ** 2
    var_y = sum_yy / area - my ** 2
    cov = sum_xy / area - mx * my
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.nan_to_num(cov / np.sqrt(var_x * var_y))

    x0 = np.full(len(ids), np.inf); x1 = np.full(len(ids), -np.inf)
    y0 = np.full(len(ids), np.inf); y1 = np.full(len(ids), -np.inf)
    np.minimum.at(x0, inv, s); np.maximum.at(x1, inv, e - 1)
    np.minimum.at(y0, inv, y); np.maximum.at(y1, inv, y)
    return [_Mark(int(x0[i]), int(y0[i]), int(x1[i]), int(y1[i]), int(area[i]), float(corr[i]))
            for i in range(len(ids))]


# --------------------------------------------------------------------------
# 4. Classification
# --------------------------------------------------------------------------
def _classify(m):
    wide, tall = m.w / m.h, m.h / m.w
    if wide >= 1.8 and m.fill >= 0.5:
        return "dash"
    if tall >= 1.5 and m.fill < 0.65 and m.corr < -0.6:
        return "sep"                                     # "/" rises to the right
    if tall >= 2.5 and m.fill >= 0.65:
        return "sep"                                     # "|"
    if wide < 1.8 and tall < 1.5 and m.fill >= 0.45:
        return "dot"
    return "other"


# --------------------------------------------------------------------------
# 5-6. Main entry point
# --------------------------------------------------------------------------
def extract_morse(data):
    """Extract a Morse sequence from image bytes. Never raises for bad input."""
    result = ExtractResult()
    img, error = load_image(data)
    if error:
        result.error = error
        return result

    gray_img = img.convert("L")
    scale = WORK_SIDE / max(gray_img.size)
    if scale < 1 or max(gray_img.size) < 400:            # shrink huge images, enlarge tiny ones
        scale = min(scale, 3.0)
        gray_img = gray_img.resize((max(1, round(gray_img.width * scale)),
                                    max(1, round(gray_img.height * scale))), Image.LANCZOS)
    gray = np.asarray(gray_img, dtype=np.uint8)

    t = _otsu_threshold(gray)
    dark = gray <= t
    if dark.all() or not dark.any():
        result.error = "The image looks blank. No dots or dashes were found."
        return result
    marks_mask = dark if dark.mean() <= 0.5 else ~dark   # marks are the smaller colour class
    contrast = abs(float(gray[dark].mean()) - float(gray[~dark].mean()))
    if contrast < 50:
        result.error = ("The image has very low contrast, so the symbols cannot be separated from the "
                        "background reliably. Try a sharper, better-lit image, or type the code manually.")
        return result

    marks = _find_marks(marks_mask)
    if marks is None or len(marks) > MAX_MARKS:
        result.error = ("The image contains too many shapes to be a Morse code image (it may be a photo "
                        "or contain other text). Crop it to just the Morse code, or type it manually.")
        return result

    # Ignore specks of noise and a frame around the whole image.
    H, W = marks_mask.shape
    if marks:
        biggest = max(m.area for m in marks)
        marks = [m for m in marks if m.area >= max(4, 0.01 * biggest)]
        framed = [m for m in marks if m.w > 0.9 * W and m.h > 0.9 * H]
        marks = [m for m in marks if m not in framed]
    for m in marks:
        m.kind = _classify(m)

    # Dots that are much bigger than the typical dot are not dots.
    dots = [m for m in marks if m.kind == "dot"]
    if dots:
        dot_size = float(np.median([max(m.w, m.h) for m in dots]))
        for m in dots:
            if max(m.w, m.h) > 3 * dot_size:
                m.kind = "other"

    symbols = [m for m in marks if m.kind in ("dot", "dash", "sep")]
    others = [m for m in marks if m.kind == "other"]
    result.symbols = sum(m.kind != "sep" for m in symbols)
    if result.symbols == 0:
        result.error = ("No dots or dashes were recognised in this image. Use a clear image of printed or "
                        "neatly drawn Morse code, or type the code manually.")
        return result
    if len(others) > result.symbols:
        result.error = ("Most shapes in this image are not dots, dashes or '/' (it may contain letters or "
                        "drawings). Crop it to just the Morse code, or type the code manually.")
        return result
    if others:
        result.warnings.append(f"{len(others)} shape(s) were not dots, dashes or '/' and were ignored.")

    result.morse = _read_sequence(symbols)
    decoded = ml.decode(result.morse)
    if not decoded.ok:
        result.warnings.append("Some groups are not valid Morse letters (shown as '?' when decoded). "
                               "The image may be unclear: please check the sequence before decoding.")
    return result


def _read_sequence(symbols):
    """Turn classified marks into Morse text using row order and gap sizes."""
    dots = [m for m in symbols if m.kind == "dot"]
    dashes = [m for m in symbols if m.kind == "dash"]
    if dots:
        unit = float(np.median([m.w for m in dots]))     # a dot is one unit wide
    else:
        unit = float(np.median([m.w for m in dashes])) / 3

    # Group marks into text rows by their vertical centre.
    rows = []
    for m in sorted(symbols, key=lambda m: m.cy):
        if rows and m.cy - np.mean([r.cy for r in rows[-1]]) <= max(4 * unit, 10):
            rows[-1].append(m)
        else:
            rows.append([m])

    # Estimate the gap between symbols of one letter from the smallest gaps.
    gaps = []
    for row in rows:
        row.sort(key=lambda m: m.x0)
        gaps += [b.x0 - a.x1 - 1 for a, b in zip(row, row[1:]) if a.kind != "sep" and b.kind != "sep"]
    symbol_gap = unit
    if gaps:
        symbol_gap = max(min(float(np.percentile(gaps, 20)), 1.2 * unit), 0.6 * unit)

    out = []
    for row in rows:
        for i, m in enumerate(row):
            if m.kind == "sep":
                out.append(" / ")
                continue
            if i and row[i - 1].kind != "sep":
                gap = m.x0 - row[i - 1].x1 - 1
                if gap >= 5 * symbol_gap:
                    out.append(" / ")
                elif gap >= 2 * symbol_gap:
                    out.append(" ")
            out.append("." if m.kind == "dot" else "-")
        out.append(" ")                                  # a new row starts a new letter
    words = ml.split_morse("".join(out))
    return " / ".join(" ".join(codes) for codes in words)

from __future__ import annotations

import hashlib
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScreenFingerprint:
    width: int
    height: int
    digest: str
    samples: tuple[int, ...]


@dataclass(frozen=True)
class ScreenChange:
    changed: bool
    distance: float
    previous_digest: str
    current_digest: str


def _png_pixels(path: Path) -> tuple[int, int, bytes, int]:
    raw = path.read_bytes()

    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")

    pos = 8
    width = height = 0
    bit_depth = color_type = 0
    idat = bytearray()

    while pos + 8 <= len(raw):
        length = struct.unpack(">I", raw[pos:pos + 4])[0]
        kind = raw[pos + 4:pos + 8]
        data = raw[pos + 8:pos + 8 + length]
        pos += 12 + length

        if kind == b"IHDR":
            (
                width,
                height,
                bit_depth,
                color_type,
                _compression,
                _filter,
                interlace,
            ) = struct.unpack(">IIBBBBB", data)

            if bit_depth != 8:
                raise ValueError("unsupported PNG bit depth")

            if interlace != 0:
                raise ValueError("interlaced PNG unsupported")

        elif kind == b"IDAT":
            idat.extend(data)

        elif kind == b"IEND":
            break

    channels = {
        0: 1,
        2: 3,
        4: 2,
        6: 4,
    }.get(color_type)

    if not channels:
        raise ValueError(
            f"unsupported PNG color type: {color_type}"
        )

    decompressed = zlib.decompress(bytes(idat))
    stride = width * channels

    rows = []
    offset = 0
    previous = bytearray(stride)

    def paeth(a: int, b: int, c: int) -> int:
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)

        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    for _y in range(height):
        filter_type = decompressed[offset]
        offset += 1

        current = bytearray(
            decompressed[offset:offset + stride]
        )
        offset += stride

        for x in range(stride):
            left = (
                current[x - channels]
                if x >= channels
                else 0
            )

            up = previous[x]

            up_left = (
                previous[x - channels]
                if x >= channels
                else 0
            )

            if filter_type == 1:
                current[x] = (
                    current[x] + left
                ) & 0xFF

            elif filter_type == 2:
                current[x] = (
                    current[x] + up
                ) & 0xFF

            elif filter_type == 3:
                current[x] = (
                    current[x]
                    + ((left + up) // 2)
                ) & 0xFF

            elif filter_type == 4:
                current[x] = (
                    current[x]
                    + paeth(
                        left,
                        up,
                        up_left,
                    )
                ) & 0xFF

            elif filter_type != 0:
                raise ValueError(
                    f"unsupported PNG filter: {filter_type}"
                )

        rows.append(bytes(current))
        previous = current

    return (
        width,
        height,
        b"".join(rows),
        channels,
    )


def fingerprint(
    image_path: str,
    *,
    grid_width: int = 32,
    grid_height: int = 18,
) -> ScreenFingerprint:
    path = Path(
        image_path
    ).expanduser().resolve()

    width, height, pixels, channels = _png_pixels(
        path
    )

    values = []

    for gy in range(grid_height):
        y = min(
            height - 1,
            int(
                (gy + 0.5)
                * height
                / grid_height
            ),
        )

        for gx in range(grid_width):
            x = min(
                width - 1,
                int(
                    (gx + 0.5)
                    * width
                    / grid_width
                ),
            )

            base = (
                y * width * channels
                + x * channels
            )

            if channels == 1:
                gray = pixels[base]

            else:
                r = pixels[base]
                g = pixels[base + 1]
                b = pixels[base + 2]

                gray = int(
                    0.299 * r
                    + 0.587 * g
                    + 0.114 * b
                )

            values.append(gray)

    sample_bytes = bytes(values)

    return ScreenFingerprint(
        width=width,
        height=height,
        digest=hashlib.sha256(
            sample_bytes
        ).hexdigest(),
        samples=tuple(values),
    )


def compare(
    previous: ScreenFingerprint | None,
    current: ScreenFingerprint,
    *,
    threshold: float = 0.055,
) -> ScreenChange:
    if previous is None:
        return ScreenChange(
            changed=True,
            distance=1.0,
            previous_digest="",
            current_digest=current.digest,
        )

    if (
        previous.width != current.width
        or previous.height != current.height
        or len(previous.samples)
        != len(current.samples)
    ):
        return ScreenChange(
            changed=True,
            distance=1.0,
            previous_digest=previous.digest,
            current_digest=current.digest,
        )

    total = 0.0

    for a, b in zip(
        previous.samples,
        current.samples,
    ):
        total += abs(a - b) / 255.0

    distance = total / max(
        1,
        len(current.samples),
    )

    return ScreenChange(
        changed=distance >= threshold,
        distance=distance,
        previous_digest=previous.digest,
        current_digest=current.digest,
    )

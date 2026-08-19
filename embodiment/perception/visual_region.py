from __future__ import annotations

import struct
import zlib
from dataclasses import (
    asdict,
    dataclass,
)
from pathlib import Path


@dataclass(frozen=True)
class VisualRegion:
    source_path: str
    crop_path: str
    left: int
    top: int
    right: int
    bottom: int
    width: int
    height: int
    anchor_x: int
    anchor_y: int

    def to_dict(self):
        return asdict(self)

    def to_absolute(
        self,
        *,
        local_x: int,
        local_y: int,
    ) -> tuple[int, int]:
        return (
            self.left + int(local_x),
            self.top + int(local_y),
        )


class PNGRegionCropper:
    """
    Minimal PNG cropper for 8-bit RGB/RGBA images.

    No Pillow dependency.
    """

    PNG_SIGNATURE = (
        b"\x89PNG\r\n\x1a\n"
    )

    @staticmethod
    def _paeth(
        a: int,
        b: int,
        c: int,
    ) -> int:
        p = a + b - c

        pa = abs(
            p - a
        )

        pb = abs(
            p - b
        )

        pc = abs(
            p - c
        )

        if (
            pa <= pb
            and pa <= pc
        ):
            return a

        if pb <= pc:
            return b

        return c

    @classmethod
    def _decode(
        cls,
        path: str,
    ):
        raw = Path(
            path
        ).read_bytes()

        if not raw.startswith(
            cls.PNG_SIGNATURE
        ):
            raise ValueError(
                "not a PNG file"
            )

        offset = 8

        width = None
        height = None
        bit_depth = None
        colour_type = None

        idat = []

        while offset < len(raw):
            length = struct.unpack(
                ">I",
                raw[
                    offset:
                    offset + 4
                ],
            )[0]

            name = raw[
                offset + 4:
                offset + 8
            ]

            payload = raw[
                offset + 8:
                offset + 8 + length
            ]

            offset += (
                12 + length
            )

            if name == b"IHDR":
                (
                    width,
                    height,
                    bit_depth,
                    colour_type,
                    compression,
                    filter_method,
                    interlace,
                ) = struct.unpack(
                    ">IIBBBBB",
                    payload,
                )

                if bit_depth != 8:
                    raise ValueError(
                        "only 8-bit PNG supported"
                    )

                if colour_type not in (
                    2,
                    6,
                ):
                    raise ValueError(
                        "only RGB/RGBA PNG supported"
                    )

                if (
                    compression != 0
                    or filter_method != 0
                    or interlace != 0
                ):
                    raise ValueError(
                        "unsupported PNG encoding"
                    )

            elif name == b"IDAT":
                idat.append(
                    payload
                )

            elif name == b"IEND":
                break

        if (
            width is None
            or height is None
            or colour_type is None
        ):
            raise ValueError(
                "PNG missing IHDR"
            )

        channels = (
            3
            if colour_type == 2
            else 4
        )

        packed = zlib.decompress(
            b"".join(
                idat
            )
        )

        stride = (
            width
            * channels
        )

        expected = (
            height
            * (
                stride + 1
            )
        )

        if len(packed) != expected:
            raise ValueError(
                "unexpected PNG scanline size"
            )

        rows = []

        previous = bytearray(
            stride
        )

        index = 0

        for _ in range(height):
            filter_type = packed[
                index
            ]

            index += 1

            encoded = bytearray(
                packed[
                    index:
                    index + stride
                ]
            )

            index += stride

            decoded = bytearray(
                stride
            )

            for i, value in enumerate(
                encoded
            ):
                left = (
                    decoded[
                        i - channels
                    ]
                    if i >= channels
                    else 0
                )

                up = previous[i]

                upper_left = (
                    previous[
                        i - channels
                    ]
                    if i >= channels
                    else 0
                )

                if filter_type == 0:
                    result = value

                elif filter_type == 1:
                    result = (
                        value
                        + left
                    ) & 255

                elif filter_type == 2:
                    result = (
                        value
                        + up
                    ) & 255

                elif filter_type == 3:
                    result = (
                        value
                        + (
                            (
                                left
                                + up
                            )
                            // 2
                        )
                    ) & 255

                elif filter_type == 4:
                    result = (
                        value
                        + cls._paeth(
                            left,
                            up,
                            upper_left,
                        )
                    ) & 255

                else:
                    raise ValueError(
                        "unsupported PNG filter"
                    )

                decoded[i] = result

            rows.append(
                bytes(decoded)
            )

            previous = decoded

        return (
            width,
            height,
            channels,
            rows,
        )

    @staticmethod
    def _chunk(
        name: bytes,
        payload: bytes,
    ) -> bytes:
        return (
            struct.pack(
                ">I",
                len(payload),
            )
            + name
            + payload
            + struct.pack(
                ">I",
                zlib.crc32(
                    name + payload
                ) & 0xffffffff,
            )
        )

    @classmethod
    def _write(
        cls,
        *,
        path: str,
        width: int,
        height: int,
        channels: int,
        rows: list[bytes],
    ):
        colour_type = (
            2
            if channels == 3
            else 6
        )

        scanlines = b"".join(
            b"\x00"
            + row
            for row in rows
        )

        data = (
            cls.PNG_SIGNATURE
            + cls._chunk(
                b"IHDR",
                struct.pack(
                    ">IIBBBBB",
                    width,
                    height,
                    8,
                    colour_type,
                    0,
                    0,
                    0,
                ),
            )
            + cls._chunk(
                b"IDAT",
                zlib.compress(
                    scanlines,
                ),
            )
            + cls._chunk(
                b"IEND",
                b"",
            )
        )

        Path(
            path
        ).write_bytes(
            data
        )

    def crop_around(
        self,
        *,
        source_path: str,
        x: int,
        y: int,
        radius_x: int = 220,
        radius_y: int = 160,
        output_path: str | None = None,
    ) -> VisualRegion:
        (
            width,
            height,
            channels,
            rows,
        ) = self._decode(
            source_path
        )

        x = max(
            0,
            min(
                int(x),
                width - 1,
            ),
        )

        y = max(
            0,
            min(
                int(y),
                height - 1,
            ),
        )

        radius_x = max(
            32,
            int(radius_x),
        )

        radius_y = max(
            32,
            int(radius_y),
        )

        left = max(
            0,
            x - radius_x,
        )

        right = min(
            width,
            x + radius_x + 1,
        )

        top = max(
            0,
            y - radius_y,
        )

        bottom = min(
            height,
            y + radius_y + 1,
        )

        crop_width = (
            right - left
        )

        crop_height = (
            bottom - top
        )

        cropped = []

        byte_left = (
            left
            * channels
        )

        byte_right = (
            right
            * channels
        )

        for row in rows[
            top:bottom
        ]:
            cropped.append(
                row[
                    byte_left:
                    byte_right
                ]
            )

        if output_path is None:
            source = Path(
                source_path
            )

            output_path = str(
                source.with_name(
                    source.stem
                    + "-neuron-region.png"
                )
            )

        self._write(
            path=output_path,
            width=crop_width,
            height=crop_height,
            channels=channels,
            rows=cropped,
        )

        return VisualRegion(
            source_path=str(
                source_path
            ),
            crop_path=str(
                output_path
            ),
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            width=crop_width,
            height=crop_height,
            anchor_x=x,
            anchor_y=y,
        )

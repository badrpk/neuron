import struct
import zlib

from perception.visual_region import (
    PNGRegionCropper,
)


def write_png(
    path,
    *,
    width=100,
    height=80,
):
    rows = []

    for y in range(height):
        row = bytearray()

        for x in range(width):
            row.extend(
                (
                    x % 256,
                    y % 256,
                    100,
                    255,
                )
            )

        rows.append(
            b"\x00"
            + bytes(row)
        )

    raw = b"".join(
        rows
    )

    def chunk(
        name,
        payload,
    ):
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

    data = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(
            b"IHDR",
            struct.pack(
                ">IIBBBBB",
                width,
                height,
                8,
                6,
                0,
                0,
                0,
            ),
        )
        + chunk(
            b"IDAT",
            zlib.compress(
                raw
            ),
        )
        + chunk(
            b"IEND",
            b"",
        )
    )

    path.write_bytes(
        data
    )


def test_minimum_radius_contract_and_translate(
    tmp_path,
):
    source = (
        tmp_path
        / "screen.png"
    )

    crop = (
        tmp_path
        / "crop.png"
    )

    write_png(
        source,
        width=100,
        height=80,
    )

    region = (
        PNGRegionCropper()
        .crop_around(
            source_path=str(source),
            x=50,
            y=40,

            #
            # Requested values are deliberately below
            # the production 32px minimum.
            #
            radius_x=20,
            radius_y=15,

            output_path=str(crop),
        )
    )

    assert crop.exists()

    #
    # Effective radius becomes 32.
    #
    assert region.left == 18
    assert region.top == 8

    assert region.right == 83
    assert region.bottom == 73

    assert region.width == 65
    assert region.height == 65

    #
    # Anchor must remain the original absolute point.
    #
    assert region.anchor_x == 50
    assert region.anchor_y == 40

    local_x = (
        region.anchor_x
        - region.left
    )

    local_y = (
        region.anchor_y
        - region.top
    )

    absolute = (
        region.to_absolute(
            local_x=local_x,
            local_y=local_y,
        )
    )

    assert absolute == (
        50,
        40,
    )


def test_crop_clamps_to_screen_edges(
    tmp_path,
):
    source = (
        tmp_path
        / "screen.png"
    )

    write_png(
        source,
        width=100,
        height=80,
    )

    region = (
        PNGRegionCropper()
        .crop_around(
            source_path=str(source),
            x=2,
            y=3,
            radius_x=30,
            radius_y=30,
        )
    )

    #
    # 30 becomes 32, then the crop is clamped
    # against the top-left screen boundary.
    #
    assert region.left == 0
    assert region.top == 0

    assert region.anchor_x == 2
    assert region.anchor_y == 3

    assert region.right == 35
    assert region.bottom == 36


def test_small_image_becomes_full_image_crop(
    tmp_path,
):
    source = (
        tmp_path
        / "screen.png"
    )

    crop = (
        tmp_path
        / "crop.png"
    )

    write_png(
        source,
        width=20,
        height=20,
    )

    cropper = (
        PNGRegionCropper()
    )

    region = cropper.crop_around(
        source_path=str(source),
        x=10,
        y=10,
        radius_x=3,
        radius_y=2,
        output_path=str(crop),
    )

    (
        width,
        height,
        channels,
        rows,
    ) = cropper._decode(
        str(crop)
    )

    #
    # 32px minimum radius is larger than the image,
    # therefore the bounded crop correctly becomes the
    # whole image.
    #
    assert region.left == 0
    assert region.top == 0
    assert region.right == 20
    assert region.bottom == 20

    assert width == 20
    assert height == 20
    assert channels == 4

    #
    # Pixel identity must still be preserved.
    #
    first_pixel = tuple(
        rows[0][0:4]
    )

    assert first_pixel == (
        0,
        0,
        100,
        255,
    )

    center_offset = (
        10
        * channels
    )

    center_pixel = tuple(
        rows[10][
            center_offset:
            center_offset + channels
        ]
    )

    assert center_pixel == (
        10,
        10,
        100,
        255,
    )


def test_larger_requested_radius_is_respected(
    tmp_path,
):
    source = (
        tmp_path
        / "screen.png"
    )

    write_png(
        source,
        width=200,
        height=150,
    )

    region = (
        PNGRegionCropper()
        .crop_around(
            source_path=str(source),
            x=100,
            y=75,
            radius_x=40,
            radius_y=35,
        )
    )

    #
    # Values above the minimum are preserved.
    #
    assert region.left == 60
    assert region.right == 141

    assert region.top == 40
    assert region.bottom == 111

    assert region.width == 81
    assert region.height == 71

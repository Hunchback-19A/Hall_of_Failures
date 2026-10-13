# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Segment-profile pictures of a morphology grid.

Red is the A-block fraction and blue is one minus that fraction. Green is the
crossing between them. A separate yellow surface is drawn where the fraction
crosses one half. The pictures use the grid they are given. They do not
replace it with another calculation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

_LEVEL = 0.5
_INSET = 0.04
_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)
_CORNERS = np.array(
    [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
    dtype=float,
)


def write_segment_figures(folder: Path, stem: str, morphology: dict[str, Any]) -> dict[str, str]:
    phi = _phi(morphology)
    names = {
        "profile": f"{stem}.profile.png",
        "segment": f"{stem}.segment.png",
        "interface": f"{stem}.interface.png",
    }
    _save(folder / names["profile"], _profile_image(phi, morphology))
    _save(folder / names["segment"], _cell_image(phi, morphology))
    _save(folder / names["interface"], _interface_image(phi, morphology))
    return names


def _phi(morphology: dict[str, Any]) -> np.ndarray:
    nx, ny, nz = (int(size) for size in morphology["mesh"])
    values = np.asarray(morphology["phi_a"], dtype=float)
    if values.size != nx * ny * nz:
        raise ValueError(f"Morphology grid has {values.size} values; the mesh needs {nx * ny * nz}")
    return values.reshape((nz, ny, nx))


def _jet(fraction: np.ndarray) -> np.ndarray:
    t = np.clip(np.asarray(fraction, dtype=float), 0.0, 1.0)
    red = np.zeros(t.shape)
    green = np.zeros(t.shape)
    blue = np.zeros(t.shape)
    low = t < 0.25
    mid_low = (t >= 0.25) & (t < 0.5)
    mid_high = (t >= 0.5) & (t < 0.75)
    high = t >= 0.75
    green[low] = t[low] / 0.25
    blue[low] = 1.0
    green[mid_low] = 1.0
    blue[mid_low] = 1.0 - (t[mid_low] - 0.25) / 0.25
    red[mid_high] = (t[mid_high] - 0.5) / 0.25
    green[mid_high] = 1.0
    red[high] = 1.0
    green[high] = 1.0 - (t[high] - 0.75) / 0.25
    return (np.stack((red, green, blue), axis=-1) * 255.0).astype(np.uint8)


def _profile_line(phi: np.ndarray) -> tuple[str, np.ndarray]:
    nz, ny, nx = phi.shape
    cx, cy, cz = nx // 2, ny // 2, nz // 2
    lines = {
        "x": phi[cz, cy, :],
        "y": phi[cz, :, cx],
        "z": phi[:, cy, cx],
    }
    axis = max(lines, key=lambda name: float(np.ptp(lines[name])))
    return axis, np.asarray(lines[axis], dtype=float)


def _profile_image(phi: np.ndarray, morphology: dict[str, Any]) -> np.ndarray:
    width, height = 760, 480
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    left, right, top, bottom = 78, 28, 36, 58
    plot_w = width - left - right
    plot_h = height - top - bottom
    image[top : top + plot_h, left : left + 1] = 40
    image[top + plot_h - 1 : top + plot_h, left : left + plot_w] = 40
    for tick in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        y = int(round(top + plot_h - 1 - tick * (plot_h - 1)))
        image[y : y + 1, left : left + plot_w] = 230
    axis, fraction = _profile_line(phi)
    complement = 1.0 - fraction
    count = max(len(fraction) - 1, 1)
    points_a = []
    points_b = []
    for index, (value_a, value_b) in enumerate(zip(fraction, complement)):
        x = left + int(round(index / count * (plot_w - 1)))
        y_a = top + plot_h - 1 - int(round(float(np.clip(value_a, 0.0, 1.0)) * (plot_h - 1)))
        y_b = top + plot_h - 1 - int(round(float(np.clip(value_b, 0.0, 1.0)) * (plot_h - 1)))
        points_a.append((x, y_a))
        points_b.append((x, y_b))
    _polyline(image, points_b, (30, 70, 220), radius=2)
    _polyline(image, points_a, (210, 30, 40), radius=2)
    _annotate_profile(image, morphology, axis, left, top, bottom)
    return image


def _polyline(image: np.ndarray, points: list[tuple[int, int]], color: tuple[int, int, int], radius: int) -> None:
    height, width = image.shape[:2]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for step in range(steps + 1):
            x = int(round(x0 + (x1 - x0) * step / steps))
            y = int(round(y0 + (y1 - y0) * step / steps))
            image[
                max(0, y - radius) : min(height, y + radius + 1),
                max(0, x - radius) : min(width, x + radius + 1),
            ] = color


def _cell_image(phi: np.ndarray, morphology: dict[str, Any]) -> np.ndarray:
    from PIL import Image, ImageDraw

    picture = Image.new("RGB", (680, 640), (0, 0, 0))
    draw = ImageDraw.Draw(picture)
    patches = []
    for quad, fraction in _face_patches(phi):
        screen, ahead = _project(quad)
        patches.append((float(np.min(ahead)), [tuple(point) for point in screen], _jet(np.array(fraction)).tolist()))
    for _depth, corners, color in sorted(patches):
        draw.polygon(corners, fill=tuple(int(channel) for channel in color))
    _wireframe(draw, (235, 235, 235))
    image = np.asarray(picture).copy()
    _colorbar(image)
    _annotate_cell(image, morphology)
    return image


def _interface_image(phi: np.ndarray, morphology: dict[str, Any]) -> np.ndarray:
    from PIL import Image, ImageDraw

    picture = Image.new("RGB", (680, 640), (0, 0, 0))
    draw = ImageDraw.Draw(picture)
    light = np.array([0.35, -0.45, 0.82])
    light /= np.linalg.norm(light)
    triangles = _interface_triangles(phi)
    shaded = []
    for triangle in triangles:
        normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
        norm = np.linalg.norm(normal)
        shade = 0.72
        if norm > 1.0e-8:
            shade = 0.55 + 0.45 * abs(float(np.dot(normal / norm, light)))
        screen, ahead = _project(triangle)
        color = tuple(int(channel * shade) for channel in (255, 214, 40))
        shaded.append((float(np.min(ahead)), [tuple(point) for point in screen], color))
    for _depth, corners, color in sorted(shaded):
        draw.polygon(corners, fill=color)
    _wireframe(draw, (210, 210, 210))
    image = np.asarray(picture).copy()
    _annotate_interface(image, morphology, bool(triangles))
    return image


def _face_patches(phi: np.ndarray):
    nz, ny, nx = phi.shape
    counts = (nx, ny, nz)
    for axis, count in enumerate(counts):
        free = [index for index in range(3) if index != axis]
        steps = [max(counts[index] - 1, 1) for index in free]
        capped = [min(step, 32) for step in steps]
        for fixed in (0, count - 1):
            for i0 in range(capped[0]):
                for i1 in range(capped[1]):
                    corners = []
                    for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        span = 1.0 - 2.0 * _INSET
                        point = [0.0, 0.0, 0.0]
                        point[axis] = _INSET if fixed == 0 else 1.0 - _INSET
                        point[free[0]] = _INSET + span * (i0 + du) / capped[0]
                        point[free[1]] = _INSET + span * (i1 + dv) / capped[1]
                        corners.append(point)
                    sample = [0, 0, 0]
                    sample[axis] = fixed
                    sample[free[0]] = min(counts[free[0]] - 1, int(round(i0 / capped[0] * (counts[free[0]] - 1))))
                    sample[free[1]] = min(counts[free[1]] - 1, int(round(i1 / capped[1] * (counts[free[1]] - 1))))
                    yield np.array(corners, dtype=float), float(phi[sample[2], sample[1], sample[0]])


def _interface_triangles(phi: np.ndarray) -> list[np.ndarray]:
    nz, ny, nx = phi.shape
    if min(nx, ny, nz) < 2:
        return []
    triangles = []
    for iz in range(nz - 1):
        for iy in range(ny - 1):
            for ix in range(nx - 1):
                corners = []
                values = []
                for ox, oy, oz in _CORNERS:
                    x, y, z = ix + int(ox), iy + int(oy), iz + int(oz)
                    corners.append(np.array((x / (nx - 1), y / (ny - 1), z / (nz - 1))))
                    values.append(float(phi[z, y, x]))
                crossings = []
                for start, end in _EDGES:
                    left, right = values[start], values[end]
                    if left == right:
                        continue
                    if min(left, right) <= _LEVEL <= max(left, right):
                        weight = 0.0 if left == _LEVEL else (_LEVEL - left) / (right - left)
                        crossings.append((1.0 - weight) * corners[start] + weight * corners[end])
                if len(crossings) < 3 or sum(values) / 8.0 < _LEVEL:
                    continue
                triangles.extend(_fan(np.vstack(crossings)))
    return triangles


def _fan(points: np.ndarray) -> list[np.ndarray]:
    center = points.mean(axis=0)
    offset = points - center
    _, singular, axes = np.linalg.svd(offset, full_matrices=False)
    if singular.size < 2 or float(singular[1]) < 1.0e-8:
        return []
    normal = axes[-1]
    tangent = np.array((1.0, 0.0, 0.0)) if abs(float(normal[0])) < 0.9 else np.array((0.0, 1.0, 0.0))
    axis_u = np.cross(normal, tangent)
    axis_u /= np.linalg.norm(axis_u)
    axis_v = np.cross(normal, axis_u)
    offset = points - center
    angle = np.arctan2(offset @ axis_v, offset @ axis_u)
    ordered = points[np.argsort(angle)]
    return [np.vstack((ordered[0], ordered[index], ordered[index + 1])) for index in range(1, len(ordered) - 1)]


def _sample(phi: np.ndarray, position: np.ndarray) -> np.ndarray:
    nz, ny, nx = phi.shape
    x = np.clip(np.rint(position[..., 0] * (nx - 1)).astype(int), 0, nx - 1)
    y = np.clip(np.rint(position[..., 1] * (ny - 1)).astype(int), 0, ny - 1)
    z = np.clip(np.rint(position[..., 2] * (nz - 1)).astype(int), 0, nz - 1)
    return phi[z, y, x]


def _paint_quad(image: np.ndarray, depth: np.ndarray, cell: np.ndarray, color_of) -> None:
    _paint_surface(image, depth, cell[[0, 1, 2]], color_of)
    _paint_surface(image, depth, cell[[0, 2, 3]], color_of)


def _paint_quad_triangle(image: np.ndarray, depth: np.ndarray, cell: np.ndarray, color: tuple[int, int, int]) -> None:
    _paint_surface(image, depth, cell, lambda _position: np.array(color, dtype=np.uint8))


def _paint_surface(image: np.ndarray, depth: np.ndarray, cell: np.ndarray, color_of) -> None:
    screen, eye_depth = _project(cell)
    x0, y0 = screen[0]
    x1, y1 = screen[1]
    x2, y2 = screen[2]
    denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(denominator) < 1.0e-6:
        return
    height, width = image.shape[:2]
    min_x = max(int(np.floor(min(x0, x1, x2))), 0)
    max_x = min(int(np.ceil(max(x0, x1, x2))) + 1, width)
    min_y = max(int(np.floor(min(y0, y1, y2))), 0)
    max_y = min(int(np.ceil(max(y0, y1, y2))) + 1, height)
    if min_x >= max_x or min_y >= max_y:
        return
    xs = np.arange(min_x, max_x)
    ys = np.arange(min_y, max_y)
    grid_x, grid_y = np.meshgrid(xs, ys)
    weight_0 = ((y1 - y2) * (grid_x - x2) + (x2 - x1) * (grid_y - y2)) / denominator
    weight_1 = ((y2 - y0) * (grid_x - x2) + (x0 - x2) * (grid_y - y2)) / denominator
    weight_2 = 1.0 - weight_0 - weight_1
    covered = (weight_0 >= -0.002) & (weight_1 >= -0.002) & (weight_2 >= -0.002)
    if not np.any(covered):
        return
    pixel_depth = weight_0 * eye_depth[0] + weight_1 * eye_depth[1] + weight_2 * eye_depth[2]
    nearer = covered & (pixel_depth > depth[min_y:max_y, min_x:max_x])
    if not np.any(nearer):
        return
    position = (
        weight_0[..., None] * cell[0]
        + weight_1[..., None] * cell[1]
        + weight_2[..., None] * cell[2]
    )
    color = color_of(position)
    if color.shape == (3,):
        color = np.broadcast_to(color, position.shape)
    view = image[min_y:max_y, min_x:max_x]
    view[nearer] = color[nearer]
    depth[min_y:max_y, min_x:max_x][nearer] = pixel_depth[nearer]


def _wireframe(draw, color: tuple[int, int, int]) -> None:
    corners = np.array(
        [
            (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
            (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
        ],
        dtype=float,
    )
    edges = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7))
    screen, _ahead = _project(corners)
    for start, end in edges:
        draw.line([tuple(screen[start]), tuple(screen[end])], fill=color, width=2)


def _project(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    eye = np.array((0.78, -1.85, 1.22))
    target = np.array((0.5, 0.5, 0.42))
    forward = target - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, np.array((0.0, 0.0, 1.0)))
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    relative = np.asarray(points, dtype=float) - eye
    horizontal = relative @ right
    vertical = relative @ up
    ahead = relative @ forward
    scale = 2.45 / np.maximum(ahead, 1.0e-4)
    screen_x = 400.0 + horizontal * scale * 250.0
    screen_y = 325.0 - vertical * scale * 250.0
    return np.column_stack((screen_x, screen_y)), ahead


def _colorbar(image: np.ndarray) -> None:
    height = image.shape[0]
    top, bottom = 70, height - 48
    samples = np.linspace(1.0, 0.0, bottom - top)
    image[top:bottom, 24:48] = _jet(samples)[:, None, :]


def _annotate_profile(
    image: np.ndarray,
    morphology: dict[str, Any],
    axis: str,
    left: int,
    top: int,
    bottom: int,
) -> None:
    source = str(morphology.get("density_source") or "segment fraction")
    name = str(morphology.get("morphology") or "morphology")
    _text(
        image,
        [
            (left + 16, top + 12, (210, 30, 40), "A-block fraction"),
            (left + 16, top + 32, (30, 70, 220), "B-block fraction, one minus A"),
            (left, image.shape[0] - bottom + 16, (40, 40, 40), f"Position along {axis}"),
            (left, 8, (40, 40, 40), f"{name} ({source}). Not a SUSHI result."),
        ],
    )
    _vertical_text(image, "Volume fraction", 8, top + 70)


def _annotate_cell(image: np.ndarray, morphology: dict[str, Any]) -> None:
    source = str(morphology.get("density_source") or "segment fraction")
    _text(
        image,
        [
            (60, 16, (240, 240, 240), "Red is A-rich. Blue is B-rich. Green is the interface."),
            (60, image.shape[0] - 28, (220, 220, 220), f"Segment fraction on the cell ({source})."),
        ],
    )


def _annotate_interface(image: np.ndarray, morphology: dict[str, Any], drawn: bool) -> None:
    source = str(morphology.get("density_source") or "segment fraction")
    message = "Surface where the A-block fraction crosses one half."
    if not drawn:
        message = "This grid does not cross one half, so there is no interface surface."
    _text(
        image,
        [
            (36, 16, (240, 240, 240), message),
            (36, image.shape[0] - 28, (220, 220, 220), f"Interface of this file ({source}). Not a SUSHI result."),
        ],
    )


_SPRITES: dict[tuple, object] = {}


def _sprite(text: str, color: tuple[int, int, int], turn: bool = False):
    key = (text, color, turn)
    cached = _SPRITES.get(key)
    if cached is not None:
        return cached
    from PIL import Image, ImageDraw

    probe = Image.new("RGBA", (max(18 * len(text), 8), 24), (0, 0, 0, 0))
    ImageDraw.Draw(probe).text((0, 0), text, fill=color + (255,), font=_font(16))
    cropped = probe.crop(probe.getbbox() or (0, 0, 1, 1))
    if turn:
        cropped = cropped.rotate(90, expand=True)
    _SPRITES[key] = cropped
    return cropped


def _vertical_text(image: np.ndarray, text: str, x: int, y: int) -> None:
    try:
        from PIL import Image
    except ImportError:
        return
    picture = Image.fromarray(image, mode="RGB")
    picture.paste(_sprite(text, (40, 40, 40), turn=True), (x, y), _sprite(text, (40, 40, 40), turn=True))
    image[...] = np.asarray(picture)


_FONT = None


def _font(size: int):
    global _FONT
    if _FONT is not None:
        return _FONT
    from PIL import ImageFont

    windir = Path(__import__("os").environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf"
    _FONT = ImageFont.truetype(str(windir), size) if windir.is_file() else ImageFont.load_default()
    return _FONT


def _text(image: np.ndarray, rows: list[tuple[int, int, tuple[int, int, int], str]]) -> None:
    try:
        from PIL import Image
    except ImportError:
        return
    picture = Image.fromarray(image, mode="RGB")
    for x, y, color, text in rows:
        sprite = _sprite(text, color)
        picture.paste(sprite, (x, y), sprite)
    image[...] = np.asarray(picture)


def _save(path: Path, image: np.ndarray) -> None:
    try:
        from PIL import Image
    except ImportError:
        _save_png(path, image)
        return
    Image.fromarray(image, mode="RGB").save(path)


def _save_png(path: Path, image: np.ndarray) -> None:
    import struct
    import zlib

    height, width = image.shape[:2]
    raw = b"".join(b"\x00" + image[row].tobytes() for row in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )

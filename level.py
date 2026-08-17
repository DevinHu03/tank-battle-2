"""Data-only campaign definitions for Steel Frontline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pygame

WIDTH, HEIGHT, TILE_SIZE = 960, 720, 24
WALL_SIZE = TILE_SIZE


class TerrainKind(Enum):
    BRICK = "brick"
    STEEL = "steel"
    WATER = "water"
    GRASS = "grass"


class MissionKind(Enum):
    ELIMINATION = "elimination"
    DEFEND = "defend"
    SURVIVAL = "survival"
    ESCORT = "escort"
    BOSS = "boss"


@dataclass
class TerrainTile:
    rect: pygame.Rect
    kind: TerrainKind
    health: int | None = None


# Compatibility name used by the original tests and presentation.
Wall = TerrainTile


@dataclass(frozen=True)
class EnemySpawn:
    kind: str
    position: tuple[int, int]
    delay: float = 0


@dataclass(frozen=True)
class LevelDefinition:
    number: int
    title: str
    mission: MissionKind
    briefing: str
    objective: str
    failure: str
    player_spawn: tuple[int, int]
    terrain: tuple[TerrainTile, ...]
    enemy_spawns: tuple[EnemySpawn, ...]
    target_spawn: tuple[int, int] | None = None
    target_health: int = 0
    duration: float = 0
    escort_route: tuple[tuple[int, int], ...] = ()
    grade_thresholds: tuple[int, int, int] = (4000, 3000, 2000)


def _tile(x: int, y: int, kind: TerrainKind) -> TerrainTile:
    return TerrainTile(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE), kind, 1 if kind == TerrainKind.BRICK else None)


def _tiles(kind: TerrainKind, coordinates: list[tuple[int, int]]) -> tuple[TerrainTile, ...]:
    return tuple(_tile(x, y, kind) for x, y in coordinates)


def _arena(bricks: list[tuple[int, int]], steel: list[tuple[int, int]] = [], water: list[tuple[int, int]] = [], grass: list[tuple[int, int]] = []) -> tuple[TerrainTile, ...]:
    return _tiles(TerrainKind.BRICK, bricks) + _tiles(TerrainKind.STEEL, steel) + _tiles(TerrainKind.WATER, water) + _tiles(TerrainKind.GRASS, grass)


def _segments(kind: TerrainKind, segments: tuple[tuple[int, int, int, bool], ...]) -> list[tuple[int, int]]:
    """Convert hand-authored maze segments into tile coordinates."""
    # Thicken structural walls to make the maze read as connected corridors;
    # decorative water/grass stays at its authored footprint.
    padding = 2 if kind in (TerrainKind.BRICK, TerrainKind.STEEL) else 0
    cells = []
    for x, y, length, vertical in segments:
        for offset in range(-padding, length + padding):
            cell = (x + offset if not vertical else x, y + offset if vertical else y)
            if 1 <= cell[0] < 39 and 1 <= cell[1] < 29: cells.append(cell)
    return cells


def _maze(brick: tuple[tuple[int, int, int, bool], ...], steel: tuple[tuple[int, int, int, bool], ...], water: tuple[tuple[int, int, int, bool], ...] = (), grass: tuple[tuple[int, int, int, bool], ...] = ()) -> tuple[TerrainTile, ...]:
    return _arena(_segments(TerrainKind.BRICK, brick), _segments(TerrainKind.STEEL, steel), _segments(TerrainKind.WATER, water), _segments(TerrainKind.GRASS, grass))


def build_campaign_levels() -> tuple[LevelDefinition, ...]:
    """Five deliberately small but distinct hand-authored arenas."""
    return (
        LevelDefinition(1, "边境突破", MissionKind.ELIMINATION, "前线缺口已经打开。熟悉机动与炮击。", "歼灭全部敌军", "玩家被摧毁", (96, 624),
            _maze(((5, 5, 13, False), (5, 5, 8, True), (11, 9, 12, False), (22, 9, 9, True), (16, 15, 14, False), (10, 15, 8, True), (5, 22, 14, False), (18, 22, 7, True), (27, 4, 10, False), (31, 7, 10, True), (27, 19, 9, False), (8, 12, 5, True), (24, 4, 6, False), (24, 20, 7, True), (12, 25, 8, False)), ((20, 4, 5, True), (25, 11, 7, False), (4, 17, 7, False), (34, 14, 9, True), (14, 6, 4, False), (29, 23, 5, True)), grass=((6, 12, 4, False), (34, 24, 3, False))),
            (EnemySpawn("scout", (80, 120)), EnemySpawn("scout", (850, 300)), EnemySpawn("armor", (780, 520)), EnemySpawn("scout", (450, 300))), grade_thresholds=(1500, 1100, 700)),
        LevelDefinition(2, "最后防线", MissionKind.DEFEND, "敌军正向指挥基地推进，守住防线。", "守卫基地并消灭三批敌人", "玩家或基地耐久归零", (100, 620),
            _maze(((4, 4, 11, False), (4, 4, 9, True), (9, 9, 12, False), (20, 6, 11, True), (14, 14, 12, False), (7, 14, 9, True), (4, 23, 15, False), (18, 19, 9, True), (27, 5, 10, False), (31, 9, 10, True), (25, 23, 11, False), (8, 5, 5, True), (25, 5, 7, False), (12, 20, 8, True), (29, 20, 6, False)), ((15, 5, 5, True), (23, 4, 7, False), (23, 16, 7, False), (34, 17, 7, True), (6, 11, 4, False), (29, 12, 5, True)), grass=((5, 18, 3, False), (29, 4, 3, False))),
            (EnemySpawn("scout", (850, 350)), EnemySpawn("sniper", (750, 180), 5), EnemySpawn("rapid", (850, 450), 10), EnemySpawn("armor", (700, 100), 15), EnemySpawn("rapid", (800, 300), 20), EnemySpawn("sniper", (700, 560), 25)), (120, 610), 8, grade_thresholds=(2600, 1900, 1200)),
        LevelDefinition(3, "钢铁风暴", MissionKind.SURVIVAL, "暴雨将至，坚持到增援抵达。", "坚持 180 秒", "玩家被摧毁", (80, 620),
            _maze(((5, 5, 9, False), (5, 5, 11, True), (13, 9, 9, True), (13, 17, 12, False), (21, 4, 11, False), (27, 7, 11, True), (30, 16, 7, False), (32, 16, 10, True), (6, 23, 13, False), (19, 20, 6, True), (10, 13, 6, False), (8, 4, 6, False), (22, 17, 8, True), (26, 21, 8, False), (14, 25, 7, True)), ((17, 4, 6, True), (22, 12, 7, False), (4, 18, 6, False), (28, 25, 7, False), (10, 7, 4, False), (34, 11, 5, True)), ((8, 15, 5, False), (24, 23, 5, False)), ((6, 10, 3, False), (34, 7, 3, False))),
            (), duration=180, grade_thresholds=(5000, 3800, 2600)),
        LevelDefinition(4, "废墟突袭", MissionKind.ELIMINATION, "装甲补给已被截断，清除废墟中的指挥部。", "歼灭全部敌军并突破废墟", "玩家被摧毁", (80, 660),
            _maze(((5, 4, 12, False), (5, 4, 8, True), (11, 10, 10, False), (20, 6, 10, True), (14, 15, 13, False), (9, 15, 9, True), (5, 24, 12, False), (18, 20, 7, True), (27, 4, 10, False), (30, 8, 12, True), (26, 24, 10, False), (8, 7, 6, True), (23, 4, 7, False), (23, 18, 8, True), (12, 23, 8, False)), ((17, 4, 5, True), (23, 11, 7, False), (4, 18, 6, False), (34, 16, 7, True), (14, 8, 4, False), (29, 22, 5, True)), ((4, 12, 6, False), (27, 17, 5, False)), ((12, 5, 3, False), (6, 26, 3, False))),
            (EnemySpawn("commander", (720, 150)), EnemySpawn("rapid", (500, 260), 4), EnemySpawn("breaker", (760, 460), 8), EnemySpawn("sniper", (400, 100), 12), EnemySpawn("armor", (800, 600), 16)), grade_thresholds=(3200, 2400, 1600)),
        LevelDefinition(5, "核心要塞", MissionKind.BOSS, "摧毁要塞核心，结束这场战役。", "突破守军并击败 Boss", "玩家被摧毁", (100, 620),
            _maze(((4, 4, 13, False), (4, 4, 10, True), (11, 9, 10, False), (16, 9, 8, True), (20, 15, 13, False), (10, 15, 8, True), (4, 23, 14, False), (18, 20, 7, True), (27, 4, 10, False), (31, 8, 11, True), (26, 24, 10, False), (8, 6, 7, True), (23, 4, 7, False), (23, 18, 8, True), (12, 24, 8, False)), ((20, 4, 5, True), (23, 11, 7, False), (5, 18, 6, False), (34, 16, 7, True), (28, 21, 5, False), (14, 7, 5, True), (29, 5, 5, False)), ((5, 13, 5, False),), ((6, 6, 3, False), (34, 25, 3, False))),
            (EnemySpawn("armor", (700, 150)), EnemySpawn("sniper", (780, 500)), EnemySpawn("rapid", (500, 160), 3), EnemySpawn("boss", (800, 220), 8)), grade_thresholds=(6000, 4500, 3000)),
    )


LEVELS = build_campaign_levels()
PLAYER_SPAWN = LEVELS[0].player_spawn
ENEMY_SPAWNS = ((100, 100), (860, 100), (860, 620), (150, 360), (810, 360))


def build_hty_walls() -> list[Wall]:
    """Legacy centred obstacle layout retained for prototype compatibility."""
    mask = ("#.#.#####.#...#", "#.#...#...#...#", "###...#....#.#.", "#.#...#.....#..", "#.#...#.....#..")
    start_x = (WIDTH - len(mask[0]) * TILE_SIZE) // 2
    start_y = (HEIGHT - len(mask) * TILE_SIZE) // 2
    return [TerrainTile(pygame.Rect(start_x + x * TILE_SIZE, start_y + y * TILE_SIZE, TILE_SIZE, TILE_SIZE), TerrainKind.BRICK)
            for y, row in enumerate(mask) for x, cell in enumerate(row) if cell == "#"]

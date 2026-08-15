"""固定关卡布局：中央砖墙以 HTY 掩码排列。"""

from dataclasses import dataclass

import pygame

WIDTH, HEIGHT = 960, 720
WALL_SIZE = 24
HTY_MASK = (
    "#.#.#####.#...#",
    "#.#...#...#...#",
    "###...#....#.#.",
    "#.#...#.....#..",
    "#.#...#.....#..",
)


@dataclass
class Wall:
    rect: pygame.Rect


def build_hty_walls() -> list[Wall]:
    """返回位于画面中央、不可摧毁的 HTY 红砖墙。"""
    start_x = (WIDTH - len(HTY_MASK[0]) * WALL_SIZE) // 2
    start_y = (HEIGHT - len(HTY_MASK) * WALL_SIZE) // 2
    return [
        Wall(pygame.Rect(start_x + x * WALL_SIZE, start_y + y * WALL_SIZE, WALL_SIZE, WALL_SIZE))
        for y, row in enumerate(HTY_MASK)
        for x, cell in enumerate(row)
        if cell == "#"
    ]


PLAYER_SPAWN = (100, HEIGHT - 100)
ENEMY_SPAWNS = ((100, 100), (860, 100), (860, 620), (150, 360), (810, 360))

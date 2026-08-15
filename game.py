"""Headless-testable rules for the three-wave tank campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import random

import pygame

from level import ENEMY_SPAWNS, HEIGHT, PLAYER_SPAWN, WIDTH, Wall, build_hty_walls


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


class GameState(Enum):
    START = "start"
    PLAYING = "playing"
    VICTORY = "victory"
    DEFEAT = "defeat"


class EnemyKind(Enum):
    SCOUT = "scout"
    ARMOR = "armor"
    SNIPER = "sniper"
    BOSS = "boss"


class PowerupKind(Enum):
    HEALTH = "health"
    RAPID = "rapid"
    SHIELD = "shield"


STATS = {
    EnemyKind.SCOUT: (1, 125, 0.55, 100), EnemyKind.ARMOR: (3, 58, 1.05, 200),
    EnemyKind.SNIPER: (1, 72, 1.25, 250), EnemyKind.BOSS: (14, 48, 1.4, 1000),
}
TANK_SIZES = {EnemyKind.SCOUT: 48, EnemyKind.ARMOR: 52, EnemyKind.SNIPER: 50, EnemyKind.BOSS: 70}
WAVES = ((EnemyKind.SCOUT,) * 3, (EnemyKind.SCOUT,) * 2 + (EnemyKind.ARMOR,) * 2 + (EnemyKind.SNIPER,), (EnemyKind.SCOUT, EnemyKind.ARMOR, EnemyKind.SNIPER, EnemyKind.BOSS))


@dataclass
class Tank:
    rect: pygame.Rect
    team: str
    direction: Direction = Direction.UP
    health: int = 1
    speed: float = 170
    cooldown: float = 0
    alive: bool = True
    flash: float = 0
    turn_timer: float = 0
    kind: EnemyKind | None = None
    fire_delay: float = 0.45
    rapid_timer: float = 0
    shield_timer: float = 0
    special_timer: float = 0
    warning_timer: float = 0


@dataclass
class Bullet:
    rect: pygame.Rect
    direction: Direction
    team: str
    speed: float = 430
    alive: bool = True
    velocity: tuple[float, float] | None = None


@dataclass
class Powerup:
    rect: pygame.Rect
    kind: PowerupKind
    ttl: float = 10


@dataclass
class Explosion:
    pos: tuple[int, int]
    ttl: float = 0.35


@dataclass
class GameWorld:
    state: GameState = GameState.PLAYING
    walls: list[Wall] = field(default_factory=build_hty_walls)
    bullets: list[Bullet] = field(default_factory=list)
    explosions: list[Explosion] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.random = random.Random()
        self.reset()

    def reset(self) -> None:
        self.state, self.wave, self.elapsed, self.score = GameState.PLAYING, 1, 0.0, 0
        self.transition_timer, self.wave_banner = 0.0, 1.8
        self.walls, self.bullets, self.explosions, self.powerups, self.events = build_hty_walls(), [], [], [], ["wave"]
        self.player = Tank(pygame.Rect(0, 0, 52, 52), "player", Direction.UP, 3, 125)
        self.player.rect.center = PLAYER_SPAWN
        self.spawn_wave(1, announce=False)

    def spawn_wave(self, number: int, announce: bool = True) -> None:
        self.wave = number
        self.enemies = []
        for index, kind in enumerate(WAVES[number - 1]):
            health, speed, delay, _ = STATS[kind]
            size = TANK_SIZES[kind]
            tank = Tank(pygame.Rect(0, 0, size, size), "enemy", Direction.DOWN, health, speed, kind=kind, fire_delay=delay)
            tank.rect.center = ENEMY_SPAWNS[index]
            tank.turn_timer = 0.5 + index * 0.2
            self.enemies.append(tank)
        self.wave_banner = 1.8
        if announce:
            self.events.append("wave")

    def active_tanks(self) -> list[Tank]:
        return [self.player, *self.enemies]

    def move_tank(self, tank: Tank, dx: float, dy: float) -> bool:
        moved = False
        for amount, axis in ((dx, "x"), (dy, "y")):
            if not amount:
                continue
            old = tank.rect.copy()
            setattr(tank.rect, axis, round(getattr(tank.rect, axis) + amount))
            invalid = not pygame.Rect(0, 0, WIDTH, HEIGHT).contains(tank.rect)
            invalid |= any(tank.rect.colliderect(wall.rect) for wall in self.walls)
            invalid |= any(other is not tank and other.alive and tank.rect.colliderect(other.rect) for other in self.active_tanks())
            if invalid:
                tank.rect = old
            else:
                moved = True
        return moved

    def try_fire(self, tank: Tank) -> bool:
        if not tank.alive or tank.cooldown > 0 or self.state != GameState.PLAYING:
            return False
        dx, dy = tank.direction.value
        bullet = Bullet(pygame.Rect(0, 0, 10, 10), tank.direction, tank.team)
        bullet.rect.center = (tank.rect.centerx + dx * (tank.rect.width // 2 + 7), tank.rect.centery + dy * (tank.rect.height // 2 + 7))
        self.bullets.append(bullet)
        tank.cooldown = 0.18 if tank.team == "player" and tank.rapid_timer > 0 else tank.fire_delay
        self.events.append("fire")
        return True

    def damage(self, tank: Tank) -> None:
        if tank is self.player and tank.shield_timer > 0:
            self.events.append("hit")
            return
        tank.health -= 1
        tank.flash = 0.18
        self.events.append("hit")
        if tank.health <= 0:
            tank.alive = False
            self.explosions.append(Explosion(tank.rect.center))
            self.events.append("explode")
            if tank.team == "enemy":
                self.score += STATS[tank.kind][3]
                if self.random.random() < 0.35:
                    kind = self.random.choice(list(PowerupKind))
                    rect = pygame.Rect(0, 0, 20, 20); rect.center = tank.rect.center
                    self.powerups.append(Powerup(rect, kind))

    def has_clear_shot(self, tank: Tank) -> bool:
        px, py = self.player.rect.center; tx, ty = tank.rect.center
        if abs(px - tx) < 15:
            direction, distance = (Direction.DOWN if py > ty else Direction.UP), abs(py - ty)
        elif abs(py - ty) < 15:
            direction, distance = (Direction.RIGHT if px > tx else Direction.LEFT), abs(px - tx)
        else:
            return False
        dx, dy = direction.value; probe = pygame.Rect(0, 0, 4, 4)
        for step in range(20, distance, 8):
            probe.center = (tx + dx * step, ty + dy * step)
            if any(probe.colliderect(wall.rect) for wall in self.walls):
                return False
        tank.direction = direction
        return True

    def _boss_salvo(self, boss: Tank) -> None:
        px, py = self.player.rect.center; bx, by = boss.rect.center
        base = math.atan2(py - by, px - bx)
        for offset in (-0.32, 0, 0.32):
            vx, vy = math.cos(base + offset), math.sin(base + offset)
            bullet = Bullet(pygame.Rect(0, 0, 12, 12), boss.direction, "enemy", 330, velocity=(vx, vy))
            bullet.rect.center = boss.rect.center; self.bullets.append(bullet)
        self.events.append("fire")

    def _enemy_ai(self, enemy: Tank, dt: float) -> None:
        enemy.turn_timer -= dt
        if enemy.kind == EnemyKind.BOSS:
            enemy.special_timer -= dt
            if enemy.warning_timer > 0:
                enemy.warning_timer -= dt
                if enemy.warning_timer <= 0:
                    self._boss_salvo(enemy); enemy.special_timer = 2.5
            elif enemy.special_timer <= 0:
                enemy.warning_timer = 0.55; self.events.append("warning")
        elif self.has_clear_shot(enemy) and enemy.cooldown <= 0:
            chance = 0.05 if enemy.kind == EnemyKind.SNIPER else 0.025
            if self.random.random() < chance:
                self.try_fire(enemy)
        if enemy.turn_timer <= 0:
            enemy.direction = self.random.choice(list(Direction)); enemy.turn_timer = self.random.uniform(0.7, 1.8)
        dx, dy = enemy.direction.value
        if not self.move_tank(enemy, dx * enemy.speed * dt, dy * enemy.speed * dt):
            enemy.direction = self.random.choice(list(Direction)); enemy.turn_timer = 0.4

    def _collect_powerups(self, dt: float) -> None:
        kept = []
        for powerup in self.powerups:
            powerup.ttl -= dt
            if self.player.rect.colliderect(powerup.rect):
                if powerup.kind == PowerupKind.HEALTH:
                    self.player.health = min(3, self.player.health + 1)
                elif powerup.kind == PowerupKind.RAPID:
                    self.player.rapid_timer = 8
                else:
                    self.player.shield_timer = 8
                self.events.append("pickup")
            elif powerup.ttl > 0:
                kept.append(powerup)
        self.powerups = kept

    def _advance_bullets(self, dt: float) -> None:
        for bullet in self.bullets:
            vx, vy = bullet.velocity or bullet.direction.value
            for _ in range(max(1, round(bullet.speed * dt / 5))):
                bullet.rect.x += round(vx * 5); bullet.rect.y += round(vy * 5)
                if not pygame.Rect(0, 0, WIDTH, HEIGHT).contains(bullet.rect) or any(bullet.rect.colliderect(w.rect) for w in self.walls):
                    bullet.alive = False; break
                targets = self.enemies if bullet.team == "player" else [self.player]
                target = next((item for item in targets if item.alive and bullet.rect.colliderect(item.rect)), None)
                if target:
                    bullet.alive = False; self.damage(target); break
        self.bullets = [bullet for bullet in self.bullets if bullet.alive]

    def update(self, dt: float) -> None:
        if self.state != GameState.PLAYING:
            return
        self.elapsed += dt; self.wave_banner = max(0, self.wave_banner - dt)
        for tank in self.active_tanks():
            tank.cooldown = max(0, tank.cooldown - dt); tank.flash = max(0, tank.flash - dt)
        self.player.rapid_timer = max(0, self.player.rapid_timer - dt); self.player.shield_timer = max(0, self.player.shield_timer - dt)
        self._collect_powerups(dt)
        if self.transition_timer > 0:
            self.transition_timer -= dt
            if self.transition_timer <= 0:
                self.spawn_wave(self.wave + 1)
            return
        for enemy in self.enemies:
            if enemy.alive:
                self._enemy_ai(enemy, dt)
        self._advance_bullets(dt)
        for boom in self.explosions: boom.ttl -= dt
        self.explosions = [boom for boom in self.explosions if boom.ttl > 0]
        if self.player.health <= 0:
            self.player.alive = False; self.state = GameState.DEFEAT; self.events.append("defeat")
        elif not any(enemy.alive for enemy in self.enemies):
            if self.wave == 3:
                self.state = GameState.VICTORY; self.events.append("victory")
            else:
                self.transition_timer = 1.8

    def final_score(self) -> int:
        return self.score + self.player.health * 300 + max(0, 500 - int(self.elapsed))

    def grade(self) -> str:
        score = self.final_score()
        return "S" if score >= 3400 else "A" if score >= 3000 else "B"

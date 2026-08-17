"""Headless-testable combat and mission rules for 《钢铁防线》."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import random

import pygame

from level import ENEMY_SPAWNS, HEIGHT, LEVELS, PLAYER_SPAWN, TILE_SIZE, WIDTH, EnemySpawn, LevelDefinition, MissionKind, TerrainKind, TerrainTile, build_hty_walls


class Direction(Enum):
    UP = (0, -1); DOWN = (0, 1); LEFT = (-1, 0); RIGHT = (1, 0)


class GameState(Enum):
    TITLE = "title"; NEW_GAME_CONFIRM = "new_game_confirm"; BRIEFING = "briefing"; PLAYING = "playing"; PAUSED = "paused"
    RESULT = "result"; UPGRADES = "upgrades"; DEFEAT = "defeat"; VICTORY = "victory"; CREDITS = "credits"; SETTINGS = "settings"
    START = "title"  # old public name


class EnemyKind(Enum):
    SCOUT = "scout"; ARMOR = "armor"; SNIPER = "sniper"; RAPID = "rapid"; BREAKER = "breaker"; COMMANDER = "commander"; BOSS = "boss"


class PowerupKind(Enum):
    HEALTH = "health"; SHIELD = "shield"; RAPID = "rapid"; SHOCK = "shock"


class UpgradeTrack(Enum):
    FIREPOWER = "firepower"; DEFENSE = "defense"; MOBILITY = "mobility"


@dataclass(frozen=True)
class UpgradeDefinition:
    key: str; track: UpgradeTrack; name: str; max_level: int; description: str


UPGRADES = (
    UpgradeDefinition("reload", UpgradeTrack.FIREPOWER, "高速装填", 3, "射击间隔 -15%"),
    UpgradeDefinition("damage", UpgradeTrack.FIREPOWER, "穿甲弹", 2, "炮弹伤害 +1"),
    UpgradeDefinition("bullet_speed", UpgradeTrack.FIREPOWER, "高速弹芯", 2, "炮弹速度 +15%"),
    UpgradeDefinition("armor", UpgradeTrack.DEFENSE, "强化装甲", 3, "生命上限 +1，恢复 1"),
    UpgradeDefinition("invulnerability", UpgradeTrack.DEFENSE, "缓冲装甲", 2, "受击无敌 +0.25 秒"),
    UpgradeDefinition("start_shield", UpgradeTrack.DEFENSE, "应急护盾", 1, "每关开始护盾 4 秒"),
    UpgradeDefinition("engine", UpgradeTrack.MOBILITY, "强力引擎", 3, "移速 +12%"),
    UpgradeDefinition("hitbox", UpgradeTrack.MOBILITY, "紧凑车体", 2, "受击区域 -10%"),
    UpgradeDefinition("magnet", UpgradeTrack.MOBILITY, "回收装置", 2, "吸附道具范围增加"),
)
UPGRADE_BY_KEY = {item.key: item for item in UPGRADES}

STATS = {
    EnemyKind.SCOUT: (1, 70, .7, 100), EnemyKind.ARMOR: (4, 32, 1.1, 220), EnemyKind.SNIPER: (1, 40, 1.35, 250),
    EnemyKind.RAPID: (2, 52, .35, 190), EnemyKind.BREAKER: (3, 31, 1.0, 260), EnemyKind.COMMANDER: (3, 39, .8, 320), EnemyKind.BOSS: (30, 26, 1.2, 1500),
}
TANK_SIZES = {kind: (70 if kind == EnemyKind.BOSS else 52 if kind == EnemyKind.ARMOR else 50) for kind in EnemyKind}
WAVES = ((EnemyKind.SCOUT,) * 3, (EnemyKind.SCOUT,) * 2 + (EnemyKind.ARMOR,) * 2 + (EnemyKind.SNIPER,), (EnemyKind.SCOUT, EnemyKind.ARMOR, EnemyKind.SNIPER, EnemyKind.BOSS))


@dataclass
class CampaignState:
    current_level: int = 1; upgrades: dict[str, int] = field(default_factory=dict); score: int = 0; elapsed: float = 0


@dataclass
class MissionState:
    kind: MissionKind; target_health: int = 0; max_target_health: int = 0; remaining: float = 0; completed: bool = False; failed: bool = False


@dataclass
class Tank:
    rect: pygame.Rect; team: str; direction: Direction = Direction.UP; health: int = 1; speed: float = 170; cooldown: float = 0; alive: bool = True
    flash: float = 0; turn_timer: float = 0; kind: EnemyKind | None = None; fire_delay: float = .45; rapid_timer: float = 0; shield_timer: float = 0
    special_timer: float = 0; warning_timer: float = 0; invulnerable: float = 0; max_health: int = 1; phase: int = 1


@dataclass
class Bullet:
    rect: pygame.Rect; direction: Direction; team: str; speed: float = 430; alive: bool = True; velocity: tuple[float, float] | None = None; damage: int = 1; breaks_bricks: bool = True


@dataclass
class Powerup:
    rect: pygame.Rect; kind: PowerupKind; ttl: float = 10


@dataclass
class Explosion:
    pos: tuple[int, int]; ttl: float = .35


@dataclass
class GameWorld:
    level: LevelDefinition | None = None
    campaign: CampaignState = field(default_factory=CampaignState)
    state: GameState = GameState.PLAYING
    terrain: list[TerrainTile] = field(default_factory=list)
    bullets: list[Bullet] = field(default_factory=list); explosions: list[Explosion] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.random = random.Random(); self.legacy = self.level is None
        self.level = self.level or LEVELS[0]
        self.reset()

    @property
    def walls(self) -> list[TerrainTile]:  # legacy view
        return [tile for tile in self.terrain if tile.kind in (TerrainKind.BRICK, TerrainKind.STEEL)]

    @walls.setter
    def walls(self, value: list[TerrainTile]) -> None:
        self.terrain = list(value)

    def reset(self) -> None:
        self.state = GameState.PLAYING; self.elapsed = 0.; self.score = 0; self.events = []; self.bullets = []; self.explosions = []; self.powerups = []; self.pending_spawns = []
        self.terrain = list(build_hty_walls() if self.legacy else self.level.terrain)
        self.wave = 1; self.transition_timer = 0.; self.wave_banner = 1.8
        self.mission = MissionState(self.level.mission, self.level.target_health, self.level.target_health, self.level.duration)
        max_health = 3 + self.campaign.upgrades.get("armor", 0)
        self.player = Tank(pygame.Rect(0, 0, 52, 52), "player", health=max_health, max_health=max_health, speed=125 * (1.12 ** self.campaign.upgrades.get("engine", 0)))
        self.player.rect.center = self.level.player_spawn if not self.legacy else PLAYER_SPAWN
        self.player.shield_timer = 4 if self.campaign.upgrades.get("start_shield") else 0
        self.target = None
        if self.level.mission in (MissionKind.DEFEND, MissionKind.ESCORT):
            self.target = Tank(pygame.Rect(0, 0, 50, 50), "target", health=self.level.target_health, max_health=self.level.target_health, speed=55)
            self.target.rect.center = self.level.target_spawn or self.level.player_spawn
            self.route_index = 1
        if self.legacy: self.spawn_wave(1, False)
        else: self._queue_level_spawns()

    def _queue_level_spawns(self) -> None:
        self.enemies = []
        self.pending_spawns = list(self.level.enemy_spawns)
        self._spawn_due()

    def _spawn_due(self) -> None:
        for spawn in list(self.pending_spawns):
            if spawn.delay <= self.elapsed:
                self.spawn_enemy(EnemyKind(spawn.kind), spawn.position); self.pending_spawns.remove(spawn)

    def spawn_enemy(self, kind: EnemyKind, position: tuple[int, int]) -> Tank:
        hp, speed, delay, _ = STATS[kind]; size = TANK_SIZES[kind]
        if self.legacy and kind == EnemyKind.BOSS: hp = 14
        tank = Tank(pygame.Rect(0, 0, size, size), "enemy", Direction.DOWN, hp, speed, kind=kind, fire_delay=delay, max_health=hp)
        tank.rect.center = position
        # Definitions describe the intended lane; a dense maze may require a
        # one-tile nudge to guarantee no tank is born inside a wall.
        if self._solid(tank.rect):
            origin = pygame.Vector2(position)
            for radius in range(1, 14):
                candidates = ((radius, 0), (-radius, 0), (0, radius), (0, -radius), (radius, radius), (-radius, radius), (radius, -radius), (-radius, -radius))
                for dx, dy in candidates:
                    tank.rect.center = origin + pygame.Vector2(dx * 24, dy * 24)
                    if pygame.Rect(0, 0, WIDTH, HEIGHT).contains(tank.rect) and not self._solid(tank.rect): break
                else: continue
                break
        tank.turn_timer = self.random.uniform(.4, 1.4); self.enemies.append(tank); return tank

    def spawn_wave(self, number: int, announce: bool = True) -> None:
        self.wave = number; self.enemies = []
        for index, kind in enumerate(WAVES[number - 1]): self.spawn_enemy(kind, ENEMY_SPAWNS[index])
        self.wave_banner = 1.8
        if announce: self.events.append("wave")

    def active_tanks(self) -> list[Tank]:
        return [item for item in [self.player, self.target, *self.enemies] if item is not None]

    def collision_rect(self, tank: Tank) -> pygame.Rect:
        """Use a compact gameplay hitbox while retaining the large tank sprite."""
        size = 20 if tank.kind != EnemyKind.BOSS else 32
        rect = pygame.Rect(0, 0, size, size); rect.center = tank.rect.center
        return rect

    def _solid(self, rect: pygame.Rect, bullet: bool = False) -> bool:
        kinds = (TerrainKind.STEEL, TerrainKind.BRICK) if bullet else (TerrainKind.STEEL, TerrainKind.BRICK, TerrainKind.WATER)
        return any(rect.colliderect(tile.rect) for tile in self.terrain if tile.kind in kinds)

    def move_tank(self, tank: Tank, dx: float, dy: float) -> bool:
        moved = False
        for amount, axis in ((dx, "x"), (dy, "y")):
            if not amount: continue
            old = tank.rect.copy(); setattr(tank.rect, axis, round(getattr(tank.rect, axis) + amount))
            hitbox = self.collision_rect(tank)
            invalid = not pygame.Rect(0, 0, WIDTH, HEIGHT).contains(hitbox) or self._solid(hitbox)
            invalid |= any(other is not tank and other.alive and hitbox.colliderect(self.collision_rect(other)) for other in self.active_tanks())
            if invalid: tank.rect = old
            else: moved = True
        return moved

    def try_fire(self, tank: Tank) -> bool:
        if not tank.alive or tank.cooldown > 0 or self.state != GameState.PLAYING: return False
        dx, dy = tank.direction.value; damage = 1 + (self.campaign.upgrades.get("damage", 0) if tank is self.player else 0)
        speed = 430 * (1.15 ** self.campaign.upgrades.get("bullet_speed", 0) if tank is self.player else 1)
        bullet = Bullet(pygame.Rect(0, 0, 10, 10), tank.direction, tank.team, speed=speed, damage=damage, breaks_bricks=tank.kind != EnemyKind.BOSS or True)
        bullet.rect.center = (tank.rect.centerx + dx * (tank.rect.width // 2 + 7), tank.rect.centery + dy * (tank.rect.height // 2 + 7)); self.bullets.append(bullet)
        reload_factor = .85 ** self.campaign.upgrades.get("reload", 0) if tank is self.player else 1
        tank.cooldown = (.18 if tank is self.player and tank.rapid_timer > 0 else tank.fire_delay) * reload_factor; self.events.append("fire"); return True

    def damage(self, tank: Tank, amount: int = 1) -> None:
        if tank is self.player and (tank.shield_timer > 0 or tank.invulnerable > 0): self.events.append("hit"); return
        tank.health -= amount; tank.flash = .18; self.events.append("hit")
        if tank is self.player: tank.invulnerable = .75 + .25 * self.campaign.upgrades.get("invulnerability", 0)
        if tank.health <= 0:
            tank.alive = False; self.explosions.append(Explosion(tank.rect.center)); self.events.append("explode")
            if tank.team == "enemy":
                self.score += STATS[tank.kind][3]
                if self.random.random() < .35:
                    rect = pygame.Rect(0, 0, 20, 20); rect.center = tank.rect.center; self.powerups.append(Powerup(rect, self.random.choice(list(PowerupKind))))

    def has_clear_shot(self, tank: Tank, target: Tank | None = None) -> bool:
        target = target or self.player; px, py = target.rect.center; tx, ty = tank.rect.center
        if abs(px - tx) < 15: direction, distance = (Direction.DOWN if py > ty else Direction.UP), abs(py - ty)
        elif abs(py - ty) < 15: direction, distance = (Direction.RIGHT if px > tx else Direction.LEFT), abs(px - tx)
        else: return False
        dx, dy = direction.value; probe = pygame.Rect(0, 0, 4, 4)
        for step in range(20, distance, 8):
            probe.center = (tx + dx * step, ty + dy * step)
            if self._solid(probe, True): return False
        tank.direction = direction; return True

    def _boss_salvo(self, boss: Tank) -> None:
        px, py = self.player.rect.center; bx, by = boss.rect.center; base = math.atan2(py - by, px - bx)
        offsets = (-.32, 0, .32) if boss.phase == 1 else tuple(i * math.tau / 10 for i in range(10)) if boss.phase == 3 else (-.7, -.35, 0, .35, .7)
        for offset in offsets:
            vx, vy = math.cos(base + offset), math.sin(base + offset); bullet = Bullet(pygame.Rect(0, 0, 12, 12), boss.direction, "enemy", 330, velocity=(vx, vy))
            bullet.rect.center = boss.rect.center; self.bullets.append(bullet)
        if boss.phase == 2: self.spawn_enemy(EnemyKind.SCOUT, (max(70, bx - 100), min(HEIGHT - 70, by + 100)))
        self.events.append("fire")

    def _enemy_ai(self, enemy: Tank, dt: float) -> None:
        enemy.turn_timer -= dt; target = self.target if self.target and enemy.kind in (EnemyKind.BREAKER, EnemyKind.COMMANDER) else self.player
        nearby_commander = any(other.alive and other.kind == EnemyKind.COMMANDER and other.rect.centerx - enemy.rect.centerx in range(-150, 151) and other.rect.centery - enemy.rect.centery in range(-150, 151) for other in self.enemies if other is not enemy)
        multiplier = 1.25 if nearby_commander else 1
        if enemy.kind == EnemyKind.BOSS:
            old_phase = enemy.phase; enemy.phase = 3 if enemy.health <= enemy.max_health * .35 else 2 if enemy.health <= enemy.max_health * .70 else 1
            if enemy.phase != old_phase: self.events.append("warning")
            enemy.special_timer -= dt
            if enemy.warning_timer > 0:
                enemy.warning_timer -= dt
                if enemy.warning_timer <= 0: self._boss_salvo(enemy); enemy.special_timer = (2.5, 1.8, 1.1)[enemy.phase - 1]
            elif enemy.special_timer <= 0: enemy.warning_timer = .55; self.events.append("warning")
        elif self.has_clear_shot(enemy, target) and enemy.cooldown <= 0: self.try_fire(enemy)
        if enemy.turn_timer <= 0:
            # State logic: seek target first, otherwise patrol around obstacles.
            dx, dy = target.rect.centerx - enemy.rect.centerx, target.rect.centery - enemy.rect.centery
            enemy.direction = Direction.RIGHT if abs(dx) > abs(dy) and dx > 0 else Direction.LEFT if abs(dx) > abs(dy) else Direction.DOWN if dy > 0 else Direction.UP
            enemy.turn_timer = self.random.uniform(.6, 1.4)
        dx, dy = enemy.direction.value
        if not self.move_tank(enemy, dx * enemy.speed * multiplier * dt, dy * enemy.speed * multiplier * dt): enemy.direction = self.random.choice(list(Direction)); enemy.turn_timer = .3

    def _collect_powerups(self, dt: float) -> None:
        kept = []; magnet = 70 * self.campaign.upgrades.get("magnet", 0)
        for item in self.powerups:
            item.ttl -= dt; distance = pygame.Vector2(self.player.rect.center).distance_to(item.rect.center)
            if magnet and distance < magnet and distance > 1:
                delta = pygame.Vector2(self.player.rect.center) - item.rect.center; item.rect.center += delta.normalize() * min(220 * dt, distance)
            if self.player.rect.colliderect(item.rect):
                if item.kind == PowerupKind.HEALTH: self.player.health = min(self.player.max_health, self.player.health + 1)
                elif item.kind == PowerupKind.RAPID: self.player.rapid_timer = 8 if self.legacy else 6
                elif item.kind == PowerupKind.SHIELD: self.player.shield_timer = 6
                else:
                    self.bullets = [bullet for bullet in self.bullets if bullet.team == "player"]
                    for enemy in self.enemies:
                        if enemy.alive and enemy.kind != EnemyKind.BOSS: self.damage(enemy)
                self.events.append("pickup")
            elif item.ttl > 0: kept.append(item)
        self.powerups = kept

    def _advance_bullets(self, dt: float) -> None:
        for bullet in self.bullets:
            vx, vy = bullet.velocity or bullet.direction.value
            for _ in range(max(1, round(bullet.speed * dt / 5))):
                bullet.rect.x += round(vx * 5); bullet.rect.y += round(vy * 5)
                brick = next((tile for tile in self.terrain if tile.kind == TerrainKind.BRICK and bullet.rect.colliderect(tile.rect)), None)
                if brick and bullet.breaks_bricks:
                    brick.health = (brick.health or 1) - bullet.damage
                    if brick.health <= 0:
                        self.terrain.remove(brick); self.events.append("break")
                    else:
                        self.events.append("brick_hit")
                    bullet.alive = False; break
                if not pygame.Rect(0, 0, WIDTH, HEIGHT).contains(bullet.rect) or self._solid(bullet.rect, True): bullet.alive = False; break
                targets = self.enemies if bullet.team == "player" else [item for item in (self.player, self.target) if item]
                target = next((item for item in targets if item.alive and bullet.rect.colliderect(self.collision_rect(item))), None)
                if target: bullet.alive = False; self.damage(target, bullet.damage); break
        self.bullets = [bullet for bullet in self.bullets if bullet.alive]

    def _update_escort(self, dt: float) -> None:
        if not self.target or self.route_index >= len(self.level.escort_route): return
        if any(enemy.alive and pygame.Vector2(enemy.rect.center).distance_to(self.target.rect.center) < 150 for enemy in self.enemies): return
        destination = pygame.Vector2(self.level.escort_route[self.route_index]); offset = destination - self.target.rect.center
        if offset.length() < 5: self.route_index += 1; return
        direction = offset.normalize(); self.move_tank(self.target, direction.x * self.target.speed * dt, direction.y * self.target.speed * dt)

    def update(self, dt: float) -> None:
        if self.state != GameState.PLAYING: return
        self.elapsed += dt; self.wave_banner = max(0, self.wave_banner - dt); self._spawn_due()
        if self.level.mission == MissionKind.SURVIVAL and int(self.elapsed) % 12 == 0 and int(self.elapsed - dt) != int(self.elapsed):
            self.spawn_enemy(self.random.choice([EnemyKind.SCOUT, EnemyKind.RAPID, EnemyKind.BREAKER]), self.random.choice([(80, 80), (880, 80), (880, 640)]))
        for tank in self.active_tanks(): tank.cooldown = max(0, tank.cooldown - dt); tank.flash = max(0, tank.flash - dt); tank.invulnerable = max(0, tank.invulnerable - dt)
        self.player.rapid_timer = max(0, self.player.rapid_timer - dt); self.player.shield_timer = max(0, self.player.shield_timer - dt); self._collect_powerups(dt)
        if self.transition_timer > 0:
            self.transition_timer -= dt
            if self.transition_timer <= 0: self.spawn_wave(self.wave + 1)
            return
        for enemy in self.enemies:
            if enemy.alive: self._enemy_ai(enemy, dt)
        self._advance_bullets(dt); self._update_escort(dt)
        for boom in self.explosions: boom.ttl -= dt
        self.explosions = [boom for boom in self.explosions if boom.ttl > 0]
        if self.player.health <= 0: self.player.alive = False
        if (self.target and self.target.health <= 0): self.target.alive = False
        if not self.player.alive or (self.target and not self.target.alive): self.state = GameState.DEFEAT; self.mission.failed = True; self.events.append("defeat"); return
        alive = any(enemy.alive for enemy in self.enemies) or self.pending_spawns
        if self.legacy and not alive:
            if self.wave == 3: self.state = GameState.VICTORY; self.events.append("victory")
            else: self.transition_timer = 1.8
        elif self.level.mission == MissionKind.SURVIVAL and self.elapsed >= self.level.duration:
            for enemy in self.enemies: enemy.alive = False
            self.mission.completed = True; self.state = GameState.VICTORY; self.events.append("victory")
        elif self.level.mission == MissionKind.ESCORT and self.route_index >= len(self.level.escort_route): self.mission.completed = True; self.state = GameState.VICTORY; self.events.append("victory")
        elif self.level.mission != MissionKind.SURVIVAL and self.level.mission != MissionKind.ESCORT and not alive:
            self.mission.completed = True; self.state = GameState.VICTORY; self.events.append("victory")

    def final_score(self) -> int:
        return self.score + self.player.health * 300 + max(0, 500 - int(self.elapsed))

    def grade(self) -> str:
        s, a, b = self.level.grade_thresholds if not self.legacy else (3400, 3000, 2000); score = self.final_score()
        return "S" if score >= s else "A" if score >= a else "B" if score >= b else "C"

    def upgrade_choices(self) -> tuple[UpgradeDefinition, UpgradeDefinition, UpgradeDefinition]:
        choices = []
        for track in UpgradeTrack:
            options = [item for item in UPGRADES if item.track == track and self.campaign.upgrades.get(item.key, 0) < item.max_level]
            choices.append(self.random.choice(options) if options else next(item for item in UPGRADES if item.track == track))
        return tuple(choices)

    def apply_upgrade(self, upgrade: UpgradeDefinition) -> bool:
        level = self.campaign.upgrades.get(upgrade.key, 0)
        if level >= upgrade.max_level: return False
        self.campaign.upgrades[upgrade.key] = level + 1; return True

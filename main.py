"""Pygame entry point and presentation for Tank Battle HTY."""

from pathlib import Path
import random
import sys

import pygame

from audio import AudioManager
from game import Direction, EnemyKind, GameState, PowerupKind, GameWorld
from level import HEIGHT, WIDTH
from storage import ScoreStore


def load_font(size: int) -> pygame.font.Font:
    path = Path("C:/Windows/Fonts/msyh.ttc")
    return pygame.font.Font(path if path.exists() else None, size)


def draw_arcade_panel(screen: pygame.Surface, rect: pygame.Rect, fill=(255, 250, 231), border=(35, 61, 55)) -> None:
    shadow = rect.move(4, 4)
    pygame.draw.rect(screen, (35, 61, 55), shadow, border_radius=3)
    pygame.draw.rect(screen, fill, rect, border_radius=3)
    pygame.draw.rect(screen, border, rect, 3, border_radius=3)
    pygame.draw.line(screen, (255, 255, 255), (rect.left + 5, rect.top + 5), (rect.right - 5, rect.top + 5), 2)


class TankSprites:
    def __init__(self) -> None:
        folder = Path(__file__).parent / "assets" / "tanks"
        self.images = {
            None: pygame.image.load(folder / "player.png").convert_alpha(),
            EnemyKind.SCOUT: pygame.image.load(folder / "scout.png").convert_alpha(),
            EnemyKind.ARMOR: pygame.image.load(folder / "armor.png").convert_alpha(),
            EnemyKind.SNIPER: pygame.image.load(folder / "sniper.png").convert_alpha(),
            EnemyKind.BOSS: pygame.image.load(folder / "boss.png").convert_alpha(),
        }
        self.cache: dict[tuple[EnemyKind | None, int, Direction], pygame.Surface] = {}

    def image_for(self, tank) -> pygame.Surface:
        key = (tank.kind if tank.team == "enemy" else None, tank.rect.width, tank.direction)
        if key not in self.cache:
            image = pygame.transform.smoothscale(self.images[key[0]], (tank.rect.width, tank.rect.height))
            angle = {Direction.UP: 0, Direction.RIGHT: -90, Direction.DOWN: 180, Direction.LEFT: 90}[tank.direction]
            self.cache[key] = pygame.transform.rotate(image, angle)
        return self.cache[key]


def draw_tank(screen: pygame.Surface, tank, sprites: TankSprites) -> None:
    center = tank.rect.center
    image = sprites.image_for(tank)
    if tank.flash > 0:
        image = image.copy(); image.fill((255, 245, 195, 90), special_flags=pygame.BLEND_RGBA_ADD)
    screen.blit(image, image.get_rect(center=center))
    if tank.shield_timer > 0: pygame.draw.circle(screen, (85, 210, 255), center, tank.rect.width // 2 + 8, 2)
    if tank.kind == EnemyKind.BOSS and tank.warning_timer > 0: pygame.draw.circle(screen, (255, 220, 75), center, tank.rect.width // 2 + 12, 3)


def draw_world(screen: pygame.Surface, world: GameWorld, font: pygame.font.Font, small: pygame.font.Font, background: pygame.Surface, high_score: int, sprites: TankSprites) -> None:
    screen.blit(background, (0, 0))
    for wall in world.walls:
        pygame.draw.rect(screen, (111, 43, 29), wall.rect); pygame.draw.rect(screen, (180, 73, 45), wall.rect.inflate(-4, -4))
    colors = {PowerupKind.HEALTH: (236, 75, 78), PowerupKind.RAPID: (250, 210, 64), PowerupKind.SHIELD: (74, 198, 244)}
    labels = {PowerupKind.HEALTH: "+", PowerupKind.RAPID: "R", PowerupKind.SHIELD: "S"}
    for item in world.powerups:
        pygame.draw.circle(screen, colors[item.kind], item.rect.center, 11); text = small.render(labels[item.kind], True, (35, 35, 30)); screen.blit(text, text.get_rect(center=item.rect.center))
    for bullet in world.bullets:
        tail = bullet.rect.move(-bullet.direction.value[0] * 10, -bullet.direction.value[1] * 10)
        pygame.draw.ellipse(screen, (255, 185, 70), tail); pygame.draw.ellipse(screen, (255, 238, 105) if bullet.team == "player" else (255, 115, 70), bullet.rect)
    for tank in [world.player, *world.enemies]:
        if tank.alive: draw_tank(screen, tank, sprites)
    for boom in world.explosions: pygame.draw.circle(screen, (255, 164, 46), boom.pos, int(28 * boom.ttl / 0.35 + 7))
    boss = next((enemy for enemy in world.enemies if enemy.alive and enemy.kind == EnemyKind.BOSS), None)
    if boss:
        pygame.draw.rect(screen, (44, 38, 34), (WIDTH // 2 - 140, 48, 280, 15)); pygame.draw.rect(screen, (204, 68, 48), (WIDTH // 2 - 138, 50, int(276 * boss.health / 14), 11))
        label = small.render("重装 Boss", True, (255, 240, 215)); screen.blit(label, label.get_rect(center=(WIDTH // 2, 40)))
    effects = []
    if world.player.rapid_timer > 0: effects.append(f"连发 {world.player.rapid_timer:0.1f}s")
    if world.player.shield_timer > 0: effects.append(f"护盾 {world.player.shield_timer:0.1f}s")
    hp_panel = pygame.Rect(18, 16, 238, 74); draw_arcade_panel(screen, hp_panel)
    hp_label = small.render("PLAYER  耐久", True, (35, 61, 55)); screen.blit(hp_label, (33, 29))
    hp_bar = pygame.Rect(33, 52, 165, 18)
    pygame.draw.rect(screen, (220, 216, 193), hp_bar, border_radius=2)
    pygame.draw.rect(screen, (57, 181, 132), (hp_bar.x + 3, hp_bar.y + 3, int((hp_bar.width - 6) * world.player.health / 3), hp_bar.height - 6), border_radius=1)
    pygame.draw.rect(screen, (35, 61, 55), hp_bar, 2, border_radius=2)
    hp_text = small.render(f"{world.player.health}/3", True, (35, 61, 55)); screen.blit(hp_text, (208, 51))
    wave_panel = pygame.Rect(WIDTH // 2 - 76, 16, 152, 42); draw_arcade_panel(screen, wave_panel, (255, 232, 174), (161, 85, 48))
    wave_text = small.render(f"WAVE  {world.wave}", True, (113, 57, 38)); screen.blit(wave_text, wave_text.get_rect(center=wave_panel.center))
    score_panel = pygame.Rect(WIDTH - 210, 16, 192, 74); draw_arcade_panel(screen, score_panel)
    score_title = small.render("SCORE", True, (35, 61, 55)); score_value = small.render(f"{world.score:05d}", True, (35, 61, 55)); best = small.render(f"BEST {high_score:05d}", True, (103, 114, 98))
    screen.blit(score_title, (WIDTH - 193, 28)); screen.blit(score_value, (WIDTH - 133, 28)); screen.blit(best, (WIDTH - 193, 56))
    controls_panel = pygame.Rect(18, HEIGHT - 41, 342, 25); draw_arcade_panel(screen, controls_panel, (255, 250, 231), (35, 61, 55))
    controls = small.render("WASD/方向键移动 · Space射击 · M静音", True, (35, 61, 55)); screen.blit(controls, (30, HEIGHT - 36))
    if effects:
        effects_panel = pygame.Rect(WIDTH - 212, HEIGHT - 41, 194, 25); draw_arcade_panel(screen, effects_panel, (220, 247, 231), (57, 144, 105))
        effect_text = small.render(" | ".join(effects), True, (35, 106, 78)); screen.blit(effect_text, (WIDTH - 201, HEIGHT - 36))
    if world.wave_banner > 0:
        title = font.render(f"第 {world.wave} 波", True, (255, 225, 94)); screen.blit(title, title.get_rect(center=(WIDTH // 2, 96)))


def overlay(screen, title, subtitle, title_font, font) -> None:
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); shade.fill((255, 250, 231, 205)); screen.blit(shade, (0, 0))
    card = pygame.Rect(WIDTH // 2 - 245, HEIGHT // 2 - 106, 490, 212); draw_arcade_panel(screen, card, (255, 246, 215), (35, 61, 55))
    heading = title_font.render(title, True, (35, 61, 55)); hint = font.render(subtitle, True, (113, 57, 38))
    screen.blit(heading, heading.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))); screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 34)))


def main() -> None:
    pygame.init(); screen = pygame.display.set_mode((WIDTH, HEIGHT)); pygame.display.set_caption("坦克大战 · HTY 战术闯关")
    clock = pygame.time.Clock(); font, small, title_font = load_font(22), load_font(16), load_font(48)
    background = pygame.transform.smoothscale(pygame.image.load(Path(__file__).parent / "assets" / "battlefield.png").convert(), (WIDTH, HEIGHT))
    audio, store, world, state, sprites = AudioManager(), ScoreStore(), GameWorld(), GameState.START, TankSprites()
    audio.start_music()
    recorded = False; running = True
    while running:
        dt = min(clock.tick(60) / 1000, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                elif event.key == pygame.K_m: audio.toggle()
                elif state == GameState.START and event.key == pygame.K_RETURN: state = GameState.PLAYING
                elif state in (GameState.VICTORY, GameState.DEFEAT) and event.key == pygame.K_r: world.reset(); state = GameState.PLAYING; recorded = False
                elif state == GameState.PLAYING and event.key == pygame.K_SPACE: world.try_fire(world.player)
        if state == GameState.PLAYING:
            keys = pygame.key.get_pressed(); dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT]); dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
            if dx or dy:
                world.player.direction = Direction.RIGHT if dx > 0 else Direction.LEFT if dx < 0 else Direction.DOWN if dy > 0 else Direction.UP
                world.move_tank(world.player, dx * world.player.speed * dt, dy * world.player.speed * dt)
            world.update(dt); state = world.state
        for sound in world.events: audio.play(sound)
        world.events.clear()
        if state in (GameState.VICTORY, GameState.DEFEAT) and not recorded:
            store.record(world.final_score(), cleared=state == GameState.VICTORY); recorded = True
        canvas = pygame.Surface((WIDTH, HEIGHT)); draw_world(canvas, world, font, small, background, store.high_score, sprites)
        shake = 3 if any(boom.ttl > 0.25 for boom in world.explosions) else 0
        screen.fill((10, 16, 13)); screen.blit(canvas, (random.randint(-shake, shake), random.randint(-shake, shake)))
        if state == GameState.START: overlay(screen, "坦克大战", "Enter 开始 · M 静音 · Esc 退出", title_font, font)
        elif state == GameState.VICTORY: overlay(screen, f"胜利！评级 {world.grade()}", f"总分 {world.final_score()} · 按 R 重开", title_font, font)
        elif state == GameState.DEFEAT: overlay(screen, "任务失败", f"得分 {world.final_score()} · 按 R 从第一波重开", title_font, font)
        pygame.display.flip()
    pygame.quit(); sys.exit()


if __name__ == "__main__": main()

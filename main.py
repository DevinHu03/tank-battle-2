"""Pygame presentation for 《钢铁防线》."""
from __future__ import annotations

from pathlib import Path
import sys

import pygame

from audio import AudioManager
from game import CampaignState, Direction, EnemyKind, GameState, PowerupKind, GameWorld
from level import HEIGHT, LEVELS, TerrainKind, WIDTH
from storage import CampaignStore


def load_font(size: int) -> pygame.font.Font:
    path = Path("C:/Windows/Fonts/msyh.ttc")
    return pygame.font.Font(path if path.exists() else None, size)


class TankSprites:
    def __init__(self) -> None:
        folder = Path(__file__).parent / "assets" / "tanks"
        image = lambda name: pygame.image.load(folder / name).convert_alpha()
        self.images = {None: image("player.png"), EnemyKind.SCOUT: image("scout.png"), EnemyKind.ARMOR: image("armor.png"), EnemyKind.SNIPER: image("sniper.png"), EnemyKind.BOSS: image("boss.png")}
        self.images.update({EnemyKind.RAPID: self.images[EnemyKind.SCOUT], EnemyKind.BREAKER: self.images[EnemyKind.ARMOR], EnemyKind.COMMANDER: self.images[EnemyKind.SNIPER]})
        self.cache: dict[tuple[EnemyKind | None, int, Direction], pygame.Surface] = {}

    def image_for(self, tank) -> pygame.Surface:
        key = (tank.kind if tank.team == "enemy" else None, tank.rect.width, tank.direction)
        if key not in self.cache:
            image = pygame.transform.smoothscale(self.images[key[0]], (tank.rect.width, tank.rect.height))
            self.cache[key] = pygame.transform.rotate(image, {Direction.UP: 0, Direction.RIGHT: -90, Direction.DOWN: 180, Direction.LEFT: 90}[tank.direction])
        return self.cache[key]


def draw_tank(screen: pygame.Surface, tank, sprites: TankSprites) -> None:
    image = sprites.image_for(tank)
    if tank.flash > 0:
        image = image.copy(); image.fill((255, 245, 195, 90), special_flags=pygame.BLEND_RGBA_ADD)
    screen.blit(image, image.get_rect(center=tank.rect.center))
    if tank.shield_timer > 0: pygame.draw.circle(screen, (85, 210, 255), tank.rect.center, tank.rect.width // 2 + 6, 2)


def text(screen, font, value, position, color=(245, 240, 215), center=False):
    surface = font.render(value, True, color); rect = surface.get_rect(center=position) if center else surface.get_rect(topleft=position); screen.blit(surface, rect)


def retro_panel(screen: pygame.Surface, rect: pygame.Rect) -> None:
    """Chunky, low-era arcade bezel shared by menus and HUD."""
    pygame.draw.rect(screen, (16, 24, 18), rect)
    pygame.draw.rect(screen, (238, 196, 96), rect, 3)
    pygame.draw.line(screen, (89, 121, 72), rect.topleft, rect.topright, 2)
    for x in range(rect.left + 8, rect.right - 4, 12): pygame.draw.rect(screen, (43, 61, 39), (x, rect.bottom - 7, 6, 3))


def load_sheet_tiles(path: Path) -> list[pygame.Surface]:
    sheet = pygame.image.load(path).convert()
    half_w, half_h = sheet.get_width() // 2, sheet.get_height() // 2
    return [pygame.transform.scale(sheet.subsurface(pygame.Rect(x * half_w, y * half_h, half_w, half_h)), (24, 24)) for y in range(2) for x in range(2)]


def draw_title_screen(screen: pygame.Surface, title_font: pygame.font.Font, font: pygame.font.Font, small: pygame.font.Font, background: pygame.Surface, entries: list[str], selected: int, has_save: bool) -> None:
    screen.blit(background, (0, 0)); shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); shade.fill((6, 12, 10, 125)); screen.blit(shade, (0, 0))
    retro_panel(screen, pygame.Rect(40, 28, 880, 150)); retro_panel(screen, pygame.Rect(92, 215, 430, 315)); retro_panel(screen, pygame.Rect(570, 215, 300, 315))
    text(screen, title_font, "钢铁防线", (WIDTH // 2, 78), center=True, color=(255, 199, 61)); text(screen, small, "STEEL FRONTLINE  //  INSERT COIN", (WIDTH // 2, 145), center=True, color=(224, 224, 166))
    text(screen, small, "MAIN OPERATIONS", (126, 240), color=(255, 174, 52))
    for index, entry in enumerate(entries):
        disabled = index == 1 and not has_save; color = (255, 209, 77) if index == selected else (114, 151, 92) if not disabled else (57, 74, 54)
        text(screen, font, ("▶  " if index == selected else "   ") + entry, (126, 290 + index * 45), color=color)
    retro_panel(screen, pygame.Rect(595, 240, 250, 220));
    for y in (265, 303, 341, 379, 417): pygame.draw.line(screen, (44, 82, 47), (605, y), (835, y), 2)
    text(screen, font, "SECTOR 01  //  READY", (612, 483), color=(255, 194, 62)); text(screen, small, "ARROW KEYS  MOVE", (612, 510), color=(112, 151, 84)); text(screen, small, "© 198X  //  KEYBOARD ONLY  //  F11 FULLSCREEN", (210, 672), color=(99, 119, 69))


def draw_world(screen, world, font, small, background, high_score, sprites, terrain_art=None, powerup_art=None) -> None:
    screen.blit(background, (0, 0))
    colors = {TerrainKind.BRICK: ((103, 46, 29), (190, 79, 42)), TerrainKind.STEEL: ((58, 63, 58), (147, 154, 139)), TerrainKind.WATER: ((26, 80, 126), (48, 128, 181)), TerrainKind.GRASS: ((38, 101, 46), (72, 144, 65))}
    for tile in world.terrain:
        outer, inner = colors[tile.kind]; pygame.draw.rect(screen, outer, tile.rect); pygame.draw.rect(screen, inner, tile.rect.inflate(-4, -4))
        if terrain_art:
            art_index = {TerrainKind.BRICK: 0, TerrainKind.STEEL: 1, TerrainKind.WATER: 2, TerrainKind.GRASS: 3}[tile.kind]
            screen.blit(terrain_art[art_index], tile.rect)
        if tile.kind == TerrainKind.BRICK:
            pygame.draw.line(screen, (83, 33, 23), (tile.rect.left, tile.rect.centery), (tile.rect.right, tile.rect.centery), 2)
            pygame.draw.line(screen, (83, 33, 23), (tile.rect.centerx, tile.rect.top), (tile.rect.centerx, tile.rect.centery), 2)
            if tile.health == 1: pygame.draw.line(screen, (255, 202, 100), tile.rect.topleft, tile.rect.bottomright, 2)
        elif tile.kind == TerrainKind.STEEL:
            pygame.draw.line(screen, (208, 213, 185), tile.rect.topleft, tile.rect.bottomright, 2); pygame.draw.line(screen, (208, 213, 185), tile.rect.topright, tile.rect.bottomleft, 2)
        elif tile.kind == TerrainKind.WATER: pygame.draw.line(screen, (125, 192, 205), (tile.rect.left + 3, tile.rect.centery), (tile.rect.right - 3, tile.rect.centery), 2)
    if world.target and world.target.alive:
        pygame.draw.rect(screen, (214, 175, 70), world.target.rect.inflate(8, 8), 2)
    item_colors = {PowerupKind.HEALTH: (236, 75, 78), PowerupKind.RAPID: (250, 210, 64), PowerupKind.SHIELD: (74, 198, 244), PowerupKind.SHOCK: (190, 100, 255)}
    for item in world.powerups:
        if powerup_art:
            icon_index = {PowerupKind.HEALTH: 0, PowerupKind.SHIELD: 1, PowerupKind.RAPID: 2, PowerupKind.SHOCK: 3}[item.kind]
            icon = powerup_art[icon_index]; screen.blit(icon, icon.get_rect(center=item.rect.center))
        else: pygame.draw.circle(screen, item_colors[item.kind], item.rect.center, 10)
    for bullet in world.bullets: pygame.draw.ellipse(screen, (255, 220, 90) if bullet.team == "player" else (255, 100, 70), bullet.rect)
    for tank in [world.player, world.target, *world.enemies]:
        if tank and tank.alive: draw_tank(screen, tank, sprites)
    for boom in world.explosions: pygame.draw.circle(screen, (255, 164, 46), boom.pos, int(28 * boom.ttl / .35 + 7))
    retro_panel(screen, pygame.Rect(12, 12, 250, 74))
    text(screen, small, f"生命 {world.player.health}/{world.player.max_health}", (25, 24)); text(screen, small, f"得分 {world.score}  最佳 {high_score}", (25, 49))
    objective = world.level.objective if world.level else ""
    progress = f" {max(0, world.level.duration - world.elapsed):.0f}s" if world.level.duration else ""
    retro_panel(screen, pygame.Rect(WIDTH // 2 - 185, 10, 370, 52)); text(screen, small, objective + progress, (WIDTH // 2, 20), center=True)
    if world.target: text(screen, small, f"目标耐久 {world.target.health}/{world.target.max_health}", (WIDTH // 2, 45), center=True, color=(255, 220, 120))
    boss = next((enemy for enemy in world.enemies if enemy.alive and enemy.kind == EnemyKind.BOSS), None)
    if boss:
        pygame.draw.rect(screen, (35, 35, 35), (WIDTH // 2 - 150, 72, 300, 14)); pygame.draw.rect(screen, (210, 65, 48), (WIDTH // 2 - 148, 74, int(296 * boss.health / boss.max_health), 10)); text(screen, small, f"要塞核心 · 阶段 {boss.phase}", (WIDTH // 2, 58), center=True)
    text(screen, small, "WASD/方向键移动  Space射击  Esc暂停  M静音", (16, HEIGHT - 28))


def overlay(screen, title, lines, title_font, font):
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); shade.fill((8, 15, 19, 220)); screen.blit(shade, (0, 0))
    retro_panel(screen, pygame.Rect(WIDTH // 2 - 280, HEIGHT // 2 - 138, 560, 270))
    text(screen, title_font, title, (WIDTH // 2, HEIGHT // 2 - 80), center=True, color=(255, 216, 102))
    for index, line in enumerate(lines): text(screen, font, line, (WIDTH // 2, HEIGHT // 2 - 10 + index * 34), center=True)


def main() -> None:
    pygame.init(); display = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE); pygame.display.set_caption("钢铁防线")
    clock = pygame.time.Clock(); font, small, title_font = load_font(22), load_font(16), load_font(44); sprites = TankSprites()
    background = pygame.transform.smoothscale(pygame.image.load(Path(__file__).parent / "assets" / "battlefield-retro.png").convert(), (WIDTH, HEIGHT))
    menu_background = pygame.transform.smoothscale(pygame.image.load(Path(__file__).parent / "assets" / "menu-arcade.png").convert(), (WIDTH, HEIGHT))
    terrain_art = load_sheet_tiles(Path(__file__).parent / "assets" / "terrain-tiles-retro.png")
    powerup_art = load_sheet_tiles(Path(__file__).parent / "assets" / "powerups-retro.png")
    store, audio = CampaignStore(), AudioManager(enabled=True); audio.start_music(); state = GameState.TITLE; menu = 0; campaign = store.campaign() or CampaignState(); world = GameWorld(LEVELS[campaign.current_level - 1], campaign)
    entries = ["新游戏", "继续游戏", "设置", "制作人员", "退出"]; running = True
    while running:
        dt = min(clock.tick(60) / 1000, .05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m: audio.toggle()
                elif event.key == pygame.K_F11:
                    flags = pygame.FULLSCREEN if not store.data["settings"]["fullscreen"] else pygame.RESIZABLE; store.data["settings"]["fullscreen"] = not store.data["settings"]["fullscreen"]; store.save(); display = pygame.display.set_mode((WIDTH, HEIGHT), flags)
                elif state == GameState.TITLE:
                    if event.key in (pygame.K_UP, pygame.K_w): menu = (menu - 1) % len(entries)
                    elif event.key in (pygame.K_DOWN, pygame.K_s): menu = (menu + 1) % len(entries)
                    elif event.key == pygame.K_RETURN:
                        if menu == 0: state = GameState.NEW_GAME_CONFIRM
                        elif menu == 1 and store.campaign(): campaign = store.campaign(); world = GameWorld(LEVELS[campaign.current_level - 1], campaign); state = GameState.BRIEFING
                        elif menu == 2: state = GameState.SETTINGS
                        elif menu == 3: state = GameState.CREDITS
                        else: running = False
                elif state == GameState.NEW_GAME_CONFIRM:
                    if event.key == pygame.K_RETURN: campaign = CampaignState(); store.save_campaign(campaign); world = GameWorld(LEVELS[0], campaign); state = GameState.BRIEFING
                    elif event.key == pygame.K_ESCAPE: state = GameState.TITLE
                elif state == GameState.BRIEFING and event.key == pygame.K_RETURN: state = GameState.PLAYING
                elif state == GameState.PLAYING:
                    if event.key == pygame.K_SPACE: world.try_fire(world.player)
                    elif event.key == pygame.K_ESCAPE: state = GameState.PAUSED
                elif state == GameState.PAUSED:
                    if event.key == pygame.K_RETURN: state = GameState.PLAYING
                    elif event.key == pygame.K_r: world.reset()
                    elif event.key == pygame.K_ESCAPE: state = GameState.TITLE
                elif state == GameState.RESULT:
                    if event.key == pygame.K_RETURN: state = GameState.UPGRADES if campaign.current_level < 5 else GameState.VICTORY
                elif state == GameState.UPGRADES and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    world.apply_upgrade(choices[event.key - pygame.K_1]); campaign.current_level += 1; store.save_campaign(campaign); world = GameWorld(LEVELS[campaign.current_level - 1], campaign); state = GameState.BRIEFING
                elif state == GameState.DEFEAT:
                    if event.key == pygame.K_RETURN: world.reset(); state = GameState.BRIEFING
                    elif event.key == pygame.K_ESCAPE: state = GameState.TITLE
                elif state in (GameState.SETTINGS, GameState.CREDITS, GameState.VICTORY) and event.key == pygame.K_ESCAPE: state = GameState.TITLE
        if state == GameState.PLAYING:
            keys = pygame.key.get_pressed(); dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT]); dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
            if dx or dy:
                # Normalize diagonal input so two keys do not grant a speed bonus.
                movement = pygame.Vector2(dx, dy).normalize() * world.player.speed * dt
                world.player.direction = Direction.RIGHT if dx > 0 else Direction.LEFT if dx < 0 else Direction.DOWN if dy > 0 else Direction.UP
                world.move_tank(world.player, movement.x, movement.y)
            world.update(dt)
            if world.state == GameState.VICTORY:
                campaign.score += world.final_score(); campaign.elapsed += world.elapsed; store.record_level(campaign.current_level, world.final_score(), world.elapsed, world.grade()); choices = world.upgrade_choices(); state = GameState.RESULT
            elif world.state == GameState.DEFEAT: state = GameState.DEFEAT
        for sound in world.events: audio.play(sound)
        world.events.clear(); canvas = pygame.Surface((WIDTH, HEIGHT))
        if state in (GameState.TITLE, GameState.NEW_GAME_CONFIRM):
            draw_title_screen(canvas, title_font, font, small, menu_background, entries, menu, bool(store.campaign()))
        else:
            draw_world(canvas, world, font, small, background, store.data["best_campaign_score"], sprites, terrain_art, powerup_art)
        if state == GameState.NEW_GAME_CONFIRM: overlay(canvas, "开始新战役？", ["将覆盖当前战役进度，保留历史纪录与设置", "Enter 确认   Esc 返回"], title_font, font)
        elif state == GameState.BRIEFING: overlay(canvas, world.level.title, [world.level.briefing, "目标：" + world.level.objective, "失败：" + world.level.failure, "Enter 开始任务"], title_font, font)
        elif state == GameState.PAUSED: overlay(canvas, "暂停", ["Enter 继续", "R 重试本关", "Esc 返回主菜单"], title_font, font)
        elif state == GameState.RESULT: overlay(canvas, f"任务完成 · {world.grade()}", [f"得分 {world.final_score()}   用时 {world.elapsed:.1f} 秒", "Enter 继续"], title_font, font)
        elif state == GameState.UPGRADES: overlay(canvas, "选择永久强化", [f"{i + 1}. {choice.name}：{choice.description}" for i, choice in enumerate(choices)], title_font, font)
        elif state == GameState.DEFEAT: overlay(canvas, "任务失败", ["Enter 从本关起点重试", "Esc 返回主菜单"], title_font, font)
        elif state == GameState.SETTINGS: overlay(canvas, "设置", [f"音乐：{'开' if store.data['settings']['music'] else '关'}  音效：{'开' if store.data['settings']['sound'] else '关'}", "M 快速静音  F11 全屏", "Esc 返回"], title_font, font)
        elif state == GameState.CREDITS: overlay(canvas, "制作人员", ["《钢铁防线》开发组", "特别致谢：HTY", "Esc 返回"], title_font, font)
        elif state == GameState.VICTORY: overlay(canvas, "战役胜利", [f"总分 {campaign.score}   总用时 {campaign.elapsed:.1f} 秒", "Esc 返回主菜单"], title_font, font)
        size = display.get_size(); scale = min(size[0] / WIDTH, size[1] / HEIGHT); target = pygame.transform.smoothscale(canvas, (int(WIDTH * scale), int(HEIGHT * scale))); display.fill((0, 0, 0)); display.blit(target, target.get_rect(center=(size[0] // 2, size[1] // 2))); pygame.display.flip()
    pygame.quit(); sys.exit()


if __name__ == "__main__": main()

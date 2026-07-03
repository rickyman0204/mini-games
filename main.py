"""成双成对 + 摇钱树 - Scratch card and Money Tree games"""
import sys
import math
import random
import logging
import asyncio
import pygame

IS_WEB = sys.platform == 'emscripten'

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, TARGET_FPS, COLORS,
    CARD_WIDTH, CARD_HEIGHT, CARD_SPACING, CARD_MARGIN_TOP,
    PRIZES, PARTICLE_COUNT_CELEBRATION, PARTICLE_LIFETIME,
    PARTICLE_GRAVITY, CELEBRATION_TEXT_DURATION, CELEBRATION_FADEOUT_DURATION,
    CELEBRATION_BLACK_DURATION, CELEBRATION_FADEIN_DURATION,
    SCRATCH_TICKET_COST, TREE_SHAKE_COST, MAX_SHAKES, BOMB_DEFUSE_COST, BOMB_REWARD,
    CAVE_ENTRY_COST, MAZE_ENTRY_COST, MAZE_CHOICES, MAZE_PRIZES,
    FISHING_ENTRY_COST, FISHING_CASTS_PER_ENTRY, FISH_TYPES,
    LOTTERY_ENTRY_COST, LOTTERY_PRIZES,
    LADDER_ENTRY_COST, DICE_ENTRY_COST,
    MATH_ENTRY_COST, MARBLE_ENTRY_COST,
    COIN_ENTRY_COST,
    HORSE_ENTRY_COST, HORSE_WIN_MIN, HORSE_WIN_MAX, HORSE_DRAW_COST,
    TRASH_ENTRY_COST,
    WOODEN_FISH_ENTRY_COST,
    WHEEL_ENTRY_COST,
    GO_OUT_ENTRY_COST, GO_OUT_PREDICT_COST,
    STRENGTH_ENTRY_COST,
    EXAM_ENTRY_COST,
    FLYING_CHESS_ENTRY_COST,
    TREE_DROPS, CAVE_COIN_TYPES, CAVE_COIN_MIN, CAVE_COIN_MAX,
)
from src.utils import (
    s, get_font, hex_to_rgb, get_mouse_pos, set_mouse_transform,
    ease_out_quad, ease_out_back, ease_out_cubic, ease_in_out_quad,
    lerp_color, clamp,
    generate_prizes, has_pair,
    draw_text_with_shadow, draw_text_with_glow, draw_rounded_panel,
    draw_button, draw_exit_button, draw_game_border,
    draw_breathing_hint, draw_result_overlay, draw_progress_bar,
)
from src.scratch_card import ScratchCard
from src.apple_tree import AppleTree
from src.money_tree import MoneyTree, ACTIONS as MONEY_TREE_ACTIONS, QUICK_DEMAND_MIN, QUICK_DEMAND_MAX
from src.bomb_game import BombGame
from src.cave_game import CaveGame
from src.maze_game import MazeGame
from src.fishing_game import FishingGame
from src.lottery_game import NumberLottery
from src.ladder_game import LadderGame
from src.dice_game import DiceGame
from src.math_game import MathGame
from src.marble_game import MarbleGame, LANDING_SPOTS
from src.coin_toss_game import CoinTossGame
from src.horse_racing import HorseRacingGame
from src.trash_game import TrashGame, TRASH_TYPES
from src.wooden_fish import WoodenFishGame
from src.wheel_game import WheelGame, SEGMENTS
from src.go_out_game import GoOutGame
from src.strength_game import StrengthGame
from src.exam_grading import ExamGradingGame
from src.flying_chess import FlyingChessGame
from src.particles import ParticleEmitter
from src.audio import Fanfare
from src.wallet import Wallet


# Game IDs
GAME_SCRATCH = 0
GAME_APPLE = 1
GAME_BOMB = 2
GAME_CAVE = 3
GAME_MAZE = 4
GAME_FISHING = 5
GAME_LOTTERY = 6
GAME_LADDER = 7
GAME_DICE = 8
GAME_MONEY = 9
GAME_MATH = 10
GAME_MARBLE = 11
GAME_COIN = 12
GAME_HORSE = 13
GAME_TRASH = 14
GAME_WOODEN_FISH = 15
GAME_WHEEL = 16
GAME_GO_OUT = 17
GAME_STRENGTH = 18
GAME_EXAM = 19
GAME_FLYING_CHESS = 20
GAME_NAMES = {
    GAME_SCRATCH: '1. 成双成对',
    GAME_APPLE: '2. 苹果树',
    GAME_BOMB: '3. 拆炸弹',
    GAME_CAVE: '4. 躲藏山洞',
    GAME_MAZE: '5. 迷宫探险',
    GAME_FISHING: '6. 钓鱼',
    GAME_LOTTERY: '7. 数字彩票',
    GAME_LADDER: '8. 爬梯子',
    GAME_DICE: '9. 骰子游戏',
    GAME_MONEY: '10. 摇钱树培养',
    GAME_MATH: '11. 随机算式',
    GAME_MARBLE: '12. 弹珠游戏',
    GAME_COIN: '13. 掷硬币',
    GAME_HORSE: '14. 赛马',
    GAME_TRASH: '15. 捡垃圾',
    GAME_WOODEN_FISH: '16. 敲木鱼',
    GAME_WHEEL: '17. 幸运转盘',
    GAME_GO_OUT: '18. 是否要出门',
    GAME_STRENGTH: '19. 力量比拼',
    GAME_EXAM: '20. 试卷批阅',
    GAME_FLYING_CHESS: '21. 飞行棋',
}


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


class Game:
    """Main game class managing both games, wallet, and navigation"""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption('小游戏合集')

        # Create resizable window with initial size
        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE
        )
        self.window_size = (WINDOW_WIDTH, WINDOW_HEIGHT)
        self.fullscreen = False

        # Set window icon
        try:
            icon = pygame.image.load('icon.ico').convert_alpha()
            pygame.display.set_icon(icon)
        except Exception:
            pass

        # Base surface: fixed 1280x900 game canvas
        self.base_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))

        # Scaling: content always rendered at 1280x900, then scaled to window
        self._update_scale()

        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.SysFont('microsoftyahei', 48, bold=True)
        self.font_subtitle = pygame.font.SysFont('microsoftyahei', 20)
        self.font_result = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        self.font_hint = pygame.font.SysFont('microsoftyahei', 18)
        self.font_money = pygame.font.SysFont('microsoftyahei', 22, bold=True)

        self.particles = ParticleEmitter()
        self.running = True

        # Background music
        try:
            import sys
            import os
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller exe — bundled data is in temp dir
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            mp3_path = os.path.join(base_path, 'man.mp3')
            pygame.mixer.music.load(mp3_path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)  # loop forever
        except Exception:
            pass

        # Wallet
        self.wallet = Wallet()

        # Game state: 'menu' -> 'playing' -> 'result' -> 'celebration'
        self.state = 'menu'
        self.state_timer = 0.0

        # Current game index
        self.current_game = GAME_SCRATCH
        self.game_switch_anim = 0.0
        self.game_slide_x = 0.0

        # Celebration
        self.celebration_phase = None
        self.celebration_timer = 0.0
        self.celebration_alpha = 0.0
        self.fanfare = Fanfare()
        self.ambient_hum = None

        # Scratch card game
        self.cards = []

        # Apple tree game (shake-based)
        self.apple_tree = AppleTree(self.wallet)

        # Money tree cultivation game
        self.money_tree = MoneyTree(self.wallet)

        # Bomb game
        self.bomb_game = BombGame(self.wallet)
        self.bomb_game.reset()

        # Cave game
        self.cave_game = CaveGame(self.wallet)
        self.cave_game.reset()

        # Maze game
        self.maze_game = MazeGame(self.wallet)
        self.maze_game.reset()

        # Fishing game
        self.fishing_game = FishingGame(self.wallet)
        self.fishing_game.reset()

        # Number Lottery
        self.lottery_game = NumberLottery(self.wallet)
        self.lottery_game.reset()

        # Ladder Climbing
        self.ladder_game = LadderGame(self.wallet)
        self.ladder_game.reset()

        # Dice Game
        self.dice_game = DiceGame(self.wallet)
        self.dice_game.reset()

        # Math Game
        self.math_game = MathGame(self.wallet)
        self.math_game.reset()

        # Marble Game
        self.marble_game = MarbleGame(self.wallet)
        self.marble_game.reset()

        # Coin Toss Game
        self.coin_game = CoinTossGame(self.wallet)
        self.coin_game.reset()

        # Horse Racing Game
        self.horse_game = HorseRacingGame(self.wallet)
        self.horse_game.reset()

        # Trash Collection Game
        self.trash_game = TrashGame(self.wallet)
        self.trash_game.reset()

        # Wooden Fish Game
        self.wooden_fish_game = WoodenFishGame(self.wallet)
        self.wooden_fish_game.reset()

        # Lucky Wheel Game
        self.wheel_game = WheelGame(self.wallet)
        self.wheel_game.reset()

        # Go Out Game
        self.go_out_game = GoOutGame(self.wallet)
        self.go_out_game.reset()

        # Strength Competition Game
        self.strength_game = StrengthGame(self.wallet)
        self.strength_game.reset()

        # Exam Grading Game
        self.exam_game = ExamGradingGame(self.wallet)
        self.exam_game.reset()

        # Flying Chess Game
        self.flying_chess_game = FlyingChessGame(self.wallet)
        self.flying_chess_game.reset()

        # Result
        self.result_text = ''
        self.result_color = COLORS['gold']
        self.result_scale = 0.0

        # Title animation
        self.title_bob = 0.0
        self.title_pulse = 0.0

        self._init_sparkles()
        self._setup_scratch_cards()

    def _update_scale(self):
        """Calculate scale factor to fit base surface into current window"""
        win_w, win_h = self.screen.get_size()
        self.window_size = (win_w, win_h)
        scale = min(win_w / WINDOW_WIDTH, win_h / WINDOW_HEIGHT)
        self._scale = scale
        self._offset_x = (win_w - WINDOW_WIDTH * scale) / 2
        self._offset_y = (win_h - WINDOW_HEIGHT * scale) / 2
        set_mouse_transform(scale, self._offset_x, self._offset_y)

    def _toggle_fullscreen(self):
        """Toggle between windowed and fullscreen mode"""
        if IS_WEB:
            return
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            info = pygame.display.Info()
            self.screen = pygame.display.set_mode(
                (info.current_w, info.current_h), pygame.FULLSCREEN
            )
        else:
            self.screen = pygame.display.set_mode(
                (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE
            )
        self._update_scale()

    def _scale_to_window(self):
        """Blit base_surface to screen with proper scaling and letterboxing"""
        self.screen.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(
            self.base_surface,
            (int(WINDOW_WIDTH * self._scale), int(WINDOW_HEIGHT * self._scale))
        )
        self.screen.blit(scaled, (self._offset_x, self._offset_y))

    def _init_sparkles(self):
        """Initialize sparkle positions for menu screen"""
        self.title_sparkles = []
        for _ in range(20):
            self.title_sparkles.append({
                'pos': (random.uniform(50, WINDOW_WIDTH - 50),
                        random.uniform(50, WINDOW_HEIGHT - 50)),
                'phase': random.uniform(0, math.pi * 2),
                'speed': random.uniform(1, 3),
            })

    def _setup_scratch_cards(self):
        """Create scratch cards for a new round"""
        prizes = generate_prizes(3)
        self.cards = []
        total_width = CARD_WIDTH * 3 + CARD_SPACING * 2
        start_x = (WINDOW_WIDTH - total_width) // 2

        for i, prize in enumerate(prizes):
            x = start_x + i * (CARD_WIDTH + CARD_SPACING)
            y = CARD_MARGIN_TOP
            card = ScratchCard(x, y, prize, i)
            self.cards.append(card)

        self.result_scale = 0.0

    def handle_events(self):
        """Process pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                self._update_scale()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_LEFT:
                    self._switch_game((self.current_game - 1) % 21)
                elif event.key == pygame.K_RIGHT:
                    self._switch_game((self.current_game + 1) % 21)
                elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    if self.state == 'playing' and self.current_game == GAME_FISHING:
                        if self.fishing_game.game_state in ('mashing', 'intro'):
                            self.fishing_game.handle_key(event.key)
                            return  # Don't process as menu confirm
                        elif self.fishing_game.game_state == 'done':
                            self._go_to_menu()
                    if self.state == 'menu':
                        self._start_current_game()
                    elif self.state == 'result':
                        self._go_to_menu()
                    elif self.celebration_phase is not None:
                        self._skip_celebration()
                    elif self.state == 'playing' and self.current_game == GAME_BOMB:
                        if self.bomb_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_CAVE:
                        if self.cave_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_MAZE:
                        if self.maze_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_FISHING:
                        if self.fishing_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_MONEY:
                        if self.money_tree.game_state == 'done':
                            if self.money_tree.won_free_scratch:
                                self.current_game = GAME_SCRATCH
                                self._setup_scratch_cards()
                                self.state = 'playing'
                                self.money_tree.reset()
                            else:
                                self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_LOTTERY:
                        if self.lottery_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_LADDER:
                        if self.ladder_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_DICE:
                        if self.dice_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_MATH:
                        if self.math_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_MARBLE:
                        if self.marble_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_COIN:
                        if self.coin_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_HORSE:
                        if self.horse_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_TRASH:
                        if self.trash_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_WOODEN_FISH:
                        if self.wooden_fish_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_WHEEL:
                        if self.wheel_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_GO_OUT:
                        if self.go_out_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_STRENGTH:
                        if self.strength_game.game_state == 'done':
                            self._go_to_menu()
                        elif self.strength_game.game_state == 'playing':
                            self.strength_game.handle_keydown(event.key)
                    elif self.state == 'playing' and self.current_game == GAME_EXAM:
                        if self.exam_game.game_state == 'done':
                            self._go_to_menu()
                    elif self.state == 'playing' and self.current_game == GAME_FLYING_CHESS:
                        if self.flying_chess_game.game_state == 'done':
                            self._go_to_menu()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = get_mouse_pos()
                    # Check navigator arrow clicks first (always responsive)
                    if self._handle_navigator_click(mouse_pos):
                        continue
                    if self.state == 'menu':
                        self._start_current_game()
                    elif self.state == 'result':
                        self._go_to_menu()
                    elif self.celebration_phase is not None:
                        self._skip_celebration()
                    elif self.state == 'playing':
                        if self.current_game == GAME_APPLE:
                            self.apple_tree.handle_click(mouse_pos)
                        elif self.current_game == GAME_MONEY:
                            if self.money_tree.game_state == 'done':
                                if self.money_tree.won_free_scratch:
                                    self.current_game = GAME_SCRATCH
                                    self._setup_scratch_cards()
                                    self.state = 'playing'
                                    self.money_tree.reset()
                                else:
                                    self._go_to_menu()
                                return
                            else:
                                self.money_tree.handle_click(mouse_pos)
                        elif self.current_game == GAME_BOMB:
                            self.bomb_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_CAVE:
                            self.cave_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_MAZE:
                            self.maze_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_FISHING:
                            self.fishing_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_LOTTERY:
                            self.lottery_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_LADDER:
                            self.ladder_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_DICE:
                            self.dice_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_MATH:
                            self.math_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_MARBLE:
                            self.marble_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_COIN:
                            self.coin_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_HORSE:
                            self.horse_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_TRASH:
                            self.trash_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_WOODEN_FISH:
                            self.wooden_fish_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_WHEEL:
                            self.wheel_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_GO_OUT:
                            self.go_out_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_STRENGTH:
                            self.strength_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_EXAM:
                            self.exam_game.handle_click(mouse_pos)
                        elif self.current_game == GAME_FLYING_CHESS:
                            self.flying_chess_game.handle_click(mouse_pos)

        # Handle scratching
        if self.state == 'playing' and self.current_game == GAME_SCRATCH:
            mouse_pressed = pygame.mouse.get_pressed()[0]
            if mouse_pressed:
                mouse_pos = get_mouse_pos()
                for card in self.cards:
                    card.handle_mouse(mouse_pos, mouse_pressed)

    def _switch_game(self, game_id: int):
        """Switch between games (only from menu state)"""
        if self.state != 'menu':
            return
        if game_id == self.current_game:
            return
        self.current_game = game_id
        self.game_switch_anim = 0.0

    def _start_current_game(self):
        """Start the current selected game"""
        if self.current_game == GAME_SCRATCH:
            if not self.wallet.can_afford(SCRATCH_TICKET_COST):
                return
            self.wallet.spend(SCRATCH_TICKET_COST)
            self._setup_scratch_cards()
        elif self.current_game == GAME_APPLE:
            if not self.wallet.can_afford(TREE_SHAKE_COST):
                return
            self.wallet.spend(TREE_SHAKE_COST)
            self.apple_tree.reset()
        elif self.current_game == GAME_MONEY:
            self.money_tree.reset()
        elif self.current_game == GAME_BOMB:
            if not self.wallet.can_afford(BOMB_DEFUSE_COST):
                return
            self.wallet.spend(BOMB_DEFUSE_COST)
            self.bomb_game.reset()
        elif self.current_game == GAME_CAVE:
            if not self.wallet.can_afford(CAVE_ENTRY_COST):
                return
            self.wallet.spend(CAVE_ENTRY_COST)
            self.cave_game.reset()
        elif self.current_game == GAME_MAZE:
            if not self.wallet.can_afford(MAZE_ENTRY_COST):
                return
            self.wallet.spend(MAZE_ENTRY_COST)
            self.maze_game.reset()
        elif self.current_game == GAME_FISHING:
            if not self.wallet.can_afford(FISHING_ENTRY_COST):
                return
            self.wallet.spend(FISHING_ENTRY_COST)
            self.fishing_game.reset()
            self.fishing_game.casts_left = FISHING_CASTS_PER_ENTRY
        elif self.current_game == GAME_LOTTERY:
            if not self.wallet.can_afford(LOTTERY_ENTRY_COST):
                return
            self.wallet.spend(LOTTERY_ENTRY_COST)
            self.lottery_game.reset()
        elif self.current_game == GAME_LADDER:
            if not self.wallet.can_afford(LADDER_ENTRY_COST):
                return
            self.wallet.spend(LADDER_ENTRY_COST)
            self.ladder_game.reset()
        elif self.current_game == GAME_DICE:
            if not self.wallet.can_afford(DICE_ENTRY_COST):
                return
            self.wallet.spend(DICE_ENTRY_COST)
            self.dice_game.reset()
        elif self.current_game == GAME_MATH:
            if not self.wallet.can_afford(MATH_ENTRY_COST):
                return
            self.wallet.spend(MATH_ENTRY_COST)
            self.math_game.reset()
        elif self.current_game == GAME_MARBLE:
            if not self.wallet.can_afford(MARBLE_ENTRY_COST):
                return
            self.wallet.spend(MARBLE_ENTRY_COST)
            self.marble_game.reset()
        elif self.current_game == GAME_COIN:
            self.coin_game.reset()
        elif self.current_game == GAME_HORSE:
            if not self.wallet.can_afford(HORSE_ENTRY_COST):
                return
            self.wallet.spend(HORSE_ENTRY_COST)
            self.horse_game.reset()
        elif self.current_game == GAME_TRASH:
            if not self.wallet.can_afford(TRASH_ENTRY_COST):
                return
            self.wallet.spend(TRASH_ENTRY_COST)
            self.trash_game.reset()
        elif self.current_game == GAME_WOODEN_FISH:
            if not self.wallet.can_afford(WOODEN_FISH_ENTRY_COST):
                return
            self.wallet.spend(WOODEN_FISH_ENTRY_COST)
            self.wooden_fish_game.reset()
        elif self.current_game == GAME_WHEEL:
            if not self.wallet.can_afford(WHEEL_ENTRY_COST):
                return
            self.wallet.spend(WHEEL_ENTRY_COST)
            self.wheel_game.reset()
        elif self.current_game == GAME_GO_OUT:
            if not self.wallet.can_afford(GO_OUT_ENTRY_COST):
                return
            self.wallet.spend(GO_OUT_ENTRY_COST)
            self.go_out_game.reset()
        elif self.current_game == GAME_STRENGTH:
            if not self.wallet.can_afford(STRENGTH_ENTRY_COST):
                return
            self.wallet.spend(STRENGTH_ENTRY_COST)
            self.strength_game.reset()
        elif self.current_game == GAME_EXAM:
            if not self.wallet.can_afford(EXAM_ENTRY_COST):
                return
            self.wallet.spend(EXAM_ENTRY_COST)
            self.exam_game.reset()
        elif self.current_game == GAME_FLYING_CHESS:
            if not self.wallet.can_afford(FLYING_CHESS_ENTRY_COST):
                return
            self.wallet.spend(FLYING_CHESS_ENTRY_COST)
            self.flying_chess_game.reset()

        self.state = 'playing'
        self.state_timer = 0.0

    def _go_to_menu(self):
        """Go back to menu"""
        self.state = 'menu'
        self.state_timer = 0.0
        self.particles.clear()

    def _skip_celebration(self):
        """Skip celebration"""
        self.fanfare.stop()
        self.particles.clear()
        self.state = 'menu'
        self.state_timer = 0.0
        self.celebration_phase = None
        self.celebration_alpha = 0.0

    def _trigger_result(self):
        """Show scratch card result"""
        prizes = [card.prize_key for card in self.cards]
        self.state = 'result'
        self.state_timer = 0.0

        if has_pair(prizes):
            # Calculate winnings: each matching prize pays its value
            prize_values = {'gold': 20, 'banknote': 10, 'coin': 5}
            winnings = sum(prize_values.get(p, 0) for p in prizes)
            self.wallet.add(winnings)

            self.result_text = f'成双成对！赢得 ¥{winnings}！'
            self.result_color = COLORS['gold']

            # Celebration particles
            for card in self.cards:
                center = (card.rect.centerx, card.rect.centery)
                color = hex_to_rgb(card.prize_data['color'])
                self.particles.emit_burst(
                    center, PARTICLE_COUNT_CELEBRATION // 3, color,
                    speed_range=(100, 300), lifetime=PARTICLE_LIFETIME,
                    size=4, gravity=PARTICLE_GRAVITY
                )
            confetti_colors = ['#FFD700', '#FF6B6B', '#2ECC71', '#C0C0C0', '#FFEC8B']
            self.particles.emit_confetti(
                (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 100),
                PARTICLE_COUNT_CELEBRATION, confetti_colors, lifetime=2.5
            )
        else:
            self.result_text = '很遗憾，没有中奖！'
            self.result_color = COLORS['text_secondary']

    def _trigger_celebration(self):
        """Start celebration animation"""
        self.state = 'celebration'
        self.state_timer = 0.0
        self.celebration_phase = 'text'
        self.celebration_timer = 0.0
        self.celebration_alpha = 0.0
        self.fanfare.play()
        self.ambient_hum = generate_ambient_hum(
            CELEBRATION_FADEOUT_DURATION + CELEBRATION_BLACK_DURATION + CELEBRATION_FADEIN_DURATION
        )

    def update(self, dt: float):
        """Update game state"""
        self.title_bob += dt
        self.title_pulse += dt * 2

        # Game switch animation
        if self.game_switch_anim < 1.0:
            self.game_switch_anim = min(1.0, self.game_switch_anim + dt * 4)

        # Update cards
        for card in self.cards:
            card.update(dt)

        # Update apple tree
        self.apple_tree.update(dt)

        # Update money tree cultivation
        self.money_tree.update(dt)

        # Update bomb game
        self.bomb_game.update(dt)

        # Update cave game
        self.cave_game.update(dt)

        # Update maze game
        self.maze_game.update(dt)

        # Update fishing game
        self.fishing_game.update(dt)

        # Update particles
        self.particles.update(dt)

        if self.state == 'playing':
            if self.current_game == GAME_SCRATCH:
                if all(card.scratched for card in self.cards):
                    self._trigger_result()
            elif self.current_game == GAME_APPLE:
                if self.apple_tree.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_MONEY:
                if self.money_tree.game_state == 'done':
                    if self.money_tree.won_free_scratch:
                        free_game = self.money_tree.won_free_game_id if self.money_tree.won_free_game_id is not None else GAME_SCRATCH
                        self.current_game = free_game
                        if free_game == GAME_SCRATCH:
                            self._setup_scratch_cards()
                        self.state = 'playing'
                        self.money_tree.reset()
                    else:
                        self._go_to_menu()
            elif self.current_game == GAME_BOMB:
                if self.bomb_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_CAVE:
                if self.cave_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_MAZE:
                if self.maze_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_FISHING:
                if self.fishing_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_LOTTERY:
                self.lottery_game.update(dt)
                if self.lottery_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_LADDER:
                self.ladder_game.update(dt)
                if self.ladder_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_DICE:
                self.dice_game.update(dt)
                if self.dice_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_MATH:
                self.math_game.update(dt)
                if self.math_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_MARBLE:
                self.marble_game.update(dt)
                if self.marble_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_COIN:
                self.coin_game.update(dt)
                if self.coin_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_HORSE:
                self.horse_game.update(dt)
                if self.horse_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_TRASH:
                self.trash_game.update(dt)
                if self.trash_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_WOODEN_FISH:
                self.wooden_fish_game.update(dt)
                if self.wooden_fish_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_WHEEL:
                self.wheel_game.update(dt)
                if self.wheel_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_GO_OUT:
                self.go_out_game.update(dt)
                if self.go_out_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_STRENGTH:
                self.strength_game.update(dt)
                if self.strength_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_EXAM:
                self.exam_game.update(dt)
                if self.exam_game.game_state == 'done':
                    self._go_to_menu()
            elif self.current_game == GAME_FLYING_CHESS:
                self.flying_chess_game.update(dt)
                if self.flying_chess_game.game_state == 'done':
                    self._go_to_menu()

        if self.state == 'result':
            self.state_timer += dt
            if self.result_scale < 1.0:
                progress = min(1.0, self.state_timer * 2.5)
                self.result_scale = ease_out_back(progress)

            # Auto celebration for big wins
            if self.state_timer >= 5.0 and '赢得' in self.result_text:
                self._trigger_celebration()

        if self.state == 'celebration':
            self._update_celebration(dt)

    def _update_celebration(self, dt: float):
        """Update celebration state machine"""
        self.celebration_timer += dt
        self.state_timer += dt

        if self.celebration_phase == 'text':
            if self.celebration_timer >= CELEBRATION_TEXT_DURATION:
                self.celebration_phase = 'fadeout'
                self.celebration_timer = 0.0
        elif self.celebration_phase == 'fadeout':
            progress = min(1.0, self.celebration_timer / CELEBRATION_FADEOUT_DURATION)
            self.celebration_alpha = ease_out_quad(progress)
            if progress >= 1.0:
                self.celebration_phase = 'black'
                self.celebration_timer = 0.0
                if self.ambient_hum:
                    channel = pygame.mixer.find_channel(True)
                    channel.play(self.ambient_hum)
        elif self.celebration_phase == 'black':
            self.celebration_alpha = 1.0
            if self.celebration_timer >= CELEBRATION_BLACK_DURATION:
                self.celebration_phase = 'fadein'
                self.celebration_timer = 0.0
                self._setup_scratch_cards()
                self.apple_tree.reset()
                self.money_tree.reset()
                self.particles.clear()
        elif self.celebration_phase == 'fadein':
            progress = min(1.0, self.celebration_timer / CELEBRATION_FADEIN_DURATION)
            self.celebration_alpha = 1.0 - ease_out_quad(progress)
            if progress >= 1.0:
                self.fanfare.stop()
                self.state = 'menu'
                self.state_timer = 0.0
                self.celebration_phase = None
                self.celebration_alpha = 0.0

    def draw(self):
        """Render everything to base surface, then scale to window"""
        surf = self.screen  # save original screen
        self.screen = self.base_surface  # redirect drawing to base

        self.screen.fill(hex_to_rgb(COLORS['bg_primary']))
        self._draw_background_decoration()

        if self.state == 'menu':
            self._draw_menu()
        elif self.state == 'playing':
            if self.current_game == GAME_SCRATCH:
                self._draw_scratching()
            elif self.current_game == GAME_APPLE:
                self._draw_apple_tree()
            elif self.current_game == GAME_BOMB:
                self._draw_bomb()
            elif self.current_game == GAME_CAVE:
                self._draw_cave()
            elif self.current_game == GAME_MAZE:
                self._draw_maze()
            elif self.current_game == GAME_FISHING:
                self._draw_fishing()
            elif self.current_game == GAME_LOTTERY:
                self._draw_lottery()
            elif self.current_game == GAME_LADDER:
                self._draw_ladder()
            elif self.current_game == GAME_DICE:
                self._draw_dice()
            elif self.current_game == GAME_MONEY:
                self._draw_money_tree()
            elif self.current_game == GAME_MATH:
                self._draw_math_game()
            elif self.current_game == GAME_MARBLE:
                self._draw_marble_game()
            elif self.current_game == GAME_COIN:
                self._draw_coin_game()
            elif self.current_game == GAME_HORSE:
                self._draw_horse_game()
            elif self.current_game == GAME_TRASH:
                self._draw_trash_game()
            elif self.current_game == GAME_WOODEN_FISH:
                self._draw_wooden_fish_game()
            elif self.current_game == GAME_WHEEL:
                self._draw_wheel_game()
            elif self.current_game == GAME_GO_OUT:
                self._draw_go_out_game()
            elif self.current_game == GAME_STRENGTH:
                self._draw_strength_game()
            elif self.current_game == GAME_EXAM:
                self._draw_exam_game()
            elif self.current_game == GAME_FLYING_CHESS:
                self._draw_flying_chess_game()
        elif self.state == 'result':
            if self.current_game == GAME_SCRATCH:
                self._draw_scratching()
            elif self.current_game == GAME_APPLE:
                self._draw_apple_tree()
            elif self.current_game == GAME_DICE:
                self._draw_dice()
            else:
                self._draw_money_tree()
            self._draw_result()
        elif self.state == 'celebration':
            self._draw_celebration()

        # Particles on top
        if self.state != 'celebration' or self.celebration_alpha < 1.0:
            self.particles.draw(self.screen)

        # Always draw game navigator and wallet
        self._draw_navigator()
        self._draw_wallet()

        self.screen = surf  # restore original screen
        self._scale_to_window()
        pygame.display.flip()

    def _draw_background_decoration(self):
        """Draw rich multi-layered background with texture and depth"""
        glow = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

        for r in range(430, 0, -5):
            ratio = r / 430
            a = int(24 * (1 - ratio))
            r_col = int(200 + 55 * ratio)
            g = int(30 + 25 * ratio)
            b = int(20 - 10 * ratio)
            pygame.draw.circle(glow, (r_col, g, b, a), (cx, cy), r)
        self.screen.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        bloom = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for r in range(260, 0, -7):
            a = int(11 * (1 - r / 260))
            pygame.draw.circle(bloom, (255, 185, 85, a), (cx, int(cy * 0.30)), r)
        self.screen.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        bottom = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for r in range(320, 0, -6):
            ratio = r / 320
            a = int(14 * (1 - ratio))
            pygame.draw.circle(bottom, (160, 25, 18, a), (cx, WINDOW_HEIGHT + 40), r)
        self.screen.blit(bottom, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        corner = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for r in range(160, 0, -10):
            a = int(6 * (1 - r / 160))
            pygame.draw.circle(corner, (180, 80, 40, a), (50, 50), r)
            pygame.draw.circle(corner, (180, 80, 40, a), (WINDOW_WIDTH - 50, 50), r)
        self.screen.blit(corner, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        self._draw_background_texture()

    def _draw_background_texture(self):
        """Draw colorful scattered confetti scraps in background-only areas"""
        if not hasattr(self, '_tex_surface'):
            colors = [
                (255, 215, 0, 55), (255, 140, 100, 45), (255, 105, 180, 40),
                (135, 206, 235, 35), (152, 251, 152, 38), (255, 160, 122, 42),
                (221, 160, 221, 36), (255, 218, 185, 48), (240, 230, 140, 42),
                (176, 224, 230, 35), (255, 182, 193, 40), (230, 190, 255, 35),
                (255, 228, 181, 48), (175, 238, 238, 38), (250, 128, 114, 40),
            ]

            self._tex_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

            for _ in range(300):
                x = random.randint(0, WINDOW_WIDTH)
                y = random.randint(0, WINDOW_HEIGHT)

                dist_center = math.hypot(x - cx, y - cy)
                if dist_center < 390:
                    continue
                dist_bloom = math.hypot(x - cx, y - cy * 0.30)
                if dist_bloom < 240:
                    continue
                dist_bottom = math.hypot(x - cx, y - (WINDOW_HEIGHT + 40))
                if dist_bottom < 290:
                    continue

                color = random.choice(colors)
                size = random.randint(3, 8)

                shape_roll = random.random()
                if shape_roll < 0.55:
                    w = random.randint(size, size * 3)
                    h = random.randint(2, size)
                    pygame.draw.rect(self._tex_surface, color, (x, y, w, h))
                elif shape_roll < 0.80:
                    pts = [(x, y), (x + size, y), (x + size // 2, y + size)]
                    pygame.draw.polygon(self._tex_surface, color, pts)
                elif shape_roll < 0.93:
                    pygame.draw.circle(self._tex_surface, color, (x, y), random.randint(2, 4))
                else:
                    w = random.randint(size, size * 2)
                    pygame.draw.rect(self._tex_surface, color, (x, y, size, w))

        self.screen.blit(self._tex_surface, (0, 0))

    def _draw_menu(self):
        """Draw the game selection menu"""
        cx = WINDOW_WIDTH // 2
        bob_y = int(math.sin(self.title_bob * 1.5) * 5)
        game_name = GAME_NAMES[self.current_game]
        title_color = hex_to_rgb(COLORS['gold'])

        glow_surf = self.font_title.render(game_name, True, (0, 0, 0))
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            r = glow_surf.get_rect(center=(cx + dx, 120 + bob_y + dy))
            self.screen.blit(glow_surf, r)

        title_shadow = self.font_title.render(game_name, True, (60, 50, 30))
        shadow_rect = title_shadow.get_rect(center=(cx + 2, 122 + bob_y))
        self.screen.blit(title_shadow, shadow_rect)

        title_surf = self.font_title.render(game_name, True, title_color)
        title_rect = title_surf.get_rect(center=(cx, 120 + bob_y))
        self.screen.blit(title_surf, title_rect)

        descripts = {
            GAME_SCRATCH: '刮开三张卡片，寻找成双成对的奖品',
            GAME_APPLE: '摇动苹果树，接住掉落的宝贝',
            GAME_MONEY: '培养摇钱树，满足需求获得奖励',
            GAME_LOTTERY: '选3个数字，位置相同就中奖',
            GAME_LADDER: '爬梯子存钱，风险递增',
            GAME_DICE: '掷三颗骰子，点数之和×2=奖金',
            GAME_MATH: '算式快速变化，点击停止看结果',
            GAME_MARBLE: '弹珠落下，看运气赢奖金',
            GAME_COIN: '1%概率立起+500，正面+15，反面-10',
            GAME_HORSE: '30格赛道，红马 vs 蓝马，先到终点赢奖金',
            GAME_BOMB: '剪断正确的电线，拆除炸弹！',
            GAME_CAVE: '选择一个山洞，金币会随机投入',
            GAME_MAZE: '三次左/右选择，探索迷宫尽头',
            GAME_FISHING: '抛竿等待，钓到珍稀鱼类',
            GAME_STRENGTH: '疯狂按空格，看谁先到目标力量',
            GAME_EXAM: '逐题判断对错，批阅试卷看成绩',
            GAME_FLYING_CHESS: '红蓝对决，50格赛道先到终点赢',
        }
        sub_text = descripts.get(self.current_game, '抛竿等待，钓到珍稀鱼类')
        sub_surf = self.font_subtitle.render(sub_text, True, hex_to_rgb(COLORS['text_secondary']))
        sub_rect = sub_surf.get_rect(center=(cx, 175))
        self.screen.blit(sub_surf, sub_rect)

        legend_methods = {
            GAME_SCRATCH: self._draw_scratch_legend,
            GAME_APPLE: self._draw_apple_legend,
            GAME_MONEY: self._draw_money_legend,
            GAME_BOMB: self._draw_bomb_legend,
            GAME_CAVE: self._draw_cave_legend,
            GAME_MAZE: self._draw_maze_legend,
            GAME_FISHING: self._draw_fishing_legend,
            GAME_LOTTERY: self._draw_lottery_legend,
            GAME_LADDER: self._draw_ladder_legend,
            GAME_DICE: self._draw_dice_legend,
            GAME_MATH: self._draw_math_legend,
            GAME_MARBLE: self._draw_marble_legend,
            GAME_COIN: self._draw_coin_legend,
            GAME_HORSE: self._draw_horse_legend,
            GAME_TRASH: self._draw_trash_legend,
            GAME_WOODEN_FISH: self._draw_wooden_fish_legend,
            GAME_WHEEL: self._draw_wheel_legend,
            GAME_GO_OUT: self._draw_go_out_legend,
            GAME_STRENGTH: self._draw_strength_legend,
            GAME_EXAM: self._draw_exam_legend,
            GAME_FLYING_CHESS: self._draw_flying_chess_legend,
        }
        draw_legend = legend_methods.get(self.current_game)
        if draw_legend:
            draw_legend()

        pulse = 0.5 + 0.5 * math.sin(self.title_pulse * 2)
        alpha = int(150 + 105 * pulse)
        cost_map = {
            GAME_SCRATCH: SCRATCH_TICKET_COST, GAME_APPLE: TREE_SHAKE_COST, GAME_MONEY: 0,
            GAME_BOMB: BOMB_DEFUSE_COST, GAME_CAVE: CAVE_ENTRY_COST, GAME_MAZE: MAZE_ENTRY_COST,
            GAME_FISHING: FISHING_ENTRY_COST, GAME_LOTTERY: LOTTERY_ENTRY_COST,
            GAME_LADDER: LADDER_ENTRY_COST, GAME_DICE: DICE_ENTRY_COST,
            GAME_MATH: MATH_ENTRY_COST, GAME_MARBLE: MARBLE_ENTRY_COST,
            GAME_COIN: COIN_ENTRY_COST,
            GAME_HORSE: HORSE_ENTRY_COST,
            GAME_TRASH: TRASH_ENTRY_COST,
            GAME_WOODEN_FISH: WOODEN_FISH_ENTRY_COST,
            GAME_WHEEL: WHEEL_ENTRY_COST,
            GAME_GO_OUT: GO_OUT_ENTRY_COST,
            GAME_STRENGTH: STRENGTH_ENTRY_COST,
            GAME_EXAM: EXAM_ENTRY_COST,
            GAME_FLYING_CHESS: FLYING_CHESS_ENTRY_COST,
        }
        cost_val = cost_map[self.current_game]
        cost_text = '免费' if cost_val == 0 else f'票价: ¥{cost_val}'

        hint_rect = pygame.Rect(cx - 120, 415, 240, 42)
        hint_s = pygame.Surface((hint_rect.width, hint_rect.height), pygame.SRCALPHA)
        hint_s.fill((255, 215, 0, int(alpha * 0.12)))
        self.screen.blit(hint_s, hint_rect)
        pygame.draw.rect(self.screen, hex_to_rgb(COLORS['gold_dark']), hint_rect, 1, border_radius=12)

        hint_surf = self.font_hint.render(f'{cost_text} - 点击或按空格开始',
                                          True, hex_to_rgb(COLORS['gold']))
        hint_surf.set_alpha(alpha)
        hint_rect_center = hint_surf.get_rect(center=(cx, 436))
        self.screen.blit(hint_surf, hint_rect_center)

        if not self.wallet.can_afford(cost_val):
            warn_surf = self.font_hint.render('金钱不足！', True, hex_to_rgb(COLORS['red_primary']))
            warn_rect = warn_surf.get_rect(center=(cx, 470))
            self.screen.blit(warn_surf, warn_rect)

        self._draw_sparkles()

    def _leg_text(self, text, x, y, color=COLORS['text_secondary'], size=17):
        """Draw legend text with dark shadow for readability on glowing background"""
        font = pygame.font.SysFont('microsoftyahei', size)
        shadow = font.render(text, True, (10, 4, 2))
        self.screen.blit(shadow, (x + 1, y + 1))
        surf = font.render(text, True, hex_to_rgb(color))
        self.screen.blit(surf, (x, y))

    def _draw_scratch_legend(self):
        """Draw prize legend for scratch cards"""
        legend_y = 210
        cx2 = WINDOW_WIDTH // 2 - 160
        for prize_key, prize_data in PRIZES.items():
            icon_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(icon_surf, hex_to_rgb(prize_data['color']), (8, 8), 7)
            pygame.draw.circle(icon_surf, hex_to_rgb(prize_data['accent_color']), (8, 8), 7, 1)
            self.screen.blit(icon_surf, (cx2, legend_y + 1))
            self._leg_text(prize_data['name'], cx2 + 22, legend_y, prize_data['color'])
            prob_text = f"{int(prize_data['probability'] * 100)}%"
            self._leg_text(prob_text, cx2 + 130, legend_y)
            legend_y += 30

    def _draw_apple_legend(self):
        """Legend for apple tree shake game"""
        from src.settings import TREE_DROPS
        legend_y = 210
        cx2 = WINDOW_WIDTH // 2 - 160
        for drop_key, drop_data in TREE_DROPS.items():
            icon_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(icon_surf, hex_to_rgb(drop_data['color']), (8, 8), 7)
            self.screen.blit(icon_surf, (cx2, legend_y + 1))
            self._leg_text(drop_data['name'], cx2 + 22, legend_y, drop_data['color'])
            prob_text = f"{int(drop_data['probability'] * 100)}%"
            val_text = f"+¥{drop_data['value']}" if drop_data['value'] > 0 else ('清零!' if drop_key == 'bug' else '结束')
            self._leg_text(f"{prob_text} {val_text}", cx2 + 100, legend_y)
            legend_y += 28
        self._leg_text(f'每次 ¥{TREE_SHAKE_COST} 摇{MAX_SHAKES}次', cx2, legend_y + 5, COLORS['gold'])

    def _draw_money_legend(self):
        """Legend for money tree cultivation game"""
        from src.money_tree import ACTIONS, QUICK_DEMAND_MIN, QUICK_DEMAND_MAX
        legend_y = 210
        cx2 = WINDOW_WIDTH // 2 - 160
        for action in ACTIONS:
            icon_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(icon_surf, hex_to_rgb(action['color']), (8, 8), 7)
            self.screen.blit(icon_surf, (cx2, legend_y + 1))
            self._leg_text(f"{action['icon']} {action['name']}", cx2 + 22, legend_y, action['color'])
            self._leg_text(f"¥{action['cost']}", cx2 + 160, legend_y)
            legend_y += 28
        self._leg_text(f'速催需求 ¥{QUICK_DEMAND_MIN}~{QUICK_DEMAND_MAX}', cx2, legend_y + 5, COLORS['gold_dark'])
        legend_y += 32
        for text, color in [('20% 无奖励', COLORS['text_secondary']), ('50% 免费刮刮乐', COLORS['gold']), ('30% ¥50~200', COLORS['success'])]:
            self._leg_text(text, cx2, legend_y, color)
            legend_y += 24
        self._leg_text('免费游玩，按需付费', cx2, legend_y + 5, COLORS['gold'])

    def _draw_bomb_legend(self):
        """Draw legend for bomb game"""
        legend_y = 210
        cx2 = WINDOW_WIDTH // 2 - 160
        for name, color, info in [('电线 绿', '#33FF33', '1/3'), ('电线 黄', '#FFCC00', '1/3'), ('电线 蓝', '#3366FF', '1/3')]:
            pygame.draw.line(self.screen, hex_to_rgb(color), (cx2, legend_y + 8), (cx2 + 14, legend_y + 8), 5)
            self._leg_text(f'{name}  {info} 概率正确', cx2 + 22, legend_y, color)
            legend_y += 28
        self._leg_text(f'奖励: +¥{BOMB_REWARD}', cx2, legend_y, COLORS['gold'])

    def _draw_sparkles(self):
        """Draw animated sparkle particles"""
        sparkle_colors = [hex_to_rgb(COLORS['gold']), hex_to_rgb(COLORS['gold_light']),
                          hex_to_rgb('#FFFFFF'), hex_to_rgb(COLORS['gold_pale'])]
        for i, sparkle in enumerate(self.title_sparkles):
            pos = sparkle['pos']
            phase = sparkle['phase']
            speed = sparkle['speed']
            color = sparkle_colors[i % len(sparkle_colors)]

            x = pos[0] + math.sin(self.title_bob * speed + phase) * 22
            y = pos[1] + math.cos(self.title_bob * speed * 0.7 + phase) * 18

            pulse = 0.5 + 0.5 * math.sin(self.title_bob * speed * 3 + phase)
            size = max(1, int(1 + pulse * 2.5))
            alpha = int(120 + 135 * pulse)

            base = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            for ring in range(size, 0, -1):
                a = int(alpha * ring / size * 0.4)
                pygame.draw.circle(base, (*color[:3], a), (size * 2, size * 2), ring * 2)
            self.screen.blit(base, (int(x) - size * 2, int(y) - size * 2))

    def _draw_scratching(self):
        """Draw scratch card game screen"""
        title_surf = self.font_title.render('成 双 成 对', True, hex_to_rgb(COLORS['gold']))
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 60))
        self.screen.blit(title_surf, title_rect)

        scratched_count = sum(1 for card in self.cards if card.scratched)
        if scratched_count > 0:
            hint_text = f'已刮开 {scratched_count}/3'
        else:
            hint_text = '用鼠标刮开三张卡片'

        hint_surf = self.font_hint.render(hint_text, True, hex_to_rgb(COLORS['text_secondary']))
        hint_rect = hint_surf.get_rect(center=(WINDOW_WIDTH // 2, 110))
        self.screen.blit(hint_surf, hint_rect)

        for card in self.cards:
            card.draw(self.screen)

    def _draw_apple_tree(self):
        """Draw apple tree game screen"""
        self.apple_tree.draw(self.screen)

    def _draw_money_tree(self):
        """Draw money tree game screen"""
        self.money_tree.draw(self.screen)

    def _draw_bomb(self):
        """Draw bomb game screen"""
        self.bomb_game.draw(self.screen)

    def _draw_cave(self):
        """Draw cave game screen"""
        self.cave_game._draw_hud(self.screen)
        self.cave_game.draw(self.screen)

    def _draw_cave_legend(self):
        """Draw legend for cave game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)
        from src.settings import CAVE_COIN_TYPES
        for coin_type, coin_data in CAVE_COIN_TYPES.items():
            prob_text = f"{int(coin_data['probability'] * 100)}%"
            value_text = f"+¥{coin_data['value']}"

            # Coin icon
            coin_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(coin_surf, hex_to_rgb(coin_data['color']), (8, 8), 7)
            self.screen.blit(coin_surf, (WINDOW_WIDTH // 2 - 150, legend_y))

            name_surf = font.render(coin_data['name'], True, hex_to_rgb(coin_data['color']))
            self.screen.blit(name_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))

            info_surf = font.render(f"{prob_text} {value_text}", True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(info_surf, (WINDOW_WIDTH // 2 + 20, legend_y - 2))

            legend_y += 28

        # 5 coins info
        from src.settings import CAVE_COIN_MIN, CAVE_COIN_MAX
        five_surf = font.render(f'共投掷 {CAVE_COIN_MIN}~{CAVE_COIN_MAX} 枚硬币', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(five_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_maze(self):
        """Draw maze game screen"""
        self.maze_game.draw(self.screen)

    def _draw_maze_legend(self):
        """Draw legend for maze game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        for prize_key, prize_data in MAZE_PRIZES.items():
            if prize_data['count'] <= 0:
                continue

            color = hex_to_rgb(prize_data['color'])
            count_text = f"x{prize_data['count']}" if prize_data['count'] > 1 else ''

            # Icon
            prize_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(prize_surf, color, (8, 8), 7)
            self.screen.blit(prize_surf, (WINDOW_WIDTH // 2 - 150, legend_y))

            name_surf = font.render(f"{prize_data['name']} {count_text}", True, color)
            self.screen.blit(name_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))

            if prize_data['value'] > 0:
                value_surf = font.render(f"+¥{prize_data['value']}", True, hex_to_rgb(COLORS['text_secondary']))
            else:
                value_surf = font.render('无奖励', True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(value_surf, (WINDOW_WIDTH // 2 + 20, legend_y - 2))

            legend_y += 28

        cost_surf = font.render(f'入场费: ¥{MAZE_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_fishing(self):
        """Draw fishing game screen"""
        self.fishing_game.draw(self.screen)

    def _draw_fishing_legend(self):
        """Draw legend for fishing game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        for fish_key, fish_data in FISH_TYPES.items():
            color = hex_to_rgb(fish_data['color'])
            prob_text = f"{int(fish_data['probability'] * 100)}%"

            # Fish icon
            fish_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(fish_surf, color, (8, 8), 7)
            self.screen.blit(fish_surf, (WINDOW_WIDTH // 2 - 150, legend_y))

            name_surf = font.render(fish_data['name'], True, color)
            self.screen.blit(name_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))

            if fish_data['value'] > 0:
                info_surf = font.render(f"{prob_text} +¥{fish_data['value']}", True, hex_to_rgb(COLORS['text_secondary']))
            else:
                info_surf = font.render(f"{prob_text} 无价值", True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(info_surf, (WINDOW_WIDTH // 2 + 20, legend_y - 2))

            legend_y += 24

        cost_surf = font.render(f'入场费: ¥{FISHING_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_lottery(self):
        """Draw lottery game screen"""
        self.lottery_game.draw(self.screen)

    def _draw_lottery_legend(self):
        """Draw legend for lottery game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        labels = {1: '对 1 个', 2: '对 2 个', 3: '对 3 个'}
        for count, prize in LOTTERY_PRIZES.items():
            color = hex_to_rgb(COLORS['gold'])
            prize_surf = font.render(labels.get(count, f'中{count}个'), True, color)
            self.screen.blit(prize_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))

            value_surf = font.render(f'+¥{prize}', True, color)
            self.screen.blit(value_surf, (WINDOW_WIDTH // 2 + 40, legend_y - 2))

            legend_y += 28

        cost_surf = font.render(f'票价: ¥{LOTTERY_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_ladder(self):
        """Draw ladder game screen"""
        self.ladder_game.draw(self.screen)

    def _draw_ladder_legend(self):
        """Draw legend for ladder game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        steps = [
            ('第 1 步', '5%', '¥15~25'),
            ('第 2 步', '10%', '¥15~25'),
            ('第 3 步', '15%', '¥15~25'),
            ('第 4 步', '20%', '¥15~25'),
            ('第 5 步', '25%', '¥15~25'),
        ]
        for step, fall, save in steps:
            step_surf = font.render(f'{step} 坠落{fall} 存{save}', True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(step_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            legend_y += 24

        risk_surf = font.render('下梯子 = 取出所有存款', True, hex_to_rgb(COLORS['success']))
        self.screen.blit(risk_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 5))

        fall_risk = font.render('坠落 = 存款清零', True, hex_to_rgb('#FF6B6B'))
        self.screen.blit(fall_risk, (WINDOW_WIDTH // 2 - 125, legend_y + 30))

        cost_surf = font.render(f'票价: ¥{LADDER_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 60))

    def _draw_dice(self):
        """Draw dice game screen"""
        self.dice_game.draw(self.screen)

    def _draw_dice_legend(self):
        """Draw legend for dice game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        combos = [
            ('三颗骰子点数之和', '×2 = 奖金', COLORS['gold']),
        ]
        for name, mult, color in combos:
            name_surf = font.render(name, True, hex_to_rgb(color))
            self.screen.blit(name_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            mult_surf = font.render(mult, True, hex_to_rgb(COLORS['gold']))
            self.screen.blit(mult_surf, (WINDOW_WIDTH // 2 + 60, legend_y - 2))
            legend_y += 28

        cost_surf = font.render(f'票价: ¥{DICE_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_math_game(self):
        """Draw math game screen"""
        self.math_game.draw(self.screen)

    def _draw_math_legend(self):
        """Draw legend for math game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        ops = [
            ('+', '加法', COLORS['text_secondary']),
            ('-', '减法', COLORS['text_secondary']),
            ('×', '乘法', COLORS['text_secondary']),
            ('÷', '除法', COLORS['text_secondary']),
        ]
        for op, name, color in ops:
            op_surf = font.render(f'{op} {name}', True, hex_to_rgb(color))
            self.screen.blit(op_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            legend_y += 24

        rule_surf = font.render('结果向上取整 × 3 = 奖金', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(rule_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 5))
        legend_y += 24

        cost_surf = font.render(f'票价: ¥{MATH_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_marble_game(self):
        """Draw marble game screen"""
        self.marble_game.draw(self.screen)

    def _draw_marble_legend(self):
        """Draw legend for marble game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        from src.marble_game import LANDING_SPOTS
        for spot in LANDING_SPOTS:
            color = hex_to_rgb(spot['color'])
            icon_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(icon_surf, color, (8, 8), 7)
            self.screen.blit(icon_surf, (WINDOW_WIDTH // 2 - 150, legend_y))

            name_surf = font.render(f"¥{spot['value']}", True, color)
            self.screen.blit(name_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            legend_y += 24

        cost_surf = font.render(f'票价: ¥{MARBLE_ENTRY_COST} 投4颗弹珠', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_coin_game(self):
        """Draw coin toss game screen"""
        self.coin_game.draw(self.screen)

    def _draw_coin_legend(self):
        """Draw legend for coin toss game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        outcomes = [
            ('硬币立起', '1%', '+¥500', COLORS['gold']),
            ('正面', '49.5%', '+¥15', COLORS['success']),
            ('反面', '49.5%', '-¥10', COLORS['red_primary']),
        ]
        for name, prob, reward, color in outcomes:
            name_surf = font.render(name, True, hex_to_rgb(color))
            self.screen.blit(name_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))

            prob_surf = font.render(f'{prob} 概率  {reward}', True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(prob_surf, (WINDOW_WIDTH // 2 + 20, legend_y - 2))
            legend_y += 28

        free_surf = font.render('免费无限次投掷', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(free_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_horse_game(self):
        """Draw horse racing game screen"""
        self.horse_game.draw(self.screen)

    def _draw_trash_game(self):
        """Draw trash collection game screen"""
        self.trash_game.draw(self.screen)

    def _draw_wooden_fish_game(self):
        """Draw wooden fish game screen"""
        self.wooden_fish_game.draw(self.screen)

    def _draw_wheel_game(self):
        """Draw lucky wheel game screen"""
        self.wheel_game.draw(self.screen)

    def _draw_go_out_game(self):
        """Draw go out game screen"""
        self.go_out_game.draw(self.screen)

    def _draw_strength_game(self):
        """Draw strength competition game screen"""
        self.strength_game.draw(self.screen)

    def _draw_exam_game(self):
        """Draw exam grading game screen"""
        self.exam_game.draw(self.screen)

    def _draw_flying_chess_game(self):
        """Draw flying chess game screen"""
        self.flying_chess_game.draw(self.screen)

    def _draw_horse_legend(self):
        """Draw legend for horse racing game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        moves = [
            ('走4步', '5%', '冲刺', COLORS['gold']),
            ('走3步', '10%', '快跑', COLORS['warning']),
            ('走2步', '30%', '普通', COLORS['text_secondary']),
            ('走1步', '50%', '慢走', COLORS['text_muted']),
            ('停步', '5%', '原地不动', COLORS['red_primary']),
        ]
        for move, prob, desc, color in moves:
            move_surf = font.render(move, True, hex_to_rgb(color))
            self.screen.blit(move_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            prob_surf = font.render(f'{prob} {desc}', True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(prob_surf, (WINDOW_WIDTH // 2 + 30, legend_y - 2))
            legend_y += 28

        legend_y += 8
        rewards = [
            ('红马先到', f'+¥{HORSE_WIN_MIN}~{HORSE_WIN_MAX}', COLORS['gold']),
            ('蓝马先到', '无奖励', COLORS['text_secondary']),
            ('同时到达', f'+¥{HORSE_DRAW_COST}', COLORS['info']),
        ]
        for desc, reward, color in rewards:
            desc_surf = font.render(desc, True, hex_to_rgb(color))
            self.screen.blit(desc_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            reward_surf = font.render(reward, True, hex_to_rgb(COLORS['gold']))
            self.screen.blit(reward_surf, (WINDOW_WIDTH // 2 + 40, legend_y - 2))
            legend_y += 24

        cost_surf = font.render(f'票价: ¥{HORSE_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_trash_legend(self):
        """Draw legend for trash collection game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        for trash_type in TRASH_TYPES:
            trash_surf = font.render(trash_type, True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(trash_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            legend_y += 24

        reward_surf = font.render(f'奖励: ¥50~200', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(reward_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 5))
        legend_y += 24

        cost_surf = font.render(f'票价: ¥{TRASH_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_wooden_fish_legend(self):
        """Draw legend for wooden fish game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        info = [
            ('点击木鱼', '获得功德', COLORS['text_secondary']),
            ('连击加速', '奖励翻倍', COLORS['gold']),
        ]
        for name, desc, color in info:
            name_surf = font.render(name, True, hex_to_rgb(color))
            self.screen.blit(name_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            desc_surf = font.render(desc, True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(desc_surf, (WINDOW_WIDTH // 2 + 40, legend_y - 2))
            legend_y += 28

        cost_surf = font.render(f'票价: ¥{WOODEN_FISH_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_wheel_legend(self):
        """Draw legend for lucky wheel game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        from src.wheel_game import SEGMENTS
        for seg in SEGMENTS:
            color = hex_to_rgb(seg['color'])
            name_surf = font.render(seg['label'], True, color)
            self.screen.blit(name_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            value_surf = font.render(f"¥{seg['value']}" if seg['value'] > 0 else '谢谢惠顾', True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(value_surf, (WINDOW_WIDTH // 2 + 40, legend_y - 2))
            legend_y += 24

        cost_surf = font.render(f'票价: ¥{WHEEL_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_go_out_legend(self):
        """Draw legend for go out game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        outcomes = [
            ('晴天出门', '好运', '+¥100~300', COLORS['gold']),
            ('雨天出门', '倒霉', '-¥50~100', COLORS['red_primary']),
        ]
        for weather, luck, reward, color in outcomes:
            name_surf = font.render(weather, True, hex_to_rgb(color))
            self.screen.blit(name_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            info_surf = font.render(f'{luck} {reward}', True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(info_surf, (WINDOW_WIDTH // 2 + 40, legend_y - 2))
            legend_y += 28

        predict_surf = font.render(f'预测天气: ¥{GO_OUT_PREDICT_COST}', True, hex_to_rgb(COLORS['info']))
        self.screen.blit(predict_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 5))
        legend_y += 24

        cost_surf = font.render(f'票价: ¥{GO_OUT_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_strength_legend(self):
        """Draw legend for strength competition game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        powers = [
            ('+1', '35%', COLORS['text_secondary']),
            ('+2', '30%', COLORS['success']),
            ('+3', '15%', COLORS['info']),
            ('+4', '10%', COLORS['warning']),
            ('+5', '5%', COLORS['gold_dark']),
            ('+10', '5%', COLORS['gold']),
        ]
        for pts, prob, color in powers:
            pts_surf = font.render(pts, True, hex_to_rgb(color))
            self.screen.blit(pts_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            prob_surf = font.render(f'{prob} 概率', True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(prob_surf, (WINDOW_WIDTH // 2 + 40, legend_y - 2))
            legend_y += 24

        target_surf = font.render('目标: 80~150 力量', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(target_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 5))
        legend_y += 24

        reward_surf = font.render('奖励: ¥300~500', True, hex_to_rgb(COLORS['success']))
        self.screen.blit(reward_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 5))
        legend_y += 24

        cost_surf = font.render(f'票价: ¥{STRENGTH_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_exam_legend(self):
        """Draw legend for exam grading game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 17, bold=True)

        values = [5, 10, 20, 50, 100]
        for val in values:
            val_surf = font.render(f'Q: ¥{val}', True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(val_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            legend_y += 24

        pass_surf = font.render(f'及格线: ¥60', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(pass_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 5))
        legend_y += 24

        cost_surf = font.render(f'票价: ¥{EXAM_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_flying_chess_legend(self):
        """Draw legend for flying chess game"""
        legend_y = 210
        font = pygame.font.SysFont('microsoftyahei', 16)

        rules = [
            ('骰子特效', '+10(1%) ×2(5%) ÷2(4%)', COLORS['text_secondary']),
            ('红天', '在红色格子后退5步', '#FF5E5E'),
            ('蓝天', '在蓝色格子前进5步', '#5E8AFF'),
            ('灰天', '在灰色格子回起点', '#AAAAAA'),
        ]
        for name, desc, color in rules:
            name_surf = font.render(name, True, hex_to_rgb(color))
            self.screen.blit(name_surf, (WINDOW_WIDTH // 2 - 125, legend_y - 2))
            desc_surf = font.render(desc, True, hex_to_rgb(COLORS['text_secondary']))
            self.screen.blit(desc_surf, (WINDOW_WIDTH // 2 + 40, legend_y - 2))
            legend_y += 24

        win_surf = font.render('先到终点赢 ¥200', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(win_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 5))
        legend_y += 24

        cost_surf = font.render(f'票价: ¥{FLYING_CHESS_ENTRY_COST}', True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(cost_surf, (WINDOW_WIDTH // 2 - 125, legend_y + 10))

    def _draw_result(self):
        """Draw result overlay with polished styling"""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay_a = min(200, int(self.state_timer * 350))
        overlay.fill((0, 0, 0, overlay_a))
        self.screen.blit(overlay, (0, 0))

        if self.result_scale > 0.01:
            text_surf = self.font_result.render(self.result_text, True,
                                                hex_to_rgb(self.result_color))
            shadow = self.font_result.render(self.result_text, True, (0, 0, 0))
            s = max(1, int(text_surf.get_width() * self.result_scale))
            h = max(1, int(text_surf.get_height() * self.result_scale))
            scaled = pygame.transform.smoothscale(text_surf, (s, h))
            sd = pygame.transform.smoothscale(shadow, (s + 4, h + 4))
            rcx, rcy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30
            sd.set_alpha(80)
            self.screen.blit(sd, sd.get_rect(center=(rcx, rcy + 2)))
            self.screen.blit(scaled, scaled.get_rect(center=(rcx, rcy)))

        if self.state_timer > 0.5:
            draw_breathing_hint(self.screen, '点击任意位置返回', self.font_hint,
                               COLORS['text_secondary'],
                               (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60),
                               self.state_timer, speed=4)

    def _draw_celebration(self):
        """Draw celebration animation with glow effects"""
        if self.celebration_phase == 'text':
            if self.current_game == GAME_SCRATCH:
                self._draw_scratching()
            elif self.current_game == GAME_APPLE:
                self._draw_apple_tree()
            elif self.current_game == GAME_DICE:
                self._draw_dice()
            elif self.current_game == GAME_MATH:
                self._draw_math_game()
            elif self.current_game == GAME_MARBLE:
                self._draw_marble_game()
            elif self.current_game == GAME_COIN:
                self._draw_coin_game()
            elif self.current_game == GAME_HORSE:
                self._draw_horse_game()
            else:
                self._draw_money_tree()

            text_alpha = min(255, int(self.celebration_timer * 400))
            cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30

            shadow_s = self.font_result.render('成 双 成 对 ！', True, (0, 0, 0))
            shadow_s.set_alpha(min(120, text_alpha // 2))
            self.screen.blit(shadow_s, shadow_s.get_rect(center=(cx + 2, cy + 2)))

            celebration_surf = self.font_result.render('成 双 成 对 ！', True,
                                                       hex_to_rgb(COLORS['gold']))
            celebration_surf.set_alpha(text_alpha)
            self.screen.blit(celebration_surf, celebration_surf.get_rect(center=(cx, cy)))

            sub_surf = self.font_subtitle.render('恭喜中奖！', True,
                                                 hex_to_rgb(COLORS['gold_light']))
            sub_surf.set_alpha(text_alpha)
            self.screen.blit(sub_surf, sub_surf.get_rect(center=(cx, cy + 55)))

            self.particles.draw(self.screen)

        elif self.celebration_phase == 'fadeout':
            self._draw_scratching()
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((5, 0, 15, int(255 * self.celebration_alpha)))
            self.screen.blit(overlay, (0, 0))

        elif self.celebration_phase == 'black':
            self.screen.fill((5, 0, 15))

        elif self.celebration_phase == 'fadein':
            self._draw_background_decoration()
            self._draw_menu()
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((5, 0, 15, int(255 * self.celebration_alpha)))
            self.screen.blit(overlay, (0, 0))

    def _handle_navigator_click(self, mouse_pos: tuple) -> bool:
        """Check if click is on navigator arrows. Returns True if handled."""
        y = WINDOW_HEIGHT - 42
        left_rect = pygame.Rect(10, y - 20, 40, 40)
        if left_rect.collidepoint(mouse_pos):
            self._switch_game((self.current_game - 1) % 21)
            return True
        right_rect = pygame.Rect(WINDOW_WIDTH - 50, y - 20, 40, 40)
        if right_rect.collidepoint(mouse_pos):
            self._switch_game((self.current_game + 1) % 21)
            return True
        return False

    def _draw_navigator(self):
        """Draw polished game navigator with custom arrow buttons"""
        y = WINDOW_HEIGHT - 42
        font_nav = pygame.font.SysFont('microsoftyahei', 18, bold=True)

        nav_bg = pygame.Rect(20, WINDOW_HEIGHT - 60, WINDOW_WIDTH - 40, 44)
        nav_s = pygame.Surface((nav_bg.width, nav_bg.height), pygame.SRCALPHA)
        nav_s.fill((255, 255, 255, 6))
        self.screen.blit(nav_s, nav_bg)
        pygame.draw.rect(self.screen, hex_to_rgb(COLORS['panel_border']), nav_bg, 1, border_radius=14)

        game_name = GAME_NAMES[self.current_game]
        current_surf = font_nav.render(game_name, True, hex_to_rgb(COLORS['gold']))
        self.screen.blit(current_surf, current_surf.get_rect(center=(WINDOW_WIDTH // 2, y)))

        mouse_pos = get_mouse_pos()

        l_cx, l_cy = 30, int(y)
        l_hover = math.hypot(mouse_pos[0] - l_cx, mouse_pos[1] - l_cy) < 18
        self._draw_arrow_button(l_cx, l_cy, 'left', l_hover)

        r_cx, r_cy = WINDOW_WIDTH - 30, int(y)
        r_hover = math.hypot(mouse_pos[0] - r_cx, mouse_pos[1] - r_cy) < 18
        self._draw_arrow_button(r_cx, r_cy, 'right', r_hover)

        hint_font = pygame.font.SysFont('microsoftyahei', 12)
        hint_surf = hint_font.render('\u2190 \u2192 \u5207\u6362 | F11 \u5168\u5c4f', True, hex_to_rgb(COLORS['text_muted']))
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(WINDOW_WIDTH // 2, y + 20)))

    def _draw_arrow_button(self, cx, cy, direction, hover=False):
        """Draw a single polished circle arrow button with glow"""
        glow_r = 24
        if hover:
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            for r in range(glow_r, 0, -3):
                a = int(50 * (1 - r / glow_r))
                pygame.draw.circle(glow_surf, (255, 200, 100, a), (glow_r, glow_r), r)
            self.screen.blit(glow_surf, (cx - glow_r, cy - glow_r), special_flags=pygame.BLEND_RGBA_ADD)

        bg_c = hex_to_rgb('#3a1818') if not hover else hex_to_rgb('#5a2828')
        shadow_c = hex_to_rgb('#1a0808')
        pygame.draw.circle(self.screen, shadow_c, (cx + 1, cy + 2), 16)
        pygame.draw.circle(self.screen, bg_c, (cx, cy), 16)

        pygame.draw.circle(self.screen, hex_to_rgb('#2a1010'), (cx, cy), 16, 1)

        border_c = hex_to_rgb(COLORS['gold']) if hover else hex_to_rgb(COLORS['gold_dark'])
        border_w = 3 if hover else 2
        pygame.draw.circle(self.screen, border_c, (cx, cy), 16, border_w)

        arrow_c = hex_to_rgb(COLORS['gold_light']) if hover else hex_to_rgb(COLORS['gold'])
        if direction == 'left':
            pts = [(cx + 5, cy - 8), (cx - 5, cy), (cx + 5, cy + 8)]
        else:
            pts = [(cx - 5, cy - 8), (cx + 5, cy), (cx - 5, cy + 8)]
        pygame.draw.polygon(self.screen, arrow_c, pts)
        pygame.draw.polygon(self.screen, hex_to_rgb(COLORS['gold_dark']), pts, 1)

    def _draw_wallet(self):
        """Draw wallet display with polished styling"""
        x = WINDOW_WIDTH - 173
        y = 8

        panel_rect = pygame.Rect(x, y, 163, 44)
        panel_s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        panel_s.fill((255, 255, 255, 5))
        self.screen.blit(panel_s, panel_rect)
        pygame.draw.rect(self.screen, hex_to_rgb(COLORS['gold_dark']), panel_rect, 2, border_radius=12)

        coin_cx, coin_cy = x + 28, y + 22
        pulse = 0.5 + 0.5 * math.sin(self.title_pulse * 1.8)
        coin_r = int(13 + pulse * 2.5)
        pygame.draw.circle(self.screen, hex_to_rgb(COLORS['gold_dark']), (coin_cx, coin_cy + 2), coin_r + 2)
        pygame.draw.circle(self.screen, hex_to_rgb(COLORS['gold']), (coin_cx, coin_cy), coin_r)
        pygame.draw.circle(self.screen, hex_to_rgb('#FFF3B0'), (coin_cx - 3, coin_cy - 4), max(3, coin_r // 3))

        money_surf = self.font_money.render(f'¥{self.wallet.balance}', True, hex_to_rgb(COLORS['gold_light']))
        self.screen.blit(money_surf, (x + 54, y + 10))

    async def run(self):
        """Main game loop - supports both desktop and web (via pygbag)"""
        while self.running:
            dt = self.clock.tick(TARGET_FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
            if IS_WEB:
                await asyncio.sleep(0)

        if not IS_WEB:
            pygame.quit()
            sys.exit()


def main():
    game = Game()
    asyncio.run(game.run())


if __name__ == '__main__':
    main()

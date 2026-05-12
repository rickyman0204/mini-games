"""Game constants and configuration for 成双成对 + 摇钱树"""

# Window settings
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 900
TARGET_FPS = 60

# Colors — 暗夜金辉主题（优化版）
COLORS = {
    # ── 背景层 ──
    'bg_primary': '#1c0e08',
    'bg_secondary': '#2f1818',
    'surface': '#3f2222',
    'overlay_bg': '#0a0505',

    # ── 卡片与面板 ──
    'card_bg': '#3d2020',
    'card_hover': '#4d2a2a',
    'card_active': '#5d3535',
    'card_border': '#6a4035',
    'panel_bg': '#2d1515',
    'panel_border': '#4a3030',

    # ── 金色系 ──
    'gold': '#ffe066',
    'gold_light': '#fff3b0',
    'gold_dark': '#c9a617',
    'gold_pale': '#fff8dc',

    # ── 文字 ──
    'text_primary': '#fff8dc',
    'text_secondary': '#e8c8a0',
    'text_muted': '#8b7060',

    # ── 功能色 ──
    'red_primary': '#ff5e5e',
    'red_light': '#ff8a8a',
    'red_dark': '#c94040',
    'success': '#51cf66',
    'success_light': '#82e89a',
    'success_dark': '#3da848',
    'warning': '#ffa94d',
    'warning_light': '#ffc078',
    'info': '#74c0fc',
    'info_light': '#a5d8ff',

    # ── 刮刮乐专用 ──
    'scratch_layer': '#c8960c',
    'silver': '#c8c8d0',
    'silver_dark': '#808090',

    # ── 苹果树专用 ──
    'tree_green': '#2e8b3a',
    'tree_dark': '#1a5c25',
    'tree_trunk': '#8b5a2b',
    'bug_color': '#7b2080',
    'bee_color': '#e8940a',
    'money_bag': '#ffe066',

    # ── 现实材质 ──
    'wood': '#9b6b44',
    'wood_dark': '#5c3717',
    'wood_light': '#d4b483',
    'green_light': '#86e8ae',
    'green_dark': '#2d6a4f',
    'green_deep': '#1a4a35',
    'stone': '#909090',
    'water': '#60d5f7',
    'water_dark': '#2e9cc4',
    'sky': '#93cceb',
    'sky_dark': '#5a9fc0',

    # ── 遮罩/覆盖 ──
    'overlay': (0, 0, 0, 180),
}

# Money system
INITIAL_WALLET = 300            # Starting money
SCRATCH_TICKET_COST = 5         # Cost per scratch card round
TREE_SHAKE_COST = 10            # Cost per money tree session
BOMB_DEFUSE_COST = 30           # Cost per bomb defusal round
BOMB_REWARD = 100               # Reward for defusing bomb correctly

# Scratch card prizes
PRIZES = {
    'gold': {
        'probability': 0.20,
        'name': '金币',
        'color': '#FFD700',
        'accent_color': '#FFA500',
    },
    'banknote': {
        'probability': 0.40,
        'name': '钱币',
        'color': '#2ECC71',
        'accent_color': '#27AE60',
    },
    'coin': {
        'probability': 0.40,
        'name': '硬币',
        'color': '#C0C0C0',
        'accent_color': '#808080',
    },
}

# Money Tree drop types with probabilities and money values
TREE_DROPS = {
    'money_bag': {
        'probability': 0.10,
        'name': '钱袋子',
        'color': '#FFD700',
        'value': 30,
        'icon': '💰',
    },
    'coin': {
        'probability': 0.20,
        'name': '钱币',
        'color': '#2ECC71',
        'value': 10,
        'icon': '',
    },
    'silver_coin': {
        'probability': 0.30,
        'name': '硬币',
        'color': '#C0C0C0',
        'value': 5,
        'icon': '',
    },
    'bug': {
        'probability': 0.20,
        'name': '虫子',
        'color': '#800080',
        'value': 0,  # Clears all money!
        'icon': '🐛',
    },
    'bee': {
        'probability': 0.20,
        'name': '蜜蜂',
        'color': '#FFA500',
        'value': 0,  # Ends session
        'icon': '🐝',
    },
}

# Scratch card layout
CARD_WIDTH = 180
CARD_HEIGHT = 220
CARD_SPACING = 30
CARD_MARGIN_TOP = 220

# Scratch thresholds
SCRATCH_THRESHOLD = 0.45

# Animation timings
ANIMATION_DURATION = 0.4
REVEAL_STAGGER = 0.15
PARTICLE_LIFETIME = 1.5

# Physics for celebration particles
PARTICLE_GRAVITY = 300
PARTICLE_COUNT_CELEBRATION = 80

# Celebration animation timings
CELEBRATION_TEXT_DURATION = 2.0
CELEBRATION_FADEOUT_DURATION = 1.5
CELEBRATION_BLACK_DURATION = 2.0
CELEBRATION_FADEIN_DURATION = 2.0

# Money Tree
MAX_SHAKES = 5
TREE_SHAKE_ANIM_DURATION = 0.6  # How long the shake animation lasts
TREE_DROP_FALL_DURATION = 1.0   # How long drops take to fall

# Bomb Defusal
BOMB_WIRES = ['green', 'yellow', 'blue']  # The three wire colors
BOMB_CUT_ANIM_DURATION = 0.8            # How long the cut animation takes
BOMB_REVEAL_DURATION = 1.5              # How long to show result

# Fishing Game
FISHING_ENTRY_COST = 30                     # Entry fee for fishing game
FISHING_CASTS_PER_ENTRY = 1                 # How many casts per entry fee
FISHING_MIN_TIME = 5                         # Minimum seconds to catch
FISHING_MAX_TIME = 20                        # Maximum seconds to catch
FISHING_TRASH_RATE = 0.10                    # 10% chance to catch trash
FISH_TYPES = {
    'trash': {'probability': 0.101, 'name': '垃圾', 'value': 0, 'color': '#555555', 'emoji': '🗑️', 'catch_min': 2, 'catch_max': 4, 'mash_min': 3, 'mash_max': 5},
    'carp': {'probability': 0.20, 'name': '鲤鱼', 'value': 10, 'color': '#FF6B35', 'emoji': '🐟', 'catch_min': 3, 'catch_max': 6, 'mash_min': 5, 'mash_max': 8},
    'crucian': {'probability': 0.16, 'name': '鲫鱼', 'value': 20, 'color': '#87CEEB', 'emoji': '🐟', 'catch_min': 3, 'catch_max': 7, 'mash_min': 7, 'mash_max': 10},
    'bream': {'probability': 0.13, 'name': '鳊鱼', 'value': 30, 'color': '#4CAF50', 'emoji': '🐟', 'catch_min': 4, 'catch_max': 8, 'mash_min': 9, 'mash_max': 13},
    'catfish': {'probability': 0.10, 'name': '鲶鱼', 'value': 50, 'color': '#795548', 'emoji': '🐟', 'catch_min': 4, 'catch_max': 9, 'mash_min': 12, 'mash_max': 16},
    'grass_carp': {'probability': 0.08, 'name': '草鱼', 'value': 80, 'color': '#66BB6A', 'emoji': '🐠', 'catch_min': 5, 'catch_max': 10, 'mash_min': 14, 'mash_max': 18},
    'bass': {'probability': 0.07, 'name': '鲈鱼', 'value': 120, 'color': '#2196F3', 'emoji': '🐠', 'catch_min': 5, 'catch_max': 12, 'mash_min': 16, 'mash_max': 20},
    'eel': {'probability': 0.06, 'name': '鳗鱼', 'value': 200, 'color': '#FF9800', 'emoji': '🐠', 'catch_min': 6, 'catch_max': 14, 'mash_min': 18, 'mash_max': 24},
    'salmon': {'probability': 0.04, 'name': '三文鱼', 'value': 350, 'color': '#E91E63', 'emoji': '🐡', 'catch_min': 7, 'catch_max': 16, 'mash_min': 20, 'mash_max': 28},
    'tuna': {'probability': 0.03, 'name': '金枪鱼', 'value': 500, 'color': '#1A237E', 'emoji': '🐡', 'catch_min': 8, 'catch_max': 18, 'mash_min': 22, 'mash_max': 30},
    'dragon_king': {'probability': 0.02, 'name': '龙王', 'value': 1000, 'color': '#FFD700', 'emoji': '🐉', 'catch_min': 10, 'catch_max': 20, 'mash_min': 25, 'mash_max': 35},
}
FISHING_RESULT_DURATION = 3.0               # How long to show result

# Number Lottery Game
LOTTERY_ENTRY_COST = 50                       # Entry fee for number lottery
LOTTERY_NUMBERS = [1, 2, 3]                   # Available numbers to choose from
LOTTERY_PRIZES = {1: 100, 2: 500, 3: 1000}   # Prize per number matched (any position)
LOTTERY_RESULT_DURATION = 3.0                 # How long to show result

# Maze Game
MAZE_ENTRY_COST = 50                         # Entry fee for maze game
MAZE_CHOICES = 3                             # Number of left/right choices
MAZE_ROOMS = 8                               # Total possible endings (2^3)
MAZE_PRIZES = {
    'diamond': {'count': 1, 'name': '钻石', 'value': 500, 'color': '#00BFFF'},
    'gold_ore': {'count': 2, 'name': '金矿', 'value': 100, 'color': '#FFD700'},
    'iron_ore': {'count': 3, 'name': '铁矿', 'value': 50, 'color': '#808080'},
    'empty': {'count': 2, 'name': '空房间', 'value': 0, 'color': '#555555'},
}
MAZE_CHOICE_DURATION = 0.5                   # Animation duration for each choice
MAZE_RESULT_DURATION = 3.0                   # How long to show final result

# Cave Game
CAVE_ENTRY_COST = 50                     # Entry fee for cave game
CAVE_COUNT = 4                           # Number of caves
CAVE_COIN_MIN = 7                      # Minimum coins thrown
CAVE_COIN_MAX = 15                     # Maximum coins thrown
CAVE_COIN_TYPES = {
    'gold': {'probability': 0.10, 'name': '金币', 'value': 100, 'color': '#FFD700'},
    'silver': {'probability': 0.20, 'name': '银币', 'value': 50, 'color': '#C0C0C0'},
    'copper': {'probability': 0.70, 'name': '铜币', 'value': 10, 'color': '#CD7F32'},
}
CAVE_THROW_ANIM_DURATION = 1.0           # How long each throw takes
CAVE_RESULT_DURATION = 2.0               # How long to show result

# Ladder Climbing Game
LADDER_ENTRY_COST = 75                      # Entry fee for ladder game
LADDER_START_FALL_RATE = 0.05               # 5% fall chance at step 1
LADDER_FALL_RATE_INCREMENT = 0.05           # +5% per step
LADDER_SAVE_MIN = 15                        # Minimum money saved per step
LADDER_SAVE_MAX = 25                        # Maximum money saved per step

# Dice Game
DICE_ENTRY_COST = 10                         # Entry fee for dice game
DICE_ROLL_ANIM_DURATION = 1.0                # How long the roll animation takes
DICE_RESULT_DURATION = 3.0                   # How long to show result

# Math Game
MATH_ENTRY_COST = 15                         # Entry fee for math game
MATH_RESULT_DURATION = 3.0                   # How long to show result

# Marble Game
MARBLE_ENTRY_COST = 20                       # Entry fee for marble game (4 marbles)
MARBLE_COUNT = 4                             # Number of marbles per game
MARBLE_DROP_DURATION = 1.5                   # Marble drop animation duration
MARBLE_RESULT_DURATION = 3.0                 # How long to show result

# Coin Toss Game
COIN_ENTRY_COST = 0                          # Free to play
COIN_EDGE_CHANCE = 0.01                      # 1% land on edge
COIN_EDGE_REWARD = 500                       # Edge reward
COIN_HEADS_REWARD = 15                       # Heads reward
COIN_TAILS_PENALTY = -10                     # Tails penalty

# Horse Racing Game
HORSE_ENTRY_COST = 50                        # Entry fee for horse racing
HORSE_WIN_MIN = 100                          # Minimum win amount
HORSE_WIN_MAX = 200                          # Maximum win amount
HORSE_DRAW_COST = 50                         # Tie reward
HORSE_TRACK_CELLS = 10                       # Number of cells per track

# Trash Collection Game
TRASH_ENTRY_COST = 100                       # Entry fee for trash collection
TRASH_TIME_LIMIT = 5                         # Seconds to collect trash
TRASH_COUNT = 20                             # Number of trash items on ground

# Wooden Fish Game
WOODEN_FISH_ENTRY_COST = 10                  # Entry fee for wooden fish game

# Lucky Wheel Game
WHEEL_ENTRY_COST = 50                        # Entry fee for wheel game

# Go Out Game
GO_OUT_ENTRY_COST = 100                      # Entry fee for go out game
GO_OUT_PREDICT_COST = 25                     # Cost to predict weather

# Strength Competition Game
STRENGTH_ENTRY_COST = 100                    # Entry fee for strength game

# Exam Grading Game
EXAM_ENTRY_COST = 25                       # Entry fee for exam grading

# Flying Chess Game
FLYING_CHESS_ENTRY_COST = 50                # Entry fee for flying chess



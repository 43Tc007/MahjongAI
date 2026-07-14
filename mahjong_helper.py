import torch
from typing import List, Dict
from dataclasses import dataclass, field
import copy

def is_flower(idx: int) -> bool:
    return idx >= 34

def is_19(tile: int) -> bool:
    return tile in [0, 9, 18, 8, 17, 26]

def is_wind(tile: int) -> bool:
    return tile >= 27 and tile <= 30

def is_dragon(tile: int) -> bool:
    return tile >= 31 and tile <= 33

def seat(player: int, game_wind: int):
    return (player - game_wind + 4) % 4

def is_zi(tile: int):
    return is_wind(tile) or is_dragon(tile)

tiles_name = {
    # Manzu (characters)
    0: "1m", 1: "2m", 2: "3m", 3: "4m", 4: "5m", 5: "6m", 6: "7m", 7: "8m", 8: "9m",
    # Pinzu (dots)
    9: "1p", 10: "2p", 11: "3p", 12: "4p", 13: "5p", 14: "6p", 15: "7p", 16: "8p", 17: "9p",
    # Souzu (bamboo)
    18: "1s", 19: "2s", 20: "3s", 21: "4s", 22: "5s", 23: "6s", 24: "7s", 25: "8s", 26: "9s",
    # Winds
    27: "E", 28: "S", 29: "W", 30: "N",
    # Dragons
    31: "white", 32: "green", 33: "red",
    # Red flowers
    34: "red flower 1", 35: "red flower 2", 36: "red flower 3", 37: "red flower 4",
    # Black flowers
    38: "black flower 1", 39: "black flower 2", 40: "black flower 3", 41: "black flower 4"
}



EAST = 0
SOUTH = 1
WEST = 2
NORTH = 3

DRAW_PHASE = 0
DISCARD_PHASE = 1
CALL_PHASE = 2

MAX_LOG_ENTRIES = 128  

@dataclass
class GameState:
    round_wind: int
    game_wind: int
    current_player: int
    wall_remaining: int
    phase: int = DRAW_PHASE

    # Player-specific data
    hands: List[torch.Tensor] = field(default_factory=lambda: [torch.zeros(42, dtype=torch.uint8) for _ in range(4)])
    flowers: List[torch.Tensor] = field(default_factory=lambda: [torch.zeros(42, dtype=torch.uint8) for _ in range(4)])
    melds: List[List[torch.Tensor]] = field(default_factory=lambda: [[] for _ in range(4)])
    men_qian_qing: List[bool] = field(default_factory=lambda: [True for _ in range(4)])
    addkanable_tiles: List[Dict[int, int]] = field(default_factory=lambda: [{}, {}, {}, {}])

    # Log: each row is [tile one‑hot (42) + player one‑hot (4)]
    log: torch.Tensor = field(default_factory=lambda: torch.zeros(MAX_LOG_ENTRIES, 42 + 4, dtype=torch.uint8))
    logline: int = 0

    # Convenience:
    last_discard: int = -1

def game_state_mask(game: GameState, player_idx: int) -> GameState:
    masked_game = copy.copy(game)
    masked_game.hands = [masked_game.hands[player_idx]]
    return masked_game

def is_subsequently_called(gamestate: GameState, logline: int):
    line = gamestate.log[logline]
    subsequent_line = gamestate.log[logline + 1]
    if subsequent_line.sum() == 0:
        return False
    discarded_tile = torch.nonzero(line, as_tuple=True)[0][0].item()
    called_tile = torch.nonzero(line, as_tuple=True)[0][0].item()
    return True if (subsequent_line.sum() == 4 or (subsequent_line.sum() == 5 and discarded_tile == called_tile)) else False
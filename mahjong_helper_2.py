import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, field

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

# DRAW HERE =  -1
WAIT_TSUMO = 0
WAIT_ADDKAN = 1
WAIT_ANKAN = 2
DISCARD = 3
WAIT_RON = 4
WAIT_KAN = 5
WAIT_PUNG = 6
WAIT_CHOW = 7

MAX_LOG_ENTRIES = 128  

@dataclass
class GameState:
    round_wind: int
    game_wind: int
    current_player: int = EAST
    wall_remaining: int = 144
    phase: int = WAIT_TSUMO

    # Player-specific data – now using np.ndarray
    hands: List[np.ndarray] = field(default_factory=lambda: [np.zeros(42, dtype=np.uint8) for _ in range(4)])
    flowers: List[np.ndarray] = field(default_factory=lambda: [np.zeros(42, dtype=np.uint8) for _ in range(4)])
    melds: List[List[np.ndarray]] = field(default_factory=lambda: [[] for _ in range(4)])
    
    # Log: each row is [tile one‑hot (42) + player one‑hot (4)]
    log: np.ndarray = field(default_factory=lambda: np.zeros((MAX_LOG_ENTRIES, 42 + 4), dtype=np.uint8))
    logline: int = 0

    # Convenience:
    last_discard: int = -1
    addkanable_tiles: List[Dict[int, int]] = field(default_factory=lambda: [{}, {}, {}, {}])
    men_qian_qing: List[bool] = field(default_factory=lambda: [True for _ in range(4)])


def melds_to_array(lst: List[np.ndarray]) -> np.ndarray:
    pad_array = np.zeros(42)
    while len(lst) < 4:
        lst.append(pad_array)
    return np.stack(lst)



def game_state_mask(game: GameState, player_idx: int) -> np.ndarray:
    # round wind, game wind, current player, wall remaining,
    metadata_array = np.zeros(shape=(4, 42 + 4), dtype=np.uint8)
    metadata_array[0, game.round_wind] = 4
    metadata_array[1, game.game_wind] = 4
    metadata_array[2, game.current_player + 42] = 1
    metadata_array[3, :] = game.wall_remaining

    hands_array = np.zeros(shape=(4, 42), dtype=np.uint8)
    hands_array[player_idx] = game.hands[player_idx]
    hands_array = np.hstack([hands_array, np.identity(4)])

    meld_player = np.array([
        [1, 0, 0, 0],
        [1, 0, 0, 0],
        [1, 0, 0, 0],
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
    ])
    melds_array = np.hstack([np.vstack([melds_to_array(game.melds[i]) for i in range(4)]), meld_player])
    flowers_array = np.hstack([np.stack(game.flowers), np.identity(4, dtype=np.uint8)])
    return np.vstack([
        metadata_array,
        hands_array,
        melds_array,
        flowers_array,
        game.log
    ])

def is_subsequently_called(gamestate: GameState, logline: int):
    line = gamestate.log[logline]
    subsequent_line = gamestate.log[logline + 1]
    if subsequent_line.sum() == 0:
        return False
    # Convert np.nonzero to get first index of non‑zero element
    discarded_tile = np.nonzero(line)[0][0]
    # FIXED: previously both used 'line', now 'subsequent_line' for the called tile
    called_tile = np.nonzero(subsequent_line)[0][0]
    return True if (subsequent_line.sum() == 4 or (subsequent_line.sum() == 5 and discarded_tile == called_tile)) else False

# Unit test
if __name__ == '__main__':
    state = GameState(EAST, EAST)
    print(game_state_mask(state, 0).shape)
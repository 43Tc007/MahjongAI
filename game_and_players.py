import torch
from typing import List, Tuple, override
from mahjong_helper import *
import random
from abc import ABC, abstractmethod

from mahjong_helper import GameState

class Player(ABC):
    """Pure decision‑maker with no stored state – all state comes from the arbiter."""
    def __init__(self):
        self.player_idx: int = -1

    @abstractmethod
    def choose_discard(self, masked_game: GameState) -> int:
        pass

    @abstractmethod
    def chow_decision(self, masked_game: GameState) -> bool:
        pass

    @abstractmethod
    def pung_decision(self, masked_game: GameState) -> bool:
        pass

    @abstractmethod
    def kan_decision(self, masked_game: GameState) -> bool:
        pass

    @abstractmethod
    def ron_decision(self, masked_game: GameState) -> bool:
        pass

class RandomPlayer(Player):
    def __init__(self):
        super().__init__()
    
    @override
    def chow_decision(self, masked_game: GameState) -> bool:
        return random.choice([True, False])
    
    @override
    def pung_decision(self, masked_game: GameState) -> bool:
        return random.choice([True, False])
    
    @override
    def kan_decision(self, masked_game: GameState) -> bool:
        return random.choice([True, False])
    
    @override
    def ron_decision(self, masked_game: GameState) -> bool:
        return random.choice([True, False])

class Arbiter:
    def __init__(self, players: List[Player], round_wind: int = EAST, game_wind: int = EAST):
        self.players = players

        for idx, p in enumerate(self.players):
            p.player_idx = idx

        self.state = GameState(
            round_wind=round_wind,
            game_wind=game_wind,
            current_player=EAST,
            wall_remaining=144,
        )

    # --- State updates (called by the game) ---

    def set_current_player(self, player_idx: int) -> None:
        self.state.current_player = player_idx

    def set_wall_remaining(self, count: int) -> None:
        self.state.wall_remaining = count

    def add_to_hand(self, player_idx: int, tile: int) -> None:
        self.state.hands[player_idx][tile] += 1

    def remove_from_hand(self, player_idx: int, tile: int) -> None:
        self.state.hands[player_idx][tile] -= 1

    def record_flower(self, player_idx: int, tile: int) -> None:
        self.state.flowers[player_idx][tile] += 1

    def add_meld(self, player_idx: int, meld: torch.Tensor) -> None:
        self.state.melds[player_idx].append(meld)
        
    def record_action(self, line: torch.Tensor) -> None:
        self.state.log[self.state.logline] = line
        self.state.logline += 1

    def record_discard(self, player_idx: int, tile: int) -> None:
        """Record a discard in the log and update last_discard."""
        line = torch.zeros(42, dtype=torch.uint8)
        line[tile] = 1
        line[player_idx + 42] = 1
        self.record_action(line)

    def record_call(self, player_idx: int, meld: torch.Tensor) -> None:
        """Record a call (chow/pung/kan) in the log. Does not update last_discard."""
        line = meld
        line[42 + player_idx] = 1
        self.record_action(line)        

    # # --- Query methods for players ---

    def get_hand(self, player_idx: int) -> torch.Tensor:
        return self.state.hands[player_idx]

    def get_flowers(self, player_idx: int) -> torch.Tensor:
        return self.state.flowers[player_idx]

    def get_melds(self, player_idx: int) -> List[torch.Tensor]:
        return self.state.melds[player_idx]

    def get_current_player(self) -> int:
        return self.state.current_player

    def get_wall_remaining(self) -> int:
        return self.state.wall_remaining

    def get_log(self) -> torch.Tensor:
        """Return the entire log tensor."""
        return self.state.log

    def get_logline(self) -> int:
        return self.state.logline

    def get_log_entry(self, idx: int) -> torch.Tensor:
        """Return a specific log row."""
        return self.state.log[idx]

    # # --- Decision requests (called by the game) ---

    def request_discard(self, player_idx: int) -> int:
        return self.players[player_idx].choose_discard(game_state_mask(self.state, player_idx))

    def request_chow(self, player_idx: int) -> bool:
        return self.players[player_idx].chow_decision(game_state_mask(self.state, player_idx))

    def request_pung(self, player_idx: int) -> bool:
        return self.players[player_idx].pung_decision(game_state_mask(self.state, player_idx))

    def request_kan(self, player_idx: int) -> bool:
        return self.players[player_idx].kan_decision(game_state_mask(self.state, player_idx))
    
    def request_ron(self, player_idx: int) -> bool:
        return self.players[player_idx].ron_decision(game_state_mask(self.state, player_idx))

    # # --- Meld execution helpers ---

    def execute_chow(self, player_idx: int, tile: int, tiles_for_chow: List[int]) -> None:
        for t in tiles_for_chow:
            self.remove_from_hand(player_idx, t)
        meld = torch.zeros(42, dtype=torch.uint8)
        meld[tiles_for_chow + [tile]] = 1
        self.add_meld(player_idx, meld)
        self.record_call(player_idx, meld)   # log the call

    def execute_pung(self, player_idx: int, tile: int) -> None:
        self.remove_from_hand(player_idx, tile)
        self.remove_from_hand(player_idx, tile)
        meld = torch.zeros(42, dtype=torch.uint8)
        meld[tile] += 3
        self.add_meld(player_idx, meld)
        self.record_call(player_idx, meld)

    def execute_kan(self, player_idx: int, tile: int) -> None:
        for _ in range(3):
            self.remove_from_hand(player_idx, tile)
        meld = torch.zeros(42, dtype=torch.uint8)
        meld[tile] += 4
        self.add_meld(player_idx, meld)
        self.record_call(player_idx, meld)
    
    def execute_ron(self, player_idx: int, tile: int) -> None:
        pass # pass through fan calculator and adjust win loss

# game utils
def chowable(game: GameState, tile: int, player_idx: int, hand_tile: Tuple[int, int]) -> bool:
    if tile > 26:
        return False
    def suit(tile: int):
        return tile // 9
    if all([
        # all three tiles are of the same suit
        suit(tile) == suit(hand_tile[0]),
        suit(tile) == suit(hand_tile[1]),
        # they are in the hand of the player
        (game.hands[player_idx][[hand_tile[0], hand_tile[1]]] >= 1).all().item()
    ]):
        return True
    return False

def pungable(game: GameState, player_idx: int, tile: int) -> bool:
    return True if game.hands[player_idx][tile] >= 2 else False

def mingkanable(game: GameState, player_idx: int, tile: int) -> bool:
    return True if game.hands[player_idx][tile] >= 3 else False

def ankanable(game: GameState, player_idx: int, tile: int) -> bool:
    return True if game.hands[player_idx][tile] == 4 and game.current_player == player_idx else False

def addkanable(game: GameState, player_idx: int, tile: int) -> bool:
    return True if tile in game.addkanable_tiles[player_idx].keys() else False


class MahjongGame:
    def __init__(self, round_wind: int, game_wind: int,
                 players: List[Player]):
        self.arbiter = Arbiter(players, round_wind, game_wind)
        self.round_wind = round_wind
        self.game_wind = game_wind
        self.current_player = EAST

        self.wall: List[int] = list(range(34)) * 4 + list(range(34, 42))
        random.shuffle(self.wall)
        self.next_tile_index = 0
        self.arbiter.set_wall_remaining(len(self.wall))

        self._deal_hands()

    def _deal_hands(self):
        for i in range(4):
            tiles_to_deal = 14 if i == self.game_wind else 13
            for _ in range(tiles_to_deal):
                self._draw_card(i)

    def _draw_card(self, player_idx: int) -> None:
        tile = self.wall[self.next_tile_index]
        self.next_tile_index += 1
        if is_flower(tile):
            self.arbiter.record_flower(player_idx, tile)
            self._draw_card(player_idx)
        else:
            self.arbiter.add_to_hand(player_idx, tile)
        self.arbiter.set_wall_remaining(self.remaining_tiles())

    def remaining_tiles(self) -> int:
        return len(self.wall) - self.next_tile_index

    # def run(self):
    #     while self.remaining_tiles() > 0:
    #         self._draw_card(self.current_player)

    #         discard_idx = self.arbiter.request_discard(self.current_player)
    #         if discard_idx == -1:
    #             break
    #         self.arbiter.remove_from_hand(self.current_player, discard_idx)
    #         self.arbiter.record_discard(self.current_player, discard_idx)

    #         called = False
    #         for offset in range(1, 4):
    #             p_idx = (self.current_player + offset) % 4
    #             if self.arbiter.request_pung(p_idx):
    #                 self.arbiter.execute_pung(p_idx, discard_idx)
    #                 self.current_player = p_idx
    #                 called = True
    #                 break
    #         if not called:
    #             self.current_player = (self.current_player + 1) % 4

    #         self.arbiter.set_current_player(self.current_player)

    #     print("Game ended.")




# # Example usage
# if __name__ == "__main__":
#     game = MahjongGame(EAST, EAST, [RandomPlayer(), RandomPlayer(), RandomPlayer(), RandomPlayer()])
#     print("Remaining tiles:", game.remaining_tiles())
#     # Access log and logline
#     print("Log shape:", game.arbiter.get_log().shape)
#     print("Logline:", game.arbiter.get_logline())
#     # game.run()   # uncomment to run
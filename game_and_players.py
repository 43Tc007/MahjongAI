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
    def choose_discard(self, masked_game: GameState) -> int:
        discardable_tiles = torch.nonzero(masked_game.hands[0]).squeeze()
        return int(discardable_tiles[random.randint(0, len(discardable_tiles) - 1)].item())
    
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
        line = torch.zeros(42 + 4, dtype=torch.uint8)
        line[tile] = 1
        line[player_idx + 42] = 1
        self.record_action(line)

    def record_call(self, player_idx: int, meld: torch.Tensor) -> None:
        """Record a call (chow/pung/kan) in the log. Does not update last_discard."""
        line = torch.hstack([meld, torch.zeros(4, dtype=torch.uint8)])
        line[player_idx + 42] = 1
        self.record_action(line)

    def update_phase(self):
        self.state.phase = (self.state.phase + 1) % 3

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

    def execute_chow(self, player_idx: int, tile: int, tiles_for_chow: Tuple[int, int]) -> None:
        for t in tiles_for_chow:
            self.remove_from_hand(player_idx, t)
        meld = torch.zeros(42, dtype=torch.uint8)
        meld[list(tiles_for_chow) + [tile]] = 1
        self.add_meld(player_idx, meld)
        self.record_call(player_idx, meld)   # log the call

    def execute_pung(self, player_idx: int, tile: int) -> None:
        self.remove_from_hand(player_idx, tile)
        self.remove_from_hand(player_idx, tile)
        meld = torch.zeros(42, dtype=torch.uint8)
        meld[tile] += 3
        self.state.addkanable_tiles[player_idx][tile] = len(self.state.melds[player_idx])
        self.add_meld(player_idx, meld)
        self.record_call(player_idx, meld)

    def execute_ming_kan(self, player_idx: int, tile: int) -> None:
        for _ in range(3):
            self.remove_from_hand(player_idx, tile)
        meld = torch.zeros(42, dtype=torch.uint8)
        meld[tile] += 4
        self.add_meld(player_idx, meld)
        self.record_call(player_idx, meld)
    
    def execute_an_kan(self, player_idx: int, tile: int) -> None:
        for _ in range(4):
            self.remove_from_hand(player_idx, tile)
        meld = torch.zeros(42, dtype=torch.uint8)
        meld[tile] += 4
        self.add_meld(player_idx, meld)
        self.record_call(player_idx, meld)

    def execute_add_kan(self, player_idx: int, tile: int) -> None:
        self.remove_from_hand(player_idx, tile)
        meld_index = self.state.addkanable_tiles[player_idx][tile]
        self.state.melds[player_idx][meld_index][tile] += 1
        self.record_call(player_idx, self.state.melds[player_idx][meld_index])

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
        self.arbiter.state.current_player = EAST
        self.wall: List[int] = list(range(34)) * 4 + list(range(34, 42))
        self.need_draw = True
        self.terminated = False
        random.shuffle(self.wall)
        self.arbiter.set_wall_remaining(len(self.wall))

        self._deal_hands()

    def _deal_hands(self):
        for i in range(4):
            tiles_to_deal = 13
            for _ in range(tiles_to_deal):
                self._draw_card(i)

    def _draw_card(self, player_idx: int) -> int:
        tile = self.wall.pop()
        self.arbiter.set_wall_remaining(self.remaining_tiles())
        if is_flower(tile):
            self.arbiter.record_flower(player_idx, tile)
            self._draw_card(player_idx)
        else:
            self.arbiter.add_to_hand(player_idx, tile)
        return tile
        
    def remaining_tiles(self) -> int:
        return len(self.wall)
    
    def handle_calls_after_discard(self, discard_tile) -> int:
        for player in range(4):
            if player == self.arbiter.state.current_player:
                continue
            if mingkanable(self.arbiter.state, player, discard_tile):
                response = self.arbiter.request_kan(player)
                if response:
                    self.arbiter.execute_ming_kan(player, discard_tile)
                    return player
        for player in range(4):
            if player == self.arbiter.state.current_player:
                continue
            if pungable(self.arbiter.state, player, discard_tile):
                response = self.arbiter.request_kan(player)
                if response:
                    self.arbiter.execute_pung(player, discard_tile)
                    self.need_draw = False
                    return player
        for player in range(4):
            if player == self.arbiter.state.current_player:
                continue
            for duplet in [(discard_tile-2, discard_tile-1), (discard_tile-1, discard_tile+1), (discard_tile+1, discard_tile+2)]: 
                if chowable(self.arbiter.state, discard_tile, player, duplet):
                    response = self.arbiter.request_chow(player)
                    if response:
                        self.arbiter.execute_chow(player, discard_tile, duplet)
                        self.need_draw = False
                        return player
        
        return (self.arbiter.state.current_player + 1) % 4

    def step(self) -> None:
        if self.arbiter.state.phase == DRAW_PHASE:
            self.draw_step()
            self.arbiter.update_phase()
        elif self.arbiter.state.phase == DISCARD_PHASE:
            self.arbiter.state.last_discard = self.discard_step()
            self.arbiter.update_phase()
        else:
            self.call_step(self.arbiter.state.last_discard)
            self.arbiter.update_phase()

    def call_step(self, discard_tile):
        next_player = self.handle_calls_after_discard(discard_tile)
        self.arbiter.set_current_player(next_player)

    def discard_step(self):
        
        self.need_draw = True

        # After that we need to choose if discard or not
        discard_tile = self.arbiter.request_discard(self.arbiter.state.current_player)
        self.arbiter.record_discard(self.arbiter.state.current_player, discard_tile)
        self.arbiter.remove_from_hand(self.arbiter.state.current_player, discard_tile)

        if self.remaining_tiles() <= 0:
            self.terminated = True
        return discard_tile

    def draw_step(self):
        if self.need_draw:
            tile = self._draw_card(self.arbiter.state.current_player)
    
            if addkanable(self.arbiter.state, self.arbiter.state.current_player, tile):
                response = self.arbiter.request_kan(self.arbiter.state.current_player)
                if response:
                    self.arbiter.execute_add_kan(self.arbiter.state.current_player, tile)

            if ankanable(self.arbiter.state, self.arbiter.state.current_player, tile):
                response = self.arbiter.request_kan(self.arbiter.state.current_player)
                if response:
                    self.arbiter.execute_an_kan(self.arbiter.state.current_player, tile)
        
# # Example usage
# if __name__ == "__main__":
#     game = MahjongGame(EAST, EAST, [RandomPlayer(), RandomPlayer(), RandomPlayer(), RandomPlayer()])
#     print("Remaining tiles:", game.remaining_tiles())
#     # Access log and logline
#     print("Log shape:", game.arbiter.get_log().shape)
#     print("Logline:", game.arbiter.get_logline())
#     # game.run()   # uncomment to run
import torch
from typing import *
from mahjong_helper import is_flower
import random

EAST = 0
SOUTH = 1
WEST = 2
NORTH = 3

class Player():
    def __init__(self):
        self.hand: torch.Tensor = torch.zeros(42)
        self.melds: torch.Tensor = torch.zeros(4, 42)
        self.flowers: torch.Tensor = torch.zeros(42)
        self.addkan: Dict[int, int] = {} # tile -> meld_index
        self.men_qian_qing = True

    def current_state(self) -> torch.Tensor:
        return torch.vstack([self.hand, self.melds, self.flowers])

    def discard(self, idx: int) -> None:
        self.hand[idx] -= 1

    def chow_decision(self):
        pass
    
    def pung_decision(self):
        pass

    def kan_decision(self):
        pass


class MahjongGame():
    def __init__(self, round_wind: int, game_wind: int):
        self.players: List[Player] = [Player() for i in range(4)]
        self.wall: List[int] = list(range(34)) * 4 + list(range(34, 42))
        random.shuffle(self.wall)
        self.next_tile_index: int = 0
        self.round_wind: int = round_wind
        self.game_wind: int = game_wind
        self.current_player: int = EAST

        self.game_start()
        
    def remaining_tiles(self) -> int:
        return 144 - self.next_tile_index

    def draw_card(self, player_idx: int) -> None:
        tile = self.wall[self.next_tile_index]
        self.next_tile_index += 1
        if is_flower(tile):
            self.players[player_idx].flowers[tile] += 1
            self.draw_card(player_idx)
        else:
            self.players[player_idx].hand[tile] += 1
            
    def game_start(self) -> None:
        for i in range(4):
            tile_number = int(i == self.game_wind) + 13
            for _ in range(tile_number):
                self.draw_card(i)

game = MahjongGame(EAST, EAST)
print(game.remaining_tiles())
print(game.players[SOUTH].current_state())
        

    
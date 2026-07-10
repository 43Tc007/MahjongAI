from hand_divisor import divide_from_tensors, CHOW, PUNG, PAIR
from mahjong_helper import *
import torch
from typing import List, Tuple
from game_and_players import MahjongGame, Player

"""
無花 done
正花 done
門前清 ip
平胡 done
翻牌 done
搶杠 bonus
杠上開花 bonus
海底 bonus
自摸 bonus
花幺 done
一臺花 done
七只花 special
對對胡 done
混一色 done
小三元 done
清一色 done
大三元 done
天湖 ip
地湖 ip
四杠子 done
坎坎胡 <- need help
杠上杠自摸
大花胡 special
字一色 done
小四喜 done
大四喜 done
請幺 done
十三幺 done / special
九子連環 done
"""

# --- flowers ---

def flowers(flowers: torch.Tensor, player, game_wind) -> int:
    def wu_hua(flowers: torch.Tensor) -> bool:
        return (flowers[34:] == 0).all().item()

    def red_zheng_hua(flowers: torch.Tensor, player, game_wind) -> bool:
        return (flowers[34 + seat(player, game_wind)] == 1).item()
    
    def black_zheng_hua(flowers: torch.Tensor, player, game_wind) -> bool:
        return (flowers[38 + seat(player, game_wind)] == 1).item()
    
    def red_yi_tai_hua(flowers: torch.Tensor) -> bool:
        return (flowers[34:37] == 1).all().item()
    
    def black_yi_tai_hua(flowers:torch.Tensor) -> bool:
        return (flowers[38:41] == 1).all().item()
    
    return wu_hua(flowers) + red_zheng_hua(flowers, player, game_wind) + black_zheng_hua(flowers, player, game_wind) + red_yi_tai_hua(flowers) + black_yi_tai_hua(flowers)

# --- main hand ---

def ping_hu(division: List[Tuple[int, int]]) -> int:
    for pack in division:
        if pack[0] == PUNG:
            return 0
    return 1

def dui_dui_hu(division: List[Tuple[int, int]]) -> int:
    for pack in division:
        if pack[1] == CHOW:
            return 0
    return True

def fan_pai(division: List[Tuple[int, int]], player: int, round_wind: int, game_wind: int) -> int:
    res = 0
    seat_wind = seat(player, game_wind)
    targets = [seat_wind + 27, round_wind + 27, 31, 32, 33]
    for pack in division:
        if pack[1] in targets:
            res += 1
    return res

def hua_yao(division: List[Tuple[int, int]]) -> int:
    for type, tile in division:
        if not (is_19(tile) or is_zi(tile)):
            return 0
    return 1

def qing_yao(division: List[Tuple[int, int]]) -> int:
    for type, tile in division:
        if not is_19(tile):
            return 0
    return 13

def da_xiao_san_yuan(division: List[Tuple[int, int]]) -> int:
    seen = 0
    pair_is_dragon = False
    for type, tile in division:
        if is_dragon(tile):
            seen += 1
            if type == PAIR:
                pair_is_dragon = True
        
    if seen != 3:
        return 0
    if pair_is_dragon:
        return 3 # 3+2=5
    return 13

def qing_hun_yi_se(division: List[Tuple[int, int]]) -> int:
    suit = -1
    zi_present = False
    for type, tile in division:
        if is_zi(tile):
            zi_present = True
            continue
        if suit == -1:
            suit = tile // 9
            continue
        if suit != tile // 9:
            return 0
    return 3 if zi_present else 7

def zi_yi_se(division: List[Tuple[int, int]]) -> int:
    for type, tile in division:
        if not is_zi(tile):
            return 0
    return 13

def da_xiao_si_xi(division: List[Tuple[int, int]]) -> int:
    seen = 0
    for type, tile in division:
        if is_wind(tile):
            seen += 1
            if type == PAIR:
                pair_is_wind = True    
    if seen != 3:
        return 0
    return 13

def jiu_zi_lian_huan(hand: torch.Tensor) -> int:
    if hand.sum() != 14:
        return -1
    for base in (0, 9, 18):
        s = hand[base:base + 9]  
        # The whole suit must contain exactly 14 tiles
        if s.sum() != 14:
            continue
        # Convert to list for easy checking
        tiles = s.tolist()
        # 1-indexed: tiles[0] = 1, tiles[8] = 9
        if tiles[0] >= 3 and all(x >= 1 for x in tiles[1:8]) and tiles[8] >= 3:
            return 13  # base is 0, 9, or 18, identifying the suit
    return 0

def si_gang_zi(calls: torch.Tensor) -> int:
    return 13 * (calls.sum(dim=1) == 4).all().item()

def shi_san_yao(hand: torch.Tensor) -> int:
    indices = torch.tensor([
        0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33,
    ])
    return (hand[indices] >= 1).all().item() * 13

def tian_hu(game):
    pass # check for no discard

def di_hu(game):
    pass # check for first discard and declare win

def men_qian_qing(game):
    pass # check for player status


def fan_calculator(game: MahjongGame, player: int, hand: torch.Tensor, calls: torch.Tensor, *, bonus: int, special: int):
    total_fan = bonus
    if special:
        return special
    



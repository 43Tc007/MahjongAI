from hand_divisor import divide_from_tensors, CHOW, PUNG, PAIR
from mahjong_helper import *
import torch
from typing import List, Tuple

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

def ping_hu(division: List[Tuple]) -> bool:
    for pack in division:
        if pack[0] == PUNG:
            return False
    return True

def dui_dui_hu(division: List[Tuple]) -> bool:
    for pack in division:
        if pack[1] == CHOW:
            return False
    return True

def fan_pai(divison: List[Tuple], player, round_wind, game_wind) -> int:
    res = 0
    seat_wind = seat(player, game_wind)
    targets = [seat_wind + 27, round_wind + 27, 31, 32, 33]
    for pack in divison:
        if pack[1] in targets:
            res += 1
    return res
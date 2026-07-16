from hand_divisor import divide_from_tensors, CHOW, PUNG, PAIR
from mahjong_helper import *
import torch
from typing import List, Tuple

"""
無花 done
正花 done
門前清 done
平胡 done
翻牌 done
搶杠 done
杠上開花 done
海底 done
自摸 done
花幺 done
一臺花 done
七只花 done
對對胡 done
混一色 done
小三元 done
清一色 done
大三元 done
天湖 done
地湖 done
四杠子 done
坎坎胡 done
杠上杠自摸
大花胡 done
字一色 done
小四喜 done
大四喜 done
請幺 done
十三幺 done
九子連環 done
"""

# --- flowers ---

def flowers(flowers: torch.Tensor, player: int, game_wind: int) -> int:
    def wu_hua(flowers: torch.Tensor) -> int:
        return int((flowers[34:] == 0).all().item())

    def red_zheng_hua(flowers: torch.Tensor, player: int, game_wind: int) -> int:
        return int((flowers[34 + seat(player, game_wind)] == 1).item())
    
    def black_zheng_hua(flowers: torch.Tensor, player: int, game_wind: int) -> int:
        return int((flowers[38 + seat(player, game_wind)] == 1).item())
    
    def red_yi_tai_hua(flowers: torch.Tensor) -> int:
        return int((flowers[34:37] == 1).all().item())
    
    def black_yi_tai_hua(flowers:torch.Tensor) -> int:
        return int((flowers[38:41] == 1).all().item())
    
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
    for _, tile in division:
        if not (is_19(tile) or is_zi(tile)):
            return 0
    return 1

def qing_yao(division: List[Tuple[int, int]]) -> int:
    for _, tile in division:
        if not is_19(tile):
            return 0
    return 13

def da_xiao_san_yuan(division: List[Tuple[int, int]]) -> int:
    seen = 0
    pair_is_dragon = False
    for pack_type, tile in division:
        if is_dragon(tile):
            seen += 1
            if pack_type == PAIR:
                pair_is_dragon = True
        
    if seen != 3:
        return 0
    if pair_is_dragon:
        return 3 # 3+2=5
    return 13

def qing_hun_yi_se(division: List[Tuple[int, int]]) -> int:
    suit = -1
    zi_present = False
    for _, tile in division:
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
    for _, tile in division:
        if not is_zi(tile):
            return 0
    return 13

def da_xiao_si_xi(division: List[Tuple[int, int]]) -> int:
    seen = 0
    for _, tile in division:
        if is_wind(tile):
            seen += 1
    if seen != 4:
        return 0
    return 13

def jiu_zi_lian_huan(hand: torch.Tensor) -> int:
    if hand.sum() != 14:
        return 0
    for base in (0, 9, 18):
        s = hand[base:base + 9]
        if s.sum() != 14:
            continue
        if s[0] >= 3 and (s[1:8] >= 1).all().item() and s[8] >= 3:
            return 13  # base is 0, 9, or 18, identifying the suit
    return 0

def si_gang_zi(calls: torch.Tensor) -> int:
    return 13 * int((calls.sum(dim=1) == 4).all().item())

def shi_san_yao(hand: torch.Tensor) -> int:
    indices = torch.tensor([
        0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33,
    ])
    return int((hand[indices] >= 1).all().item()) * 13

def tsumo(game: GameState, player: int) -> int:
    return (game.current_player == player) * 1

def tian_hu(game: GameState, player: int) -> int:
    if player != EAST:
        return 0
    return int((game.log[:, :42] == 0).all().item()) * 13

def di_hu(game: GameState, player: int) -> int:
    if tsumo(game, player):
        return 0
    return int((game.log[:, :42].sum() == 1).item()) * 13

def men_qian_qing(game: GameState, player: int) -> int:
    return int(game.men_qian_qing[player]) * 1

def hai_di_lao_yue(game: GameState) -> int:
    return (game.wall_remaining == 0) * 1

def qiang_gang(game: GameState, player: int) -> int:
    return (game.log[game.logline, :42].sum().item() == 4 and game.current_player != player) * 1

def gang_shang_kai_hua(game: GameState, player: int) -> int:
    return (game.log[game.logline, :42].sum().item() == 4 and game.current_player == player) * 1

def kan_kan_hu(game: GameState, player: int, division: List[Tuple[int, int]], win_tile: int) -> int:
    if tsumo(game, player):
        return men_qian_qing(game, player) * 13
    pair_tile: int = [tile for pack_type, tile in division if pack_type == PAIR][0]
    return (win_tile == pair_tile) * 13

def hua_hu(game: GameState, player: int, win_tile: int) -> int:
    if is_flower(win_tile):
        return int((game.flowers[player].sum() == 7) * 3 + (game.flowers[player].sum() == 8)) * 13
    return 0


def calculate_fan(
    game: GameState, player: int, win_tile: int) -> int:



    if hua_hu(game, player, win_tile):
        return hua_hu(game, player, win_tile)
    if shi_san_yao(game.hands[player]):
        return 13
    
    success, divisions = divide_from_tensors(game.hands[player], game.melds[player])
    # ---- Base fan (independent of the chosen meld division) ----
    assert success

    base_fan = (
        flowers(game.flowers[player], player, game.game_wind) +
        jiu_zi_lian_huan(game.hands[player]) +
        si_gang_zi(stack_to_tensor(game.melds[player])) +
        shi_san_yao(game.hands[player]) +
        tsumo(game, player) +
        tian_hu(game, player) +
        di_hu(game, player) +
        men_qian_qing(game, player) +
        hai_di_lao_yue(game) +
        qiang_gang(game, player) +
        gang_shang_kai_hua(game, player) 
    )

    max_fan = 0
    for division in divisions:
        temp_fan = (base_fan + 
            ping_hu(division) + 
            dui_dui_hu(division) + 
            fan_pai(division, player, game.round_wind, game.game_wind) + 
            hua_yao(division) + 
            qing_yao(division) + 
            da_xiao_san_yuan(division) + 
            qing_hun_yi_se(division) + 
            zi_yi_se(division) + 
            da_xiao_si_xi(division) + 
            kan_kan_hu(game, player, division, win_tile)
        )
        if temp_fan > max_fan:
            max_fan = temp_fan

    return max(13, max_fan)
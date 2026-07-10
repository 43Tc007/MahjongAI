"""
Coded by Copilot: https://copilot.microsoft.com/conversations/join/zNEDtb1cHLek4rpxhfw3q
"""

import torch
from mahjong_helper import tiles_name
# Pack types
PACK_TYPE_PUNG = "pung"
PACK_TYPE_CHOW = "chow"
PACK_TYPE_PAIR = "pair"

class Pack:
    def __init__(self, pack_type, base_tile):
        self.pack_type = pack_type
        self.base_tile = base_tile
    def __repr__(self):
        return f"{self.pack_type}({tiles_name[self.base_tile]})"

class Division:
    def __init__(self):
        self.packs = [None] * 5  # 4 melds + 1 pair
    def copy(self):
        d = Division()
        d.packs = self.packs[:]
        return d

def is_numbered_suit(tile):
    return tile < 27  # 0–26 are manzu/pinzu/souzu

def tile_rank(tile):
    return tile % 9 + 1

def make_pack(pack_type, tile):
    return Pack(pack_type, tile)

def divide_tail(cnt_table, fixed_cnt, work_division, result):
    for t in range(34):  # only standard tiles
        if cnt_table[t] >= 2:
            cnt_table[t] -= 2
            if torch.all(cnt_table[:34] == 0):  # all used up
                cnt_table[t] += 2
                work_division.packs[4] = make_pack(PACK_TYPE_PAIR, t)
                result.append(work_division.copy())
                return True
            cnt_table[t] += 2
    return False

# def divide_recursively(cnt_table, fixed_cnt, step, work_division, result):
#     idx = step + fixed_cnt
#     if idx == 4:  # 4 melds filled
#         return divide_tail(cnt_table, fixed_cnt, work_division, result)

#     ret = False
#     for t in range(34):  # only standard tiles
#         if cnt_table[t] == 0:
#             continue

#         # Pung
#         if cnt_table[t] >= 3:
#             work_division.packs[idx] = make_pack(PACK_TYPE_PUNG, t)
#             cnt_table[t] -= 3
#             if divide_recursively(cnt_table, fixed_cnt, step + 1, work_division, result):
#                 ret = True
#             cnt_table[t] += 3

#         # Chow
#         if is_numbered_suit(t) and tile_rank(t) <= 7:
#             if cnt_table[t] and cnt_table[t+1] and cnt_table[t+2]:
#                 work_division.packs[idx] = make_pack(PACK_TYPE_CHOW, t)
#                 cnt_table[t] -= 1
#                 cnt_table[t+1] -= 1
#                 cnt_table[t+2] -= 1
#                 if divide_recursively(cnt_table, fixed_cnt, step + 1, work_division, result):
#                     ret = True
#                 cnt_table[t] += 1
#                 cnt_table[t+1] += 1
#                 cnt_table[t+2] += 1
#     return ret

# def canonical_division(div):
#     """
#     Convert a Division into a canonical tuple form for deduplication.
#     - Sort melds (packs[0..3]) so order doesn’t matter
#     - Pair (packs[4]) is kept separate
#     """
#     melds = tuple(sorted(
#         (p.pack_type, p.base_tile) for p in div.packs[:4] if p is not None
#     ))
#     pair = (div.packs[4].pack_type, div.packs[4].base_tile) if div.packs[4] else None
#     return (melds, pair)

# def divide_win_hand(tile_tensor, fixed_packs=[]):
#     cnt_table = tile_tensor.clone()
#     result = []
#     seen = set()  # track canonical divisions

#     work_division = Division()
#     for i, p in enumerate(fixed_packs):
#         work_division.packs[i] = p

#     divide_recursively(cnt_table, len(fixed_packs), 0, work_division, result)

#     # Deduplicate
#     unique_results = []
#     for d in result:
#         key = canonical_division(d)
#         if key not in seen:
#             seen.add(key)
#             unique_results.append(d)

#     return unique_results

def divide_recursively(cnt_table, fixed_cnt, step, work_division, result, memo):
    idx = step + fixed_cnt
    if idx == 4:
        return divide_tail(cnt_table, fixed_cnt, work_division, result)

    # Memoization key: tuple of counts + current step
    key = (tuple(cnt_table[:34].tolist()), step)
    if key in memo:
        return False
    memo.add(key)

    ret = False
    for t in range(34):
        if cnt_table[t] == 0:
            continue

        # Pung
        if cnt_table[t] >= 3:
            work_division.packs[idx] = make_pack(PACK_TYPE_PUNG, t)
            cnt_table[t] -= 3
            if divide_recursively(cnt_table, fixed_cnt, step + 1, work_division, result, memo):
                ret = True
            cnt_table[t] += 3

        # Chow
        if is_numbered_suit(t) and tile_rank(t) <= 7:
            if cnt_table[t] and cnt_table[t+1] and cnt_table[t+2]:
                work_division.packs[idx] = make_pack(PACK_TYPE_CHOW, t)
                cnt_table[t] -= 1; cnt_table[t+1] -= 1; cnt_table[t+2] -= 1
                if divide_recursively(cnt_table, fixed_cnt, step + 1, work_division, result, memo):
                    ret = True
                cnt_table[t] += 1; cnt_table[t+1] += 1; cnt_table[t+2] += 1
    return ret

def divide_win_hand(tile_tensor, fixed_packs=[]):
    cnt_table = tile_tensor.clone()
    result = []
    memo = set()  # memoization cache

    work_division = Division()
    for i, p in enumerate(fixed_packs):
        work_division.packs[i] = p

    divide_recursively(cnt_table, len(fixed_packs), 0, work_division, result, memo)
    return result

# Example usage:
tiles = torch.hstack([torch.tensor([3,3,3,3,2,0,0,0,0]), torch.zeros(42 - 9)])

divisions = divide_win_hand(tiles)

for d in divisions:
    print(d.packs)
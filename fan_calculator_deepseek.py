"""
Coded by DeepSeek: https://chat.deepseek.com/share/vb406kju8itpu4v3ie
"""

import torch
from collections import Counter
from typing import List, Tuple

# Tile types (0-33 = standard, 34-41 = flowers)
TILE_COUNT = 34
FLOWER_COUNT = 8
ALL_TILES = list(range(TILE_COUNT))

# Pack types
PAIR, PUNG, CHOW = 0, 1, 2

# Helper: make a pack tuple (type, tile)
def make_pack(pack_type: int, tile: int) -> Tuple[int, int]:
    return (pack_type, tile)

# Check if a tile is a numbered suit (man, pin, sou)
def is_numbered_suit(t: int) -> bool:
    return t < 27  # 0-26 are numbered

# Tile names for display (first 34 only)
TILE_NAMES = {
    0: "1m", 1: "2m", 2: "3m", 3: "4m", 4: "5m", 5: "6m", 6: "7m", 7: "8m", 8: "9m",
    9: "1p", 10: "2p", 11: "3p", 12: "4p", 13: "5p", 14: "6p", 15: "7p", 16: "8p", 17: "9p",
    18: "1s", 19: "2s", 20: "3s", 21: "4s", 22: "5s", 23: "6s", 24: "7s", 25: "8s", 26: "9s",
    27: "E", 28: "S", 29: "W", 30: "N",
    31: "white", 32: "green", 33: "red"
}

# Sort key for packs: by tile first, then type
def pack_key(p: Tuple[int, int]) -> Tuple[int, int]:
    return (p[1], p[0])

# Convert a pack to a readable string
def pack_to_str(p: Tuple[int, int]) -> str:
    typ, tile = p
    if typ == PAIR:
        return f"pair({TILE_NAMES[tile]})"
    elif typ == PUNG:
        return f"pung({TILE_NAMES[tile]})"
    elif typ == CHOW:
        # For chow, the stored tile is the middle one; show the sequence
        return f"chow({TILE_NAMES[tile-1]}-{TILE_NAMES[tile]}-{TILE_NAMES[tile+1]})"
    else:
        return "unknown"

# ---------- Core algorithm ----------

def divide_tail_add_division(fixed_cnt: int, work_division: List[Tuple[int, int]],
                             result: List[List[Tuple[int, int]]]) -> None:
    """
    Add the current division if not already present.
    Only the melds (indices fixed_cnt .. 3) are considered; the pair is at index 4.
    """
    # Copy and sort the melds (excluding the pair)
    temp = work_division[:]  # shallow copy of list of packs
    melds = temp[fixed_cnt:4]
    melds_sorted = sorted(melds, key=pack_key)
    temp[fixed_cnt:4] = melds_sorted

    # Check for duplicate
    for d in result:
        existing_melds = d[fixed_cnt:4]
        existing_sorted = sorted(existing_melds, key=pack_key)
        if existing_sorted == melds_sorted:
            return  # duplicate found, discard

    # Not a duplicate, append
    result.append(temp)


def divide_tail(cnt_table: List[int], fixed_cnt: int,
                work_division: List[Tuple[int, int]],
                result: List[List[Tuple[int, int]]]) -> bool:
    """
    Try to form a pair from the remaining tiles.
    Returns True if at least one solution is found.
    """
    for t in ALL_TILES:
        if cnt_table[t] >= 2:
            cnt_table[t] -= 2
            if all(c == 0 for c in cnt_table):
                # All tiles used; set the pair
                work_division[4] = make_pack(PAIR, t)
                divide_tail_add_division(fixed_cnt, work_division, result)
                cnt_table[t] += 2
                return True
            cnt_table[t] += 2
    return False


def is_division_branch_exist(fixed_cnt: int, step: int,
                             work_division: List[Tuple[int, int]],
                             result: List[List[Tuple[int, int]]]) -> bool:
    """
    Check if the current prefix of melds (step melds, starting at fixed_cnt)
    is already present as a subset in any existing division.
    Used for pruning.
    """
    if not result or step < 3:
        return False

    current_melds = work_division[fixed_cnt:fixed_cnt+step]
    current_sorted = sorted(current_melds, key=pack_key)
    current_counter = Counter(current_sorted)

    for d in result:
        existing_melds = d[fixed_cnt:4]
        existing_sorted = sorted(existing_melds, key=pack_key)
        existing_counter = Counter(existing_sorted)
        # Check if current multiset is a subset of existing
        if all(current_counter[k] <= existing_counter[k] for k in current_counter):
            return True
    return False


def divide_recursively(cnt_table: List[int], fixed_cnt: int, step: int,
                       work_division: List[Tuple[int, int]],
                       result: List[List[Tuple[int, int]]]) -> bool:
    """
    Recursively build melds.
    Returns True if at least one complete division is found.
    """
    idx = step + fixed_cnt
    if idx == 4:
        # All 4 melds are formed; now try to make a pair
        return divide_tail(cnt_table, fixed_cnt, work_division, result)

    ret = False
    for t in ALL_TILES:
        if cnt_table[t] == 0:
            continue

        # Pung
        if cnt_table[t] >= 3:
            work_division[idx] = make_pack(PUNG, t)
            if not is_division_branch_exist(fixed_cnt, step+1, work_division, result):
                cnt_table[t] -= 3
                if divide_recursively(cnt_table, fixed_cnt, step+1, work_division, result):
                    ret = True
                cnt_table[t] += 3

        # Chow (only for numbered suits)
        if is_numbered_suit(t):
            rank = t % 9
            if rank <= 6:  # t+1 and t+2 are in the same suit
                if cnt_table[t+1] > 0 and cnt_table[t+2] > 0:
                    # Store the middle tile (t+1) as in the original code
                    work_division[idx] = make_pack(CHOW, t+1)
                    if not is_division_branch_exist(fixed_cnt, step+1, work_division, result):
                        cnt_table[t] -= 1
                        cnt_table[t+1] -= 1
                        cnt_table[t+2] -= 1
                        if divide_recursively(cnt_table, fixed_cnt, step+1, work_division, result):
                            ret = True
                        cnt_table[t] += 1
                        cnt_table[t+1] += 1
                        cnt_table[t+2] += 1

    return ret


def divide_win_hand(standing_tiles: List[int],
                    fixed_packs: List[Tuple[int, int]] = None) -> Tuple[bool, List[List[Tuple[int, int]]]]:
    """
    Main entry point.
    :param standing_tiles: list of tile indices (0-33) in the hand (excluding fixed melds)
    :param fixed_packs: list of already formed melds (e.g., from calls)
    :return: (success, list of divisions) where each division is a list of 5 packs.
    """
    if fixed_packs is None:
        fixed_packs = []
    fixed_cnt = len(fixed_packs)

    # Build count table from standing tiles (ignore flowers >33)
    cnt_table = [0] * TILE_COUNT
    for tile in standing_tiles:
        if tile < TILE_COUNT:
            cnt_table[tile] += 1

    result = []
    # Initialize work_division with fixed packs and placeholders for the remaining slots
    work_division = fixed_packs + [None] * (5 - fixed_cnt)

    success = divide_recursively(cnt_table, fixed_cnt, 0, work_division, result)
    return success, result


# ---------- Tensor input wrapper ----------

def divide_from_tensors(hand_tensor: torch.Tensor,
                        fixed_melds_tensor: torch.Tensor) -> Tuple[bool, List[List[Tuple[int, int]]]]:
    """
    Parameters:
        hand_tensor      : torch.Tensor of shape (42,) – counts of standing tiles.
                           Only the first 34 indices are used (standard tiles); flowers (34–41) are ignored.
        fixed_melds_tensor: torch.Tensor of shape (4, 42) – each row is a count vector for a fixed meld.
                           A row with all zeros is ignored; valid meld rows must sum to 3.
                           Pung:  e.g., [3,0,…] for a pung of tile 0.
                           Chow: e.g., [1,1,1,0,…] for a chow of tiles t, t+1, t+2.
    Returns:
        (success, divisions) where divisions is a list of all distinct divisions.
    """
    # 1. Extract standing tiles from the hand tensor (first 34 entries)
    hand_counts = hand_tensor[:TILE_COUNT].tolist()
    standing_tiles = []
    for tile, cnt in enumerate(hand_counts):
        standing_tiles.extend([tile] * cnt)

    # 2. Parse fixed melds from the 4x42 tensor
    fixed_packs = []
    for row in fixed_melds_tensor:
        row_counts = row[:TILE_COUNT].tolist()
        total = sum(row_counts)
        if total == 0:
            continue                     # empty row – ignore

        # Try pung: one tile count == 3
        pung_tile = None
        for tile, cnt in enumerate(row_counts):
            if cnt == 3:
                pung_tile = tile
                break
        if pung_tile is not None:
            fixed_packs.append(make_pack(PUNG, pung_tile))
            continue

        # Try chow: three consecutive numbered tiles each count = 1
        chow_found = False
        for tile in range(TILE_COUNT):
            if is_numbered_suit(tile):
                rank = tile % 9
                if rank <= 6:   # t, t+1, t+2 are all valid
                    if (row_counts[tile] == 1 and
                        row_counts[tile+1] == 1 and
                        row_counts[tile+2] == 1):
                        # Store the middle tile (as in the original algorithm)
                        fixed_packs.append(make_pack(CHOW, tile+1))
                        chow_found = True
                        break
        if not chow_found:
            raise ValueError(f"Invalid fixed meld row: {row_counts}")

    # 3. Call the core algorithm
    return divide_win_hand(standing_tiles, fixed_packs)

# ---------- Example usage ----------
if __name__ == "__main__":
    # Example hand: 14 tiles (standing) – a complete winning hand with no fixed melds.
    hand = [
        1, 2, 3,   # 2-3-4m chow
        13, 13, 13, # 5p pung
        23, 24, 25, # 6s-7s-8s chow
        27, 27      # pair of East
    ]
    # Build hand tensor (42 dims)
    hand_tensor = torch.zeros(42, dtype=torch.int)
    for tile in hand:
        hand_tensor[tile] += 1

    # No fixed melds – tensor of zeros (4x42)
    fixed_tensor = torch.zeros((4, 42), dtype=torch.int)
    fixed_tensor[0] = 3

    success, divisions = divide_from_tensors(hand_tensor, fixed_tensor)
    print(f"Success: {success}")
    print(f"Number of divisions: {len(divisions)}")
    for i, div in enumerate(divisions):
        print(f"Division {i+1}:")
        for j, pack in enumerate(div):
            if pack is not None:
                print(f"  {j}: {pack_to_str(pack)}")
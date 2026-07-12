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

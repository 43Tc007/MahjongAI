import torch
from mahjong_helper import *
from visualizer import *
import pygame
from sys import exit
from game_and_players import *
import time

pygame.init()
screen = pygame.display.set_mode((800, 800))

clock = pygame.time.Clock()

font_path = "C:/Windows/Fonts/seguisym.ttf"
font = pygame.font.Font(font_path, 48)

def string_to_surface_rect(s: str, center: Tuple[int, int], angle: int):
    surface = font.render(s, False, 'black')
    surface = pygame.transform.rotozoom(surface, angle, 1)
    rect = surface.get_rect(center=center)
    return surface, rect

def hands_to_surface_rect(hand: torch.Tensor, player_idx: int):
    positions = [
        (400, 750),
        (750, 400),
        (400, 50),
        (50, 400)
    ]
    angles = [
        0, 
        90,
        180,
        270
    ]
    return string_to_surface_rect(
        tensor_to_tiles_string(hand), 
        center=positions[player_idx], 
        angle=angles[player_idx]
    )

def crop_surface(surface: pygame.Surface) -> pygame.Surface:
    """Return a new surface cropped to the non-transparent area."""
    bbox = surface.get_bounding_rect()
    if bbox.width == 0 or bbox.height == 0:
        return pygame.Surface((0, 0), pygame.SRCALPHA)
    return surface.subsurface(bbox).copy()

def discard_to_surf_rect(log: torch.Tensor):
    discards: List[List[str]] = [[] for _ in range(4)]
    for line_number in range(game.arbiter.get_logline()):
        if log[line_number].sum() == 2 and not is_subsequently_called(state, line_number):
            temp = torch.nonzero(log[line_number])
            tile, player_idx = int(temp[0, 0].item()), int((temp[1, 0] - 42).item())
            discards[player_idx].append(tiles_unicode[tile])
    discard_strings: List[str] = ["".join(discards[i]) for i in range(4)]

    # New positions & angles as requested
    discard_positions = [
        (300, 500),  # player 0 (bottom)
        (500, 500),  # player 1 (right)
        (500, 300),  # player 2 (top)
        (300, 300)   # player 3 (left)
    ]
    angles = [0, -90, -180, -270]          # rotation (negative for clockwise)
    anchors = ['topleft', 'bottomleft', 'bottomright', 'topright']

    surfaces_rects = []
    for i, dstr in enumerate(discard_strings):
        if not dstr:
            surf = pygame.Surface((0, 0), pygame.SRCALPHA)
            rect = surf.get_rect()
            setattr(rect, anchors[i], discard_positions[i])
            surfaces_rects.append((surf, rect))
            continue

        # Split into rows of 6 tiles
        chunk_size = 6
        chunks = [dstr[j:j+chunk_size] for j in range(0, len(dstr), chunk_size)]

        # Render each row, crop it tightly, and collect the cropped surfaces
        cropped_rows = []
        for chunk in chunks:
            row_surf = font.render(chunk, False, 'black')
            cropped_row = crop_surface(row_surf)
            cropped_rows.append(cropped_row)

        # Stack the cropped rows vertically with no extra space
        if not cropped_rows:
            continue
        max_width = max(r.get_width() for r in cropped_rows)
        total_height = sum(r.get_height() for r in cropped_rows)
        combined = pygame.Surface((max_width, total_height), pygame.SRCALPHA)
        y_offset = 0
        for row in cropped_rows:
            combined.blit(row, (0, y_offset))
            y_offset += row.get_height()

        # Rotate the combined surface (clockwise by the given angle)
        rotated = pygame.transform.rotate(combined, -angles[i])  # pygame rotates CCW

        # Crop the final rotated surface to remove any rotation‑added padding
        cropped = crop_surface(rotated)

        # Position the chosen corner exactly at the discard position
        rect = cropped.get_rect()
        setattr(rect, anchors[i], discard_positions[i])
        surfaces_rects.append((cropped, rect))

    return surfaces_rects

def melds_and_flowers_to_surface_rects(state: GameState) -> List[Tuple[pygame.Surface, pygame.Rect]]:
    """Return a list of (surface, rect) for each player's melds and flowers combined."""
    results = []
    # Positions slightly inward from each player's hand
    positions = [
        (400, 700),   # player 0 (bottom)
        (700, 400),   # player 1 (right)
        (400, 100),   # player 2 (top)
        (100, 400)    # player 3 (left)
    ]
    angles = [0, 90, 180, 270]

    for player_idx in range(4):
        flower_tensor = state.flowers[player_idx]
        flower_str = tensor_to_tiles_string(flower_tensor) if flower_tensor.sum() > 0 else ""

        melds = state.melds[player_idx]
        meld_str = " ".join(tensor_to_tiles_string(m) for m in melds) if melds else ""

        combined = ""
        if flower_str:
            combined += flower_str
        if meld_str:
            if combined:
                combined += " "
            combined += meld_str

        if combined:
            surf, rect = string_to_surface_rect(
                combined,
                center=positions[player_idx],
                angle=angles[player_idx]
            )
            results.append((surf, rect))
        # Skip players with nothing to display

    return results

def render_game_state(state: GameState):

   # game information
    square_rect = pygame.Rect(0, 0, 200, 200)
    square_rect.center = (400, 400)
    pygame.draw.rect(screen, 'grey', square_rect)
    game_info_string = \
    f"""{['E', 'S', 'W', 'N'][state.round_wind]} {state.game_wind + 1} {state.wall_remaining}"""
    game_info_surface = font.render(game_info_string, False, 'white')
    screen.blit(game_info_surface, square_rect)

    # discard
    for surf, rect in discard_to_surf_rect(state.log):
        screen.blit(surf, rect)

    # meld and flowers
    for surf, rect in melds_and_flowers_to_surface_rects(state):
        screen.blit(surf, rect)
    # for player_idx in range(4):
    #     flower_tensor = state.flowers[player_idx]
    #     flower_str = tensor_to_tiles_string(flower_tensor) if flower_tensor.sum() > 0 else ""

    #     melds = state.melds[player_idx]
    #     meld_str = " ".join(tensor_to_tiles_string(m) for m in melds) if melds else ""

    #     # plain concatenation: flowers then melds, with a space if both exist
    #     combined = ""
    #     if flower_str:
    #         combined += flower_str
    #     if meld_str:
    #         if combined:
    #             combined += " "
    #         combined += meld_str

    #     if combined:
    #         # positions slightly inward from each hand
    #         positions = [
    #             (400, 700),   # player 0 (bottom)
    #             (700, 400),   # player 1 (right)
    #             (400, 100),   # player 2 (top)
    #             (100, 400)    # player 3 (left)
    #         ]
    #         angles = [0, 90, 180, 270]
    #         surf, rect = string_to_surface_rect(combined, center=positions[player_idx], angle=angles[player_idx])
    #         screen.blit(surf, rect)
    # # hand
    for player_idx, hand in enumerate(state.hands):
        hand_surf, hand_rect = hands_to_surface_rect(hand, player_idx)
        screen.blit(hand_surf, hand_rect)

    

game = MahjongGame(0, 0, [RandomPlayer() for _ in range(4)])
state = game.arbiter.state

while True:
    # pygame quit block
    screen.fill('white')
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
    if not game.terminated:
        time.sleep(0.1)
        game.step()
            
    render_game_state(state)
    pygame.display.update()
    clock.tick(60)
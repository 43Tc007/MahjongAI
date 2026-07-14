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
font = pygame.font.Font(font_path, 45)

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


def render_game_state(state: GameState):
   # game information

    square_rect = pygame.Rect(0, 0, 200, 200)
    square_rect.center = (400, 400)
    pygame.draw.rect(screen, 'grey', square_rect)
    game_info_string = \
    f"""{['EAST', 'SOUTH', 'WEST', 'NORTH'][game.arbiter.state.round_wind]} {game.arbiter.state.game_wind + 1} {game.arbiter.state.wall_remaining}"""
    game_info_surface = font.render(game_info_string, False, 'white')
    screen.blit(game_info_surface, square_rect)


    for player_idx, hand in enumerate(state.hands):
        surf, rect = hands_to_surface_rect(hand, player_idx)
        screen.blit(surf, rect)

    

game = MahjongGame(0, 0, [RandomPlayer() for _ in range(4)])
state = game.arbiter.state

while True:
    # pygame quit block
    screen.fill('white')
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    time.sleep(1)
    game.step()
    render_game_state(state)

    pygame.display.update()
    clock.tick(60)
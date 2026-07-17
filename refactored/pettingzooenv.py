import gymnasium
import numpy as np
import pygame
from gymnasium import spaces
from pettingzoo import AECEnv
from pettingzoo.utils import AgentSelector
from gymnasium.spaces import Discrete
from gymnasium.utils import seeding
from refactored.mahjong_helper_2 import GameState, EAST, SOUTH, WEST, NORTH, game_state_mask, game_state_array
from refactored.pygame_visualizer import render_game_state
from typing import List
from mahjong_helper_2 import *

class MahjongGameEnv(AECEnv):
    
    metadata = {"render_modes": ["human"], "name": "MahjongV0"}

    def __init__(self, render_mode=None):
        """
        The init method takes in environment arguments and
         should define the following attributes:
        - possible_agents
        - render_mode

        Note: as of v1.18.1, the action_spaces and observation_spaces attributes are deprecated.
        Spaces should be defined in the action_space() and observation_space() methods.
        If these methods are not overridden, spaces will be inferred from self.observation_spaces/action_spaces, raising a warning.

        These attributes should not be changed after initialization.
        """
        self.possible_agents = [f"player_{i}" for i in range(4)]
        self.agents = self.possible_agents[:]
        self.agent_name_mapping = {name: i for i, name in enumerate(self.possible_agents)}

        self.render_mode = render_mode
        self.gamestate: GameState = GameState(
            round_wind=EAST,
            game_wind=EAST,
            current_player=EAST,
            wall_remaining=144,
        )
        if render_mode == "human":
            pygame.init()
            self.screen = pygame.display.set_mode((800, 800))
            pygame.display.set_caption("Mahjong Environment")
            self.font = pygame.font.Font("C:/Windows/Fonts/seguisym.ttf", 48)

    def observation_space(self, agent) -> gymnasium.Space:
        return spaces.Box(low=0, high=255, shape=(156, 46), dtype=np.uint8)
    
    def action_space(self, agent) -> gymnasium.Space:
        return Discrete(74)
    
    def render(self):
        """
        Render the current game state in human mode using the pygame visualizer.
        """
        if self.render_mode is None:
            gymnasium.logger.warn(
                "You are calling render method without specifying any render mode."
            )
            return None

        elif self.render_mode == "human":
            render_game_state(state=self.gamestate, screen=self.screen, font=self.font)

    def observe(self, agent):
        """
        Observe should return the observation of the specified agent. This function
        should return a sane observation (though not necessarily the most up to date possible)
        at any time after reset() is called.
        """
        return {
            'observation': game_state_mask(self.gamestate, self.agent_name_mapping[agent]),
            'aciton_mask': self.action_mask
        }
    
    def state(self):
        return game_state_array(self.gamestate)
    
    def close(self):
        if pygame.get_init():
            pygame.quit()

    def reset(self, seed: int | None = None, options: dict | None = None) -> None:
        if seed is not None:
            self.np_random, self.np_random_seed = seeding.np_random(seed)
        self.agents = self.possible_agents[:]
        self.rewards = {agent: 0 for agent in self.agents}
        self._cumulative_rewards = {agent: 0 for agent in self.agents}
        self.terminations = {agent: False for agent in self.agents}
        self.truncations = {agent: False for agent in self.agents}
        self.infos = {agent: {} for agent in self.agents}
        if not pygame.get_init():
            pygame.init()

        """
        Our AgentSelector utility allows easy cyclic stepping through the agents list.
        """
        self._agent_selector = AgentSelector(self.agents)
        self.agent_selection = self._agent_selector.next() # return player0
        """
        Insert reset logic
        """
        self.gamestate = GameState(
            round_wind=np.random.randint(0, 4),
            game_wind=np.random.randint(0, 4),
            current_player=EAST,
            wall_remaining=144,
        )
        self.action_mask: np.ndarray = np.zeros(74, dtype=np.uint8)
        self.deal_hands()
    
    def deal_hands(self):
        for player_idx in range(4):
            for _ in range(13):
                while True:
                    tile = draw_tile(self.gamestate, player_idx, self.gamestate.wall)
                    if not is_flower(tile):
                        break
                    execute_flower(self.gamestate, player_idx, tile)

        flower_counts = [int(self.gamestate.flowers[player_idx].sum()) for player_idx in range(4)]
        if any(count >= 7 for count in flower_counts):
            for agent in self.agents:
                self.terminations[agent] = True
                self.rewards[agent] = 0
                self._cumulative_rewards[agent] = 0
                self.infos[agent]["reason"] = "initial_flower"
        self.gamestate.wall_remaining = len(self.gamestate.wall)
    
    def step(self, action) -> None:
        pass
    
    
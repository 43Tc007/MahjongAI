import gymnasium
import numpy as np
import pygame
from gymnasium import spaces
from pettingzoo import AECEnv
from pettingzoo.utils import AgentSelector
from gymnasium.spaces import Discrete
from gymnasium.utils import seeding
from mahjong_helper import GameState, EAST, SOUTH, WEST, NORTH, game_state_mask, game_state_array
from pygame_visualizer import render_game_state
from typing import List
from mahjong_helper import *
from hand_divisor import divide_from_tensors
from fan_calculator import calculate_fan
from copy import deepcopy

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
        """
        First 34 are discard of the 34 different tiles.
        Another 34 for addkan / ankan
        Then tile-2, tile-1 chow for the discard tile discarded by others
            tile-1, tile+1 chow,
            tile + 1, tile+2 chow
            pon 
            ming kan
            ron / tsumo depending if the current player is the agent
            pass
        """
        return Discrete(75)
    
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
            'action_mask': self.action_mask
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
        self.action_mask: np.ndarray = np.zeros(75, dtype=np.uint8)
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
    
    def generate_action_mask(self, player_idx: int, target_tile: int | None = None) -> np.ndarray:
        action_mask = np.zeros(75, dtype=np.uint8)
        action_mask[74] = 1
        if self.gamestate.phase == WAIT_TSUMO_ADD_KAN_AN_KAN:
            # ADD KAN / AN KAN
            for tile in range(34):
                if (self.gamestate.hands[player_idx][tile] == 1 and tile in self.gamestate.addkanable_tiles) or self.gamestate.hands[player_idx][tile] == 4: 
                    action_mask[tile + 34] = 1
            # TSUMO
            assert target_tile is not None
            fan = calculate_fan(self.gamestate, player_idx, target_tile)
            if fan >= 3:
                action_mask[73] = 1

        elif self.gamestate.phase == DISCARD:
            action_mask[:42] = (self.gamestate.hands[player_idx] != 0).astype(int)

        elif self.gamestate.phase == WAIT_RESPONSE:
            assert target_tile is not None
            # chow
            if ((self.gamestate.current_player - player_idx) % 4 == 3 and target_tile <= 26):

                if (self.gamestate.hands[player_idx][target_tile - 2] >= 1 and 
                    self.gamestate.hands[player_idx][target_tile - 1] >= 1 and 
                    target_tile // 9 == (target_tile - 2) // 9 and
                    target_tile // 9 == (target_tile - 1) // 9
                ):
                    action_mask[68] = 1

                if (self.gamestate.hands[player_idx][target_tile - 1] >= 1 and 
                    self.gamestate.hands[player_idx][target_tile + 1] >= 1 and 
                    target_tile // 9 == (target_tile - 1) // 9 and
                    target_tile // 9 == (target_tile + 1) // 9
                ):
                    action_mask[69] = 1

                if (self.gamestate.hands[player_idx][target_tile + 1] >= 1 and 
                    self.gamestate.hands[player_idx][target_tile + 2] >= 1 and 
                    target_tile // 9 == (target_tile + 1) // 9 and
                    target_tile // 9 == (target_tile + 2) // 9
                ):
                    action_mask[70] = 1
            # pung
            if self.gamestate.hands[player_idx][target_tile] >= 2:
                action_mask[71] = 1
            # ming kan
            if self.gamestate.hands[player_idx][target_tile] >= 3:
                action_mask[72] = 1
            # ron
            copy_gamestate = deepcopy(self.gamestate)
            copy_gamestate.hands[player_idx][target_tile] += 1
            if calculate_fan(copy_gamestate, player_idx, target_tile) >= 3:
                action_mask[73] = 1
        else:
            assert target_tile is not None
            if calculate_fan(self.gamestate, player_idx, target_tile) >= 3:
                action_mask[73] = 1

        return action_mask
    
    def terminate_game(self, target_tile: int = -1, winnning_player_idx: int = -1, losing_player_idx: int = -1, terminate_type="exhausted"):
        payout = {
            3 : 1,
            4 : 2,
            5 : 3,
            6 : 4,
            7 : 6,
            8 : 8,
            9 : 12,
            10 : 16,
            11 : 24,
            12 : 32,
            13 : 48
        }

        if terminate_type == "tsumo":
            fan = calculate_fan(self.gamestate, winnning_player_idx, target_tile)
            winner = self.agents[winnning_player_idx]
            for agent in self.agents:
                self.terminations[agent] = True
                if agent == winner:
                    self.rewards[agent] = payout[fan] * 1.5
                else:
                    self.rewards[agent] = - payout[fan] * 0.5
            self.infos[winner] = {'win_type': 'tsumo', 'fan': fan}
        elif terminate_type == "ron":
            fan = calculate_fan(self.gamestate, winnning_player_idx, target_tile)
            winner = self.agents[winnning_player_idx]
            loser = self.agents[losing_player_idx]
            for agent in self.agents:
                self.terminations[agent] = True
                if agent == winner:
                    self.rewards[agent] = payout[fan] 
                elif agent == loser:
                    self.rewards[agent] = - payout[fan] 
                else:
                    self.rewards[agent] = 0
            self.infos[winner] = {'win_type': 'ron', 'fan': fan}
        elif terminate_type == "exhausted":
            for agent in self.agents:
                self.terminations[agent] = True
                self.rewards = {agent: 0 for agent in self.agents}
                self.infos[agent] = {'win_type': 'draw', 'fan': 0}   
        return  # exit step, episode ends
    
    
            
    def step(self, action) -> None:
        if self.gamestate.phase == WAIT_TSUMO_ADD_KAN_AN_KAN:
            if 34 <= int(action) <= 67:
                tile = int(action) - 34
                if tile in self.gamestate.addkanable_tiles:
                    execute_add_kan(self.gamestate, int(self.agent_selection), tile)
                else:
                    execute_an_kan(self.gamestate, int(self.agent_selection), tile)
            elif int(action) == 73:
                self.terminate_game(target_tile=self.gamestate.last_drawn, winnning_player_idx=self.gamestate.current_player, terminate_type="tsumo")
            else:
                assert int(action) == 74
        elif self.gamestate.phase == DISCARD:
            execute_discard(self.gamestate, int(self.agent_selection), int(action))
        elif self.gamestate.phase == WAIT_RESPONSE: # phase is WAIT_RESPONSE
            self.gamestate.action_array[int(action)] = self.agent_name_mapping[self.agent_selection]
        else:
            if int(action) == 73:
                self.terminate_game(target_tile=self.gamestate.last_drawn, winnning_player_idx=self.gamestate.current_player, terminate_type="tsumo")
            else:
                idxs = np.nonzero(self.gamestate.hands[self.gamestate.current_player][34:])[0]
                tile = int(34 + idxs[0])
                execute_flower(self.gamestate, self.gamestate.current_player, tile=tile)

        #  ... update until next decision has to be made
        while not self.terminations[self.agent_selection]:
            if self.gamestate.phase == WAIT_TSUMO_ADD_KAN_AN_KAN:
                self.gamestate.phase = DISCARD
                self.action_mask = self.generate_action_mask(self.agent_name_mapping[self.agent_selection])
                break

            if self.gamestate.phase == DISCARD:
                self.gamestate.phase = WAIT_RESPONSE
                self.gamestate.action_array = np.zeros(shape=(75,))

            if self.gamestate.phase == WAIT_RESPONSE:
                self.agent_selection = self._agent_selector.next()
                # phase end
                if self.agent_name_mapping[self.agent_selection] == self.gamestate.current_player:
                    # evaluates the action list, and do the action
                    if self.gamestate.action_array[73]: # if ron, terminate
                        self.terminate_game(self.gamestate.last_discard, self.gamestate.action_array[72], self.gamestate.current_player, terminate_type="ron")
                        break
                    elif self.gamestate.wall_remaining == 0:
                        self.terminate_game(terminate_type="exhausted")
                        break
                    elif self.gamestate.action_array[72]: 
                        execute_ming_kan(self.gamestate, self.agent_name_mapping[self.gamestate.action_array[72]], self.gamestate.last_discard)
                        self.agent_selection = self.agents[self.gamestate.action_array[72]]
                        self._agent_selector.reset()
                        self.gamestate.current_player = self.agent_name_mapping[self.agent_selection]
                        self.gamestate.phase = WAIT_HUA_HU
                    elif self.gamestate.action_array[71]:
                        execute_pon(self.gamestate, self.agent_name_mapping[self.gamestate.action_array[71]], self.gamestate.last_discard)
                        self.agent_selection = self.agents[self.gamestate.action_array[71]]
                        self._agent_selector.reset()
                        self.gamestate.current_player = self.agent_name_mapping[self.agent_selection]
                        self.gamestate.phase = WAIT_TSUMO_ADD_KAN_AN_KAN
                    elif self.gamestate.action_array[70]:
                        execute_chow(self.gamestate, self.agent_name_mapping[self.gamestate.action_array[70]], self.gamestate.last_discard, [self.gamestate.last_discard-2, self.gamestate.last_discard-1])
                        self.agent_selection = self.agents[self.gamestate.action_array[70]]
                        self._agent_selector.reset()
                        self.gamestate.current_player = self.agent_name_mapping[self.agent_selection]
                        self.gamestate.phase = WAIT_TSUMO_ADD_KAN_AN_KAN
                    elif self.gamestate.action_array[69]:
                        execute_chow(self.gamestate, self.agent_name_mapping[self.gamestate.action_array[69]], self.gamestate.last_discard, [self.gamestate.last_discard-1, self.gamestate.last_discard+1])
                        self.agent_selection = self.agents[self.gamestate.action_array[69]]
                        self._agent_selector.reset()
                        self.gamestate.current_player = self.agent_name_mapping[self.agent_selection]
                        self.gamestate.phase = WAIT_TSUMO_ADD_KAN_AN_KAN
                    elif self.gamestate.action_array[68]:
                        execute_chow(self.gamestate, self.agent_name_mapping[self.gamestate.action_array[68]], self.gamestate.last_discard, [self.gamestate.last_discard+1, self.gamestate.last_discard+2])
                        self.agent_selection = self.agents[self.gamestate.action_array[68]]
                        self._agent_selector.reset()
                        self.gamestate.current_player = self.agent_name_mapping[self.agent_selection]
                        self.gamestate.phase = WAIT_TSUMO_ADD_KAN_AN_KAN
                else:
                    self.action_mask = self.generate_action_mask(self.agent_name_mapping[self.agent_selection], self.gamestate.last_discard)
                    if self.action_mask.sum() >= 2:
                        break

            if self.gamestate.phase == WAIT_HUA_HU:
                if self.gamestate.wall_remaining == 0:
                    self.terminate_game(terminate_type="exhausted")
                    break
                drawn_tile = draw_tile(self.gamestate, self.gamestate.current_player, self.gamestate.wall)
                while is_flower(drawn_tile):
                    self.gamestate.phase = WAIT_HUA_HU
                    self.action_mask = self.generate_action_mask(self.gamestate.current_player, drawn_tile)
                    if self.action_mask.sum() >= 2:
                        break
                    else:
                        execute_flower(self.gamestate, self.agent_selection, drawn_tile)
                        if self.gamestate.wall_remaining == 0:
                            self.terminate_game(terminate_type="exhausted")
                            break
                        drawn_tile = draw_tile(self.gamestate, self.gamestate.current_player, self.gamestate.wall)
                self.gamestate.phase = WAIT_TSUMO_ADD_KAN_AN_KAN
                self.action_mask = self.generate_action_mask(self.gamestate.current_player, drawn_tile)
                if self.action_mask.sum() >= 2:
                    break
"""
Train an RL agent on the custom Mahjong environment using Ray RLlib.
"""

import os
from pathlib import Path

import ray
import torch
import torch.nn as nn
from ray import tune
from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.env.wrappers.pettingzoo_env import PettingZooEnv
from ray.rllib.models import ModelCatalog
from ray.rllib.models.torch.torch_modelv2 import TorchModelV2
from ray.rllib.utils.framework import try_import_torch
from ray.tune.registry import register_env
from gymnasium.spaces import Discrete, Dict, Box
import numpy as np

# Import your custom environment
from pettingzooenv import MahjongGameEnv

torch, nn = try_import_torch()


class MahjongCNNModel(TorchModelV2, nn.Module):
    """
    Custom neural network for Mahjong environment.

    Input: Dict with keys:
        - 'observation': shape (156, 46) uint8 grid
        - 'action_mask': shape (75,) uint8 (1 = allowed)
    Output: logits over 75 actions, with invalid actions masked to -inf.
    """

    def __init__(self, obs_space, act_space, num_outputs, *args, **kwargs):
        TorchModelV2.__init__(self, obs_space, act_space, num_outputs, *args, **kwargs)
        nn.Module.__init__(self)

        # The observation grid: treat as 1-channel image (H=156, W=46)
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, stride=2),   # -> (32, 77, 22)
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2),  # -> (64, 38, 10)
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),  # -> (64, 36, 8)
            nn.ReLU(),
        )
        # Compute flattened size: 64 * 36 * 8 = 18432
        self.flatten = nn.Flatten()
        self.fc = nn.Sequential(
            nn.Linear(18432, 512),
            nn.ReLU(),
        )
        self.policy = nn.Linear(512, num_outputs)
        self.value = nn.Linear(512, 1)

    def forward(self, input_dict, state, seq_lens):
        # Extract observation (grid) and action mask
        obs = input_dict["obs"]["observation"]   # shape: (batch, 156, 46)
        mask = input_dict["obs"]["action_mask"]  # shape: (batch, 75)

        # Add channel dimension and convert to float
        obs = obs.unsqueeze(1).float()           # (batch, 1, 156, 46)

        # Forward through conv layers
        x = self.conv(obs)
        x = self.flatten(x)
        x = self.fc(x)

        # Compute logits and value
        logits = self.policy(x)
        self._value_out = self.value(x).flatten()

        # Apply action mask: set logits of invalid actions to -inf
        # mask is 1 for allowed, 0 for disallowed
        mask = mask.bool()
        logits[~mask] = -1e9   # effectively -inf

        return logits, state

    def value_function(self):
        return self._value_out


def env_creator(args=None):
    """
    Create the Mahjong environment and wrap it with RLlib's PettingZoo wrapper.
    """
    env = MahjongGameEnv()
    # The wrapper converts AECEnv to RLlib's multi-agent API
    return PettingZooEnv(env)


if __name__ == "__main__":
    ray.init()

    env_name = "MahjongV0"

    # Register the environment with tune
    register_env(env_name, lambda config: env_creator(config))

    # Register the custom model
    ModelCatalog.register_custom_model("MahjongCNNModel", MahjongCNNModel)

    # Get observation and action spaces from a dummy env to pass to the config
    dummy_env = env_creator()
    obs_space = dummy_env.observation_space
    act_space = dummy_env.action_space

    # PPO configuration
    config = (
        PPOConfig()
        .environment(
            env=env_name,
            clip_actions=False,          # we mask instead
            disable_env_checking=True,
        )
        .rollouts(
            num_rollout_workers=4,
            rollout_fragment_length=128,
        )
        .training(
            train_batch_size=512,
            lr=2e-5,
            gamma=0.99,
            lambda_=0.9,
            use_gae=True,
            clip_param=0.4,
            grad_clip=None,
            entropy_coeff=0.1,
            vf_loss_coeff=0.25,
            sgd_minibatch_size=64,
            num_sgd_iter=10,
        )
        .framework("torch")
        .resources(num_gpus=int(os.environ.get("RLLIB_NUM_GPUS", "0")))
        .multi_agent(
            policies={
                "default_policy": (None, obs_space, act_space, {})
            },
            policy_mapping_fn=lambda agent_id, *args, **kwargs: "default_policy",
        )
        .model(
            custom_model="MahjongCNNModel",
        )
    )

    storage_uri = (Path("~/ray_results") / env_name).expanduser().resolve().as_uri()

    tune.run(
        "PPO",
        name="Mahjong_PPO",
        stop={"timesteps_total": 5_000_000},   # adjust as needed
        checkpoint_freq=10,
        storage_path=storage_uri,
        config=config.to_dict(),
    )
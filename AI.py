import numpy as np
from pettingzooenv import MahjongGameEnv, render_game_state  # adjust import if needed
import time
import pygame

pygame.init()
screen = pygame.display.set_mode(size=(800, 800))
font = pygame.font.Font("C:/Windows/Fonts/seguisym.ttf", 48)

def random_agent(env, agent):
    """Select a random legal action for the given agent."""
    obs = env.observe(agent)
    action_mask = obs['action_mask']
    legal_actions = np.where(action_mask == 1)[0]
    if len(legal_actions) == 0:
        # Fallback: pass (action 74) should always be legal
        return 74
    return np.random.choice(legal_actions)

def main():
    # Create environment (set render_mode="human" to see the GUI)
    env = MahjongGameEnv(render_mode=None)  # or None for headless
    env.reset()

    # Loop over episodes
    for episode in range(100):  # play 5 rounds
        env.reset()
        print(f"\n--- Episode {episode+1} ---")
        for agent in env.agent_iter():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
            screen.fill('white')
            render_game_state(env.gamestate, screen, font)
            pygame.display.update()

            # Get observation and action mask for the current agent
            obs = env.observe(agent)
            action_mask = obs['action_mask']

            # Let the agent decide (here: random)
            action = random_agent(env, agent)

            # Step the environment
            env.step(action)


            # If the round ended, break out of the loop (the next reset will start a new one)
            if env.terminations[agent]:
                # Print outcome info
                print(f"Round ended. Rewards: {env.rewards}")
                break

    env.close()

if __name__ == "__main__":
    main()
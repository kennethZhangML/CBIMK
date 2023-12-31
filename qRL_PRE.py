import torch
import torch.nn as nn
import torch.nn.functional as F
import gym
import random
import numpy as np
from collections import deque

class DQN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, output_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x

class ReplayMemory:
    def __init__(self, capacity):
        self.capacity = capacity
        self.memory = deque(maxlen = capacity)

    def push(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        batch = random.sample(self.memory, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            torch.FloatTensor(states),
            torch.LongTensor(actions),
            torch.FloatTensor(rewards),
            torch.FloatTensor(next_states),
            torch.FloatTensor(dones)
        )

    def __len__(self):
        return len(self.memory)


class DQNAgent:
    def __init__(self, state_size, action_size):
        self.batch_size = 32
        self.memory_size = 1000
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        self.learning_rate = 0.001
        self.target_update = 10

        self.state_size = state_size
        self.action_size = action_size
        self.memory = ReplayMemory(capacity = self.memory_size)

        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.policy = DQN(self.state_size, self.action_size).to(self.device)
        self.target = DQN(self.state_size, self.action_size).to(self.device)
        self.target.load_state_dict(self.policy.state_dict())

        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.RMSprop(self.policy.parameters(), lr = self.learning_rate)

    def choose_action(self, state):
        if np.random.random() < self.epsilon:
            return random.randrange(self.action_size)

        state = torch.FloatTensor(state).unsqueeze(0).to(self.device)

        with torch.no_grad():
            q_values = self.policy(state)
        return q_values.max(1)[1].item()

    def store_memory(self, state, action, reward, next_state, done):
        self.memory.push(state, action, reward, next_state, done)

    def update_nn(self):
        if len(self.memory) < self.batch_size:
            return

        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)

        Q_targets = self.target(next_states).detach().max(1)[0].unsqueeze(1)
        Q_targets = rewards + (self.gamma * Q_targets * (1 - dones))
        Q_expected = self.policy(states).gather(1, actions.unsqueeze(1))

        loss = self.criterion(Q_expected, Q_targets)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    def update_target(self):
        self.target.load_state_dict(self.policy.state_dict())

    def update_epsilon(self):
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def save(self, filename):
        torch.save(self.policy.state_dict(), filename)

    def load(self, filename):
        self.policy.load_state_dict(torch.load(filename))
        self.target.load_state_dict(self.policy.state_dict())
        self.target.eval()

if __name__ == "__main__":
    env = gym.make("CartPole-v1")
    state_size = env.observation_space.shape[0]
    action_size = env.action_space.n

    num_episodes = 1000
    learning_rate = 0.001
    epsilon = 1.0
    discount_factor = 0.99

    agent = DQNAgent(state_size, action_size)

    for episode in range(num_episodes):
        state = env.reset()
        action = agent.choose_action(state)
        done = False
        total_reward = 0

        while not done:
            next_state, reward, done, _ = env.step(action)
            agent.store_memory(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward

            agent.update_nn()

            if episode % agent.target_update == 0:
                agent.update_target()

            agent.update_epsilon()

        print("Episode {}/{}, Total Rewards: {}".format(episode + 1, num_episodes, total_reward))

    agent.save("trained_qTrade.pth")

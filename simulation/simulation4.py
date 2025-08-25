import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import random

GRID_SIZE = 100
DECAY_RATE = 0.02  # how fast cells "fade" back to unsurveyed

class Environment:
    def __init__(self, grid_size=GRID_SIZE, obstacles=None):
        self.grid_size = grid_size
        self.coverage = np.zeros((grid_size, grid_size))
        if obstacles is not None:
            # use provided obstacle layout
            self.obstacles = obstacles.copy()
        else:
            self.obstacles = np.zeros((grid_size, grid_size), dtype=bool)

    def decay(self):
        self.coverage = np.clip(self.coverage - DECAY_RATE, 0, 1)


class Drone:
    def __init__(self, env, start_x, start_y, x_start, x_end, type, speed=1, search_area=1):
        self.env = env
        self.x = start_x
        self.y = start_y
        self.x_start = x_start
        self.x_end = x_end
        self.speed = speed
        self.search_area = search_area
        self.dir = 1  # start moving right

    def step(self):
        r = self.search_area
        for i in range(self.x - r, self.x + r + 1):
            for j in range(self.y - r, self.y + r + 1):
                if 0 <= i < self.env.grid_size and 0 <= j < self.env.grid_size:
                    if not self.env.obstacles[j, i]:
                        self.env.coverage[j, i] = 1.0

        next_x = self.x + self.dir * self.speed
        if self.x_start <= next_x < self.x_end and not self.env.obstacles[self.y, next_x]:
            self.x = next_x
        else:
            next_y = self.y + max(1, self.search_area * 2)
            if next_y < self.env.grid_size and not self.env.obstacles[next_y, self.x]:
                self.y = next_y
                self.dir *= -1


def generate_obstacles(grid_size, num_obstacles):
    obstacles = np.zeros((grid_size, grid_size), dtype=bool)
    for _ in range(num_obstacles):
        x, y = random.randint(0, grid_size-10), random.randint(0, grid_size-10)
        w, h = random.randint(5, 15), random.randint(5, 15)
        obstacles[y:y+h, x:x+w] = True
    return obstacles


def create_drones(env, swarm_size, speed, radius):
    drones = []
    if (swarm_size>1):
        type = "swarm"
    else:
        type = "single"
    strip_width = GRID_SIZE // swarm_size
    for i in range(swarm_size):
        x_start = i * strip_width
        x_end = (i+1) * strip_width if i < swarm_size-1 else GRID_SIZE
        drones.append(Drone(env, x_start, 0, x_start, x_end,
                            type=type, speed=speed, search_area=radius))
    return drones


# --- Setup ---
shared_obstacles = generate_obstacles(GRID_SIZE, 5)

env_single = Environment(obstacles=shared_obstacles)
env_swarm  = Environment(obstacles=shared_obstacles)

drones_single = create_drones(env_single, 1, speed=2, radius=5)
drones_swarm  = create_drones(env_swarm, 5, speed=2, radius=1)

# --- Visualization ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
plt.subplots_adjust(bottom=0.25)

img1 = ax1.imshow(env_single.coverage, cmap='Greens', vmin=0, vmax=1)
ax1.set_title("Single Drone (radius=5)")
img2 = ax2.imshow(env_swarm.coverage, cmap='Greens', vmin=0, vmax=1)
ax2.set_title("Swarm Drones (radius=1)")

ax1.imshow(env_single.obstacles, cmap='gray', alpha=0.5)
ax2.imshow(env_swarm.obstacles, cmap='gray', alpha=0.5)

scat1 = ax1.scatter([d.x for d in drones_single], [d.y for d in drones_single], c='red')
scat2 = ax2.scatter([d.x for d in drones_swarm], [d.y for d in drones_swarm], c='red')


# --- Reset button ---
resetax = plt.axes([0.82, 0.9, 0.1, 0.05])
button = Button(resetax, 'Reset')

def reset(event):
    global env_single, env_swarm, drones_single, drones_swarm, img1, img2, scat1, scat2, shared_obstacles

    shared_obstacles = generate_obstacles(GRID_SIZE, 5)

    env_single = Environment(obstacles=shared_obstacles)
    env_swarm  = Environment(obstacles=shared_obstacles)

    drones_single = create_drones(env_single, 1, speed=2, radius=5)
    drones_swarm  = create_drones(env_swarm, 5, speed=2, radius=1)

    ax1.clear(); ax2.clear()

    img1 = ax1.imshow(env_single.coverage, cmap='Greens', vmin=0, vmax=1)
    img2 = ax2.imshow(env_swarm.coverage, cmap='Greens', vmin=0, vmax=1)

    ax1.imshow(env_single.obstacles, cmap='gray', alpha=0.5)
    ax2.imshow(env_swarm.obstacles, cmap='gray', alpha=0.5)

    scat1 = ax1.scatter([d.x for d in drones_single], [d.y for d in drones_single], c='red')
    scat2 = ax2.scatter([d.x for d in drones_swarm], [d.y for d in drones_swarm], c='red')

    fig.canvas.draw_idle()

button.on_clicked(reset)


def update(frame):
    env_single.decay()
    env_swarm.decay()

    for d in drones_single: d.step()
    for d in drones_swarm: d.step()

    img1.set_data(env_single.coverage)
    img2.set_data(env_swarm.coverage)

    scat1.set_offsets([(d.x, d.y) for d in drones_single])
    scat2.set_offsets([(d.x, d.y) for d in drones_swarm])

    return img1, img2, scat1, scat2

from matplotlib.animation import FuncAnimation
ani = FuncAnimation(fig, update, frames=200, interval=50, blit=False)
plt.show()

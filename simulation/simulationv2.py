import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.widgets import Slider, Button
import random

GRID_SIZE = 32
DECAY_RATE = 0.01  # how fast cells "fade" back to unsurveyed

class Environment:
    def __init__(self, grid_size=GRID_SIZE, num_obstacles=10):
        self.grid_size = grid_size
        self.coverage = np.zeros((grid_size, grid_size))
        self.obstacles = np.zeros((grid_size, grid_size), dtype=bool)
        self.generate_obstacles(num_obstacles)

    def generate_obstacles(self, num_obstacles):
        self.obstacles.fill(False)
        for _ in range(num_obstacles):
            x, y = random.randint(0, self.grid_size-20), random.randint(0, self.grid_size-20)
            w, h = random.randint(5, 20), random.randint(5, 20)
            self.obstacles[y:y+h, x:x+w] = True

    def decay(self):
        self.coverage = np.clip(self.coverage - DECAY_RATE, 0, 1)

    def survey_cell(self, x, y):
        if 0 <= x < self.grid_size and 0 <= y < self.grid_size:
            if not self.obstacles[y, x]:
                self.coverage[y, x] = 1.0

class Drone:
    def __init__(self, env, start_x, start_y, x_start, x_end, speed=1):
        self.env = env
        self.x, self.y = start_x, start_y
        self.x_start = x_start
        self.x_end = x_end
        self.speed = speed
        self.dir = 1  # moving right initially

    def step(self):
        for _ in range(self.speed):  # move "speed" cells per step
            # Survey current cell
            self.env.survey_cell(self.x, self.y)

            # Try to move horizontally
            next_x = self.x + self.dir
            if self.x_start <= next_x < self.x_end and not self.env.obstacles[self.y, next_x]:
                self.x = next_x
            else:
                # Move down one row if possible
                next_y = self.y + 1
                if next_y < self.env.grid_size and not self.env.obstacles[next_y, self.x]:
                    self.y = next_y
                    self.dir *= -1  # reverse zig-zag direction
                else:
                    # stuck at bottom or blocked - stop
                    pass

def create_drones(env, swarm_size, speed):
    drones = []
    strip_width = GRID_SIZE // swarm_size
    for i in range(swarm_size):
        x_start = i * strip_width
        x_end = (i+1) * strip_width if i < swarm_size-1 else GRID_SIZE
        drones.append(Drone(env, x_start, 0, x_start, x_end, speed=speed))
    return drones

# --- Setup ---
env_single = Environment(num_obstacles=10)
env_swarm = Environment(num_obstacles=10)

drones_single = create_drones(env_single, 1, speed=1)
drones_swarm = create_drones(env_swarm, 3, speed=1)

# --- Visualization ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
plt.subplots_adjust(bottom=0.25)

cmap = colors.ListedColormap(['white', 'green'])
bounds = [0, 0.5, 1]
norm = colors.BoundaryNorm(bounds, cmap.N)

img1 = ax1.imshow(env_single.coverage, cmap='Greens', vmin=0, vmax=1)
ax1.set_title("Single Drone")
img2 = ax2.imshow(env_swarm.coverage, cmap='Greens', vmin=0, vmax=1)
ax2.set_title("Swarm Drones")

# obstacle overlay
ax1.imshow(env_single.obstacles, cmap='gray', alpha=0.5)
ax2.imshow(env_swarm.obstacles, cmap='gray', alpha=0.5)

# Sliders
ax_slider1 = plt.axes([0.15, 0.12, 0.65, 0.03])
ax_slider2 = plt.axes([0.15, 0.08, 0.65, 0.03])
ax_slider3 = plt.axes([0.15, 0.04, 0.65, 0.03])

slider_obstacles = Slider(ax_slider1, 'Obstacles', 0, 50, valinit=10, valstep=1)
slider_swarm = Slider(ax_slider2, 'Swarm Size', 1, 10, valinit=3, valstep=1)
slider_speed = Slider(ax_slider3, 'Speed', 1, 5, valinit=1, valstep=1)

# Reset button
resetax = plt.axes([0.82, 0.9, 0.1, 0.05])
button = Button(resetax, 'Reset')

def reset(event):
    global env_single, env_swarm, drones_single, drones_swarm, img1, img2, scat1, scat2

    # Recreate environments
    env_single = Environment(num_obstacles=int(slider_obstacles.val))
    env_swarm = Environment(num_obstacles=int(slider_obstacles.val))

    # Recreate drones
    drones_single = create_drones(env_single, 1, speed=int(slider_speed.val))
    drones_swarm = create_drones(env_swarm, int(slider_swarm.val), speed=int(slider_speed.val))

    # Clear old plots
    ax1.clear()
    ax2.clear()

    # Redraw environments
    img1 = ax1.imshow(env_single.coverage, cmap='Blues', vmin=0, vmax=1)
    img2 = ax2.imshow(env_swarm.coverage, cmap='Blues', vmin=0, vmax=1)

    # Redraw obstacles
    ax1.imshow(env_single.obstacles, cmap='gray', alpha=0.5)
    ax2.imshow(env_swarm.obstacles, cmap='gray', alpha=0.5)

    # Redraw drone scatters
    scat1 = ax1.scatter([d.x for d in drones_single], [d.y for d in drones_single], c='red')
    scat2 = ax2.scatter([d.x for d in drones_swarm], [d.y for d in drones_swarm], c='red')

    # Titles
    ax1.set_title("Single Drone")
    ax2.set_title("Swarm Drones")

    fig.canvas.draw_idle()



button.on_clicked(reset)

def update(frame):
    env_single.decay()
    env_swarm.decay()
    for d in drones_single:
        d.step()
    for d in drones_swarm:
        d.step()
    img1.set_data(env_single.coverage)
    img2.set_data(env_swarm.coverage)
    return img1, img2

from matplotlib.animation import FuncAnimation
ani = FuncAnimation(fig, update, frames=200, interval=50, blit=False)
plt.show()

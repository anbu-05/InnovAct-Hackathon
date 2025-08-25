import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.widgets import Slider, Button
import random

GRID_SIZE = 64
DECAY_RATE = 0.01  # how fast cells "fade" back to unsurveyed

class Environment:
    def __init__(self, grid_size=GRID_SIZE, num_obstacles=10, survey_radius=1):
        self.grid_size = grid_size
        self.coverage = np.zeros((grid_size, grid_size))
        self.obstacles = np.zeros((grid_size, grid_size), dtype=bool)
        self.survey_radius = survey_radius
        self.generate_obstacles(num_obstacles)

    def generate_obstacles(self, num_obstacles):
        self.obstacles.fill(False)
        for _ in range(num_obstacles):
            x, y = random.randint(0, self.grid_size-10), random.randint(0, self.grid_size-10)
            w, h = random.randint(5, 15), random.randint(5, 15)
            self.obstacles[y:y+h, x:x+w] = True

    def decay(self):
        self.coverage = np.clip(self.coverage - DECAY_RATE, 0, 1)

    def survey_cell(self, x, y):
        r = self.survey_radius
        for i in range(x-r, x+r+1):
            for j in range(y-r, y+r+1):
                if 0 <= i < self.grid_size and 0 <= j < self.grid_size:
                    if not self.obstacles[j, i]:
                        self.coverage[j, i] = 1.0

class Drone:
    def __init__(self, env, start_x, start_y, x_start, x_end, speed=1, search_area=1):
        self.env = env
        self.x = start_x
        self.y = start_y
        self.x_start = x_start
        self.x_end = x_end
        self.speed = speed
        self.search_area = search_area
        self.dir = 1  # start moving right

    def step(self):
        # Survey an area instead of a single cell
        r = self.search_area
        for i in range(self.x - r, self.x + r + 1):
            for j in range(self.y - r, self.y + r + 1):
                if 0 <= i < self.env.grid_size and 0 <= j < self.env.grid_size:
                    if not self.env.obstacles[j, i]:
                        self.env.coverage[j, i] = 1.0

        # Move horizontally
        next_x = self.x + self.dir * self.speed
        if self.x_start <= next_x < self.x_end and not self.env.obstacles[self.y, next_x]:
            self.x = next_x
        else:
            # Move down by half search area when hitting boundary/obstacle
            next_y = self.y + max(1, self.search_area // 2)
            if next_y < self.env.grid_size and not self.env.obstacles[next_y, self.x]:
                self.y = next_y
                self.dir *= -1  # zig-zag




def create_drones(env, swarm_size, speed):
    drones = []
    strip_width = GRID_SIZE // swarm_size
    for i in range(swarm_size):
        x_start = i * strip_width
        x_end = (i+1) * strip_width if i < swarm_size-1 else GRID_SIZE
        drones.append(Drone(env, x_start, 0, x_start, x_end, speed=speed))
    return drones

# --- Setup ---
env_single = Environment(num_obstacles=10, survey_radius=10)  # left side radius=10
env_swarm = Environment(num_obstacles=10, survey_radius=1)   # right side radius=1

drones_single = create_drones(env_single, 1, speed=1)
drones_swarm = create_drones(env_swarm, 3, speed=1)

# --- Visualization ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
plt.subplots_adjust(bottom=0.25)

img1 = ax1.imshow(env_single.coverage, cmap='Greens', vmin=0, vmax=1)
ax1.set_title("Single Drone (radius=10)")
img2 = ax2.imshow(env_swarm.coverage, cmap='Greens', vmin=0, vmax=1)
ax2.set_title("Swarm Drones (radius=1)")

ax1.imshow(env_single.obstacles, cmap='gray', alpha=0.5)
ax2.imshow(env_swarm.obstacles, cmap='gray', alpha=0.5)

scat1 = ax1.scatter([d.x for d in drones_single], [d.y for d in drones_single], c='red')
scat2 = ax2.scatter([d.x for d in drones_swarm], [d.y for d in drones_swarm], c='red')

# Sliders
ax_slider1 = plt.axes([0.15, 0.20, 0.65, 0.03])
ax_slider2 = plt.axes([0.15, 0.16, 0.65, 0.03])
ax_slider3 = plt.axes([0.15, 0.12, 0.65, 0.03])

slider_obstacles = Slider(ax_slider1, 'Obstacles', 0, 50, valinit=10, valstep=1)
slider_swarm = Slider(ax_slider2, 'Swarm Size', 1, 10, valinit=3, valstep=1)
slider_speed = Slider(ax_slider3, 'Speed', 1, 5, valinit=1, valstep=1)

# Position them below the existing ones
ax_slider_single_r = plt.axes([0.15, 0.08, 0.65, 0.03], facecolor='lightgoldenrodyellow')
slider_single_r = Slider(ax_slider_single_r, 'Single Radius', 1, 20, valinit=10, valstep=1)

ax_slider_swarm_r = plt.axes([0.15, 0.04, 0.65, 0.03], facecolor='lightgoldenrodyellow')
slider_swarm_r = Slider(ax_slider_swarm_r, 'Swarm Radius', 1, 5, valinit=1, valstep=1)


# Reset button
resetax = plt.axes([0.82, 0.9, 0.1, 0.05])
button = Button(resetax, 'Reset')

def reset(event):
    global env_single, env_swarm, drones_single, drones_swarm, img1, img2, scat1, scat2

    env_single = Environment(num_obstacles=int(slider_obstacles.val),
                             survey_radius=int(slider_single_r.val))
    env_swarm = Environment(num_obstacles=int(slider_obstacles.val),
                            survey_radius=int(slider_swarm_r.val))

    drones_single = create_drones(env_single, 1, speed=int(slider_speed.val))
    drones_swarm = create_drones(env_swarm, int(slider_swarm.val), speed=int(slider_speed.val))

    ax1.clear(); ax2.clear()

    img1 = ax1.imshow(env_single.coverage, cmap='Greens', vmin=0, vmax=1)
    img2 = ax2.imshow(env_swarm.coverage, cmap='Greens', vmin=0, vmax=1)

    ax1.imshow(env_single.obstacles, cmap='gray', alpha=0.5)
    ax2.imshow(env_swarm.obstacles, cmap='gray', alpha=0.5)

    scat1 = ax1.scatter([d.x for d in drones_single], [d.y for d in drones_single], c='red')
    scat2 = ax2.scatter([d.x for d in drones_swarm], [d.y for d in drones_swarm], c='red')

    ax1.set_title(f"Single Drone (radius={int(slider_single_r.val)})")
    ax2.set_title(f"Swarm Drones (radius={int(slider_swarm_r.val)})")

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

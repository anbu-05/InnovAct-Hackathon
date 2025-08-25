# Simulation of drones surveying a 256x256 grid with obstacles
# - Left subplot: single drone
# - Right subplot: swarm of N drones (slider-controlled)
# - Slider controls: obstacle count, swarm size (number of drones), drone speed
# - Cells covered by drones are shaded and fade over time (decay)
# - Drones avoid obstacles reactively (simple collision check and random reheading)
#
# To run: execute this cell in a Jupyter environment (or IPython). The Matplotlib window is interactive.
# Resize the window if controls overlap. Use the sliders to change obstacle count, swarm size and speed.
# Press "Reset" to regenerate obstacles (keeps seed randomization but uses current slider values).
#
# Note: For performance we use a 256x256 grid and update at ~15 FPS. If your machine is slow, reduce grid size.
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation
import math
import random

# -------------------- Parameters --------------------
GRID_SIZE = 50  # 256x256 grid
DEFAULT_OBSTACLES = 2
DEFAULT_SWARM = 5
DEFAULT_SPEED = 1.0  # units per second (adjustable)
SENSOR_RADIUS = 2.0  # units
DECAY_FACTOR = 0.995  # per frame decay multiplier (slower decay)
DT = 0.1  # simulation time step in seconds (smaller -> smoother)

# -------------------- Utility helpers --------------------
def in_bounds(x, y):
    return 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE

def sample_free_position(obstacle_mask, rng=np.random):
    # sample until find free cell (x,y) as floats centered in cell
    for _ in range(10000):
        x = rng.uniform(0, GRID_SIZE)
        y = rng.uniform(0, GRID_SIZE)
        ix, iy = int(x), int(y)
        if in_bounds(ix, iy) and not obstacle_mask[iy, ix]:
            return x, y
    # fallback scan
    ys, xs = np.where(~obstacle_mask)
    idx = rng.choice(len(xs))
    return xs[idx] + 0.5, ys[idx] + 0.5

def make_obstacles(count, rng_seed=None):
    rng = np.random.RandomState(rng_seed)
    mask = np.zeros((GRID_SIZE, GRID_SIZE), dtype=bool)
    for _ in range(count):
        # choose rectangle or circle randomly
        if rng.rand() < 0.6:
            # rectangle
            w = rng.randint(4, 30)
            h = rng.randint(4, 30)
            x = rng.randint(0, GRID_SIZE - w)
            y = rng.randint(0, GRID_SIZE - h)
            mask[y:y+h, x:x+w] = True
        else:
            # circle
            r = rng.randint(3, 18)
            cx = rng.randint(r, GRID_SIZE - r)
            cy = rng.randint(r, GRID_SIZE - r)
            yy, xx = np.ogrid[:GRID_SIZE, :GRID_SIZE]
            circle = (xx - cx)**2 + (yy - cy)**2 <= r*r
            mask[circle] = True
    return mask

def coverage_update_from_drone(coverage, obstacle_mask, x, y):
    # mark grid cells within SENSOR_RADIUS around (x,y) as fully covered (value=1)
    r = SENSOR_RADIUS
    minx = max(0, int(math.floor(x - r)))
    maxx = min(GRID_SIZE-1, int(math.ceil(x + r)))
    miny = max(0, int(math.floor(y - r)))
    maxy = min(GRID_SIZE-1, int(math.ceil(y + r)))
    for iy in range(miny, maxy+1):
        for ix in range(minx, maxx+1):
            if obstacle_mask[iy, ix]:
                continue
            # center of cell at (ix+0.5, iy+0.5)
            cx = ix + 0.5
            cy = iy + 0.5
            if (cx - x)**2 + (cy - y)**2 <= r*r:
                coverage[iy, ix] = 1.0

# -------------------- Drone class --------------------
class Drone:
    def __init__(self, x, y, obstacle_mask, rng=None):
        self.x = x
        self.y = y
        self.obstacle_mask = obstacle_mask
        self.rng = rng or np.random.RandomState()
        # heading in radians
        self.heading = self.rng.uniform(0, 2 * math.pi)
        # small random bias to encourage exploration
        self.turn_bias = self.rng.normal(0, 0.2)
    
    def step(self, speed, dt):
        # try to move forward; if collision would occur, pick a new heading
        nx = self.x + math.cos(self.heading) * speed * dt
        ny = self.y + math.sin(self.heading) * speed * dt
        # check bounds and obstacle collision (sample several points around next pos)
        if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
            # reflect off borders
            self.heading = (self.heading + math.pi * (0.5 + self.rng.rand() * 0.5)) % (2*math.pi)
            return
        if self._position_is_blocked(nx, ny):
            # try small turns until we find free
            turned = False
            for attempt in range(10):
                # random small turn plus bias
                self.heading += (self.rng.randn() * 0.6 + 0.4)
                nx = self.x + math.cos(self.heading) * speed * dt
                ny = self.y + math.sin(self.heading) * speed * dt
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and not self._position_is_blocked(nx, ny):
                    turned = True
                    break
            if not turned:
                # jump to random nearby free position (escape local trap)
                fx, fy = sample_free_position(self.obstacle_mask, rng=self.rng)
                self.x, self.y = fx, fy
                self.heading = self.rng.uniform(0, 2*math.pi)
                return
        # with small probability, slightly change heading to explore
        if self.rng.rand() < 0.15:
            self.heading += self.rng.randn() * 0.4 + self.turn_bias
        # apply move
        self.x = nx
        self.y = ny
    
    def _position_is_blocked(self, x, y):
        # check the grid cells that the drone overlaps (small circle)
        ix = int(x)
        iy = int(y)
        if not in_bounds(ix, iy):
            return True
        # check neighbors as well
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx = ix + dx
                ny = iy + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and self.obstacle_mask[ny, nx]:
                    # if the center-to-center distance is small, treat as blocked
                    if ((nx+0.5 - x)**2 + (ny+0.5 - y)**2) < 1.0:
                        return True
        return False

# -------------------- Simulation state --------------------
class Simulation:
    def __init__(self, obstacle_count=DEFAULT_OBSTACLES, swarm_size=DEFAULT_SWARM, speed=DEFAULT_SPEED, rng_seed=None):
        self.rng = np.random.RandomState(rng_seed)
        self.obstacle_count = int(obstacle_count)
        self.swarm_size = int(swarm_size)
        self.speed = speed
        self.obstacle_mask = make_obstacles(self.obstacle_count, rng_seed=self.rng.randint(0,1<<30))
        # coverage arrays for left (single) and right (swarm)
        self.coverage_single = np.zeros((GRID_SIZE, GRID_SIZE), dtype=float)
        self.coverage_swarm = np.zeros((GRID_SIZE, GRID_SIZE), dtype=float)
        # initialize drones
        self.single_drone = self._create_drone_for(self.obstacle_mask)
        self.swarm = [self._create_drone_for(self.obstacle_mask) for _ in range(self.swarm_size)]
        # keep time counter
        self.time = 0.0
    
    def _create_drone_for(self, obstacle_mask):
        x, y = sample_free_position(obstacle_mask, rng=self.rng)
        return Drone(x, y, obstacle_mask, rng=np.random.RandomState(self.rng.randint(0,1<<30)))
    
    def reset(self, obstacle_count=None, swarm_size=None, speed=None):
        if obstacle_count is not None:
            self.obstacle_count = int(obstacle_count)
        if swarm_size is not None:
            self.swarm_size = int(swarm_size)
        if speed is not None:
            self.speed = speed
        self.obstacle_mask = make_obstacles(self.obstacle_count, rng_seed=self.rng.randint(0,1<<30))
        self.coverage_single.fill(0.0)
        self.coverage_swarm.fill(0.0)
        self.single_drone = self._create_drone_for(self.obstacle_mask)
        self.swarm = [self._create_drone_for(self.obstacle_mask) for _ in range(self.swarm_size)]
        self.time = 0.0
    
    def step(self, dt):
        # advance simulation by dt
        # single drone
        self.single_drone.step(self.speed, dt)
        coverage_update_from_drone(self.coverage_single, self.obstacle_mask, self.single_drone.x, self.single_drone.y)
        # swarm
        for d in self.swarm:
            d.step(self.speed, dt)
            coverage_update_from_drone(self.coverage_swarm, self.obstacle_mask, d.x, d.y)
        # decay coverage
        self.coverage_single *= DECAY_FACTOR
        self.coverage_swarm *= DECAY_FACTOR
        self.time += dt
    
    def coverage_stats(self):
        free_cells = np.sum(~self.obstacle_mask)
        covered_single = np.sum(self.coverage_single > 0.5)
        covered_swarm = np.sum(self.coverage_swarm > 0.5)
        return {
            "free_cells": int(free_cells),
            "covered_single": int(covered_single),
            "covered_swarm": int(covered_swarm),
            "pct_single": 100.0 * covered_single / free_cells if free_cells else 0.0,
            "pct_swarm": 100.0 * covered_swarm / free_cells if free_cells else 0.0,
        }

# -------------------- Visualization --------------------
sim = Simulation(DEFAULT_OBSTACLES, DEFAULT_SWARM, DEFAULT_SPEED, rng_seed=12345)

fig, axes = plt.subplots(1, 2, figsize=(12, 6))
ax_single, ax_swarm = axes

im_single = ax_single.imshow(sim.coverage_single, origin='lower', interpolation='nearest', vmin=0, vmax=1)
ax_single.set_title("Single Drone Coverage")
ax_single.set_xlim(-0.5, GRID_SIZE - 0.5)
ax_single.set_ylim(-0.5, GRID_SIZE - 0.5)

im_swarm = ax_swarm.imshow(sim.coverage_swarm, origin='lower', interpolation='nearest', vmin=0, vmax=1)
ax_swarm.set_title(f"Swarm Coverage (N={sim.swarm_size})")
ax_swarm.set_xlim(-0.5, GRID_SIZE - 0.5)
ax_swarm.set_ylim(-0.5, GRID_SIZE - 0.5)

# overlay obstacles as semi-opaque layer by making a colored mask (we avoid setting colors per instruction)
obstacle_overlay = np.zeros((GRID_SIZE, GRID_SIZE))
obstacle_overlay[sim.obstacle_mask] = 1.0
# show obstacles under the coverage (so black rectangles don't obscure drone markers)
ax_single.imshow(obstacle_overlay, origin='lower', interpolation='nearest', alpha=0.35, vmin=0, vmax=1)
ax_swarm.imshow(obstacle_overlay, origin='lower', interpolation='nearest', alpha=0.35, vmin=0, vmax=1)

# drone scatters (initial empty)
sc_single = ax_single.scatter([], [], s=40)
sc_swarm = ax_swarm.scatter([], [], s=20)

# Text stats
stat_ax = fig.add_axes([0.02, 0.02, 0.96, 0.06])
stat_ax.axis('off')
stat_text = stat_ax.text(0.01, 0.5, "", va='center')

# Slider axes
axcolor = 'lightgoldenrodyellow'
ax_obstacles = fig.add_axes([0.15, 0.92, 0.3, 0.03])
ax_swarm = fig.add_axes([0.6, 0.92, 0.3, 0.03])
ax_speed = fig.add_axes([0.15, 0.88, 0.3, 0.03])

slider_obstacles = Slider(ax_obstacles, 'Obstacles', 0, 80, valinit=DEFAULT_OBSTACLES, valstep=1)
slider_swarm = Slider(ax_swarm, 'Swarm Size', 1, 40, valinit=DEFAULT_SWARM, valstep=1)
slider_speed = Slider(ax_speed, 'Drone speed (u/s)', 0.1, 5.0, valinit=DEFAULT_SPEED)

# Reset button
ax_reset = fig.add_axes([0.82, 0.86, 0.12, 0.05])
btn_reset = Button(ax_reset, 'Reset', hovercolor='0.975')

# Callbacks
def reset_callback(event):
    obs = int(slider_obstacles.val)
    sw = int(slider_swarm.val)
    sp = float(slider_speed.val)
    sim.reset(obstacle_count=obs, swarm_size=sw, speed=sp)
    # refresh overlays for obstacles
    global obstacle_overlay_im1, obstacle_overlay_im2
    # remove previous overlays and re-add
    for artist in ax_single.get_images()[1:], ax_swarm.get_images()[1:]:
        pass
    # redraw obstacle overlay by clearing and re-imshowing (simpler approach)
    ax_single.images.clear()
    ax_swarm.images.clear()
    global im_single, im_swarm
    im_single = ax_single.imshow(sim.coverage_single, origin='lower', interpolation='nearest', vmin=0, vmax=1)
    ax_single.imshow(sim.obstacle_mask.astype(float), origin='lower', interpolation='nearest', alpha=0.35, vmin=0, vmax=1)
    im_swarm = ax_swarm.imshow(sim.coverage_swarm, origin='lower', interpolation='nearest', vmin=0, vmax=1)
    ax_swarm.imshow(sim.obstacle_mask.astype(float), origin='lower', interpolation='nearest', alpha=0.35, vmin=0, vmax=1)

btn_reset.on_clicked(reset_callback)

def slider_update(val):
    # when sliders change, we don't immediately regenerate obstacles except on Reset to avoid constant regen
    sim.speed = float(slider_speed.val)
    # but swarm size should be applied by resizing swarm list (keep positions for existing drones)
    new_sw = int(slider_swarm.val)
    if new_sw != sim.swarm_size:
        # add or remove drones
        if new_sw > sim.swarm_size:
            for _ in range(new_sw - sim.swarm_size):
                sim.swarm.append(sim._create_drone_for(sim.obstacle_mask))
        else:
            sim.swarm = sim.swarm[:new_sw]
        sim.swarm_size = new_sw
    # obstacle slider effect will be applied when Reset button is clicked (intentional to avoid constant regen)
    
slider_obstacles.on_changed(slider_update)
slider_swarm.on_changed(slider_update)
slider_speed.on_changed(slider_update)

# Animation step
def animate(frame):
    # step simulation for several substeps for smoother motion
    steps_per_frame = max(1, int(0.03 / DT))  # aim ~30ms per frame chunking
    for _ in range(3):
        sim.step(DT)
    # update images
    im_single.set_data(sim.coverage_single)
    im_swarm.set_data(sim.coverage_swarm)
    # update scatter positions
    sc_single.set_offsets([[sim.single_drone.x, sim.single_drone.y]])
    swarm_positions = np.array([[d.x, d.y] for d in sim.swarm])
    if len(swarm_positions) > 0:
        sc_swarm.set_offsets(swarm_positions)
    else:
        sc_swarm.set_offsets([])
    ax_swarm.set_title(f"Swarm Coverage (N={sim.swarm_size})")
    # update stats text
    s = sim.coverage_stats()
    stat_text.set_text(f"Time: {sim.time:.1f}s    Free cells: {s['free_cells']}    "
                       f"Single covered: {s['covered_single']} ({s['pct_single']:.1f}%)    "
                       f"Swarm covered: {s['covered_swarm']} ({s['pct_swarm']:.1f}%)")
    return im_single, im_swarm, sc_single, sc_swarm, stat_text

anim = FuncAnimation(fig, animate, interval=80, blit=False)

plt.tight_layout(rect=[0, 0.06, 1, 0.94])
plt.show()

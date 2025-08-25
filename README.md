# Swarm-Based Relay Architecture for Low-Cost SAR Drones

> **central idea (tl;dr):** use a swarm of cheap search drones + a few relay/transmit drones to cover SAR areas faster and cheaper than single large SAR drones.

---

## Project overview

we're building a prototype and simulator for a two-layer swarm SAR system: lightweight search drones (secondary mesh) scout dangerous areas and send detections to a small set of transmit/relay drones (primary mesh), which forward data to the base station.

this reduces the need for long-range RF and heavy, expensive payloads on every drone — search drones can be cheaper, take more risks, and search in parallel.

---

## Features

* two-layer mesh network (search swarm + transmit swarm)
* real-time relaying of video/telemetry from search drones to base via transmit drones
* simulation (grid-based) comparing area coverage of single vs swarm
* ESP32-based demo showing primary, secondary, and base node interactions

---

## Architecture 

* **search swarm (secondary):** many low-cost/lightweight drones with short-range RF, basic cameras/thermal sensors, limited onboard processing.
* **transmit swarm (primary):** fewer, higher-capability drones with stronger RF, better processors and endurance; act as relays to base.

**workflow:**

1. search drone detects candidate → broadcasts local alert on secondary mesh.
2. nearest transmit drone relays/streams that search drone's feed to base.
3. swarm adjusts links dynamically to maintain end-to-end connectivity and redundancy.

**verification & redundancy:** transmit drone provides higher-bandwidth relay and context; operators can task multiple search drones for multi-angle coverage.

---

## Typical SAR situations

* **aerial scanning:** flood rooftops, open fields
* **complex indoor/underground:** mines, collapsed buildings
* **dangerous environments:** fires, hazardous-material incidents

common constraints to keep in mind: base-station distance, time-to-search, safety/failsafes, battery life.

---

## Hardware & cost notes (reference + prototype targets)

> **reference commercial platforms**

* **DJI Matrice 350 RTK** (example of high-end SAR drone)

  * price: roughly **\$10,000–\$20,000+** depending on payload
  * flight time: \~55 min (hot-swap batteries)
  * range: up to \~15 km (depends on RF/payload)
  * sensors: zoom camera, thermal, laser rangefinder, obstacle avoidance

* **DJI Mavic 3 Thermal** (reference compact drone)

  * price: roughly **\$1,500**
  * flight time: \~45 min
  * range: up to \~15 km (depending on configuration)
  * sensors: 20 MP visual, thermal module

> **our prototype targets**

* **search drone (target spec)**

  * price: **\~\$1,500** (goal)
  * flight time: **1–1.5 hours** (larger battery)
  * range: **\~4–5 km** (short-range RF in swarm)
  * sensors: thermal (640×512), 20 MP visual, GPS
  * weight: \~1.5 kg
  * ruggedness: extra prop guards, basic obstacle sensing

* **transmit drone (target spec)**

  * price: **\$10,000–\$15,000** (for a high-capacity relay)
  * flight time: **1–2 hours**
  * range to base: **up to \~15 km** (high-bandwidth link)
  * sensors: wide-angle camera, laser rangefinder, robust processor for streaming
  * form: fixed-wing or hybrid for endurance

**note:** 
* these are target/spec suggestions for prototyping and cost comparisons — tune to actual parts when building. 

* Streaming & processing assumptions
    * this architecture relies on **each search drone having just enough processing power to encode and stream one video feed** into the mesh. they do not need heavy onboard compute for complex fusion — minimal encoding + basic detection is enough.
    * the mesh routing algorithm will select an **optimal path** (minimizing number of hops and relays) so that the minimum number of transmit-capable drones are used to get video from a search drone to the base. this optimization is part of future work (routing + link-budget aware path selection).

---

## Why swarm helps 

* **faster coverage:** parallel search vs serial scanning.
* **cost & risk:** cheaper search drones are cheaper to replace; transmit drones avoid going into dangerous zones.
* **redundancy:** many cheap nodes → graceful degradation.
* **initial cost:** can be higher (more units), but operating cost in risky deployments is lower.

### Visual comparison


![Swarm setup](https://github.com/anbu-05/InnovAct-Hackathon/blob/main/media/swarm.jpg) *Caption: multiple secondary search drones + a primary relay — covers a much larger effective area for the same total budget. for an equivalent total budget (e.g., one high-end drone vs a transmit drone + several cheaper search drones), the swarm can cover a wider area because search nodes are distributed — each contributes a local sensing radius that, together, forms a much larger union of coverage.*



![Traditional single-drone](https://github.com/anbu-05/InnovAct-Hackathon/blob/main/media/single.jpg)
*Caption: a single high-capability drone — similar total cost but smaller effective coverage and poor obstacle resilience. when an obstacle blocks a search path, individual cheap search drones can re-route locally or other nearby search drones can cover the occluded region immediately. a single drone must change its whole scan course (and therefore loses coverage elsewhere) to go around obstacles, which increases time-to-search for the entire area.*
*

![simple simulation of search pattern](https://github.com/anbu-05/InnovAct-Hackathon/blob/main/media/simulation.mp4) *Caption: The simulation highlights the effectiveness of swarm-based search compared to a single drone. While the single drone (left) covers a narrow path with limited visibility, the swarm (right) achieves broader, parallel coverage, significantly reducing blind spots and improving efficiency in obstacle-rich environments.*

---

## Demonstration / what’s in this repo

* `primary/` — code for the transmit/relay node (ESP32)
* `secondary/` — code for the search node (ESP32 / camera)
* `base/` — laptop-side scripts demonstrating base-station behavior and receiving relayed streams
* `simulation/` — grid-based search simulator (see `simulation/simulation4.py`) comparing single vs swarm coverage

---

## Quick start — simulation

1. run the comparison sim:

```bash
python simulation/simulation4.py
```

* `simulation4.py` runs a 256×256 grid with random obstacles. drones are red dots, covered area is shaded green and decays over time (decay rate = 0.01) to simulate the need for rescanning.
* algorithm: currently a simple linear search (fast to run, easy to reproduce). consider swapping to a randomized / coverage path algorithm later.

**Dependencies:** install only the Python packages the sim needs:

```bash
pip install numpy matplotlib
```

## Quick start — ESP32 demo

**what's included:** example sketches for `primary`, `secondary`, and a `base` client.

**primary node — required edits (important):**

Open the primary sketch and replace these lines with your laptop hotspot credentials and IP:

```cpp
const char* LAPTOP_SSID = "Laptop";
const char* LAPTOP_PASS = "password";
const char* LAPTOP_IP = "192.168.137.1"; // <-- replace if your laptop IP differs
```

* Find your laptop IP on Windows using `ipconfig` and use the IPv4 address of the adapter serving the hotspot.

**base (laptop) — launch command:**

Run the base server with this command from the repo root:

```bash
python3 ./BaseServer.py --host 0.0.0.0 --port 9000
```

**Wi‑Fi hotspot requirement:**

* Make sure the laptop hotspot is set to **2.4 GHz** (ESP32 devices usually cannot connect to 5 GHz hotspots).

**general steps:**

1. flash the appropriate sketches to the right ESP32 nodes (esp32-cam for camera node if used).
2. update the constants shown above in the primary sketch, then flash and power on nodes.
3. start `BaseServer.py` on your laptop and confirm the IP/port match what you placed in `LAPTOP_IP`.
4. use the serial monitor or the base script to view relayed frames.

> note: the repo contains demo code intended for educational prototyping. adapt RF library/config to your hardware.

## Limitations

* prototype uses short-range RF (ESP32) for demonstration — not representative of production RF links.
* search algorithm is simple; it demonstrates coverage but not optimized path planning.
* sensor payloads in the repo are simulated or low-cost commercial modules — you'll need to pick production-grade sensors for real SAR.

---

## Future work / improvements

* implement improved coverage algorithms (Lawnmower / spiral / frontier / frontier-based exploration)
* integrate opportunistic multi-angle stitching and target confirmation pipelines
* add power-aware scheduling and dynamic battery swap/return-to-base logic
* field tests with real RF modules (LoRa, LTE/5G, mesh radios) and tuned link budgets

---

## Folder structure (suggested)

```
/ (repo root)
├─ primary/            # transmit relay node code (ESP32)
├─ secondary/          # search node code (ESP32)
│  ├─ secondary-NoCam/ # search node code without camera (sensor-only / nav)
│  └─ secondary-Cam/   # search node code with esp32-cam / camera integration
├─ base/               # base-station scripts
├─ simulation/         # sims (simulation4.py)
├─ docs/               # optional: design docs, CAD, BOM
└─ README.md
```

---

## Contribution & contact

* PRs welcome. open issues for bugs / feature requests.
* if you want to prototype hardware, open an issue describing parts and tests and we can add a `hardware/` folder and a BOM.

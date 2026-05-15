

https://github.com/user-attachments/assets/73b964aa-6a4c-4b20-9bc0-b3916e1d9858

# ACO Appliance Scheduler — NEPRA 2025

**Course:** Analysis of Algorithms (Spring 2026)
**Topic:** Ant Colony Optimization for Time-of-Use Appliance Scheduling
**Tariff Model:** NEPRA 2025 Pakistan slab tariffs + Time-of-Use multipliers

---

## What This Project Does

Given a household with 15 appliances (7 fixed-schedule + 8 shiftable), this
project uses **Ant Colony Optimization (ACO)** to decide *when* to run each
shiftable appliance during a 24-hour day so that the **monthly electricity
bill is minimized**, while respecting:

- NEPRA 2025 slab tariffs (5 cumulative tiers from PKR 4.78 to PKR 48.46/unit)
- Time-of-Use multipliers (peak 1.5x, off-peak 0.7x, standard 1.0x)
- Hourly load capacity constraint (3000W breaker limit)

This is a real, NP-hard combinatorial optimization problem — a flavor of
parallel-machine scheduling combined with bin packing under non-linear costs.

---

## Repository Structure

```
.
├── aco_scheduler.py        # Core ACO + tariff model + baselines
├── empirical_analysis.py   # Benchmarks: time vs n/m/t, convergence, quality
├── requirements.txt
├── results/                # Generated plots (after running benchmarks)
└── README.md
```

---

## Running

```bash
pip install -r requirements.txt

# Quick demo: ACO vs greedy vs random
python aco_scheduler.py

# Full empirical analysis (generates all 6 plots in ./results/)
python empirical_analysis.py
```

---

## Key Results

| Method | Monthly Bill (PKR) | Notes |
|---|---|---|
| Random schedule (avg of 10) | 43,894 | No optimization |
| Greedy (cheapest-slot-first) | 37,914 | Naive heuristic |
| **ACO (this work)** | **37,115** | **2.11% better than greedy, 15.4% better than random** |

ACO converges within ~20 iterations and is highly stable (std deviation across
runs: ~5 PKR).

---

## Algorithm: Ant Colony Optimization

ACO is a metaheuristic inspired by how real ants find shortest paths between
their nest and food. Artificial ants stochastically construct candidate
solutions guided by a pheromone matrix τ[i][h] (desirability of placing
appliance *i* in time slot *h*), reinforced by past success, and a heuristic
η[i][h] (1/tariff_multiplier — prefer cheaper slots).

**Pseudocode:**

```
initialize tau[i][h] = 1 for all appliances i and hours h
for iteration = 1 to T:
    for ant = 1 to M:
        for each shiftable appliance i (random order):
            for each required hour:
                pick slot h with probability proportional to:
                    tau[i][h]^alpha  *  eta[i][h]^beta  *  capacity_factor[h]
                add slot h to schedule of appliance i
    evaluate all M solutions (compute monthly bill)
    evaporate pheromones:  tau *= (1 - rho)
    deposit pheromones:    top-k ants reinforce their choices
    elitist deposit:       best-so-far ant reinforces extra
    clamp tau to [0.1, 50] to prevent stagnation
return best schedule found
```

**Complexity:** `O(n · m · t · H)` per run, where:
- *n* = appliances
- *m* = ants per iteration
- *t* = iterations
- *H* = 24 (time slots)

---

## Why ACO Beats Greedy Here

Greedy assigns each appliance to the cheapest available slot in turn. This
fails because:

1. **Capacity blindness** — once a cheap slot is full, later appliances are
   pushed to expensive slots. ACO learns to *coordinate* placements so loads
   are balanced.
2. **Slab non-linearity** — the NEPRA per-unit price jumps 3x at the 200-unit
   boundary. ACO's stochastic exploration finds joint allocations that keep
   the heaviest hours just under slab boundaries.

---

## Author

Muhammad Wajahat Rehman

# Presentation Outline — ACO Appliance Scheduler
## ~8-minute talk, 10 slides

---

### Slide 1 — Title
- **Ant Colony Optimization for Time-of-Use Appliance Scheduling**
- Subtitle: NEPRA 2025 Tariffs · A Real Pakistani Use Case
- Your name, course, instructor, date
- Optional: small thumbnail of the load-profile chart in a corner

**Speaker note:** "Most algorithm projects pick TSP. I wanted to solve a problem someone in this room actually has — your monthly KESC/IESCO bill."

---

### Slide 2 — The Real-World Problem (30 sec)
- One sentence: *"How should I schedule my high-power appliances to minimize my electricity bill?"*
- Two pain points to highlight:
  - NEPRA slab cliff: PKR 11.51 → 34.03 at 200 units (3× jump)
  - Time-of-Use rates: peak 1.5×, off-peak 0.7×
- Stat: a typical household pays 25–40% more than the optimum just from bad timing

**Speaker note:** "If you've ever stared at your meter on the 28th of the month, this slide is for you."

---

### Slide 3 — Why It's a Real Algorithm Problem (45 sec)
- 8 shiftable appliances × 24 slots × variable run-hours = **search space larger than 10⁴⁰**
- Cost function is **non-linear** (slab cliffs) → classical methods break
- Greedy fails because it's blind to capacity constraints and slab boundaries
- Brute force is infeasible (24⁸ ≈ 110 billion just for slot selection)
- Conclusion: this is genuinely NP-hard → metaheuristic territory

---

### Slide 4 — Ant Colony Optimization (1 min)
Two columns:
- **Left:** small diagram or doodle of real ants laying pheromone trails between nest and food
- **Right:** the artificial-ant analog
  - τ[i][h] = pheromone (learned)
  - η[i][h] = heuristic (1 / TOU multiplier)
  - Ants sample slots probabilistically
  - Best ants reinforce; pheromones evaporate

**Speaker note:** "Real ants don't have a CPU. They follow stronger smells. Artificial ants do exactly the same — they pick choices proportional to remembered success."

---

### Slide 5 — Pseudocode (45 sec)
A clean, abbreviated version (don't put the full 25-line block):

```
for iteration = 1..T:
    for ant = 1..M:
        build a schedule by sampling slots
        with probability ∝ τ^α · η^β · capacity_factor
    evaluate all schedules (compute bill)
    evaporate τ; top ants deposit pheromone
return best schedule
```

**Speaker note:** "Five lines, but the magic is in the third one. That's where exploration meets exploitation."

---

### Slide 6 — Implementation (30 sec)
- Python 3, ~300 lines, from scratch
- NumPy for the τ matrix vectorization
- Modular: tariff model, capacity model, ACO, baselines all separate
- Reproducible: every random source is seeded
- **Code is on GitHub** (link)

---

### Slide 7 — The Money Shot (1 min) ⭐
- Show **figure 6 (24-hour load profile)** — this is your wow moment
- Annotate live:
  - "Greedy crams everything into the cheapest hours and crashes into the capacity cap"
  - "ACO spreads the load — same off-peak savings, but no breaker trips"
- Bottom of slide: bar chart (figure 5)
  - Random: PKR 43,894 · Greedy: PKR 37,914 · **ACO: PKR 37,115**
  - Annual savings vs greedy: ~PKR 9,600/year
  - Annual savings vs random: ~PKR 81,000/year

**Speaker note:** "Two percent over greedy doesn't sound like much. But the killer chart is this one — look at how ACO handles the capacity ceiling."

---

### Slide 8 — Empirical Validation (45 sec)
Two charts side by side:
- **Convergence curve** (figure 4) — "settles within 25 iterations"
- **Time-vs-size** (figure 1) — "linear scaling, matches theory"

Bullet points:
- Standard deviation across runs: PKR 5.29 (extremely stable)
- Memory footprint: ~100 KB peak

---

### Slide 9 — Complexity Analysis (45 sec)
On-screen formula (large):
- **Time:** Θ(T · M · S · R_max · H)
- **Space:** O(N · H + M · S · R_max)
- For my parameters (T=150, M=30, S=8, R_max=24, H=24): under 2 seconds

Comparison table:
| Algorithm | Time | Quality |
|-----------|------|---------|
| Brute force | Θ(H^(S·R)) — infeasible | Optimal |
| Greedy | Θ(S·H log H) | 2% gap |
| **ACO** | Θ(T·M·S·R·H) | Near-optimal |

---

### Slide 10 — Reflection & Q&A
- **What I learned:**
  - Algorithm-problem fit matters more than algorithm choice
  - My first formulation was too easy; greedy was provably optimal
  - The redesigned problem (TOU + capacity) is where ACO earns its keep
- **Future work:** integrate live tariff API; mobile app; battery storage
- **Repo:** github.com/yourusername/aco-appliance-scheduler
- "Questions?"

---

## Q&A Anticipated

**Q: Why ACO over Genetic Algorithm?**
A: Both would work — ACO's pheromone matrix maps directly onto the (appliance, slot) decision structure, while GA's chromosome encoding would be more contrived. ACO is more natural for this problem geometry.

**Q: Is 2% really worth a metaheuristic?**
A: At Pakistani household scale, that's roughly Rs. 9,600/year. At industrial scale (factories, EV fleets), 2% is 7-figure savings. And the algorithm runs in under 2 seconds — there's no downside.

**Q: How did you tune the parameters?**
A: Empirically. I ran the experiment 2 script with different m, t, α, β values and watched the convergence curves. Final parameters: α=1, β=3, ρ=0.10, m=20, t=50.

**Q: What if the user adds a new appliance?**
A: The dataset is declarative — adding an appliance is one line. The pheromone matrix grows by one row, and the algorithm reruns in seconds.

**Q: Does it generalize beyond NEPRA?**
A: Yes — the slab function and TOU function are pluggable. K-Electric, IESCO, LESCO all have similar structure. International TOU tariffs (US, UK, EU) work the same way.

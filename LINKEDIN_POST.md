# LinkedIn Post Draft

## Option A — The Story Version (recommended)

---

I started with an electricity bill calculator. I ended up with an algorithm research project.

For my Analysis of Algorithms course (Spring 2026), I built an Ant Colony Optimization scheduler that decides when each appliance in your home should run to minimize your monthly electricity bill — while respecting NEPRA 2025 slab tariffs, time-of-use multipliers, and your circuit breaker's load capacity.

The problem turned out to be genuinely NP-hard. The slab cliff at 200 units (rates jumping from PKR 11.51 to 34.03) makes the cost function non-linear. Add peak vs off-peak rates and a capacity constraint, and greedy approaches start to fail.

Results, on a typical 15-appliance household:
↳ Random scheduling: PKR 43,894/month
↳ Naive greedy: PKR 37,914/month
↳ ACO: PKR 37,115/month
↳ ~PKR 81,000 saved annually vs random, and the algorithm runs in under 2 seconds

The most valuable lesson came from a failure: my first problem formulation was too simple, and greedy was provably optimal — leaving nothing for ACO to improve. Redesigning the problem to expose its real combinatorial structure was where the project clicked.

Built from scratch in Python (no optimization libraries). NEPRA tariffs, time-of-use multipliers, capacity constraints — everything modeled honestly. Empirical analysis includes 6 graphs covering execution time scaling, convergence behavior, and quality comparison against baselines.

Code, report, and graphs: [GitHub link]

#AlgorithmAnalysis #AntColonyOptimization #SwarmIntelligence #Python #NEPRA #SmartGrid

---

## Option B — The Short Version

---

Spent the week implementing Ant Colony Optimization for appliance scheduling under NEPRA 2025 tariffs. The slab cliff at 200 units makes this genuinely NP-hard.

ACO finds schedules ~15% cheaper than random, ~2% cheaper than greedy, in under 2 seconds. The 24-hour load profile chart speaks for itself.

Built from scratch in Python. Code + report on GitHub: [link]

#AnalysisOfAlgorithms #ACO #Python

---

## Tips for posting

- Pick **Option A** if you want engagement from professors/recruiters — the story arc (failure → redesign → success) reads well.
- Pick **Option B** if your network is mostly devs who'll click through to GitHub.
- Attach the **load profile chart** (figure 6) as the post image — it's the most visually striking.
- Tag your instructor and university for reach.
- Best time to post: weekday morning, 9–11am.

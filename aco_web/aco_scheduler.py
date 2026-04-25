"""
Ant Colony Optimization for Time-of-Use Appliance Scheduling
=============================================================

PROBLEM:
    Each appliance has REQUIRED daily run-hours (e.g., washing machine = 2 hr).
    The day is split into 24 hourly slots, each with a TARIFF MULTIPLIER:
        Peak hours (6pm-10pm)     -> 1.5x  (expensive)
        Off-peak (10pm-6am)       -> 0.7x  (cheap)
        Standard (otherwise)       -> 1.0x

    Some appliances are "shiftable" (washer, iron, geyser, EV charger).
    Others are "fixed" (lights, fan, AC, fridge).

    GOAL: Schedule shiftable appliances into time slots to MINIMIZE total bill,
          subject to:
            - Each shiftable appliance's required hours are met
            - Hourly load capacity (total kW per slot <= breaker limit)

    This is NP-hard (scheduling + bin-packing flavor) and greedy fails because:
      1. Locally cheapest slots can violate capacity, forcing expensive slots later
      2. Slab tariff (cumulative monthly kWh) creates non-linear costs
         that depend on the joint schedule of all appliances

Author: Muhammad
Course: Analysis of Algorithms - Spring 2026
"""

import random
import numpy as np
from typing import List, Tuple, Dict
from dataclasses import dataclass


# ============================================================================
# NEPRA 2025 Tariff (matches your HTML calculator)
# ============================================================================

FIXED_CHARGE = 75.0  # PKR/month

def tou_multiplier(hour: int) -> float:
    """Time-of-Use tariff multiplier for a given hour-of-day (0-23)."""
    if 22 <= hour or hour < 6:        # Off-peak (night)
        return 0.7
    if 18 <= hour < 22:               # Peak (evening)
        return 1.5
    return 1.0                        # Standard (day)


def slab_rate(cumulative_kwh: float) -> float:
    """NEPRA per-unit rate for current cumulative monthly kWh."""
    if cumulative_kwh <= 50:  return 4.78
    if cumulative_kwh <= 100: return 8.52
    if cumulative_kwh <= 200: return 11.51
    if cumulative_kwh <= 300: return 34.03
    return 48.46


# ============================================================================
# Appliance Dataset
# ============================================================================

@dataclass
class Appliance:
    name: str
    watts: int
    required_hours: int
    shiftable: bool
    fixed_slots: Tuple[int, ...] = ()


APPLIANCES = [
    Appliance("Refrigerator",    150, 24, False, tuple(range(24))),
    Appliance("Ceiling Fan",      75, 12, False, tuple(range(8, 20))),
    Appliance("LED Light",        15,  6, False, (6, 7, 18, 19, 20, 21)),
    Appliance("Air Conditioner",1500,  6, False, (13, 14, 15, 16, 17, 18)),
    Appliance("Television",      120,  5, False, (19, 20, 21, 22, 23)),
    Appliance("Laptop",           65,  8, False, (9, 10, 11, 12, 13, 14, 15, 16)),
    Appliance("Desktop PC",      300,  4, False, (10, 11, 14, 15)),

    # Shiftable - ACO decides when these run
    Appliance("Washing Machine", 500, 2, True),
    Appliance("Iron",           1200, 1, True),
    Appliance("Geyser",         2000, 2, True),
    Appliance("Electric Kettle",1500, 1, True),
    Appliance("Microwave",      1000, 1, True),
    Appliance("Water Pump",      750, 2, True),
    Appliance("Dishwasher",     1200, 1, True),
    Appliance("EV Charger",     2200, 4, True),
]

LOAD_CAPACITY_WATTS = 3000  # household breaker limit (tightened to make problem harder)


# ============================================================================
# Bill Calculation
# ============================================================================

def hourly_kwh_profile(schedule: Dict[int, List[int]]) -> List[float]:
    profile = [0.0] * 24
    for app_idx, slots in schedule.items():
        watts = APPLIANCES[app_idx].watts
        for h in slots:
            profile[h] += watts / 1000.0
    return profile


def compute_monthly_bill(schedule: Dict[int, List[int]]) -> Tuple[float, float, List[float]]:
    """
    Bill = FIXED + sum_h (kWh_h * slab_rate(cumulative) * tou_multiplier(h))
    Computed across 30 days, with cumulative kWh tracked for slab pricing.
    """
    profile = hourly_kwh_profile(schedule)
    bill = FIXED_CHARGE
    cumulative_kwh = 0.0
    total_kwh = 0.0

    for _day in range(30):
        for hour in range(24):
            kwh = profile[hour]
            if kwh <= 0:
                continue
            rate = slab_rate(cumulative_kwh) * tou_multiplier(hour)
            bill += kwh * rate
            cumulative_kwh += kwh
            total_kwh += kwh

    return bill, total_kwh, profile


def capacity_violations(schedule: Dict[int, List[int]]) -> int:
    profile_watts = [0.0] * 24
    for app_idx, slots in schedule.items():
        watts = APPLIANCES[app_idx].watts
        for h in slots:
            profile_watts[h] += watts
    return sum(1 for p in profile_watts if p > LOAD_CAPACITY_WATTS)


def evaluate(schedule: Dict[int, List[int]]) -> Tuple[float, float]:
    """Returns (fitness, bill). Higher fitness is better."""
    bill, _, _ = compute_monthly_bill(schedule)
    violations = capacity_violations(schedule)
    fitness = -bill - 5000.0 * violations
    return fitness, bill


def build_full_schedule(shiftable_choices: Dict[int, List[int]]) -> Dict[int, List[int]]:
    schedule = {}
    for i, a in enumerate(APPLIANCES):
        if a.shiftable:
            schedule[i] = shiftable_choices.get(i, [])
        else:
            schedule[i] = list(a.fixed_slots)
    return schedule


# ============================================================================
# ACO Implementation
# ============================================================================

class ACOScheduler:
    """
    ACO for time-of-use scheduling.
    Pheromone tau[i][h] = desirability of placing appliance i in slot h.
    Heuristic eta[i][h] = 1/tou_multiplier(h)  -> prefers cheaper slots.
    """

    def __init__(
        self,
        n_ants: int = 30,
        n_iterations: int = 150,
        alpha: float = 1.0,
        beta: float = 3.0,
        rho: float = 0.10,
        q: float = 100.0,
        seed: int = None,
    ):
        self.n = len(APPLIANCES)
        self.n_ants = n_ants
        self.n_iterations = n_iterations
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.q = q
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.shiftable_idx = [i for i, a in enumerate(APPLIANCES) if a.shiftable]
        self.H = 24
        self.tau = np.ones((self.n, self.H))
        self.eta = np.array([
            [1.0 / tou_multiplier(h) for h in range(self.H)]
            for _ in range(self.n)
        ])

    def construct_solution(self) -> Dict[int, List[int]]:
        load = [0.0] * self.H
        for i, a in enumerate(APPLIANCES):
            if not a.shiftable:
                for h in a.fixed_slots:
                    load[h] += a.watts

        choices = {}
        order = self.shiftable_idx[:]
        random.shuffle(order)

        for i in order:
            a = APPLIANCES[i]
            need = a.required_hours
            available = list(range(self.H))
            chosen = []
            for _ in range(need):
                if not available:
                    break
                tau_h = np.array([self.tau[i][h] for h in available]) ** self.alpha
                eta_h = np.array([self.eta[i][h] for h in available]) ** self.beta
                cap_factor = np.array([
                    0.05 if load[h] + a.watts > LOAD_CAPACITY_WATTS else 1.0
                    for h in available
                ])
                probs = tau_h * eta_h * cap_factor
                total = probs.sum()
                if total <= 0:
                    h = random.choice(available)
                else:
                    probs = probs / total
                    h = available[np.random.choice(len(available), p=probs)]
                chosen.append(h)
                load[h] += a.watts
                available.remove(h)
            choices[i] = sorted(chosen)
        return choices

    def update_pheromones(self, solutions, fitnesses, best_sol, best_fit):
        self.tau *= (1 - self.rho)
        ranked = sorted(zip(solutions, fitnesses), key=lambda x: -x[1])
        top_k = ranked[: max(1, self.n_ants // 3)]
        for sol, fit in top_k:
            deposit = self.q / max(abs(fit) / 1000.0, 1.0)
            for app_idx, slots in sol.items():
                for h in slots:
                    self.tau[app_idx][h] += deposit
        if best_sol is not None:
            elite_deposit = 2.0 * self.q / max(abs(best_fit) / 1000.0, 1.0)
            for app_idx, slots in best_sol.items():
                for h in slots:
                    self.tau[app_idx][h] += elite_deposit
        self.tau = np.clip(self.tau, 0.1, 50.0)

    def run(self, verbose: bool = False):
        best_sol = None
        best_fit = -float('inf')
        best_bill = 0.0
        history = []
        for it in range(self.n_iterations):
            shiftable_solutions = [self.construct_solution() for _ in range(self.n_ants)]
            full_schedules = [build_full_schedule(s) for s in shiftable_solutions]
            evals = [evaluate(s) for s in full_schedules]
            fitnesses = [e[0] for e in evals]
            bills = [e[1] for e in evals]
            it_best_idx = int(np.argmax(fitnesses))
            if fitnesses[it_best_idx] > best_fit:
                best_fit = fitnesses[it_best_idx]
                best_sol = shiftable_solutions[it_best_idx]
                best_bill = bills[it_best_idx]
            self.update_pheromones(shiftable_solutions, fitnesses, best_sol, best_fit)
            history.append((it, best_fit, float(np.mean(fitnesses)), best_bill))
            if verbose and (it % 10 == 0 or it == self.n_iterations - 1):
                print(f"  Iter {it:3d} | best_bill=PKR {best_bill:8,.2f} | "
                      f"mean_fit={np.mean(fitnesses):10,.0f}")
        return best_sol, best_fit, best_bill, history


# ============================================================================
# Baselines
# ============================================================================

def random_baseline(seed: int = 0) -> Tuple[Dict, float]:
    rng = random.Random(seed)
    choices = {}
    for i, a in enumerate(APPLIANCES):
        if a.shiftable:
            choices[i] = sorted(rng.sample(range(24), a.required_hours))
    full = build_full_schedule(choices)
    bill, _, _ = compute_monthly_bill(full)
    return choices, bill


def greedy_cheapest_first() -> Tuple[Dict, float]:
    """Naive greedy: pick cheapest available slots respecting capacity."""
    hours_by_cost = sorted(range(24), key=lambda h: tou_multiplier(h))
    load = [0.0] * 24
    for a in APPLIANCES:
        if not a.shiftable:
            for h in a.fixed_slots:
                load[h] += a.watts
    choices = {}
    for i, a in enumerate(APPLIANCES):
        if not a.shiftable:
            continue
        chosen = []
        for h in hours_by_cost:
            if len(chosen) >= a.required_hours:
                break
            if load[h] + a.watts <= LOAD_CAPACITY_WATTS:
                chosen.append(h)
                load[h] += a.watts
        if len(chosen) < a.required_hours:
            for h in hours_by_cost:
                if h in chosen:
                    continue
                chosen.append(h)
                if len(chosen) >= a.required_hours:
                    break
        choices[i] = sorted(chosen)
    full = build_full_schedule(choices)
    bill, _, _ = compute_monthly_bill(full)
    return choices, bill


# ============================================================================
# Demo
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("ACO Time-of-Use Appliance Scheduler -- NEPRA 2025")
    print("=" * 70)
    n_shift = sum(1 for a in APPLIANCES if a.shiftable)
    print(f"Total appliances: {len(APPLIANCES)} ({n_shift} shiftable)")
    print(f"Capacity limit: {LOAD_CAPACITY_WATTS} W per hour")
    print(f"TOU: peak (6pm-10pm) 1.5x | off-peak (10pm-6am) 0.7x")
    print()

    print("RANDOM baseline:")
    rand_bills = [random_baseline(s)[1] for s in range(10)]
    print(f"  Average: PKR {np.mean(rand_bills):,.2f}, Best: PKR {min(rand_bills):,.2f}")

    print("\nGREEDY (cheapest-slot-first):")
    g_choices, g_bill = greedy_cheapest_first()
    g_full = build_full_schedule(g_choices)
    print(f"  Bill: PKR {g_bill:,.2f}")
    print(f"  Capacity violations: {capacity_violations(g_full)}")

    print("\nACO:")
    aco = ACOScheduler(n_ants=30, n_iterations=150, seed=42)
    sol, fit, bill, hist = aco.run(verbose=True)
    full = build_full_schedule(sol)
    print(f"\n  Final bill: PKR {bill:,.2f}")
    print(f"  Capacity violations: {capacity_violations(full)}")

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Random (avg):  PKR {np.mean(rand_bills):>10,.2f}")
    print(f"Greedy:        PKR {g_bill:>10,.2f}")
    print(f"ACO:           PKR {bill:>10,.2f}")
    print()
    if g_bill > bill:
        print(f"ACO vs Greedy: PKR {g_bill - bill:,.2f} saved/month "
              f"({(g_bill - bill)/g_bill*100:.2f}%)")
    print(f"ACO vs Random: PKR {np.mean(rand_bills) - bill:,.2f} saved/month "
          f"({(np.mean(rand_bills) - bill)/np.mean(rand_bills)*100:.2f}%)")

    print("\nACO-optimized shiftable schedule:")
    print(f"{'Appliance':<22}{'Slots (hour-of-day)':<40}")
    print("-" * 62)
    for i in sorted(sol.keys()):
        hours_str = ", ".join(f"{h:02d}:00" for h in sol[i])
        print(f"{APPLIANCES[i].name:<22}{hours_str:<40}")

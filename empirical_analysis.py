"""
Empirical Analysis for ACO Appliance Scheduler
===============================================
Generates the data and graphs required for Section 4 (CLO 2.1) of the report:
  - Execution time vs problem size (number of appliances)
  - Execution time vs number of ants
  - Execution time vs number of iterations
  - Convergence curve (best bill over iterations)
  - Solution quality comparison: ACO vs greedy vs random
"""

import time
import tracemalloc
import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # headless

from aco_scheduler import (
    APPLIANCES, Appliance, ACOScheduler, build_full_schedule,
    compute_monthly_bill, evaluate, greedy_cheapest_first, random_baseline,
    LOAD_CAPACITY_WATTS, tou_multiplier
)
import aco_scheduler


# ============================================================================
# Helpers: build subset problems of varying size
# ============================================================================

def make_subset(n_shiftable: int):
    """
    Build an APPLIANCES subset with all 7 fixed appliances + first n_shiftable
    shiftable ones. Used to test ACO at different problem sizes.
    """
    fixed = [a for a in APPLIANCES if not a.shiftable]
    shiftable = [a for a in APPLIANCES if a.shiftable][:n_shiftable]
    return fixed + shiftable


def with_subset(subset, fn, *args, **kwargs):
    """Run `fn` with APPLIANCES temporarily replaced by `subset`."""
    original = aco_scheduler.APPLIANCES
    aco_scheduler.APPLIANCES = subset
    try:
        return fn(*args, **kwargs)
    finally:
        aco_scheduler.APPLIANCES = original


# ============================================================================
# Experiment 1: Time vs problem size (n shiftable appliances)
# ============================================================================

def experiment_size_scaling():
    print("\n[Experiment 1] Execution time vs problem size")
    sizes = [2, 4, 6, 8]  # shiftable appliances
    n_runs = 2            # average over runs
    n_ants = 20
    n_iters = 50

    results = []
    for n in sizes:
        subset = make_subset(n)
        times = []
        bills = []
        peak_mems = []
        for run in range(n_runs):
            def run_aco():
                aco = ACOScheduler(n_ants=n_ants, n_iterations=n_iters,
                                   seed=run * 7 + 1)
                return aco.run(verbose=False)

            tracemalloc.start()
            t0 = time.perf_counter()
            sol, fit, bill, hist = with_subset(subset, run_aco)
            elapsed = time.perf_counter() - t0
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            times.append(elapsed)
            bills.append(bill)
            peak_mems.append(peak / 1024)  # KB

        avg_t = np.mean(times)
        avg_bill = np.mean(bills)
        avg_mem = np.mean(peak_mems)
        results.append((n, avg_t, avg_bill, avg_mem))
        print(f"  n={n:2d} shiftable -> {avg_t:6.3f}s, "
              f"bill PKR {avg_bill:>10,.0f}, mem {avg_mem:>7.1f} KB")
    return results


# ============================================================================
# Experiment 2: Time vs number of ants
# ============================================================================

def experiment_ants_scaling():
    print("\n[Experiment 2] Execution time vs number of ants")
    ant_counts = [10, 20, 30, 50]
    n_iters = 50
    n_runs = 2

    results = []
    for m in ant_counts:
        times = []
        bills = []
        for run in range(n_runs):
            t0 = time.perf_counter()
            aco = ACOScheduler(n_ants=m, n_iterations=n_iters,
                               seed=run * 11 + 3)
            _, _, bill, _ = aco.run(verbose=False)
            times.append(time.perf_counter() - t0)
            bills.append(bill)
        avg_t = np.mean(times)
        avg_bill = np.mean(bills)
        results.append((m, avg_t, avg_bill))
        print(f"  m={m:2d} ants -> {avg_t:6.3f}s, bill PKR {avg_bill:>10,.0f}")
    return results


# ============================================================================
# Experiment 3: Time vs iterations (and convergence)
# ============================================================================

def experiment_iterations_scaling():
    print("\n[Experiment 3] Execution time vs iterations & convergence")
    iter_counts = [25, 50, 100, 150]
    n_ants = 20
    n_runs = 2

    results = []
    full_history = None
    for t_iters in iter_counts:
        times = []
        bills = []
        last_hist = None
        for run in range(n_runs):
            t0 = time.perf_counter()
            aco = ACOScheduler(n_ants=n_ants, n_iterations=t_iters,
                               seed=run * 13 + 5)
            _, _, bill, hist = aco.run(verbose=False)
            times.append(time.perf_counter() - t0)
            bills.append(bill)
            last_hist = hist
        avg_t = np.mean(times)
        avg_bill = np.mean(bills)
        results.append((t_iters, avg_t, avg_bill))
        if t_iters == max(iter_counts):
            full_history = last_hist
        print(f"  t={t_iters:3d} iters -> {avg_t:6.3f}s, bill PKR {avg_bill:>10,.0f}")
    return results, full_history


# ============================================================================
# Experiment 4: Solution quality comparison
# ============================================================================

def experiment_quality_comparison():
    print("\n[Experiment 4] Solution quality: ACO vs Greedy vs Random")
    n_runs = 5

    rand_bills = [random_baseline(s)[1] for s in range(n_runs)]
    _, g_bill = greedy_cheapest_first()

    aco_bills = []
    for run in range(n_runs):
        aco = ACOScheduler(n_ants=20, n_iterations=100, seed=run + 100)
        _, _, bill, _ = aco.run(verbose=False)
        aco_bills.append(bill)

    print(f"  Random:  mean=PKR {np.mean(rand_bills):>10,.2f}, "
          f"std=PKR {np.std(rand_bills):>8,.2f}")
    print(f"  Greedy:  PKR {g_bill:>10,.2f} (deterministic)")
    print(f"  ACO:     mean=PKR {np.mean(aco_bills):>10,.2f}, "
          f"std=PKR {np.std(aco_bills):>8,.2f}")
    print(f"  ACO vs Greedy savings: {(g_bill - np.mean(aco_bills))/g_bill*100:.2f}%")
    return rand_bills, g_bill, aco_bills


# ============================================================================
# Plotting
# ============================================================================

def plot_results(size_data, ants_data, iter_data, history,
                 rand_bills, g_bill, aco_bills, outdir="results"):
    import os
    os.makedirs(outdir, exist_ok=True)

    plt.style.use("seaborn-v0_8-whitegrid")

    # Plot 1: Time vs problem size
    fig, ax = plt.subplots(figsize=(8, 5))
    ns = [r[0] for r in size_data]
    ts = [r[1] for r in size_data]
    ax.plot(ns, ts, "o-", linewidth=2, markersize=10, color="#38bdf8")
    ax.set_xlabel("Number of shiftable appliances (n)", fontsize=12)
    ax.set_ylabel("Execution time (seconds)", fontsize=12)
    ax.set_title("ACO Execution Time vs Problem Size\n(m=20 ants, t=50 iterations)",
                 fontsize=13)
    for n, tt in zip(ns, ts):
        ax.annotate(f"{tt:.2f}s", (n, tt), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{outdir}/01_time_vs_size.png", dpi=120)
    plt.close(fig)

    # Plot 2: Time vs number of ants
    fig, ax = plt.subplots(figsize=(8, 5))
    ms = [r[0] for r in ants_data]
    ts = [r[1] for r in ants_data]
    ax.plot(ms, ts, "s-", linewidth=2, markersize=10, color="#818cf8")
    ax.set_xlabel("Number of ants (m)", fontsize=12)
    ax.set_ylabel("Execution time (seconds)", fontsize=12)
    ax.set_title("ACO Execution Time vs Colony Size\n(n=8 shiftable, t=50 iterations)",
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(f"{outdir}/02_time_vs_ants.png", dpi=120)
    plt.close(fig)

    # Plot 3: Time vs iterations
    fig, ax = plt.subplots(figsize=(8, 5))
    its = [r[0] for r in iter_data]
    ts = [r[1] for r in iter_data]
    ax.plot(its, ts, "^-", linewidth=2, markersize=10, color="#34d399")
    ax.set_xlabel("Iterations (t)", fontsize=12)
    ax.set_ylabel("Execution time (seconds)", fontsize=12)
    ax.set_title("ACO Execution Time vs Iteration Count\n(n=8 shiftable, m=20 ants)",
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(f"{outdir}/03_time_vs_iterations.png", dpi=120)
    plt.close(fig)

    # Plot 4: Convergence curve
    fig, ax = plt.subplots(figsize=(9, 5))
    iters = [h[0] for h in history]
    best_bills = [h[3] for h in history]
    ax.plot(iters, best_bills, "-", linewidth=2, color="#38bdf8", label="ACO best-so-far")
    ax.axhline(g_bill, color="#fbbf24", linestyle="--", linewidth=2, label=f"Greedy baseline")
    ax.axhline(np.mean(rand_bills), color="#f87171", linestyle=":", linewidth=2,
               label=f"Random baseline (avg)")
    ax.set_xlabel("Iteration", fontsize=12)
    ax.set_ylabel("Monthly bill (PKR)", fontsize=12)
    ax.set_title("ACO Convergence: Bill vs Iteration", fontsize=13)
    ax.legend(loc="upper right", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"{outdir}/04_convergence.png", dpi=120)
    plt.close(fig)

    # Plot 5: Quality comparison bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    methods = ["Random\n(avg of 10)", "Greedy", "ACO\n(avg of 10)"]
    values = [np.mean(rand_bills), g_bill, np.mean(aco_bills)]
    errors = [np.std(rand_bills), 0, np.std(aco_bills)]
    colors = ["#f87171", "#fbbf24", "#38bdf8"]
    bars = ax.bar(methods, values, yerr=errors, capsize=8, color=colors,
                  edgecolor="black", linewidth=1)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 200,
                f"PKR {val:,.0f}", ha="center", fontsize=11, fontweight="bold")
    ax.set_ylabel("Monthly bill (PKR)", fontsize=12)
    ax.set_title("Solution Quality Comparison", fontsize=13)
    ax.set_ylim(0, max(values) * 1.15)
    fig.tight_layout()
    fig.savefig(f"{outdir}/05_quality_comparison.png", dpi=120)
    plt.close(fig)

    # Plot 6: Hourly load profile (greedy vs ACO) — for the report visualization
    aco = ACOScheduler(n_ants=30, n_iterations=150, seed=42)
    aco_sol, _, _, _ = aco.run(verbose=False)
    aco_full = build_full_schedule(aco_sol)
    aco_profile = [
        sum(APPLIANCES[i].watts for i, slots in aco_full.items() if h in slots)
        for h in range(24)
    ]
    g_choices, _ = greedy_cheapest_first()
    g_full = build_full_schedule(g_choices)
    g_profile = [
        sum(APPLIANCES[i].watts for i, slots in g_full.items() if h in slots)
        for h in range(24)
    ]

    fig, ax = plt.subplots(figsize=(11, 5))
    hours = np.arange(24)
    width = 0.4
    ax.bar(hours - width/2, g_profile, width, label="Greedy", color="#fbbf24",
           edgecolor="black", linewidth=0.5)
    ax.bar(hours + width/2, aco_profile, width, label="ACO", color="#38bdf8",
           edgecolor="black", linewidth=0.5)
    ax.axhline(LOAD_CAPACITY_WATTS, color="red", linestyle="--",
               label=f"Capacity limit ({LOAD_CAPACITY_WATTS}W)")
    # Shade peak/off-peak
    for h in range(24):
        if 18 <= h < 22:
            ax.axvspan(h - 0.5, h + 0.5, color="#f87171", alpha=0.10)
        elif 22 <= h or h < 6:
            ax.axvspan(h - 0.5, h + 0.5, color="#34d399", alpha=0.10)
    ax.set_xlabel("Hour of day", fontsize=12)
    ax.set_ylabel("Total load (W)", fontsize=12)
    ax.set_title(
        "24-hour Load Profile: Greedy vs ACO\n"
        "(green=off-peak 0.7x | red=peak 1.5x)", fontsize=13)
    ax.set_xticks(hours)
    ax.legend(loc="upper left", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{outdir}/06_load_profile.png", dpi=120)
    plt.close(fig)

    print(f"\nAll graphs saved to ./{outdir}/")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("EMPIRICAL ANALYSIS - ACO Appliance Scheduler")
    print("=" * 70)

    size_data = experiment_size_scaling()
    ants_data = experiment_ants_scaling()
    iter_data, history = experiment_iterations_scaling()
    rand_bills, g_bill, aco_bills = experiment_quality_comparison()

    plot_results(size_data, ants_data, iter_data, history,
                 rand_bills, g_bill, aco_bills)

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)

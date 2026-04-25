"""
Flask backend for the ACO Appliance Scheduler demo.

Endpoints:
  GET  /                  -> serves the demo page
  GET  /api/appliances    -> returns the default appliance dataset (JSON)
  POST /api/run           -> streams ACO iterations as Server-Sent Events
                             (so the frontend can animate progress live)

Architecture:
  The ACO algorithm itself is unmodified — we import the same aco_scheduler.py
  used in the empirical analysis and the report. This file is purely a thin
  HTTP wrapper around it. That way, the algorithm shown in the demo is provably
  the same one analyzed in the report.
"""

import json
import time
from dataclasses import asdict
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

import aco_scheduler as A

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Static endpoints
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/appliances")
def get_appliances():
    """Return the default appliance dataset for the input form."""
    data = []
    for i, a in enumerate(A.APPLIANCES):
        data.append({
            "index": i,
            "name": a.name,
            "watts": a.watts,
            "required_hours": a.required_hours,
            "shiftable": a.shiftable,
            "fixed_slots": list(a.fixed_slots) if a.fixed_slots else [],
        })
    return jsonify({
        "appliances": data,
        "capacity_watts": A.LOAD_CAPACITY_WATTS,
        "fixed_charge": A.FIXED_CHARGE,
    })


# ---------------------------------------------------------------------------
# The streaming ACO endpoint
# ---------------------------------------------------------------------------

def sse(event_dict):
    """Format a Python dict as a Server-Sent Event line."""
    return f"data: {json.dumps(event_dict)}\n\n"


@app.route("/api/run", methods=["POST"])
def run_aco():
    """
    Run ACO and stream progress to the client.

    Request body (JSON):
      appliances:   [{name, watts, required_hours, shiftable, fixed_slots}]  (optional override)
      capacity:     int                       (optional)
      n_ants:       int   (default 20)
      n_iterations: int   (default 80)
      seed:         int   (default 42)
      delay_ms:     int   (default 80)        # animation pacing

    Streams events of type:
      meta        — initial setup info
      baseline    — random/greedy bill values for the chart
      iteration   — per-iteration best bill, mean fitness, current best schedule
      done        — final result with full schedule, savings vs baselines
      error       — any exception
    """
    payload = request.get_json(silent=True) or {}
    n_ants = int(payload.get("n_ants", 20))
    n_iterations = int(payload.get("n_iterations", 80))
    seed = int(payload.get("seed", 42))
    delay_ms = int(payload.get("delay_ms", 80))

    # Optional appliance override
    if "appliances" in payload and payload["appliances"]:
        custom = []
        for a in payload["appliances"]:
            custom.append(A.Appliance(
                name=a["name"],
                watts=int(a["watts"]),
                required_hours=int(a["required_hours"]),
                shiftable=bool(a["shiftable"]),
                fixed_slots=tuple(a.get("fixed_slots", []) or []),
            ))
        A.APPLIANCES.clear()
        A.APPLIANCES.extend(custom)
    if "capacity" in payload and payload["capacity"]:
        A.LOAD_CAPACITY_WATTS = int(payload["capacity"])

    @stream_with_context
    def generate():
        try:
            # ---------- Meta ----------
            yield sse({
                "type": "meta",
                "n_ants": n_ants,
                "n_iterations": n_iterations,
                "appliances": [
                    {"name": a.name, "watts": a.watts,
                     "required_hours": a.required_hours,
                     "shiftable": a.shiftable,
                     "fixed_slots": list(a.fixed_slots) if a.fixed_slots else []}
                    for a in A.APPLIANCES
                ],
                "capacity": A.LOAD_CAPACITY_WATTS,
            })

            # ---------- Baselines (computed up-front for the chart) ----------
            rand_bills = [A.random_baseline(s)[1] for s in range(5)]
            rand_avg = sum(rand_bills) / len(rand_bills)
            _, greedy_bill = A.greedy_cheapest_first()
            yield sse({
                "type": "baseline",
                "random_avg": rand_avg,
                "greedy": greedy_bill,
            })

            # ---------- ACO main loop, manually unrolled so we can stream ----------
            aco = A.ACOScheduler(
                n_ants=n_ants, n_iterations=n_iterations, seed=seed,
                alpha=1.0, beta=3.0, rho=0.10, q=100.0,
            )
            best_sol = None
            best_fit = float("-inf")
            best_bill = 0.0

            import numpy as np
            for it in range(n_iterations):
                shiftable_solutions = [aco.construct_solution() for _ in range(n_ants)]
                full_schedules = [A.build_full_schedule(s) for s in shiftable_solutions]
                evals = [A.evaluate(s) for s in full_schedules]
                fitnesses = [e[0] for e in evals]
                bills = [e[1] for e in evals]

                it_best_idx = int(np.argmax(fitnesses))
                if fitnesses[it_best_idx] > best_fit:
                    best_fit = fitnesses[it_best_idx]
                    best_sol = shiftable_solutions[it_best_idx]
                    best_bill = bills[it_best_idx]

                aco.update_pheromones(shiftable_solutions, fitnesses, best_sol, best_fit)

                # Build slot-load profile of best-so-far for the chart
                full_best = A.build_full_schedule(best_sol)
                profile = [0] * 24
                for app_idx, slots in full_best.items():
                    watts = A.APPLIANCES[app_idx].watts
                    for h in slots:
                        profile[h] += watts

                # Snapshot of pheromone matrix (downsample for transfer size)
                tau_snapshot = aco.tau.tolist()

                yield sse({
                    "type": "iteration",
                    "iteration": it,
                    "best_bill": float(best_bill),
                    "mean_fit": float(np.mean(fitnesses)),
                    "iteration_bills": [float(b) for b in bills],
                    "load_profile": profile,
                    "best_schedule": {
                        str(k): list(v) for k, v in best_sol.items()
                    } if best_sol else {},
                    "tau": tau_snapshot,
                })

                if delay_ms > 0:
                    time.sleep(delay_ms / 1000.0)

            # ---------- Done ----------
            full_best = A.build_full_schedule(best_sol)
            yield sse({
                "type": "done",
                "best_bill": float(best_bill),
                "best_schedule": {
                    str(k): list(v) for k, v in best_sol.items()
                },
                "appliance_names": [a.name for a in A.APPLIANCES],
                "savings_vs_random": float(rand_avg - best_bill),
                "savings_vs_greedy": float(greedy_bill - best_bill),
                "pct_vs_random": float((rand_avg - best_bill) / rand_avg * 100),
                "pct_vs_greedy": float((greedy_bill - best_bill) / greedy_bill * 100),
            })
        except Exception as e:
            import traceback
            yield sse({"type": "error", "message": str(e),
                       "trace": traceback.format_exc()})

    return Response(generate(), mimetype="text/event-stream")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n  ACO Appliance Scheduler — local demo")
    print("  Open http://127.0.0.1:5000 in your browser\n")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)

# ACO Appliance Scheduler — Live Demo

A web-based demonstration of the Ant Colony Optimization algorithm running on
the appliance scheduling problem analyzed in the report.

## What this demo shows

Open the page in your browser. You'll see:

- **Pheromone matrix** — a 15 × 24 grid (one row per appliance, one column per
  hour-of-day). As ACO runs, brighter cells indicate stronger pheromone trails,
  meaning the colony is "agreeing" that a particular appliance should run at a
  particular hour. This is the algorithm's *learned memory* visualised in real
  time.

- **Convergence chart** — the best-so-far monthly bill plotted against
  iteration number, with the greedy and random baselines as dashed reference
  lines. You'll see ACO start above greedy, dive below it within ~10–20
  iterations, and stabilise.

- **Live stats** — current iteration, current best bill, and savings vs the
  greedy baseline, updating each iteration.

- **Final schedule** — once the algorithm finishes, the recommended hour-by-hour
  schedule for every appliance is displayed.

The algorithm runs on the **same `aco_scheduler.py`** used in the empirical
analysis and the report. The Flask backend is a thin wrapper — no algorithmic
changes.

## How to run it

### Easy way (Windows)

Double-click **`run.bat`**. It installs Flask if needed, starts the server,
and opens your browser automatically.

### Manual way (any OS)

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Architecture

```
Browser  ──HTTP──>  Flask (app.py)
                       │
                       ▼
                aco_scheduler.py   <-- the algorithm itself, unchanged
```

The frontend posts ACO parameters to `/api/run`. The backend executes ACO
iteration-by-iteration and streams updates back to the browser using
**Server-Sent Events** (SSE). The browser draws each iteration's pheromone
state and bill onto the page in real time.

## Files

```
aco_web/
├── app.py                  # Flask backend (HTTP + SSE)
├── aco_scheduler.py        # Algorithm (copy of the one analyzed in the report)
├── templates/
│   └── index.html          # Frontend (HTML + CSS + JavaScript, single file)
├── requirements.txt
├── run.bat                 # Windows one-click launcher
└── README.md
```

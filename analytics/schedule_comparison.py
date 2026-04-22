# analytics/schedule_comparison.py
#
# Automatically simulates all busy-hour schedules across all models
# and displays results side-by-side for comparison.
#
# DROP THIS FILE into your  analytics/  folder.
# Then add  option 7  in main.py  (instructions at bottom of this file).

import time
import math
import numpy as np
from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel
from rich.columns import Columns
from rich.text    import Text
from rich import box

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — SCHEDULE DEFINITIONS
# Each schedule represents a real hospital time-of-day scenario.
# mu (service rate) stays fixed — same doctors, same speed.
# lambda changes — patient demand varies throughout the day.
# ─────────────────────────────────────────────────────────────────────────────

SCHEDULES = [
    {
        "label":       "06:00–08:00",
        "period":      "Early Morning",
        "emoji":       "🌅",
        "lambda":      3,
        "description": "Low demand — walk-ins only",
    },
    {
        "label":       "08:00–10:00",
        "period":      "Morning Rush",
        "emoji":       "🌄",
        "lambda":      6,
        "description": "Referrals + scheduled patients",
    },
    {
        "label":       "10:00–12:00",
        "period":      "Peak Hours",
        "emoji":       "☀️ ",
        "description": "Highest demand of the day",
        "lambda":      9,
    },
    {
        "label":       "12:00–14:00",
        "period":      "Lunch Lull",
        "emoji":       "🌤️ ",
        "lambda":      5,
        "description": "Drop in arrivals at midday",
    },
    {
        "label":       "14:00–16:00",
        "period":      "Afternoon Peak",
        "emoji":       "🌇",
        "lambda":      8,
        "description": "Second wave — afternoon patients",
    },
    {
        "label":       "16:00–18:00",
        "period":      "Evening Wind-Down",
        "emoji":       "🌆",
        "lambda":      4,
        "description": "Reducing demand toward close",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — DEPARTMENT DEFINITIONS
# Each department has its own mu and number of servers.
# These match your existing scenarios.json exactly.
# ─────────────────────────────────────────────────────────────────────────────

DEPARTMENTS = [
    {
        "name":    "OPD",
        "mu":      12,
        "servers": 2,
        "model":   "MMK",
        "color":   "cyan",
    },
    {
        "name":    "Pharmacy",
        "mu":      8,
        "servers": 3,
        "model":   "MMK",
        "color":   "green",
    },
    {
        "name":    "Laboratory",
        "mu":      6,
        "servers": 2,
        "model":   "MMK",
        "color":   "yellow",
    },
    {
        "name":    "QC Inspection",
        "mu":      2.4,
        "servers": 1,
        "model":   "MG1",
        "Cs2":     0.5,
        "color":   "magenta",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — ANALYTICAL FORMULA ENGINE
# These are the same formulas from your models/ folder,
# inlined here so this file is self-contained and portable.
# ─────────────────────────────────────────────────────────────────────────────

def compute_mm1(lam, mu):
    """M/M/1 analytical formulas."""
    rho = lam / mu
    if rho >= 1:
        return None   # unstable — caller handles this
    lq = rho**2 / (1 - rho)
    wq = lq / lam * 60          # convert hours → minutes
    return {"rho": rho, "Lq": lq, "Wq_min": wq}


def compute_mmk(lam, mu, k):
    """M/M/K analytical formulas using Erlang-C."""
    rho = lam / (k * mu)
    if rho >= 1:
        return None
    r = lam / mu
    # P0 — probability system is empty
    sum_terms = sum((r**n) / math.factorial(n) for n in range(k))
    last_term  = (r**k) / (math.factorial(k) * (1 - rho))
    P0 = 1 / (sum_terms + last_term)
    # Lq
    lq = (P0 * (r**k) * rho) / (math.factorial(k) * (1 - rho)**2)
    wq = lq / lam * 60
    return {"rho": rho, "Lq": lq, "Wq_min": wq}


def compute_mg1(lam, mu, Cs2=0.5):
    """M/G/1 Pollaczek-Khinchine formula."""
    rho = lam / mu
    if rho >= 1:
        return None
    lq = (rho**2 * (1 + Cs2)) / (2 * (1 - rho))
    wq = lq / lam * 60
    return {"rho": rho, "Lq": lq, "Wq_min": wq}


def run_formula(dept, lam):
    """Dispatch to the correct analytical model for a department."""
    model = dept["model"]
    if model == "MM1":
        return compute_mm1(lam, dept["mu"])
    elif model == "MMK":
        return compute_mmk(lam, dept["mu"], dept["servers"])
    elif model == "MG1":
        return compute_mg1(lam, dept["mu"], dept.get("Cs2", 0.5))
    return None

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — SIMULATION ENGINE
# Minimal SimPy simulation inlined here.
# Reuses the same logic as simulation/simulator.py.
# ─────────────────────────────────────────────────────────────────────────────

def run_simulation(lam, mu, k, sim_hours=2, seed=42, erlang_k=None):
    """
    Discrete-event simulation of an M/M/K or M/Ek/K queue.
    Returns avg wait time (min) and avg queue length.
    sim_hours=2 keeps each run fast for live demos.
    """
    import simpy

    rng       = np.random.default_rng(seed)
    waits     = []
    queue_log = []

    def service_time():
        if erlang_k:
            # Erlang-k = sum of k exponentials each with rate k*mu
            return sum(rng.exponential(1 / (erlang_k * mu))
                       for _ in range(erlang_k))
        return rng.exponential(1 / mu)

    def patient(env, server):
        arrival = env.now
        with server.request() as req:
            yield req
            wait = env.now - arrival
            waits.append(wait)
            yield env.timeout(service_time())

    def arrivals(env, server):
        while True:
            yield env.timeout(rng.exponential(1 / lam))
            queue_log.append(len(server.queue))
            env.process(patient(env, server))

    env    = simpy.Environment()
    server = simpy.Resource(env, capacity=k)
    env.process(arrivals(env, server))
    env.run(until=sim_hours)

    avg_wait = float(np.mean(waits)) * 60 if waits else 0.0
    avg_lq   = float(np.mean(queue_log))  if queue_log else 0.0
    return {"Wq_sim_min": round(avg_wait, 2), "Lq_sim": round(avg_lq, 3)}

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — VISUAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def rho_bar(rho, width=20):
    """
    Visual utilisation bar.
    Green < 0.70 | Yellow 0.70–0.85 | Red > 0.85
    """
    if rho is None:
        return Text("██ UNSTABLE ██", style="bold red")

    filled = int(round(rho * width))
    empty  = width - filled

    if rho < 0.70:
        style = "bold green"
        label = "LOW"
    elif rho < 0.85:
        style = "bold yellow"
        label = "MED"
    else:
        style = "bold red"
        label = "HIGH"

    bar = Text()
    bar.append("█" * filled, style=style)
    bar.append("░" * empty,  style="dim white")
    bar.append(f"  {rho:.2%} {label}", style=style)
    return bar


def lq_bar(lq, max_lq=20, width=15):
    """Horizontal bar proportional to queue length."""
    if lq is None:
        return Text("∞ UNSTABLE", style="bold red")
    filled = min(int((lq / max_lq) * width), width)
    color  = "green" if lq < 2 else "yellow" if lq < 5 else "red"
    bar = Text()
    bar.append("▓" * filled, style=f"bold {color}")
    bar.append(f"  {lq:.2f}", style=color)
    return bar


def status_icon(rho):
    if rho is None or rho >= 1:  return "[bold red]✘ FAIL [/bold red]"
    if rho >= 0.85:               return "[bold red]⚠ HIGH [/bold red]"
    if rho >= 0.70:               return "[yellow]~ MED  [/yellow]"
    return "[bold green]✔ OK   [/bold green]"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — DISPLAY FUNCTIONS
# Three different views you can show in the presentation.
# ─────────────────────────────────────────────────────────────────────────────

def display_schedule_table(dept, results_by_schedule):
    """
    View A — One department across all time slots.
    Shows how a single department's queue changes throughout the day.
    """
    t = Table(
        title=f"[bold]{dept['name']}  |  μ={dept['mu']}/hr  K={dept['servers']} server(s)[/bold]",
        box=box.ROUNDED,
        header_style=f"bold {dept['color']}",
        show_lines=True,
    )
    t.add_column("Time Slot",      style="bold white",  width=14)
    t.add_column("Period",         style="dim white",   width=16)
    t.add_column("λ (arr/hr)",     justify="center",    width=10)
    t.add_column("ρ Utilisation",  width=28)
    t.add_column("Lq (queue)",     width=22)
    t.add_column("Wq (min)",       justify="right",     width=10)
    t.add_column("Status",         justify="center",    width=10)

    for sched, res in zip(SCHEDULES, results_by_schedule):
        if res is None:
            t.add_row(
                sched["label"], sched["period"],
                str(sched["lambda"]),
                Text("SYSTEM UNSTABLE", style="bold red"),
                Text("∞", style="bold red"),
                "∞",
                "[bold red]✘ FAIL[/bold red]",
            )
        else:
            t.add_row(
                f"{sched['emoji']} {sched['label']}",
                sched["period"],
                str(sched["lambda"]),
                rho_bar(res["rho"]),
                lq_bar(res["Lq"]),
                f"{res['Wq_min']:.1f}",
                status_icon(res["rho"]),
            )
    console.print(t)


def display_crossdept_table(schedule, dept_results):
    """
    View B — One time slot across all departments.
    Shows which department is most stressed at a given hour.
    """
    t = Table(
        title=f"[bold]All Departments  |  {schedule['emoji']} {schedule['period']}  "
              f"({schedule['label']})  —  λ = {schedule['lambda']} arrivals/hr[/bold]",
        box=box.ROUNDED,
        header_style="bold white",
        show_lines=True,
    )
    t.add_column("Department",    style="bold white",  width=16)
    t.add_column("Model",         justify="center",    width=10)
    t.add_column("Servers",       justify="center",    width=9)
    t.add_column("ρ Utilisation", width=28)
    t.add_column("Lq (waiting)",  width=22)
    t.add_column("Wq (min)",      justify="right",     width=10)
    t.add_column("Status",        justify="center",    width=10)

    for dept, res in zip(DEPARTMENTS, dept_results):
        if res is None:
            t.add_row(
                dept["name"], dept["model"], str(dept["servers"]),
                Text("UNSTABLE", style="bold red"),
                Text("∞",        style="bold red"),
                "∞", "[bold red]✘[/bold red]",
            )
        else:
            t.add_row(
                f"[{dept['color']}]{dept['name']}[/{dept['color']}]",
                dept["model"],
                str(dept["servers"]),
                rho_bar(res["rho"]),
                lq_bar(res["Lq"]),
                f"{res['Wq_min']:.1f}",
                status_icon(res["rho"]),
            )
    console.print(t)


def display_heatmap(all_results):
    """
    View C — Full heatmap: every department × every time slot.
    The complete picture — colour-coded by queue severity.
    """
    console.print(Panel(
        "[bold white]FULL DAY QUEUE HEATMAP[/bold white]  —  "
        "[green]■ Low (Lq<2)[/green]  "
        "[yellow]■ Medium (Lq 2–5)[/yellow]  "
        "[red]■ High (Lq>5)[/red]  "
        "[bold red]■ UNSTABLE[/bold red]",
        style="bold white on dark_blue"
    ))

    t = Table(box=box.SIMPLE_HEAD, header_style="bold white", show_lines=False)
    t.add_column("Time  /  Dept", style="bold white", width=16)

    for dept in DEPARTMENTS:
        t.add_column(dept["name"], justify="center",
                     style=f"bold {dept['color']}", width=16)

    for i, sched in enumerate(SCHEDULES):
        row_cells = [f"{sched['emoji']} {sched['label']}\n{sched['period']}"]
        for j, dept in enumerate(DEPARTMENTS):
            res = all_results[i][j]
            if res is None:
                cell = Text("✘ UNSTBL", style="bold red on dark_red")
            else:
                lq = res["Lq"]
                wq = res["Wq_min"]
                if lq < 2:
                    style = "bold green"
                    icon  = "✔"
                elif lq < 5:
                    style = "bold yellow"
                    icon  = "~"
                else:
                    style = "bold red"
                    icon  = "⚠"
                cell = Text(
                    f"{icon} Lq={lq:.1f}\n  Wq={wq:.0f}m",
                    style=style
                )
            row_cells.append(cell)
        t.add_row(*row_cells)

    console.print(t)


def display_simulation_vs_analytical(dept, schedule):
    """
    View D — Side-by-side analytical vs simulation for one dept + time slot.
    Demonstrates that simulation converges to theory.
    """
    lam = schedule["lambda"]
    console.rule(
        f"[bold cyan]Analytical vs Simulation  |  "
        f"{dept['name']}  |  {schedule['period']}  λ={lam}[/bold cyan]"
    )

    analytical = run_formula(dept, lam)

    sim_results = {}
    for hours in [2, 8, 50, 200]:
        sim_results[hours] = run_simulation(
            lam=lam, mu=dept["mu"], k=dept["servers"],
            sim_hours=hours,
            erlang_k=dept.get("erlang_k"),
        )

    t = Table(box=box.ROUNDED, show_lines=True,
              title="[bold]Convergence: Simulation → Analytical (longer = more accurate)[/bold]")
    t.add_column("Source",         style="bold white",  width=22)
    t.add_column("Lq (queue len)", justify="right",     width=16)
    t.add_column("Wq (wait min)",  justify="right",     width=16)
    t.add_column("Accuracy",       width=26)

    if analytical:
        t.add_row(
            "[bold cyan]Analytical (exact)[/bold cyan]",
            f"[bold cyan]{analytical['Lq']:.3f}[/bold cyan]",
            f"[bold cyan]{analytical['Wq_min']:.2f}[/bold cyan]",
            "[bold cyan]★ Ground Truth[/bold cyan]",
        )
        t.add_section()

    for hours, sim in sim_results.items():
        if analytical:
            err = abs(sim["Lq_sim"] - analytical["Lq"]) / max(analytical["Lq"], 0.001) * 100
            if err < 10:   acc_style, acc_label = "green",  f"≈ {err:.1f}% off  ✔"
            elif err < 25: acc_style, acc_label = "yellow", f"≈ {err:.1f}% off  ~"
            else:          acc_style, acc_label = "red",    f"≈ {err:.1f}% off  ✘"
            acc_text = Text(acc_label, style=f"bold {acc_style}")
        else:
            acc_text = Text("(no analytical baseline)", style="dim")

        t.add_row(
            f"Simulation  {hours:>4}hr run",
            str(sim["Lq_sim"]),
            str(sim["Wq_sim_min"]),
            acc_text,
        )

    console.print(t)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — MASTER RUNNER
# Computes ALL results upfront, then offers a menu of views.
# ─────────────────────────────────────────────────────────────────────────────

def run_schedule_comparison():
    """
    Main entry point — called from main.py option 7.
    Pre-computes all analytical results then offers interactive views.
    """
    console.print()
    console.print(Panel(
        "[bold white]🏥  NAIROBI HOSPITAL — FULL DAY SCHEDULE COMPARISON[/bold white]\n"
        "[dim]Analytical queuing models run across all departments and all time slots[/dim]",
        style="bold on dark_blue", padding=(1, 4)
    ))

    # ── Pre-compute ALL analytical results (instant — no simulation) ──────────
    console.print("\n[dim]Computing analytical results for all schedules × departments...[/dim]")
    t0 = time.time()

    # all_results[schedule_index][dept_index] = result dict or None
    all_results = []
    for sched in SCHEDULES:
        row = []
        for dept in DEPARTMENTS:
            row.append(run_formula(dept, sched["lambda"]))
        all_results.append(row)

    elapsed = time.time() - t0
    console.print(
        f"[green]✔ Done — {len(SCHEDULES)} schedules × "
        f"{len(DEPARTMENTS)} departments = "
        f"{len(SCHEDULES)*len(DEPARTMENTS)} scenarios computed in "
        f"{elapsed:.3f}s[/green]\n"
    )

    # ── Interactive menu ──────────────────────────────────────────────────────
    while True:
        console.print("[bold cyan]─── Choose a View ───────────────────────────────────────[/bold cyan]")
        console.print("  [bold]A[/bold]  One department across all time slots")
        console.print("  [bold]B[/bold]  All departments at one time slot")
        console.print("  [bold]C[/bold]  Full heatmap (all departments × all time slots)")
        console.print("  [bold]D[/bold]  Simulation vs Analytical convergence demo")
        console.print("  [bold]Q[/bold]  Back to main menu\n")

        choice = console.input("[bold yellow]Select view [A/B/C/D/Q]: [/bold yellow]").strip().upper()

        if choice == "Q":
            break

        elif choice == "A":
            # Pick a department
            console.print()
            for i, d in enumerate(DEPARTMENTS, 1):
                console.print(f"  {i}. [{d['color']}]{d['name']}[/{d['color']}]  "
                               f"(μ={d['mu']}, K={d['servers']})")
            try:
                di = int(console.input("\n[yellow]Select department [1-4]: [/yellow]")) - 1
                dept = DEPARTMENTS[di]
                console.print()
                display_schedule_table(dept, [all_results[si][di] for si in range(len(SCHEDULES))])
            except (ValueError, IndexError):
                console.print("[red]Invalid selection[/red]")

        elif choice == "B":
            # Pick a time slot
            console.print()
            for i, s in enumerate(SCHEDULES, 1):
                console.print(f"  {i}. {s['emoji']} {s['label']}  —  {s['period']}  (λ={s['lambda']})")
            try:
                si = int(console.input("\n[yellow]Select time slot [1-6]: [/yellow]")) - 1
                sched = SCHEDULES[si]
                console.print()
                display_crossdept_table(sched, all_results[si])
            except (ValueError, IndexError):
                console.print("[red]Invalid selection[/red]")

        elif choice == "C":
            console.print()
            display_heatmap(all_results)

        elif choice == "D":
            # Pick dept and time slot for convergence demo
            console.print()
            for i, d in enumerate(DEPARTMENTS, 1):
                console.print(f"  {i}. [{d['color']}]{d['name']}[/{d['color']}]")
            try:
                di = int(console.input("\n[yellow]Select department [1-4]: [/yellow]")) - 1
                for i, s in enumerate(SCHEDULES, 1):
                    console.print(f"  {i}. {s['emoji']} {s['period']}  λ={s['lambda']}")
                si = int(console.input("[yellow]Select time slot [1-6]: [/yellow]")) - 1
                console.print(
                    "\n[dim]Running simulations at 4 different durations "
                    "(2hr / 8hr / 50hr / 200hr)...[/dim]\n"
                )
                display_simulation_vs_analytical(DEPARTMENTS[di], SCHEDULES[si])
            except (ValueError, IndexError):
                console.print("[red]Invalid selection[/red]")

        console.print()


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE MODE  —  python analytics/schedule_comparison.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_schedule_comparison()
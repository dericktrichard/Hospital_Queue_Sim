import json
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, FloatPrompt
from models.mm1 import MM1
from models.mmk import MMK
from models.mg1 import MG1
from simulation.simulator import HospitalSimulator
from analytics.reporter import print_results
from analytics.schedule_comparison import run_schedule_comparison   # ← NEW

console = Console()

def run_scenario(name, cfg):
    console.rule(f"[bold yellow]{cfg['description']}")
    lam, mu, k = cfg["lambda"], cfg["mu"], cfg["servers"]

    # Analytical
    try:
        if cfg["model"] == "MM1":
            m = MM1(lam, mu)
        elif cfg["model"] == "MMK":
            m = MMK(lam, mu, k)
        elif cfg["model"] == "MG1":
            m = MG1(lam, mu, cfg.get("Cs2", 1.0))
        print_results(f"[Analytical] {name}", m.summary())
    except ValueError as e:
        console.print(f"[bold red]⚠ Analytical model skipped: {e}[/bold red]")
        console.print(f"[dim]Tip: ρ must be < 1. Try increasing servers or reducing λ.[/dim]\n")

    # Simulation
    sim = HospitalSimulator(lam, mu, num_servers=k,
                            sim_hours=8,
                            erlang_k=cfg.get("erlang_k"))
    sim.run(department=name)
    print_results(f"[Simulation - 8hr run] {name}", sim.results())

def main():
    console.print("\n[bold cyan]🏥 Nairobi Hospital Queuing Analysis System[/bold cyan]")
    console.print("[dim]Models: M/M/1, M/M/K, M/G/1 | Simulation via SimPy[/dim]\n")

    with open("data/scenarios.json") as f:
        scenarios = json.load(f)

    console.print("[bold]Available Scenarios:[/bold]")
    for i, (k, v) in enumerate(scenarios.items(), 1):
        console.print(f"  {i}. {k} — {v['description']}")

    console.print("  5. Custom input")
    console.print("  6. Run ALL scenarios")
    console.print("  7. [bold cyan]Full day schedule comparison (all departments)[/bold cyan]")  # ← NEW
    console.print()

    choice = Prompt.ask("Select", choices=["1","2","3","4","5","6","7"])   # ← 7 added

    keys = list(scenarios.keys())
    if choice in ["1","2","3","4"]:
        name = keys[int(choice)-1]
        run_scenario(name, scenarios[name])
    elif choice == "6":
        for name, cfg in scenarios.items():
            run_scenario(name, cfg)
    elif choice == "7":                    # ← NEW block
        run_schedule_comparison()
    else:
        # Custom
        lam = FloatPrompt.ask("Arrival rate λ (per hr)")
        mu  = FloatPrompt.ask("Service rate μ (per hr)")
        k   = IntPrompt.ask("Number of servers")
        cfg = {"description": "Custom", "lambda": lam, "mu": mu,
               "servers": k, "erlang_k": None,
               "model": "MM1" if k==1 else "MMK", "Cs2": 1.0}
        run_scenario("Custom", cfg)

if __name__ == "__main__":
    main()
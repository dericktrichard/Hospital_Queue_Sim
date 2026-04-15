# dashboard/visualize.py
import matplotlib.pyplot as plt
import numpy as np
from simulation.simulator import HospitalSimulator

def plot_queue_vs_servers(lam=15, mu=12, max_k=5):
    """Show how adding servers reduces queue length."""
    ks, Lqs, Wqs = [], [], []
    for k in range(1, max_k+1):
        sim = HospitalSimulator(lam, mu, num_servers=k, sim_hours=8)
        sim.run()
        r = sim.results()
        ks.append(k)
        Lqs.append(r["Avg queue length (simulated)"])
        Wqs.append(r["Avg wait time (min)"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Hospital OPD: Effect of Adding Servers", fontsize=14, fontweight='bold')

    ax1.bar(ks, Lqs, color='steelblue')
    ax1.set_xlabel("Number of Servers (K)")
    ax1.set_ylabel("Avg Queue Length")
    ax1.set_title("Queue Length vs Servers")

    ax2.bar(ks, Wqs, color='tomato')
    ax2.set_xlabel("Number of Servers (K)")
    ax2.set_ylabel("Avg Wait Time (min)")
    ax2.set_title("Wait Time vs Servers")

    plt.tight_layout()
    plt.savefig("queue_analysis.png", dpi=150)
    plt.show()
    print("Chart saved as queue_analysis.png")

if __name__ == "__main__":
    plot_queue_vs_servers()
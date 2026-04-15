# 🏥 Nairobi Hospital Queuing Analysis System

A practical implementation of **Queuing Theory** (from BSM course) applied
to a Kenyan hospital outpatient setting.

## Models Implemented
| Model | Kendall Notation | Use Case |
|-------|-----------------|----------|
| Model I   | M/M/1 : ∞/FCFS | OPD single doctor |
| Model VII | M/M/K : ∞/FCFS | Pharmacy, 3 counters |
| Model V/VI| M/G/1 (P-K)    | Lab with Erlang service |

## Run
```bash
python main.py          # Interactive CLI
python dashboard/visualize.py   # Generate charts
```
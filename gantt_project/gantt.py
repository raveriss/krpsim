#!/usr/bin/env python3

from typing import TypedDict, List
import warnings
import matplotlib.pyplot as plt
import pandas as pd

# Filtrer l’avertissement de glyphe manquant (optionnel)
warnings.filterwarnings("ignore", message="Glyph 128736")

class Task(TypedDict):
    Task: str
    Start: int
    Duration: int

# Définition des tâches avec typage explicite
tasks: List[Task] = [
    {"Task": "do_etagere #1",    "Start": 0,  "Duration": 10},
    {"Task": "do_montant #1",    "Start": 0,  "Duration": 15},
    {"Task": "do_fond",          "Start": 0,  "Duration": 20},
    {"Task": "do_etagere #2",    "Start": 1,  "Duration": 10},
    {"Task": "do_montant #2",    "Start": 1,  "Duration": 15},
    {"Task": "do_etagere #3",    "Start": 2,  "Duration": 10},
    {"Task": "do_armoire_ikea",  "Start": 20, "Duration": 30},
]

# Transformation en DataFrame avec annotation de type
df: pd.DataFrame = pd.DataFrame(tasks)
df["Finish"] = df["Start"] + df["Duration"]
df = df.sort_values(by="Start", ascending=True)

# Création du diagramme de Gantt
fig: plt.Figure
ax: plt.Axes
fig, ax = plt.subplots(figsize=(10, 6))

for idx, row in df.iterrows():
    ax.barh(row["Task"], row["Duration"], left=row["Start"], align="center")

ax.set_xlabel("Temps")
ax.set_ylabel("Tâches")
ax.set_title("Diagramme de Gantt")
ax.grid(True)

plt.tight_layout()
plt.show()

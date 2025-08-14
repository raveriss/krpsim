import matplotlib.pyplot as plt
import pandas as pd

# Données du résultat krpsim
tasks_data = [
    {"Task": "cuisson_1", "Start": 0, "Duration": 10},
    {"Task": "cuisson_2", "Start": 10, "Duration": 10},
    {"Task": "cuisson_4", "Start": 20, "Duration": 10},
    {"Task": "cuisson_5", "Start": 30, "Duration": 10},
]

df = pd.DataFrame(tasks_data)
df["Finish"] = df["Start"] + df["Duration"]

# Création du diagramme de Gantt
fig, ax = plt.subplots(figsize=(8, 3))
for idx, row in df.iterrows():
    ax.barh(row["Task"], row["Duration"], left=row["Start"])

ax.set_xlabel("Temps")
ax.set_ylabel("Tâches")
ax.set_title("Diagramme de Gantt - Processus de cuisson")
ax.grid(True, axis="x", linestyle="--", alpha=0.6)

plt.tight_layout()
plt.show()

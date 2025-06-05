import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap, BoundaryNorm

# Define breaks and colors to match the attached colorbar
breaks = [
    0, 0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2,
    2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.6, 7, 8, 9, 10, 12, 14, 16, 20, 24
]
colors = [
    "#ffffff",  # 0
    "#e0f7fa",  # 0.01
    "#b2ebf2",  # 0.05
    "#b2f7e6",  # 0.1
    "#a7e9af",  # 0.15
    "#7ed957",  # 0.2
    "#43a047",  # 0.3
    "#00bcd4",  # 0.4
    "#2196f3",  # 0.5
    "#42a5f5",  # 0.75
    "#1976d2",  # 1
    "#64b5f6",  # 1.25
    "#90caf9",  # 1.5
    "#b3e5fc",  # 1.75
    "#fbc02d",  # 2
    "#f9a825",  # 2.5
    "#f57c00",  # 3
    "#ef6c00",  # 3.5
    "#e65100",  # 4
    "#e53935",  # 4.5
    "#b71c1c",  # 5
    "#c62828",  # 5.5
    "#ad1457",  # 6
    "#6a1b9a",  # 6.6
    "#7b1fa2",  # 7
    "#8e24aa",  # 8
    "#9c27b0",  # 9
    "#6d4c41",  # 10
    "#795548",  # 12
    "#a1887f",  # 14
    "#bcaaa4",  # 16
    "#212121",  # 20
    "#fff59d",  # 24
]
cmap = ListedColormap(colors)
norm = BoundaryNorm(breaks, ncolors=len(colors))

# Draw a custom colorbar where each color segment is the same width
fig, ax = plt.subplots(figsize=(len(breaks) * 0.7, 5))
ax.set_axis_off()

# Draw rectangles for each color step, all the same width
n = len(breaks) - 1
bar_width = 1.0 / n
for i in range(n):
    ax.add_patch(
        plt.Rectangle(
            (i * bar_width, 0), bar_width, 1,
            color=colors[i], transform=ax.transAxes, clip_on=False, linewidth=0
        )
    )

# Draw ticks and labels
for i in range(len(breaks)):
    xpos = i * bar_width
    ax.text(
        xpos, -0.08, str(breaks[i]),
        ha='center', va='top', fontsize=20, rotation=45, transform=ax.transAxes
    )

# Draw label
ax.text(0.5, 1.15, 'Total Precipitation (inches)', ha='center', va='bottom', fontsize=24, transform=ax.transAxes)

plt.xlim(0, 1)
plt.ylim(0, 1)
plt.savefig("PRECIP_colorbar.png", dpi=220, bbox_inches='tight', transparent=True)
plt.close()

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm
import numpy as np

# Lightning colorbar settings
vmin = 0
vmax = 20  # Adjust as needed for your data range
gamma = 0.5
cmap = 'inferno'

fig, ax = plt.subplots(figsize=(8, 1.2), dpi=300)
fig.subplots_adjust(bottom=0.5, top=0.9, left=0.05, right=0.95)

norm = PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)
cb = matplotlib.colorbar.ColorbarBase(
    ax, cmap=cmap, norm=norm, orientation='horizontal', extend='max'
)
cb.set_label('Lightning (flashes/grid cell)')
cb.set_ticks(np.linspace(vmin, vmax, 11))
cb.set_ticklabels([f"{int(t)}" for t in np.linspace(vmin, vmax, 11)])

plt.savefig("LIGHTNING_colorbar.png", bbox_inches='tight', pad_inches=0.1, transparent=True)
plt.close(fig)
print("Colorbar PNG saved as LIGHTNING_colorbar.png")

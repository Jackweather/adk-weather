import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

# MSLP colorbar settings (hPa)
mslp_levels = np.arange(960, 1050+1, 10)  # 960 to 1050 hPa, every 10 hPa
cmap = LinearSegmentedColormap.from_list(
    "mslp_cmap",
    [
        "#313695",  # deep blue (low pressure)
        "#4575b4",
        "#74add1",
        "#abd9e9",
        "#e0f3f8",
        "#ffffbf",  # neutral (yellow)
        "#fee090",
        "#fdae61",
        "#f46d43",
        "#d73027",  # deep red (high pressure)
    ],
    N=256
)

vmin = mslp_levels[0]
vmax = mslp_levels[-1]

fig, ax = plt.subplots(figsize=(8, 1.2), dpi=300)
fig.subplots_adjust(bottom=0.5, top=0.9, left=0.05, right=0.95)

norm = plt.Normalize(vmin=vmin, vmax=vmax)
cb = matplotlib.colorbar.ColorbarBase(
    ax, cmap=cmap, norm=norm, orientation='horizontal', extend='both'
)
cb.set_label('Mean Sea Level Pressure (hPa)')
cb.set_ticks(mslp_levels)
cb.set_ticklabels([str(int(t)) for t in mslp_levels])

plt.savefig("mslp_colorbar.png", bbox_inches='tight', pad_inches=0.1, transparent=True)
plt.close(fig)
print("Colorbar PNG saved as mslp_colorbar.png")

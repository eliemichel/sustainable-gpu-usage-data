import numpy as np
import matplotlib.pyplot as plt

import matplotlib.patches as mpatches
import matplotlib.path as mpath
Path = mpath.Path


def make_bar_link_patch(
    start_bar_x,
    start_bar_y_range,
    end_bar_x,
    end_bar_y_range,
    color = 'r',
    alpha = 0.5,
    ec=None,
    linewidth=0
):
    """Utility function to draw a link between two bars of a bar chart"""
    bar_x_diff = end_bar_x - start_bar_x
    path_data = [
        (Path.MOVETO, (start_bar_x, start_bar_y_range[0])),
        (Path.CURVE4, (start_bar_x + bar_x_diff * 0.333, start_bar_y_range[0])),
        (Path.CURVE4, (start_bar_x + bar_x_diff * 0.667, end_bar_y_range[0])),
        (Path.CURVE4, (end_bar_x, end_bar_y_range[0])),
        (Path.LINETO, (end_bar_x, end_bar_y_range[1])),
        (Path.CURVE4, (start_bar_x + bar_x_diff * 0.667, end_bar_y_range[1])),
        (Path.CURVE4, (start_bar_x + bar_x_diff * 0.333, start_bar_y_range[1])),
        (Path.CURVE4, (start_bar_x, start_bar_y_range[1])),
        (Path.CLOSEPOLY, (0, 0)),
    ]
    codes, verts = zip(*path_data)
    path = Path(verts, codes)
    return mpatches.PathPatch(
        path,
        linewidth=linewidth,
        ec=ec,
        facecolor=color,
        alpha=alpha,
    )

def demo():
    species = (
        "Adelie\n $\\mu=$3700.66g",
        "Chinstrap\n $\\mu=$3733.09g",
        "Gentoo\n $\\mu=5076.02g$",
    )
    weight_counts = {
        "Below": np.array([70, 31, 58]),
        "Above": np.array([82, 37, 66]),
    }
    width = 0.5

    fig, ax = plt.subplots()
    bottom = np.zeros(3)

    for boolean, weight_count in weight_counts.items():
        p = ax.bar(species, weight_count, width, label=boolean, bottom=bottom)
        bottom += weight_count

    ax.set_title("Number of penguins with above average body mass")
    ax.legend(loc="upper right")

    above = weight_counts["Above"]
    below = weight_counts["Below"]
    for column in range(len(species) - 1):
        start_bar_y_range = below[column], below[column] + above[column]
        end_bar_y_range = below[column+1], below[column+1] + above[column+1]
        ax.add_patch(make_bar_link_patch(
            column + width/2, start_bar_y_range,
            column + 1 - width/2, end_bar_y_range,
            color = (1.0, 0.5, 0.0),
            alpha = 0.2,
        ))

    plt.show()

# demo()

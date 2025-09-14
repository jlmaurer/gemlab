from typing import cast

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from scipy.stats import gaussian_kde


def graph_correlations(corr_mat: np.ndarray, names: list[str] | None = None) -> None:
    """Correlation plot for an N x D array of D variables"""
    num_samples, num_vars = corr_mat.shape
    if num_vars > 15:
        print('Too many variables, plot will not look good')
        return

    num_bins = int(np.ceil(np.sqrt(num_samples)))

    _, axes = plt.subplots(num_vars, num_vars, figsize=(8, 8), layout='constrained')
    axes = cast(np.ndarray[Axes], axes)  # type: ignore numpy/numpy#24738
    for k1 in range(num_vars):
        for k2 in range(num_vars):
            if k1 < k2:
                xy = np.vstack([corr_mat[:, k2], corr_mat[:, k1]])
                z = gaussian_kde(xy)(xy)
                axes[k1, k2].scatter(corr_mat[:, k2], corr_mat[:, k1], c=z, s=1)
                if names is not None:
                    axes[k1, k2].set_xlabel(names[k1])
                    axes[k1, k2].set_ylabel(names[k2])

            elif k1 == k2:
                axes[k1, k2].hist(corr_mat[:, k1], num_bins, density=True)
                if names is not None:
                    axes[k1, k2].set_xlabel(names[k1])

            else:
                axes[k1, k2].remove()

    plt.show()

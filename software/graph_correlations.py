import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde


def graph_correlations(corr_mat, names=None):
    """Correlation plot for an N x D array of D variables"""    
    Nsamples, Nvars = corr_mat.shape
    if Nvars > 15:
        print('Too many variables, plot will not look good')
        return None
    
    nbins = int(np.ceil(np.sqrt(Nsamples)))

    fig, axs = plt.subplots(Nvars, Nvars, figsize=(8,8), layout='constrained')
    for k1 in range(Nvars):
        for k2 in range(Nvars):
            if k1 < k2:
                xy = np.vstack([corr_mat[:,k2], corr_mat[:,k1]])
                z = gaussian_kde(xy)(xy)
                axs[k1,k2].scatter(corr_mat[:,k2], corr_mat[:,k1], c=z, s=1)
                if names is not None:
                    axs[k1,k2].set_xlabel(names[k1])
                    axs[k1,k2].set_ylabel(names[k2])

            elif k1 == k2:
                axs[k1,k2].hist(corr_mat[:,k1], nbins, density=True)
                if names is not None:
                    axs[k1,k2].set_xlabel(names[k1])
            
            else:
                axs[k1,k2].remove()
            
    
    plt.show()
                
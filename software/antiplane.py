import numpy as np


def inter_rate(sdot, D, x):
    return (sdot/np.pi) * np.arctan2(x,D)


def coseismic_disp(sdot, D, x):
    return (sdot/np.pi) * np.arctan2(D, x)


def inter_strain(sdot, D, x):
    return -0.5 * (sdot/np.pi) * (1/D) / (1 + np.square(x/D))


def plot_def(fun, sdot, D, scale):
    import matplotlib.pyplot as plt

    x = np.linspace(-scale, scale, 101)
    deformation = fun(sdot, D, x)

    plt.figure(figsize=(10,3))
    plt.plot(x, deformation)
    plt.plot(x[x<0], -(sdot/2) * np.ones((50,1)))
    plt.plot(x[x>0], (sdot/2) * np.ones((50,1)))
    plt.ylim([-0.6 * sdot,0.6 * sdot])
    plt.xlabel('Distance')
    plt.show()    

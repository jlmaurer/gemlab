import numpy as np


def mw2mo(Mw):
    return 10 ** (1.5 * (Mw + 6.03))


def mo2area(Mo, dtau=3):
    """Dtau is in MPa"""
    area = (Mo / (dtau * 1e6)) ** (2 / 3)
    return area / 1e6  # convert m^2 to km^2


def mo2mw(Mo):
    return (2 / 3) * np.log10(Mo * 1e7) - 10.7

"""
Find the reference point in temporalCoherence.h5
"""

import random

import numpy as np
from osgeo import gdal


ds: gdal.Dataset | None = gdal.Open('temporalCoherence.h5', gdal.GA_ReadOnly)
assert ds is not None
data = ds.GetRasterBand(1).ReadAsArray()

yx = random.choice(np.argwhere(data == data.max()))

print('y:', yx[0], ', x:', yx[1])

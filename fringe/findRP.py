import argparse
import random

import numpy as np
from osgeo import gdal


parser = argparse.ArgumentParser(description='find the reference point in temporalCoherence.h5')

ds = gdal.Open('temporalCoherence.h5', gdal.GA_ReadOnly)
data = ds.GetRasterBand(1).ReadAsArray()

yx = random.choice(np.argwhere(data == data.max()))

print('y:', yx[0], ', x:', yx[1])

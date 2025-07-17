import numpy as np


# Bounding box holding latitudes and longitudes, formatted "South, North, West, East".
# RAiDER's preferred format.
type SNWE = tuple[float, float, float, float]

# A bounding box format we run into from other applications.
# CAREFUL NOT TO MIX THEM UP! These types are here so you can annotate different
# bounding boxes according to their layout and tell them apart.
# Can also be thought of as "minx, miny, maxx, maxy", where Y/North is positive.
type WSEN = tuple[float, float, float, float]


# Helpers for type annotating the dimensions of a numpy array.
# When you use these, your type checker will alert you when an annotated array
# is used in a way inconsistent with its dimensions.
type FloatArray1D = np.ndarray[tuple[int], np.dtype[np.floating]]
type FloatArray2D = np.ndarray[tuple[int, int], np.dtype[np.floating]]
type FloatArray3D = np.ndarray[tuple[int, int, int], np.dtype[np.floating]]
# ... (repeat the pattern as needed for higher dimensions)

# Any number of dimensions -- when ndim is not able to be known ahead of time
type FloatArrayND = np.ndarray[tuple[int, ...], np.dtype[np.floating]]

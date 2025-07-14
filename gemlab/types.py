import numpy as np


# Bounding box formatted South and North latitudes, then West and East longitudes
type SNWE = tuple[float, float, float, float]

type WSEN = tuple[float, float, float, float]

# Helpers for numpy's verbose and ugly typing
type FloatArray1D = np.ndarray[tuple[int], np.dtype[np.floating]]
type FloatArray2D = np.ndarray[tuple[int, int], np.dtype[np.floating]]
type FloatArray3D = np.ndarray[tuple[int, int, int], np.dtype[np.floating]]

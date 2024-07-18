import h5py
import os

from pyproj import CRS
from rasterio import open,Affine
from rasterio.warp import reproject, Resampling
import pyproj


DEFAULT_DICT = {
    'driver': 'GTiff', 
    'dtype': 'float64', 
    'nodata': 0, 
    'width': 6, 
    'height': 6, 
    'count': 1, 
    'crs': CRS.from_epsg(4326), 
    'transform': Affine(30.0, 0.0, -105.0, 0.0, -30.0, 105.0), 
    'blockysize': 6, 
    'tiled': False, 
    'interleave': 'band', 
    'compress': 'lzw',
}


def read_h5(fname):
    with h5py.File(fname, 'r') as f:
        vel = f['velocity'][()]
        width = int(f.attrs['WIDTH'])
        hgt = int(f.attrs['FILE_LENGTH'])
        R = f.attrs['EARTH_RADIUS']
        crs = f.attrs['EPSG']
        ndv = f.attrs['NO_DATA_VALUE']
        xstep = f.attrs['X_STEP']
        ystep = f.attrs['Y_STEP']        
        lat1 = float(f.attrs['LAT_REF1'])
        lon1 = float(f.attrs['LON_REF4'])

    profile = DEFAULT_DICT
    profile['nodata'] = float(ndv)
    profile['width'] = width
    profile['height'] = hgt
    profile['crs'] = CRS.from_user_input(crs)
    profile['dtype'] = vel[0,0].dtype
    profile['transform'] = Affine(float(xstep), 0, lon1, 0, float(ystep), lat1) 
    
    return vel, profile

def write_gtiff(fname, outname=None):
    '''Read an HDF5 velocity file and write the velocity out to a GeoTiff'''
    if outname is None:
        outname = os.path.splitext(fname)[0] + '.tif'
    vel, profile = read_h5(fname) 
    ds = open(outname, "w")
    ds.profile = profile
    ds.write(vel, 1)
    ds.close()

    
def reproject_geotiff(input_filename, output_filename, src_epsg, dst_epsg, resampling=Resampling.nearest):
  """
  Reprojects a GeoTIFF from one coordinate system to another.

  Args:
      input_filename: Path to the input GeoTIFF file.
      output_filename: Path to the output GeoTIFF file.
      src_epsg: EPSG code of the source coordinate system.
      dst_epsg: EPSG code of the destination coordinate system.
      resampling: Resampling method to use during reprojection (default: nearest).
  """
  # Open the source GeoTIFF
  with open(input_filename) as src:
    # Get source data, transform, and CRS
    data = src.read(1)
    src_transform = src.transform
    src_crs = src.crs

  # Define source and destination CRS objects using pyproj
  src_crs_obj = pyproj.CRS.from_epsg(src_epsg)
  dst_crs_obj = pyproj.CRS.from_epsg(dst_epsg)

  # Perform reprojection using rasterio.warp.reproject
  destination_transform, destination_data = reproject(
      data,
      src_transform=src_transform,
      src_crs=src_crs_obj,
      dst_crs=dst_crs_obj,
      resampling=resampling,
  )

  # Open the output GeoTIFF with updated information
  with open(output_filename, "w", driver="GTiff", height=data.shape[0], width=data.shape[1],
            count=1, dtype=data.dtype, transform=destination_transform, crs=dst_crs) as dst:
    dst.write(destination_data, 1)


def single_band_to_rgb(input_filename, output_filename):
  """
  Converts a single-band GeoTIFF to a 3-band grayscale RGB image.

  Args:
      input_filename: Path to the single-band GeoTIFF file.
      output_filename: Path to the output 3-band RGB GeoTIFF file.
  """
  # Open the single-band GeoTIFF
  with open(input_filename) as src:
    data = src.read(1)
    transform = src.transform
    crs = src.crs

  # Create a 3-band array by replicating the single band
  rgb_data = np.stack([data, data, data], axis=-1)

  # Write the replicated data as a 3-band GeoTIFF
  with open(output_filename, "w", driver="GTiff", height=data.shape[0], width=data.shape[1],
            count=3, dtype=data.dtype, transform=transform, crs=crs) as dst:
    dst.write(rgb_data)


if __name__=='__main__':
    write_gtiff('velocity.h5', outname='velocity.tif')   
    reproject_geotiff('velocity.tif', 'velocity_geo.tif', '32615', '4326')
    single_band_to_rgb('velocity_geo.tif', 'velocity_visual.tif')


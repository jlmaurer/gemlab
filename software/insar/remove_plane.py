import rasterio

import numpy as np
import matplotlib.pyplot as plt


def read_raster(filename='velocity.tif'):
    '''
    Read a raster file and return its data, coordinates, and metadata.
    '''
    with rasterio.open(filename, 'r') as f:
        trans = f.transform
        vel = f.read(1)
        x = np.array([trans[2] + trans[0]*k for k in range(vel.shape[1])])
        y = np.array([trans[5] + trans[4]*k for k in range(vel.shape[0])])
        X,Y = np.meshgrid(x, y)
        mask = vel != f.nodata
        vel = vel[mask]
        X = X[mask]
        Y = Y[mask]

    return vel, X, Y

def remove_planar_trend(vel, X, Y):
    '''
    Remove a planar trend from the velocity data.
    '''
    if np.abs(X.max()) > 1e4:
        big_flag = True
        X = X/1000. # scale X,Y for better numerical stability
        Y = Y/1000.

    G = np.stack([np.ones(len(vel)), X, Y], axis=-1) 

    # solve for three parameters: two slopes and an intercept
    mhat, res, rank, s = np.linalg.lstsq(G,vel, rcond=None)
    predicted_plane = np.dot(G, mhat)
    vel_detrended = vel - predicted_plane
    if big_flag:
        mhat = [m / 1000. for m in mhat]
    return vel_detrended, mhat


def write_vel_to_raster(veldata, old_raster='velocity.tif', new_raster='velocity_noplane.tif'):
    '''
Write the detrended velocity data to a new raster file.
    '''
    with rasterio.open(old_raster, 'r') as src:
        vel = src.read(1)
        vel[vel != src.nodata] = veldata
        with rasterio.open(new_raster, 'w', **src.meta) as dst:
            dst.write(vel, 1)


def plot_velocity(raster, title='Detrended Velocity'):
    '''
    Plot the detrended velocity data.
    '''
    with rasterio.open(raster, 'r') as f:
        vel = f.read(1)
        trans = f.transform

    plt.figure(figsize=(10, 6))
    plt.imshow(vel, cmap='viridis',extent=(trans[2], trans[2] + trans[0] * vel.shape[1], trans[5] + trans[4] * vel.shape[0], trans[5]), origin='upper')
    plt.colorbar(label='Velocity (m/s)')
    plt.title(title)
    plt.show()


if __name__ == '__main__':
    vel, X, Y = read_raster()
    vel_detrended, mhat = remove_planar_trend(vel, X, Y)
    write_vel_to_raster(vel_detrended)
    print(f'Detrended velocity written to velocity_noplane.tif with parameters: {mhat}')
    print('Mean and standard deviation of original velocity:{:.5f}, {:.5f} m/yr'.format(np.mean(vel), np.std(vel)))
    print('Mean and standard deviation of detrended velocity:{:.5f}, {:.5f} m/yr'.format(np.mean(vel_detrended), np.std(vel_detrended)))
    print('Done.')
    # TODO: add plotting functionality
    # print('To visualize the results, use the following command:')
    # print('python -m remove_plane.plot_velocity --raster velocity_noplane.tif --title "Detrended Velocity"')
    # print('You can also use the following command to visualize the original velocity data:')
    # print('python -m remove_plane.plot_velocity --raster velocity.tif --title "Original Velocity"')

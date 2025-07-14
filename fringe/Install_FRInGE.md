# Install FRInGE

Steps to install Fringe - estimate deformation time-series by exploiting interferometric covariance matrix for distributed scatterers (DS) and the phase history of pixels that exhibit very little temporal variation (PS)

## Step 1: Set upthe environment
Create a conda environment for running fringe
```
> conda create -n fringe python=3.8
> conda activate fringe
```

### 1.1 Prerequisites
```
> conda install cmake
> conda install cython
> conda install gdal
> conda install libgdal
> conda install armadillo
> conda install lapack
> conda install blas
> conda install -c conda-forge isce2
> conda install gxx_linux-64
> conda install pybind11=2.9
# libgdal is installed when installing gdal
```
### 1.2 Set ISCE2 environment variables

**IMPORTANT** : Set ISCE2 environment variables before installing Fringe

Fringe installation will fail if these variables aren't set. This should be corrected in the Fringe installation guide.
```
# Option 1
ISCE_HOME=/home/rd873/anaconda3/envs/isce2/lib/python3.7/site-packages/isce
ISCE_STACK=/home/rd873/anaconda3/envs/isce2/share/isce2
PATH=$ISCE_HOME/bin:$ISCE_HOME/applications:$ISCE_STACK/topsStack:$ISCE_STACK/stripmapStack:$ISCE_STACK/prepStackToStaMPS/bin:$PATH
PYTHONPATH=/home/rd873/anaconda3/envs/isce2/lib/python3.7/site-packages:$PYTHONPATH

# Option 2
ISCE_HOME=/home/mrl83k/.conda/envs/fringe/lib/python3.8/site-packages/isce
ISCE_STACK=/home/mrl83k/.conda/envs/fringe/share/isce2
PATH=$ISCE_HOME/bin:$ISCE_HOME/applications:$ISCE_STACK/topsStack:$ISCE_STACK/stripmapStack:$ISCE_STACK/prepStackToStaMPS/bin:$PATH
PYTHON_PATH=/home/mrl83k/.conda/envs/fringe/lib/python3.8/site-packages
```
Edit the lines according to your path

## Step 2: Install FRInGE

Follow steps in https://github.com/isce-framework/fringe/blob/main/docs/install.md

```
> cd ~/softwares
> rm -rf fringe
> mkdir fringe
> cd fringe
```
### 2.1 Separate folders

The `src`, `build` and `install` folders need to be separate.

```
> mkdir install build src
```

### 2.2 Clone the repo

```
> cd src
> git clone https://github.com/isce-framework/fringe.git
```

### 2.3 Build and install

In the build folder

```
> cd build

# On OSX
> CXX=clang++ cmake -DCMAKE_FIND_FRAMEWORK=NEVER -DCMAKE_INSTALL_PREFIX=../install ../src/fringe

# On Linux
> CXX=g++ cmake -DCMAKE_INSTALL_PREFIX=../install ../src/fringe

# If "conda install gxx_linux-64 / clangxx_osx-64"
> CXX=${CXX} cmake -DCMAKE_INSTALL_PREFIX=../install ../src/fringe

---

# With python 3.7 or python 3.8 or in cases when cmake cannot
# find the correct Python paths run with 
# (Option 1)        
# > CXX=${CXX} cmake -DPython_EXECUTABLE=~/anaconda3/envs/isce2/bin/python \
#	-DPython_INCLUDE_DIR=~/anaconda3/envs/isce2/include/python3.7m \
#	-DPython_LIBRARY=~/anaconda3/envs/isce2/lib/libpython3.7m.so \
#	-DCMAKE_INSTALL_PREFIX=../install ../src/fringe

# (Option 2) 
# > CXX=${CXX} cmake -DPython_EXECUTABLE=/home/mrl83k/.conda/envs/fringe/bin/python \
#   -DPython_INCLUDE_DIR=/home/mrl83k/.conda/envs/fringe/include/python3.8 \ 
#   -DPython_LIBRARY=/home/mrl83k/.conda/envs/fringe/lib/libpython3.8.so \ 
#   -DCMAKE_INSTALL_PREFIX=./install ../src/fringe
```

Don't forget to **edit the lines according to your conda env python installation**.

```
> make all
# if cannot find the header crypt.h then run
# > conda install -c conda-forge libxcrypt

> make install
```

### 2.4 Set environment variables

Set the following variables after installation

```
export PATH=$PATH:/home/rd873/softwares/fringe/install/bin
export PYTHONPATH=$PYTHONPATH:/home/rd873/softwares/fringe/install/python
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/rd873/softwares/fringe/install/lib
```
edit the lines according to your path.

## An error you might run into

* Note if getting error `cmake: error while loading shared libraries: librhash.so.0: cannot open shared object file: No such file or directory` 
check `/user/envs/bin/` and see if there is a cmake file. Delete that and it gets rid of it.

* Note if getting error `ImportError: libgfortran.so.3: cannot open shared object file: No such file or directory`, do `conda install -c conda-forge libgfortran`.

* Note when installing ISCE got the error `Added empty dependency for problem type SOLVER_RULE_UPDATE` in the solving environment however it seemed to have otherwise installed without any other incident.

* If getting `CMakeLists.txt not found error` make sure if there should be `..` or `.`. It tells it to go back to the build folder. `../install ../src/fringe`

* To install fringe in the python 3.8 environment, it had to be `./install ../src/fringe` 

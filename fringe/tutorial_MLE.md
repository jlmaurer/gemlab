# Fringe
---

**Requirements:**
```
* combine_SLCs.py
* prep_fringe_downsampled.py
* make_geometry.py
* findRP.py
```

Create a fringe folder and activate the **ISCE2** environment first. 

If ../merged/SLC/_date_/* folder only has two files ( `*.slc.full.vrt`, `*.slc.full.xml` ), we should combine SLC first.

```bash

python combine_SLCs.py -p /mnt/stor/geob/jlmd9g/YiChieh/Haiti/SenDT69/stack_Oct27/merged

```

After this step, there should be five files in each date folder ( `*.slc.full`, `*.slc.full.aux.xml`, `*.slc.full.vrt`, `*.slc.full.xml`, `*.slc.hdr` ).

## Step 1. 

In the fringe folder, run the commands below.

```bash

tops2vrt.py -i ../merged/ -s coreg_stack -g geometry -c slcs -b 0 24710 56370 67680

nmap.py -i coreg_stack/slcs_base.vrt -o KS2/nmap -c KS2/count -x 5 -y 5

sequential.py -i ../merged/SLC -s 30 -o Sequential -w KS2/nmap -b coreg_stack/slcs_base.vrt -x 5 -y 5

```

### An error you might run into

* If getting the error `ERROR 4: coreg_stack/slcs_base.vrt: No such file or directory Cannot open stack file { coreg_stack/slcs_base.vrt } with GDAL for reading. GDALOpen failed - coreg_stack/slcs_base.vrt Exiting with error code .... (102)`. Change the line `coreg_stack/slcs_base.vrt` to whatever the full path name is, or if still not working, just find out what the bounding box coordinates related to the file are. In this case, they were the same as `nmap.py` file.  

* If `nmaplib not found` error happens, make sure that either a direct path is set or activate_isce.sh was set. 

* If either error appears: 
```
Traceback (most recent call last):

File "/home/mrl83k/SEFStorage/Maryann/tools/fringe/src/fringe/src/sequential/sequential.py", line 168, in inps.bbox = tuple([int(i) for i in inps.bbox])

File "/home/mrl83k/SEFStorage/Maryann/tools/fringe/src/fringe/src/sequential/sequential.py", line 168, in inps.bbox = tuple([int(i) for i in inps.bbox])

ValueError: invalid literal for int() with base 10: '/home/mrl83k/SEFStorage/Maryann/tools/fringe/coreg_stack/slcs_base.vrt'
```

OR 
```
Number of SLCs discovered: 0 


We assume that the SLCs and the ann files are sorted in the same order writing /mnt/stor/geob/jlmd9g/Maryann/tools/fringe/Sequential/Datum_connection/stack/stack.vrt

Traceback (most recent call last): File "/home/mrl83k/SEFStorage/Maryann/tools/fringe/src/fringe/src/sequential/sequential.py", line 253, in compSlcStack.writeStackVRT()

File "/mnt/stor/geob/jlmd9g/Maryann/tools/fringe/src/fringe/src/sequential/Stack.py", line 143, in writeStackVRT width, height, xmin, ymin, xsize, ysize = self.get_x_y_offsets(-1)

File "/mnt/stor/geob/jlmd9g/Maryann/tools/fringe/src/fringe/src/sequential/Stack.py", line 161, in get_x_y_offsets slc = self.slcList[ind]

IndexError: list index out of range
```

Unfortunately, for the above, the only solution that I found was to delete all the folders except for the installed ones and restart the entire first step again. It should work fine after.  


* If this error appears: 
```
Number of uint32 bytes for mask: 8 

Number of rows  = 45345 

Number of cols  = 9557 

Number of bands = 30 

Length mismatch between input dataset and weight dataset  

Exiting with error code ....(107) 

Traceback (most recent call last): 

  File "/home/mrl83k/SEFStorage/Maryann/tools/fringe/src/fringe/src/sequential/sequential.py", line 221, in <module> 

    miniStack.writeStackVRT() 

  File "/mnt/stor/geob/jlmd9g/Maryann/tools/fringe/src/fringe/src/sequential/Stack.py", line 104, in writeStackVRT 

    width = ds.RasterXSize 

AttributeError: 'NoneType' object has no attribute 'RasterXSize' 
```

This means that the x and y, aka the range and azimuth for the `nmap.py` and `sequential.py`, were not set directly. Go back and double-check those values.  

 



<aside>
    
> 💡 Hints for [tops2vrt.py]
> 
> If `-B lon/lat` failed, use `-b x/y` to replace it. 
> 
> For the value of `-b`, check the dimension of `slc.full.vrt` file (`gdalinfo merged/SLC/_date_/_date_.slc.full.vrt`)
>
> But if we use `-b` to specify the region, we should adjust the geometry manually. Please check **Making Geometry** section for more details.

</aside>



## Step 2. 

In the fringe folder, run the commands below.

```bash

adjustMiniStacks.py -s slcs/ -m Sequential/miniStacks/ -d Sequential/Datum_connection/ -M 30 -o adjusted_wrapped_DS

ampdispersion.py -i coreg_stack/slcs_base.vrt -o ampDispersion/ampdispersion -m ampDispersion/mean


cd ampDispersion

gdal2isce_xml.py -i ampdispersion

gdal2isce_xml.py -i mean


cd ..

imageMath.py -e="a<0.4" --a=ampDispersion/ampdispersion  -o ampDispersion/ps_pixels -t byte

integratePS.py -s coreg_stack/slcs_base.vrt -d adjusted_wrapped_DS/ -t Sequential/Datum_connection/EVD/tcorr.bin -p ampDispersion/ps_pixels -o PS_DS --unwrap_method snaphu

unwrapStack.py -s slcs -m Sequential/miniStacks/ -d Sequential/Datum_connection/ -M 30 -u 'unwrap_fringe.py' --unw_method snaphu


```

## Step 3. Unwrapping the interferograms

You must create the geometry **before running Step 3**. While Step 3 may still run if you manually create the `multilook.py` file, Step 4 will not work unless the geometry is properly set up.

Make sure to run `make_geometry.py` inside the `geometry` folder.

Then, navigate to the `PS_DS` folder and run the following commands. Be sure to set the rangelooks (`-r`) and azimuthlooks (`-a`) values according to your needs — and they must match the values you used in `make_geometry.py`.

In the example below, we use rangelooks = 9 and azimuthlooks = 3 (i.e., `python make_geometry.py -r 9 -a 3`).


```bash

rm *rlks9*alks3*int
ls *int >  list_int.txt

awk '{print "multilook.py "substr($1,1,17)".int -r 9 -a 3 -o "substr($1,1,17)"_rlks9_alks3.int"}' list_int.txt > multilook.txt

chmod +x multilook.txt
./multilook.txt

gdal2isce_xml.py -i tcorr_ds_ps.bin
multilook.py  tcorr_ds_ps.bin -r 9 -a 3 -o tcorr_ds_ps_rlks9_alks3.bin

ls *rlks9*alks3*int > multilook_int.txt

awk '{print "unwrap_fringe.py -m snaphu -i "$1" -c tcorr_ds_ps_rlks9_alks3.bin -o unwrap/"substr($1,1,17)".unw"}' multilook_int.txt > run_unwrap.txt

chmod +x run_unwrap.txt
./run_unwrap.txt

```
### An error you might run into

* For the module not finding “_gdal” might have to do “conda install -c conda-forge openssl=3" 


## Step 4. Generate MintPy folder

Check **line 159, 313-318** in `prep_fringe_downloaded.py`. The value of rangelooks and azimuthlooks should be consistent with what you set before.

```bash
python prep_fringe_downsampled.py  -u './PS_DS/unwrap/*.unw' -c ./PS_DS/tcorr_ds_ps.bin -g ./geometry/multi_rlks9_alks3/ -m '../reference/IW*.xml' -b ../baselines -o ./mintpy
```

## Step 5. Step of mintpy

After finishing step 4, we will get the `timeseries.h5`, `temporalCoherence.h5`, `maskPS.h5`, `inputs/ifgramStack.h5`, and `inputs/geometryRadar.h5`.

Choose the reference point (`findRP.py`) and decide the correction you want in mintpy.

```bash
reference_point.py timeseries.h5 -y 7069 -x 2552

generate_mask.py temporalCoherence.h5 -m 0.7 -o maskTempCoh.h5

#tropo_pyaps3.py -f timeseries.h5 -g inputs/geometryRadar.h5 #don't need for now 

#remove_ramp.py timeseries_ERA5.h5 -m maskTempCoh.h5 -s linear  #don't need for now 

dem_error.py timeseries.h5 -g inputs/geometryRadar.h5

timeseries2velocity.py timeseries_demErr.h5

geocode.py velocity.h5 -l inputs/geometryRadar.h5 --lalo-step 0.000833334 0.000833334

geocode.py timeseries_demErr.h5 -l inputs/geometryRadar.h5 --lalo-step 0.000833334 0.000833334

geocode.py inputs/geometryRadar.h5 -l inputs/geometryRadar.h5 --lalo-step 0.000833334 0.000833334

geocode.py maskPS.h5 -l inputs/geometryRadar.h5 --lalo-step 0.000833334 0.000833334

geocode.py maskTempCoh.h5 -l inputs/geometryRadar.h5 --lalo-step 0.000833334 0.000833334
```

**Done!** You can do the post-processing now

The finished folder structure should be similar to this: [folder structure](https://github.com/yichiehlee/gemlab/blob/tutorial_MLE.md/fringe/folder_structure.md)



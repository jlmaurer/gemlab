# Fringe
---

**Requirements:**
```
* combine_SLCs.py
* prep_fringe_downsampled.py
* make_geometry.py
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

<aside>
    
> 💡 [tops2vrt.py]
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

Go to the PS_DS folder and run the commands below. Remember to change the value of rangelooks (rlks, -r) and azimuthlooks (alks, -a). 

Here we set rangelooks as 9 and azimuthlooks as 3 as an example.


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

## Step 4. Generate mintpy folder

Check line 159, 313-318 in `prep_fringe_downloaded.py`. The value of rangelooks and azimuthlooks should be consistent with what you set before.

```bash
python prep_fringe_downsampled.py  -u './PS_DS/unwrap/*.unw' -c ./PS_DS/tcorr_ds_ps.bin -g ./geometry/multi_rlks9_alks3/ -m '../reference/IW*.xml' -b ../baselines -o ./mintpy
```

## Step 5. Step of mintpy

After finishing step 4, we will get the `timeseries.h5`, `temporalCoherence.h5`, and `inputs/geometryRadar.h5`.

Choose the reference point and decide the correction that you want to do in mintpy.

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

---

# Making Geometry

## Step 1. Create  `shadowMask.vrt`, `incLocal.vrt`, and `los.vrt` file

If we use `-b` to specify the region, we should manually adjust the geometry before **step3**. Take `-r 9 -a 3` as an example. 

After **step 1**, the geometry folder should have three files (`hgt.vrt`, `lat.vrt`, `lon.vrt`). 

Copy the format and create `shadowMask.vrt`, `incLocal.vrt`, and `los.vrt` manually (change the SourceFilename to `shadowMask.vrt`, `incLocal.vrt`, and `los.vrt`). Here is an example.

The format of `los.vrt` file is slightly different because los has two bands, including incidenceAngle and azimuthAngle. Please be careful with the indentation and the band number.

    - original file 3 (files): hgt.vrt, lat.vrt, lon.vrt
        
```bash
#shadowMask.vrt File
<VRTDataset rasterXSize="11750" rasterYSize="27450"> 
    <VRTRasterBand dataType="Float64" band="1">
      <SimpleSource>
        <SourceFilename>/mnt/stor/geob/jlmd9g/YiChieh/Haiti/SenDT69/stack_Oct27/merged/geom_reference/shadowMask.rdr.full.vrt</SourceFilename>
        <SourceBand>1</SourceBand>
        <SourceProperties RasterXSize="67584" RasterYSize="27454" DataType="Float64"/>
        <SrcRect xOff="0" yOff="0" xSize="11750" ySize="27450"/>
        <DstRect xOff="0" yOff="0" xSize="11750" ySize="27450"/>
      </SimpleSource>
    </VRTRasterBand>
</VRTDataset>
```

```bash
#incLocal.vrt File
<VRTDataset rasterXSize="11750" rasterYSize="27450">
    <VRTRasterBand dataType="Float64" band="1">
      <SimpleSource>
        <SourceFilename>/mnt/stor/geob/jlmd9g/YiChieh/Haiti/SenDT69/stack_Oct27/merged/geom_reference/incLocal.rdr.full.vrt</SourceFilename>
        <SourceBand>1</SourceBand>
        <SourceProperties RasterXSize="67584" RasterYSize="27454" DataType="Float64"/>
        <SrcRect xOff="0" yOff="0" xSize="11750" ySize="27450"/>
        <DstRect xOff="0" yOff="0" xSize="11750" ySize="27450"/>
      </SimpleSource>
    </VRTRasterBand>
</VRTDataset>
```
        
```bash
#los.vrt file
#los has 2 bands, the incidenceAngle and azimuthAngle
<VRTDataset rasterXSize="11750" rasterYSize="27450">
    <VRTRasterBand dataType="Float64" band="1">
      <SimpleSource>
        <SourceFilename>/mnt/stor/geob/jlmd9g/YiChieh/Haiti/SenDT69/stack_Oct27/merged/geom_reference/los.rdr.full.vrt</SourceFilename>
        <SourceBand>1</SourceBand>
        <SourceProperties RasterXSize="67584" RasterYSize="27454" DataType="Float64"/>
        <SrcRect xOff="0" yOff="0" xSize="11750" ySize="27450"/>
        <DstRect xOff="0" yOff="0" xSize="11750" ySize="27450"/>
      </SimpleSource>
    </VRTRasterBand>
    <VRTRasterBand dataType="Float64" band="2">
      <SimpleSource>
        <SourceFilename>/mnt/stor/geob/jlmd9g/YiChieh/Haiti/SenDT69/stack_Oct27/merged/geom_reference/los.rdr.full.vrt</SourceFilename>
        <SourceBand>2</SourceBand>
        <SourceProperties RasterXSize="67584" RasterYSize="27454" DataType="Float64"/>
        <SrcRect xOff="0" yOff="0" xSize="11750" ySize="27450"/>
        <DstRect xOff="0" yOff="0" xSize="11750" ySize="27450"/>
      </SimpleSource>
    </VRTRasterBand>
</VRTDataset>
```

## Step 2. Making Geometry

After running `make_geometry.py` there should be 30 files in the geometry folder and 24 files in the geometry/multi_rlks*_alks* folder.

```python
python make_geometry.py -r 9 -a 3
```

## Step 3. Create *.vrt file

Go to the multi_rlks*_alks* folder and create `*.vrt` files.

Copy the content from the original `*.vrt`, but change the SourceFilename to `incLocal_rlks9_alks3.rdr`.

Do the same things to the other five files. After this step, should be 30 files in the multi_rlks*_alks* folder. Here is an example.

```bash
#Check the size of incLocal_rlks9_alks3.rdr and change line1, 6, 7, and 8. 
#(line7&8) Make xOff&yOff as 0, xSize&ySize as same as the size of incLocal_rlks9_alks3.rdr.

<VRTDataset rasterXSize="1305" rasterYSize="9150"> 
    <VRTRasterBand dataType="Float64" band="1">
      <SimpleSource>
        <SourceFilename>incLocal_rlks9_alks3.rdr</SourceFilename>
        <SourceBand>1</SourceBand>
        <SourceProperties RasterXSize="1305" RasterYSize="9150" DataType="Float64"/>
        <SrcRect xOff="0" yOff="0" xSize="1305" ySize="9150"/>
        <DstRect xOff="0" yOff="0" xSize="1305" ySize="9150"/>
      </SimpleSource>
    </VRTRasterBand>
</VRTDataset>
```

```bash
<VRTDataset rasterXSize="1305" rasterYSize="9150"> 
    <VRTRasterBand dataType="Float64" band="1">
      <SimpleSource>
        <SourceFilename>los_rlks10_alks6.rdr</SourceFilename>
        <SourceBand>1</SourceBand>
        <SourceProperties RasterXSize="1305" RasterYSize="9150" DataType="Float64"/>
        <SrcRect xOff="0" yOff="0" xSize="1305" ySize="9150"/>
        <DstRect xOff="0" yOff="0" xSize="1305" ySize="9150"/>
      </SimpleSource>
    </VRTRasterBand>
    <VRTRasterBand dataType="Float64" band="2">
      <SimpleSource>
        <SourceFilename>los_rlks10_alks6.rdr</SourceFilename>
        <SourceBand>2</SourceBand>
        <SourceProperties RasterXSize="1305" RasterYSize="9150" DataType="Float64"/>
        <SrcRect xOff="0" yOff="0" xSize="1305" ySize="9150"/>
        <DstRect xOff="0" yOff="0" xSize="1305" ySize="9150"/>
      </SimpleSource>
    </VRTRasterBand>
</VRTDataset>
```

**Done**

---

The finished folder structure should be similar to this:

```bash
.
├── adjusted_wrapped_DS
│   ├── *.slc.vrt
├── ampDispersion
│   ├── ampdispersion
│   ├── ampdispersion.aux.xml
│   ├── ampdispersion.hdr
│   ├── ampdispersion.vrt
│   ├── ampdispersion.xml
│   ├── mean
│   ├── mean.aux.xml
│   ├── mean.hdr
│   ├── mean.vrt
│   ├── mean.xml
│   ├── ps_pixels
│   ├── ps_pixels.vrt
│   └── ps_pixels.xml
├── combine_SLCs.py
├── coreg_stack
│   └── slcs_base.vrt
├── geometry
│   ├── hgt.hdr
│   ├── hgt.rdr
│   ├── hgt.rdr.vrt
│   ├── hgt.rdr.xml
│   ├── hgt.vrt
│   ├── incLocal.hdr
│   ├── incLocal.rdr
│   ├── incLocal.rdr.vrt
│   ├── incLocal.rdr.xml
│   ├── incLocal.vrt
│   ├── lat.hdr
│   ├── lat.rdr
│   ├── lat.rdr.vrt
│   ├── lat.rdr.xml
│   ├── lat.vrt
│   ├── lon.hdr
│   ├── lon.rdr
│   ├── lon.rdr.vrt
│   ├── lon.rdr.xml
│   ├── lon.vrt
│   ├── los.hdr
│   ├── los.rdr
│   ├── los.rdr.vrt
│   ├── los.rdr.xml
│   ├── los.vrt
│   ├── make_geometry.py
│   ├── multi_rlks9_alks3
│   │   ├── hgt_rlks9_alks3.rdr
│   │   ├── hgt_rlks9_alks3.rdr.rsc
│   │   ├── hgt_rlks9_alks3.rdr.vrt
│   │   ├── hgt_rlks9_alks3.rdr.xml
│   │   ├── hgt.vrt
│   │   ├── incLocal_rlks9_alks3.rdr
│   │   ├── incLocal_rlks9_alks3.rdr.rsc
│   │   ├── incLocal_rlks9_alks3.rdr.vrt
│   │   ├── incLocal_rlks9_alks3.rdr.xml
│   │   ├── incLocal.vrt
│   │   ├── lat_rlks9_alks3.rdr
│   │   ├── lat_rlks9_alks3.rdr.rsc
│   │   ├── lat_rlks9_alks3.rdr.vrt
│   │   ├── lat_rlks9_alks3.rdr.xml
│   │   ├── lat.vrt
│   │   ├── lon_rlks9_alks3.rdr
│   │   ├── lon_rlks9_alks3.rdr.rsc
│   │   ├── lon_rlks9_alks3.rdr.vrt
│   │   ├── lon_rlks9_alks3.rdr.xml
│   │   ├── lon.vrt
│   │   ├── los_rlks9_alks3.rdr
│   │   ├── los_rlks9_alks3.rdr.rsc
│   │   ├── los_rlks9_alks3.rdr.vrt
│   │   ├── los_rlks9_alks3.rdr.xml
│   │   ├── los.vrt
│   │   ├── shadowMask_rlks9_alks3.rdr
│   │   ├── shadowMask_rlks9_alks3.rdr.rsc
│   │   ├── shadowMask_rlks9_alks3.rdr.vrt
│   │   ├── shadowMask_rlks9_alks3.rdr.xml
│   │   └── shadowMask.vrt
│   ├── shadowMask.hdr
│   ├── shadowMask.rdr
│   ├── shadowMask.rdr.vrt
│   ├── shadowMask.rdr.xml
│   └── shadowMask.vrt
├── KS2
│   ├── count
│   ├── count.aux.xml
│   ├── count.hdr
│   ├── nmap
│   ├── nmap.aux.xml
│   └── nmap.hdr
├── mintpy
│   ├── demErr.h5
│   ├── geo_geometryRadar.h5
│   ├── geo_maskPS.h5
│   ├── geo_maskTempCoh.h5
│   ├── geo_timeseries_demErr.h5
│   ├── geo_velocity.h5
│   ├── inputs
│   │   ├── geometryRadar.h5
│   │   └── ifgramStack.h5
│   ├── maskPS.h5
│   ├── maskTempCoh.h5
│   ├── temporalCoherence.h5
│   ├── timeseries_demErr.h5
│   ├── timeseries.h5
│   ├── timeseriesResidual.h5
│   └── velocity.h5
├── prep_fringe_downsampled.py
├── PS_DS
│   ├── *.hdr
│   ├── *.int
│   ├── *_rlks9_alks3.int
│   ├── *_rlks9_alks3.int.rsc
│   ├── list_int.txt
│   ├── multilook_int.txt
│   ├── multilook.txt
│   ├── run_unwrap.txt
│   ├── tcorr_ds_ps.bin
│   ├── tcorr_ds_ps.bin.vrt
│   ├── tcorr_ds_ps.bin.xml
│   ├── tcorr_ds_ps.hdr
│   ├── tcorr_ds_ps_rlks9_alks3.bin
│   ├── tcorr_ds_ps_rlks9_alks3.bin.rsc
│   ├── tcorr_ds_ps_rlks9_alks3.bin.vrt
│   ├── tcorr_ds_ps_rlks9_alks3.bin.xml
│   └── unwrap
│       ├── *.unw
│       ├── *.unw.conncomp
│       ├── *.unw.conncomp.vrt
│       ├── *.unw.conncomp.xml
│       ├── *.unw.vrt
│       └── *.unw.xml
├── Sequential
│   ├── compressedSlc
│   │   └── *
│   │       ├── *.slc
│   │       ├── *.slc.hdr
│   │       └── *.slc.vrt
│   ├── Datum_connection
│   │   ├── EVD
│   │   │   ├── *.slc
│   │   │   ├── *.slc.hdr
│   │   │   ├── *.slc
│   │   │   ├── *.slc.hdr
│   │   │   ├── compslc.bin
│   │   │   ├── compslc.bin.hdr
│   │   │   ├── tcorr.bin
│   │   │   └── tcorr.bin.hdr
│   │   ├── slcs
│   │   │   └── *.vrt
│   │   └── stack
│   │       └── stack.vrt
│   ├── fullStack
│   │   ├── slcs
│   │   │   └── *.vrt
│   │   └── stack
│   │       └── stack.vrt
│   └── miniStacks
│       └── *
│           ├── EVD
│           │   ├── *.slc
│           │   ├── *.slc.hdr
│           │   ├── tcorr.bin
│           │   └── tcorr.bin.hdr
│           ├── slcs
│           │   └── *.vrt
│           └── stack
│               └── stack.vrt
└── slcs
    └── *.vrt
```

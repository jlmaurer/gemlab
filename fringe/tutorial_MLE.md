# Step 1. Fringe1.bsub

under fringe_MLE folder

gdalinfo merged/SLC/_date_/_date_.slc.full.vrt, check the dimension of slc.full.vrt.file

Overlap is very less only 30. Keep it minimum 500

```bash
#!/bin/bash
#SBATCH --job-name=fringe1
#SBATCH -N 1
#SBATCH --ntasks=32
#SBATCH --time=5-00:00:00
#SBATCH --mail-type=begin,end,fail,requeue
#SBATCH --mail-user=_user_@mst.edu
#SBATCH --export=all
#SBATCH --out=Foundry-%j.out
#SBATCH --mem-per-cpu=4000
#SBATCH -p general

export PATH=/home/yl3mz/anaconda3/envs/isce2/bin:$PATH
module load anaconda
source activate  /home/yl3mz/anaconda3/envs/isce2

#run combine_SLCs.py when ../merged/SLC/*/ folder only has 2 files: *.slc.full.vrt,*.slc.full.xml
python combine_SLCs.py -p /mnt/stor/geob/jlmd9g/YiChieh/Haiti/SenDT69/stack_Oct27/merged

tops2vrt.py -i ../merged/ -s coreg_stack -g geometry -c slcs -b 0 24710 56370 67680
nmap.py -i coreg_stack/slcs_base.vrt -o KS2/nmap -c KS2/count -x 5 -y 5
sequential.py -i ../merged/SLC -s 30 -o Sequential -w KS2/nmap -b coreg_stack/slcs_base.vrt -x 5 -y 5
echo 'job finished'
```

<aside>
💡 [tops2vrt.py] -B lon/lat > failed, used -b x/y to replace it

But if we use `-b` to specify the region, we should adjust the geometry manually.

</aside>

# Step 2. Fringe2.bsub

under fringe_MLE folder

```bash
#!/bin/bash
#SBATCH --job-name=fringe1
#SBATCH -N 1
#SBATCH --ntasks=32
#SBATCH --time=5-00:00:00
#SBATCH --mail-type=begin,end,fail,requeue
#SBATCH --mail-user=_user_@mst.edu
#SBATCH --export=all
#SBATCH --out=Foundry-%j.out
#SBATCH --mem-per-cpu=4000
#SBATCH -p general

export PATH=/home/yl3mz/anaconda3/envs/isce2/bin:$PATH
module load anaconda
source activate  /home/yl3mz/anaconda3/envs/isce2
adjustMiniStacks.py -s slcs/ -m Sequential/miniStacks/ -d Sequential/Datum_connection/ -M 30 -o adjusted_wrapped_DS
ampdispersion.py -i coreg_stack/slcs_base.vrt -o ampDispersion/ampdispersion -m ampDispersion/mean

cd ampDispersion
gdal2isce_xml.py -i ampdispersion
gdal2isce_xml.py -i mean
cd ..

imageMath.py -e="a<0.4" --a=ampDispersion/ampdispersion  -o ampDispersion/ps_pixels -t byte
integratePS.py -s coreg_stack/slcs_base.vrt -d adjusted_wrapped_DS/ -t Sequential/Datum_connection/EVD/tcorr.bin -p ampDispersion/ps_pixels -o PS_DS --unwrap_method snaphu
unwrapStack.py -s slcs -m Sequential/miniStacks/ -d Sequential/Datum_connection/ -M 30 -u 'unwrap_fringe.py' --unw_method snaphu
echo 'job finished'
```

# Step 3. Fringe3.bsub

Back to the upper folder: `cd ..` , using `make_fringe.py` to generate `fringerun3.bsub` file which will under the fringe_MLE/PS_DS folder

Goal: unwrapping the interferograms

```python
python make_fringe.py -sf /mnt/stor/geob/jlmd9g/YiChieh/Haiti/SenDT69/stack_Oct27 -fn fringeMLE_Feb27_A5 -bbox '19.65 19.9 -70.65 -70.3' -ssize 30 -sn 3 -rlks 9 -alks 3
```


# Step 4. Generate mintpy folder

prep_fringe_downloaded.py

check line159, 313-318

```python
python prep_fringe_downsampled.py  -u './PS_DS/unwrap/*.unw' -c ./PS_DS/tcorr_ds_ps.bin -g ./geometry/multi_rlks9_alks3/ -m '../reference/IW*.xml' -b ../baselines -o ./mintpy
```

# Step 5. run the step of mintpy



---

# Making Geometry

1. If we use `-b` to specify the region, we should manually adjust the geometry before **step3**. Take `-r 9 -a 3` as an example. 

After **step 1**, the geometry folder should have three files (`hgt.vrt`, `lat.vrt`, `lon.vrt`). 

Copy the format and create `shadowMask.vrt`, `incLocal.vrt`, and `los.vrt` manually. Here is an example.

    - original file 3 (files): hgt.vrt, lat.vrt, lon.vrt
    - **create shadowMask, incLocal, los.vrt manually**
        
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

2. 
```python
python make_geometry.py -r 9 -a 3
```
After running `make_geometry.py`, there should be 30 files in the geometry folder and 24 files in the multi_rlks*_alks* folder.

3. cd multi & create `hgt.vrt`, the content copy from the original `*.vrt`, but change the SourceFilename to `hgt_rlks9_alks3.rdr`  (do the same things to other five files) (Total should be 30 files)

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

do the same for lon, lat, los, shadowMaksk, incLocal

remember to change prep_fringe_downsampled.py (line159, 313-318)

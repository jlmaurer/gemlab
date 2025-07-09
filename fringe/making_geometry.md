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

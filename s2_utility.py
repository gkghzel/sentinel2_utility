import os
from osgeo import gdal, gdal_array
import zipfile as zp
import re
import numpy as np
from datetime import datetime

# initialization
ws = os.getcwd()
sidiZid = ws+r"\vector_data\sz\sz_limite\limiteSidiZid.shp"
tbeinya = ws+r"\vector_data\tb\tb_limite\limiteTbeinya.shp"

# utilitary functions to manipulate confusion matrix
# --functions--

def dateTransform(dateString): # formatting date string
  day = dateString[-2:len(dateString)]
  months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
  month = months[int(dateString[4:6])-1]
  year = dateString[0:4]
  return (day, month, year)


# resampling a band to refrence band specs
def resampleToRef(Finput, Fref, Fout): # resampling input image to refrence image pixel size
  input = openDataSet(Finput)
  ref = openDataSet(Fref)
  output = rasterFromTemp(Fref, Fout, "GTiff")
  gdal.ReprojectImage(input, output, input.GetProjection(), ref.GetProjection(), gdal.gdalconst.GRA_CubicSpline)
  output = None
  input = None
  ref = None
  return 0

# clip Raster to polygon extent (resample to 10 m if needed)

def clipToPolygon10(RInput, ROutput, ClipingExtent): # cliping 10m pixel size to cliping extent
  gdal.Warp(ROutput, RInput, cutlineDSName=ClipingExtent, cropToCutline=True)
  ds = openDataSet(ROutput)
  ds.GetRasterBand(1).SetNoDataValue(0)
  ds = None
  return 0

def clipToPolygonNot10(RInput, ROutput, ClipingExtent, RasterRef): # cliping non 10m pixel size to cliping extent
  ROutputRes = ROutput+"tmp.tif"
  resampleToRef(RInput, RasterRef, ROutputRes)
  clipToPolygon10(ROutputRes, ROutput, ClipingExtent)
  os.remove(ROutputRes)
  return 0

# opening a raster as gdal dataset

def openDataSet(fn, access=1):
  ds = gdal.Open(fn, access)
  if ds is None:
    print("Failed opening raster")
  return ds

# creating a raster from template

def rasterFromTemp(fn, newFn, driName, bn=0): # creating blank raster in refrence image geotransform parameters
  ds = openDataSet(fn)
  driver = gdal.GetDriverByName(driName)
  if bn == 0:
      bn = ds.RasterCount
  print("creating "+str(bn)+" band raster")
  newDs = driver.Create(newFn, xsize=ds.RasterXSize,ysize=ds.RasterYSize, bands=bn, eType=gdal.GDT_UInt16)
  newDs.SetGeoTransform(ds.GetGeoTransform())
  newDs.SetProjection(ds.GetProjection())
  ds = None
  return newDs

# concatenating all images

def gdalBuildFullStack(sceneList, stackName='enter stackname', flist=[]): # building layerstack from bands in sceneList or flist, Output : scene instance
  outputImage = "clipped//"+stackName
  if flist == []:
    for i in sceneList:
      for j in i.toShapeBands.keys():
          flist.append(i.toShapeBands[j])
    for i in range(len(flist)):
      flist[i] = ""+flist[i]

  bandCount = len(flist)
  output = rasterFromTemp(flist[0], outputImage, "GTiff", bandCount)
  flist.sort()
  for i in range(len(flist)):
    print("Writing band "+flist[i])
    tmpDs = gdal.Open(flist[i])
    tmpBand = tmpDs.GetRasterBand(1)
    output.GetRasterBand(i+1).WriteArray(tmpBand.ReadAsArray())
    output.GetRasterBand(i+1).SetNoDataValue(0)
    if flist[i][-12:-8] != "NDVI" and flist[i][-12:-8] != "REVI" and flist[i][-12:-8] != "SWVI":
      day, month, year = dateTransform(flist[i][-27:-19])
      output.GetRasterBand(i+1).SetDescription(year +'_'+month+'_'+day+'_'+flist[i][-11:-8])
    else:
      day, month, year = dateTransform(flist[i][-28:-20])
      output.GetRasterBand(i+1).SetDescription(year +'_'+month+'_'+day+'_'+flist[i][-12:-8])

    if flist[i][-11:-8] == "B04":
      output.GetRasterBand(i+1).SetColorInterpretation(3)
    if flist[i][-11:-8] == "B03":
      output.GetRasterBand(i+1).SetColorInterpretation(4)
    if flist[i][-11:-8] == "B02":
      output.GetRasterBand(i+1).SetColorInterpretation(5) # composition coloré
  output = None

  fullScene = Scene(stackName)
  for i in flist:
    print(i)
    day, month, year = dateTransform(i[-27:-19])
    key = year+'_'+month+'_'+day+'_'+i[-12:-8]
    fullScene.toShapeBands[key] = i
  fullScene.sceneName = fullScene.fname[0:-4]
  fullScene.layerstack = "clipped//"+fullScene.fname
  fullScene.tile = sceneList[0].tile

  return fullScene



# --classes--


class Scene:
  def __init__(self, fname):
    self.fname = fname
    self.sceneName = ''
    self.fpath = ''             # file path
    self.bands = {}             # file path dictionary
    self.toShapeBands = {}      # file path dictionary
    self.layerstack = ''        # file path


  def updateTile(self):
    self.tile = self.fname[38:44]
    day, month, year = dateTransform(self.fname[11:19])
    self.sceneName = self.tile+'_'+year+'_'+month+day

  def updateBands(self): # getting available bands paths (10m, 20m, 60m)
    pattern10m = '.*10m.jp2$'
    pattern20m = '.*20m.jp2$'
    # pattern60m = '.*60m.jp2$'
    tmp = zp.ZipFile("raw\\"+self.fname, 'r')
    for i in tmp.filelist:
      if re.match(pattern10m, i.filename):
        self.bands[i.filename[-11:-8]] = i.filename
      elif re.match(pattern20m, i.filename):
        self.bands[i.filename[-11:-8]] = i.filename
      # elif re.match(pattern60m, i.filename):
      #   self.bands[i.filename[-11:-8]] = i.filename
    tmp = None
    return 0

  def extractBands(self): # extracting available bands to image specific folder
    tmp = zp.ZipFile("raw\\"+self.fname, 'r')
    
    for i in self.bands:
      if self.bands[i][0:65] in os.listdir():
        pass
      print(i+" : "+self.bands[i])
      os.chdir(r"./raw_bands")
      tmp.extract(self.bands[i])
      os.chdir(ws)
    
    tmp = None
    return 0

  def clipToShape(self, shape): # clipping bands to study area extent, resampking to 10m pixel size of needed
    pattern10m = '.*10m.jp2$'
    # ws = os.getcwd()
    
    os.mkdir("clipped\\"+self.sceneName)
    for i in self.bands:
      isLegitBand = i != "TCI" and i != "PRB" and i != "SCL" and i != "AOT" and i != "WVP"
      if re.match(pattern10m, self.bands[i]) and isLegitBand:
        print("clipping "+i)
        self.toShapeBands[i] = "clipped\\" + self.sceneName+"\\"+self.bands[i][123:-3]+"tif"
        clipToPolygon10(r"./raw_bands/"+self.bands[i], self.toShapeBands[i], shape)

    for i in self.toShapeBands:
      refBand = self.toShapeBands[i]
      break
    for i in self.bands:
      isLegitBand = i != "TCI" and i != "PRB" and i != "SCL" and i != "AOT" and i != "WVP"
      if not(re.match(pattern10m, self.bands[i])) and isLegitBand:
        print("clipping "+i)
        self.toShapeBands[i] = "clipped\\" + self.sceneName+"\\"+self.bands[i][123:-3]+"tif"
        clipToPolygonNot10(r"./raw_bands/"+self.bands[i], self.toShapeBands[i], shape, refBand)

    
    return 0

  def gdalConcat(self):  # concatenating single image bands to monodate layerstack
    inputFolder = "clipped\\"+self.sceneName
    outputImage = self.sceneName+".tif"
    ws = os.getcwd()
    os.chdir(inputFolder)
    flist = os.listdir()
    bandCount = len(flist)
    output = rasterFromTemp(flist[0], outputImage, "GTiff", bandCount)
    flist.sort()
    for i in range(len(flist)):
      print("Writing band "+flist[i])
      tmpDs = gdal.Open(flist[i])
      tmpBand = tmpDs.GetRasterBand(1)
      output.GetRasterBand(i+1).WriteArray(tmpBand.ReadAsArray())
      output.GetRasterBand(i+1).SetNoDataValue(0)
      output.GetRasterBand(i+1).SetDescription(flist[i][-11:-8])
      if flist[i][-11:-8] == "B04":
        output.GetRasterBand(i+1).SetColorInterpretation(3)
      if flist[i][-11:-8] == "B03":
        output.GetRasterBand(i+1).SetColorInterpretation(4)
      if flist[i][-11:-8] == "B02":
        output.GetRasterBand(i+1).SetColorInterpretation(5)
    output = None
    os.chdir(ws)
    self.layerstack = "clipped\\"+self.sceneName+".tif"
    return 0


# sample code

if __name__ == "__main__":
    # searching for raw files
    raw_data = os.listdir(r'./raw')
    scene_array = []
    for fname in raw_data:
        if fname =="_":
            pass
        os.chdir(r'./raw')
        scene_array.append(Scene(fname))
        os.chdir(ws)
    for scene in scene_array:
        print(scene.fname)
        scene.updateTile()
        scene.updateBands()
        scene.extractBands()

        if scene.tile == "T32SPF":
            scene.clipToShape(sidiZid)
        if scene.tile == "T32SMF":
            scene.clipToShape(tbeinya)
        
        scene.gdalConcat()

    # building a layerstack from all bands in the same tile

    T32SMF_tiles = []
    T32SPF_tiles = []

    for scene in scene_array:
        print(scene.tile)
        if scene.tile == "T32SPF":
            T32SPF_tiles.append(scene)
        if scene.tile == "T32SMF":
            T32SMF_tiles.append(scene)
    if T32SPF_tiles != []:
        T32SPF_fullstack = gdalBuildFullStack(T32SPF_tiles, "T32SPF_fullstack.tif")
    if T32SMF_tiles != []:
        T32SMF_fullstack = gdalBuildFullStack(T32SMF_tiles, "T32SMF_fullstack.tif")
            

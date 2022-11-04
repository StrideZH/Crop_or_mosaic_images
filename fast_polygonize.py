#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   fast_polygonize.py
@Time    :   2022/11/04 22:21:00
@Author  :   StrideH
@Desc    :   Test improve the speed of polygonize by cutting grid blocks, then parallel processing, and finally merging
'''


import os
from osgeo import gdal
from multiprocessing import Pool
import subprocess
import time
import shutil
import re

# 裁剪tif成xtiles * ytiles的小块
def split_raster(raster, xtiles, ytiles):
    # get raster bounds
    # 获取栅格边界
    ul = [float(i) for i in re.findall(r'\d+\.\d+', gdal.Info(raster).split('Upper Left')[1].split(')')[0])]    # 左上角坐标
    lr = [float(i) for i in re.findall(r'\d+\.\d+', gdal.Info(raster).split('Lower Right')[1].split(')')[0])]   # 右下角坐标
    xmin = ul[0]
    xsize = lr[0] - xmin
    ysize = ul[1] - lr[1]
    xdif = xsize / xtiles
    for x in range(xtiles):
        xmax = xmin + xdif
        ymax = ul[1]
        ydif = ysize / ytiles
        for y in range(ytiles):
            ymin = ymax - ydif
            # Create chunk of source raster
            gdal.Translate(
                f'output/{x}_{y}.tif',
                raster,
                projWin=[xmin, ymax, xmax, ymin],
                format='GTiff'
            )
            ymax = ymin
        xmin = xmax

# 栅格转矢量
class usage():
    def __init__(self, model, XCHUNKS, YCHUNKS, OUTPUT, RASTER):
        self.model = model
        self.XCHUNKS = XCHUNKS
        self.YCHUNKS = YCHUNKS
        self.OUTPUT = OUTPUT
        self.RASTER = RASTER
    
    # 选择转换模式
    def get_opts(self):
        if self.model == 'all' or self.model == 'single':
            print('Testing ' + self.RASTER + ' as a single file:')
            self.single_file()
        if self.model == 'all' or self.model == 'serial':
            print('Testing ' + self.RASTER + ' in serial:')
            self.in_serial()
        if self.model == 'all' or self.model == 'parallel':
            print('Testing ' + self.RASTER + ' in parallel:')
            self.in_parallel()
    
    # 单个文件直接转矢量
    def single_file(self):
        # 整栅格转矢量
        subprocess.call(["python", "gdal_polygonize.py", self.RASTER, "-f", "ESRI Shapefile", self.OUTPUT + "/temp_single.shp", "-nomask", "-8"])
        # 删除DN为0的面
        subprocess.call(["ogr2ogr", "-f", "ESRI Shapefile", self.OUTPUT + "/out_single.shp", self.OUTPUT + "/temp_single.shp", "-where", "DN != 0"])
        # 删除临时文件
        os.remove(self.OUTPUT + "/temp_single.shp")
        os.remove(self.OUTPUT + "/temp_single.shx")
        os.remove(self.OUTPUT + "/temp_single.dbf")
        os.remove(self.OUTPUT + "/temp_single.prj")

    # 分块转矢量
    def in_serial(self):
        # 切割栅格
        split_raster(self.RASTER, self.XCHUNKS, self.YCHUNKS)
        
        for x in range(0, self.XCHUNKS):
            for y in range(0, self.YCHUNKS):
                # 小块栅格转矢量
                subprocess.call(["python", "gdal_polygonize.py", self.OUTPUT + str(x) + "_" + str(y) + ".tif", "-f", "ESRI Shapefile", self.OUTPUT + "/serial_" + str(x) + "_" + str(y) + ".shp", "-nomask", "-8"])
                # 删除DN为0的面并合并
                subprocess.call(["ogr2ogr", "-f", "ESRI Shapefile", self.OUTPUT + "/out_serial.shp", self.OUTPUT + "/serial_" + str(x) + "_" + str(y) + ".shp", "-update", "-append", "-where", "DN != 0"])
                # 删除临时文件
                os.remove(self.OUTPUT + str(x) + "_" + str(y) + ".tif")
                os.remove(self.OUTPUT + "/serial_" + str(x) + "_" + str(y) + ".shp")
                os.remove(self.OUTPUT + "/serial_" + str(x) + "_" + str(y) + ".shx")
                os.remove(self.OUTPUT + "/serial_" + str(x) + "_" + str(y) + ".dbf")
                os.remove(self.OUTPUT + "/serial_" + str(x) + "_" + str(y) + ".prj")

    # 分块并行转矢量，使用多进程
    def polygonize_test(self, chunk):
        # 小块栅格转矢量
        subprocess.call(["python", "gdal_polygonize.py", "-q", self.OUTPUT + chunk + ".tif", "-f", "ESRI Shapefile", self.OUTPUT + "/parallel_" + chunk + ".shp", "-nomask", "-8"])
        # 删除DN为0的面并合并
        subprocess.call(["ogr2ogr", "-f", "ESRI Shapefile", self.OUTPUT + "/out_parallel.shp", self.OUTPUT + "/parallel_" + chunk + ".shp", "-update", "-append", "-where", "DN != 0"])
        return chunk

    # 分块并行转矢量
    def in_parallel(self):
        # 切割栅格
        split_raster(self.RASTER, self.XCHUNKS, self.YCHUNKS)
        # 多进程
        pool = Pool(processes=4)
        chunks = []
        for x in range(0, self.XCHUNKS):
            for y in range(0, self.YCHUNKS):
                chunks.append(str(x) + "_" + str(y))
                pool.apply_async(self.polygonize_test, (str(x) + "_" + str(y),))
                time.sleep(0.1) # 防止进程太快，导致文件未生成
                # print(k.get())
        
        # 关闭进程池
        pool.close()
        pool.join()

        # 删除临时文件
        for chunk in chunks:
            os.remove(self.OUTPUT + chunk + ".tif")
            os.remove(self.OUTPUT + "/parallel_" + chunk + ".shp")
            os.remove(self.OUTPUT + "/parallel_" + chunk + ".shx")
            os.remove(self.OUTPUT + "/parallel_" + chunk + ".dbf")
            os.remove(self.OUTPUT + "/parallel_" + chunk + ".prj")

if __name__ == '__main__':
    # 添加环境变量
    # os.environ['GDAL_PATH_PY'] = r'C:\Users\YeZiyu\.conda\envs\geo\Lib\site-packages\osgeo_utils'
    # os.environ['GDAL_PATH'] = r'C:\Users\YeZiyu\.conda\envs\geo\Scripts'
    
    if os.path.exists('input'):
        shutil.rmtree('input')
    if os.path.exists('output'):
        shutil.rmtree('output')
    
    os.mkdir('input')
    os.mkdir('output')
    

    INPUT = r'E:\jsnu\#00_project\mon\11.3号之前\测试数据\newresult.tif'    # 输入栅格
    OUTPUT='./output/'  # 输出路径
    RASTER='./input/temp.vrt'   # 临时虚拟栅格

    XCHUNKS = 3 # 横向切割块数
    YCHUNKS = 3 # 纵向切割块数

    # 源代码 用时18.8s
    # single 用时26s
    # 测试了x,y均为2,3,4时的用时
    # serial (x, y) = (2, 2)时用时最短 用时15s
    # parallel (x, y) = (3, 3)时用时最短 用时8.6s
    METHOD = 'single' # 转矢量方法，single为单进程，serial为分块串行，parallel为分块并行

    # make VRT, white=nodata
    os.system('gdal_translate -q -a_nodata 255 -of VRT ' + INPUT + ' ' + RASTER)

    # 实例化类
    polygonize = usage(METHOD, XCHUNKS, YCHUNKS, OUTPUT, RASTER)

    # 转矢量
    start = time.time()
    polygonize.get_opts()
    print('time: ', time.time() - start)
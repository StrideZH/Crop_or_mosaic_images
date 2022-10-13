#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   crop_merge_image.py
@Time    :   2022/9/30 15:38:45
@Author  :   StrideH
@Desc    :   crop image(.jpg, .png, .tif) and merge them back to a new image
'''

import os
from skimage import io
import geopandas as gpd
from osgeo import gdal, osr, ogr
from affine import Affine
import numpy as np
from PIL import Image
import rasterio as rio
from rasterio import features

class GRID:
    # 裁剪jpg或png图片
    @staticmethod
    def crop_image(file_path, save_path, crop_size, is_supplement = False):
        """
        :param file_path: 图片路径
        :param save_path: 保存路径
        :param crop_size: 裁剪尺寸
        :param is_supplement: 是否补全
        :return: 裁剪结果, 文件名: 原始文件名_行号_列号.jpg or png
        """
        # 获取文件名
        file_dir, file_name_ex = os.path.split(file_path)
        file_name, extension = os.path.splitext(file_name_ex)
        # 保存路径存在
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        # 读取图片
        try:
            img = io.imread(file_path)
        except:
            print('Error: {} not exist or image format is wrong.'.format(file_path))
            return
        # 图片必须大于裁剪尺寸，必须为3通道
        if len(img.shape) == 3:
            width, height, channel= img.shape
            print(img.shape)
            if width < crop_size or height < crop_size:
                print('Error: width or height < crop_size.')
                return
            # 是否补全裁剪
            wb = False
            hb = False
            num_width = width // crop_size
            num_height = height // crop_size
            if is_supplement:
                if width % crop_size != 0:
                    num_width += 1
                    wb = True
                if height % crop_size != 0:
                    num_height += 1
                    hb = True

            # 裁剪
            print('---------------------------------------------------------------------')
            print('Start crop file: {}'.format(file_path))
            print('width: {}, height: {}, channel: {}'.format(width, height, channel))
            print('---------------------------------------------------------------------')
            p = 0
            for i in range(num_width):
                offset_width = i * crop_size
                if wb and i == num_width - 1:
                    offset_width = width - crop_size
                for j in range(num_height):
                    offset_height = j * crop_size
                    if hb and j == num_height - 1:
                        offset_height = height - crop_size
                    # 裁成三通道
                    cropped = img[offset_width: offset_width + crop_size, offset_height: offset_height + crop_size, :]
                    # 保存为 原文件名_裁剪行号_裁剪列号.tif
                    io.imsave(os.path.join(save_path, '{}_{}_{}'.format(file_name, i, j) + extension), cropped)
                    p += 1
                    print('Crop {} image: {}_{}_{}'.format(p, file_name, i, j) + extension)
            print('Success crop {} images.'.format(p))
        else:
            print('Error: img.shape = {}'.format(img.shape))
    
    # 重叠裁剪jpg或png图片(带重叠率)
    @staticmethod
    def crop_image_overlap(file_path, save_path, crop_size, overlap_rate):
        '''
        :param file_path: 原图路径
        :param save_path: 保存路径
        :param crop_size: 裁剪尺寸
        :param overlap_rate: 重叠率
        :return: 裁剪结果, 文件名: 原始文件名_行号_列号.jpg or .png
        '''
        # 获取文件名
        file_dir, file_name_ex = os.path.split(file_path)
        file_name, extension = os.path.splitext(file_name_ex)
        # 保存路径存在
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        # 读取图片
        try:
            img = io.imread(file_path)
        except:
            print('Error: {} not exist or image format is wrong.'.format(file_path))
            return

        # 重叠率在0-1之间
        if overlap_rate < 0 or overlap_rate > 1:
            print('Error: overlap_rate must between 0 and 1.')
            return

        # 图片必须大于裁剪尺寸，必须为3通道
        if len(img.shape) == 3:
            width, height, channel= img.shape
            print(img.shape)
            if width < crop_size or height < crop_size:
                print('Error: width or height < crop_size.')
                return
            # 裁剪
            p = 0
            for i in np.arange(0, width // crop_size, 1 - overlap_rate):
                for j in np.arange(0, height // crop_size, 1 - overlap_rate):
                    if int((i + 1)*crop_size) > width or int((j + 1)*crop_size) > height:
                        continue
                    # 裁剪区域
                    cropped = img[int(i*crop_size): int((i + 1)*crop_size), int(j*crop_size): int((j + 1)*crop_size), :]
                    # 保存为 原文件名_裁剪行号_裁剪列号.tif
                    io.imsave(os.path.join(save_path, '{}_{}_{}_r{}'.format(file_name, i, j, overlap_rate) + extension), cropped)
                    p += 1
            print('Success crop {} images.'.format(p))
        else:
            print('Error: img.shape = {}'.format(img.shape))
    
    # 裁剪tif图片, 参数is_supplement表示是否补充切割
    @staticmethod
    def crop_tif(file_path, save_path, crop_size, is_supplement=False):
        '''
        :param file_path: 待切割tif文件路径
        :param save_path: 切割后保存路径
        :param crop_size: 切割尺寸
        :param is_supplement: 是否补全切割
        :return: 切割结果, 文件名: 原始文件名_行号_列号.tif
        '''
        # 获取文件名
        file_dir, file_name_ex = os.path.split(file_path)
        file_name, extension = os.path.splitext(file_name_ex)
        # 保存路径存在
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        # 读取tif
        try:
            dataset = gdal.Open(file_path)
        except:
            print('Error: {} not exist or image format is wrong.'.format(file_path))
            return
        # 获取tif的基本信息
        width = dataset.RasterXSize
        height = dataset.RasterYSize
        channel = dataset.RasterCount
        # 图片必须大于裁剪尺寸
        if width < crop_size or height < crop_size:
            print('Error: width or height < crop_size.')
            return
        ori_transform = dataset.GetGeoTransform()
        proj = dataset.GetProjection()
        top_left_x = ori_transform[0]  # 左上角x坐标
        top_left_y = ori_transform[3]  # 左上角y坐标
        w_e_pixel_resolution = ori_transform[1]  # 东西方向像素分辨率
        n_s_pixel_resolution = ori_transform[5]  # 南北方向像素分辨率
        pcs = osr.SpatialReference()
        pcs.ImportFromWkt(proj)

        # 读取原图中的每个波段，通道数从1开始
        in_band = []
        # 单波段Tif需要先进行色域转换，位深转为1位
        if channel == 1:
            img = dataset.GetRasterBand(1).ReadAsArray()
            img = np.array(img, dtype=np.uint8)
            max_color = np.max(img)
            img = np.where(img == max_color, 0, 255)
            in_band.append(img)
        else:
            for i in range(channel):
                in_band.append(dataset.GetRasterBand(i + 1))
        # 是否需要最后不足补充，进行反向裁剪
        wb = False
        hb = False
        num_width = int(width/crop_size)
        num_height = int(height/crop_size)
        if is_supplement:
            # 判断是否能完美切割
            if width % crop_size != 0:
                num_width += 1
                wb = True
            if height % crop_size != 0:
                num_height += 1
                hb = True
        # 裁剪
        print('---------------------------------------------------------------------')
        print('Start crop file: {}'.format(file_path))
        print('width: {}, height: {}, channel: {}'.format(width, height, channel))
        print('Projection coordinate system: ', pcs.GetAttrValue('projcs'))
        print('Geospatial coordinate system: ', pcs.GetAttrValue('geogcs'))
        print('---------------------------------------------------------------------')
        # 创建用于记录坐标投影的txt文件中
        f = open(os.path.join(save_path, '{}_info.txt'.format(file_name)), 'w')
        count = 0
        for i in range(num_width):
            offset_x = crop_size * i
            if i == num_width - 1 and wb:
                offset_x = width - crop_size
            for j in range(num_height):
                count += 1
                offset_y = crop_size * j
                if j == num_height - 1 and hb:
                    offset_y = height - crop_size
                # 读取裁剪区域
                out_band = []
                # 单波段Tif单独处理
                if channel == 1:
                    out_band.append(in_band[0][offset_y: offset_y + crop_size, offset_x: offset_x + crop_size])
                else:
                    for k in range(channel):
                        out_band.append(in_band[k].ReadAsArray(offset_x, offset_y, crop_size, crop_size))
                # 保存为 save_path/原文件名_裁剪行号_裁剪列号.tif
                gtif_driver = gdal.GetDriverByName('GTiff')
                output_name = os.path.join(save_path, '{}_{}_{}'.format(file_name, j, i) + extension)
                if channel == 1:
                    out_data = gtif_driver.Create(output_name, crop_size, crop_size, 1, gdal.GDT_Byte)
                else:
                    out_data = gtif_driver.Create(output_name, crop_size, crop_size, channel, in_band[0].DataType)
                print("create new tif file succeed, file name is {}".format(output_name))
                # 设置裁剪区域的地理参考
                top_left_x1 = top_left_x + offset_x * w_e_pixel_resolution
                top_left_y1 = top_left_y + offset_y * n_s_pixel_resolution
                new_transform = (top_left_x1, ori_transform[1], ori_transform[2], top_left_y1, ori_transform[4], ori_transform[5])
                out_data.SetGeoTransform(new_transform)
                # 设置SRS属性（投影信息）
                out_data.SetProjection(proj)
                # 将投影信息和坐标信息写入到txt文件中, 格式为“文件名_投影信息_地理参考六参数”
                f.write('{}*_&{}*_&{}*_&{}*_&{}*_&{}*_&{}*_&{}'.format(output_name, proj, top_left_x1, ori_transform[1], ori_transform[2], top_left_y1, ori_transform[4], ori_transform[5]))
                f.write('\n')
                # 写入裁剪区域
                for k in range(channel):
                    out_data.GetRasterBand(k + 1).WriteArray(out_band[k])
                # 将缓存写入磁盘，直接保存
                out_data.FlushCache()
                del out_data
        f.close()
        print('Success crop {} images.'.format(count))

    # 合并图片jpg或png(只能用于没有重叠切割的图片，经过补全切割或重叠率的图片不可用)
    @staticmethod
    def merge_image(file_path, save_path):
        '''
        :param file_path: 待合并图片所在文件夹(文件名格式: 原文件名_裁剪行号_裁剪列号.jpg)
        :param save_path: 合并后图片保存路径
        :return: merge image
        '''
        # 获取文件夹下所有图片
        file_list = [os.path.join(file_path, file) for file in os.listdir(file_path) if file.endswith('.jpg') or file.endswith('.png')] 
        # 文件名按从左到右从上到下排序
        file_list.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
        file_list.sort(key=lambda x: int(x.split('_')[-2]))
        # 获取所有的文件名
        file_name_list = []
        for file in file_list:
            if '/' in file:
                file_name_list.append(file.split('/')[-1].split('.')[0])
            else:
                file_name_list.append(file.split('\\')[-1].split('.')[0])
        # 获取图片的宽高及原文件名
        img = Image.open(os.path.join(file_path, file_list[0]))
        width, height = img.size
        ori_name = file_name_list[0][::-1].split('_', 2)[-1][::-1]
        # 获取最大行列号
        width_num = 0
        height_num = 0
        for filename in file_name_list:
            height_num = max(height_num, int(filename.split('_')[-2]))
            width_num = max(width_num, int(filename.split('_')[-1]))
        # 获取合并图片的宽高
        new_height = (height_num + 1) * height
        new_width = (width_num + 1) * width
        # 创建新图片
        new_img = Image.new(img.mode, (new_width, new_height))
        # 拼接图片
        for i in range(height_num + 1):
            for j in range(width_num + 1):
                try:
                    img = Image.open(os.path.join(file_path, '{}_{}_{}.jpg'.format(ori_name, i, j)))
                except:
                    print('No image: {}_{}_{}.jpg'.format(ori_name, i, j))
                    continue
                new_img.paste(img, (j * width, i * height))
        # 保存图片
        new_img.save(save_path)
        print('Success merge image. save path is {}'.format(save_path))


    # 合并tif
    @staticmethod
    def merge_tif(file_path, save_path):
        '''
        :param file_path: 待合并tif所在文件夹
        :param save_path: 合并后tif保存路径
        :return: merge tif
        '''
        # 获取文件夹下所有tif文件
        file_list = [os.path.join(file_path, file) for file in os.listdir(file_path) if file.endswith('.tif') or file.endswith('.tiff')]
        # 文件路径下没有tif文件
        if len(file_list) == 0:
            print('Error: No tif file in {}'.format(file_path))
            return
        # 创建vrt(虚拟文件)
        vrt = gdal.BuildVRT('temp.vrt', file_list)
        # vrt文件转为tif
        gdal.Translate(save_path, vrt)
        print('Success merge tif file. save path: {}'.format(save_path))
        vrt = None
    
    # 合并tif(带投影信息和地理坐标)
    @staticmethod
    def merge_tif_with_proj(file_path, save_path, txt_path):
        '''
        :param file_path: 待合并tif所在文件夹
        :param save_path: 合并后tif保存路径
        :return: merge tif
        '''
        # 获取文件夹下所有tif文件
        file_list = [os.path.join(file_path, file) for file in os.listdir(file_path) if file.endswith('.tif') or file.endswith('.tiff')]
        # 文件路径下没有tif文件
        if len(file_list) == 0:
            print('Error: No tif file in {}'.format(file_path))
            return
        # 读取txt文件
        with open(txt_path, 'r') as f:
            lines = f.readlines()
        if len(lines) != len(file_list):
            print('Error: txt file is not match tif file.')
            return
        # 获取每个文件对应的投影信息和地理坐标
        info = []
        for line in lines:
            file_name = line.split('*_&')[0]
            proj = line.split('*_&')[1]
            geo_0 = line.split('*_&')[2]
            geo_1 = line.split('*_&')[3]
            geo_2 = line.split('*_&')[4]
            geo_3 = line.split('*_&')[5]
            geo_4 = line.split('*_&')[6]
            geo_5 = line.split('*_&')[7]
            info.append([file_name, proj, geo_0, geo_1, geo_2, geo_3, geo_4, geo_5])

        # 将地理坐标和投影信息写入tif文件
        for i in range(len(file_list)):
            for j in range(len(info)):
                # 预测结果文件名与原始tif文件名一致
                if os.path.split(file_list[i])[-1] == os.path.split(info[j][0])[-1]:
                    ds = gdal.Open(file_list[i])
                    ds_with_coord = gdal.GetDriverByName('GTiff').CreateCopy(os.path.split(file_list[i])[0] + '/temp.tif', ds)
                    ds_with_coord.SetProjection(info[j][1])
                    ds_with_coord.SetGeoTransform([float(info[j][2]), float(info[j][3]), float(info[j][4]), float(info[j][5]), float(info[j][6]), float(info[j][7])])
                    ds_with_coord = None
                    ds = None
                    os.remove(file_list[i])
                    os.rename(os.path.split(file_list[i])[0] + '/temp.tif', file_list[i])
                    break
        
        # 创建vrt(虚拟文件)
        vrt = gdal.BuildVRT('temp.vrt', file_list)
        # vrt文件转为tif
        gdal.Translate(save_path, vrt)
        print('Success merge tif file. save path: {}'.format(save_path))
        vrt = None

    
    # 批量切割大杂烩
    @staticmethod
    def batch_cut(file_path, save_path, crop_size, is_supplement=True):
        '''
        :param file_path: 待切割文件夹
        :param save_path: 切割后文件保存路径
        :return: batch cut
        '''
        # 获取文件夹下所有文件
        file_list = [os.path.join(file_path, file) for file in os.listdir(file_path)]
        # 文件路径下没有文件
        if len(file_list) == 0:
            print('Error: No file in {}'.format(file_path))
            return
        # 保存路径存在
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        # 遍历文件
        for file in file_list:
            # 判断文件类型
            if file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.png'):
                # 切割图片
                GRID.crop_image(file, save_path, crop_size, is_supplement)
            elif file.endswith('.tif') or file.endswith('.tiff'):
                # 切割tif
                GRID.crop_tif(file, save_path, crop_size, is_supplement)
            else:
                print('Error: {} is not image or tif file.'.format(file))
                continue
        print('Success batch cut image or tif file.')
    
    
    # 栅格转矢量
    @staticmethod
    def raster_to_vector(file_path, save_path, txt_path = None):
        '''
        :param file_path: 待转换mask tif文件
        :param save_path: 转换后文件保存文件夹
        :txt_path: 坐标文件, 用于与Tif文件重叠
        :return: raster to vector
        '''
        # 读取tif文件
        ds = gdal.Open(file_path)
        if ds is None:
            print('Error: {} is not tif file.'.format(file_path))
            return

        # 获取tif文件的投影信息和地理坐标
        prj = osr.SpatialReference()
        prj.ImportFromWkt(ds.GetProjection())  # 读取栅格数据的投影信息

        # 如果有txt坐标文件，优先使用txt文件的投影信息和地理坐标
        if txt_path is not None:
            with open(txt_path, 'r') as f:
                lines = f.readlines()
            # 查找对应文件名的投影信息和地理坐标
            for line in lines:
                if line.split('*_&')[0] == file_path:
                    # 获取投影信息和地理坐标
                    prj = line.split('*_&')[1]
                    break
        # 获取tif文件的波段数据
        band_data = ds.GetRasterBand(1)
        # 保存为shp文件
        # 创建shp文件
        driver = ogr.GetDriverByName('ESRI Shapefile')
        # 若文件存在则删除
        if os.path.exists(save_path):
            driver.DeleteDataSource(save_path)
        ds_shp = driver.CreateDataSource(save_path)
        # 创建图层
        layer = ds_shp.CreateLayer(os.path.splitext(os.path.split(save_path)[1])[0], prj, ogr.wkbPolygon)
        # 创建属性表
        field_name = ogr.FieldDefn('value', ogr.OFTReal)
        layer.CreateField(field_name)
        gdal.Polygonize(band_data, None, layer, 0)
        # 释放资源
        ds_shp.SyncToDisk()
        ds_shp = None

        # 读取shp文件
        ds_result = ogr.Open(save_path.replace('.tif', '.shp'), gdal.GA_Update)
        # 删除shp属性表最后一行并保存
        # print(layer.GetFeatureCount())
        layer = ds_result.GetLayer(0)
        layer.DeleteFeature(layer.GetFeatureCount() - 1)
        # 释放资源
        ds_result.SyncToDisk()
        ds_result = None
        
        print('Success raster to vector. save path: {}'.format(save_path.replace('.tif', '.shp')))

    # 矢量转栅格
    @staticmethod
    def vector_to_raster(shp_file_path, save_path, tif_file_path, output_channel = 'single'):
        '''
        :param shp_file_path: 待转换shp文件
        :param save_path: 转换后文件保存文件夹
        :param tif_file_path: 用于获取tif文件的图像大小范围
        :param output_format: 输出文件格式
        :param output_channel: 输出通道数
        :return: vector to raster
        '''
        # 读取shp文件
        shapefile = gpd.read_file(shp_file_path)
        if shapefile is None:
            raise Exception('Error: {} is not shp file.'.format(shp_file_path))
        # 读取tif文件
        ds = gdal.Open(tif_file_path)
        if ds is None:
            print('Error: {} is not tif file.'.format(tif_file_path))
            return
        # 获取tif文件的图像大小范围
        xsize = ds.RasterXSize
        ysize = ds.RasterYSize
        # 获取tif文件的投影信息和地理坐标
        prj = ds.GetProjection()
        geotransform = ds.GetGeoTransform()
        afn = Affine.from_gdal(*geotransform)
        # 通道数
        if output_channel == 'single':
            channel = 1
        elif output_channel == 'multi':
            channel = 3
        else:
            raise Exception('Error: output_channel must be single or multi.')
        
        meta = {'driver': 'GTiff',
                'height': ysize,
                'width': xsize,
                'count': channel,
                'dtype': 'uint8',
                'crs': prj,
                'transform': afn,
                'nodata': 2}    # nodata = 2, 用于区分背景和边界，不占用背景像素值0
        
        # 单通道则每块矢量图斑内部填充为1，多通道则每块矢量图斑内部填充为[255, 255, 255]
        if output_channel == 'single':
            fill_value = 1
        elif output_channel == 'multi':
            fill_value = 255
        field_val = [fill_value] * len(shapefile.geometry)

        # 无论是什么格式的影像，先作为tif处理
        if save_path.endswith('.tif') or save_path.endswith('.tiff'):
            save_temp_path = save_path
        elif save_path.endswith('.jpg') or save_path.endswith('.jpeg') or save_path.endswith('.png'):
            save_temp_path = save_path.replace(save_path.split('.')[-1], 'tif')
        else:
            raise Exception('Error: {} is not support format.'.format(save_path.split('.')[-1]))
        
        # 如果保存文件存在则先删除
        if os.path.exists(save_path):
            os.remove(save_path)
        if os.path.exists(save_temp_path):
            os.remove(save_temp_path)
        # 创建tif文件，背景填充为0
        with rio.open(save_temp_path, 'w', **meta) as out:
            if channel == 1:
                out.write(np.zeros((ysize, xsize), dtype=np.uint8), 1)
            elif channel == 3:
                out.write(np.zeros((3, ysize, xsize), dtype=np.uint8), [1, 2, 3])
        # 读取tif文件
        with rio.open(save_temp_path, 'r+') as out:
            for i in range(channel):
                out_arr = out.read(i + 1)
                # 读取shp文件
                shapes = ((geom, value) for geom, value in zip(shapefile.geometry, field_val))
                burned = features.rasterize(shapes=shapes, fill=0, out=out_arr, transform=out.transform)
                out.write_band(i + 1, burned)
        
        # 如果为多通道则直接保存
        if channel == 3:
            if save_path.endswith('.jpg') or save_path.endswith('.jpeg'):
                os.system('gdal_translate -of JPEG {} {}'.format(save_temp_path, save_path))
                os.remove(save_temp_path)
            elif save_path.endswith('.png'):
                os.system('gdal_translate -of PNG {} {}'.format(save_temp_path, save_path))
                os.remove(save_temp_path)
            print('Success vector to raster. save path: {}'.format(save_path))
            return
        
        # 单通道处理
        # 设置tif文件位深度为1位
        # 先转灰度图
        img_l = Image.open(save_temp_path).convert('L')
        # 再转二值图
        img_b = img_l.point(lambda x: 0 if x < 1 else 1, '1')
        # 保存
        img_b.save(save_temp_path)
        
        # 如果为保存为tif，转位深会丢失投影信息和地理坐标，所以需要重新设置
        # 设置投影信息和地理坐标
        ds = gdal.Open(save_temp_path, gdal.GA_Update)
        ds.SetProjection(prj)
        ds.SetGeoTransform(geotransform)
        # 释放资源
        ds = None
            
        if save_path.endswith('.jpg') or save_path.endswith('.jpeg'):
            os.system('gdal_translate -of JPEG {} {}'.format(save_temp_path, save_path))
            os.remove(save_temp_path)
        elif save_path.endswith('.png'):
            os.system('gdal_translate -of PNG {} {}'.format(save_temp_path, save_path))
            os.remove(save_temp_path)
        
        print('Success vector to raster. save path: {}'.format(save_path))
        
        
        
    
    # 生成坐标文件
    @staticmethod
    def generate_txt(file_path, save_path):
        '''
        :param file_path: 待生成坐标文件的tif文件
        :param save_path: 生成坐标文件保存路径
        :return: generate txt
        '''
        # 读取tif文件
        ds = gdal.Open(file_path)
        if ds is None:
            print('Error: {} is not tif file.'.format(file_path))
            return
        # 获取tif文件的投影信息和地理坐标
        prj = osr.SpatialReference()
        prj.ImportFromWkt(ds.GetProjection())  # 读取栅格数据的投影信息
        geo = ds.GetGeoTransform()
        # 生成坐标文件
        with open(save_path, 'w') as f:
            f.write('{}*_&{}*_&{}*_&{}*_&{}*_&{}*_&{}*_&{}'.format(file_path, prj, geo[0], geo[1], geo[2], geo[3], geo[4], geo[5]))
            f.write('\n')
        print('Success generate txt. save path: {}'.format(save_path))

                

if __name__ == '__main__':
    # file_path = r'C:\Users\69452\Desktop\mon\9.30日晚之前\data\建筑物_h1182_w349_F42_dataset7.jpg'
    # file_path = r'C:\Users\69452\Desktop\10.7日任务\裁剪测试数据\band3.tif'
    # file_path = r'C:\Users\69452\Desktop\mon\9_30日晚之前\data\mosaic_output.tif'
    # save_path = r'C:\Users\69452\Desktop\mon\9_30日晚之前\data\crop2'
    # file_path = r'C:\Users\69452\Desktop\mon\9_30日晚之前\data\crop2'
    # save_path = r'C:\Users\69452\Desktop\mon\9.30日晚之前\data\merge_gdal.tif'
    # save_path = r'C:\Users\69452\Desktop\mon\9_30日晚之前\data\merge_crop2.tif'
    # file_path = r'C:\Users\69452\Desktop\mon\10.7日任务\裁剪测试数据'
    # save_path = r'C:\Users\69452\Desktop\mon\10.7日任务\cut\\'
    # file_path = r'C:\Users\69452\Desktop\mon\10.7日任务\cut_2'
    # save_path = r'C:\Users\69452\Desktop\mon\10.7日任务\merge_crop.tif'
    # file_path = r'D:\jsnu\AI RS\WHU\image_label_croped\test\2_0_3_mask.tif'
    # save_path = r'D:\jsnu\AI RS\WHU\image_label_croped\test'
    # file_path = r'C:\Users\69452\Desktop\mon\10.7日任务\band3result'
    # save_path = r'C:\Users\69452\Desktop\mon\10.7日任务\merge.tif'
    file_path = r'C:\Users\69452\Desktop\mon\10.13日晚之前\测试数据\shp\building.shp'
    save_path = r'C:\Users\69452\Desktop\mon\10.13日晚之前\测试数据\merge_shp_multi.tif'
    tif_path = r'C:\Users\69452\Desktop\mon\10.13日晚之前\测试数据\raster\band3.tif'


    crop_size = 1000

    # GRID.crop_tif(file_path, save_path, crop_size, is_supplement=True)
    # GRID.crop_image(file_path, save_path, crop_size, is_supplement=True)
    # GRID.merge_tif(file_path, save_path)
    # GRID.merge_tif_with_proj(file_path, save_path, r'C:\Users\69452\Desktop\mon\10.7日任务\cut_2\band4_info.txt')
    # GRID.batch_cut(file_path, save_path, crop_size, is_supplement=True)
    # GRID.generate_txt(r'D:\jsnu\AI RS\WHU\image_label_croped\test\2_0_3.tif', r'D:\jsnu\AI RS\WHU\image_label_croped\test\2_0_3.txt')
    # GRID.raster_to_vector(file_path, save_path, txt_path=r'D:\jsnu\AI RS\WHU\image_label_croped\test\2_0_3.txt')
    # GRID.merge_tif_with_proj(file_path, save_path, r'C:\Users\69452\Desktop\mon\10.7日任务\band3_info.txt')
    # GRID.raster_to_vector(save_path, save_path.replace('.tif', '.shp'))
    
    '''     两种模式：多通道和单通道    多波段 RGB分为（0,0,0）（255,255,255）  单波段，1bit，只含值0和1 (JPG无法调成1位深度，只能调成8位深度，其余可行)'''
    '''     不同后缀名更改保存文件的后缀名即可    '''
    GRID.vector_to_raster(file_path, save_path, tif_path, 'multi')
    # GRID.vector_to_raster(file_path, save_path, tif_path, 'single')

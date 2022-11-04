#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   test.py
@Time    :   2022/10/08 22:05:02
@Author  :   StrideH
@Desc    :   crop .tif file with different channels
'''
import os
from osgeo import gdal, osr
import numpy as np

def crop_tif(file_path, save_path, crop_size, is_supplement=False, crop_channel = 'all'):
    '''
    :param file_path: 待切割tif文件路径
    :param save_path: 切割后保存路径
    :param crop_size: 切割尺寸
    :param is_supplement: 是否补全切割
    :param crop_model: 切割模式, all为全部通道切割, RGB为RGB通道切割, R为R通道切割, G为G通道切割, B为B通道切割, NIR为NIR通道切割
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
    if channel == 1:
        crop_channel == 'all'
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
        if crop_channel == 'all':
            for i in range(channel):
                in_band.append(dataset.GetRasterBand(i + 1))
        elif crop_channel == 'RGB':
            for i in range(3):
                in_band.append(dataset.GetRasterBand(i + 1))
        elif crop_channel == 'R':
            in_band.append(dataset.GetRasterBand(1))
        elif crop_channel == 'G':
            in_band.append(dataset.GetRasterBand(2))
        elif crop_channel == 'B':
            in_band.append(dataset.GetRasterBand(3))
        elif crop_channel == 'NIR' and channel == 4:
            in_band.append(dataset.GetRasterBand(4))
        else:
            print('Error: crop_channel is wrong.')
            return
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
                for k in range(len(in_band)):
                    out_band.append(in_band[k].ReadAsArray(offset_x, offset_y, crop_size, crop_size))
            # 保存为 save_path/原文件名_裁剪行号_裁剪列号.tif
            gtif_driver = gdal.GetDriverByName('GTiff')
            output_name = os.path.join(save_path, '{}_{}_{}'.format(file_name, j, i) + extension)
            if channel == 1:
                out_data = gtif_driver.Create(output_name, crop_size, crop_size, 1, gdal.GDT_Byte)
            else:
                out_data = gtif_driver.Create(output_name, crop_size, crop_size, len(out_band), in_band[0].DataType)
            print("create new tif file succeed, file name is {}".format(output_name))
            # 设置裁剪区域的地理参考
            top_left_x1 = top_left_x + offset_x * w_e_pixel_resolution
            top_left_y1 = top_left_y + offset_y * n_s_pixel_resolution
            new_transform = (top_left_x1, ori_transform[1], ori_transform[2], top_left_y1, ori_transform[4], ori_transform[5])
            out_data.SetGeoTransform(new_transform)
            # 设置SRS属性（投影信息）
            out_data.SetProjection(proj)
            # 构建金字塔
            # out_data.BuildOverviews("NEAREST", [2, 4, 8, 16, 32, 64])
            # 将投影信息和坐标信息写入到txt文件中, 格式为“文件名_投影信息_地理参考六参数”
            f.write('{}*_&{}*_&{}*_&{}*_&{}*_&{}*_&{}*_&{}'.format(output_name, proj, top_left_x1, ori_transform[1], ori_transform[2], top_left_y1, ori_transform[4], ori_transform[5]))
            f.write('\n')
            # 写入裁剪区域
            for k in range(len(out_band)):
                out_data.GetRasterBand(k + 1).WriteArray(out_band[k])
            # 将缓存写入磁盘，直接保存
            out_data.FlushCache()
            del out_data
    f.close()
    print('Success crop {} images.'.format(count))

if __name__ == '__main__':
    # 文件路径
    file_path = r'C:\Users\69452\Desktop\mon\10.7日任务\裁剪测试数据\band3.tif'
    # 保存路径
    save_path = r'C:\Users\69452\Desktop\mon\10.7日任务\裁剪结果'
    # 裁剪大小
    crop_size = 512
    # 是否需要最后不足补充，进行反向裁剪
    is_supplement = True
    # crop_channel 六种裁剪通道方式
    # all 裁剪全部通道
    # RGB 裁剪RGB三通道
    # R 裁剪R通道
    # G 裁剪G通道
    # B 裁剪B通道
    # NIR 裁剪NIR通道
    crop_tif(file_path, save_path, crop_size, is_supplement, crop_channel='all')
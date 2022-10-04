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
from osgeo import gdal, osr
import numpy as np
from PIL import Image

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

        # 设置对应tif文件的投影信息和地理坐标
        for i in range(len(file_list)):
            ds = gdal.Open(file_list[i], gdal.GA_Update)
            # 找到对应文件名的投影信息和地理坐标
            for j in range(len(info)):
                if info[j][0] == file_list[i]:
                    ds.SetProjection(info[j][1])
                    ds.SetGeoTransform((float(info[j][2]), float(info[j][3]), float(info[j][4]), float(info[j][5]), float(info[j][6]), float(info[j][7])))
                    break
            ds = None

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
                GRID().crop_image(file, save_path, crop_size, is_supplement)
            elif file.endswith('.tif') or file.endswith('.tiff'):
                # 切割tif
                GRID().crop_tif(file, save_path, crop_size, is_supplement)
            else:
                print('Error: {} is not image or tif file.'.format(file))
                continue
        print('Success batch cut image or tif file.')

                

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
    file_path = r'C:\Users\69452\Desktop\mon\10.7日任务\cut_2'
    save_path = r'C:\Users\69452\Desktop\mon\10.7日任务\merge_crop.tif'

    crop_size = 1000

    # GRID.crop_tif(file_path, save_path, crop_size, is_supplement=True)
    # GRID.crop_image(file_path, save_path, crop_size, is_supplement=True)
    # GRID.merge_tif(file_path, save_path)
    # GRID.merge_tif_with_proj(file_path, save_path, r'C:\Users\69452\Desktop\mon\10.7日任务\cut_2\band4_info.txt')
    GRID.batch_cut(file_path, save_path, crop_size, is_supplement=True)
import ocr
import axis
import head
import sys
import draw_bottomline
import subprocess
import os
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import math


def save_predict_as_csv(x_label, y_label, data, save_path):
    df = pd.DataFrame(data, columns=x_label, index=y_label)
    df.to_csv(save_path)


def main(filename):
    chart_name = filename + '.png'
    folder_path = os.path.join(os.path.abspath(sys.path[0]), "../data/")
    chart_path = folder_path + chart_name
    craft_model_path = os.path.join(
        os.path.abspath(sys.path[0]), "../craft_mlt_25k.pth")
    subprocess.call(["python", "CRAFT-pytorch/test.py",
                     "--test_folder=" + folder_path,
                     "--trained_model=" + craft_model_path,
                     "--file_name=" + chart_name])
    box_path = os.path.join(os.path.abspath(
        sys.path[0]), '../result/res_' + filename + '.txt')

    predict_path = os.path.join(os.path.abspath(
        sys.path[0]), '../result/pred_' + filename + '.csv')

    axis_points, degrees = axis.axis(folder_path, chart_name)
    axis_list = [x[0] + x[1] for x in axis_points]

    result, dbox = ocr.tick_to_value(chart_path, box_path, axis_list)

    zaxis = result[0]
    tick_val = 0.0
    tick_px = float(dbox[0])
    delta_dic = {}
    for i in range(len(zaxis)-1):
        try:
            z1 = zaxis[i+1]
            z0 = zaxis[i]
            if z1 is not None and z0 is not None:
                tick_val = float(z1 - z0)
                delta_dic.setdefault(tick_val, 0)
                delta_dic[tick_val] += 1
        except:
            continue

    maxcnt = 0
    for val, cnt in delta_dic.items():
        if cnt > maxcnt:
            tick_val = val
            maxcnt = cnt

    template_coordinate = head.run(filename)
    bottom_line = draw_bottomline.main(filename, axis_points, degrees, dbox)

    x_len = len(bottom_line)
    y_len = -1
    for temp_coord in template_coordinate:
        y_len = max(y_len, len(temp_coord[0]))

    xaxis = []
    for i in range(x_len):
        if i < len(result[1]):
            xaxis.append(result[1][i])
        else:
            xaxis.append("miss")

    yaxis = []
    for i in range(y_len):
        if i < len(result[2]):
            yaxis.append(result[2][i])
        else:
            yaxis.append("miss")

    coord_map = np.zeros((x_len, y_len, 2))
    data_map = np.zeros((x_len, y_len))

    min_delta = 1000
    for i, line in enumerate(bottom_line):
        x_list = template_coordinate[i][0]
        y_list = template_coordinate[i][1]
        points = list(zip(x_list, y_list))

        min_delta_c, _ = find_delta(points, line)
        min_delta = min(min_delta, min_delta_c)

    for i, line in enumerate(bottom_line):
        x_list = template_coordinate[i][0]
        y_list = template_coordinate[i][1]
        points = list(zip(x_list, y_list))

        len_points = len(points)
        jd = 0
        for j, point in enumerate(points):
            if i >= x_len or (j+jd) >= y_len:
                continue

            h_px, yp0 = line.height(point)
            h_val = h_px * tick_val / tick_px
            coord_map[i, j+jd] = point
            data_map[i, j+jd] = h_val

            if j < len_points - 1:
                x0, y0 = point
                x1, y1 = points[j+1]
                _, yp1 = line.height(points[j+1])

                dist = np.sqrt((x1-x0)**2+(yp1-yp0)**2)
                n = int(round(dist / min_delta))

                for k in range(n-1):
                    if (j+jd+k+1) >= y_len:
                        continue
                    coord_map[i, j+jd+k+1, :] = None
                    data_map[i, j+jd+k+1] = math.nan
                jd += n - 1

        left = y_len - (len_points + jd)
        if left > 0:
            data_map[i, len_points + jd:] = math.nan

    print(data_map)
    save_predict_as_csv(xaxis, reversed(yaxis), data_map.T, predict_path)
    # draw_values(chart_path, data_map, coord_map)


def find_delta(points, line):
    # boxes should be sorted by ascending order

    min_delta = 1000  # TODO: change to static max variable
    min_dx = 0
    min_dy = 0
    for i in range(len(points)-1):
        x0, y0 = points[i]
        x1, y1 = points[i+1]
        _, yp0 = line.height(points[i])
        _, yp1 = line.height(points[i+1])
        dx = x1 - x0
        dy = yp1 - yp0
        delta = np.sqrt(dx**2 + dy**2)
        if delta < min_delta:
            min_delta = delta
            min_dx = dx
            min_dy = dy

    delta_pos = np.array([min_dx, min_dy])
    return min_delta, delta_pos


def draw_values(chart_path, data_map, coord_map):
    img = Image.open(chart_path).convert('RGB')
    draw = ImageDraw.Draw(img)

    ih, jh = data_map.shape
    for i in range(ih):
        for j in range(jh):
            x, y = coord_map[i, j]
            h_val = data_map[i, j]
            if not math.isnan(h_val):
                draw.text((x-15, y-20), str(round(h_val)), fill=(0, 0, 0))
    plt.imshow(img)
    plt.show()


if __name__ == "__main__":
    filename = sys.argv[1]  # ex) Matlab8
    main(filename)

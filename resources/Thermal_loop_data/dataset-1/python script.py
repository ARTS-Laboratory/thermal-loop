# -*- coding: utf-8 -*-
"""
Created on Tue Jul 15 10:48:53 2025

@author: localuser
"""


import os
import numpy as np
import matplotlib.pyplot as plt

file_path = os.path.expanduser('~/Desktop/Thermocouple data/0.5_gal_min_test.lvm')
data = np.loadtxt(file_path, skiprows=16500,)
#to use a specific number of rows use max_rows=x, dont forget to also skip 23 lines
num_rows = data.shape[0]
time = np.arange(num_rows) * 1/3600
#if the data is 4 times a second multiple 3600 by 4 etc.

plt.plot(time, data[:, 1], label='Sensor 1', color='blue', linewidth=0.5)
plt.plot(time, data[:, 2], label='Sensor 2', color='orange', linewidth=0.5)

plt.xlabel('Time (hours)')
plt.ylabel('Temperature (^oC)')
plt.title('Temperature Over Time')
plt.legend()
plt.grid(True)
plt.tight_layout()

output_path = os.path.expanduser("~/Desktop/Thermocouple data/temperature_plot.pdf")

plt.savefig(output_path, dpi=600, bbox_inches='tight', facecolor='white')


plt.show()


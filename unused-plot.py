#!/bin/python2

import matplotlib.pyplot as plt
import sys
import re
import math

def f(wc, wp, yc, d):
    return math.floor((yc-d)/(wp-wc)) + 1


x = []
y = []

wp = 10.0
wc = 9.0
yc = 10.0

step = wp / 200
xcur = 0.0

for i in range(200):
    x.append(xcur)
    xcur += step

for xp in x:
    y.append(f(wc, wp, yc, xp))

plt.plot(x, y)
plt.show()

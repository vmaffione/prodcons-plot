#!/bin/python2

import matplotlib.pyplot as plt
import sys
import re


x = []
y = []
while 1:
    l = sys.stdin.readline()
    if l == '':
        break
    m = re.match(r'([^ ]+) +([^ ]+)', l);
    if m:
        x.append(float(m.group(1)))
        y.append(float(m.group(2)))

plt.plot(x, y)
plt.show()

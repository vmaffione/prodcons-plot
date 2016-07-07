#!/usr/bin/env python

import argparse
import re
import math


class ProdConsState:
    def __init__(self, args):
        self.args = args

        self.t = 0.0

        self.qlen = 0
        self.pkt_prod = 0
        self.pkt_cons = 0
        self.prod_events = []
        self.cons_events = []

        self.future = []

        self.pkts = 0
        self.prod_sleeps = 0
        self.cons_sleeps = 0
        self.prod_kicks = 0
        self.cons_kicks = 0
        self.cons_active = False
        self.prod_active = True

    def dump(self):
        from matplotlib import pyplot as plt

        xunit = min(self.args.wp, self.args.wc)

        max_time = max(self.prod_events[-1][0] + self.prod_events[-1][2],
                       self.cons_events[-1][0] + self.cons_events[-1][2])
        fig = plt.figure()
        ax = plt.axes(xlim=(0, self.args.xunits * xunit), ylim=(0, 100))

        y = 95
        ofs = 0
        size = 2
        for ev in self.prod_events:
            if ev[0] + ev[2] - ofs > self.args.xunits * xunit:
                ofs += self.args.xunits * xunit
                y -= 10
            ev = (ev[0] - ofs, ev[1], ev[2])
            if ev[1] == 'z':
                line = plt.Line2D((ev[0], ev[0] + ev[2]), (y + size/2, y + size/2), lw=2.5)
                plt.gca().add_line(line)
            elif ev[1] == 'n':
                poly = plt.Polygon([[ev[0], y], [ev[0], y + size], [ev[0] + ev[2], y]], color = 'y')
                plt.gca().add_patch(poly)
            elif ev[1] == 's':
                poly = plt.Polygon([[ev[0], y], [ev[0] + ev[2], y], [ev[0] + ev[2], y + size]], color = 'b')
                plt.gca().add_patch(poly)
            else:
                rectangle = plt.Rectangle((ev[0], y), ev[2], size, fc='r')
                plt.gca().add_patch(rectangle)

        y = 92
        ofs = 0
        for ev in self.cons_events:
            if ev[0] + ev[2] - ofs > self.args.xunits * xunit:
                ofs += self.args.xunits * xunit
                y -= 10
            ev = (ev[0] - ofs, ev[1], ev[2])
            if ev[1] == 'z':
                line = plt.Line2D((ev[0], ev[0] + ev[2]), (y + size/2, y + size/2), lw=2.5)
                plt.gca().add_line(line)
            elif ev[1] == 'n':
                poly = plt.Polygon([[ev[0], y], [ev[0], y + size], [ev[0] + ev[2], y + size]], color = 'y')
                plt.gca().add_patch(poly)
            elif ev[1] == 's':
                poly = plt.Polygon([[ev[0], y + size], [ev[0] + ev[2], y + size], [ev[0] + ev[2], y]], color = 'b')
                plt.gca().add_patch(poly)
            else:
                rectangle = plt.Rectangle((ev[0], y), ev[2], size, fc='g')
                plt.gca().add_patch(rectangle)

        plt.show()

    def future_push(self, t, cb):
        for i in range(len(self.future)):
            if t < self.future[i][0] or (t == self.future[i][0] and \
                    (cb == ProdConsState.prod_sleep_back or \
                     cb == ProdConsState.cons_sleep_back)):
                self.future.insert(i, (t, cb))
                return
        self.future.append((t, cb))

    # Simulation routines for sleep
    def prod_sleep_front(self):
        if self.qlen < self.args.l:
            self.prod_events.append((self.t, self.pkt_prod, self.args.wp))
            self.future_push(self.t + self.args.wp, ProdConsState.prod_sleep_back)
        else:
            self.prod_events.append((self.t, 'z', self.args.yp))
            self.future_push(self.t + self.args.yp, ProdConsState.prod_sleep_front)
            self.prod_sleeps += 1

    def prod_sleep_back(self):
        self.qlen += 1
        self.pkt_prod += 1
        self.future_push(self.t, ProdConsState.prod_sleep_front)

    def cons_sleep_front(self):
        if self.qlen > 0:
            self.cons_events.append((self.t, self.pkt_cons, self.args.wc))
            self.future_push(self.t + self.args.wc, ProdConsState.cons_sleep_back)
        else:
            self.cons_events.append((self.t, 'z', self.args.yc))
            self.future_push(self.t + self.args.yc, ProdConsState.cons_sleep_front)
            self.cons_sleeps += 1

    def cons_sleep_back(self):
        self.qlen -= 1
        self.pkt_cons += 1
        self.future_push(self.t, ProdConsState.cons_sleep_front)
        self.pkts += 1

    # Simulation routines for notifications
    def prod_ntfy_front(self):
        if self.qlen < self.args.l:
            self.prod_events.append((self.t, self.pkt_prod, self.args.wp))
            self.future_push(self.t + self.args.wp, ProdConsState.prod_ntfy_back)
        else:
            self.prod_active = False

    def prod_ntfy_back(self):
        self.qlen += 1
        self.pkt_prod += 1
        t_next = self.t
        if not self.cons_active:
            self.cons_active = True
            self.prod_events.append((self.t, 'n', self.args.np))
            self.cons_events.append((self.t + self.args.np, 's', self.args.sc))
            self.future_push(self.t + self.args.np + self.args.sc, ProdConsState.cons_ntfy_front)
            self.prod_kicks += 1
            t_next += self.args.np
        self.future_push(t_next, ProdConsState.prod_ntfy_front)

    def cons_ntfy_front(self):
        if self.qlen > 0:
            self.cons_events.append((self.t, self.pkt_cons, self.args.wc))
            self.future_push(self.t + self.args.wc, ProdConsState.cons_ntfy_back)
        else:
            self.cons_active = False

    def cons_ntfy_back(self):
        self.qlen -= 1
        self.pkt_cons += 1
        t_next = self.t
        self.pkts += 1
        if not self.prod_active:
            self.prod_active = True
            self.cons_events.append((self.t, 'n', self.args.nc))
            self.prod_events.append((self.t + self.args.nc, 's', self.args.sp))
            self.future_push(self.t + self.args.nc + self.args.sp, ProdConsState.prod_ntfy_front)
            self.cons_kicks += 1
            t_next += self.args.nc
        self.future_push(t_next, ProdConsState.cons_ntfy_front)


def simulate(args):
    pcs = ProdConsState(args)
    if args.algorithm == 'sleep':
        pcs.cons_events.append((0, 'z', args.cons_offset))
        pcs.future_push(0, ProdConsState.prod_sleep_front)
        pcs.future_push(args.cons_offset, ProdConsState.cons_sleep_front)
    elif args.algorithm == 'notify':
        pcs.future_push(0, ProdConsState.prod_ntfy_front)
        pcs.future_push(args.cons_offset, ProdConsState.cons_ntfy_front)

    cnt = 0
    while pcs.t <= args.time_max:
        if len(pcs.future) == 0:
            print('Out of events')
            break

        nxt = pcs.future.pop(0)
        pcs.t = nxt[0]
        if nxt[1] != None:
            nxt[1](pcs)

        cnt += 1

    return pcs


# Average per-packet time as computed by the producer
def t_prod(args, pcs):
    return args.wp + pcs.prod_sleeps * pcs.args.yp / pcs.pkts

# Average per-packet time as computed by the consumer
def t_cons(args, pcs):
    return args.wc + pcs.cons_sleeps * pcs.args.yc / pcs.pkts

# Upper bound for t_prod (t_cons), which happens when producer and
# consumer alternate
def t_bounds(args):
    if args.wc < args.wp:
        # Worst case: find minimum m | (Yp + (Wc-0)) + (m+1)wp > Wc L + m Wc
        m_worst = math.floor((args.wc * args.l - (args.yp + args.wc - 0) - args.wp)/(args.wp - args.wc)) + 1
        # Best case: find minimum m | (Wc) + (m+1)wp > Wc L + m Wc
        m_best = math.floor((args.wc * args.l - (args.wc) - args.wp)/(args.wp - args.wc)) + 1
    else:
        m_worst = math.floor((args.wp * args.l - (args.yc + args.wp - 0) - args.wc)/(args.wc - args.wp)) + 1
        m_best = math.floor((args.wp * args.l - (args.wp) - args.wc)/(args.wc - args.wp)) + 1

    if m_worst < 0:
        m_worst = 0
    if m_best < 0:
        m_best = 0

    # Who dominates the cycle ?
    alt_c = args.yc + args.l * args.wc
    alt_p = args.yp + args.l * args.wp
    if alt_c > alt_p:
        return ((args.yc + args.wc * (m_best + args.l)) / (m_best + args.l),
                (args.yc + args.wc * (m_worst + args.l)) / (m_worst + args.l))

    return ((args.yp + args.wp * (m_best + args.l)) / (m_best + args.l),
            (args.yp + args.wp * (m_worst + args.l)) / (m_worst + args.l))


def plot_depends(args, xs, t_vec, t_lower_vec, t_higher):
    from matplotlib import pyplot as plt
    plt.plot(xs, t_vec, 'o-', label='T_avg')
    plt.plot(xs, t_lower_vec, 'x-', label='T_lower')
    plt.plot(xs, t_higher_vec, 'x-', label='T_higher')
    plt.ylabel('Average per-packet time')
    plt.xlabel(args.depends)
    plt.title('How per-packet time depends from Yc/Yp')
    plt.grid(True)
    plt.legend(loc='upper left')
    plt.show()


description = "Python script to simulate sleeping prod/cons"
epilog = "2016 Vincenzo Maffione <v.maffione@gmail.com>"

argparser = argparse.ArgumentParser(description = description,
                                    epilog = epilog)
argparser.add_argument('-t', '--time-max',
                       help = "Max simulation time", type = int,
                       default = 195)
argparser.add_argument('--wp', help = "Wp", type = float, default = 2.0)
argparser.add_argument('--wc', help = "Wc", type = float, default = 1.0)
argparser.add_argument('--yp', help = "Yp", type = float, default = 3.0)
argparser.add_argument('--yc', help = "Yc", type = float, default = 5.0)
argparser.add_argument('--nc', help = "Nc", type = float, default = 3.0)
argparser.add_argument('--np', help = "Np", type = float, default = 4.5)
argparser.add_argument('--sc', help = "Sc", type = float, default = 2.1)
argparser.add_argument('--sp', help = "Sp", type = float, default = 7.1)
argparser.add_argument('-l', help = "Queue length", type = int, default = 3)
argparser.add_argument('--cons-offset', help = "Consumer start delay", type = float, default = 0.0)
argparser.add_argument('-q', '--quiet', help = "Compute only stats", action='store_true')
argparser.add_argument('--xunits', help = "Wp/Wc units per line in the plot", type = int, default = 180)

argparser.add_argument('-a', '--algorithm', help = "Algorithm",
                       choices=['sleep', 'notify'], default = 'sleep')

argparser.add_argument('--depends', help = "Dependency on", choices=['yp', 'yc'])
argparser.add_argument('--ymax', help = "max Yc or Yp when depends is specified",
                       type = int, default = 100)
argparser.add_argument('--points', help = "number of Yp or Yc points to test when depends is specified",
                       type = int, default = 150)

args = argparser.parse_args()


print('Parameters:')
print('    L  = %.2f' % args.l)
print('    Wp = %.2f' % args.wp)
print('    Wc = %.2f' % args.wc)
print('    Yp = %.2f' % args.yp)
print('    Yc = %.2f' % args.yc)
print('    Np = %.2f' % args.np)
print('    Nc = %.2f' % args.nc)
print('    Sp = %.2f' % args.sp)
print('    Sc = %.2f' % args.sc)
print('')

mx = max(args.l * args.wp, args.l * args.wc, args.yp, args.yc,
         args.np, args.nc, args.sp, args.sc)

if args.depends:

    # Check that simulation length is acceptable
    args.time_max = max(mx * 1000, args.time_max)
    print('Simulation length: %d' % args.time_max)

    # Start from the region where slow-party sleep happens
    if args.wc < args.wp:
        args.ymin = (args.l - 1) * args.wp - args.wc
    else:
        args.ymin = (args.l - 1) * args.wc - args.wp
    args.ymin -= 10 # just to show some more
    if args.ymin < 1:
        args.ymin = 1

    xs = []
    t_vec = []
    t_lower_vec = []
    t_higher_vec = []
    incr = (args.ymax - args.ymin)/args.points
    x = args.ymin
    while x < args.ymax:
        if args.depends == 'yp':
            args.yp = x
        else:
            args.yc = x
        pcs = simulate(args)
        t_vec.append(t_prod(args, pcs))
        bounds = t_bounds(args)
        t_lower_vec.append(bounds[0])
        t_higher_vec.append(bounds[1])
        xs.append(x)
        x += incr

    plot_depends(args, xs, t_vec, t_lower_vec, t_higher_vec)

else:
    args.time_max = max(mx * 100, args.time_max)

    pcs = simulate(args)

    if not args.quiet:
        pcs.dump()

    print('Packets processed %d' % pcs.pkts)
    print('Producer sleeps   %d' % pcs.prod_sleeps)
    print('Consumer sleeps   %d' % pcs.cons_sleeps)
    bounds = t_bounds(args)
    print('Time per packet %f (or %f), bounds (%f %f)' % \
            (t_prod(args, pcs), t_cons(args, pcs), bounds[0], bounds[1]))

#!/usr/bin/env python

import argparse
import math
import time
import re


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

    def dump(self, worst_case_pktidx):
        from matplotlib import pyplot as plt

        xunit = min(self.args.wp, self.args.wc)

        fig = plt.figure()
        ax = plt.axes(xlim=(0, self.args.xunits * xunit), ylim=(0, 100))

        y = 95
        ofs = 0
        size = 2
        for ev in self.prod_events:
            if ev[0] + ev[2] - ofs > self.args.xunits * xunit:
                ofs += self.args.xunits * xunit
                y -= 10
                if y < 0:
                    break
            ev = (ev[0] - ofs, ev[1], ev[2])
            if ev[1] == 'z':
                line = plt.Line2D((ev[0], ev[0] + ev[2]), (y + size/2, y + size/2), lw=4.5)
                plt.gca().add_line(line)
            elif ev[1] == 'n':
                poly = plt.Polygon([[ev[0], y], [ev[0], y + size], [ev[0] + ev[2], y]], color = 'y')
                plt.gca().add_patch(poly)
            elif ev[1] == 's':
                poly = plt.Polygon([[ev[0], y], [ev[0] + ev[2], y], [ev[0] + ev[2], y + size]], color = '#0080f0')
                plt.gca().add_patch(poly)
            else:
                color = 'k' if self.args.algorithm != 'poll' and ev[1] in worst_case_pktidx else 'g'
                rectangle = plt.Rectangle((ev[0], y), ev[2], size, fc=color)
                plt.gca().add_patch(rectangle)

        y = 92
        ofs = 0
        for ev in self.cons_events:
            if ev[0] + ev[2] - ofs > self.args.xunits * xunit:
                ofs += self.args.xunits * xunit
                y -= 10
                if y < 0:
                    break
            ev = (ev[0] - ofs, ev[1], ev[2])
            if ev[1] == 'z':
                line = plt.Line2D((ev[0], ev[0] + ev[2]), (y + size/2, y + size/2), lw=4.5)
                plt.gca().add_line(line)
            elif ev[1] == 'n':
                poly = plt.Polygon([[ev[0], y], [ev[0], y + size], [ev[0] + ev[2], y + size]], color = 'y')
                plt.gca().add_patch(poly)
            elif ev[1] == 's':
                poly = plt.Polygon([[ev[0], y + size], [ev[0] + ev[2], y + size], [ev[0] + ev[2], y]], color = '#0080f0')
                plt.gca().add_patch(poly)
            else:
                color = 'k' if self.args.algorithm != 'poll' and ev[1] in worst_case_pktidx else 'r'
                rectangle = plt.Rectangle((ev[0], y), ev[2], size, fc=color)
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
        if not self.cons_active and self.qlen >= self.args.kp:
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
        if not self.prod_active and self.args.l - self.qlen >= self.args.kc:
            self.prod_active = True
            self.cons_events.append((self.t, 'n', self.args.nc))
            self.prod_events.append((self.t + self.args.nc, 's', self.args.sp))
            self.future_push(self.t + self.args.nc + self.args.sp, ProdConsState.prod_ntfy_front)
            self.cons_kicks += 1
            t_next += self.args.nc
        self.future_push(t_next, ProdConsState.cons_ntfy_front)

    # Simulation routines for polling
    def prod_poll_front(self):
        if self.qlen < self.args.l:
            self.prod_events.append((self.t, self.pkt_prod, self.args.wp))
            self.future_push(self.t + self.args.wp, ProdConsState.prod_poll_back)
        else:
            self.prod_active = False

    def prod_poll_back(self):
        self.qlen += 1
        self.pkt_prod += 1
        self.future_push(self.t, ProdConsState.prod_poll_front)
        if not self.cons_active:
            self.cons_active = True
            self.future_push(self.t, ProdConsState.cons_poll_front)

    def cons_poll_front(self):
        if self.qlen > 0:
            self.cons_events.append((self.t, self.pkt_cons, self.args.wc))
            self.future_push(self.t + self.args.wc, ProdConsState.cons_poll_back)
        else:
            self.cons_active = False

    def cons_poll_back(self):
        self.qlen -= 1
        self.pkt_cons += 1
        self.future_push(self.t, ProdConsState.cons_poll_front)
        self.pkts += 1
        if not self.prod_active:
            self.prod_active = True
            self.future_push(self.t, ProdConsState.prod_poll_front)

    def future_print(self, fut):
        if fut[1] in [ProdConsState.prod_sleep_front,
                      ProdConsState.prod_ntfy_front,
                      ProdConsState.prod_poll_front,
                      ProdConsState.prod_sleep_back,
                      ProdConsState.prod_ntfy_back,
                      ProdConsState.prod_poll_back]:
            actor = 'P'
        else:
            actor = 'C'
        if fut[1] in [ProdConsState.prod_sleep_front,
                      ProdConsState.prod_ntfy_front,
                      ProdConsState.prod_poll_front,
                      ProdConsState.cons_sleep_front,
                      ProdConsState.cons_ntfy_front,
                      ProdConsState.cons_poll_front]:
            action = 'starts'
        else:
            action = 'ends'
        print('%s message %s at %s' % (actor, action, fut[0]))



def simulate(args):

    end = time.time() + args.time_max

    pcs = ProdConsState(args)
    if args.algorithm == 'sleep':
        pcs.cons_events.append((0, 'z', args.cons_offset))
        pcs.future_push(0, ProdConsState.prod_sleep_front)
        pcs.future_push(args.cons_offset, ProdConsState.cons_sleep_front)
    elif args.algorithm == 'notify':
        pcs.future_push(0, ProdConsState.prod_ntfy_front)
        pcs.future_push(args.cons_offset, ProdConsState.cons_ntfy_front)
    elif args.algorithm == 'poll':
        pcs.future_push(0, ProdConsState.prod_poll_front)
        pcs.future_push(args.cons_offset, ProdConsState.cons_poll_front)

    cnt = 0
    while time.time() < end:
        if len(pcs.future) == 0:
            print('Out of events')
            break

        nxt = pcs.future.pop(0)
        #pcs.future_print(nxt)
        pcs.t = nxt[0]
        if nxt[1] != None:
            nxt[1](pcs)

        cnt += 1

    return pcs


# Average per-packet time as computed by the producer
def t_prod(args, pcs):
    slc = 0 if pcs.pkts == 0 else pcs.prod_sleeps * pcs.args.yp / pcs.pkts
    return args.wp + slc


# Average per-packet time as computed by the consumer
def t_cons(args, pcs):
    slc = 0 if pcs.pkts == 0 else pcs.cons_sleeps * pcs.args.yc / pcs.pkts
    return args.wc + slc


# Average per-packet energy
def energy(args, pcs):
    if pcs.pkts == 0:
        return 0
    return ((args.wc + args.wp) * pcs.pkts + (pcs.cons_sleeps + pcs.prod_sleeps) * args.ye) / pcs.pkts


# Average batch
def batch(args, pcs):
    if pcs.prod_sleeps + pcs.cons_sleeps == 0:
        return 0
    return pcs.pkts / (pcs.prod_sleeps + pcs.cons_sleeps)


# Upper bound for t_prod (t_cons), which happens when producer and
# consumer alternate sleeping
def t_bounds(args):
    if args.wc < args.wp:
        m = math.floor(((args.l-1) * args.wc - args.wp)/(args.wp - args.wc)) + 1
        t_best = ((args.l + m) * args.wc + args.yc)/(args.l + m)
    else:
        m = math.floor(((args.l-1) * args.wp - args.wc)/(args.wc - args.wp)) + 1
        t_best = ((args.l + m) * args.wp + args.yp)/(args.l + m)

    return t_best, max(args.wp + args.yp/args.l, args.wc + args.yc/args.l)

# Valid only for L > 1 and Kp = 1
def latency_bound(args):
    if args.algorithm == 'sleep':
        if args.wc < args.wp and args.yc < (args.l-1) * args.wp - args.wc:
            # Fast consumer
            return 2 * args.wp + args.yc + args.wc

        elif args.wp < args.wc and args.yp < (args.l-1) * args.wc - args.wp:
            # Fast producer
            return args.wc * (args.l + 1)

        else:
            # Long sleeps
            h = math.floor((args.yc + args.l * args.wc - (args.l-1) * args.wp)/args.yp) + 1
            return 2 * args.wp + args.wc + args.yc + h * args.yp

    elif args.algorithm == 'notify':
        ss_lat = (max(args.wp, args.sc - (args.l - 2) * args.wp) + args.kc * args.wc +
                  args.nc + args.sp + args.wp + args.np + args.sc + args.wc)
        if args.wc < args.wp:
            fp_lat = 0
        else:
            m = math.floor((args.sp + (args.kc - 1) * args.wp)/(args.wc - args.wp)) + 1
            fp_lat = (args.wp + (args.l + args.kc) * args.wc +
                      (1 + math.floor((args.l - 1) / m)) * args.nc)

        return max(ss_lat, fp_lat)

    elif args.algorithm == 'poll':
        return ((args.l + 1) * args.wc) if args.wp < args.wc else (2 * args.wp + args.wc)


def service_latency(pcs, args):
    # Compute worst case service latencies
    cev = 0
    pev = 0
    pktidx = 0
    last_wp_t = 0
    worst_case_pktidx = []
    worst_case_latency = 0
    while pev < len(pcs.prod_events) and cev < len(pcs.cons_events):
        while pev < len(pcs.prod_events) and pcs.prod_events[pev][1] != pktidx:
            pev += 1

        while cev < len(pcs.cons_events) and pcs.cons_events[cev][1] != pktidx:
            cev += 1

        if pev >= len(pcs.prod_events) or cev >= len(pcs.cons_events):
            break

        latency = pcs.cons_events[cev][0] + pcs.args.wc - last_wp_t
        last_wp_t = pcs.prod_events[pev][0]

        if abs(latency - worst_case_latency) < 0.00000001:
            worst_case_pktidx.append(pktidx)
        elif latency > worst_case_latency:
            worst_case_latency = latency
            worst_case_pktidx = [pktidx]
        #print('pkt #%d --> latency %.2f' % (pktidx, latency))
        pktidx += 1

    if worst_case_latency - latency_bound(args) > 0.000001:
        print('ERROR: worst case latency exceeds the bound')

    return worst_case_latency, worst_case_pktidx


def plot_depends(args, xs, t_vec, t_lower_vec, t_higher_vec, energy_vec):
    from matplotlib import pyplot as plt
    plt.plot(xs, t_vec, 'o-', label='T_avg')
    plt.plot(xs, t_lower_vec, 'x-', label='T_lower')
    plt.plot(xs, t_higher_vec, 'x-', label='T_higher')
    plt.plot(xs, energy_vec, 'o-', label='Energy')
    plt.ylabel('Average per-packet time / Energy')
    plt.xlabel(args.depends)
    plt.title('How per-packet time and energy depend from Yc/Yp')
    plt.grid(True)
    plt.legend(loc='upper left')
    plt.show()


description = "Python script to simulate sleeping prod/cons"
epilog = "2016 Vincenzo Maffione <v.maffione@gmail.com>"

argparser = argparse.ArgumentParser(description = description,
                                    epilog = epilog)
argparser.add_argument('-t', '--time-max',
                       help = "Max simulation time for each run",
                       type = float, default = 0.5)
argparser.add_argument('--wp', help = "Wp", type = float, default = 2.0)
argparser.add_argument('--wc', help = "Wc", type = float, default = 1.0)
argparser.add_argument('--yp', help = "Yp", type = float, default = 5.0)
argparser.add_argument('--yc', help = "Yc", type = float, default = 5.0)
argparser.add_argument('--ye', help = "Ye", type = float, default = 2.5)
argparser.add_argument('--nc', help = "Nc", type = float, default = 3.0)
argparser.add_argument('--np', help = "Np", type = float, default = 4.5)
argparser.add_argument('--sc', help = "Sc", type = float, default = 2.1)
argparser.add_argument('--sp', help = "Sp", type = float, default = 7.1)
argparser.add_argument('--kp', help = "Kp", type = int, default = 1)
argparser.add_argument('--kc', help = "Kc", type = int, default = 1)
argparser.add_argument('-l', help = "Queue length", type = int, default = 3)
argparser.add_argument('--cons-offset', help = "Consumer start delay", type = float, default = 0.0)
argparser.add_argument('-q', '--quiet', help = "Compute only stats", action='store_true')
argparser.add_argument('--xunits', help = "Wp/Wc units per line in the plot", type = int, default = 180)
argparser.add_argument('--all-worst-latencies', help = "Show all the worst case latencies", action='store_true')

argparser.add_argument('-a', '--algorithm', help = "Algorithm",
                       choices=['sleep', 'notify', 'poll'], default = 'sleep')

argparser.add_argument('--depends', help = "Dependency on", choices=['yp', 'yc', 'y'])
argparser.add_argument('--ymax', help = "max Yc or Yp when depends is specified",
                       type = float, default = 100.0)
argparser.add_argument('--points', help = "number of Yp or Yc points to test when depends is specified",
                       type = int, default = 150)

args = argparser.parse_args()

if args.depends:
    args.yc = max(args.yc, args.ye)
    args.yp = max(args.yp, args.ye)

print('Parameters:')
print('    L  = %d' % args.l)
print('    Wp = %.2f' % args.wp)
print('    Wc = %.2f' % args.wc)
print('    Yp = %.2f' % args.yp)
print('    Yc = %.2f' % args.yc)
print('    Ye = %.2f' % args.ye)
print('    Np = %.2f' % args.np)
print('    Nc = %.2f' % args.nc)
print('    Sp = %.2f' % args.sp)
print('    Sc = %.2f' % args.sc)
print('    Kp = %d' % args.kp)
print('    Kc = %d' % args.kc)
print('')

mx = max(args.wp, args.wc, args.yp, args.yc,
         args.np, args.nc, args.sp, args.sc)

if args.depends:
    print("%11s %11s %11s %11s" % (args.depends, 'time', 'energy', 'batch'))
    xs = []
    t_vec = []
    t_lower_vec = []
    t_higher_vec = []
    energy_vec = []
    incr = (args.ymax - args.ye)/args.points
    x = args.ye
    while x < args.ymax:
        if args.depends == 'yp':
            args.yp = x
        elif args.depends == 'yc':
            args.yc = x
        else:
            args.yp = args.yc = x

        pcs = simulate(args)
        t_vec.append(t_prod(args, pcs))
        energy_vec.append(energy(args, pcs))
        bounds = t_bounds(args)
        t_lower_vec.append(bounds[0])
        t_higher_vec.append(bounds[1])
        xs.append(x)
        print("%11.2f %11.2f %11.2f %11.2f" % (x, t_prod(args, pcs),
              energy(args, pcs), batch(args, pcs)))
        x += incr

    plot_depends(args, xs, t_vec, t_lower_vec, t_higher_vec, energy_vec)

else:
    pcs = simulate(args)

    worst_case_latency, worst_case_pktidx = service_latency(pcs, args)
    print('Worst case latency: %.2f, bound %.2f' % \
          (worst_case_latency, latency_bound(args)))

    if not args.quiet:
        if not args.all_worst_latencies:
            worst_case_pktidx = [worst_case_pktidx[min(2, len(worst_case_pktidx)-1)]]
        pcs.dump(worst_case_pktidx)

    print('Packets processed %d' % pcs.pkts)
    print('Producer sleeps   %d' % pcs.prod_sleeps)
    print('Consumer sleeps   %d' % pcs.cons_sleeps)
    bounds = t_bounds(args)
    print('Time per packet %f (or %f), sleep bounds (%f %f)' % \
            (t_prod(args, pcs), t_cons(args, pcs), bounds[0], bounds[1]))
    print('Energy per packet %f' % (energy(args, pcs),))

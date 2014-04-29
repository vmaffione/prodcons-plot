#!/bin/bash

SC=200
NC=200
WC=500
SP=200
NP=2000

for i in {400..600}; do
    ./prodcon -s${SP} -n${NP} -w${i} -S${SC} -N${NC} -W${WC} -L256 -T2000 -O | tail -n1
done

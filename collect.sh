#!/bin/bash

SC=200
NC=200
WC=500
SP=200
NP=2000

for WP in {1..1000}; do
    RES=$(./prodcon -s${SP} -n${NP} -w${WP} -S${SC} -N${NC} -W${WC} -L256 -T2000 -O | tail -n1 | cut -f 3 -d' ')
    echo ${WP} ${RES}
done

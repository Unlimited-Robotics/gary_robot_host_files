#!/bin/bash

export DISPLAY=:0
pkill vino
/usr/lib/vino/vino-server --display=$DISPLAY

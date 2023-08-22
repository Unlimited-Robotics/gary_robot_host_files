#!/bin/bash
sudo busybox devmem 0x0c303000 32 0x0000C400
sudo busybox devmem 0x0c303008 32 0x0000C458
sudo busybox devmem 0x0c303010 32 0x0000C400
sudo busybox devmem 0x0c303018 32 0x0000C458

sudo modprobe pcan
sudo modprobe peak_usb
sudo ip link set can0 up type can bitrate 1000000

sudo modprobe can
sudo modprobe can_raw
sudo modprobe mttcan
sudo ip link set can1 type can bitrate 1000000 triple-sampling on
sudo ip link set can2 type can bitrate 1000000 triple-sampling on
sudo ip link set up can1
sudo ip link set up can2
exit 0
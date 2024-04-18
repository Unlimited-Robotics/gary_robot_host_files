#!/bin/bash

# https://docs.qq.com/doc/DUEdIc29sSEpJc1d3

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

SERIALCAN0=003A00165457530120383638
SERIALCAN1=002E002B5457530220383638

CAN_UDEV_RULES_FILE="/etc/udev/rules.d/99-candlelight.rules"

can_udev_rules () {
cat << EOF
SUBSYSTEMS=="net", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="606f", ATTRS{serial}=="$SERIALCAN0", NAME="can0"
SUBSYSTEMS=="net", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="606f", ATTRS{serial}=="$SERIALCAN1", NAME="can1"
EOF
}

if [ -f "$CAN_UDEV_RULES_FILE" ]
then
    echo -e "${GREEN}$CAN_UDEV_RULES_FILE exists. ${NC}"
else
    echo -e "${YELLOW}$CAN_UDEV_RULES_FILE does not exist, creating udev rules.${NC}"
    can_udev_rules > $CAN_UDEV_RULES_FILE
    udevadm trigger
    udevadm control --reload-rules
fi

sleep 5
# CAN devices connected over USB
# Bus 001 Device 024: ID 1d50:606f OpenMoko, Inc. USB2.0 Hub
DEVICES=($(sudo lsusb -d 1d50:606f -v | grep -i iserial | cut -c 29-))
if [[ ${DEVICES[@]} =~ $SERIALCAN0 ]]
then
    echo -e "${GREEN}CAN0 device found! $SERIALCAN0 ${NC}"
    ip link set dev can0 up type can bitrate 1000000
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}CAN0 is up!${NC}"
    else
        echo -e "${RED}ERROR: can't setup CAN0! $SERIALCAN0 ${NC}"
    fi

else
    echo -e "${RED}ERROR: CAN0 device not found! $SERIALCAN0 ${NC}"
fi

if [[ ${DEVICES[@]} =~ $SERIALCAN1 ]]
then
    echo -e "${GREEN}CAN1 device found! $SERIALCAN1 ${NC}"
    ip link set dev can1 up type can bitrate 1000000
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}CAN1 is up!${NC}"
    else
        echo -e "${RED}ERROR: can't setup CAN1! $SERIALCAN0 ${NC}"
    fi
else
    echo -e "${RED}ERROR: CAN1 device not found! $SERIALCAN1 ${NC}"
fi
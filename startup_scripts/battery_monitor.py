#!/bin/python3

import can
import time


CAN_INTERFACE = 'can0'
BATTERY_CAN_ID = 0x105

BATTERY_FILE_PATH = '/tmp/battery_level'
MESSAGE_TIMEOUT = 180 # 180 seconds (3 minutes)

INITIAL_BATTERY_LEVEL_STR = '!!!'
INITIAL_BATTERY_CHARGING_STR = '!'
DEFAULT_BATTERY_LEVEL_STR = '---'
DEFAULT_BATTERY_CHARGING_STR = '-'


# global variabled
battery_level = INITIAL_BATTERY_LEVEL_STR
battery_level_last_time = time.time()
battery_charging = INITIAL_BATTERY_CHARGING_STR
battery_charging_last_time = time.time()
update_file = False

def write_file():

    global battery_level
    global battery_level_last_time
    global battery_charging
    global battery_charging_last_time
    global update_file

    # print(f'{battery_charging}{battery_level}')
    with open(BATTERY_FILE_PATH, "w") as f:
        f.write(
                f'{battery_charging}{battery_level}\n'
            )


def main():

    global battery_level
    global battery_level_last_time
    global battery_charging
    global battery_charging_last_time
    global update_file

    write_file()

    time.sleep(5.0)

    can_interface = CAN_INTERFACE
    bus = can.interface.Bus(channel=can_interface, bustype='socketcan')

    while True:
        message = bus.recv(timeout=5.0)
        
        if message is not None:

            if message.arbitration_id==BATTERY_CAN_ID:
                # Message from microcontroller

                if message.data[0]==0x22:
                    # Battery level message
                    battery_level = str(int(message.data[7])).zfill(3)
                    battery_level_last_time = time.time()
                    update_file = True

                if message.data[0]==0x29:
                    # Battery charging status message
                    if message.data[7] & 0x40:
                        battery_charging = 'D'
                    else:
                        battery_charging = 'C'
                    battery_charging_last_time = time.time()
                    update_file = True
        
        else:
            # If not message received, set to default values
            battery_level = DEFAULT_BATTERY_LEVEL_STR
            battery_charging = DEFAULT_BATTERY_CHARGING_STR
            update_file = True

        
        if battery_level not in \
                [DEFAULT_BATTERY_LEVEL_STR, INITIAL_BATTERY_LEVEL_STR]:
            if (time.time() - battery_level_last_time) >= MESSAGE_TIMEOUT:
                battery_level = DEFAULT_BATTERY_LEVEL_STR
                update_file = True


        if battery_charging not in \
                [DEFAULT_BATTERY_CHARGING_STR, INITIAL_BATTERY_CHARGING_STR]:
            if (time.time() - battery_charging_last_time) >= MESSAGE_TIMEOUT:
                battery_charging = DEFAULT_BATTERY_CHARGING_STR
                update_file = True
                    
        
        if update_file:
            write_file()
            update_file = False


if __name__ == "__main__":
    main()

#!/bin/python3

import can
import time
import os
import logging
from logging.handlers import SysLogHandler
from queue import Queue, Empty, Full
from threading import Thread

def retrieve_env_variable(name: str):
    ENV_FILE_PATH = r'/opt/raya_os/env'
    env_file = open(ENV_FILE_PATH,'r').read()
    if env_file.find(name)==-1:
        raise Exception(f'Environment variable {name} not found in {ENV_FILE_PATH}')
    if env_file[:env_file.find(name)+len(name)+1].splitlines()[-1].find("#")!=-1:
        raise Exception(f'Environment variable {name} is commented in {ENV_FILE_PATH}')
    ini=env_file.find(name)+(len(name)+1)
    rest=env_file[ini:]
    search_enter=rest.find('\n')
    return rest[:search_enter]

GARY_SENSORS_CAN_INTERFACE = retrieve_env_variable("GARY_SENSORS_CAN_INTERFACE")

BATTERY_CAN_ID = int(retrieve_env_variable("GARY_SENSORS_MC_ID"),base=16)
GARY_LEDS_TOPMC_CANID = int(retrieve_env_variable("GARY_LEDS_TOPMC_CANID"),base=16)
GARY_LEDS_BOTMC_CANID = int(retrieve_env_variable("GARY_LEDS_BOTMC_CANID"),base=16)

GARY_LEDS_CAN_INTERFACE = retrieve_env_variable("GARY_LEDS_CAN_INTERFACE")

UR_SOUND_OUT = retrieve_env_variable("UR_SOUND_OUT")

BATTERY_LOW_LEVEL = 30
BATTERY_CRITICAL_LEVEL = 10

BATTERY_FILE_PATH = r'/tmp/battery_level'
MESSAGE_TIMEOUT = 180 # 180 seconds (3 minutes)

INITIAL_BATTERY_LEVEL_STR = '!!!'
INITIAL_BATTERY_CHARGING_STR = '!'
DEFAULT_BATTERY_LEVEL_STR = '---'
DEFAULT_BATTERY_CHARGING_STR = '-'

# Create a logger
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)
syslog_handler = SysLogHandler(address='/dev/log')
syslog_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
syslog_handler.setFormatter(formatter)
logger.addHandler(syslog_handler)


# global variabled
battery_level = INITIAL_BATTERY_LEVEL_STR
battery_level_last_time = time.time()
battery_charging = INITIAL_BATTERY_CHARGING_STR
battery_charging_last_time = time.time()
update_file = False
read_first_time = False

def write_file():

    global battery_level
    global battery_level_last_time
    global battery_charging
    global battery_charging_last_time
    global update_file

    logger.info(
        f'The current battery status is:{battery_charging}{battery_level}'
    )
    with open(BATTERY_FILE_PATH, "w") as f:
        f.write(
                f'{battery_charging}{battery_level}\n'
            )

def ping_registers():
    with can.interface.Bus(
            channel=GARY_SENSORS_CAN_INTERFACE,
            bustype='socketcan'
        ) as bus: 
            while True:
                # Msg to get all sensors value
                ping_msg = can.Message(
                    arbitration_id=0x103, 
                    data=[0x53,0x53,0x03,0x01,0x54,0x00,0x00,0x00], 
                    is_extended_id=False
                )
                try:
                    bus.send(ping_msg)
                except can.CanError:
                    print("Ping NOT sent")
                time.sleep(20)


def low_battery_sender(queue: Queue):
    global read_first_time
    battery_level = 100
    chargin_state = False
    try:
        while True:
            try:
                data = queue.get(block=False)
                if data is not None:
                    battery_level, chargin_state = data
            except Empty:
                pass
            speed = 0x16 if battery_level <= BATTERY_CRITICAL_LEVEL else 0x32
            if battery_level < BATTERY_LOW_LEVEL and not chargin_state and read_first_time:
                # Send LEDs animation
                head_leds_msg = can.Message(
                    arbitration_id=GARY_LEDS_TOPMC_CANID, 
                    data=[0x48, 0x4C, 0x05, speed, 0x01, 80, 0x20, 0x00], 
                    is_extended_id=False
                )
                chest_leds_msg = can.Message(
                    arbitration_id=GARY_LEDS_TOPMC_CANID, 
                    data=[0x43, 0x4C, 0x02, speed, 0x01, 80, 0x20, 0x00], 
                    is_extended_id=False
                )
                skirt_leds_msg = can.Message(
                    arbitration_id=GARY_LEDS_BOTMC_CANID, 
                    data=[0x53, 0x4C, 0x0F, speed, 0x01, 80, 0x20, 0x00], 
                    is_extended_id=False
                )
                with can.Bus(
                    interface='socketcan',
                    channel=GARY_LEDS_CAN_INTERFACE
                ) as bus:
                    try:
                        bus.send(head_leds_msg)
                        bus.send(chest_leds_msg)
                        bus.send(skirt_leds_msg)
                    except can.CanError:
                        # sudo ifconfig can2 txqueuelen 1000
                        print("LED's animations NOT sent")
                os.system(
                    f'sudo -u \'#1000\' XDG_RUNTIME_DIR=/run/user/1000 paplay --device {UR_SOUND_OUT} '
                    f'{os.getcwd()}/data/very_low_battery.wav'
                )
            time.sleep(2)
    except Exception as e:
        print(f"Error with CAN configuration: {e}")
        exit(1)

def main():

    global battery_level
    global battery_level_last_time
    global battery_charging
    global battery_charging_last_time
    global update_file
    global read_first_time

    write_file()
    time.sleep(5.0)
    queue = Queue(maxsize=1)
    queue.put(None)
    low_battery_sender_thread = Thread(
        target=low_battery_sender, 
        args=(queue, ), 
        daemon=True)
    low_battery_sender_thread.start()

    ping_thread = Thread(
        target=ping_registers,
        daemon=True)
    enable_ping = False
    request_uC_version = True
    can_version = ""
    battery_level = 0
    chargin_state = False
    try:
        with can.interface.Bus(
            channel=GARY_SENSORS_CAN_INTERFACE,
            bustype='socketcan'
        ) as bus: 
            while True:
                message = bus.recv(timeout=None)
                if request_uC_version:
                    try:
                        bus.send(can.Message(
                            arbitration_id=0x103, 
                            data=[0x53, 0x53, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00], 
                            is_extended_id=False
                        ))
                    except can.CanError:
                        print("Request uC Version NOT sent")
                if message is not None:
                    if message.arbitration_id==BATTERY_CAN_ID:

                        # Enable ping every x seconds to get battery data from uC
                        if message.data[0]==0x00 and not enable_ping:
                            can_version = str(message.data[3:], 'utf-8')[2:]
                            if can_version[0]>='2':
                                if not ping_thread.is_alive():
                                    ping_thread.start()
                                enable_ping = True
                                print(f"Start ping, uC Version: {can_version}")
                            request_uC_version = False

                        # Message from microcontroller
                        if message.data[0]==0x22:
                            # Battery level message
                            battery_level = str(int(message.data[7])).zfill(3)
                            battery_level_last_time = time.time()
                            update_file = True           
                            read_first_time =True  
                        if message.data[0]==0x29:
                            # Battery charging status message
                            if message.data[7] & 0x40:
                                battery_charging = 'D'
                                chargin_state = False
                            else:
                                battery_charging = 'C'
                                chargin_state = True
                            battery_charging_last_time = time.time()
                            update_file = True
                        try:
                            queue.put(
                                item=(int(battery_level), chargin_state), 
                                block=False
                            )
                        except Full:
                            pass
                
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
    finally:
        bus.shutdown()
        print("End")


if __name__ == "__main__":
    main()
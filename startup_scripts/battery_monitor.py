#!/bin/python3
# Important!!!, install iterators: sudo python3 -m pip install iterators
import os
import sys
import time
import logging
import subprocess
from threading import Thread
from iterators import TimeoutIterator
from logging.handlers import RotatingFileHandler

def retrieve_env_variable(name: str):
    ENV_FILE_PATH = '/opt/raya_os/env'
    env_file = open(ENV_FILE_PATH,'r').read()
    if env_file.find(name)==-1:
        raise Exception(f'Environment variable {name} not found in {ENV_FILE_PATH}')
    if env_file[:env_file.find(name)+len(name)+1].splitlines()[-1].find("#")!=-1:
        raise Exception(f'Environment variable {name} is commented in {ENV_FILE_PATH}')
    ini=env_file.find(name)+(len(name)+1)
    rest=env_file[ini:]
    search_enter=rest.find('\n')
    return rest[:search_enter]

def execute(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line 
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

# Retrieve values from env robot
GARY_SENSORS_CAN_INTERFACE = retrieve_env_variable("GARY_SENSORS_CAN_INTERFACE")
BATTERY_CAN_ID = int(retrieve_env_variable("GARY_SENSORS_MC_ID"),base=16)
GARY_LEDS_TOPMC_CANID = int(retrieve_env_variable("GARY_LEDS_TOPMC_CANID"),base=16)
GARY_LEDS_BOTMC_CANID = int(retrieve_env_variable("GARY_LEDS_BOTMC_CANID"),base=16)
GARY_LEDS_CAN_INTERFACE = retrieve_env_variable("GARY_LEDS_CAN_INTERFACE")
UR_SOUND_OUT = retrieve_env_variable("UR_SOUND_OUT")

# Script configurations
BATTERY_LOW_LEVEL = 30
BATTERY_CRITICAL_LEVEL = 10
BATTERY_FILE_PATH = '/tmp/battery_level'
BATTERY_REGISTERS_PING_TIME = 10
MESSAGE_TIMEOUT = 180 # 180 seconds (3 minutes)
SOUND_ALERT_PATH=os.getcwd()+'/data/very_low_battery.wav'

INITIAL_BATTERY_LEVEL_STR = '!!!'
INITIAL_BATTERY_CHARGING_STR = '!'
DEFAULT_BATTERY_LEVEL_STR = '---'
DEFAULT_BATTERY_CHARGING_STR = '-'

class Logger():
    def __init__(self, name):
        # Create a logger
        file_handler = RotatingFileHandler(
            filename=f'/tmp/{name}.log', 
            mode='a', 
            maxBytes=1024, 
            backupCount=1
        )
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        handlers = [file_handler, stdout_handler]

        logging.basicConfig(
            level=logging.DEBUG, 
            format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        self.logger = logging.getLogger(name)
    
    def get_logger(self):
        return self.logger

logger = Logger('battery_monitor').get_logger()

def pingValues():
    while True:
        # Ping registers from 0x22 to 0x29
        cmd = f'/usr/bin/cansend {GARY_SENSORS_CAN_INTERFACE} 103#5353032229000000'
        while True:
            ec = os.system(cmd)
            if ec != 0:
                logger.error(f"Can't send data to {GARY_SENSORS_CAN_INTERFACE}!")
            time.sleep(BATTERY_REGISTERS_PING_TIME)

def getBatteryStatus():
    try:
        for dump in execute(['/usr/bin/candump',GARY_SENSORS_CAN_INTERFACE]):
            if dump[19:21]=="22":
                yield int(dump[-3:],base=16)
            if dump[19:21]=="29":
                yield int(dump[-3:],base=16)&0x40 == 0 # True if charging
    except:
        logger.error(f"CAN Bus failed to start: {GARY_SENSORS_CAN_INTERFACE}!")

def sendDischarging(level: int):
    speed = 0x16 if level <= BATTERY_CRITICAL_LEVEL else 0x32
    head_leds_cmd = f'/usr/bin/cansend {GARY_LEDS_CAN_INTERFACE}  {GARY_LEDS_TOPMC_CANID}#484C05{speed}01802000'
    chest_leds_msg = f'/usr/bin/cansend {GARY_LEDS_CAN_INTERFACE} {GARY_LEDS_TOPMC_CANID}#434C02{speed}01802000'
    skirt_leds_msg = f'/usr/bin/cansend {GARY_LEDS_CAN_INTERFACE} {GARY_LEDS_BOTMC_CANID}#534C0F{speed}01802000'
    logger.info("Sending alert to leds")
    ec = os.system(head_leds_cmd)
    if ec != 0: logger.error(f"Can't send data to {GARY_LEDS_CAN_INTERFACE}!")
    ec = os.system(chest_leds_msg)
    if ec != 0: logger.error(f"Can't send data to {GARY_LEDS_CAN_INTERFACE}!")
    ec = os.system(skirt_leds_msg)
    if ec != 0: logger.error(f"Can't send data to {GARY_LEDS_CAN_INTERFACE}!")
    logger.info("Playing low battery sound")
    os.system(
            f'sudo -u \'#1000\' XDG_RUNTIME_DIR=/run/user/1000 paplay --device {UR_SOUND_OUT} '
            f'{SOUND_ALERT_PATH}'
        )
    if ec != 0: logger.error(f"Can't play file!")


def main():
    logger.info(f'Parameters:')
    logger.info(f'*   File path: {BATTERY_FILE_PATH}')
    logger.info(f'*   Message timeout: {BATTERY_FILE_PATH} seconds')
    logger.info(f'*   CAN Interface: {GARY_SENSORS_CAN_INTERFACE}')
    logger.info(f'*   Battery CAN ID (Sensors): {BATTERY_CAN_ID} ({hex(BATTERY_CAN_ID)})')
    logger.info(f'*   Sound alert file path: {SOUND_ALERT_PATH} ({"Exist" if os.path.isfile(SOUND_ALERT_PATH) else "Missing file"})')

    level = None
    state = None
    os.system(f'echo "!!!!" > {BATTERY_FILE_PATH} ')

    ping_thread = Thread(target=pingValues)
    ping_thread.setDaemon(True)
    ping_thread.start()

    it = TimeoutIterator(getBatteryStatus(), timeout=MESSAGE_TIMEOUT)
    for i in it:
        if i == it.get_sentinel():
            level = None
            state = None
            os.system(f'echo "----" > {BATTERY_FILE_PATH} ')
        else:
            if isinstance(i, bool):
                state = 'C' if i else 'D'
            else:
                level = i
        logger.info(f'Level: {level}, Status: {state}')
        if level!=None and state!=None:
            os.system(f'echo {state}{str(level).zfill(3)} > {BATTERY_FILE_PATH}')
            if level < BATTERY_LOW_LEVEL and state == 'D':
                sendDischarging(level)



if __name__ == "__main__":
    main()
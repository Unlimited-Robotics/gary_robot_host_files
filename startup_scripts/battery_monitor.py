#!/bin/python3
# Important!!!
# install iterators: sudo -H python3 -m pip install iterators
# install can-utils: sudo apt install can-utils
import os
import sys
import time
import logging
import subprocess
from threading import Thread
from iterators import TimeoutIterator
from logging.handlers import RotatingFileHandler, SysLogHandler

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
BATTERY_CAN_ID = int(retrieve_env_variable("GARY_SENSORS_UC_CAN_ID"),base=16)
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
SOUND_ALERT_PATH='/startup_scripts/data/very_low_battery.wav'
SOUND_ALERT_MS=30000
PLAY_ALERT=False
WAIT_START_TIME = 5

INITIAL_BATTERY_LEVEL_STR = '!!!'
INITIAL_BATTERY_CHARGING_STR = '!'
DEFAULT_BATTERY_LEVEL_STR = '---'
DEFAULT_BATTERY_CHARGING_STR = '-'

class Logger():
    def __init__(self, name):
        log_filename = f'/startup_scripts/log/{name}.log'
        os.makedirs(os.path.dirname(log_filename), exist_ok=True)
        # Create a logger
        file_handler = RotatingFileHandler(
            filename= log_filename, 
            mode='a', 
            maxBytes=1024, 
            backupCount=1
        )
        syslog_handler = SysLogHandler(address='/dev/log')
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        handlers = [file_handler, stdout_handler, syslog_handler]

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
    head_leds_cmd  = f'/usr/bin/cansend {GARY_LEDS_CAN_INTERFACE} {hex(GARY_LEDS_TOPMC_CANID)[2:]}#484C05{speed}03802000'
    chest_leds_msg = f'/usr/bin/cansend {GARY_LEDS_CAN_INTERFACE} {hex(GARY_LEDS_TOPMC_CANID)[2:]}#434C02{speed}03802000'
    skirt_leds_msg = f'/usr/bin/cansend {GARY_LEDS_CAN_INTERFACE} {hex(GARY_LEDS_BOTMC_CANID)[2:]}#534C0F{speed}03802000'
    logger.info("Sending alert to leds")
    ec = os.system(head_leds_cmd)
    if ec != 0: logger.error(f"Can't send data to {GARY_LEDS_CAN_INTERFACE}!")
    ec = os.system(chest_leds_msg)
    if ec != 0: logger.error(f"Can't send data to {GARY_LEDS_CAN_INTERFACE}!")
    ec = os.system(skirt_leds_msg)
    if ec != 0: logger.error(f"Can't send data to {GARY_LEDS_CAN_INTERFACE}!")

def playBatteryAlert():
    global PLAY_ALERT
    while True:
        if PLAY_ALERT:
            logger.info("Playing low battery sound")
            ec = os.system(
                    f'sudo -u \'#1000\' XDG_RUNTIME_DIR=/run/user/1000 paplay --device {UR_SOUND_OUT} '
                    f'{SOUND_ALERT_PATH}'
                )
            if ec != 0: logger.error(f"Can't play file!")
        time.sleep(SOUND_ALERT_MS/1000)

def write_to_file(level, state):
    os.system(f'echo "{state}{level}" > {BATTERY_FILE_PATH} ')


def main():
    global PLAY_ALERT
    logger.info(f'Parameters:')
    logger.info(f'*   File path: {BATTERY_FILE_PATH}')
    logger.info(f'*   Message timeout: {BATTERY_FILE_PATH} seconds')
    logger.info(f'*   CAN Interface: {GARY_SENSORS_CAN_INTERFACE}')
    logger.info(f'*   Battery CAN ID (Sensors): {BATTERY_CAN_ID} ({hex(BATTERY_CAN_ID)})')
    logger.info(f'*   Sound alert file path: {SOUND_ALERT_PATH} ({"Exist" if os.path.isfile(SOUND_ALERT_PATH) else "Missing file"})')
    logger.info(f'Waiting start time')
    time.sleep(WAIT_START_TIME)
    logger.info(f'Wait for can sensors interface')
    attemps = 1
    while True:
        try:
            logger.info(f'Attemp: {attemps}')
            attemps+=1
            if attemps>20:
                logger.error(f'CAN interface {GARY_SENSORS_CAN_INTERFACE} is down...')
                attemps=1
            ps = subprocess.Popen(('ip','link','show'), stdout=subprocess.PIPE)
            output = subprocess.check_output(('grep', '-o', '-P', ': can.{0,1}'), stdin=ps.stdout)
            ps.wait()
            can_list = output.decode("utf-8").replace('\n','').replace(':','').split(" ")[1:]
            if GARY_SENSORS_CAN_INTERFACE in can_list:
                break
        except subprocess.CalledProcessError:
            time.sleep(5)

    logger.info(f'Sensors CAN interface is up')

    level = None
    state = None
    write_to_file(level=INITIAL_BATTERY_LEVEL_STR, state=INITIAL_BATTERY_CHARGING_STR)

    ping_thread = Thread(target=pingValues)
    ping_thread.setDaemon(True)
    ping_thread.start()

    play_alert_thread = Thread(target=playBatteryAlert)
    play_alert_thread.setDaemon(True)
    play_alert_thread.start()

    it = TimeoutIterator(getBatteryStatus(), timeout=MESSAGE_TIMEOUT)
    for i in it:
        if i == it.get_sentinel():
            level = None
            state = None
            write_to_file(level=DEFAULT_BATTERY_LEVEL_STR, state=DEFAULT_BATTERY_CHARGING_STR)
        else:
            if isinstance(i, bool):
                state = 'C' if i else 'D'
            else:
                level = i
        logger.info(f'Level: {level}, Status: {state}')
        if level!=None and state!=None:
            write_to_file(level=str(level).zfill(3), state=state)
            if level < BATTERY_LOW_LEVEL and state == 'D':
                sendDischarging(level)
                PLAY_ALERT=True
            else:
                PLAY_ALERT=False



if __name__ == "__main__":
    main()
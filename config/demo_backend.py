from distutils import dir_util
import uuid
import os
import time

import signal
import yaml
from SwarmBootstrapUtils import yaml_parser
import subprocess
import enum
import threading


class DemoLauncher:
    def __init__(self):
        self._run_process = None
        self._status = DemoLauncher.Status.IDLE
        self._status_file = 'status.txt'

        # if not self._has_valid_initial_state():
        #     raise ValueError(
        #         'Launcher was terminated improperly and the last state is: ' +
        #         self._read_last_state_from_file())


    def _start_script(self, config_dir, drone_ips):
        run_cmd = 'python3 run.py ' + config_dir
        self._run_process = subprocess.Popen(run_cmd.split(), start_new_session=True,
                                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def _stop_script(self):
        pgid = os.getpgid(self._run_process.pid)
        os.killpg(pgid, signal.SIGINT)
        os.waitpid(-pgid, 0)
        alive_pgids = subprocess.check_output('ps x o pgid'.split()).decode(
            "utf-8").rstrip().replace(' ', '').split('\n')
        while str(pgid) in alive_pgids:
            time.sleep(1)
            alive_pgids = subprocess.check_output('ps x o pgid'.split()).decode(
                "utf-8").rstrip().replace(' ', '').split('\n')
        self._change_status(DemoLauncher.Status.IDLE)
        self._run_process = None

    def _wait_for_ready(self):
        while self._status == DemoLauncher.Status.LAUNCHING:
            next_line = self._run_process.stdout.readline().decode("utf-8").rstrip()
            print(next_line)
            if next_line == 'Start flying!! Press Ctrl+C to terminate the program.':
                if self._status == DemoLauncher.Status.LAUNCHING:
                    self._change_status(DemoLauncher.Status.FLYING)
                return

    def launch(self, config_dir, drone_ips):
        if self._status == DemoLauncher.Status.IDLE:
            self._change_status(DemoLauncher.Status.LAUNCHING)
            self._start_script(config_dir, drone_ips)
            wait_thread = threading.Thread(target=self._wait_for_ready)
            wait_thread.start()
        else:
            raise ValueError(
                'Script can only be launched if current state is IDLE, but the current state is: '
                '' + str(self._status.name))

    def stop(self):
        if self._status == DemoLauncher.Status.STOPPING:
            raise ValueError('Waiting for all processes being killed. Please be patient...')
        elif self._status == DemoLauncher.Status.IDLE:
            raise ValueError('There is no process running')
        else:
            self._change_status(DemoLauncher.Status.STOPPING)
            stopping_thread = threading.Thread(target=self._stop_script)
            stopping_thread.start()

    def get_status(self):
        return self._status

    def _change_status(self, new_status):
        self._status = new_status
        self._write_current_state_to_file()

    def _write_current_state_to_file(self):
        with open(self._status_file, 'a+') as file:
            file.write(str(self._status.name) + '\n')

    # def _read_last_state_from_file(self):
    #     with open(self._status_file, 'a+') as file:
    #         # The last line is a blank line. We read the second last one
    #         lines = file.readlines()
    #         if len(lines) >= 2:
    #             last_state = file.readlines()[-2]
    #         else:
    #             last_state = ''
    #     return last_state

    # def _has_valid_initial_state(self):
    #     last_state = self._read_last_state_from_file()
    #     if last_state == '' or last_state == DemoLauncher.Status.IDLE.name:
    #         return True
    #     else:
    #         return False

    class Status(enum.Enum):
        IDLE = 1
        LAUNCHING = 2
        READY = 3
        FLYING = 4
        STOPPING = 5

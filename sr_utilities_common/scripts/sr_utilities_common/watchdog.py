#!/usr/bin/python

import sys
import rospy
import curses
import locale
import psutil
from threading import Thread, Lock
from sr_utilities_common.shutdown_handler import ShutdownHandler


# TODO: Change to decided convention of enum and put inside of class
class Status:
    PENDING, OK, ERROR = ('pending', 'ok', 'error')


class SrWatchdog(object):
    def __init__(self, checks_class=None, error_checks_list=[], warning_checks_list=[]):
        self.checks_class = checks_class
        self.error_checks_list = error_checks_list
        self.warning_checks_list = warning_checks_list

        self.demo_status = Status.PENDING
        self.cpu_usage = 0
        self.cpu_usage_per_core = []
        self.node_logs = []
        self.check_results = {}
        self.checks_done_in_current_cycle = 0

        self.init_reporting()

    def init_reporting(self):
        locale.setlocale(locale.LC_ALL, '')
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.noecho()
        curses.cbreak()

    def main_thread_method(self):
        while not rospy.is_shutdown():
            self.report_status()
            self.get_cpu_usage()

    def checks_thread_method(self):
        while not rospy.is_shutdown():
            self.run_checks()

    def run(self):
        main_thread = Thread(target=self.main_thread_method).start()
        checks_thread = Thread(target=self.checks_thread_method).start()

    def report_status(self):
        self.stdscr.clear()
        if Status.OK == self.demo_status:
            color_pair_idx = 4
        elif Status.ERROR == self.demo_status:
            color_pair_idx = 3
        else:
            color_pair_idx = 1

        self.stdscr.addstr(0, 0, "Demo status:".format(self.demo_status))
        self.stdscr.addstr(0, 13, self.demo_status, curses.color_pair(color_pair_idx))

        number_of_failing_tests = sum(val is False for val in self.check_results.values())
        for idx, key in enumerate([key for key, val in self.check_results.items() if val is False]):
            if idx < number_of_failing_tests - 1:
                box_utf_8 = u'\u251C'.encode('utf-8')
            else:
                box_utf_8 = u'\u2514'.encode('utf-8')
            arrow_str = box_utf_8 + u'\u2500'.encode('utf-8') + u'\u2500'.encode('utf-8') + u'\u257C'.encode('utf-8')
            self.stdscr.addstr(idx+1, 4, arrow_str)
            self.stdscr.addstr(idx+1, 9, key)

        self.stdscr.addstr(number_of_failing_tests+2, 0, "CPU usage: {} {} [%]".format(self.cpu_usage,
                                                                                       tuple(self.cpu_usage_per_core)))

        checks_done_in_cycle_percent = self.checks_done_in_current_cycle / float(len(self.error_checks_list) +
                                                                                 len(self.warning_checks_list)) * 100
        self.stdscr.addstr(number_of_failing_tests+4, 0, "Current check cycle completion: {} %"
                                                         .format(checks_done_in_cycle_percent))
        self.stdscr.addstr(number_of_failing_tests+5, 0, "\n-----------------------------------\n")

        if 10 < len(self.node_logs):
            del self.node_logs[0]
        for idx, log in enumerate(self.node_logs):
            if 'info' == log[1]:
                color_pair_idx = 1
            elif 'warn' == log[1]:
                color_pair_idx = 2
            elif 'err' == log[1]:
                color_pair_idx = 3
            self.stdscr.addstr(log[0] + '\n', curses.color_pair(color_pair_idx))
        self.stdscr.refresh()

    def run_checks(self):
        self.checks_done_in_current_cycle = 0
        self.run_error_checks()
        self.run_warning_checks()
        rospy.sleep(1)

    def run_status_checks(self, check_type):
        if 'err' == check_type:
            checks_list = self.error_checks_list
            msg_type = 'ERROR'
        elif 'warn' == check_type:
            checks_list = self.warning_checks_list
            msg_type = 'WARN'
        else:
            raise ValueError("Wrong status check type")

        for check in checks_list:
            if check not in self.check_results:
                self.check_results[check] = True
            method_to_call = getattr(self.checks_class, check)
            try:
                return_value = method_to_call()
            except Exception as ex:
                self.node_logs.append(("[WARN] Check \'{}\' threw an exception: \'{}\'. Skipping..."
                                       .format(check, type(ex).__name__), 'warn'))
                self.checks_done_in_current_cycle += 1
                continue

            if isinstance(return_value, bool):
                result = return_value
                error_msg = None
            elif isinstance(return_value, tuple) and 2 == len(return_value):
                result = return_value[0]
                error_msg = return_value[1]
            else:
                self.node_logs.append(("[WARN] Wrong method result format for \'{}\'. "
                                       "Need either a bool or (bool, string) tuple!".format(check), 'warn'))
                continue

            if result != self.check_results[check]:
                if not result:
                    if error_msg is None:
                        error_log = ("[{}] Check \'{}\' failed!".format(msg_type, check), check_type)
                    else:
                        error_log = ("[{}] Check \'{}\' failed with message: {}"
                                     .format(msg_type, check, error_msg), check_type)
                    self.node_logs.append(error_log)
                else:
                    self.node_logs.append(("[INFO] Check \'{}\' passing now!".format(check), 'info'))

            if 'err' == check_type:
                self.check_results[check] = result

            if not result:
                self.demo_status = Status.ERROR

            self.checks_done_in_current_cycle += 1

        if False not in self.check_results.values():
            self.demo_status = Status.OK

    def run_error_checks(self):
        self.run_status_checks('err')

    def run_warning_checks(self):
        self.run_status_checks('warn')

    def get_cpu_usage(self):
            self.cpu_usage_per_core = psutil.cpu_percent(interval=1, percpu=True)
            self.cpu_usage = sum(self.cpu_usage_per_core)/len(self.cpu_usage_per_core)

    def clean_up(self):
        curses.echo()
        curses.nocbreak()
        curses.endwin()
        exit(0)


class TestChecksClass(object):
    def __init__(self):
        self.tmp = [0, 0, 0]

    def mock_check_robot_clear_from_collision(self):
        rospy.sleep(2)
        if self.tmp[0] != 1:
            self.tmp[0] = 1
            return False
        else:
            self.tmp[0] = 0
            return True

    def mock_check_if_arm_running(self):
        rospy.sleep(3)
        if self.tmp[1] != 0:
            self.tmp[1] = 0
            return False
        else:
            self.tmp[1] = 1
            return True

    def mock_check_if_hand_running(self):
        rospy.sleep(1)
        self.tmp[2] += 1
        if self.tmp[2] > 5 and self.tmp[2] < 10:
            return (False, "Hand not running!")
        else:
            return True


if __name__ == '__main__':
    rospy.init_node('mock_sr_teleop_watchdog')

    test_class = TestChecksClass()
    error_checks_list = ['mock_check_if_arm_running', 'mock_check_if_hand_running']
    warning_checks_list = ['mock_check_robot_clear_from_collision']

    teleop_watchdog = SrWatchdog(test_class, error_checks_list, warning_checks_list)
    shutdown_handler = ShutdownHandler(teleop_watchdog, 'clean_up()')
    teleop_watchdog.run()
    rospy.spin()
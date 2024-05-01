import ctypes
import threading
import time


class AlarmCounter:
    def __init__(self, bound):
        self.count = 0
        self.bound = bound
        self.lock = threading.Lock()

    def increment(self, value=1):
        with self.lock:
            self.count += value
    
    def judge(self, work_id):
        if self.count >= self.bound:
            # print(f"Counter of thread {work_id} reached the number of alarms {self.bound}.")
            return True
        return False


def terminate_threads(threads: list[threading.Thread]):
    for thread in threads:
        if thread.is_alive():
            thread_id = thread.ident
            # print(f"Timeout reached, terminating thread {thread_id}")
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id),
                                                         ctypes.py_object(SystemExit))
            if res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                print("Exception raise failure in kill timeout threads")


def get_early_stop_time(start_time: time.time, time_duration: int, hard_time_bound: bool):
    if time_duration is None or hard_time_bound is True:
        return None
    early_stop_time = start_time + time_duration * 60
    return early_stop_time

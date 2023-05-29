import sys
from multiprocessing import Process
from sys import excepthook


class MyProcess(Process):
    '''Process class with excepthook'''

    def run(self):
        try:
            super().run()
        except Exception:
            excepthook(*sys.exc_info())
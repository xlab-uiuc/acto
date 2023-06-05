from multiprocessing import Queue
from multiprocessing.sharedctypes import Value
from threading import Event, Thread


class ActoTimer(Thread):
    '''A resettable timer'''

    def __init__(self, interval, queue: Queue, queue_msg):
        Thread.__init__(self)
        self.interval = interval
        self.finished = Event()
        self.resetted = True
        self.queue = queue
        self.queue_msg = queue_msg

    def cancel(self):
        """Stop the timer if it hasn't finished yet"""
        self.finished.set()

    def run(self):
        while self.resetted:
            self.resetted = False
            self.finished.wait(self.interval)
        
        # notify the main thread using a queue
        
        try:    
            self.queue.put(self.queue_msg)
        except (ValueError, AssertionError): # the queue might have been closed. It is safe to do so because system has converged
            # above python 3.8, a valueError is raised while below 3.8, an AssertionError is raised
            pass
        self.finished.set()

    def reset(self):
        '''Reset the timer'''

        self.resetted = True
        self.finished.set()
        self.finished.clear()


if __name__ == '__main__':
    timer = ActoTimer(10)
    timer.start()
    timer.reset()
    timer.join()
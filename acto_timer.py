from threading import Thread, Event

class ActoTimer(Thread):
    '''A resettable timer'''
    
    def __init__(self, interval):
        Thread.__init__(self)
        self.interval = interval
        self.finished = Event()
        self.resetted = True
    
    def cancel(self):
        """Stop the timer if it hasn't finished yet"""
        self.finished.set()

    def run(self):
        while self.resetted:
            self.resetted = False
            self.finished.wait(self.interval)

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
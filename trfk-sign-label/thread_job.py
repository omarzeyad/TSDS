import threading


class ThreadJob(threading.Thread):
    def __init__(self, callback, event, interval):
        '''
        Runs the callback function after interval seconds.

        Args:
            callback -- callback function to invoke
            event -- external event for controlling the update operation
            interval -- time in seconds after which are required to fire the callback
        '''
        super(ThreadJob, self).__init__()
        self.callback = callback
        self.event = event
        self.interval = interval

        self.paused = True
        self.state = threading.Condition()

    def run(self):
        while not self.event.wait(self.interval):
            if not self.paused:
                self.callback()

    def pause(self):
        with self.state:
            self.paused = True

    def resume(self):
        with self.state:
            self.paused = False

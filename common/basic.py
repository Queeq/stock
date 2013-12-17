# Progress calculation and printing
class Progress(object):
    def __init__(self, maximum):
        self.maximum = maximum
        self.last_percent = 0
    def show(self, current):
        percent = round(current/self.maximum * 100)
        if percent > self.last_percent:
            self.last_percent = percent
            print ("%d%% complete \r" % percent, end="")
            if percent == 100:
                print ("")


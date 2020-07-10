# import math
# import numpy

from saleae.range_measurements import DigitalMeasurer
from saleae.data.timing import GraphTimeDelta

class DutyCycleMeasurer(DigitalMeasurer):
    supported_measurements = ["dutyCycle"]

    # Initialize your measurement extension here
    # Each measurement object will only be used once, so feel free to do all per-measurement initialization here
    def __init__(self, requested_measurements):
        super().__init__(requested_measurements)
        self.positive_duration = GraphTimeDelta(0.0)
        self.negative_duration = GraphTimeDelta(0.0)
        # (time, value)
        self.last_value = None
        self.pulse_count = 0
        self.last_pulse = 0

    # This method will be called one or more times per measurement with batches of data
    # data has the following interface
    #   * Iterate over to get transitions in the form of pairs of `Time`, Bitstate (`True` for high, `False` for low)
    # `Time` currently only allows taking a difference with another `Time`, to produce a `float` number of seconds
    def process_data(self, data):
        for t, bitstate in data:
            if self.last_value is None:
                self.last_value = (t, bitstate)
                continue
            if self.last_value[1] == bitstate:
                continue
            dt = t - self.last_value[0]
            self.pulse_count += 1
            self.last_pulse = dt
            if self.last_value[1]:
                # with open(r"C:\Users\tdkostk\Desktop\analyzer.txt", 'a') as f:
                #     if self.positive_duration is not None:
                #         f.write("\npositive_duration = %g\n" % float(
                #             self.positive_duration))
                self.positive_duration += dt
                    # f.write("dt = %g\n" % float(dt))
                    # f.write("positive_duration = %g\n" % float(
                    #     self.positive_duration))
                    # f.write("float(dt) = %g\n" % float(dt))
                    # f.write("float(None + dt) = %g\n" % float(None + dt))
            else:
                self.negative_duration += dt
            self.last_value = (t, bitstate)

    # This method is called after all the relevant data has been passed to `process_data`
    # It returns a dictionary of the request_measurements values
    def measure(self):
        # if odd number of pulses, subtract the last one
        if self.pulse_count % 2 != 0:
            if self.last_value[1]:
                self.negative_duration -= self.last_pulse
            else:
                self.positive_duration -= self.last_pulse
            self.pulse_count -= 1
        total_duration = float(self.positive_duration + self.negative_duration)
        # with open(r"C:\Users\tdkostk\Desktop\analyzer.txt", 'a') as f:
        #     f.write("positive_duration = %g\n" % float(self.positive_duration))
        #     f.write("negative_duration = %g\n" % float(self.negative_duration))
        #     f.write("total_duration = %g\n" % float(total_duration))
        if float(self.positive_duration) * float(self.negative_duration) == 0:
            #value = "None"
            value = None
            #value = 0.0
        else:
            # self.positive_duration -= GraphTimeDelta(0.005)
            # self.negative_duration -= GraphTimeDelta(0.005)
            # total_duration = self.positive_duration + self.negative_duration
            #value = "%.3f%%" % (float(self.positive_duration) * 100 / float(total_duration))
            value = float(self.positive_duration) * 100 / float(total_duration)
        if value is None:
            return {}
        else:
            return {"dutyCycle": value}


import numpy as np
import math

class Gauges():
    def __init__(self, *args, **kwargs):

        self.prevackoeff = np.array([1.1558, -7.5993])
        self.kaltkathodkoeff = np.array([1.3091, -18.6852])

    def vorvakuum(self, volt) -> float:

        liste = [a*volt**i for i, a in enumerate(self.prevackoeff[::-1])]
        return '%.2E' % math.exp(np.sum(liste))

    def kaltkathode(self, volt) -> float:

        liste = [a*volt**i for i, a in enumerate(self.kaltkathodkoeff[::-1])]
        return '%.2E' % math.exp(np.sum(liste))


# balzers = Gauges()
# print(balzers.vorvakuum(3.3))
# print(balzers.kaltkathode(3))


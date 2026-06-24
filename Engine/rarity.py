from enum import Enum
from defines import *

from stats import Stat

class Rarities(Enum):
    NORMAL = 1        # No Mods       # 70 in 100
    MAGIC = 2          # 0-1 prefix and suffix Mod         # 50 in 100
    RARE = 3         # 1-3 prefix and suffix Mods      # 5 in 100
    UNIQUE = 4            # 2-4 Mods      # 1 in 100




class Rarity:
    def __init__(self):
        self.rarity = None
        self.stat = Stat()
        self.stat.setMaximumStat(100)
        self.stat.setMinimumStat(0)

        self.stat.calculate()

    def reprJSON(self):
        reprDict = dict(rarity=self.rarity.name)
        reprDict.update(dict(
            stats=self.stat.reprJSON()
        ))

        return reprDict

    def roll(self):
        
        if chanceRoll(round(0.1 + self.stat.totalStat, ROUND_DECIMALS)):
            self.rarity = Rarities.UNIQUE
        elif chanceRoll(round(1 + self.stat.totalStat, ROUND_DECIMALS)):
            self.rarity = Rarities.RARE
        elif chanceRoll(round(5 + self.stat.totalStat, ROUND_DECIMALS)):
            self.rarity = Rarities.MAGIC
        else:
            self.rarity = Rarities.NORMAL




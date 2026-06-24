from defines import *
from stats import Stats
from equipments import Equipments
from inventory import Inventory

class BaseCharacter:

    def __init__(self, name):
        self.name = name
        self.equipments = Equipments()
        self.stats = Stats()
        self.level = 1

        self.alive = True

        self.setBaseStats()
        self.stats.calculate()

        self.restore()

    def reprJSON(self):
       return dict(
            name=self.name,
            level=self.level,
            alive=self.alive,
            equipments=self.equipments.reprJSON(),
            stats=self.stats.reprJSON()
       ) 

    def restore(self):
        self.stats.life.currentStat = self.stats.life.totalStat
        self.stats.mana.currentStat = self.stats.mana.totalStat
        self.stats.energyShield.currentStat = self.stats.energyShield.totalStat

    def regenerate(self):   
        self.stats.life.regenerate()
        if self.stats.life.currentStat <= 0:
            self.alive = False
        else:
            self.alive = True
        self.stats.mana.regenerate()
        self.stats.energyShield.regenerate()

    def setBaseStats(self):
        self.stats.coldResistance.setMaximumStat(75)
        self.stats.fireResistance.setMaximumStat(75)
        self.stats.lightningResistance.setMaximumStat(75)
        self.stats.choasResistance.setMaximumStat(75)

    def recalibrate(self):
            
        self.stats.normalize() # Sets character stats to default values 
        self.setBaseStats() # Sets character stats based on character specific attributes 
        self.joinEquipmentStats() # joins equipmentstats to character stats
        self.stats.calculate() # calculates the result values for character stat
        self.restore()
    
    def update(self):
        if self.stats.life.currentStat and self.stats.life.currentStat <= 0:
            self.alive = False
            return False


        self.regenerate()

    def joinEquipmentStats(self):
        for equipment in self.equipments.__dict__:
            if self.equipments.__dict__[equipment]:
                self.stats.joinStats(self.equipments.__dict__[equipment].stats)

    def equip(self, equipment):
        return self.equipments.equip(equipment)

    def unEquip(self, slot):
        pass

    def engage(self, target):
        if not isinstance(target, __class__): return False

        # calculate accuracy agains targets evasion 


        # Physical Damage -> Fire Damage -> Cold Damage -> Lighting Damage -> Chaos Damage

        # Physical Damage 


       

        physicalDamage = self.stats.calculateCritModifier(self.stats.physicalDamage.totalStat)
        

        print(target.stats.life.currentStat)
        print(physicalDamage)
        target.stats.life.drain(physicalDamage)
        print(target.stats.life.currentStat)

        return True

class Monster(BaseCharacter):
    def __init__(self, name):
        super().__init__(name)

class Character(BaseCharacter):

    def __init__(self, name):
        super().__init__(name)

        self.inventory = Inventory()
    
    def setBaseStats(self):
        super().setBaseStats()

        self.stats.life.addPositiveStat(50)
        self.stats.life.regenerateStat.addPositiveStat(10)
        self.stats.mana.addPositiveStat(40)
        self.stats.mana.regenerateStat.addPositiveStat(10)
        self.stats.evasion.addPositiveStat(53)

    def reprJSON(self):
        reprDict = super().reprJSON()
        reprDict.update(dict(inventory=self.inventory))
        return reprDict
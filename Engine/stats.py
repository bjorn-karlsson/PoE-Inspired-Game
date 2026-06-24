from defines import *

class Stat():
    def __init__(self):

        self.normalize()
        self.totalMaximum = None
        self.totalMinimum = None
    
    def normalize(self):
        self.totalStat = 0.0

        self.positiveStat = 0.0
        self.negativeStat = 0.0

        self.increasedStat = 0.0
        self.reducedStat = 0.0

        self.moreStat = 1.0
        self.lessStat = 1.0

    def reprJSON(self):
        reprDict = dict()
        if(self.totalStat != 0):
            reprDict.update(totalStat=self.totalStat)
        if(self.positiveStat != 0):
            reprDict.update(positiveStat=self.positiveStat)
        if(self.negativeStat != 0):
            reprDict.update(negativeStat=self.negativeStat)
        if(self.increasedStat != 0):
            reprDict.update(increasedStat=self.increasedStat)
        if(self.reducedStat != 0):
            reprDict.update(reducedStat=self.reducedStat)
        if(self.moreStat != 1):
            reprDict.update(moreStat=self.moreStat)
        if(self.lessStat != 1):
            reprDict.update(lessStat=self.lessStat)
        if(isinstance(self.totalMaximum, int)):
            reprDict.update(totalMaximum=self.totalMaximum)
        if(isinstance(self.totalMinimum, int)):
            reprDict.update(totalMinimum=self.totalMinimum)

        return reprDict

    def roundTotalValue(self):
        self.totalStat = round(self.totalStat, ROUND_DECIMALS)
    

    def addPositiveStat(self, addedNumericStat: int) :
        self.positiveStat += addedNumericStat
    
    def removePositiveStat(self, removedNumericStat: int) :
        self.positiveStat -= removedNumericStat

    def addNegativeStat(self, addedNumericStat: int) :
        self.negativeStat += addedNumericStat
    
    def removeNegativeStat(self, removedNumericStat: int) :
        self.negativeStat -= removedNumericStat
    

    def addReducedStat(self ,percentageStat: int):
        self.reducedStat += percentageStat
    
    def addIncreasedStat(self, percentageStat: int):
        self.increasedStat += percentageStat

    def removeReducedStat(self, percentageStat: int):
        self.reducedStat -= percentageStat
    
    def removeIncreasedStat(self, percentageStat: int):
        self.increasedStat -= percentageStat
    


    def addMoreStat(self, multiplierStat: int):
        self.moreStat *= 1 + (multiplierStat / 100)
    
    def removeMoreStat(self, multiplierStat: int):
        self.moreStat /= 1 + (multiplierStat / 100)

    def addLessStat(self, multiplierStat: int):
        self.lessStat *= 1 + (multiplierStat / 100)
    
    def removeLessStat(self, multiplierStat: int):
        self.lessStat /= 1 + (multiplierStat / 100)


    
    def setMaximumStat(self, maximumStat: int):
        self.totalMaximum = maximumStat

    def setMinimumStat(self, minimumStat: int):
        self.totalMinimum = minimumStat

    def calculate(self, debugSum = False):
        sum = round((self.positiveStat - self.negativeStat) * (1 + (self.increasedStat / 100) - (self.reducedStat / 100)) * self.moreStat / self.lessStat, ROUND_DECIMALS)
        
        if(debugSum):
            print(sum)

        if(self.totalMaximum and sum >= self.totalMaximum):
            self.totalStat = self.totalMaximum
        elif(self.totalMinimum and sum <= self.totalMinimum):
            self.totalStat = self.totalMinimum
        else:
            self.totalStat = sum
    
    def joinStat(self, addedStat: 'Stat'):
        self.positiveStat  += addedStat.positiveStat
        self.negativeStat  += addedStat.negativeStat
        self.increasedStat += addedStat.increasedStat
        self.reducedStat   += addedStat.reducedStat
        self.moreStat      *= addedStat.moreStat
        self.lessStat      *= addedStat.lessStat
    
    def disconnectStat(self, removedStat: 'Stat'):
        self.positiveStat  -= removedStat.positiveStat
        self.negativeStat  -= removedStat.negativeStat
        self.increasedStat -= removedStat.increasedStat
        self.reducedStat   -= removedStat.reducedStat
        self.moreStat      /= removedStat.moreStat
        self.lessStat      /= removedStat.lessStat

class AttributeStat:
    def __init__(self):
        self.strength = Stat()
        self.dexterity = Stat()
        self.intelligence = Stat()

    def reprJSON(self):
        reprDict = dict()
        for key, val in self.__dict__.items():
            reprVal = val.reprJSON()
            if (len(reprVal) == 0):
                continue
                
            string = '{"' + key + '": ' + json.dumps(reprVal) + '}'
            reprDict.update(json.loads(string))
           
        return reprDict

    
    def addPositiveStrength(self, value: int): self.strength.addPositiveStat(value)
    def addNegativeStrength(self, value: int): self.strength.addNegativeStat(value)
    def addIncreasedStrength(self, value: int): self.strength.addIncreasedStat(value)
    def addReducedStrength(self, value: int): self.strength.addReducedStat(value)
    def addMoreStrength(self, value: int): self.strength.addMoreStat(value)
    def addLessStrength(self, value: int): self.strength.addLessStat(value)

    def removePositiveStrength(self, value: int): self.strength.removePositiveStat(value)
    def removeNegativeStrength(self, value: int): self.strength.removeNegativeStat(value)
    def removeIncreasedStrength(self, value: int): self.strength.removeIncreasedStat(value)
    def removeReducedStrength(self, value: int): self.strength.removeReducedStat(value)
    def removeMoreStrength(self, value: int): self.strength.removeMoreStat(value)
    def removeLessStrength(self, value: int): self.strength.removeLessStat(value)


    def addPositiveDexterity(self, value: int): self.dexterity.addPositiveStat(value)
    def addNegativeDexterity(self, value: int): self.dexterity.addNegativeStat(value)
    def addIncreasedDexterity(self, value: int): self.dexterity.addIncreasedStat(value)
    def addReducedDexterity(self, value: int): self.dexterity.addReducedStat(value)
    def addMoreDexterity(self, value: int): self.dexterity.addMoreStat(value)
    def addLessDexterity(self, value: int): self.dexterity.addLessStat(value)

    def removePositiveDexterity(self, value: int): self.dexterity.removePositiveStat(value)
    def removeNegativeDexterity(self, value: int): self.dexterity.removeNegativeStat(value)
    def removeIncreasedDexterity(self, value: int): self.dexterity.removeIncreasedStat(value)
    def removeReducedDexterity(self, value: int): self.dexterity.removeReducedStat(value)
    def removeMoreDexterity(self, value: int): self.dexterity.removeMoreStat(value)
    def removeLessDexterity(self, value: int): self.dexterity.removeLessStat(value)


    def addPositiveIntelligence(self, value: int): self.intelligence.addPositiveStat(value)
    def addNegativeIntelligence(self, value: int): self.intelligence.addNegativeStat(value)
    def addIncreasedIntelligence(self, value: int): self.intelligence.addIncreasedStat(value)
    def addReducedIntelligence(self, value: int): self.intelligence.addReducedStat(value)
    def addMoreIntelligence(self, value: int): self.intelligence.addMoreStat(value)
    def addLessIntelligence(self, value: int): self.intelligence.addLessStat(value) 

    def removePositiveIntelligence(self, value: int): self.intelligence.removePositiveStat(value)
    def removeNegativeIntelligence(self, value: int): self.intelligence.removeNegativeStat(value)
    def removeIncreasedIntelligence(self, value: int): self.intelligence.removeIncreasedStat(value)
    def removeReducedIntelligence(self, value: int): self.intelligence.removeReducedStat(value)
    def removeMoreIntelligence(self, value: int): self.intelligence.removeMoreStat(value)
    def removeLessIntelligence(self, value: int): self.intelligence.removeLessStat(value) 
    

    def addPositiveToAllAttributes(self, value: int): 
        self.addPositiveStrength(value)
        self.addPositiveDexterity(value)
        self.addPositiveIntelligence(value)
    def addNegativeToAllAttributes(self, value: int): 
        self.addNegativeStrength(value)
        self.addNegativeDexterity(value)
        self.addNegativeIntelligence(value)
    def addIncreasedToAllAttributes(self, value: int): 
        self.addIncreasedStrength(value)
        self.addIncreasedDexterity(value)
        self.addIncreasedIntelligence(value)
    def addReducedToAllAttributes(self, value: int): 
        self.addReducedStrength(value)
        self.addReducedDexterity(value)
        self.addReducedIntelligence(value)
    def addMoreToAllAttributes(self, value: int): 
        self.addMoreStrength(value)
        self.addMoreDexterity(value)
        self.addMoreIntelligence(value)
    def addLessToAllAttributes(self, value: int): 
        self.addLessStrength(value)
        self.addLessDexterity(value)
        self.addLessIntelligence(value)

    def removePositiveToAllAttributes(self, value: int): 
        self.removePositiveStrength(value)
        self.removePositiveDexterity(value)
        self.removePositiveIntelligence(value)
    def removeNegativeToAllAttributes(self, value: int): 
        self.removeNegativeStrength(value)
        self.removeNegativeDexterity(value)
        self.removeNegativeIntelligence(value)
    def removeIncreasedToAllAttributes(self, value: int): 
        self.removeIncreasedStrength(value)
        self.removeIncreasedDexterity(value)
        self.removeIncreasedIntelligence(value)
    def removeReducedToAllAttributes(self, value: int): 
        self.removeReducedStrength(value)
        self.removeReducedDexterity(value)
        self.removeReducedIntelligence(value)
    def removeMoreToAllAttributes(self, value: int): 
        self.removeMoreStrength(value)
        self.removeMoreDexterity(value)
        self.removeMoreIntelligence(value)
    def removeLessToAllAttributes(self, value: int): 
        self.removeLessStrength(value)
        self.removeLessDexterity(value)
        self.removeLessIntelligence(value)

class PoolStat(Stat):

    def __init__(self):
        super().__init__()
        self.currentStat = None
        self.regenerateStat = Stat()

    def reprJSON(self):
        reprDict = super().reprJSON()
        if(self.currentStat):
            reprDict.update(currentStat=self.currentStat)

        if(len(self.regenerateStat.reprJSON()) != 0):
            reprDict.update(dict(regenerateStat=self.regenerateStat.reprJSON()))

        return reprDict

    def calculate(self):
        self.regenerateStat.calculate()
        super().calculate()

    def regenerate(self):
        newCurrentStat = self.currentStat + self.regenerateStat.totalStat
        if newCurrentStat >= self.totalStat:
            self.currentStat = self.totalStat
        elif newCurrentStat <= 0:
            self.currentStat = 0.0
        else:
            self.currentStat = newCurrentStat

    def drain(self, amount):
        sum = round(self.currentStat - amount, ROUND_DECIMALS)
        if(sum < 0):
            sum = 0.0
        self.currentStat = sum


class LifeStat (PoolStat): 
    def __init__(self): super().__init__()
class EnergyShieldStat (PoolStat):
    def __init__(self): super().__init__()
class ManaStat (PoolStat):
    def __init__(self): super().__init__()

class EvasionStat (Stat): 
    def __init__(self): super().__init__()
class ArmourStat (Stat): 
    def __init__(self): super().__init__()

class FireResistanceStat (Stat): 
    def __init__(self): super().__init__()
class ColdResistanceStat (Stat): 
    def __init__(self): super().__init__()
class LightningResistanceStat (Stat): 
    def __init__(self): super().__init__()
class ChaosResistanceStat (Stat): 
    def __init__(self): super().__init__()

class AccuracyStat (Stat): 
    def __init__(self): super().__init__()
class PhysicalDamageStat (Stat): 
    def __init__(self): super().__init__()
class RangedDamageStat (Stat): 
    def __init__(self): super().__init__()
class SpellDamageStat (Stat): 
    def __init__(self): super().__init__()
class FireDamageStat (Stat): 
    def __init__(self): super().__init__()
class ColdDamageStat (Stat): 
    def __init__(self): super().__init__()
class LightningDamageStat (Stat): 
    def __init__(self): super().__init__()
class ChaosDamageStat (Stat): 
    def __init__(self): super().__init__()

class AttackSpeedStat (Stat): 
    def __init__(self): super().__init__()
class CastSpeedStat (Stat): 
    def __init__(self): super().__init__()

class CriticalStrikeChanceStat (Stat): 
    def __init__(self): super().__init__()
    def roll(self) -> bool:
        return chanceRoll(self.totalStat)


class CriticalStrikeDamageStat (Stat): 
    def __init__(self): super().__init__()

    def calculateDamage(self, currentDamage) -> float:
        return round(currentDamage * ((self.totalStat + 100) / 100), ROUND_DECIMALS)



class Stats:
    def __init__(self):
        self.attributes = AttributeStat()
        
        self.life = LifeStat()
        self.mana = ManaStat()
        self.energyShield = EnergyShieldStat()
        self.evasion = EvasionStat()
        self.armour = ArmourStat()
        self.fireResistance = FireResistanceStat()
        self.coldResistance = ColdResistanceStat()
        self.lightningResistance = LightningResistanceStat()
        self.choasResistance = ChaosResistanceStat()
        self.accuracy = AccuracyStat()
        self.physicalDamage = PhysicalDamageStat()

        self.rangedDamage = RangedDamageStat()
        self.spellDamage = SpellDamageStat()
        self.fireDamage = FireDamageStat()
        self.coldDamage = ColdDamageStat()
        self.lightningDamage = LightningDamageStat()
        self.chaosDamage = ChaosDamageStat()

        self.attackSpeed = AttackSpeedStat()
        self.castSpeed = CastSpeedStat()

        self.criticalStrikeChance = CriticalStrikeChanceStat()
        self.criticalStrikeDamage = CriticalStrikeDamageStat()

    def reprJSON(self):

        reprDict = dict()
        for key, val in self.__dict__.items():
            reprVal = val.reprJSON()
            if (len(reprVal) == 0):
                continue
                
            string = '{"' + key + '": ' + json.dumps(reprVal) + '}'
            reprDict.update(json.loads(string))
           
        return reprDict


    def calculate(self):
        
        self.attributes.strength.calculate()
        self.attributes.dexterity.calculate()
        self.attributes.intelligence.calculate()

        self.life.addPositiveStat(self.attributes.strength.totalStat / 2)
        self.life.calculate()
        

        self.mana.addPositiveStat(self.attributes.intelligence.totalStat / 2)
        self.mana.calculate()
        
        
        self.energyShield.addIncreasedStat(self.attributes.intelligence.totalStat / 5)
        self.energyShield.calculate()

        self.physicalDamage.addPositiveStat(self.attributes.strength.totalStat / 2)
        self.physicalDamage.calculate()

        self.rangedDamage.addIncreasedStat(self.attributes.dexterity.totalStat / 5)
        self.rangedDamage.calculate()

        self.spellDamage.addIncreasedStat(self.attributes.intelligence.totalStat / 5)
        self.spellDamage.calculate()

        self.accuracy.addPositiveStat(self.attributes.dexterity.totalStat * 2)
        self.accuracy.calculate()

        self.evasion.addPositiveStat(self.attributes.dexterity.totalStat / 2)
        self.evasion.calculate()

        self.armour.calculate()


        
        self.fireDamage.calculate()
        self.coldDamage.calculate()
        self.lightningDamage.calculate()
        self.chaosDamage.calculate()

        self.attackSpeed.calculate()
        self.castSpeed.calculate()

        self.fireResistance.calculate()
        self.coldResistance.calculate()
        self.lightningResistance.calculate()
        self.choasResistance.calculate()

        self.criticalStrikeChance.calculate()
        self.criticalStrikeDamage.calculate()
    
    def joinSingleStat(self, addedStat: Stat):
        if isinstance(addedStat, Stat):
            for k in self.__dict__:
                if(self.__dict__[k].__class__.__name__ == addedStat.__class__.__name__):
                    self.__dict__[k].joinStat(addedStat)
                    break
                
        elif(isinstance(addedStat, AttributeStat)):
            self.attributes.strength.joinStat(addedStat.strength)
            self.attributes.dexterity.joinStat(addedStat.dexterity)
            self.attributes.intelligence.joinStat(addedStat.intelligence)
    
    def disconnectSingleStat(self, removedStat: Stat):
        if isinstance(removedStat, Stat):
            for k in self.__dict__:
                if(self.__dict__[k].__class__.__name__ == removedStat.__class__.__name__):
                    self.__dict__[k].disconnectStat(removedStat)
                    break

        elif(isinstance(removedStat, AttributeStat)):
            self.attributes.strength.disconnectStat(removedStat.strength)
            self.attributes.dexterity.disconnectStat(removedStat.dexterity)
            self.attributes.intelligence.disconnectStat(removedStat.intelligence)

    def joinStats(self, addedStats: 'Stats'):

        self.attributes.strength.joinStat(addedStats.attributes.strength)
        self.attributes.dexterity.joinStat(addedStats.attributes.dexterity)
        self.attributes.intelligence.joinStat(addedStats.attributes.strength)

        for key, val in self.__dict__.items():
            
            if(isinstance(val, AttributeStat)):
                continue

            if(isinstance(val, PoolStat)):
                self.__dict__[key].joinStat(addedStats.__dict__[key])
                self.__dict__[key].regenerateStat.joinStat(addedStats.__dict__[key].regenerateStat)
                continue
            
            self.__dict__[key].joinStat(addedStats.__dict__[key])


    def disconnectStats(self, removedStats: 'Stats'):

        self.attributes.strength.disconnectStat(removedStats.attributes.strength)
        self.attributes.dexterity.disconnectStat(removedStats.attributes.dexterity)
        self.attributes.intelligence.disconnectStat(removedStats.attributes.strength)

        for key, val in self.__dict__.items():
            
            if(isinstance(val, AttributeStat)):
                continue

            if(isinstance(val, PoolStat)):
                self.__dict__[key].disconnectStat(removedStats.__dict__[key])
                self.__dict__[key].regenerateStat.disconnectStat(removedStats.__dict__[key].regenerateStat)
                continue
            
            self.__dict__[key].disconnectStat(removedStats.__dict__[key])

    def normalize(self):

        self.attributes.strength.normalize()
        self.attributes.dexterity.normalize()
        self.attributes.intelligence.normalize()

        for key, val in self.__dict__.items():
            
            if(isinstance(val, AttributeStat)):
                continue

            if(isinstance(val, PoolStat)):
                self.__dict__[key].normalize()
                self.__dict__[key].regenerateStat.normalize()
                continue
            
            self.__dict__[key].normalize()

    def calculateCritModifier(self, statValue: float) -> float:
      
        if self.criticalStrikeChance.roll():
            statValue = self.criticalStrikeDamage.calculateDamage(statValue)

        return statValue
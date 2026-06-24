from defines import *
from stats import Stats
from rarity import *
from modifiers import *

class Equipment():

    def get(name):
        return BASEITEMSDATA[name]

    def __init__(self):
        self.domain = None
        self.dropLevel = None
        
        self.implicits = []
        self.prefixes = []
        self.suffixes = []

        self.inventoryHeight = None
        self.inventoryWidth = None

        self.itemClass = None
        self.name = None
    
        self.properties = {}
        #releaseState 
        self.requirements = {}
        
        self.tags = []
        self.rarity = Rarity()
        #visualIdentity

        self.stats = Stats()

        #self.rollEquipment()


    def reprJSON(self):
        return self.__dict__

    def rollEquipment(self):
        self.rollRarity()
        self.rollModifiers()
        

    def generateEquipment(domain = 'item', dropLevel = 100, itemClass = None):
        
        newEquipment = Equipment()

        while True:
            selectedItemIndex = round(random.random() * len(BASEITEMSDATA) - 1)
            selectedItemName = list(BASEITEMSDATA.keys())[selectedItemIndex]
            selectedItem = Equipment.get(selectedItemName)

            if selectedItem.get('domain') != domain:
                continue

            if selectedItem.get('drop_level') > dropLevel:
                continue

            if itemClass and selectedItem.get('item_class') != itemClass:
                continue
               

            break
        
        
        newEquipment.domain = selectedItem.get('domain')
        newEquipment.dropLevel = selectedItem.get('drop_level')
        newEquipment.inventoryHeight = selectedItem.get('inventory_height')
        newEquipment.inventoryWidth = selectedItem.get('inventory_width')

        newEquipment.itemClass = selectedItem.get('item_class')
        newEquipment.name = selectedItem.get('name')
        newEquipment.properties = selectedItem.get('properties')
        newEquipment.requirements = selectedItem.get('requirements')
        
        newEquipment.tags = selectedItem.get('tags')


        if len(selectedItem.get('implicits')) > 0:
            implicits = []
            for implicitIndex in range(len(selectedItem.get('implicits'))):
                implicits.append(selectedItem['implicits'][implicitIndex])
                #implicits.append(Modifier.get(selectedItem['implicits'][implicitIndex]))
                
            newEquipment.implicits = implicits

        
        newEquipment.rollRarity()
        newEquipment.rollModifiers()

        return newEquipment

    def setRarity(self, Rarity : Rarities):
        self.rarity.rarity = Rarity

    def rollRarity(self):
        self.rarity.roll()

    def setModifiers(self, modifiers):
        pass

    def rollModifiers(self):

        prefixes = 0
        suffixes = 0
        
        if self.rarity.rarity == Rarities.NORMAL or self.rarity.rarity == Rarities.UNIQUE:
            return False

        elif self.rarity.rarity == Rarities.MAGIC: 
            while (prefixes + suffixes) < 1:
                prefixes = round(random.random() * 1)
                suffixes = round(random.random() * 1)

        elif self.rarity.rarity == Rarities.RARE: 
            while (prefixes + suffixes) < 3:
                prefixes = round(random.random() * 3)
                suffixes = round(random.random() * 3)





        prefixMods = []
        suffixMods = []
        
        groups = set()

        for itemTag in self.tags:
            
            for modName, modData in MODIFIERSDATA.items():
                if modData['domain'] != 'item':
                    continue

                if modData['generation_type'] != 'prefix' and modData['generation_type'] != 'suffix':
                    continue
                

                if modData['required_level'] > self.dropLevel:
                    continue
                
                groups.add(modData['groups'][0]) 

                spawnWeights = modData['spawn_weights']
                for weight in spawnWeights:
                    if itemTag == weight['tag'] and weight['weight'] != 0:
                        weight.update({'modType' : modData['generation_type'], 'mod' : modName})
                    
                        if modData['generation_type'] == 'prefix':
                            prefixMods.append(weight)
                        elif modData['generation_type'] == 'suffix':
                            suffixMods.append(weight)
            

        
        
        prefixModWeights = {item['mod']: item['weight'] for  item in prefixMods}
        prefixModTotalWeight = sum(prefixModWeights.values())

        suffixModWeights = {item['mod']: item['weight'] for  item in suffixMods}
        suffixModTotalWeight = sum(suffixModWeights.values())


        
        for index in range(prefixes):
            randomNum = random.uniform(0, prefixModTotalWeight)
            for mod, weight in prefixModWeights.items():
                if randomNum - weight < 0:
                    self.prefixes.append(Modifier.get(mod))
                    break
                randomNum -= weight

        for index in range(suffixes):
            randomNum = random.uniform(0, suffixModTotalWeight)
            for mod, weight in suffixModWeights.items():
                if randomNum - weight < 0:
                    self.suffixes.append(Modifier.get(mod))
                    break
                randomNum -= weight

        printAsJson(list(groups))




    def setTags(self, tags):
        self.tags = tags

    def setStats(self, stats : Stats):
        self.stats = stats

    def calculateStats(self):
        pass



class Weapon(Equipment): 
    pass

class Armour(Equipment): 
    pass
class Helmet(Armour):
    pass
class BodyArmour(Armour):
    pass
class Gloves(Armour):
    pass
class Boots(Armour):
    pass

class Accessories(Equipment): 
    pass
class Amulet(Accessories):
    pass
class Ring(Accessories):
    pass
class Belt(Accessories):
    pass

class Equipments():
    def __init__(self):
        self.weapon = None
        self.helmet = None
        self.bodyArmour = None
        self.gloves = None
        self.boots = None
        self.amulet = None
        self.ring1 = None
        self.ring2 = None
        self.belt = None

    def reprJSON(self):
        reprDict = self.__dict__
        return reprDict
        #for key, val in self.__dict__.items():
        #    if(not val):
        #        continue
        #    string = '{"' + key + '": ' + json.dumps(val.reprJSON()) + '}'
        #    reprDict.update(json.loads(string))

        

    def equip(self, newEquipment: Equipment):
        replacedEquipment = None
        if isinstance(newEquipment, Weapon):  
            replacedEquipment = self.weapon
            self.weapon = newEquipment
        elif isinstance(newEquipment, Helmet):
            replacedEquipment = self.helmet
            self.helmet = newEquipment
        elif isinstance(newEquipment, BodyArmour):
            replacedEquipment = self.bodyArmour
            self.bodyArmour = newEquipment
        elif isinstance(newEquipment, Gloves):
            replacedEquipment = self.gloves
            self.gloves = newEquipment
        elif isinstance(newEquipment, Boots):
            replacedEquipment = self.boots
            self.boots = newEquipment
        elif isinstance(newEquipment, Amulet):
            replacedEquipment = self.amulet
            self.amulet = newEquipment
        elif isinstance(newEquipment, Belt):
            replacedEquipment = self.belt
            self.belt = newEquipment 
        elif isinstance(newEquipment, Ring):
            pass
     
        return replacedEquipment


from defines import * 
from stats import *
from equipments import *
from characters import *
from rarity import *







monster = Monster("Monster")
character = Character('Character')

weaponStats = Stats()
hemletStats1 = Stats()
glovesStats1 = Stats()

weaponStats.physicalDamage.addPositiveStat(10)
hemletStats1.life.addPositiveStat(40)

hemletStats1.attributes.addPositiveToAllAttributes(10)

glovesStats1.life.regenerateStat.addPositiveStat(20)

#weapon = Equipment.generateEquipment()
#weapon.setStats(weaponStats)


while True:
    uniqueHelmet = Equipment.generateEquipment()
    if uniqueHelmet.rarity.rarity == Rarities.RARE or uniqueHelmet.rarity.rarity == Rarities.RARE:
        printAsJson(uniqueHelmet)
        break
#printAsJson(uniqueHelmet)
exit()
helmet1 = Helmet()
helmet1.setStats(hemletStats1)

gloves1 = Gloves()
gloves1.setStats(glovesStats1)


character.equip(weapon)
character.equip(helmet1)
character.equip(gloves1)
character.recalibrate()


monster.equip(weapon)
monster.equip(helmet1)
monster.equip(gloves1)
monster.recalibrate()


#printAsJson(weapon)


#character.engage(monster)
#printAsJson(monster)


#character.engage(monster)
#printAsJson(monster)


exit()

with open('data/base_items.json', 'r') as f:
    itemDatas = json.loads(f.read())

with open('data/mods.json', 'r') as f:
    modsDatas = json.loads(f.read())



for item in itemDatas:
    for implicitIndex in range(len(itemDatas[item]['implicits'])):
        itemDatas[item]['implicits'][implicitIndex] = modsDatas[itemDatas[item]['implicits'][implicitIndex]]

    

for mod in modsDatas:
    if modsDatas[mod]['domain'] != 'item':
        continue

    

printAsJson(itemDatas) 
    




#printAsJson(data)

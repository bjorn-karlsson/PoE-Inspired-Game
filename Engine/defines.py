import os
import json
#from random import random
import random

ROUND_DECIMALS = 1

BASEITEMSFILE =  'data/base_items.json'
MODIFIERSFILE =  'data/mods.json'
TAGSFILE = 'data/tags.json'

with open(BASEITEMSFILE) as f:
    print('Loading base items...')
    BASEITEMSDATA = json.loads(f.read())

with open(MODIFIERSFILE) as f:
    print('Loading mods...')
    MODIFIERSDATA = json.loads(f.read())

with open(TAGSFILE) as f:
    print('Loading tags...')
    TAGSDATA = json.loads(f.read())



class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj,'reprJSON'):
            return obj.reprJSON()
        else:
            return json.JSONEncoder.default(self, obj)


class Null:
    def reprJSON(self):
        return None
    


def printAsJson(obj):
    print(json.dumps(obj, cls=ComplexEncoder, indent=4))




def chanceRoll(odds) -> bool:
    if odds < round(random.random() * 100, ROUND_DECIMALS):
            return False
    return True




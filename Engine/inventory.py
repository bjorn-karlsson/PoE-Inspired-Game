from equipments import *

class Inventory:


    def __init__(self):
        self.items = []
        self.size = 32
        self.currentSize = 0

    def reprJSON(self):
       return dict(items = self.items)
       

    def addItem(self, item : Equipment):
        if self.currentSize + item.inventorySize > self.size:
            return False
        
        self.items.append(item)
        self.currentSize += item.inventorySize



    def getItemByIndex(self, index):
        if item := isinstance(self.items[index], Equipment):
            self.currentSize -= item.inventorySize
            return self.items.pop(index)     

    def getItemByName(self, name):
        index = 0
        
        while index < len(self.items):
            if self.items[index] == name:
                self.currentSize -= self.items[index].inventorySize
                return self.items.pop(index)     
            index += 1

    def deleteItemByIndex(self, index):
        if item := isinstance(self.items[index], Equipment):
            self.currentSize -= item.inventorySize
            self.items.pop(index)
            return True
        
    

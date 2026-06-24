"""A simple, size-limited inventory of items."""

from .items import Item


class Inventory:
    def __init__(self, size=32):
        self.items = []
        self.size = size

    @property
    def currentSize(self):
        return sum(item.inventorySize for item in self.items)

    def reprJSON(self):
        return {"size": self.size, "used": self.currentSize, "items": self.items}

    def addItem(self, item: Item) -> bool:
        if self.currentSize + item.inventorySize > self.size:
            return False
        self.items.append(item)
        return True

    def removeItemByIndex(self, index) -> Item:
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def findItemByName(self, name) -> int:
        for index, item in enumerate(self.items):
            if item.name == name:
                return index
        return -1

    def removeItemByName(self, name) -> Item:
        index = self.findItemByName(name)
        return self.removeItemByIndex(index) if index >= 0 else None

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

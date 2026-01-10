"""
Import presets for automatic card naming during deck imports
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Standard Tarot deck (78 cards)
STANDARD_TAROT = {
    # Major Arcana (0-21)
    "00": "The Fool", "0": "The Fool", "fool": "The Fool",
    "01": "The Magician", "1": "The Magician", "magician": "The Magician",
    "02": "The High Priestess", "2": "The High Priestess", "highpriestess": "The High Priestess", "high_priestess": "The High Priestess",
    "03": "The Empress", "3": "The Empress", "empress": "The Empress",
    "04": "The Emperor", "4": "The Emperor", "emperor": "The Emperor",
    "05": "The Hierophant", "5": "The Hierophant", "hierophant": "The Hierophant",
    "06": "The Lovers", "6": "The Lovers", "lovers": "The Lovers",
    "07": "The Chariot", "7": "The Chariot", "chariot": "The Chariot",
    "08": "Strength", "8": "Strength", "strength": "Strength",
    "09": "The Hermit", "9": "The Hermit", "hermit": "The Hermit",
    "10": "Wheel of Fortune", "wheeloffortune": "Wheel of Fortune", "wheel": "Wheel of Fortune",
    "11": "Justice", "justice": "Justice",
    "12": "The Hanged Man", "hangedman": "The Hanged Man", "hanged": "The Hanged Man",
    "13": "Death", "death": "Death",
    "14": "Temperance", "temperance": "Temperance",
    "15": "The Devil", "devil": "The Devil",
    "16": "The Tower", "tower": "The Tower",
    "17": "The Star", "star": "The Star",
    "18": "The Moon", "moon": "The Moon",
    "19": "The Sun", "sun": "The Sun",
    "20": "Judgement", "judgement": "Judgement", "judgment": "Judgement",
    "21": "The World", "world": "The World",
    
    # Wands
    "aceofwands": "Ace of Wands", "wands01": "Ace of Wands", "wands1": "Ace of Wands", "wandsace": "Ace of Wands",
    "twoofwands": "Two of Wands", "wands02": "Two of Wands", "wands2": "Two of Wands",
    "threeofwands": "Three of Wands", "wands03": "Three of Wands", "wands3": "Three of Wands",
    "fourofwands": "Four of Wands", "wands04": "Four of Wands", "wands4": "Four of Wands",
    "fiveofwands": "Five of Wands", "wands05": "Five of Wands", "wands5": "Five of Wands",
    "sixofwands": "Six of Wands", "wands06": "Six of Wands", "wands6": "Six of Wands",
    "sevenofwands": "Seven of Wands", "wands07": "Seven of Wands", "wands7": "Seven of Wands",
    "eightofwands": "Eight of Wands", "wands08": "Eight of Wands", "wands8": "Eight of Wands",
    "nineofwands": "Nine of Wands", "wands09": "Nine of Wands", "wands9": "Nine of Wands",
    "tenofwands": "Ten of Wands", "wands10": "Ten of Wands",
    "pageofwands": "Page of Wands", "wandspage": "Page of Wands", "wands11": "Page of Wands",
    "knightofwands": "Knight of Wands", "wandsknight": "Knight of Wands", "wands12": "Knight of Wands",
    "queenofwands": "Queen of Wands", "wandsqueen": "Queen of Wands", "wands13": "Queen of Wands",
    "kingofwands": "King of Wands", "wandsking": "King of Wands", "wands14": "King of Wands",
    # Wands single-letter prefix (w01-w14)
    "w01": "Ace of Wands", "w1": "Ace of Wands",
    "w02": "Two of Wands", "w2": "Two of Wands",
    "w03": "Three of Wands", "w3": "Three of Wands",
    "w04": "Four of Wands", "w4": "Four of Wands",
    "w05": "Five of Wands", "w5": "Five of Wands",
    "w06": "Six of Wands", "w6": "Six of Wands",
    "w07": "Seven of Wands", "w7": "Seven of Wands",
    "w08": "Eight of Wands", "w8": "Eight of Wands",
    "w09": "Nine of Wands", "w9": "Nine of Wands",
    "w10": "Ten of Wands",
    "w11": "Page of Wands",
    "w12": "Knight of Wands",
    "w13": "Queen of Wands",
    "w14": "King of Wands",
    
    # Cups
    "aceofcups": "Ace of Cups", "cups01": "Ace of Cups", "cups1": "Ace of Cups", "cupsace": "Ace of Cups",
    "twoofcups": "Two of Cups", "cups02": "Two of Cups", "cups2": "Two of Cups",
    "threeofcups": "Three of Cups", "cups03": "Three of Cups", "cups3": "Three of Cups",
    "fourofcups": "Four of Cups", "cups04": "Four of Cups", "cups4": "Four of Cups",
    "fiveofcups": "Five of Cups", "cups05": "Five of Cups", "cups5": "Five of Cups",
    "sixofcups": "Six of Cups", "cups06": "Six of Cups", "cups6": "Six of Cups",
    "sevenofcups": "Seven of Cups", "cups07": "Seven of Cups", "cups7": "Seven of Cups",
    "eightofcups": "Eight of Cups", "cups08": "Eight of Cups", "cups8": "Eight of Cups",
    "nineofcups": "Nine of Cups", "cups09": "Nine of Cups", "cups9": "Nine of Cups",
    "tenofcups": "Ten of Cups", "cups10": "Ten of Cups",
    "pageofcups": "Page of Cups", "cupspage": "Page of Cups", "cups11": "Page of Cups",
    "knightofcups": "Knight of Cups", "cupsknight": "Knight of Cups", "cups12": "Knight of Cups",
    "queenofcups": "Queen of Cups", "cupsqueen": "Queen of Cups", "cups13": "Queen of Cups",
    "kingofcups": "King of Cups", "cupsking": "King of Cups", "cups14": "King of Cups",
    # Cups single-letter prefix (c01-c14)
    "c01": "Ace of Cups", "c1": "Ace of Cups",
    "c02": "Two of Cups", "c2": "Two of Cups",
    "c03": "Three of Cups", "c3": "Three of Cups",
    "c04": "Four of Cups", "c4": "Four of Cups",
    "c05": "Five of Cups", "c5": "Five of Cups",
    "c06": "Six of Cups", "c6": "Six of Cups",
    "c07": "Seven of Cups", "c7": "Seven of Cups",
    "c08": "Eight of Cups", "c8": "Eight of Cups",
    "c09": "Nine of Cups", "c9": "Nine of Cups",
    "c10": "Ten of Cups",
    "c11": "Page of Cups",
    "c12": "Knight of Cups",
    "c13": "Queen of Cups",
    "c14": "King of Cups",
    
    # Swords
    "aceofswords": "Ace of Swords", "swords01": "Ace of Swords", "swords1": "Ace of Swords", "swordsace": "Ace of Swords",
    "twoofswords": "Two of Swords", "swords02": "Two of Swords", "swords2": "Two of Swords",
    "threeofswords": "Three of Swords", "swords03": "Three of Swords", "swords3": "Three of Swords",
    "fourofswords": "Four of Swords", "swords04": "Four of Swords", "swords4": "Four of Swords",
    "fiveofswords": "Five of Swords", "swords05": "Five of Swords", "swords5": "Five of Swords",
    "sixofswords": "Six of Swords", "swords06": "Six of Swords", "swords6": "Six of Swords",
    "sevenofswords": "Seven of Swords", "swords07": "Seven of Swords", "swords7": "Seven of Swords",
    "eightofswords": "Eight of Swords", "swords08": "Eight of Swords", "swords8": "Eight of Swords",
    "nineofswords": "Nine of Swords", "swords09": "Nine of Swords", "swords9": "Nine of Swords",
    "tenofswords": "Ten of Swords", "swords10": "Ten of Swords",
    "pageofswords": "Page of Swords", "swordspage": "Page of Swords", "swords11": "Page of Swords",
    "knightofswords": "Knight of Swords", "swordsknight": "Knight of Swords", "swords12": "Knight of Swords",
    "queenofswords": "Queen of Swords", "swordsqueen": "Queen of Swords", "swords13": "Queen of Swords",
    "kingofswords": "King of Swords", "swordsking": "King of Swords", "swords14": "King of Swords",
    # Swords single-letter prefix (s01-s14)
    "s01": "Ace of Swords", "s1": "Ace of Swords",
    "s02": "Two of Swords", "s2": "Two of Swords",
    "s03": "Three of Swords", "s3": "Three of Swords",
    "s04": "Four of Swords", "s4": "Four of Swords",
    "s05": "Five of Swords", "s5": "Five of Swords",
    "s06": "Six of Swords", "s6": "Six of Swords",
    "s07": "Seven of Swords", "s7": "Seven of Swords",
    "s08": "Eight of Swords", "s8": "Eight of Swords",
    "s09": "Nine of Swords", "s9": "Nine of Swords",
    "s10": "Ten of Swords",
    "s11": "Page of Swords",
    "s12": "Knight of Swords",
    "s13": "Queen of Swords",
    "s14": "King of Swords",
    
    # Pentacles
    "aceofpentacles": "Ace of Pentacles", "pentacles01": "Ace of Pentacles", "pentacles1": "Ace of Pentacles", "pentaclesace": "Ace of Pentacles",
    "twoofpentacles": "Two of Pentacles", "pentacles02": "Two of Pentacles", "pentacles2": "Two of Pentacles",
    "threeofpentacles": "Three of Pentacles", "pentacles03": "Three of Pentacles", "pentacles3": "Three of Pentacles",
    "fourofpentacles": "Four of Pentacles", "pentacles04": "Four of Pentacles", "pentacles4": "Four of Pentacles",
    "fiveofpentacles": "Five of Pentacles", "pentacles05": "Five of Pentacles", "pentacles5": "Five of Pentacles",
    "sixofpentacles": "Six of Pentacles", "pentacles06": "Six of Pentacles", "pentacles6": "Six of Pentacles",
    "sevenofpentacles": "Seven of Pentacles", "pentacles07": "Seven of Pentacles", "pentacles7": "Seven of Pentacles",
    "eightofpentacles": "Eight of Pentacles", "pentacles08": "Eight of Pentacles", "pentacles8": "Eight of Pentacles",
    "nineofpentacles": "Nine of Pentacles", "pentacles09": "Nine of Pentacles", "pentacles9": "Nine of Pentacles",
    "tenofpentacles": "Ten of Pentacles", "pentacles10": "Ten of Pentacles",
    "pageofpentacles": "Page of Pentacles", "pentaclespage": "Page of Pentacles", "pentacles11": "Page of Pentacles",
    "knightofpentacles": "Knight of Pentacles", "pentaclesknight": "Knight of Pentacles", "pentacles12": "Knight of Pentacles",
    "queenofpentacles": "Queen of Pentacles", "pentaclesqueen": "Queen of Pentacles", "pentacles13": "Queen of Pentacles",
    "kingofpentacles": "King of Pentacles", "pentaclesking": "King of Pentacles", "pentacles14": "King of Pentacles",
    # Pentacles single-letter prefix (p01-p14)
    "p01": "Ace of Pentacles", "p1": "Ace of Pentacles",
    "p02": "Two of Pentacles", "p2": "Two of Pentacles",
    "p03": "Three of Pentacles", "p3": "Three of Pentacles",
    "p04": "Four of Pentacles", "p4": "Four of Pentacles",
    "p05": "Five of Pentacles", "p5": "Five of Pentacles",
    "p06": "Six of Pentacles", "p6": "Six of Pentacles",
    "p07": "Seven of Pentacles", "p7": "Seven of Pentacles",
    "p08": "Eight of Pentacles", "p8": "Eight of Pentacles",
    "p09": "Nine of Pentacles", "p9": "Nine of Pentacles",
    "p10": "Ten of Pentacles",
    "p11": "Page of Pentacles",
    "p12": "Knight of Pentacles",
    "p13": "Queen of Pentacles",
    "p14": "King of Pentacles",
    
    # Coins (alternate for Pentacles)
    "aceofcoins": "Ace of Pentacles", "coins01": "Ace of Pentacles", "coins1": "Ace of Pentacles",
    "twoofcoins": "Two of Pentacles", "coins02": "Two of Pentacles", "coins2": "Two of Pentacles",
    "threeofcoins": "Three of Pentacles", "coins03": "Three of Pentacles", "coins3": "Three of Pentacles",
    "fourofcoins": "Four of Pentacles", "coins04": "Four of Pentacles", "coins4": "Four of Pentacles",
    "fiveofcoins": "Five of Pentacles", "coins05": "Five of Pentacles", "coins5": "Five of Pentacles",
    "sixofcoins": "Six of Pentacles", "coins06": "Six of Pentacles", "coins6": "Six of Pentacles",
    "sevenofcoins": "Seven of Pentacles", "coins07": "Seven of Pentacles", "coins7": "Seven of Pentacles",
    "eightofcoins": "Eight of Pentacles", "coins08": "Eight of Pentacles", "coins8": "Eight of Pentacles",
    "nineofcoins": "Nine of Pentacles", "coins09": "Nine of Pentacles", "coins9": "Nine of Pentacles",
    "tenofcoins": "Ten of Pentacles", "coins10": "Ten of Pentacles",
    "pageofcoins": "Page of Pentacles", "coinspage": "Page of Pentacles", "coins11": "Page of Pentacles",
    "knightofcoins": "Knight of Pentacles", "coinsknight": "Knight of Pentacles", "coins12": "Knight of Pentacles",
    "queenofcoins": "Queen of Pentacles", "coinsqueen": "Queen of Pentacles", "coins13": "Queen of Pentacles",
    "kingofcoins": "King of Pentacles", "coinsking": "King of Pentacles", "coins14": "King of Pentacles",
    
    # Disks (alternate for Pentacles - Thoth)
    "aceofdisks": "Ace of Pentacles", "disks01": "Ace of Pentacles",
    "twoofdisks": "Two of Pentacles", "disks02": "Two of Pentacles",
    "threeofdisks": "Three of Pentacles", "disks03": "Three of Pentacles",
    "fourofdisks": "Four of Pentacles", "disks04": "Four of Pentacles",
    "fiveofdisks": "Five of Pentacles", "disks05": "Five of Pentacles",
    "sixofdisks": "Six of Pentacles", "disks06": "Six of Pentacles",
    "sevenofdisks": "Seven of Pentacles", "disks07": "Seven of Pentacles",
    "eightofdisks": "Eight of Pentacles", "disks08": "Eight of Pentacles",
    "nineofdisks": "Nine of Pentacles", "disks09": "Nine of Pentacles",
    "tenofdisks": "Ten of Pentacles", "disks10": "Ten of Pentacles",
    "princessofdisks": "Page of Pentacles", "disks11": "Page of Pentacles",
    "princeofdisks": "Knight of Pentacles", "disks12": "Knight of Pentacles",
    "queenofdisks": "Queen of Pentacles", "disks13": "Queen of Pentacles",
    "knightofdisks": "King of Pentacles", "disks14": "King of Pentacles",
}

# Standard Lenormand deck (36 cards)
STANDARD_LENORMAND = {
    "01": "Rider", "1": "Rider", "rider": "Rider",
    "02": "Clover", "2": "Clover", "clover": "Clover",
    "03": "Ship", "3": "Ship", "ship": "Ship",
    "04": "House", "4": "House", "house": "House",
    "05": "Tree", "5": "Tree", "tree": "Tree",
    "06": "Clouds", "6": "Clouds", "clouds": "Clouds",
    "07": "Snake", "7": "Snake", "snake": "Snake",
    "08": "Coffin", "8": "Coffin", "coffin": "Coffin",
    "09": "Bouquet", "9": "Bouquet", "bouquet": "Bouquet", "flowers": "Bouquet",
    "10": "Scythe", "scythe": "Scythe",
    "11": "Whip", "whip": "Whip", "broom": "Whip",
    "12": "Birds", "birds": "Birds", "owls": "Birds",
    "13": "Child", "child": "Child",
    "14": "Fox", "fox": "Fox",
    "15": "Bear", "bear": "Bear",
    "16": "Stars", "stars": "Stars",
    "17": "Stork", "stork": "Stork",
    "18": "Dog", "dog": "Dog",
    "19": "Tower", "tower": "Tower",
    "20": "Garden", "garden": "Garden",
    "21": "Mountain", "mountain": "Mountain",
    "22": "Crossroads", "crossroads": "Crossroads", "paths": "Crossroads",
    "23": "Mice", "mice": "Mice",
    "24": "Heart", "heart": "Heart",
    "25": "Ring", "ring": "Ring",
    "26": "Book", "book": "Book",
    "27": "Letter", "letter": "Letter",
    "28": "Man", "man": "Man", "gentleman": "Man",
    "29": "Woman", "woman": "Woman", "lady": "Woman",
    "30": "Lily", "lily": "Lily", "lilies": "Lily",
    "31": "Sun", "sun": "Sun",
    "32": "Moon", "moon": "Moon",
    "33": "Key", "key": "Key",
    "34": "Fish", "fish": "Fish",
    "35": "Anchor", "anchor": "Anchor",
    "36": "Cross", "cross": "Cross",
}

# Pre-Golden Dawn Tarot (swaps Strength/Justice - 8 and 11)
# In Marseille/Pre-Golden Dawn ordering: 8 = Justice, 11 = Strength (also called Fortitude)
PRE_GOLDEN_DAWN_TAROT = dict(STANDARD_TAROT)
# Override the numbered entries for 8 and 11
PRE_GOLDEN_DAWN_TAROT.update({
    "08": "Justice", "8": "Justice",
    "11": "Strength",
})

# Thoth Tarot - Crowley/Harris deck with different card names and court cards
# Major Arcana: Strength→Lust, Justice→Adjustment, Judgement→The Aeon, The World→The Universe
# Court Cards: King→Knight, Queen→Queen, Knight→Prince, Page→Princess
THOTH_TAROT = dict(STANDARD_TAROT)
THOTH_TAROT.update({
    # Major Arcana name changes
    "08": "Lust", "8": "Lust", "strength": "Lust", "lust": "Lust",
    "11": "Adjustment", "justice": "Adjustment", "adjustment": "Adjustment",
    "20": "The Aeon", "judgement": "The Aeon", "judgment": "The Aeon", "aeon": "The Aeon",
    "21": "The Universe", "world": "The Universe", "universe": "The Universe",
    
    # Wands court cards
    "pageofwands": "Princess of Wands", "wandspage": "Princess of Wands", "wands11": "Princess of Wands",
    "knightofwands": "Prince of Wands", "wandsknight": "Prince of Wands", "wands12": "Prince of Wands",
    "queenofwands": "Queen of Wands", "wandsqueen": "Queen of Wands", "wands13": "Queen of Wands",
    "kingofwands": "Knight of Wands", "wandsking": "Knight of Wands", "wands14": "Knight of Wands",
    "w11": "Princess of Wands", "w12": "Prince of Wands", "w13": "Queen of Wands", "w14": "Knight of Wands",
    "princessofwands": "Princess of Wands", "wandsprincess": "Princess of Wands",
    "princeofwands": "Prince of Wands", "wandsprince": "Prince of Wands",
    
    # Cups court cards
    "pageofcups": "Princess of Cups", "cupspage": "Princess of Cups", "cups11": "Princess of Cups",
    "knightofcups": "Prince of Cups", "cupsknight": "Prince of Cups", "cups12": "Prince of Cups",
    "queenofcups": "Queen of Cups", "cupsqueen": "Queen of Cups", "cups13": "Queen of Cups",
    "kingofcups": "Knight of Cups", "cupsking": "Knight of Cups", "cups14": "Knight of Cups",
    "c11": "Princess of Cups", "c12": "Prince of Cups", "c13": "Queen of Cups", "c14": "Knight of Cups",
    "princessofcups": "Princess of Cups", "cupsprincess": "Princess of Cups",
    "princeofcups": "Prince of Cups", "cupsprince": "Prince of Cups",
    
    # Swords court cards
    "pageofswords": "Princess of Swords", "swordspage": "Princess of Swords", "swords11": "Princess of Swords",
    "knightofswords": "Prince of Swords", "swordsknight": "Prince of Swords", "swords12": "Prince of Swords",
    "queenofswords": "Queen of Swords", "swordsqueen": "Queen of Swords", "swords13": "Queen of Swords",
    "kingofswords": "Knight of Swords", "swordsking": "Knight of Swords", "swords14": "Knight of Swords",
    "s11": "Princess of Swords", "s12": "Prince of Swords", "s13": "Queen of Swords", "s14": "Knight of Swords",
    "princessofswords": "Princess of Swords", "swordsprincess": "Princess of Swords",
    "princeofswords": "Prince of Swords", "swordsprince": "Prince of Swords",
    
    # Disks (Pentacles) court cards - Thoth calls them Disks
    "pageofpentacles": "Princess of Disks", "pentaclespage": "Princess of Disks", "pentacles11": "Princess of Disks",
    "knightofpentacles": "Prince of Disks", "pentaclesknight": "Prince of Disks", "pentacles12": "Prince of Disks",
    "queenofpentacles": "Queen of Disks", "pentaclesqueen": "Queen of Disks", "pentacles13": "Queen of Disks",
    "kingofpentacles": "Knight of Disks", "pentaclesking": "Knight of Disks", "pentacles14": "Knight of Disks",
    "p11": "Princess of Disks", "p12": "Prince of Disks", "p13": "Queen of Disks", "p14": "Knight of Disks",
    "princessofpentacles": "Princess of Disks", "pentaclesprincess": "Princess of Disks",
    "princeofpentacles": "Prince of Disks", "pentaclesprince": "Prince of Disks",
    # Disk-specific patterns
    "pageofdisks": "Princess of Disks", "diskspage": "Princess of Disks", "disks11": "Princess of Disks",
    "knightofdisks": "Prince of Disks", "disksknight": "Prince of Disks", "disks12": "Prince of Disks",
    "queenofdisks": "Queen of Disks", "disksqueen": "Queen of Disks", "disks13": "Queen of Disks",
    "kingofdisks": "Knight of Disks", "disksking": "Knight of Disks", "disks14": "Knight of Disks",
    "princessofdisks": "Princess of Disks", "disksprincess": "Princess of Disks",
    "princeofdisks": "Prince of Disks", "disksprince": "Prince of Disks",
    
    # Disks pip cards (Thoth name for Pentacles)
    "aceofdisks": "Ace of Disks", "disks01": "Ace of Disks", "disks1": "Ace of Disks", "disksace": "Ace of Disks",
    "twoofdisks": "Two of Disks", "disks02": "Two of Disks", "disks2": "Two of Disks",
    "threeofdisks": "Three of Disks", "disks03": "Three of Disks", "disks3": "Three of Disks",
    "fourofdisks": "Four of Disks", "disks04": "Four of Disks", "disks4": "Four of Disks",
    "fiveofdisks": "Five of Disks", "disks05": "Five of Disks", "disks5": "Five of Disks",
    "sixofdisks": "Six of Disks", "disks06": "Six of Disks", "disks6": "Six of Disks",
    "sevenofdisks": "Seven of Disks", "disks07": "Seven of Disks", "disks7": "Seven of Disks",
    "eightofdisks": "Eight of Disks", "disks08": "Eight of Disks", "disks8": "Eight of Disks",
    "nineofdisks": "Nine of Disks", "disks09": "Nine of Disks", "disks9": "Nine of Disks",
    "tenofdisks": "Ten of Disks", "disks10": "Ten of Disks",
    # Also map pentacles patterns to Disks for Thoth
    "aceofpentacles": "Ace of Disks", "pentacles01": "Ace of Disks", "pentacles1": "Ace of Disks", "pentaclesace": "Ace of Disks",
    "twoofpentacles": "Two of Disks", "pentacles02": "Two of Disks", "pentacles2": "Two of Disks",
    "threeofpentacles": "Three of Disks", "pentacles03": "Three of Disks", "pentacles3": "Three of Disks",
    "fourofpentacles": "Four of Disks", "pentacles04": "Four of Disks", "pentacles4": "Four of Disks",
    "fiveofpentacles": "Five of Disks", "pentacles05": "Five of Disks", "pentacles5": "Five of Disks",
    "sixofpentacles": "Six of Disks", "pentacles06": "Six of Disks", "pentacles6": "Six of Disks",
    "sevenofpentacles": "Seven of Disks", "pentacles07": "Seven of Disks", "pentacles7": "Seven of Disks",
    "eightofpentacles": "Eight of Disks", "pentacles08": "Eight of Disks", "pentacles8": "Eight of Disks",
    "nineofpentacles": "Nine of Disks", "pentacles09": "Nine of Disks", "pentacles9": "Nine of Disks",
    "tenofpentacles": "Ten of Disks", "pentacles10": "Ten of Disks",
    "p01": "Ace of Disks", "p1": "Ace of Disks",
    "p02": "Two of Disks", "p2": "Two of Disks",
    "p03": "Three of Disks", "p3": "Three of Disks",
    "p04": "Four of Disks", "p4": "Four of Disks",
    "p05": "Five of Disks", "p5": "Five of Disks",
    "p06": "Six of Disks", "p6": "Six of Disks",
    "p07": "Seven of Disks", "p7": "Seven of Disks",
    "p08": "Eight of Disks", "p8": "Eight of Disks",
    "p09": "Nine of Disks", "p9": "Nine of Disks",
    "p10": "Ten of Disks",
})

# Standard Playing Cards (52 cards)
PLAYING_CARDS_52 = {
    # Hearts
    "aceofhearts": "Ace of Hearts", "hearts01": "Ace of Hearts", "hearts1": "Ace of Hearts", "heartsace": "Ace of Hearts",
    "ah": "Ace of Hearts", "ha": "Ace of Hearts", "h1": "Ace of Hearts", "h01": "Ace of Hearts",
    "twoofhearts": "Two of Hearts", "hearts02": "Two of Hearts", "hearts2": "Two of Hearts",
    "2h": "Two of Hearts", "h2": "Two of Hearts", "h02": "Two of Hearts",
    "threeofhearts": "Three of Hearts", "hearts03": "Three of Hearts", "hearts3": "Three of Hearts",
    "3h": "Three of Hearts", "h3": "Three of Hearts", "h03": "Three of Hearts",
    "fourofhearts": "Four of Hearts", "hearts04": "Four of Hearts", "hearts4": "Four of Hearts",
    "4h": "Four of Hearts", "h4": "Four of Hearts", "h04": "Four of Hearts",
    "fiveofhearts": "Five of Hearts", "hearts05": "Five of Hearts", "hearts5": "Five of Hearts",
    "5h": "Five of Hearts", "h5": "Five of Hearts", "h05": "Five of Hearts",
    "sixofhearts": "Six of Hearts", "hearts06": "Six of Hearts", "hearts6": "Six of Hearts",
    "6h": "Six of Hearts", "h6": "Six of Hearts", "h06": "Six of Hearts",
    "sevenofhearts": "Seven of Hearts", "hearts07": "Seven of Hearts", "hearts7": "Seven of Hearts",
    "7h": "Seven of Hearts", "h7": "Seven of Hearts", "h07": "Seven of Hearts",
    "eightofhearts": "Eight of Hearts", "hearts08": "Eight of Hearts", "hearts8": "Eight of Hearts",
    "8h": "Eight of Hearts", "h8": "Eight of Hearts", "h08": "Eight of Hearts",
    "nineofhearts": "Nine of Hearts", "hearts09": "Nine of Hearts", "hearts9": "Nine of Hearts",
    "9h": "Nine of Hearts", "h9": "Nine of Hearts", "h09": "Nine of Hearts",
    "tenofhearts": "Ten of Hearts", "hearts10": "Ten of Hearts",
    "10h": "Ten of Hearts", "h10": "Ten of Hearts", "th": "Ten of Hearts",
    "jackofhearts": "Jack of Hearts", "heartsjack": "Jack of Hearts", "hearts11": "Jack of Hearts",
    "jh": "Jack of Hearts", "hj": "Jack of Hearts", "h11": "Jack of Hearts",
    "queenofhearts": "Queen of Hearts", "heartsqueen": "Queen of Hearts", "hearts12": "Queen of Hearts",
    "qh": "Queen of Hearts", "hq": "Queen of Hearts", "h12": "Queen of Hearts",
    "kingofhearts": "King of Hearts", "heartsking": "King of Hearts", "hearts13": "King of Hearts",
    "kh": "King of Hearts", "hk": "King of Hearts", "h13": "King of Hearts",

    # Diamonds
    "aceofdiamonds": "Ace of Diamonds", "diamonds01": "Ace of Diamonds", "diamonds1": "Ace of Diamonds", "diamondsace": "Ace of Diamonds",
    "ad": "Ace of Diamonds", "da": "Ace of Diamonds", "d1": "Ace of Diamonds", "d01": "Ace of Diamonds",
    "twoofdiamonds": "Two of Diamonds", "diamonds02": "Two of Diamonds", "diamonds2": "Two of Diamonds",
    "2d": "Two of Diamonds", "d2": "Two of Diamonds", "d02": "Two of Diamonds",
    "threeofdiamonds": "Three of Diamonds", "diamonds03": "Three of Diamonds", "diamonds3": "Three of Diamonds",
    "3d": "Three of Diamonds", "d3": "Three of Diamonds", "d03": "Three of Diamonds",
    "fourofdiamonds": "Four of Diamonds", "diamonds04": "Four of Diamonds", "diamonds4": "Four of Diamonds",
    "4d": "Four of Diamonds", "d4": "Four of Diamonds", "d04": "Four of Diamonds",
    "fiveofdiamonds": "Five of Diamonds", "diamonds05": "Five of Diamonds", "diamonds5": "Five of Diamonds",
    "5d": "Five of Diamonds", "d5": "Five of Diamonds", "d05": "Five of Diamonds",
    "sixofdiamonds": "Six of Diamonds", "diamonds06": "Six of Diamonds", "diamonds6": "Six of Diamonds",
    "6d": "Six of Diamonds", "d6": "Six of Diamonds", "d06": "Six of Diamonds",
    "sevenofdiamonds": "Seven of Diamonds", "diamonds07": "Seven of Diamonds", "diamonds7": "Seven of Diamonds",
    "7d": "Seven of Diamonds", "d7": "Seven of Diamonds", "d07": "Seven of Diamonds",
    "eightofdiamonds": "Eight of Diamonds", "diamonds08": "Eight of Diamonds", "diamonds8": "Eight of Diamonds",
    "8d": "Eight of Diamonds", "d8": "Eight of Diamonds", "d08": "Eight of Diamonds",
    "nineofdiamonds": "Nine of Diamonds", "diamonds09": "Nine of Diamonds", "diamonds9": "Nine of Diamonds",
    "9d": "Nine of Diamonds", "d9": "Nine of Diamonds", "d09": "Nine of Diamonds",
    "tenofdiamonds": "Ten of Diamonds", "diamonds10": "Ten of Diamonds",
    "10d": "Ten of Diamonds", "d10": "Ten of Diamonds", "td": "Ten of Diamonds",
    "jackofdiamonds": "Jack of Diamonds", "diamondsjack": "Jack of Diamonds", "diamonds11": "Jack of Diamonds",
    "jd": "Jack of Diamonds", "dj": "Jack of Diamonds", "d11": "Jack of Diamonds",
    "queenofdiamonds": "Queen of Diamonds", "diamondsqueen": "Queen of Diamonds", "diamonds12": "Queen of Diamonds",
    "qd": "Queen of Diamonds", "dq": "Queen of Diamonds", "d12": "Queen of Diamonds",
    "kingofdiamonds": "King of Diamonds", "diamondsking": "King of Diamonds", "diamonds13": "King of Diamonds",
    "kd": "King of Diamonds", "dk": "King of Diamonds", "d13": "King of Diamonds",

    # Clubs
    "aceofclubs": "Ace of Clubs", "clubs01": "Ace of Clubs", "clubs1": "Ace of Clubs", "clubsace": "Ace of Clubs",
    "ac": "Ace of Clubs", "ca": "Ace of Clubs", "c1": "Ace of Clubs", "c01": "Ace of Clubs",
    "twoofclubs": "Two of Clubs", "clubs02": "Two of Clubs", "clubs2": "Two of Clubs",
    "2c": "Two of Clubs", "c2": "Two of Clubs", "c02": "Two of Clubs",
    "threeofclubs": "Three of Clubs", "clubs03": "Three of Clubs", "clubs3": "Three of Clubs",
    "3c": "Three of Clubs", "c3": "Three of Clubs", "c03": "Three of Clubs",
    "fourofclubs": "Four of Clubs", "clubs04": "Four of Clubs", "clubs4": "Four of Clubs",
    "4c": "Four of Clubs", "c4": "Four of Clubs", "c04": "Four of Clubs",
    "fiveofclubs": "Five of Clubs", "clubs05": "Five of Clubs", "clubs5": "Five of Clubs",
    "5c": "Five of Clubs", "c5": "Five of Clubs", "c05": "Five of Clubs",
    "sixofclubs": "Six of Clubs", "clubs06": "Six of Clubs", "clubs6": "Six of Clubs",
    "6c": "Six of Clubs", "c6": "Six of Clubs", "c06": "Six of Clubs",
    "sevenofclubs": "Seven of Clubs", "clubs07": "Seven of Clubs", "clubs7": "Seven of Clubs",
    "7c": "Seven of Clubs", "c7": "Seven of Clubs", "c07": "Seven of Clubs",
    "eightofclubs": "Eight of Clubs", "clubs08": "Eight of Clubs", "clubs8": "Eight of Clubs",
    "8c": "Eight of Clubs", "c8": "Eight of Clubs", "c08": "Eight of Clubs",
    "nineofclubs": "Nine of Clubs", "clubs09": "Nine of Clubs", "clubs9": "Nine of Clubs",
    "9c": "Nine of Clubs", "c9": "Nine of Clubs", "c09": "Nine of Clubs",
    "tenofclubs": "Ten of Clubs", "clubs10": "Ten of Clubs",
    "10c": "Ten of Clubs", "c10": "Ten of Clubs", "tc": "Ten of Clubs",
    "jackofclubs": "Jack of Clubs", "clubsjack": "Jack of Clubs", "clubs11": "Jack of Clubs",
    "jc": "Jack of Clubs", "cj": "Jack of Clubs", "c11": "Jack of Clubs",
    "queenofclubs": "Queen of Clubs", "clubsqueen": "Queen of Clubs", "clubs12": "Queen of Clubs",
    "qc": "Queen of Clubs", "cq": "Queen of Clubs", "c12": "Queen of Clubs",
    "kingofclubs": "King of Clubs", "clubsking": "King of Clubs", "clubs13": "King of Clubs",
    "kc": "King of Clubs", "ck": "King of Clubs", "c13": "King of Clubs",

    # Spades
    "aceofspades": "Ace of Spades", "spades01": "Ace of Spades", "spades1": "Ace of Spades", "spadesace": "Ace of Spades",
    "as": "Ace of Spades", "sa": "Ace of Spades", "s1": "Ace of Spades", "s01": "Ace of Spades",
    "twoofspades": "Two of Spades", "spades02": "Two of Spades", "spades2": "Two of Spades",
    "2s": "Two of Spades", "s2": "Two of Spades", "s02": "Two of Spades",
    "threeofspades": "Three of Spades", "spades03": "Three of Spades", "spades3": "Three of Spades",
    "3s": "Three of Spades", "s3": "Three of Spades", "s03": "Three of Spades",
    "fourofspades": "Four of Spades", "spades04": "Four of Spades", "spades4": "Four of Spades",
    "4s": "Four of Spades", "s4": "Four of Spades", "s04": "Four of Spades",
    "fiveofspades": "Five of Spades", "spades05": "Five of Spades", "spades5": "Five of Spades",
    "5s": "Five of Spades", "s5": "Five of Spades", "s05": "Five of Spades",
    "sixofspades": "Six of Spades", "spades06": "Six of Spades", "spades6": "Six of Spades",
    "6s": "Six of Spades", "s6": "Six of Spades", "s06": "Six of Spades",
    "sevenofspades": "Seven of Spades", "spades07": "Seven of Spades", "spades7": "Seven of Spades",
    "7s": "Seven of Spades", "s7": "Seven of Spades", "s07": "Seven of Spades",
    "eightofspades": "Eight of Spades", "spades08": "Eight of Spades", "spades8": "Eight of Spades",
    "8s": "Eight of Spades", "s8": "Eight of Spades", "s08": "Eight of Spades",
    "nineofspades": "Nine of Spades", "spades09": "Nine of Spades", "spades9": "Nine of Spades",
    "9s": "Nine of Spades", "s9": "Nine of Spades", "s09": "Nine of Spades",
    "tenofspades": "Ten of Spades", "spades10": "Ten of Spades",
    "10s": "Ten of Spades", "s10": "Ten of Spades", "ts": "Ten of Spades",
    "jackofspades": "Jack of Spades", "spadesjack": "Jack of Spades", "spades11": "Jack of Spades",
    "js": "Jack of Spades", "sj": "Jack of Spades", "s11": "Jack of Spades",
    "queenofspades": "Queen of Spades", "spadesqueen": "Queen of Spades", "spades12": "Queen of Spades",
    "qs": "Queen of Spades", "sq": "Queen of Spades", "s12": "Queen of Spades",
    "kingofspades": "King of Spades", "spadesking": "King of Spades", "spades13": "King of Spades",
    "ks": "King of Spades", "sk": "King of Spades", "s13": "King of Spades",
}

# Playing Cards with Jokers (54 cards)
PLAYING_CARDS_54 = dict(PLAYING_CARDS_52)
PLAYING_CARDS_54.update({
    "joker": "Joker", "joker1": "Red Joker", "joker01": "Red Joker", "redjoker": "Red Joker",
    "joker2": "Black Joker", "joker02": "Black Joker", "blackjoker": "Black Joker",
    "jr": "Red Joker", "jb": "Black Joker",
})

# Built-in presets
BUILTIN_PRESETS = {
    "Tarot (RWS Ordering)": {
        "type": "Tarot",
        "mappings": STANDARD_TAROT,
        "description": "Rider-Waite-Smith ordering: 8=Strength, 11=Justice. Standard 78-card tarot deck.",
        "suit_names": {"wands": "Wands", "cups": "Cups", "swords": "Swords", "pentacles": "Pentacles"}
    },
    "Tarot (Pre-Golden Dawn Ordering)": {
        "type": "Tarot",
        "mappings": PRE_GOLDEN_DAWN_TAROT,
        "description": "Marseille/Pre-Golden Dawn ordering: 8=Justice, 11=Strength. Standard 78-card tarot deck.",
        "suit_names": {"wands": "Wands", "cups": "Cups", "swords": "Swords", "pentacles": "Pentacles"}
    },
    "Tarot (Thoth)": {
        "type": "Tarot",
        "mappings": THOTH_TAROT,
        "description": "Crowley/Harris Thoth deck: Lust, Adjustment, The Aeon, The Universe. Knight/Queen/Prince/Princess courts. Disks instead of Pentacles.",
        "suit_names": {"wands": "Wands", "cups": "Cups", "swords": "Swords", "pentacles": "Disks"}
    },
    "Lenormand (36 cards)": {
        "type": "Lenormand",
        "mappings": STANDARD_LENORMAND,
        "description": "Standard 36-card Lenormand deck",
        "suit_names": {"hearts": "Hearts", "diamonds": "Diamonds", "clubs": "Clubs", "spades": "Spades"}
    },
    "Playing Cards (52 cards)": {
        "type": "Oracle",
        "mappings": PLAYING_CARDS_52,
        "description": "Standard 52-card playing card deck (Hearts, Diamonds, Clubs, Spades)",
        "suit_names": {"hearts": "Hearts", "diamonds": "Diamonds", "clubs": "Clubs", "spades": "Spades"}
    },
    "Playing Cards with Jokers (54 cards)": {
        "type": "Oracle",
        "mappings": PLAYING_CARDS_54,
        "description": "Playing card deck with 2 jokers (52 cards + Red Joker + Black Joker)",
        "suit_names": {"hearts": "Hearts", "diamonds": "Diamonds", "clubs": "Clubs", "spades": "Spades"}
    },
    "Oracle (filename only)": {
        "type": "Oracle",
        "mappings": {},
        "description": "Uses cleaned filename as card name (for custom oracle decks)",
        "suit_names": {}
    }
}


class ImportPresets:
    """Manages import presets for automatic card naming"""
    
    def __init__(self, presets_file: str = None):
        if presets_file is None:
            self.presets_file = Path(os.path.dirname(os.path.abspath(__file__))) / 'import_presets.json'
        else:
            self.presets_file = Path(presets_file)
        
        self.custom_presets = {}
        self._load_presets()
    
    def _load_presets(self):
        """Load custom presets from file"""
        if self.presets_file.exists():
            try:
                with open(self.presets_file, 'r') as f:
                    self.custom_presets = json.load(f)
            except Exception:
                self.custom_presets = {}
    
    def _save_presets(self):
        """Save custom presets to file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(self.custom_presets, f, indent=2)
        except Exception as e:
            print(f"Error saving presets: {e}")
    
    def get_all_presets(self) -> Dict:
        """Get all presets (builtin + custom, with custom overriding builtin if same name)"""
        all_presets = dict(BUILTIN_PRESETS)
        for name, preset in self.custom_presets.items():
            # If custom preset has same name as builtin, it overrides the builtin
            if name in BUILTIN_PRESETS:
                all_presets[name] = preset  # Override builtin
            else:
                all_presets[f"Custom: {name}"] = preset
        return all_presets
    
    def is_preset_customized(self, name: str) -> bool:
        """Check if a builtin preset has been customized"""
        clean_name = name.replace("Custom: ", "")
        return clean_name in self.custom_presets and clean_name in BUILTIN_PRESETS
    
    def is_builtin_preset(self, name: str) -> bool:
        """Check if a preset name is a builtin preset"""
        return name in BUILTIN_PRESETS
    
    def get_preset_names(self) -> List[str]:
        """Get list of all preset names"""
        return list(self.get_all_presets().keys())
    
    def get_preset(self, name: str) -> Optional[Dict]:
        """Get a specific preset by name"""
        # Check if it's a builtin that has been customized
        if name in BUILTIN_PRESETS and name in self.custom_presets:
            return self.custom_presets[name]
        
        if name in BUILTIN_PRESETS:
            return BUILTIN_PRESETS[name]
        
        clean_name = name.replace("Custom: ", "")
        if clean_name in self.custom_presets:
            return self.custom_presets[clean_name]
        
        return None
    
    def add_custom_preset(self, name: str, cartomancy_type: str, 
                         mappings: Dict[str, str], description: str = "",
                         suit_names: Dict[str, str] = None):
        """Add or update a custom preset"""
        self.custom_presets[name] = {
            "type": cartomancy_type,
            "mappings": mappings,
            "description": description
        }
        if suit_names:
            self.custom_presets[name]["suit_names"] = suit_names
        self._save_presets()
    
    def delete_custom_preset(self, name: str):
        """Delete a custom preset"""
        clean_name = name.replace("Custom: ", "")
        if clean_name in self.custom_presets:
            del self.custom_presets[clean_name]
            self._save_presets()
    
    def map_filename_to_card(self, filename: str, preset_name: str = None,
                              custom_suit_names: dict = None) -> str:
        """
        Map a filename to a card name using the specified preset.
        Returns the mapped name or a cleaned version of the filename.
        custom_suit_names: dict with keys 'wands', 'cups', 'swords', 'pentacles'
        """
        # Get just the filename without extension
        stem = Path(filename).stem

        # Create normalized key (lowercase, no spaces/separators)
        normalized = re.sub(r'[\s_\-\.]', '', stem.lower())

        # Try to find in preset
        if preset_name:
            preset = self.get_preset(preset_name)
            if preset and preset.get('mappings'):
                mappings = preset['mappings']

                # Direct match
                if normalized in mappings:
                    card_name = mappings[normalized]
                    return self._apply_custom_suit_names(card_name, custom_suit_names)

                # Try with original stem
                if stem.lower() in mappings:
                    card_name = mappings[stem.lower()]
                    return self._apply_custom_suit_names(card_name, custom_suit_names)

                # Try extracting just numbers from filename (for patterns like "PLen-A-01")
                number_match = re.search(r'(\d+)(?=\D*$)', stem)
                if number_match:
                    number_only = number_match.group(1)
                    if number_only in mappings:
                        card_name = mappings[number_only]
                        return self._apply_custom_suit_names(card_name, custom_suit_names)

        # Fall back to cleaned filename
        return self._clean_filename(stem)
    
    def _apply_custom_suit_names(self, card_name: str, custom_suit_names: dict = None) -> str:
        """Replace default suit names with custom ones"""
        if not custom_suit_names:
            return card_name
        
        # Map of default names to their keys
        default_suits = {
            'Wands': 'wands',
            'Cups': 'cups',
            'Swords': 'swords',
            'Pentacles': 'pentacles',
        }
        
        for default_name, key in default_suits.items():
            if f'of {default_name}' in card_name:
                custom_name = custom_suit_names.get(key, default_name)
                return card_name.replace(f'of {default_name}', f'of {custom_name}')
        
        return card_name
    
    def _clean_filename(self, filename: str) -> str:
        """Clean a filename into a readable card name"""
        # Replace separators with spaces
        name = re.sub(r'[\s_\-\.]+', ' ', filename)
        # Title case
        name = name.title()
        # Clean up spacing
        name = ' '.join(name.split())
        return name
    
    def get_sort_order(self, card_name: str, preset_name: str = None) -> int:
        """Get a sort order for a card based on the preset"""
        if not preset_name:
            return 0
        
        preset = self.get_preset(preset_name)
        if not preset or not preset.get('mappings'):
            return 0
        
        # Find the card in mappings and return position
        mappings = preset['mappings']
        values = list(set(mappings.values()))
        
        try:
            return values.index(card_name)
        except ValueError:
            return len(values)  # Unknown cards go at the end
    
    def preview_import(self, folder: str, preset_name: str, 
                      custom_suit_names: dict = None) -> List[Tuple[str, str, int]]:
        """
        Preview what cards would be imported from a folder.
        Returns list of (original_filename, mapped_name, sort_order) tuples.
        """
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        results = []
        
        folder_path = Path(folder)
        if not folder_path.exists():
            return results
        
        for filepath in sorted(folder_path.iterdir()):
            if filepath.suffix.lower() in valid_extensions:
                mapped_name = self.map_filename_to_card(filepath.name, preset_name, custom_suit_names)
                sort_order = self._get_card_sort_order(mapped_name, custom_suit_names)
                results.append((filepath.name, mapped_name, sort_order))
        
        # Sort by sort order
        results.sort(key=lambda x: x[2])
        
        return results
    
    def _get_card_sort_order(self, card_name: str, custom_suit_names: dict = None) -> int:
        """Get sort order: Major Arcana (0-21), then Wands, Cups, Swords, Pentacles"""
        name_lower = card_name.lower()
        
        # Major arcana order
        major_arcana = {
            'the fool': 0, 'fool': 0,
            'the magician': 1, 'magician': 1,
            'the high priestess': 2, 'high priestess': 2,
            'the empress': 3, 'empress': 3,
            'the emperor': 4, 'emperor': 4,
            'the hierophant': 5, 'hierophant': 5,
            'the lovers': 6, 'lovers': 6,
            'the chariot': 7, 'chariot': 7,
            'strength': 8,
            'the hermit': 9, 'hermit': 9,
            'wheel of fortune': 10,
            'justice': 11,
            'the hanged man': 12, 'hanged man': 12,
            'death': 13,
            'temperance': 14,
            'the devil': 15, 'devil': 15,
            'the tower': 16, 'tower': 16,
            'the star': 17, 'star': 17,
            'the moon': 18, 'moon': 18,
            'the sun': 19, 'sun': 19,
            'judgement': 20, 'judgment': 20,
            'the world': 21, 'world': 21,
        }
        
        if name_lower in major_arcana:
            return major_arcana[name_lower]
        
        # Rank order within suits
        rank_order = {
            'ace': 0, 'two': 1, 'three': 2, 'four': 3, 'five': 4,
            'six': 5, 'seven': 6, 'eight': 7, 'nine': 8, 'ten': 9,
            'page': 10, 'princess': 10, 'jack': 10,
            'knight': 11, 'prince': 11,
            'queen': 12,
            'king': 13,
        }
        
        # Get suit names (custom or default)
        suit_names = custom_suit_names or {}
        wands_name = suit_names.get('wands', 'Wands').lower()
        cups_name = suit_names.get('cups', 'Cups').lower()
        swords_name = suit_names.get('swords', 'Swords').lower()
        pentacles_name = suit_names.get('pentacles', 'Pentacles').lower()
        
        # Suit base values (after 22 major arcana)
        suit_bases = {
            wands_name: 100,
            cups_name: 200,
            swords_name: 300,
            pentacles_name: 400,
            # Also include defaults in case mixed
            'wands': 100, 'cups': 200, 'swords': 300, 'pentacles': 400,
            'coins': 400, 'disks': 400,
        }
        
        # Find suit
        for suit_name, base in suit_bases.items():
            if f'of {suit_name}' in name_lower:
                # Find rank
                for rank, rank_val in rank_order.items():
                    if name_lower.startswith(rank):
                        return base + rank_val
                return base + 50  # Unknown rank
        
        return 999  # Unknown cards at end


# Global instance
_presets_instance = None


def get_presets() -> ImportPresets:
    """Get the global import presets instance"""
    global _presets_instance
    if _presets_instance is None:
        _presets_instance = ImportPresets()
    return _presets_instance

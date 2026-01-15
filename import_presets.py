"""
Import presets for automatic card naming during deck imports
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Court card preset definitions
COURT_PRESETS = {
    "RWS (Page/Knight/Queen/King)": {
        "page": "Page",
        "knight": "Knight",
        "queen": "Queen",
        "king": "King"
    },
    "Thoth (Princess/Prince/Queen/Knight)": {
        "page": "Princess",
        "knight": "Prince",
        "queen": "Queen",
        "king": "Knight"
    },
    "Marseille (Valet/Cavalier/Queen/King)": {
        "page": "Valet",
        "knight": "Cavalier",
        "queen": "Queen",
        "king": "King"
    },
    "Custom...": None  # Signals UI should show text fields
}

# Archetype mapping options
ARCHETYPE_MAPPING_OPTIONS = [
    "Map to RWS archetypes",
    "Map to Thoth archetypes",
    "Create new archetypes"
]

# Standard RWS court card archetypes (for mapping)
RWS_COURT_ARCHETYPES = {
    "page": "Page",
    "knight": "Knight",
    "queen": "Queen",
    "king": "King"
}

# Standard Thoth court card archetypes (for mapping)
THOTH_COURT_ARCHETYPES = {
    "page": "Princess",
    "knight": "Prince",
    "queen": "Queen",
    "king": "Knight"
}


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

# Standard Kipper deck (36 cards)
STANDARD_KIPPER = {
    "01": "Main Male", "1": "Main Male", "mainmale": "Main Male", "hauptperson": "Main Male",
    "02": "Main Female", "2": "Main Female", "mainfemale": "Main Female",
    "03": "Marriage", "3": "Marriage", "marriage": "Marriage", "union": "Marriage",
    "04": "Meeting", "4": "Meeting", "meeting": "Meeting", "rendezvous": "Meeting",
    "05": "Good Gentleman", "5": "Good Gentleman", "goodgentleman": "Good Gentleman", "goodman": "Good Gentleman",
    "06": "Good Lady", "6": "Good Lady", "goodlady": "Good Lady", "goodwoman": "Good Lady",
    "07": "Pleasant Letter", "7": "Pleasant Letter", "pleasantletter": "Pleasant Letter", "goodnews": "Pleasant Letter",
    "08": "False Person", "8": "False Person", "falseperson": "False Person", "falsity": "False Person",
    "09": "A Change", "9": "A Change", "change": "A Change", "achange": "A Change",
    "10": "A Journey", "journey": "A Journey", "ajourney": "A Journey", "travel": "A Journey",
    "11": "Gain Money", "gainmoney": "Gain Money", "winmoney": "Gain Money", "wealth": "Gain Money",
    "12": "Rich Girl", "richgirl": "Rich Girl", "wealthygirl": "Rich Girl",
    "13": "Rich Man", "richman": "Rich Man", "wealthyman": "Rich Man",
    "14": "Sad News", "sadnews": "Sad News", "badnews": "Sad News", "message": "Sad News",
    "15": "Success in Love", "successinlove": "Success in Love", "loversuccess": "Success in Love",
    "16": "His Thoughts", "histhoughts": "His Thoughts", "herthoughts": "His Thoughts", "thoughts": "His Thoughts",
    "17": "A Gift", "gift": "A Gift", "agift": "A Gift", "present": "A Gift",
    "18": "A Small Child", "smallchild": "A Small Child", "child": "A Small Child", "asmallchild": "A Small Child",
    "19": "A Funeral", "funeral": "A Funeral", "afuneral": "A Funeral", "death": "A Funeral",
    "20": "House", "house": "House", "home": "House",
    "21": "Living Room", "livingroom": "Living Room", "parlor": "Living Room", "room": "Living Room",
    "22": "Official Person", "officialperson": "Official Person", "military": "Official Person", "official": "Official Person",
    "23": "Court House", "courthouse": "Court House", "court": "Court House",
    "24": "Theft", "theft": "Theft", "thief": "Theft", "stealing": "Theft",
    "25": "High Honors", "highhonors": "High Honors", "honor": "High Honors", "achievement": "High Honors",
    "26": "Great Fortune", "greatfortune": "Great Fortune", "fortune": "Great Fortune", "luck": "Great Fortune",
    "27": "Unexpected Money", "unexpectedmoney": "Unexpected Money", "surprise": "Unexpected Money",
    "28": "Expectation", "expectation": "Expectation", "hope": "Expectation", "waiting": "Expectation",
    "29": "Prison", "prison": "Prison", "confinement": "Prison", "jail": "Prison",
    "30": "Court", "30": "Court", "legal": "Court", "judge": "Court", "judiciary": "Court",
    "31": "Short Illness", "shortillness": "Short Illness", "illness": "Short Illness", "sickness": "Short Illness",
    "32": "Grief and Adversity", "grief": "Grief and Adversity", "adversity": "Grief and Adversity", "sorrow": "Grief and Adversity",
    "33": "Gloomy Thoughts", "gloomythoughts": "Gloomy Thoughts", "sadness": "Gloomy Thoughts", "melancholy": "Gloomy Thoughts",
    "34": "Work", "work": "Work", "employment": "Work", "occupation": "Work", "labor": "Work",
    "35": "A Long Way", "longway": "A Long Way", "longroad": "A Long Way", "distance": "A Long Way",
    "36": "Hope, Great Water", "hope": "Hope, Great Water", "greatwater": "Hope, Great Water", "water": "Hope, Great Water", "ocean": "Hope, Great Water",
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

# Gnostic/Eternal Tarot - Samael Aun Weor / Glorian Publishing system
# 78 Arcana with unique names (no traditional suits for Minor Arcana)
# Major Arcana: 1-22, Minor Arcana: 23-78
GNOSTIC_ETERNAL_TAROT = {
    # Major Arcana (1-22)
    "01": "Arcanum 1: The Magician", "1": "Arcanum 1: The Magician",
    "themagician": "Arcanum 1: The Magician", "magician": "Arcanum 1: The Magician",
    "02": "Arcanum 2: The Priestess", "2": "Arcanum 2: The Priestess",
    "thepriestess": "Arcanum 2: The Priestess", "priestess": "Arcanum 2: The Priestess",
    "highpriestess": "Arcanum 2: The Priestess",
    "03": "Arcanum 3: The Empress", "3": "Arcanum 3: The Empress",
    "theempress": "Arcanum 3: The Empress", "empress": "Arcanum 3: The Empress",
    "04": "Arcanum 4: The Emperor", "4": "Arcanum 4: The Emperor",
    "theemperor": "Arcanum 4: The Emperor", "emperor": "Arcanum 4: The Emperor",
    "05": "Arcanum 5: The Hierarch", "5": "Arcanum 5: The Hierarch",
    "thehierarch": "Arcanum 5: The Hierarch", "hierarch": "Arcanum 5: The Hierarch",
    "hierophant": "Arcanum 5: The Hierarch",
    "06": "Arcanum 6: Indecision", "6": "Arcanum 6: Indecision",
    "indecision": "Arcanum 6: Indecision", "thelovers": "Arcanum 6: Indecision", "lovers": "Arcanum 6: Indecision",
    "07": "Arcanum 7: Triumph", "7": "Arcanum 7: Triumph",
    "triumph": "Arcanum 7: Triumph", "thechariot": "Arcanum 7: Triumph", "chariot": "Arcanum 7: Triumph",
    "08": "Arcanum 8: Justice", "8": "Arcanum 8: Justice",
    "justice": "Arcanum 8: Justice",
    "09": "Arcanum 9: The Hermit", "9": "Arcanum 9: The Hermit",
    "thehermit": "Arcanum 9: The Hermit", "hermit": "Arcanum 9: The Hermit",
    "10": "Arcanum 10: Retribution",
    "retribution": "Arcanum 10: Retribution", "wheeloffortune": "Arcanum 10: Retribution", "wheel": "Arcanum 10: Retribution",
    "11": "Arcanum 11: Persuasion",
    "persuasion": "Arcanum 11: Persuasion", "strength": "Arcanum 11: Persuasion",
    "12": "Arcanum 12: The Apostolate",
    "theapostolate": "Arcanum 12: The Apostolate", "apostolate": "Arcanum 12: The Apostolate",
    "hangedman": "Arcanum 12: The Apostolate", "thehangedman": "Arcanum 12: The Apostolate",
    "13": "Arcanum 13: Immortality",
    "immortality": "Arcanum 13: Immortality", "death": "Arcanum 13: Immortality",
    "14": "Arcanum 14: Temperance",
    "temperance": "Arcanum 14: Temperance",
    "15": "Arcanum 15: Passion",
    "passion": "Arcanum 15: Passion", "thedevil": "Arcanum 15: Passion", "devil": "Arcanum 15: Passion",
    "16": "Arcanum 16: Fragility",
    "fragility": "Arcanum 16: Fragility", "thetower": "Arcanum 16: Fragility", "tower": "Arcanum 16: Fragility",
    "17": "Arcanum 17: Hope",
    "hope": "Arcanum 17: Hope", "thestar": "Arcanum 17: Hope", "star": "Arcanum 17: Hope",
    "18": "Arcanum 18: Twilight",
    "twilight": "Arcanum 18: Twilight", "themoon": "Arcanum 18: Twilight", "moon": "Arcanum 18: Twilight",
    "19": "Arcanum 19: Inspiration",
    "inspiration": "Arcanum 19: Inspiration", "thesun": "Arcanum 19: Inspiration", "sun": "Arcanum 19: Inspiration",
    "20": "Arcanum 20: Resurrection",
    "resurrection": "Arcanum 20: Resurrection", "judgement": "Arcanum 20: Resurrection", "judgment": "Arcanum 20: Resurrection",
    "21": "Arcanum 21: Transmutation",
    "transmutation": "Arcanum 21: Transmutation", "theworld": "Arcanum 21: Transmutation", "world": "Arcanum 21: Transmutation",
    "22": "Arcanum 22: The Return",
    "thereturn": "Arcanum 22: The Return", "return": "Arcanum 22: The Return",
    "thefool": "Arcanum 22: The Return", "fool": "Arcanum 22: The Return",
    # Note: In Gnostic system, The Fool is Arcanum 22, not 0

    # Minor Arcana (23-78) - each with unique name
    "23": "Arcanum 23: The Plower", "theplower": "Arcanum 23: The Plower", "plower": "Arcanum 23: The Plower",
    "24": "Arcanum 24: The Weaver", "theweaver": "Arcanum 24: The Weaver", "weaver": "Arcanum 24: The Weaver",
    "25": "Arcanum 25: The Argonaut", "theargonaut": "Arcanum 25: The Argonaut", "argonaut": "Arcanum 25: The Argonaut",
    "26": "Arcanum 26: The Prodigy", "theprodigy": "Arcanum 26: The Prodigy", "prodigy": "Arcanum 26: The Prodigy",
    "27": "Arcanum 27: The Unexpected", "theunexpected": "Arcanum 27: The Unexpected", "unexpected": "Arcanum 27: The Unexpected",
    "28": "Arcanum 28: Uncertainty", "uncertainty": "Arcanum 28: Uncertainty",
    "29": "Arcanum 29: Domesticity", "domesticity": "Arcanum 29: Domesticity",
    "30": "Arcanum 30: Exchange", "exchange": "Arcanum 30: Exchange",
    "31": "Arcanum 31: Impediments", "impediments": "Arcanum 31: Impediments",
    "32": "Arcanum 32: Magnificence", "magnificence": "Arcanum 32: Magnificence",
    "33": "Arcanum 33: Alliance", "alliance": "Arcanum 33: Alliance",
    "34": "Arcanum 34: Innovation", "innovation": "Arcanum 34: Innovation",
    "35": "Arcanum 35: Grief", "grief": "Arcanum 35: Grief",
    "36": "Arcanum 36: Initiation", "initiation": "Arcanum 36: Initiation",
    "37": "Arcanum 37: Art and Science", "artandscience": "Arcanum 37: Art and Science",
    "38": "Arcanum 38: Duplicity", "duplicity": "Arcanum 38: Duplicity", "biplicity": "Arcanum 38: Duplicity",
    "39": "Arcanum 39: Testimony", "testimony": "Arcanum 39: Testimony",
    "40": "Arcanum 40: Presentiment", "presentiment": "Arcanum 40: Presentiment",
    "41": "Arcanum 41: Uneasiness", "uneasiness": "Arcanum 41: Uneasiness",
    "42": "Arcanum 42: Preeminence", "preeminence": "Arcanum 42: Preeminence",
    "43": "Arcanum 43: Hallucination", "hallucination": "Arcanum 43: Hallucination", "imagination": "Arcanum 43: Hallucination",
    "44": "Arcanum 44: Thinking", "thinking": "Arcanum 44: Thinking", "thought": "Arcanum 44: Thinking",
    "45": "Arcanum 45: Regeneration", "regeneration": "Arcanum 45: Regeneration",
    "46": "Arcanum 46: Patrimony", "patrimony": "Arcanum 46: Patrimony",
    "47": "Arcanum 47: Conjecturing", "conjecturing": "Arcanum 47: Conjecturing", "deduction": "Arcanum 47: Conjecturing",
    "48": "Arcanum 48: Consummation", "consummation": "Arcanum 48: Consummation",
    "49": "Arcanum 49: Versatility", "versatility": "Arcanum 49: Versatility",
    "50": "Arcanum 50: Affinity", "affinity": "Arcanum 50: Affinity",
    "51": "Arcanum 51: Counseling", "counseling": "Arcanum 51: Counseling",
    "52": "Arcanum 52: Premeditation", "premeditation": "Arcanum 52: Premeditation",
    "53": "Arcanum 53: Resentment", "resentment": "Arcanum 53: Resentment",
    "54": "Arcanum 54: Examination", "examination": "Arcanum 54: Examination",
    "55": "Arcanum 55: Contrition", "contrition": "Arcanum 55: Contrition",
    "56": "Arcanum 56: Pilgrimage", "pilgrimage": "Arcanum 56: Pilgrimage",
    "57": "Arcanum 57: Rivalry", "rivalry": "Arcanum 57: Rivalry",
    "58": "Arcanum 58: Requalification", "requalification": "Arcanum 58: Requalification",
    "59": "Arcanum 59: Revelation", "revelation": "Arcanum 59: Revelation",
    "60": "Arcanum 60: Evolution", "evolution": "Arcanum 60: Evolution",
    "61": "Arcanum 61: Solitude", "solitude": "Arcanum 61: Solitude",
    "62": "Arcanum 62: Proscription", "proscription": "Arcanum 62: Proscription",
    "63": "Arcanum 63: Communion", "communion": "Arcanum 63: Communion",
    "64": "Arcanum 64: Vehemence", "vehemence": "Arcanum 64: Vehemence", "zeal": "Arcanum 64: Vehemence",
    "65": "Arcanum 65: Learning", "learning": "Arcanum 65: Learning",
    "66": "Arcanum 66: Perplexity", "perplexity": "Arcanum 66: Perplexity",
    "67": "Arcanum 67: Friendship", "friendship": "Arcanum 67: Friendship",
    "68": "Arcanum 68: Speculation", "speculation": "Arcanum 68: Speculation",
    "69": "Arcanum 69: Chance", "chance": "Arcanum 69: Chance",
    "70": "Arcanum 70: Cooperation", "cooperation": "Arcanum 70: Cooperation",
    "71": "Arcanum 71: Avarice", "avarice": "Arcanum 71: Avarice",
    "72": "Arcanum 72: Purification", "purification": "Arcanum 72: Purification",
    "73": "Arcanum 73: Love and Desire", "loveanddesire": "Arcanum 73: Love and Desire",
    "74": "Arcanum 74: Offering", "offering": "Arcanum 74: Offering",
    "75": "Arcanum 75: Generosity", "generosity": "Arcanum 75: Generosity",
    "76": "Arcanum 76: The Dispenser", "thedispenser": "Arcanum 76: The Dispenser", "dispenser": "Arcanum 76: The Dispenser",
    "77": "Arcanum 77: Disorientation", "disorientation": "Arcanum 77: Disorientation",
    "78": "Arcanum 78: Renaissance", "renaissance": "Arcanum 78: Renaissance",
}

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

# I Ching - 64 Hexagrams
# Format: position -> English name (metadata provides Chinese, pinyin, etc.)
I_CHING_HEXAGRAMS = {
    "01": "The Creative", "1": "The Creative",
    "02": "The Receptive", "2": "The Receptive",
    "03": "Difficulty at the Beginning", "3": "Difficulty at the Beginning",
    "04": "Youthful Folly", "4": "Youthful Folly",
    "05": "Waiting", "5": "Waiting",
    "06": "Conflict", "6": "Conflict",
    "07": "The Army", "7": "The Army",
    "08": "Holding Together", "8": "Holding Together",
    "09": "Small Taming", "9": "Small Taming",
    "10": "Treading",
    "11": "Peace",
    "12": "Standstill",
    "13": "Fellowship",
    "14": "Great Possession",
    "15": "Modesty",
    "16": "Enthusiasm",
    "17": "Following",
    "18": "Work on the Decayed",
    "19": "Approach",
    "20": "Contemplation",
    "21": "Biting Through",
    "22": "Grace",
    "23": "Splitting Apart",
    "24": "Return",
    "25": "Innocence",
    "26": "Great Taming",
    "27": "Nourishment",
    "28": "Great Excess",
    "29": "The Abysmal",
    "30": "The Clinging",
    "31": "Influence",
    "32": "Duration",
    "33": "Retreat",
    "34": "Great Power",
    "35": "Progress",
    "36": "Darkening of the Light",
    "37": "The Family",
    "38": "Opposition",
    "39": "Obstruction",
    "40": "Deliverance",
    "41": "Decrease",
    "42": "Increase",
    "43": "Breakthrough",
    "44": "Coming to Meet",
    "45": "Gathering Together",
    "46": "Pushing Upward",
    "47": "Oppression",
    "48": "The Well",
    "49": "Revolution",
    "50": "The Cauldron",
    "51": "The Arousing",
    "52": "Keeping Still",
    "53": "Development",
    "54": "The Marrying Maiden",
    "55": "Abundance",
    "56": "The Wanderer",
    "57": "The Gentle",
    "58": "The Joyous",
    "59": "Dispersion",
    "60": "Limitation",
    "61": "Inner Truth",
    "62": "Small Excess",
    "63": "After Completion",
    "64": "Before Completion",
}

# Built-in presets
# Default card back filename patterns (matched case-insensitively, without extension)
DEFAULT_CARD_BACK_PATTERNS = [
    "cardback", "card_back", "card-back",
    "back", "deckback", "deck_back", "deck-back",
    "cover", "reverse", "verso",
    "00_back", "00-back", "00back",
    "back_00", "back-00", "back00",
]

BUILTIN_PRESETS = {
    "Tarot (RWS Ordering)": {
        "type": "Tarot",
        "mappings": STANDARD_TAROT,
        "description": "Rider-Waite-Smith ordering: 8=Strength, 11=Justice. Standard 78-card tarot deck.",
        "suit_names": {"wands": "Wands", "cups": "Cups", "swords": "Swords", "pentacles": "Pentacles"},
        "card_back_patterns": DEFAULT_CARD_BACK_PATTERNS
    },
    "Tarot (Pre-Golden Dawn Ordering)": {
        "type": "Tarot",
        "mappings": PRE_GOLDEN_DAWN_TAROT,
        "description": "Marseille/Pre-Golden Dawn ordering: 8=Justice, 11=Strength. Standard 78-card tarot deck.",
        "suit_names": {"wands": "Wands", "cups": "Cups", "swords": "Swords", "pentacles": "Pentacles"},
        "card_back_patterns": DEFAULT_CARD_BACK_PATTERNS
    },
    "Tarot (Thoth)": {
        "type": "Tarot",
        "mappings": THOTH_TAROT,
        "description": "Crowley/Harris Thoth deck: Lust, Adjustment, The Aeon, The Universe. Knight/Queen/Prince/Princess courts. Disks instead of Pentacles.",
        "suit_names": {"wands": "Wands", "cups": "Cups", "swords": "Swords", "pentacles": "Disks"},
        "card_back_patterns": DEFAULT_CARD_BACK_PATTERNS
    },
    "Tarot (Gnostic/Eternal)": {
        "type": "Tarot",
        "mappings": GNOSTIC_ETERNAL_TAROT,
        "description": "Gnostic/Samael Aun Weor system (Glorian Publishing). 78 Arcana with unique names. No traditional suits - Minor Arcana are Arcanum 23-78.",
        "suit_names": {},
        "card_back_patterns": DEFAULT_CARD_BACK_PATTERNS
    },
    "Lenormand (36 cards)": {
        "type": "Lenormand",
        "mappings": STANDARD_LENORMAND,
        "description": "Standard 36-card Lenormand deck",
        "suit_names": {"hearts": "Hearts", "diamonds": "Diamonds", "clubs": "Clubs", "spades": "Spades"},
        "card_back_patterns": DEFAULT_CARD_BACK_PATTERNS
    },
    "Kipper (36 cards)": {
        "type": "Kipper",
        "mappings": STANDARD_KIPPER,
        "description": "Traditional German 36-card Kipper fortune-telling deck",
        "suit_names": {},
        "card_back_patterns": DEFAULT_CARD_BACK_PATTERNS
    },
    "Playing Cards (52 cards)": {
        "type": "Playing Cards",
        "mappings": PLAYING_CARDS_52,
        "description": "Standard 52-card playing card deck (Hearts, Diamonds, Clubs, Spades)",
        "suit_names": {"hearts": "Hearts", "diamonds": "Diamonds", "clubs": "Clubs", "spades": "Spades"},
        "card_back_patterns": DEFAULT_CARD_BACK_PATTERNS
    },
    "Playing Cards with Jokers (54 cards)": {
        "type": "Playing Cards",
        "mappings": PLAYING_CARDS_54,
        "description": "Playing card deck with 2 jokers (52 cards + Red Joker + Black Joker)",
        "suit_names": {"hearts": "Hearts", "diamonds": "Diamonds", "clubs": "Clubs", "spades": "Spades"},
        "card_back_patterns": DEFAULT_CARD_BACK_PATTERNS
    },
    "I Ching (64 Hexagrams)": {
        "type": "I Ching",
        "mappings": I_CHING_HEXAGRAMS,
        "description": "64 I Ching Hexagrams with Chinese characters, pinyin, and English translations",
        "suit_names": {},
        "card_back_patterns": DEFAULT_CARD_BACK_PATTERNS,
        "custom_fields": [
            {"name": "Hexagram", "type": "text"},
            {"name": "Pinyin", "type": "text"},
            {"name": "Simplified Chinese", "type": "text"},
            {"name": "Traditional Chinese", "type": "text"},
        ]
    },
    "Oracle (filename only)": {
        "type": "Oracle",
        "mappings": {},
        "description": "Uses cleaned filename as card name (for custom oracle decks)",
        "suit_names": {},
        "card_back_patterns": DEFAULT_CARD_BACK_PATTERNS
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
    
    def find_card_back_image(self, folder: str, preset_name: str = None) -> Optional[str]:
        """
        Find a card back image in the folder based on preset patterns.
        Returns the full path to the card back image, or None if not found.
        """
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        folder_path = Path(folder)

        if not folder_path.exists():
            return None

        # Get patterns from preset, or use defaults
        patterns = DEFAULT_CARD_BACK_PATTERNS
        if preset_name:
            preset = self.get_preset(preset_name)
            if preset and preset.get('card_back_patterns'):
                patterns = preset['card_back_patterns']

        # Search for matching files
        for filepath in folder_path.iterdir():
            if filepath.suffix.lower() in valid_extensions:
                stem_lower = filepath.stem.lower()
                # Check for exact match with any pattern
                for pattern in patterns:
                    if stem_lower == pattern.lower():
                        return str(filepath)

        return None

    def is_card_back_file(self, filename: str, preset_name: str = None) -> bool:
        """
        Check if a filename matches card back patterns.
        """
        stem_lower = Path(filename).stem.lower()

        # Get patterns from preset, or use defaults
        patterns = DEFAULT_CARD_BACK_PATTERNS
        if preset_name:
            preset = self.get_preset(preset_name)
            if preset and preset.get('card_back_patterns'):
                patterns = preset['card_back_patterns']

        for pattern in patterns:
            if stem_lower == pattern.lower():
                return True
        return False

    def preview_import(self, folder: str, preset_name: str,
                      custom_suit_names: dict = None) -> List[Tuple[str, str, int]]:
        """
        Preview what cards would be imported from a folder.
        Returns list of (original_filename, mapped_name, sort_order) tuples.
        Excludes card back images from the list.
        """
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        results = []

        folder_path = Path(folder)
        if not folder_path.exists():
            return results

        for filepath in sorted(folder_path.iterdir()):
            if filepath.suffix.lower() in valid_extensions:
                # Skip card back images
                if self.is_card_back_file(filepath.name, preset_name):
                    continue
                mapped_name = self.map_filename_to_card(filepath.name, preset_name, custom_suit_names)
                sort_order = self._get_card_sort_order(mapped_name, custom_suit_names)
                results.append((filepath.name, mapped_name, sort_order))

        # Sort by sort order
        results.sort(key=lambda x: x[2])

        return results

    def preview_import_with_metadata(self, folder: str, preset_name: str,
                                      custom_suit_names: dict = None,
                                      custom_court_names: dict = None,
                                      archetype_mapping: str = None) -> List[dict]:
        """
        Preview what cards would be imported from a folder, including full metadata.
        Returns list of dicts with: filename, name, sort_order, archetype, rank, suit
        Excludes card back images from the list.

        custom_court_names: dict with keys 'page', 'knight', 'queen', 'king'
        archetype_mapping: 'Map to RWS archetypes', 'Map to Thoth archetypes', or 'Create new archetypes'
        """
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        results = []

        folder_path = Path(folder)
        if not folder_path.exists():
            return results

        for filepath in sorted(folder_path.iterdir()):
            if filepath.suffix.lower() in valid_extensions:
                # Skip card back images
                if self.is_card_back_file(filepath.name, preset_name):
                    continue
                mapped_name = self.map_filename_to_card(filepath.name, preset_name, custom_suit_names)
                # Apply court card name customization
                if custom_court_names:
                    mapped_name = self._apply_custom_court_names(mapped_name, custom_court_names)

                # For sort_order, use the original filename stem to extract numbers
                # This is important for presets like I Ching where the mapped name
                # loses the number (e.g., "01" -> "The Creative")
                sort_order = self._get_card_sort_order(filepath.stem, custom_suit_names,
                                                       preset_name, custom_court_names)

                # Get metadata - for I Ching, use sort_order from filename
                preset = self.get_preset(preset_name)
                preset_type = preset.get('type') if preset else None
                if preset_type == 'I Ching' and sort_order != 999:
                    metadata = self._get_iching_metadata_by_position(sort_order)
                else:
                    metadata = self.get_card_metadata(mapped_name, preset_name, custom_suit_names,
                                                      custom_court_names, archetype_mapping)

                results.append({
                    'filename': filepath.name,
                    'name': mapped_name,
                    'sort_order': sort_order,
                    'archetype': metadata.get('archetype'),
                    'rank': metadata.get('rank'),
                    'suit': metadata.get('suit'),
                    'custom_fields': metadata.get('custom_fields'),
                })

        # Sort by sort order
        results.sort(key=lambda x: x['sort_order'])

        return results
    
    def get_card_metadata(self, card_name: str, preset_name: str, custom_suit_names: dict = None,
                          custom_court_names: dict = None, archetype_mapping: str = None) -> dict:
        """
        Get full metadata for a card based on its name and the preset.
        Returns dict with: archetype, rank, suit, sort_order

        custom_court_names: dict with keys 'page', 'knight', 'queen', 'king'
        archetype_mapping: 'Map to RWS archetypes', 'Map to Thoth archetypes', or 'Create new archetypes'
        """
        preset = self.get_preset(preset_name)
        preset_type = preset.get('type', 'Oracle') if preset else 'Oracle'

        sort_order = self._get_card_sort_order(card_name, custom_suit_names, preset_name, custom_court_names)

        if preset_type == 'Tarot':
            return self._get_tarot_metadata(card_name, sort_order, custom_suit_names, preset_name,
                                            custom_court_names, archetype_mapping)
        elif preset_type == 'Lenormand':
            return self._get_lenormand_metadata(card_name, sort_order)
        elif preset_type == 'Kipper':
            return self._get_kipper_metadata(card_name, sort_order)
        elif preset_type == 'Playing Cards':
            return self._get_playing_card_metadata(card_name, sort_order)
        elif preset_type == 'I Ching':
            return self._get_iching_metadata(card_name, sort_order)
        else:
            # Oracle
            return self._get_oracle_metadata(card_name, sort_order)

    def get_card_metadata_by_sort_order(self, sort_order: int, preset_name: str) -> dict:
        """
        Get metadata for a card based purely on its sort order position (1, 2, 3...).
        This is useful when cards don't have parseable names but are in the correct order.
        Returns dict with: archetype, rank, suit, sort_order
        """
        preset = self.get_preset(preset_name)
        preset_type = preset.get('type', 'Oracle') if preset else 'Oracle'

        # Use a placeholder card name - the metadata functions will use sort_order
        placeholder_name = f"Card {sort_order}"

        if preset_type == 'Tarot':
            # Check if it's Gnostic - it uses sort_order directly
            is_gnostic = preset_name and 'gnostic' in preset_name.lower()
            if is_gnostic:
                return self._get_gnostic_tarot_metadata(placeholder_name, sort_order)
            else:
                # For standard Tarot, map sort_order to card position
                return self._get_tarot_metadata_by_position(sort_order, preset_name)
        elif preset_type == 'Lenormand':
            return self._get_lenormand_metadata_by_position(sort_order)
        elif preset_type == 'Kipper':
            return self._get_kipper_metadata_by_position(sort_order)
        elif preset_type == 'Playing Cards':
            return self._get_playing_card_metadata_by_position(sort_order)
        elif preset_type == 'I Ching':
            return self._get_iching_metadata_by_position(sort_order)
        else:
            # Oracle - just return basic info
            return {
                'archetype': placeholder_name,
                'rank': str(sort_order),
                'suit': None,
                'sort_order': sort_order
            }

    def _get_tarot_metadata_by_position(self, position: int, preset_name: str) -> dict:
        """Get Tarot metadata by numeric position (1-78)."""
        is_thoth = preset_name and 'thoth' in preset_name.lower()
        is_pre_golden_dawn = preset_name and 'pre-golden' in preset_name.lower()
        use_thoth_ordering = is_thoth or is_pre_golden_dawn

        # Major Arcana: positions 1-22 (or 0-21 depending on system)
        # We'll use 1-22 for Major, 23-78 for Minor (matching sort_order convention)
        if position <= 0 or position > 78:
            return {'archetype': None, 'rank': None, 'suit': None, 'sort_order': position}

        if position <= 22:
            # Major Arcana
            major_by_position = {
                1: ('The Fool', '0'),
                2: ('The Magician', 'I'),
                3: ('The High Priestess', 'II'),
                4: ('The Empress', 'III'),
                5: ('The Emperor', 'IV'),
                6: ('The Hierophant', 'V'),
                7: ('The Lovers', 'VI'),
                8: ('The Chariot', 'VII'),
            }
            if use_thoth_ordering:
                major_by_position.update({
                    9: ('Justice / Adjustment', 'VIII'),
                    10: ('The Hermit', 'IX'),
                    11: ('Wheel of Fortune', 'X'),
                    12: ('Strength / Lust', 'XI'),
                })
            else:
                major_by_position.update({
                    9: ('Strength / Lust', 'VIII'),
                    10: ('The Hermit', 'IX'),
                    11: ('Wheel of Fortune', 'X'),
                    12: ('Justice / Adjustment', 'XI'),
                })
            major_by_position.update({
                13: ('The Hanged Man', 'XII'),
                14: ('Death', 'XIII'),
                15: ('Temperance', 'XIV'),
                16: ('The Devil', 'XV'),
                17: ('The Tower', 'XVI'),
                18: ('The Star', 'XVII'),
                19: ('The Moon', 'XVIII'),
                20: ('The Sun', 'XIX'),
                21: ('Judgement / The Aeon', 'XX'),
                22: ('The World / The Universe', 'XXI'),
            })
            if position in major_by_position:
                name, rank = major_by_position[position]
                return {
                    'archetype': name,
                    'rank': rank,
                    'suit': 'Major Arcana',
                    'sort_order': position
                }

        # Minor Arcana: positions 23-78
        # 14 cards per suit: Ace-10 + Page/Knight/Queen/King
        minor_position = position - 22  # 1-56
        suit_index = (minor_position - 1) // 14  # 0-3
        card_in_suit = ((minor_position - 1) % 14) + 1  # 1-14

        suits = ['Wands', 'Cups', 'Swords', 'Pentacles']
        if is_thoth:
            suits[3] = 'Disks'

        if suit_index < 4:
            suit = suits[suit_index]
            if card_in_suit <= 10:
                # Pip cards
                ranks = ['Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten']
                rank_name = ranks[card_in_suit - 1]
                return {
                    'archetype': f"{rank_name} of {suit}",
                    'rank': str(card_in_suit),
                    'suit': suit,
                    'sort_order': position
                }
            else:
                # Court cards (11-14)
                if is_thoth:
                    court_names = ['Princess', 'Prince', 'Queen', 'Knight']
                    verbose_ranks = [
                        'Page / Knave / Princess / Court Card 1',
                        'Knight / Prince / Court Card 2',
                        'Queen / Court Card 3',
                        'King / Knight (Thoth) / Court Card 4'
                    ]
                else:
                    court_names = ['Page', 'Knight', 'Queen', 'King']
                    verbose_ranks = [
                        'Page / Knave / Princess / Court Card 1',
                        'Knight / Prince / Court Card 2',
                        'Queen / Court Card 3',
                        'King / Court Card 4'
                    ]
                court_idx = card_in_suit - 11  # 0-3
                return {
                    'archetype': f"{court_names[court_idx]} of {suit}",
                    'rank': verbose_ranks[court_idx],
                    'suit': suit,
                    'sort_order': position
                }

        return {'archetype': None, 'rank': None, 'suit': None, 'sort_order': position}

    def _get_lenormand_metadata_by_position(self, position: int) -> dict:
        """Get Lenormand metadata by numeric position (1-36).

        Each Lenormand card has an associated playing card rank and suit.
        """
        # Format: (archetype, playing_card_rank, playing_card_suit)
        lenormand_cards = [
            ('Rider', '9', 'Hearts'),
            ('Clover', '6', 'Diamonds'),
            ('Ship', '10', 'Spades'),
            ('House', 'King', 'Hearts'),
            ('Tree', '7', 'Hearts'),
            ('Clouds', 'King', 'Clubs'),
            ('Snake', 'Queen', 'Clubs'),
            ('Coffin', '9', 'Diamonds'),
            ('Bouquet', 'Queen', 'Spades'),
            ('Scythe', 'Jack', 'Diamonds'),
            ('Whip', 'Jack', 'Clubs'),
            ('Birds', '7', 'Diamonds'),
            ('Child', 'Jack', 'Spades'),
            ('Fox', '9', 'Clubs'),
            ('Bear', '10', 'Clubs'),
            ('Stars', '6', 'Hearts'),
            ('Stork', 'Queen', 'Hearts'),
            ('Dog', '10', 'Hearts'),
            ('Tower', '6', 'Spades'),
            ('Garden', '8', 'Spades'),
            ('Mountain', '8', 'Clubs'),
            ('Crossroads', 'Queen', 'Diamonds'),
            ('Mice', '7', 'Clubs'),
            ('Heart', 'Jack', 'Hearts'),
            ('Ring', 'Ace', 'Clubs'),
            ('Book', '10', 'Diamonds'),
            ('Letter', '7', 'Spades'),
            ('Man', 'Ace', 'Hearts'),
            ('Woman', 'Ace', 'Spades'),
            ('Lily', 'King', 'Spades'),
            ('Sun', 'Ace', 'Diamonds'),
            ('Moon', '8', 'Hearts'),
            ('Key', '8', 'Diamonds'),
            ('Fish', 'King', 'Diamonds'),
            ('Anchor', '9', 'Spades'),
            ('Cross', '6', 'Clubs'),
        ]
        if 1 <= position <= 36:
            archetype, rank, suit = lenormand_cards[position - 1]
            return {
                'archetype': archetype,
                'rank': rank,
                'suit': suit,
                'sort_order': position
            }
        return {'archetype': None, 'rank': None, 'suit': None, 'sort_order': position}

    def _get_kipper_metadata_by_position(self, position: int) -> dict:
        """Get Kipper metadata by numeric position (1-36)."""
        kipper_cards = [
            'Main Male', 'Main Female', 'Marriage', 'Rendezvous', 'Good Gentleman',
            'Good Lady', 'Pleasant Letter', 'False Person', 'A Change', 'A Journey',
            'Lots of Money', 'Rich Girl', 'Rich Good Gentleman', 'Sad News',
            'Success in Love', 'His Thoughts', 'A Gift', 'A Small Child', 'A Funeral',
            'House', 'Living Room', 'Military Person', 'Court House', 'Theft',
            'High Honours', 'Great Fortune', 'Unexpected Money', 'Expectations',
            'Prison', 'Judiciary', 'Illness', 'Grief and Adversity', 'Gloomy Thoughts',
            'Occupation', 'A Long Way', 'Hope, Great Water'
        ]
        if 1 <= position <= 36:
            card_name = kipper_cards[position - 1]
            return {
                'archetype': card_name,
                'rank': str(position),
                'suit': None,
                'sort_order': position
            }
        return {'archetype': None, 'rank': None, 'suit': None, 'sort_order': position}

    def _get_playing_card_metadata_by_position(self, position: int) -> dict:
        """Get Playing Card metadata by numeric position (1-54)."""
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = ['Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King']

        if 1 <= position <= 52:
            suit_idx = (position - 1) // 13
            rank_idx = (position - 1) % 13
            suit = suits[suit_idx]
            rank = ranks[rank_idx]
            return {
                'archetype': f"{rank} of {suit}",
                'rank': str(rank_idx + 1),
                'suit': suit,
                'sort_order': position
            }
        elif position == 53:
            return {'archetype': 'Red Joker', 'rank': '53', 'suit': 'Joker', 'sort_order': 53}
        elif position == 54:
            return {'archetype': 'Black Joker', 'rank': '54', 'suit': 'Joker', 'sort_order': 54}

        return {'archetype': None, 'rank': None, 'suit': None, 'sort_order': position}

    def _get_iching_metadata_by_position(self, position: int) -> dict:
        """Get I Ching hexagram metadata by numeric position (1-64).

        Returns metadata with:
        - archetype: English name (e.g., "The Creative")
        - rank: Hexagram number
        - suit: None (not used for I Ching)
        - custom_fields: dict with 'Hexagram', 'Pinyin', 'Simplified Chinese', 'Traditional Chinese'
        """
        # All 64 hexagrams: (unicode, simplified, traditional_if_different, pinyin, English)
        # Traditional is empty string if same as simplified
        hexagrams = [
            ('䷀', '乾', '', 'Qián', 'The Creative'),
            ('䷁', '坤', '', 'Kūn', 'The Receptive'),
            ('䷂', '屯', '', 'Zhūn', 'Difficulty at the Beginning'),
            ('䷃', '蒙', '', 'Méng', 'Youthful Folly'),
            ('䷄', '需', '', 'Xū', 'Waiting'),
            ('䷅', '讼', '訟', 'Sòng', 'Conflict'),
            ('䷆', '师', '師', 'Shī', 'The Army'),
            ('䷇', '比', '', 'Bǐ', 'Holding Together'),
            ('䷈', '小畜', '', 'Xiǎo Chù', 'Small Taming'),
            ('䷉', '履', '', 'Lǚ', 'Treading'),
            ('䷊', '泰', '', 'Tài', 'Peace'),
            ('䷋', '否', '', 'Pǐ', 'Standstill'),
            ('䷌', '同人', '', 'Tóng Rén', 'Fellowship'),
            ('䷍', '大有', '', 'Dà Yǒu', 'Great Possession'),
            ('䷎', '谦', '謙', 'Qiān', 'Modesty'),
            ('䷏', '豫', '', 'Yù', 'Enthusiasm'),
            ('䷐', '随', '隨', 'Suí', 'Following'),
            ('䷑', '蛊', '蠱', 'Gǔ', 'Work on the Decayed'),
            ('䷒', '临', '臨', 'Lín', 'Approach'),
            ('䷓', '观', '觀', 'Guān', 'Contemplation'),
            ('䷔', '噬嗑', '', 'Shì Kè', 'Biting Through'),
            ('䷕', '贲', '賁', 'Bì', 'Grace'),
            ('䷖', '剥', '剝', 'Bō', 'Splitting Apart'),
            ('䷗', '复', '復', 'Fù', 'Return'),
            ('䷘', '无妄', '無妄', 'Wú Wàng', 'Innocence'),
            ('䷙', '大畜', '', 'Dà Chù', 'Great Taming'),
            ('䷚', '颐', '頤', 'Yí', 'Nourishment'),
            ('䷛', '大过', '大過', 'Dà Guò', 'Great Excess'),
            ('䷜', '坎', '', 'Kǎn', 'The Abysmal'),
            ('䷝', '离', '離', 'Lí', 'The Clinging'),
            ('䷞', '咸', '', 'Xián', 'Influence'),
            ('䷟', '恒', '恆', 'Héng', 'Duration'),
            ('䷠', '遁', '遯', 'Dùn', 'Retreat'),
            ('䷡', '大壮', '大壯', 'Dà Zhuàng', 'Great Power'),
            ('䷢', '晋', '晉', 'Jìn', 'Progress'),
            ('䷣', '明夷', '', 'Míng Yí', 'Darkening of the Light'),
            ('䷤', '家人', '', 'Jiā Rén', 'The Family'),
            ('䷥', '睽', '', 'Kuí', 'Opposition'),
            ('䷦', '蹇', '', 'Jiǎn', 'Obstruction'),
            ('䷧', '解', '', 'Xiè', 'Deliverance'),
            ('䷨', '损', '損', 'Sǔn', 'Decrease'),
            ('䷩', '益', '', 'Yì', 'Increase'),
            ('䷪', '夬', '', 'Guài', 'Breakthrough'),
            ('䷫', '姤', '', 'Gòu', 'Coming to Meet'),
            ('䷬', '萃', '', 'Cuì', 'Gathering Together'),
            ('䷭', '升', '', 'Shēng', 'Pushing Upward'),
            ('䷮', '困', '', 'Kùn', 'Oppression'),
            ('䷯', '井', '', 'Jǐng', 'The Well'),
            ('䷰', '革', '', 'Gé', 'Revolution'),
            ('䷱', '鼎', '', 'Dǐng', 'The Cauldron'),
            ('䷲', '震', '', 'Zhèn', 'The Arousing'),
            ('䷳', '艮', '', 'Gèn', 'Keeping Still'),
            ('䷴', '渐', '漸', 'Jiàn', 'Development'),
            ('䷵', '归妹', '歸妹', 'Guī Mèi', 'The Marrying Maiden'),
            ('䷶', '丰', '豐', 'Fēng', 'Abundance'),
            ('䷷', '旅', '', 'Lǚ', 'The Wanderer'),
            ('䷸', '巽', '', 'Xùn', 'The Gentle'),
            ('䷹', '兑', '兌', 'Duì', 'The Joyous'),
            ('䷺', '涣', '渙', 'Huàn', 'Dispersion'),
            ('䷻', '节', '節', 'Jié', 'Limitation'),
            ('䷼', '中孚', '', 'Zhōng Fú', 'Inner Truth'),
            ('䷽', '小过', '小過', 'Xiǎo Guò', 'Small Excess'),
            ('䷾', '既济', '既濟', 'Jì Jì', 'After Completion'),
            ('䷿', '未济', '未濟', 'Wèi Jì', 'Before Completion'),
        ]
        if 1 <= position <= 64:
            unicode_char, simplified, traditional, pinyin, english = hexagrams[position - 1]
            return {
                'archetype': english,
                'rank': str(position),
                'suit': None,
                'sort_order': position,
                'custom_fields': {
                    'Hexagram': unicode_char,
                    'Pinyin': pinyin,
                    'Simplified Chinese': simplified,
                    'Traditional Chinese': traditional,
                }
            }
        return {'archetype': None, 'rank': None, 'suit': None, 'sort_order': position}

    def _get_tarot_metadata(self, card_name: str, sort_order: int, custom_suit_names: dict = None,
                            preset_name: str = None, custom_court_names: dict = None,
                            archetype_mapping: str = None) -> dict:
        """Get metadata for a Tarot card, respecting preset ordering and court customization.

        custom_court_names: dict with keys 'page', 'knight', 'queen', 'king' -> custom display names
        archetype_mapping: 'Map to RWS archetypes', 'Map to Thoth archetypes', or 'Create new archetypes'
        """
        name_lower = card_name.lower()

        # Handle Gnostic/Eternal Tarot - unique system with 78 numbered Arcana
        is_gnostic = preset_name and 'gnostic' in preset_name.lower()
        if is_gnostic:
            return self._get_gnostic_tarot_metadata(card_name, sort_order)

        # Determine ordering based on preset
        # RWS ordering: Strength=VIII, Justice=XI
        # Pre-Golden Dawn / Thoth ordering: Justice/Adjustment=VIII, Strength/Lust=XI
        is_thoth = preset_name and 'thoth' in preset_name.lower()
        is_pre_golden_dawn = preset_name and 'pre-golden' in preset_name.lower()
        use_thoth_ordering = is_thoth or is_pre_golden_dawn

        # Major Arcana - combined RWS/Thoth archetypes where they differ
        # Format: (archetype, rank, suit)
        # Ranks for Strength/Lust and Justice/Adjustment depend on ordering
        if use_thoth_ordering:
            strength_rank = 'XI'
            justice_rank = 'VIII'
        else:
            strength_rank = 'VIII'
            justice_rank = 'XI'

        major_arcana_names = {
            'the fool': ('The Fool', '0', 'Major Arcana'),
            'fool': ('The Fool', '0', 'Major Arcana'),
            'the magician': ('The Magician / The Magus', 'I', 'Major Arcana'),
            'magician': ('The Magician / The Magus', 'I', 'Major Arcana'),
            'the magus': ('The Magician / The Magus', 'I', 'Major Arcana'),
            'magus': ('The Magician / The Magus', 'I', 'Major Arcana'),
            'the high priestess': ('The High Priestess / The Priestess', 'II', 'Major Arcana'),
            'high priestess': ('The High Priestess / The Priestess', 'II', 'Major Arcana'),
            'the priestess': ('The High Priestess / The Priestess', 'II', 'Major Arcana'),
            'priestess': ('The High Priestess / The Priestess', 'II', 'Major Arcana'),
            'the empress': ('The Empress', 'III', 'Major Arcana'),
            'empress': ('The Empress', 'III', 'Major Arcana'),
            'the emperor': ('The Emperor', 'IV', 'Major Arcana'),
            'emperor': ('The Emperor', 'IV', 'Major Arcana'),
            'the hierophant': ('The Hierophant', 'V', 'Major Arcana'),
            'hierophant': ('The Hierophant', 'V', 'Major Arcana'),
            'the lovers': ('The Lovers', 'VI', 'Major Arcana'),
            'lovers': ('The Lovers', 'VI', 'Major Arcana'),
            'the chariot': ('The Chariot', 'VII', 'Major Arcana'),
            'chariot': ('The Chariot', 'VII', 'Major Arcana'),
            'strength': ('Strength / Lust', strength_rank, 'Major Arcana'),
            'lust': ('Strength / Lust', strength_rank, 'Major Arcana'),
            'the hermit': ('The Hermit', 'IX', 'Major Arcana'),
            'hermit': ('The Hermit', 'IX', 'Major Arcana'),
            'wheel of fortune': ('Wheel of Fortune / Fortune', 'X', 'Major Arcana'),
            'fortune': ('Wheel of Fortune / Fortune', 'X', 'Major Arcana'),
            'the wheel': ('Wheel of Fortune / Fortune', 'X', 'Major Arcana'),
            'wheel': ('Wheel of Fortune / Fortune', 'X', 'Major Arcana'),
            'justice': ('Justice / Adjustment', justice_rank, 'Major Arcana'),
            'adjustment': ('Justice / Adjustment', justice_rank, 'Major Arcana'),
            'the hanged man': ('The Hanged Man', 'XII', 'Major Arcana'),
            'hanged man': ('The Hanged Man', 'XII', 'Major Arcana'),
            'death': ('Death', 'XIII', 'Major Arcana'),
            'temperance': ('Temperance / Art', 'XIV', 'Major Arcana'),
            'art': ('Temperance / Art', 'XIV', 'Major Arcana'),
            'the devil': ('The Devil', 'XV', 'Major Arcana'),
            'devil': ('The Devil', 'XV', 'Major Arcana'),
            'the tower': ('The Tower', 'XVI', 'Major Arcana'),
            'tower': ('The Tower', 'XVI', 'Major Arcana'),
            'the star': ('The Star', 'XVII', 'Major Arcana'),
            'star': ('The Star', 'XVII', 'Major Arcana'),
            'the moon': ('The Moon', 'XVIII', 'Major Arcana'),
            'moon': ('The Moon', 'XVIII', 'Major Arcana'),
            'the sun': ('The Sun', 'XIX', 'Major Arcana'),
            'sun': ('The Sun', 'XIX', 'Major Arcana'),
            'judgement': ('Judgement / The Aeon', 'XX', 'Major Arcana'),
            'judgment': ('Judgement / The Aeon', 'XX', 'Major Arcana'),
            'the aeon': ('Judgement / The Aeon', 'XX', 'Major Arcana'),
            'aeon': ('Judgement / The Aeon', 'XX', 'Major Arcana'),
            'the world': ('The World / The Universe', 'XXI', 'Major Arcana'),
            'world': ('The World / The Universe', 'XXI', 'Major Arcana'),
            'the universe': ('The World / The Universe', 'XXI', 'Major Arcana'),
            'universe': ('The World / The Universe', 'XXI', 'Major Arcana'),
        }

        if name_lower in major_arcana_names:
            archetype, rank, suit = major_arcana_names[name_lower]
            return {
                'archetype': archetype,
                'rank': rank,
                'suit': suit,
                'sort_order': sort_order
            }

        # Minor Arcana - parse "Rank of Suit" pattern
        # Build list of all court card names to recognize (standard + custom)
        # Map from display name (lowercase) -> (position, rank_name, sort_offset)
        # Position is for archetype mapping, rank_name is what goes in metadata,
        # sort_offset is added to suit base (11, 12, 13, 14)

        # Standard rank names for each court position (based on sort offset)
        # These encompass all common names for each position
        court_rank_by_position = {
            11: 'Page / Knave / Princess / Court Card 1',
            12: 'Knight / Prince / Court Card 2',
            13: 'Queen / Court Card 3',
            14: 'King / Knight (Thoth) / Court Card 4',
        }

        # For Thoth: Princess=11, Prince=12, Queen=13, Knight=14
        # For RWS/standard: Page=11, Knight=12, Queen=13, King=14
        if is_thoth:
            # Thoth court cards - these are their own archetypes
            # Also include RWS names mapped to Thoth equivalents for compatibility
            court_card_info = {
                'princess': ('princess', 11),
                'prince': ('prince', 12),
                'queen': ('queen', 13),
                'knight': ('knight', 14),  # Thoth Knight = King position
                # RWS names mapped to Thoth positions
                'page': ('princess', 11),      # Page -> Princess position
                'knave': ('princess', 11),
                'valet': ('princess', 11),
                'king': ('knight', 14),        # King -> Knight (Thoth) position
                'cavalier': ('prince', 12),    # Cavalier -> Prince position
            }
        else:
            # Standard/RWS court cards
            court_card_info = {
                'page': ('page', 11),
                'princess': ('page', 11),  # Maps to Page archetype
                'valet': ('page', 11),
                'knave': ('page', 11),
                'knight': ('knight', 12),
                'prince': ('knight', 12),  # Maps to Knight archetype
                'cavalier': ('knight', 12),
                'queen': ('queen', 13),
                'king': ('king', 14),
            }

        # Add custom court names if provided
        if custom_court_names:
            court_card_info[custom_court_names.get('page', '').lower()] = ('page', 11)
            court_card_info[custom_court_names.get('knight', '').lower()] = ('knight', 12)
            court_card_info[custom_court_names.get('queen', '').lower()] = ('queen', 13)
            court_card_info[custom_court_names.get('king', '').lower()] = ('king', 14)
            # Remove empty string key if any custom name was empty
            court_card_info.pop('', None)

        # Pip card ranks
        rank_names = {
            'ace': 'Ace', 'two': 'Two', 'three': 'Three', 'four': 'Four', 'five': 'Five',
            'six': 'Six', 'seven': 'Seven', 'eight': 'Eight', 'nine': 'Nine', 'ten': 'Ten',
        }

        suit_names = ['wands', 'cups', 'swords', 'pentacles', 'coins', 'disks']
        if custom_suit_names:
            suit_names.extend([v.lower() for v in custom_suit_names.values()])

        # Build reverse mapping from custom suit names to standard archetypes
        # e.g., 'earth' -> 'Pentacles', 'fire' -> 'Wands'
        # Disks/Coins always map to Pentacles for archetype consistency
        suit_to_archetype = {
            'wands': 'Wands', 'cups': 'Cups', 'swords': 'Swords', 'pentacles': 'Pentacles',
            'coins': 'Pentacles', 'disks': 'Pentacles',
        }
        if custom_suit_names:
            # Map custom names back to their standard archetype suits
            if 'wands' in custom_suit_names:
                suit_to_archetype[custom_suit_names['wands'].lower()] = 'Wands'
            if 'cups' in custom_suit_names:
                suit_to_archetype[custom_suit_names['cups'].lower()] = 'Cups'
            if 'swords' in custom_suit_names:
                suit_to_archetype[custom_suit_names['swords'].lower()] = 'Swords'
            if 'pentacles' in custom_suit_names:
                suit_to_archetype[custom_suit_names['pentacles'].lower()] = 'Pentacles'

        # Check for court cards first
        # Sort by court name length (descending) to match longer names first
        for court_name in sorted(court_card_info.keys(), key=len, reverse=True):
            position, sort_offset = court_card_info[court_name]
            for suit_name in suit_names:
                if f'{court_name} of {suit_name}' in name_lower:
                    # Map to standard archetype suit
                    archetype_suit = suit_to_archetype.get(suit_name, suit_name.title())

                    # Get the standard rank name based on sort position
                    rank_name = court_rank_by_position.get(sort_offset, court_name.title())

                    # Build archetype - for Thoth, use the Thoth court names with (Thoth) suffix
                    if is_thoth:
                        # Map position to Thoth archetype name
                        thoth_archetype_names = {
                            'princess': 'Princess', 'prince': 'Prince',
                            'queen': 'Queen', 'knight': 'Knight'
                        }
                        archetype_rank = thoth_archetype_names.get(position, court_name.title())
                        archetype = f"{archetype_rank} of {archetype_suit} (Thoth)"
                    else:
                        # For non-Thoth, use the archetype mapping system
                        archetype = self._get_court_archetype(
                            position, archetype_suit, court_name.title(), archetype_mapping
                        )

                    return {
                        'archetype': archetype,
                        'rank': rank_name,
                        'suit': archetype_suit,
                        'sort_order': sort_order
                    }

        # Check for pip cards
        for rank_key, rank_val in rank_names.items():
            for suit_name in suit_names:
                if f'{rank_key} of {suit_name}' in name_lower:
                    # Map to standard archetype suit
                    archetype_suit = suit_to_archetype.get(suit_name, suit_name.title())

                    archetype = f"{rank_val} of {archetype_suit}"

                    return {
                        'archetype': archetype,
                        'rank': rank_val,
                        'suit': archetype_suit,
                        'sort_order': sort_order
                    }

        # Unknown card
        return {
            'archetype': None,
            'rank': None,
            'suit': None,
            'sort_order': sort_order
        }

    def _get_court_archetype(self, base_position: str, suit: str, display_rank: str,
                             archetype_mapping: str = None) -> str:
        """Determine the archetype for a court card based on mapping option.

        base_position: 'page', 'knight', 'queen', or 'king'
        suit: The normalized suit name (e.g., 'Wands')
        display_rank: The actual rank name displayed on the card (e.g., 'Princess')
        archetype_mapping: 'Map to RWS archetypes', 'Map to Thoth archetypes', or 'Create new archetypes'
        """
        if archetype_mapping == 'Map to RWS archetypes':
            # Map to standard RWS names: Page, Knight, Queen, King
            archetype_rank = RWS_COURT_ARCHETYPES.get(base_position, display_rank)
        elif archetype_mapping == 'Map to Thoth archetypes':
            # Map to Thoth names: Princess, Prince, Queen, Knight
            archetype_rank = THOTH_COURT_ARCHETYPES.get(base_position, display_rank)
        else:
            # Create new archetypes - use the display name as-is
            archetype_rank = display_rank

        return f"{archetype_rank} of {suit}"

    def _apply_custom_court_names(self, card_name: str, custom_court_names: dict) -> str:
        """Replace standard court card names with custom ones in a card name.

        custom_court_names: dict with keys 'page', 'knight', 'queen', 'king'
        """
        if not custom_court_names:
            return card_name

        # Map of standard names to their position key
        standard_to_position = {
            'Page': 'page', 'Princess': 'page', 'Valet': 'page',
            'Knight': 'knight', 'Prince': 'knight', 'Cavalier': 'knight',
            'Queen': 'queen',
            'King': 'king',
        }

        for standard_name, position in standard_to_position.items():
            if f'{standard_name} of ' in card_name:
                custom_name = custom_court_names.get(position)
                if custom_name and custom_name != standard_name:
                    return card_name.replace(f'{standard_name} of ', f'{custom_name} of ')

        return card_name

    def _get_gnostic_tarot_metadata(self, card_name: str, sort_order: int) -> dict:
        """Get metadata for a Gnostic/Eternal Tarot card.

        The Gnostic system has 78 Arcana numbered 1-78, each with a unique name.
        - Arcana 1-22: Major Arcana equivalent
        - Arcana 23-78: Minor Arcana equivalent (no suits, unique names)

        Metadata is assigned by sort_order (1-78).
        """
        # All 78 Arcana with their names
        gnostic_arcana = {
            1: "Arcanum 1: The Magician",
            2: "Arcanum 2: The Priestess",
            3: "Arcanum 3: The Empress",
            4: "Arcanum 4: The Emperor",
            5: "Arcanum 5: The Hierarch",
            6: "Arcanum 6: Indecision",
            7: "Arcanum 7: Triumph",
            8: "Arcanum 8: Justice",
            9: "Arcanum 9: The Hermit",
            10: "Arcanum 10: Retribution",
            11: "Arcanum 11: Persuasion",
            12: "Arcanum 12: The Apostolate",
            13: "Arcanum 13: Immortality",
            14: "Arcanum 14: Temperance",
            15: "Arcanum 15: Passion",
            16: "Arcanum 16: Fragility",
            17: "Arcanum 17: Hope",
            18: "Arcanum 18: Twilight",
            19: "Arcanum 19: Inspiration",
            20: "Arcanum 20: Resurrection",
            21: "Arcanum 21: Transmutation",
            22: "Arcanum 22: The Return",
            23: "Arcanum 23: The Plower",
            24: "Arcanum 24: The Weaver",
            25: "Arcanum 25: The Argonaut",
            26: "Arcanum 26: The Prodigy",
            27: "Arcanum 27: The Unexpected",
            28: "Arcanum 28: Uncertainty",
            29: "Arcanum 29: Domesticity",
            30: "Arcanum 30: Exchange",
            31: "Arcanum 31: Impediments",
            32: "Arcanum 32: Magnificence",
            33: "Arcanum 33: Alliance",
            34: "Arcanum 34: Innovation",
            35: "Arcanum 35: Grief",
            36: "Arcanum 36: Initiation",
            37: "Arcanum 37: Art and Science",
            38: "Arcanum 38: Duplicity",
            39: "Arcanum 39: Testimony",
            40: "Arcanum 40: Presentiment",
            41: "Arcanum 41: Uneasiness",
            42: "Arcanum 42: Preeminence",
            43: "Arcanum 43: Hallucination",
            44: "Arcanum 44: Thinking",
            45: "Arcanum 45: Regeneration",
            46: "Arcanum 46: Patrimony",
            47: "Arcanum 47: Conjecturing",
            48: "Arcanum 48: Consummation",
            49: "Arcanum 49: Versatility",
            50: "Arcanum 50: Affinity",
            51: "Arcanum 51: Counseling",
            52: "Arcanum 52: Premeditation",
            53: "Arcanum 53: Resentment",
            54: "Arcanum 54: Examination",
            55: "Arcanum 55: Contrition",
            56: "Arcanum 56: Pilgrimage",
            57: "Arcanum 57: Rivalry",
            58: "Arcanum 58: Requalification",
            59: "Arcanum 59: Revelation",
            60: "Arcanum 60: Evolution",
            61: "Arcanum 61: Solitude",
            62: "Arcanum 62: Proscription",
            63: "Arcanum 63: Communion",
            64: "Arcanum 64: Vehemence",
            65: "Arcanum 65: Learning",
            66: "Arcanum 66: Perplexity",
            67: "Arcanum 67: Friendship",
            68: "Arcanum 68: Speculation",
            69: "Arcanum 69: Chance",
            70: "Arcanum 70: Cooperation",
            71: "Arcanum 71: Avarice",
            72: "Arcanum 72: Purification",
            73: "Arcanum 73: Love and Desire",
            74: "Arcanum 74: Offering",
            75: "Arcanum 75: Generosity",
            76: "Arcanum 76: The Dispenser",
            77: "Arcanum 77: Disorientation",
            78: "Arcanum 78: Renaissance",
        }

        # Try to determine arcanum number from sort_order or card name
        arcanum_num = None

        # If sort_order is valid (1-78), use it
        if 1 <= sort_order <= 78:
            arcanum_num = sort_order
        else:
            # Try to extract number from card name (e.g., "Arcanum 23: The Plower" or just "23")
            import re
            match = re.search(r'(?:arcanum\s*)?(\d+)', card_name.lower())
            if match:
                num = int(match.group(1))
                if 1 <= num <= 78:
                    arcanum_num = num

        if arcanum_num and arcanum_num in gnostic_arcana:
            archetype = gnostic_arcana[arcanum_num]
            # Determine card type
            if arcanum_num <= 22:
                card_type = "Major Arcana"
            else:
                card_type = "Minor Arcana"

            return {
                'archetype': archetype,
                'rank': str(arcanum_num),
                'suit': card_type,
                'sort_order': arcanum_num
            }

        # Fallback - return basic info
        return {
            'archetype': card_name,
            'rank': str(sort_order) if sort_order else None,
            'suit': None,
            'sort_order': sort_order
        }

    def _get_lenormand_metadata(self, card_name: str, sort_order: int) -> dict:
        """Get metadata for a Lenormand card.

        Each Lenormand card has:
        - archetype: the card name (Rider, Clover, etc.)
        - card_number: 1-36, used for sort_order
        - rank: the playing card rank (6, 7, 8, 9, 10, Jack, Queen, King, Ace)
        - suit: the playing card suit (Hearts, Diamonds, Clubs, Spades)
        """
        # Lenormand cards with their number, playing card rank, and suit
        # Format: 'keyword': (archetype, card_number, rank, suit)
        lenormand_cards = {
            'rider': ('Rider', 1, '9', 'Hearts'),
            'clover': ('Clover', 2, '6', 'Diamonds'),
            'ship': ('Ship', 3, '10', 'Spades'),
            'house': ('House', 4, 'King', 'Hearts'),
            'tree': ('Tree', 5, '7', 'Hearts'),
            'clouds': ('Clouds', 6, 'King', 'Clubs'),
            'snake': ('Snake', 7, 'Queen', 'Clubs'),
            'coffin': ('Coffin', 8, '9', 'Diamonds'),
            'bouquet': ('Bouquet', 9, 'Queen', 'Spades'),
            'flowers': ('Bouquet', 9, 'Queen', 'Spades'),
            'scythe': ('Scythe', 10, 'Jack', 'Diamonds'),
            'whip': ('Whip', 11, 'Jack', 'Clubs'),
            'broom': ('Whip', 11, 'Jack', 'Clubs'),
            'birds': ('Birds', 12, '7', 'Diamonds'),
            'owls': ('Birds', 12, '7', 'Diamonds'),
            'child': ('Child', 13, 'Jack', 'Spades'),
            'fox': ('Fox', 14, '9', 'Clubs'),
            'bear': ('Bear', 15, '10', 'Clubs'),
            'stars': ('Stars', 16, '6', 'Hearts'),
            'stork': ('Stork', 17, 'Queen', 'Hearts'),
            'dog': ('Dog', 18, '10', 'Hearts'),
            'tower': ('Tower', 19, '6', 'Spades'),
            'garden': ('Garden', 20, '8', 'Spades'),
            'mountain': ('Mountain', 21, '8', 'Clubs'),
            'crossroads': ('Crossroads', 22, 'Queen', 'Diamonds'),
            'paths': ('Crossroads', 22, 'Queen', 'Diamonds'),
            'mice': ('Mice', 23, '7', 'Clubs'),
            'heart': ('Heart', 24, 'Jack', 'Hearts'),
            'ring': ('Ring', 25, 'Ace', 'Clubs'),
            'book': ('Book', 26, '10', 'Diamonds'),
            'letter': ('Letter', 27, '7', 'Spades'),
            'man': ('Man', 28, 'Ace', 'Hearts'),
            'gentleman': ('Man', 28, 'Ace', 'Hearts'),
            'woman': ('Woman', 29, 'Ace', 'Spades'),
            'lady': ('Woman', 29, 'Ace', 'Spades'),
            'lily': ('Lily', 30, 'King', 'Spades'),
            'lilies': ('Lily', 30, 'King', 'Spades'),
            'sun': ('Sun', 31, 'Ace', 'Diamonds'),
            'moon': ('Moon', 32, '8', 'Hearts'),
            'key': ('Key', 33, '8', 'Diamonds'),
            'fish': ('Fish', 34, 'King', 'Diamonds'),
            'anchor': ('Anchor', 35, '9', 'Spades'),
            'cross': ('Cross', 36, '6', 'Clubs'),
        }

        name_lower = card_name.lower()
        # Sort by key length descending to match longer/more specific keys first
        # (e.g., 'woman' before 'man', 'gentleman' before 'man')
        sorted_items = sorted(lenormand_cards.items(), key=lambda x: len(x[0]), reverse=True)
        for key, (archetype, card_number, rank, suit) in sorted_items:
            if key in name_lower:
                return {
                    'archetype': archetype,
                    'rank': rank,
                    'suit': suit,
                    'sort_order': card_number
                }

        return {
            'archetype': None,
            'rank': None,
            'suit': None,
            'sort_order': sort_order
        }

    def _get_kipper_metadata(self, card_name: str, sort_order: int) -> dict:
        """Get metadata for a Kipper card.

        Kipper cards have numbers 1-36 but no playing card associations.
        The card number is used for sort_order, not rank.
        """
        # Format: 'keyword': (archetype, card_number)
        kipper_cards = {
            'main male': ('Main Male', 1), 'hauptperson': ('Main Male', 1),
            'main female': ('Main Female', 2),
            'marriage': ('Marriage', 3), 'union': ('Marriage', 3),
            'meeting': ('Meeting', 4), 'rendezvous': ('Meeting', 4),
            'good gentleman': ('Good Gentleman', 5), 'good man': ('Good Gentleman', 5),
            'good lady': ('Good Lady', 6), 'good woman': ('Good Lady', 6),
            'pleasant letter': ('Pleasant Letter', 7), 'good news': ('Pleasant Letter', 7),
            'false person': ('False Person', 8), 'falsity': ('False Person', 8),
            'a change': ('A Change', 9), 'change': ('A Change', 9),
            'a journey': ('A Journey', 10), 'journey': ('A Journey', 10), 'travel': ('A Journey', 10),
            'gain money': ('Gain Money', 11), 'win money': ('Gain Money', 11), 'wealth': ('Gain Money', 11),
            'rich girl': ('Rich Girl', 12), 'wealthy girl': ('Rich Girl', 12),
            'rich man': ('Rich Man', 13), 'wealthy man': ('Rich Man', 13),
            'sad news': ('Sad News', 14), 'bad news': ('Sad News', 14),
            'success in love': ('Success in Love', 15), 'love success': ('Success in Love', 15),
            'his thoughts': ('His Thoughts', 16), 'her thoughts': ('His Thoughts', 16), 'thoughts': ('His Thoughts', 16),
            'a gift': ('A Gift', 17), 'gift': ('A Gift', 17), 'present': ('A Gift', 17),
            'a small child': ('A Small Child', 18), 'small child': ('A Small Child', 18), 'child': ('A Small Child', 18),
            'a funeral': ('A Funeral', 19), 'funeral': ('A Funeral', 19), 'death': ('A Funeral', 19),
            'house': ('House', 20), 'home': ('House', 20),
            'living room': ('Living Room', 21), 'parlor': ('Living Room', 21), 'room': ('Living Room', 21),
            'official person': ('Official Person', 22), 'military': ('Official Person', 22), 'official': ('Official Person', 22),
            'court house': ('Court House', 23), 'courthouse': ('Court House', 23),
            'theft': ('Theft', 24), 'thief': ('Theft', 24), 'stealing': ('Theft', 24),
            'high honors': ('High Honors', 25), 'honor': ('High Honors', 25), 'achievement': ('High Honors', 25),
            'great fortune': ('Great Fortune', 26), 'fortune': ('Great Fortune', 26), 'luck': ('Great Fortune', 26),
            'unexpected money': ('Unexpected Money', 27), 'surprise': ('Unexpected Money', 27),
            'expectation': ('Expectation', 28), 'hope': ('Expectation', 28), 'waiting': ('Expectation', 28),
            'prison': ('Prison', 29), 'confinement': ('Prison', 29), 'jail': ('Prison', 29),
            'court': ('Court', 30), 'legal': ('Court', 30), 'judge': ('Court', 30), 'judiciary': ('Court', 30),
            'short illness': ('Short Illness', 31), 'illness': ('Short Illness', 31), 'sickness': ('Short Illness', 31),
            'grief and adversity': ('Grief and Adversity', 32), 'grief': ('Grief and Adversity', 32), 'adversity': ('Grief and Adversity', 32), 'sorrow': ('Grief and Adversity', 32),
            'gloomy thoughts': ('Gloomy Thoughts', 33), 'sadness': ('Gloomy Thoughts', 33), 'melancholy': ('Gloomy Thoughts', 33),
            'work': ('Work', 34), 'employment': ('Work', 34), 'occupation': ('Work', 34), 'labor': ('Work', 34),
            'a long way': ('A Long Way', 35), 'long way': ('A Long Way', 35), 'long road': ('A Long Way', 35), 'distance': ('A Long Way', 35),
            'hope, great water': ('Hope, Great Water', 36), 'great water': ('Hope, Great Water', 36), 'water': ('Hope, Great Water', 36), 'ocean': ('Hope, Great Water', 36),
        }

        name_lower = card_name.lower()
        # Sort by key length descending to match longer/more specific keys first
        sorted_items = sorted(kipper_cards.items(), key=lambda x: len(x[0]), reverse=True)
        for key, (archetype, card_number) in sorted_items:
            if key in name_lower:
                return {
                    'archetype': archetype,
                    'rank': None,
                    'suit': None,
                    'sort_order': card_number
                }

        return {
            'archetype': None,
            'rank': None,
            'suit': None,
            'sort_order': sort_order
        }

    def _get_playing_card_metadata(self, card_name: str, sort_order: int) -> dict:
        """Get metadata for a Playing Card"""
        name_lower = card_name.lower()

        # Jokers
        if 'joker' in name_lower:
            if 'red' in name_lower:
                return {'archetype': 'Red Joker', 'rank': 'Joker', 'suit': None, 'sort_order': sort_order}
            elif 'black' in name_lower:
                return {'archetype': 'Black Joker', 'rank': 'Joker', 'suit': None, 'sort_order': sort_order}
            else:
                return {'archetype': 'Joker', 'rank': 'Joker', 'suit': None, 'sort_order': sort_order}

        # Rank names - both word and numeric forms
        rank_names = {
            'ace': 'Ace', 'a': 'Ace',
            'two': 'Two', '2': 'Two',
            'three': 'Three', '3': 'Three',
            'four': 'Four', '4': 'Four',
            'five': 'Five', '5': 'Five',
            'six': 'Six', '6': 'Six',
            'seven': 'Seven', '7': 'Seven',
            'eight': 'Eight', '8': 'Eight',
            'nine': 'Nine', '9': 'Nine',
            'ten': 'Ten', '10': 'Ten',
            'jack': 'Jack', 'j': 'Jack',
            'queen': 'Queen', 'q': 'Queen',
            'king': 'King', 'k': 'King',
        }

        suit_names = ['hearts', 'diamonds', 'clubs', 'spades']

        for rank_key, rank_val in rank_names.items():
            for suit_name in suit_names:
                if f'{rank_key} of {suit_name}' in name_lower:
                    archetype = f"{rank_val} of {suit_name.title()}"
                    return {
                        'archetype': archetype,
                        'rank': rank_val,
                        'suit': suit_name.title(),
                        'sort_order': sort_order
                    }

        return {
            'archetype': None,
            'rank': None,
            'suit': None,
            'sort_order': sort_order
        }

    def _get_iching_metadata(self, card_name: str, sort_order: int) -> dict:
        """Get metadata for an I Ching hexagram.

        Tries to parse hexagram number from card name, falls back to sort_order.
        """
        name_lower = card_name.lower().strip()

        # Try to extract hexagram number from the card name
        # Match patterns like "Hexagram 1", "1.", "01", "01_the_creative", etc.
        # First try at the start of the name
        match = re.match(r'^(?:hexagram\s*)?(\d+)', name_lower)
        if match:
            hex_num = int(match.group(1))
            if 1 <= hex_num <= 64:
                return self._get_iching_metadata_by_position(hex_num)

        # Try to find any number in the name (e.g., from filename like "hexagram_01.jpg")
        all_numbers = re.findall(r'(\d+)', name_lower)
        for num_str in all_numbers:
            hex_num = int(num_str)
            if 1 <= hex_num <= 64:
                return self._get_iching_metadata_by_position(hex_num)

        # Fall back to position-based
        return self._get_iching_metadata_by_position(sort_order)

    def _get_oracle_metadata(self, card_name: str, sort_order: int) -> dict:
        """Get metadata for an Oracle card.

        If the card name starts with a number, use that as the sort order.
        Oracle cards don't have standard archetypes, ranks, or suits.
        """
        # Try to extract a leading number from the card name for sort order
        match = re.match(r'^(\d+)', card_name.strip())
        if match:
            sort_order = int(match.group(1))

        return {
            'archetype': None,
            'rank': None,
            'suit': None,
            'sort_order': sort_order
        }

    def _get_card_sort_order(self, card_name: str, custom_suit_names: dict = None,
                             preset_name: str = None, custom_court_names: dict = None) -> int:
        """Get sort order: Major Arcana (0-21), then Wands, Cups, Swords, Pentacles for Tarot.
        For Playing Cards: Jokers (1-2), then Spades=1xx, Hearts=2xx, Clubs=3xx, Diamonds=4xx.
        For I Ching: Hexagram number (1-64).
        Respects preset ordering for Strength/Justice swap.

        Court cards are always ordered: first court=11, second=12, third=13, fourth=14
        regardless of their display names (Page, Knave, Princess, etc.)"""
        name_lower = card_name.lower()

        # Check preset type
        preset = self.get_preset(preset_name) if preset_name else None
        preset_type = preset.get('type') if preset else None

        # I Ching: extract hexagram number from filename/name
        if preset_type == 'I Ching':
            # First try at the start of the name
            match = re.match(r'^(?:hexagram\s*)?(\d+)', name_lower)
            if match:
                hex_num = int(match.group(1))
                if 1 <= hex_num <= 64:
                    return hex_num
            # Try to find any number in the name
            all_numbers = re.findall(r'(\d+)', name_lower)
            for num_str in all_numbers:
                hex_num = int(num_str)
                if 1 <= hex_num <= 64:
                    return hex_num
            return 999  # Unknown

        is_playing_cards = preset_type == 'Playing Cards'

        if is_playing_cards:
            return self._get_playing_card_sort_order(name_lower)

        # Determine ordering based on preset
        # RWS ordering: Strength=8, Justice=11
        # Pre-Golden Dawn / Thoth ordering: Justice/Adjustment=8, Strength/Lust=11
        is_thoth = preset_name and 'thoth' in preset_name.lower()
        is_pre_golden_dawn = preset_name and 'pre-golden' in preset_name.lower()
        use_thoth_ordering = is_thoth or is_pre_golden_dawn

        if use_thoth_ordering:
            strength_order = 11
            justice_order = 8
        else:
            strength_order = 8
            justice_order = 11

        # Major arcana order
        major_arcana = {
            'the fool': 0, 'fool': 0,
            'the magician': 1, 'magician': 1, 'the magus': 1, 'magus': 1,
            'the high priestess': 2, 'high priestess': 2, 'the priestess': 2, 'priestess': 2,
            'the empress': 3, 'empress': 3,
            'the emperor': 4, 'emperor': 4,
            'the hierophant': 5, 'hierophant': 5,
            'the lovers': 6, 'lovers': 6,
            'the chariot': 7, 'chariot': 7,
            'strength': strength_order, 'lust': strength_order,
            'the hermit': 9, 'hermit': 9,
            'wheel of fortune': 10, 'fortune': 10, 'the wheel': 10, 'wheel': 10,
            'justice': justice_order, 'adjustment': justice_order,
            'the hanged man': 12, 'hanged man': 12,
            'death': 13,
            'temperance': 14, 'art': 14,
            'the devil': 15, 'devil': 15,
            'the tower': 16, 'tower': 16,
            'the star': 17, 'star': 17,
            'the moon': 18, 'moon': 18,
            'the sun': 19, 'sun': 19,
            'judgement': 20, 'judgment': 20, 'the aeon': 20, 'aeon': 20,
            'the world': 21, 'world': 21, 'the universe': 21, 'universe': 21,
        }

        if name_lower in major_arcana:
            return major_arcana[name_lower]

        # Pip card rank order within suits (Ace-Ten = 1-10 for sort order calculation)
        pip_rank_order = {
            'ace': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        }

        # Court card positions - map to fixed sort offsets (11, 12, 13, 14)
        # For Thoth: Princess=11, Prince=12, Queen=13, Knight=14
        # For RWS/standard: Page=11, Knight=12, Queen=13, King=14
        is_thoth = preset_name and 'thoth' in preset_name.lower()

        if is_thoth:
            court_positions = {
                'princess': 11,
                'prince': 12,
                'queen': 13,
                'knight': 14,  # Thoth Knight = King position
            }
        else:
            court_positions = {
                'page': 11, 'princess': 11, 'jack': 11, 'knave': 11, 'valet': 11,
                'knight': 12, 'prince': 12, 'cavalier': 12,
                'queen': 13,
                'king': 14,
            }

        # Add custom court names if provided - they map to their position's sort order
        if custom_court_names:
            if custom_court_names.get('page'):
                court_positions[custom_court_names['page'].lower()] = 11
            if custom_court_names.get('knight'):
                court_positions[custom_court_names['knight'].lower()] = 12
            if custom_court_names.get('queen'):
                court_positions[custom_court_names['queen'].lower()] = 13
            if custom_court_names.get('king'):
                court_positions[custom_court_names['king'].lower()] = 14

        # Get suit names (custom or default)
        suit_names = custom_suit_names or {}
        wands_name = suit_names.get('wands', 'Wands').lower()
        cups_name = suit_names.get('cups', 'Cups').lower()
        swords_name = suit_names.get('swords', 'Swords').lower()
        pentacles_name = suit_names.get('pentacles', 'Pentacles').lower()

        # Suit base values for Minor Arcana
        # Wands: 100-114, Cups: 200-214, Swords: 300-314, Pentacles: 400-414
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
                # Check court cards first (sort by length to match longer names first)
                for court_name in sorted(court_positions.keys(), key=len, reverse=True):
                    if name_lower.startswith(court_name):
                        return base + court_positions[court_name]
                # Check pip cards
                for rank, rank_val in pip_rank_order.items():
                    if name_lower.startswith(rank):
                        return base + rank_val
                return base + 50  # Unknown rank

        return 999  # Unknown cards at end

    def _get_playing_card_sort_order(self, name_lower: str) -> int:
        """Get sort order for playing cards.
        Jokers: 1 (Red), 2 (Black)
        Suits: Spades=1xx, Hearts=2xx, Clubs=3xx, Diamonds=4xx
        Ranks: Two=01, Three=02, ... Ten=09, Jack=10, Queen=11, King=12, Ace=13
        Order within suit: 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A
        Examples: Two of Spades=101, Ace of Spades=113, Two of Hearts=201, Ace of Diamonds=413
        """
        # Jokers first
        if 'joker' in name_lower:
            if 'red' in name_lower:
                return 1
            elif 'black' in name_lower:
                return 2
            else:
                return 1  # Default joker to 1

        # Suit base values
        suit_bases = {
            'spades': 100,
            'hearts': 200,
            'clubs': 300,
            'diamonds': 400,
        }

        # Rank values (2-A order: 2=1, 3=2, ..., K=12, A=13)
        # Include both word and numeric forms
        rank_values = {
            'two': 1, '2': 1,
            'three': 2, '3': 2,
            'four': 3, '4': 3,
            'five': 4, '5': 4,
            'six': 5, '6': 5,
            'seven': 6, '7': 6,
            'eight': 7, '8': 7,
            'nine': 8, '9': 8,
            'ten': 9, '10': 9,
            'jack': 10, 'j': 10,
            'queen': 11, 'q': 11,
            'king': 12, 'k': 12,
            'ace': 13, 'a': 13,
        }

        # Find suit and rank
        for suit_name, base in suit_bases.items():
            if f'of {suit_name}' in name_lower:
                for rank, rank_val in rank_values.items():
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

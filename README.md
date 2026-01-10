# Tarot Journal v0.3.32

A modern journaling app for tarot, lenormand, and oracle card readings.

## Features

- **Card Library**: Organize decks by type (Tarot, Lenormand, Oracle)
- **Visual Spread Designer**: Create and save custom card layouts with drag-and-drop
- **Journal Entries**: Record readings with rich text notes
- **Auto-Tagging**: Entries automatically tagged with deck, spread, and card info
- **Search & Filter**: Find entries by text, tags, deck, or spread
- **Import Presets**: Smart filename-to-card mapping for bulk imports
- **Fast Thumbnails**: Cached thumbnails for quick image loading
- **Statistics**: Track your most-used decks and spreads
- **Cross-Platform**: Works on macOS, Windows, and Linux

## Requirements

- Python 3.9+
- wxPython
- Pillow

## Installation

1. Extract the files to a folder
2. Install dependencies:
   ```bash
   pip3 install wxPython Pillow
   ```
   
   Note: wxPython installation may take a few minutes as it compiles native components.

3. Run the app:
   ```bash
   python3 main.py
   ```

### Alternative: tkinter version

A tkinter-based version is included as `main_tk.py` if you prefer not to install wxPython:
```bash
pip3 install Pillow
python3 main_tk.py
```

## Quick Start

### Adding a Deck

1. Go to **Card Library** tab
2. Click **Import Folder** to import a folder of card images
3. Select an import preset (Standard Tarot, Lenormand, or Oracle)
4. Preview the card name mappings and click **Import**

### Using Import Presets

The app includes built-in presets for:
- **Standard Tarot (78 cards)**: Maps common filename patterns to card names
- **Lenormand (36 cards)**: Maps numbered/named files to Lenormand cards
- **Oracle (filename only)**: Uses cleaned filenames as card names

Create custom presets in **Settings** → **Import Presets**:
1. Click **+ New Preset**
2. Enter mappings in format: `filename → Card Name`
3. Save for future imports

### Recording a Reading

1. Go to **Journal** tab
2. Click **+ New Entry**
3. Select a spread and deck
4. Click card positions to assign cards
5. Write your notes and click **Save Entry**

### Creating Spreads

1. Go to **Spreads** tab
2. Click **+ New**
3. Click **+ Add Position** to add card positions
4. Drag positions to arrange them on the canvas
5. Right-click positions to delete them
6. Enter a name and click **Save Spread**

## File Organization

Recommended folder structure for card images:
```
Decks/
├── Rider-Waite/
│   ├── 00_fool.jpg
│   ├── 01_magician.jpg
│   └── ...
├── Lenormand-Classic/
│   ├── 01_rider.jpg
│   ├── 02_clover.jpg
│   └── ...
└── My-Oracle/
    ├── card1.jpg
    └── ...
```

## Settings

### Appearance / Themes
Customize the app's look and feel:
- **Preset Themes**: Choose from Dark (default), Light, Midnight Purple, or Forest Green
- **Custom Colors**: Edit all colors using hex values (#RRGGBB) with live preview
- **Live Preview**: Theme changes apply immediately without restarting
- **Import/Export**: Share themes as JSON files

### Import Presets
Configure filename-to-card mappings for different deck types. Built-in presets handle common naming conventions automatically.

### Thumbnail Cache
The app creates small thumbnail versions of card images for faster loading. You can:
- View cache size and count
- Clear the cache if needed (thumbnails regenerate automatically)

## Data Storage

- **Database**: `tarot_journal.db` (SQLite)
- **Thumbnails**: `.thumbnail_cache/` folder
- **Presets**: `import_presets.json`
- **Theme**: `theme_config.json`

All data is stored in the app folder.

## Troubleshooting

**App won't start:**
- Ensure Python 3.9+ is installed: `python3 --version`
- Install Pillow: `pip3 install Pillow`

**Images not loading:**
- Check that image files exist at their original paths
- Supported formats: JPG, PNG, GIF, WebP

**Slow performance:**
- The first time you view a deck, thumbnails are generated
- Subsequent views will be much faster
- Check Settings → Thumbnail Cache for cache status

## Customization

### Adding Cartomancy Types
Edit `database.py` to add new types in `create_default_spreads()`.

### Theme Colors
Edit the `COLORS` dictionary in `main.py` to customize the appearance.

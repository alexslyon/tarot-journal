#!/usr/bin/env python3
"""
Tarot Journal - A journaling app for cartomancy
wxPython GUI version
"""

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb
from PIL import Image
import json
import os
import re
from datetime import datetime
from pathlib import Path
from database import Database, create_default_spreads, create_default_decks
from thumbnail_cache import get_cache
from import_presets import get_presets, BUILTIN_PRESETS
from theme_config import get_theme, PRESET_THEMES

# Version
VERSION = "0.3.32"

# Load theme
_theme = get_theme()
COLORS = _theme.get_colors()
_fonts_config = _theme.get_fonts()


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_wx_color(key):
    """Get a wx.Colour from theme"""
    return wx.Colour(*hex_to_rgb(COLORS.get(key, '#000000')))


class TarotJournalApp(wx.App):
    def OnInit(self):
        frame = MainFrame()
        frame.Show()
        return True


class MainFrame(wx.Frame):
    def __init__(self):
        # Get screen size and set window to 85% of it, with max bounds
        display = wx.Display()
        screen_rect = display.GetClientArea()
        width = min(1200, int(screen_rect.width * 0.85))
        height = min(800, int(screen_rect.height * 0.85))
        
        super().__init__(None, title="Tarot Journal", size=(width, height))
        
        # Initialize systems
        self.db = Database()
        create_default_spreads(self.db)
        create_default_decks(self.db)
        self.thumb_cache = get_cache()
        self.presets = get_presets()
        
        # State
        self.current_entry_id = None
        self.selected_deck_id = None
        self.selected_card_ids = set()  # Multi-select support
        self.editing_spread_id = None
        self.designer_positions = []
        self.drag_data = {'idx': None, 'offset_x': 0, 'offset_y': 0}
        self._current_deck_id_for_cards = None
        self._current_cards_sorted = []
        self._current_cards_categorized = {}
        self._current_suit_names = {}
        self._current_deck_type = 'Tarot'
        self._card_widgets = {}  # Track card widgets by card_id
        self.show_card_names = True  # Display option for card names
        
        # Bitmap cache
        self.bitmap_cache = {}
        
        # Set up UI
        self.SetBackgroundColour(get_wx_color('bg_primary'))
        self._create_ui()
        self._refresh_all()
        
        # Center on screen
        self.Centre()
        
        # Force refresh of all colors after everything is built
        wx.CallAfter(self._refresh_all_colors)
    
    def _refresh_all_colors(self):
        """Refresh all widget colors - needed after initial render"""
        self._update_widget_colors(self)
        self._refresh_notebook_colors()
    
    def _refresh_notebook_colors(self):
        """Refresh notebook tab colors - needed after initial render"""
        # Main notebook
        self.notebook.SetTabAreaColour(get_wx_color('bg_primary'))
        self.notebook.SetActiveTabColour(get_wx_color('bg_tertiary'))
        self.notebook.SetNonActiveTabTextColour(get_wx_color('text_primary'))
        self.notebook.SetActiveTabTextColour(get_wx_color('text_primary'))
        self.notebook.SetGradientColourTo(get_wx_color('bg_tertiary'))
        self.notebook.SetGradientColourFrom(get_wx_color('bg_secondary'))
        self.notebook.Refresh()
        self.notebook.Update()
    
    def _create_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Header
        header = wx.Panel(self)
        header.SetBackgroundColour(get_wx_color('bg_primary'))
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        title = wx.StaticText(header, label="Tarot Journal")
        title.SetForegroundColour(get_wx_color('text_primary'))
        title.SetFont(wx.Font(22, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        header_sizer.Add(title, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        
        header_sizer.AddStretchSpacer()
        
        stats_btn = wx.Button(header, label="Stats")
        stats_btn.Bind(wx.EVT_BUTTON, self._on_stats)
        header_sizer.Add(stats_btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        
        header.SetSizer(header_sizer)
        main_sizer.Add(header, 0, wx.EXPAND)
        
        # FlatNotebook with full color control
        style = (fnb.FNB_NO_X_BUTTON | fnb.FNB_NO_NAV_BUTTONS | 
                fnb.FNB_NODRAG | fnb.FNB_VC8)
        self.notebook = fnb.FlatNotebook(self, agwStyle=style)
        
        # Apply theme colors to notebook - dark tabs with light text
        self.notebook.SetTabAreaColour(get_wx_color('bg_primary'))
        self.notebook.SetActiveTabColour(get_wx_color('bg_tertiary'))
        self.notebook.SetNonActiveTabTextColour(get_wx_color('text_primary'))
        self.notebook.SetActiveTabTextColour(get_wx_color('text_primary'))
        self.notebook.SetGradientColourTo(get_wx_color('bg_tertiary'))
        self.notebook.SetGradientColourFrom(get_wx_color('bg_secondary'))
        
        self.journal_panel = self._create_journal_panel()
        self.library_panel = self._create_library_panel()
        self.spreads_panel = self._create_spreads_panel()
        self.settings_panel = self._create_settings_panel()
        
        self.notebook.AddPage(self.journal_panel, "Journal")
        self.notebook.AddPage(self.library_panel, "Card Library")
        self.notebook.AddPage(self.spreads_panel, "Spreads")
        self.notebook.AddPage(self.settings_panel, "Settings")
        
        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
    
    # ═══════════════════════════════════════════
    # JOURNAL PANEL
    # ═══════════════════════════════════════════
    def _create_journal_panel(self):
        panel = wx.Panel(self.notebook)
        panel.SetBackgroundColour(get_wx_color('bg_primary'))
        
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)
        splitter.SetBackgroundColour(get_wx_color('bg_primary'))
        splitter.SetMinimumPaneSize(250)
        
        # Left: Entry list
        left = wx.Panel(splitter)
        left.SetBackgroundColour(get_wx_color('bg_primary'))
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Search
        self.search_ctrl = wx.SearchCtrl(left)
        self.search_ctrl.Bind(wx.EVT_SEARCH, self._on_search)
        self.search_ctrl.Bind(wx.EVT_TEXT, self._on_search)
        left_sizer.Add(self.search_ctrl, 0, wx.EXPAND | wx.ALL, 5)
        
        # Tag filter
        self.tag_filter = wx.Choice(left)
        self.tag_filter.Bind(wx.EVT_CHOICE, self._on_tag_filter)
        left_sizer.Add(self.tag_filter, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Entry list
        self.entry_list = wx.ListCtrl(left, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.entry_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.entry_list.SetForegroundColour(get_wx_color('text_primary'))
        self.entry_list.InsertColumn(0, "Date", width=90)
        self.entry_list.InsertColumn(1, "Title", width=180)
        self.entry_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_entry_select)
        left_sizer.Add(self.entry_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        new_btn = wx.Button(left, label="+ New Entry")
        new_btn.Bind(wx.EVT_BUTTON, self._on_new_entry_dialog)
        btn_sizer.Add(new_btn, 0, wx.RIGHT, 5)
        
        edit_btn = wx.Button(left, label="Edit")
        edit_btn.Bind(wx.EVT_BUTTON, self._on_edit_entry_dialog)
        btn_sizer.Add(edit_btn, 0, wx.RIGHT, 5)
        
        del_btn = wx.Button(left, label="Delete")
        del_btn.Bind(wx.EVT_BUTTON, self._on_delete_entry)
        btn_sizer.Add(del_btn, 0)
        
        left_sizer.Add(btn_sizer, 0, wx.ALL, 5)
        left.SetSizer(left_sizer)
        
        # Right: Entry Viewer (read-only)
        self.viewer_panel = scrolled.ScrolledPanel(splitter)
        self.viewer_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        self.viewer_panel.SetupScrolling()
        self.viewer_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Placeholder text
        self.viewer_placeholder = wx.StaticText(self.viewer_panel, label="Select an entry to view")
        self.viewer_placeholder.SetForegroundColour(get_wx_color('text_secondary'))
        self.viewer_placeholder.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        self.viewer_sizer.Add(self.viewer_placeholder, 0, wx.ALL, 20)
        
        self.viewer_panel.SetSizer(self.viewer_sizer)
        
        splitter.SplitVertically(left, self.viewer_panel, 300)
        
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(splitter, 1, wx.EXPAND)
        panel.SetSizer(panel_sizer)
        
        return panel
    
    # ═══════════════════════════════════════════
    # LIBRARY PANEL
    # ═══════════════════════════════════════════
    def _create_library_panel(self):
        panel = wx.Panel(self.notebook)
        panel.SetBackgroundColour(get_wx_color('bg_primary'))
        
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)
        splitter.SetBackgroundColour(get_wx_color('bg_primary'))
        splitter.SetMinimumPaneSize(250)
        
        # Left: Deck list
        left = wx.Panel(splitter)
        left.SetBackgroundColour(get_wx_color('bg_primary'))
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        
        decks_label = wx.StaticText(left, label="Decks")
        decks_label.SetForegroundColour(get_wx_color('text_primary'))
        left_sizer.Add(decks_label, 0, wx.ALL, 5)
        
        # Type filter
        self.type_filter = wx.Choice(left, choices=['All', 'Tarot', 'Lenormand', 'Oracle'])
        self.type_filter.SetSelection(0)
        self.type_filter.Bind(wx.EVT_CHOICE, self._on_type_filter)
        left_sizer.Add(self.type_filter, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Deck list
        self.deck_list = wx.ListCtrl(left, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.deck_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.deck_list.SetForegroundColour(get_wx_color('text_primary'))
        self.deck_list.InsertColumn(0, "Name", width=140)
        self.deck_list.InsertColumn(1, "Type", width=80)
        self.deck_list.InsertColumn(2, "#", width=40)
        self.deck_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_deck_select)
        self.deck_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_edit_deck)
        left_sizer.Add(self.deck_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Buttons - vertical stack for cleaner look
        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Add and Import on first row
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(left, label="+ Add")
        add_btn.Bind(wx.EVT_BUTTON, self._on_add_deck)
        row1.Add(add_btn, 1, wx.RIGHT, 5)
        
        import_btn = wx.Button(left, label="Import Folder")
        import_btn.Bind(wx.EVT_BUTTON, self._on_import_folder)
        row1.Add(import_btn, 1)
        btn_sizer.Add(row1, 0, wx.EXPAND | wx.BOTTOM, 5)
        
        # Edit and Delete on second row
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        edit_deck_btn = wx.Button(left, label="Edit Deck")
        edit_deck_btn.Bind(wx.EVT_BUTTON, self._on_edit_deck)
        row2.Add(edit_deck_btn, 1, wx.RIGHT, 5)
        
        del_btn = wx.Button(left, label="Delete")
        del_btn.Bind(wx.EVT_BUTTON, self._on_delete_deck)
        row2.Add(del_btn, 1)
        btn_sizer.Add(row2, 0, wx.EXPAND)
        
        left_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)
        left.SetSizer(left_sizer)
        
        # Right: Cards grid with filter
        right = wx.Panel(splitter)
        right.SetBackgroundColour(get_wx_color('bg_primary'))
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Header row with title and filter
        header_row = wx.BoxSizer(wx.HORIZONTAL)
        
        self.deck_title = wx.StaticText(right, label="Select a deck")
        self.deck_title.SetForegroundColour(get_wx_color('text_primary'))
        self.deck_title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        header_row.Add(self.deck_title, 0, wx.ALIGN_CENTER_VERTICAL)
        
        header_row.AddStretchSpacer()
        
        # Show card names checkbox with separate label for better visibility
        self.show_card_names_cb = wx.CheckBox(right, label="")
        self.show_card_names_cb.SetValue(self.show_card_names)
        self.show_card_names_cb.Bind(wx.EVT_CHECKBOX, self._on_toggle_card_names)
        header_row.Add(self.show_card_names_cb, 0, wx.ALIGN_CENTER_VERTICAL)
        
        names_label = wx.StaticText(right, label="Show names")
        names_label.SetForegroundColour(get_wx_color('text_primary'))
        names_label.Bind(wx.EVT_LEFT_DOWN, lambda e: self._toggle_card_names_checkbox())
        header_row.Add(names_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        
        # Card filter dropdown
        filter_label = wx.StaticText(right, label="Filter:")
        filter_label.SetForegroundColour(get_wx_color('text_primary'))
        header_row.Add(filter_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        self.card_filter_names = ['All', 'Major Arcana', 'Wands', 'Cups', 'Swords', 'Pentacles']
        self.card_filter_choice = wx.Choice(right, choices=self.card_filter_names)
        self.card_filter_choice.SetSelection(0)
        self.card_filter_choice.Bind(wx.EVT_CHOICE, self._on_card_filter_change)
        header_row.Add(self.card_filter_choice, 0, wx.ALIGN_CENTER_VERTICAL)
        
        right_sizer.Add(header_row, 0, wx.EXPAND | wx.ALL, 10)
        
        # Single scrolled panel for cards (filtered dynamically)
        self.cards_scroll = scrolled.ScrolledPanel(right)
        self.cards_scroll.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.cards_scroll.SetupScrolling()
        self.cards_sizer = wx.WrapSizer(wx.HORIZONTAL)
        self.cards_scroll.SetSizer(self.cards_sizer)
        
        right_sizer.Add(self.cards_scroll, 1, wx.EXPAND | wx.ALL, 5)
        
        # Card buttons
        card_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_card_btn = wx.Button(right, label="+ Add Card")
        add_card_btn.Bind(wx.EVT_BUTTON, self._on_add_card)
        card_btn_sizer.Add(add_card_btn, 0, wx.RIGHT, 5)
        
        import_cards_btn = wx.Button(right, label="Import Images")
        import_cards_btn.Bind(wx.EVT_BUTTON, self._on_import_cards)
        card_btn_sizer.Add(import_cards_btn, 0, wx.RIGHT, 5)
        
        edit_card_btn = wx.Button(right, label="Edit Selected")
        edit_card_btn.Bind(wx.EVT_BUTTON, self._on_edit_card)
        card_btn_sizer.Add(edit_card_btn, 0, wx.RIGHT, 5)
        
        del_card_btn = wx.Button(right, label="Delete Selected")
        del_card_btn.Bind(wx.EVT_BUTTON, self._on_delete_card)
        card_btn_sizer.Add(del_card_btn, 0)
        
        right_sizer.Add(card_btn_sizer, 0, wx.ALL, 10)
        right.SetSizer(right_sizer)
        
        splitter.SplitVertically(left, right, 280)
        
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(splitter, 1, wx.EXPAND)
        panel.SetSizer(panel_sizer)
        
        return panel
    
    # ═══════════════════════════════════════════
    # SPREADS PANEL
    # ═══════════════════════════════════════════
    def _create_spreads_panel(self):
        panel = wx.Panel(self.notebook)
        panel.SetBackgroundColour(get_wx_color('bg_primary'))
        
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)
        splitter.SetBackgroundColour(get_wx_color('bg_primary'))
        splitter.SetMinimumPaneSize(200)
        
        # Left: Spread list
        left = wx.Panel(splitter)
        left.SetBackgroundColour(get_wx_color('bg_primary'))
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        
        spreads_label = wx.StaticText(left, label="Spreads")
        spreads_label.SetForegroundColour(get_wx_color('text_primary'))
        left_sizer.Add(spreads_label, 0, wx.ALL, 5)
        
        self.spread_list = wx.ListCtrl(left, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER)
        self.spread_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.spread_list.SetForegroundColour(get_wx_color('text_primary'))
        self.spread_list.SetTextColour(get_wx_color('text_primary'))
        self.spread_list.InsertColumn(0, "", width=230)
        self.spread_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_spread_select)
        left_sizer.Add(self.spread_list, 1, wx.EXPAND | wx.ALL, 5)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        new_btn = wx.Button(left, label="+ New")
        new_btn.Bind(wx.EVT_BUTTON, self._on_new_spread)
        btn_sizer.Add(new_btn, 0, wx.RIGHT, 5)
        
        del_btn = wx.Button(left, label="Delete")
        del_btn.Bind(wx.EVT_BUTTON, self._on_delete_spread)
        btn_sizer.Add(del_btn, 0)
        
        left_sizer.Add(btn_sizer, 0, wx.ALL, 5)
        left.SetSizer(left_sizer)
        
        # Right: Designer
        right = wx.Panel(splitter)
        right.SetBackgroundColour(get_wx_color('bg_primary'))
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Name/description
        meta_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(right, label="Name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        meta_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.spread_name_ctrl = wx.TextCtrl(right, size=(200, -1))
        self.spread_name_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        self.spread_name_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        meta_sizer.Add(self.spread_name_ctrl, 0, wx.RIGHT, 20)
        
        desc_label = wx.StaticText(right, label="Description:")
        desc_label.SetForegroundColour(get_wx_color('text_primary'))
        meta_sizer.Add(desc_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.spread_desc_ctrl = wx.TextCtrl(right)
        self.spread_desc_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        self.spread_desc_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        meta_sizer.Add(self.spread_desc_ctrl, 1)
        
        right_sizer.Add(meta_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Instructions
        instr = wx.StaticText(right, label="Drag positions to arrange • Right-click to delete")
        instr.SetForegroundColour(get_wx_color('text_dim'))
        right_sizer.Add(instr, 0, wx.LEFT, 10)
        
        # Designer canvas
        self.designer_canvas = wx.Panel(right, size=(-1, 450))
        self.designer_canvas.SetBackgroundColour(get_wx_color('card_slot'))
        self.designer_canvas.Bind(wx.EVT_PAINT, self._on_designer_paint)
        self.designer_canvas.Bind(wx.EVT_LEFT_DOWN, self._on_designer_left_down)
        self.designer_canvas.Bind(wx.EVT_LEFT_UP, self._on_designer_left_up)
        self.designer_canvas.Bind(wx.EVT_MOTION, self._on_designer_motion)
        self.designer_canvas.Bind(wx.EVT_RIGHT_DOWN, self._on_designer_right_down)
        right_sizer.Add(self.designer_canvas, 1, wx.EXPAND | wx.ALL, 10)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_pos_btn = wx.Button(right, label="+ Add Position")
        add_pos_btn.Bind(wx.EVT_BUTTON, self._on_add_position)
        btn_sizer.Add(add_pos_btn, 0, wx.RIGHT, 10)
        
        clear_btn = wx.Button(right, label="Clear All")
        clear_btn.Bind(wx.EVT_BUTTON, self._on_clear_positions)
        btn_sizer.Add(clear_btn, 0)
        
        btn_sizer.AddStretchSpacer()
        
        save_btn = wx.Button(right, label="Save Spread")
        save_btn.Bind(wx.EVT_BUTTON, self._on_save_spread)
        btn_sizer.Add(save_btn, 0)
        
        right_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)
        right.SetSizer(right_sizer)
        
        splitter.SplitVertically(left, right, 250)
        
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(splitter, 1, wx.EXPAND)
        panel.SetSizer(panel_sizer)
        
        return panel
    
    # ═══════════════════════════════════════════
    # SETTINGS PANEL
    # ═══════════════════════════════════════════
    def _create_settings_panel(self):
        panel = scrolled.ScrolledPanel(self.notebook)
        panel.SetBackgroundColour(get_wx_color('bg_primary'))
        panel.SetupScrolling()
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Theme section
        theme_box = wx.StaticBox(panel, label="Appearance")
        theme_box.SetForegroundColour(get_wx_color('accent'))
        theme_sizer = wx.StaticBoxSizer(theme_box, wx.VERTICAL)
        
        preset_sizer = wx.BoxSizer(wx.HORIZONTAL)
        theme_preset_label = wx.StaticText(panel, label="Theme Preset:")
        theme_preset_label.SetForegroundColour(get_wx_color('text_primary'))
        preset_sizer.Add(theme_preset_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.theme_choice = wx.Choice(panel, choices=list(PRESET_THEMES.keys()))
        self.theme_choice.SetSelection(0)
        preset_sizer.Add(self.theme_choice, 0, wx.RIGHT, 10)
        
        apply_theme_btn = wx.Button(panel, label="Apply Preset")
        apply_theme_btn.Bind(wx.EVT_BUTTON, self._on_apply_theme)
        preset_sizer.Add(apply_theme_btn, 0, wx.RIGHT, 10)
        
        customize_btn = wx.Button(panel, label="Customize...")
        customize_btn.Bind(wx.EVT_BUTTON, self._on_customize_theme)
        preset_sizer.Add(customize_btn, 0)
        
        theme_sizer.Add(preset_sizer, 0, wx.ALL, 10)
        
        sizer.Add(theme_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Import presets section
        presets_box = wx.StaticBox(panel, label="Import Presets")
        presets_box.SetForegroundColour(get_wx_color('accent'))
        presets_sizer = wx.StaticBoxSizer(presets_box, wx.VERTICAL)
        
        presets_desc = wx.StaticText(panel, label="Configure filename mappings for deck imports.")
        presets_desc.SetForegroundColour(get_wx_color('text_primary'))
        presets_sizer.Add(presets_desc, 0, wx.ALL, 10)
        
        presets_inner = wx.BoxSizer(wx.HORIZONTAL)
        
        # Preset list
        self.presets_list = wx.ListCtrl(panel, size=(250, 150), style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER)
        self.presets_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.presets_list.SetForegroundColour(get_wx_color('text_primary'))
        self.presets_list.SetTextColour(get_wx_color('text_primary'))
        self.presets_list.InsertColumn(0, "", width=230)
        self.presets_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_preset_select)
        self.presets_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_edit_preset)
        presets_inner.Add(self.presets_list, 0, wx.RIGHT, 10)
        
        # Preset details
        self.preset_details = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(300, 150))
        self.preset_details.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.preset_details.SetForegroundColour(get_wx_color('text_primary'))
        presets_inner.Add(self.preset_details, 1, wx.EXPAND)
        
        presets_sizer.Add(presets_inner, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        preset_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        new_preset_btn = wx.Button(panel, label="+ New Preset")
        new_preset_btn.Bind(wx.EVT_BUTTON, self._on_new_preset)
        preset_btn_sizer.Add(new_preset_btn, 0, wx.RIGHT, 5)
        
        edit_preset_btn = wx.Button(panel, label="Edit")
        edit_preset_btn.Bind(wx.EVT_BUTTON, self._on_edit_preset)
        preset_btn_sizer.Add(edit_preset_btn, 0, wx.RIGHT, 5)
        
        del_preset_btn = wx.Button(panel, label="Delete")
        del_preset_btn.Bind(wx.EVT_BUTTON, self._on_delete_preset)
        preset_btn_sizer.Add(del_preset_btn, 0)
        
        presets_sizer.Add(preset_btn_sizer, 0, wx.ALL, 10)
        
        sizer.Add(presets_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Cache section
        cache_box = wx.StaticBox(panel, label="Thumbnail Cache")
        cache_box.SetForegroundColour(get_wx_color('accent'))
        cache_sizer = wx.StaticBoxSizer(cache_box, wx.HORIZONTAL)
        
        self.cache_label = wx.StaticText(panel, label="")
        self.cache_label.SetForegroundColour(get_wx_color('text_primary'))
        cache_sizer.Add(self.cache_label, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 10)
        
        refresh_btn = wx.Button(panel, label="Refresh")
        refresh_btn.Bind(wx.EVT_BUTTON, lambda e: self._update_cache_info())
        cache_sizer.Add(refresh_btn, 0, wx.ALL, 10)
        
        clear_btn = wx.Button(panel, label="Clear Cache")
        clear_btn.Bind(wx.EVT_BUTTON, self._on_clear_cache)
        cache_sizer.Add(clear_btn, 0, wx.ALL, 10)
        
        sizer.Add(cache_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # About section
        about_box = wx.StaticBox(panel, label="About")
        about_box.SetForegroundColour(get_wx_color('accent'))
        about_sizer = wx.StaticBoxSizer(about_box, wx.VERTICAL)
        
        about_text = wx.StaticText(panel, label=f"Tarot Journal v{VERSION}\nA journaling app for tarot, lenormand, and oracle readings.")
        about_text.SetForegroundColour(get_wx_color('text_secondary'))
        about_sizer.Add(about_text, 0, wx.ALL, 10)
        
        sizer.Add(about_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        
        # Initialize
        self._refresh_presets_list()
        self._update_cache_info()
        
        return panel
    
    # ═══════════════════════════════════════════
    # REFRESH METHODS
    # ═══════════════════════════════════════════
    def _refresh_all(self):
        self._refresh_entries_list()
        self._refresh_decks_list()
        self._refresh_spreads_list()
        self._refresh_tags_list()
        self._update_deck_choice()
        self._update_spread_choice()
    
    def _refresh_entries_list(self):
        self.entry_list.DeleteAllItems()
        
        search = self.search_ctrl.GetValue()
        tag_idx = self.tag_filter.GetSelection()
        tag_ids = None
        
        if tag_idx > 0:
            tags = self.db.get_tags()
            if tag_idx - 1 < len(tags):
                tag_ids = [tags[tag_idx - 1]['id']]
        
        if search or tag_ids:
            entries = self.db.search_entries(query=search if search else None, tag_ids=tag_ids)
        else:
            entries = self.db.get_entries()
        
        for entry in entries:
            date_str = entry['created_at'][:10] if entry['created_at'] else ''
            title = entry['title'] or '(Untitled)'
            idx = self.entry_list.InsertItem(self.entry_list.GetItemCount(), date_str)
            self.entry_list.SetItem(idx, 1, title)
            self.entry_list.SetItemData(idx, entry['id'])
    
    def _refresh_decks_list(self):
        self.deck_list.DeleteAllItems()
        
        type_filter = self.type_filter.GetString(self.type_filter.GetSelection())
        
        if type_filter == 'All':
            decks = self.db.get_decks()
        else:
            types = self.db.get_cartomancy_types()
            type_id = None
            for t in types:
                if t['name'] == type_filter:
                    type_id = t['id']
                    break
            decks = self.db.get_decks(type_id) if type_id else []
        
        for deck in decks:
            cards = self.db.get_cards(deck['id'])
            idx = self.deck_list.InsertItem(self.deck_list.GetItemCount(), deck['name'])
            self.deck_list.SetItem(idx, 1, deck['cartomancy_type_name'])
            self.deck_list.SetItem(idx, 2, str(len(cards)))
            self.deck_list.SetItemData(idx, deck['id'])
        
        self._update_deck_choice()
    
    def _refresh_spreads_list(self):
        self.spread_list.DeleteAllItems()
        spreads = self.db.get_spreads()
        for spread in spreads:
            idx = self.spread_list.InsertItem(self.spread_list.GetItemCount(), spread['name'])
            self.spread_list.SetItemData(idx, spread['id'])
        self._update_spread_choice()
    
    def _refresh_tags_list(self):
        tags = self.db.get_tags()
        self.tag_filter.Clear()
        self.tag_filter.Append("All Tags")
        for tag in tags:
            self.tag_filter.Append(tag['name'])
        self.tag_filter.SetSelection(0)
    
    def _update_deck_choice(self):
        """Update the deck map for use in dialogs"""
        decks = self.db.get_decks()
        self._deck_map = {}
        for deck in decks:
            name = f"{deck['name']} ({deck['cartomancy_type_name']})"
            self._deck_map[name] = deck['id']
    
    def _update_spread_choice(self):
        """Update the spread map for use in dialogs"""
        spreads = self.db.get_spreads()
        self._spread_map = {}
        for spread in spreads:
            self._spread_map[spread['name']] = spread['id']
    
    def _refresh_cards_display(self, deck_id):
        self.cards_sizer.Clear(True)
        self.bitmap_cache.clear()
        self.selected_card_ids = set()
        self._card_widgets = {}
        self._current_deck_id_for_cards = deck_id
        self._current_cards_sorted = []
        self._current_cards_categorized = {}
        self._current_suit_names = {}
        
        if not deck_id:
            self.cards_scroll.Layout()
            return
        
        cards = self.db.get_cards(deck_id)
        deck = self.db.get_deck(deck_id)
        suit_names = self.db.get_deck_suit_names(deck_id)
        self._current_suit_names = suit_names
        self._current_deck_type = deck['cartomancy_type_name'] if deck else 'Tarot'
        
        if deck:
            self.deck_title.SetLabel(f"{deck['name']} ({deck['cartomancy_type_name']})")
        
        # Update filter dropdown based on deck type
        if self._current_deck_type == 'Lenormand':
            # Lenormand uses playing card suits
            new_choices = ['All', 'Hearts', 'Diamonds', 'Clubs', 'Spades']
        else:
            # Tarot uses Major Arcana + tarot suits
            new_choices = ['All', 'Major Arcana', 
                          suit_names.get('wands', 'Wands'),
                          suit_names.get('cups', 'Cups'),
                          suit_names.get('swords', 'Swords'),
                          suit_names.get('pentacles', 'Pentacles')]
        
        # Update dropdown if choices changed
        current_choices = [self.card_filter_choice.GetString(i) for i in range(self.card_filter_choice.GetCount())]
        if current_choices != new_choices:
            self.card_filter_choice.Clear()
            for choice in new_choices:
                self.card_filter_choice.Append(choice)
            self.card_filter_choice.SetSelection(0)
        
        self.card_filter_names = new_choices
        
        # Sort and categorize cards
        if self._current_deck_type == 'Lenormand':
            self._current_cards_sorted = self._sort_lenormand_cards(list(cards))
            self._current_cards_categorized = self._categorize_lenormand_cards(self._current_cards_sorted)
        else:
            self._current_cards_sorted = self._sort_cards(list(cards), suit_names)
            self._current_cards_categorized = self._categorize_cards(self._current_cards_sorted, suit_names)
        
        # Display cards based on current filter
        self._display_filtered_cards()
    
    def _display_filtered_cards(self):
        """Display cards based on current filter selection"""
        # Clear existing widgets
        self.cards_scroll.DestroyChildren()
        self.cards_sizer = wx.WrapSizer(wx.HORIZONTAL)
        self.cards_scroll.SetSizer(self.cards_sizer)
        self._card_widgets = {}
        
        filter_idx = self.card_filter_choice.GetSelection()
        filter_name = self.card_filter_names[filter_idx] if filter_idx >= 0 and filter_idx < len(self.card_filter_names) else 'All'
        
        if filter_name == 'All':
            cards_to_show = self._current_cards_sorted
        elif self._current_deck_type == 'Lenormand':
            # Lenormand filtering by playing card suit
            cards_to_show = self._current_cards_categorized.get(filter_name, [])
        else:
            # Tarot filtering
            if filter_name == 'Major Arcana':
                cards_to_show = self._current_cards_categorized.get('Major Arcana', [])
            elif filter_name in ['Wands', self._current_suit_names.get('wands', 'Wands')]:
                cards_to_show = self._current_cards_categorized.get('Wands', [])
            elif filter_name in ['Cups', self._current_suit_names.get('cups', 'Cups')]:
                cards_to_show = self._current_cards_categorized.get('Cups', [])
            elif filter_name in ['Swords', self._current_suit_names.get('swords', 'Swords')]:
                cards_to_show = self._current_cards_categorized.get('Swords', [])
            elif filter_name in ['Pentacles', self._current_suit_names.get('pentacles', 'Pentacles')]:
                cards_to_show = self._current_cards_categorized.get('Pentacles', [])
            else:
                cards_to_show = self._current_cards_sorted
        
        for card in cards_to_show:
            self._create_card_widget(self.cards_scroll, self.cards_sizer, card)
        
        self.cards_scroll.Layout()
        self.cards_scroll.SetupScrolling()
        self.cards_scroll.Refresh()
    
    def _sort_lenormand_cards(self, cards):
        """Sort Lenormand cards by traditional order (1-36)"""
        # Map card names to their traditional order
        lenormand_order = {
            'rider': 1, 'clover': 2, 'ship': 3, 'house': 4, 'tree': 5,
            'clouds': 6, 'snake': 7, 'coffin': 8, 'bouquet': 9, 'flowers': 9,
            'scythe': 10, 'whip': 11, 'broom': 11, 'birds': 12, 'owls': 12,
            'child': 13, 'fox': 14, 'bear': 15, 'stars': 16, 'stork': 17,
            'dog': 18, 'tower': 19, 'garden': 20, 'mountain': 21,
            'crossroads': 22, 'paths': 22, 'mice': 23, 'heart': 24,
            'ring': 25, 'book': 26, 'letter': 27, 'man': 28, 'gentleman': 28,
            'woman': 29, 'lady': 29, 'lily': 30, 'lilies': 30, 'sun': 31,
            'moon': 32, 'key': 33, 'fish': 34, 'anchor': 35, 'cross': 36,
        }
        
        def get_lenormand_order(card):
            name = card['name'].lower().strip()
            # Direct lookup
            if name in lenormand_order:
                return lenormand_order[name]
            # Try to extract number from name if present
            match = re.match(r'^(\d+)', name)
            if match:
                return int(match.group(1))
            return 999
        
        return sorted(cards, key=get_lenormand_order)
    
    def _categorize_lenormand_cards(self, cards):
        """Categorize Lenormand cards by their traditional playing card suit associations"""
        # Map card names to suits
        lenormand_suits_by_name = {
            'rider': 'Hearts', 'clover': 'Diamonds', 'ship': 'Spades',
            'house': 'Hearts', 'tree': 'Hearts', 'clouds': 'Clubs',
            'snake': 'Clubs', 'coffin': 'Diamonds', 'bouquet': 'Spades',
            'flowers': 'Spades', 'scythe': 'Diamonds', 'whip': 'Clubs',
            'broom': 'Clubs', 'birds': 'Diamonds', 'owls': 'Diamonds',
            'child': 'Spades', 'fox': 'Clubs', 'bear': 'Clubs',
            'stars': 'Hearts', 'stork': 'Hearts', 'dog': 'Hearts',
            'tower': 'Spades', 'garden': 'Spades', 'mountain': 'Clubs',
            'crossroads': 'Diamonds', 'paths': 'Diamonds', 'mice': 'Clubs',
            'heart': 'Hearts', 'ring': 'Clubs', 'book': 'Diamonds',
            'letter': 'Spades', 'man': 'Hearts', 'gentleman': 'Hearts',
            'woman': 'Spades', 'lady': 'Spades', 'lily': 'Spades',
            'lilies': 'Spades', 'sun': 'Diamonds', 'moon': 'Hearts',
            'key': 'Diamonds', 'fish': 'Diamonds', 'anchor': 'Spades',
            'cross': 'Clubs',
        }
        
        categorized = {
            'Hearts': [],
            'Diamonds': [],
            'Clubs': [],
            'Spades': [],
        }
        
        for card in cards:
            name = card['name'].lower().strip()
            suit = lenormand_suits_by_name.get(name)
            if suit:
                categorized[suit].append(card)
        
        return categorized
    
    def _sort_cards(self, cards, suit_names):
        """Sort cards: Major Arcana first (Fool-World), then Wands, Cups, Swords, Pentacles (Ace-King)"""
        
        # Define sort order
        major_arcana_order = {
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
            'wheel of fortune': 10, 'the wheel': 10, 'wheel': 10,
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
        
        rank_order = {
            'ace': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'page': 11, 'jack': 11, 'princess': 11,
            'knight': 12, 'prince': 12,
            'queen': 13,
            'king': 14
        }
        
        # Suit order (Wands, Cups, Swords, Pentacles)
        suit_order = {
            suit_names.get('wands', 'Wands').lower(): 100,
            suit_names.get('cups', 'Cups').lower(): 200,
            suit_names.get('swords', 'Swords').lower(): 300,
            suit_names.get('pentacles', 'Pentacles').lower(): 400,
            'wands': 100, 'cups': 200, 'swords': 300, 'pentacles': 400,
            'coins': 400, 'disks': 400,
        }
        
        def get_sort_key(card):
            name_lower = card['name'].lower()
            
            # Check if it's a major arcana
            if name_lower in major_arcana_order:
                return (0, major_arcana_order[name_lower], 0)
            
            # Check for suit cards
            for suit_name, suit_val in suit_order.items():
                if f'of {suit_name}' in name_lower:
                    # Find rank
                    for rank, rank_val in rank_order.items():
                        if name_lower.startswith(rank):
                            return (1, suit_val, rank_val)
                    return (1, suit_val, 50)  # Unknown rank
            
            # Unknown card - put at end
            return (2, 999, card.get('card_order', 0))
        
        return sorted(cards, key=get_sort_key)
    
    def _categorize_cards(self, cards, suit_names):
        """Categorize cards into Major Arcana and suits"""
        categorized = {
            'Major Arcana': [],
            'Wands': [],
            'Cups': [],
            'Swords': [],
            'Pentacles': [],
        }
        
        # Map suit names to category keys
        suit_map = {
            suit_names.get('wands', 'Wands').lower(): 'Wands',
            suit_names.get('cups', 'Cups').lower(): 'Cups',
            suit_names.get('swords', 'Swords').lower(): 'Swords',
            suit_names.get('pentacles', 'Pentacles').lower(): 'Pentacles',
            'wands': 'Wands', 'cups': 'Cups', 'swords': 'Swords',
            'pentacles': 'Pentacles', 'coins': 'Pentacles', 'disks': 'Pentacles',
        }
        
        major_arcana_names = {
            'the fool', 'fool', 'the magician', 'magician', 'the high priestess',
            'high priestess', 'the empress', 'empress', 'the emperor', 'emperor',
            'the hierophant', 'hierophant', 'the lovers', 'lovers', 'the chariot',
            'chariot', 'strength', 'the hermit', 'hermit', 'wheel of fortune',
            'the wheel', 'wheel', 'justice', 'the hanged man', 'hanged man',
            'death', 'temperance', 'the devil', 'devil', 'the tower', 'tower',
            'the star', 'star', 'the moon', 'moon', 'the sun', 'sun',
            'judgement', 'judgment', 'the world', 'world'
        }
        
        for card in cards:
            name_lower = card['name'].lower()
            
            # Check major arcana
            if name_lower in major_arcana_names:
                categorized['Major Arcana'].append(card)
                continue
            
            # Check suits
            found = False
            for suit_name, category in suit_map.items():
                if f'of {suit_name}' in name_lower:
                    categorized[category].append(card)
                    found = True
                    break
            
            # If not found, try to detect from numbered cards or other patterns
            if not found:
                # Could be a court card with different naming
                pass
        
        return categorized
    
    def _create_card_widget(self, parent, sizer, card):
        """Create a card widget and add to sizer"""
        # Panel height: thumbnail (120x180 cached) + padding, plus text if showing
        # Thumbnail display is about 120+8 padding = 128 height after scaling
        panel_height = 175 if self.show_card_names else 140
        card_panel = wx.Panel(parent, size=(130, panel_height))
        card_panel.SetBackgroundColour(get_wx_color('bg_tertiary'))
        card_panel.card_id = card['id']
        
        # Register widget for later access
        self._card_widgets[card['id']] = card_panel
        
        card_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Thumbnail
        if card['image_path']:
            thumb_path = self.thumb_cache.get_thumbnail_path(card['image_path'])
            if thumb_path:
                try:
                    img = wx.Image(thumb_path, wx.BITMAP_TYPE_ANY)
                    # Scale to fit while preserving aspect ratio
                    max_width, max_height = 200, 300
                    orig_width, orig_height = img.GetWidth(), img.GetHeight()
                    scale = min(max_width / orig_width, max_height / orig_height)
                    new_width = int(orig_width * scale)
                    new_height = int(orig_height * scale)
                    img = img.Scale(new_width, new_height, wx.IMAGE_QUALITY_HIGH)
                    bmp = wx.StaticBitmap(card_panel, bitmap=wx.Bitmap(img))
                    card_sizer.Add(bmp, 0, wx.ALL | wx.ALIGN_CENTER, 4)
                    bmp.Bind(wx.EVT_LEFT_DOWN, lambda e, cid=card['id']: self._on_card_click(e, cid))
                    bmp.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card['id']: self._on_edit_card(None, cid))
                except:
                    self._add_placeholder(card_panel, card_sizer, card['id'])
            else:
                self._add_placeholder(card_panel, card_sizer, card['id'])
        else:
            self._add_placeholder(card_panel, card_sizer, card['id'])
        
        # Name (only if setting is enabled)
        if self.show_card_names:
            name = wx.StaticText(card_panel, label=card['name'])
            name.SetForegroundColour(get_wx_color('text_primary'))
            name.Wrap(210)
            card_sizer.Add(name, 0, wx.ALL | wx.ALIGN_CENTER, 4)
            name.Bind(wx.EVT_LEFT_DOWN, lambda e, cid=card['id']: self._on_card_click(e, cid))
            name.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card['id']: self._on_edit_card(None, cid))
        
        card_panel.SetSizer(card_sizer)
        card_panel.Bind(wx.EVT_LEFT_DOWN, lambda e, cid=card['id']: self._on_card_click(e, cid))
        card_panel.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card['id']: self._on_edit_card(None, cid))
        
        sizer.Add(card_panel, 0, wx.ALL, 6)
    
    def _on_card_filter_change(self, event):
        """Handle card filter dropdown change"""
        if hasattr(self, '_current_cards_sorted') and self._current_cards_sorted:
            self._display_filtered_cards()
        event.Skip()
    
    def _add_placeholder(self, parent, sizer, card_id):
        placeholder = wx.StaticText(parent, label="🂠", size=(100, 120))
        placeholder.SetFont(wx.Font(48, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        placeholder.SetForegroundColour(get_wx_color('text_dim'))
        sizer.Add(placeholder, 0, wx.ALL | wx.ALIGN_CENTER, 4)
        placeholder.Bind(wx.EVT_LEFT_DOWN, lambda e, cid=card_id: self._on_card_click(e, cid))
        placeholder.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card_id: self._on_edit_card(None, cid))
    
    def _on_card_click(self, event, card_id):
        """Handle card click with multi-select support (Shift+click)"""
        # Check for shift key
        if event.ShiftDown():
            # Toggle selection
            if card_id in self.selected_card_ids:
                self.selected_card_ids.discard(card_id)
            else:
                self.selected_card_ids.add(card_id)
        else:
            # Single select - clear others
            self.selected_card_ids = {card_id}
        
        self._update_card_selection_display()
    
    def _update_card_selection_display(self):
        """Update visual highlighting of selected cards"""
        for cid, widget in self._card_widgets.items():
            if cid in self.selected_card_ids:
                widget.SetBackgroundColour(get_wx_color('accent_dim'))
            else:
                widget.SetBackgroundColour(get_wx_color('bg_tertiary'))
            widget.Refresh()
        
        self.cards_scroll.Refresh()
    
    def _refresh_presets_list(self):
        self.presets_list.DeleteAllItems()
        for name in self.presets.get_preset_names():
            self.presets_list.InsertItem(self.presets_list.GetItemCount(), name)
    
    def _update_cache_info(self):
        count = self.thumb_cache.get_cache_count()
        size_mb = self.thumb_cache.get_cache_size() / (1024 * 1024)
        self.cache_label.SetLabel(f"{count} thumbnails cached ({size_mb:.1f} MB)")
    
    # ═══════════════════════════════════════════
    # EVENT HANDLERS - Journal
    # ═══════════════════════════════════════════
    def _on_search(self, event):
        self._refresh_entries_list()
    
    def _on_tag_filter(self, event):
        self._refresh_entries_list()
    
    def _on_entry_select(self, event):
        idx = event.GetIndex()
        entry_id = self.entry_list.GetItemData(idx)
        self.current_entry_id = entry_id
        self._display_entry_in_viewer(entry_id)
    
    def _display_entry_in_viewer(self, entry_id):
        """Display an entry in the right panel viewer"""
        # Clear existing content
        self.viewer_sizer.Clear(True)
        
        entry = self.db.get_entry(entry_id)
        if not entry:
            placeholder = wx.StaticText(self.viewer_panel, label="Entry not found")
            placeholder.SetForegroundColour(get_wx_color('text_secondary'))
            self.viewer_sizer.Add(placeholder, 0, wx.ALL, 20)
            self.viewer_panel.Layout()
            return
        
        # Title
        title = wx.StaticText(self.viewer_panel, label=entry['title'] or "Untitled")
        title.SetForegroundColour(get_wx_color('text_primary'))
        title.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.viewer_sizer.Add(title, 0, wx.ALL, 15)
        
        # Date
        if entry['created_at']:
            try:
                dt = datetime.fromisoformat(entry['created_at'])
                date_str = dt.strftime('%B %d, %Y')
            except:
                date_str = entry['created_at'][:10]
            date_label = wx.StaticText(self.viewer_panel, label=date_str)
            date_label.SetForegroundColour(get_wx_color('text_secondary'))
            self.viewer_sizer.Add(date_label, 0, wx.LEFT | wx.BOTTOM, 15)
        
        # Reading info
        readings = self.db.get_entry_readings(entry_id)
        if readings:
            reading = readings[0]
            
            # Spread and deck info
            info_parts = []
            if reading['spread_name']:
                info_parts.append(f"Spread: {reading['spread_name']}")
            if reading['deck_name']:
                info_parts.append(f"Deck: {reading['deck_name']}")
            
            if info_parts:
                info_label = wx.StaticText(self.viewer_panel, label=" • ".join(info_parts))
                info_label.SetForegroundColour(get_wx_color('text_secondary'))
                self.viewer_sizer.Add(info_label, 0, wx.LEFT | wx.BOTTOM, 15)
            
            # Cards in spread layout
            if reading['cards_used']:
                cards_used = json.loads(reading['cards_used'])
                
                # Get image paths from deck
                deck_cards = {}
                if reading['deck_name']:
                    for name, did in self._deck_map.items():
                        if reading['deck_name'] in name:
                            for card in self.db.get_cards(did):
                                deck_cards[card['name']] = card['image_path']
                            break
                
                # Get spread positions
                spread_positions = []
                if reading['spread_name'] and reading['spread_name'] in self._spread_map:
                    spread = self.db.get_spread(self._spread_map[reading['spread_name']])
                    if spread:
                        spread_positions = json.loads(spread['positions'])
                
                # Create spread display
                if spread_positions:
                    max_x = max(p.get('x', 0) + p.get('width', 80) for p in spread_positions)
                    max_y = max(p.get('y', 0) + p.get('height', 120) for p in spread_positions)
                    
                    spread_panel = wx.Panel(self.viewer_panel, size=(max_x + 20, max_y + 20))
                    spread_panel.SetBackgroundColour(get_wx_color('card_slot'))
                    
                    for i, pos in enumerate(spread_positions):
                        x, y = pos.get('x', 0), pos.get('y', 0)
                        w, h = pos.get('width', 80), pos.get('height', 120)
                        label = pos.get('label', f'Position {i+1}')
                        
                        if i < len(cards_used):
                            card_name = cards_used[i]
                            image_path = deck_cards.get(card_name)
                            image_placed = False
                            
                            if image_path and os.path.exists(image_path):
                                try:
                                    from PIL import Image as PILImage
                                    pil_img = PILImage.open(image_path)
                                    pil_img = pil_img.convert('RGB')
                                    
                                    orig_w, orig_h = pil_img.size
                                    if orig_h > 0:
                                        target_h = h - 4
                                        scale_factor = target_h / orig_h
                                        target_w = int(orig_w * scale_factor)
                                        pil_img = pil_img.resize((target_w, target_h), PILImage.LANCZOS)
                                        
                                        wx_img = wx.Image(target_w, target_h)
                                        wx_img.SetData(pil_img.tobytes())
                                        bmp = wx.StaticBitmap(spread_panel, bitmap=wx.Bitmap(wx_img))
                                        img_x = x + (w - target_w) // 2
                                        bmp.SetPosition((img_x, y + 2))
                                        image_placed = True
                                except Exception:
                                    pass
                            
                            if not image_placed:
                                slot = wx.Panel(spread_panel, size=(w, h))
                                slot.SetPosition((x, y))
                                slot.SetBackgroundColour(get_wx_color('accent_dim'))
                                slot_label = wx.StaticText(slot, label=card_name[:12])
                                slot_label.SetForegroundColour(get_wx_color('text_primary'))
                                slot_label.SetPosition((5, h//2 - 8))
                        else:
                            slot = wx.Panel(spread_panel, size=(w, h))
                            slot.SetPosition((x, y))
                            slot.SetBackgroundColour(get_wx_color('bg_tertiary'))
                            slot_label = wx.StaticText(slot, label=label)
                            slot_label.SetForegroundColour(get_wx_color('text_secondary'))
                            slot_label.SetPosition((5, h//2 - 8))
                    
                    self.viewer_sizer.Add(spread_panel, 0, wx.LEFT | wx.BOTTOM, 15)
                else:
                    # No spread - show cards in a row
                    cards_sizer = wx.WrapSizer(wx.HORIZONTAL)
                    for card_name in cards_used:
                        card_panel = wx.Panel(self.viewer_panel, size=(90, 140))
                        card_panel.SetBackgroundColour(get_wx_color('bg_tertiary'))
                        card_sizer_inner = wx.BoxSizer(wx.VERTICAL)
                        
                        image_path = deck_cards.get(card_name)
                        if image_path and os.path.exists(image_path):
                            try:
                                from PIL import Image as PILImage
                                pil_img = PILImage.open(image_path)
                                pil_img = pil_img.convert('RGB')
                                pil_img = pil_img.resize((80, 110), PILImage.LANCZOS)
                                
                                wx_img = wx.Image(80, 110)
                                wx_img.SetData(pil_img.tobytes())
                                bmp = wx.StaticBitmap(card_panel, bitmap=wx.Bitmap(wx_img))
                                card_sizer_inner.Add(bmp, 0, wx.ALL | wx.ALIGN_CENTER, 2)
                            except:
                                pass
                        
                        name_label = wx.StaticText(card_panel, label=card_name[:15])
                        name_label.SetForegroundColour(get_wx_color('text_primary'))
                        name_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                        card_sizer_inner.Add(name_label, 0, wx.ALL | wx.ALIGN_CENTER, 2)
                        
                        card_panel.SetSizer(card_sizer_inner)
                        cards_sizer.Add(card_panel, 0, wx.ALL, 5)
                    
                    self.viewer_sizer.Add(cards_sizer, 0, wx.LEFT | wx.BOTTOM, 15)
        
        # Notes
        if entry['content']:
            notes_label = wx.StaticText(self.viewer_panel, label="Notes:")
            notes_label.SetForegroundColour(get_wx_color('accent'))
            notes_label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            self.viewer_sizer.Add(notes_label, 0, wx.LEFT, 15)
            
            notes_text = wx.StaticText(self.viewer_panel, label=entry['content'])
            notes_text.SetForegroundColour(get_wx_color('text_primary'))
            notes_text.Wrap(500)
            self.viewer_sizer.Add(notes_text, 0, wx.LEFT | wx.BOTTOM, 15)
        
        # Tags
        entry_tags = self.db.get_entry_tags(entry_id)
        if entry_tags:
            tags_label = wx.StaticText(self.viewer_panel, label="Tags:")
            tags_label.SetForegroundColour(get_wx_color('accent'))
            tags_label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            self.viewer_sizer.Add(tags_label, 0, wx.LEFT, 15)
            
            tag_names = [t['name'] for t in entry_tags]
            tags_text = wx.StaticText(self.viewer_panel, label=", ".join(tag_names))
            tags_text.SetForegroundColour(get_wx_color('text_secondary'))
            self.viewer_sizer.Add(tags_text, 0, wx.LEFT | wx.BOTTOM, 15)
        
        self.viewer_panel.Layout()
        self.viewer_panel.SetupScrolling()
    
    def _on_new_entry_dialog(self, event):
        """Open dialog to create a new entry"""
        self._open_entry_editor(None)
    
    def _on_edit_entry_dialog(self, event):
        """Open dialog to edit selected entry"""
        if not self.current_entry_id:
            wx.MessageBox("Select an entry to edit.", "No Entry", wx.OK | wx.ICON_INFORMATION)
            return
        self._open_entry_editor(self.current_entry_id)
    
    def _open_entry_editor(self, entry_id):
        """Open the entry editor dialog"""
        is_new = entry_id is None
        
        if is_new:
            entry_id = self.db.add_entry(title="New Entry")
            entry = self.db.get_entry(entry_id)
        else:
            entry = self.db.get_entry(entry_id)
            if not entry:
                return
        
        dlg = wx.Dialog(self, title="New Entry" if is_new else "Edit Entry", 
                       size=(800, 700), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title_sizer = wx.BoxSizer(wx.HORIZONTAL)
        title_label = wx.StaticText(dlg, label="Title:")
        title_label.SetForegroundColour(get_wx_color('text_primary'))
        title_sizer.Add(title_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        title_ctrl = wx.TextCtrl(dlg)
        title_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        title_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        title_ctrl.SetValue(entry['title'] or '')
        title_sizer.Add(title_ctrl, 1, wx.EXPAND)
        sizer.Add(title_sizer, 0, wx.EXPAND | wx.ALL, 15)
        
        # Spread/Deck selection
        select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        spread_label = wx.StaticText(dlg, label="Spread:")
        spread_label.SetForegroundColour(get_wx_color('text_primary'))
        select_sizer.Add(spread_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        spread_choice = wx.Choice(dlg, choices=list(self._spread_map.keys()))
        select_sizer.Add(spread_choice, 0, wx.RIGHT, 20)
        
        deck_label = wx.StaticText(dlg, label="Deck:")
        deck_label.SetForegroundColour(get_wx_color('text_primary'))
        select_sizer.Add(deck_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        deck_choice = wx.Choice(dlg, choices=list(self._deck_map.keys()))
        select_sizer.Add(deck_choice, 0)
        
        sizer.Add(select_sizer, 0, wx.LEFT | wx.RIGHT, 15)
        
        # Spread canvas
        spread_canvas = wx.Panel(dlg, size=(-1, 350))
        spread_canvas.SetBackgroundColour(get_wx_color('card_slot'))
        sizer.Add(spread_canvas, 0, wx.EXPAND | wx.ALL, 15)
        
        # Cards label
        cards_label = wx.StaticText(dlg, label="Click positions above to assign cards")
        cards_label.SetForegroundColour(get_wx_color('text_dim'))
        sizer.Add(cards_label, 0, wx.LEFT, 15)
        
        # Notes
        notes_label = wx.StaticText(dlg, label="Notes:")
        notes_label.SetForegroundColour(get_wx_color('text_primary'))
        sizer.Add(notes_label, 0, wx.LEFT | wx.TOP, 15)
        
        content_ctrl = wx.TextCtrl(dlg, style=wx.TE_MULTILINE)
        content_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        content_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        content_ctrl.SetMinSize((-1, 120))
        content_ctrl.SetValue(entry['content'] or '')
        sizer.Add(content_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)
        
        # Store state for this dialog
        dlg._spread_cards = {}
        dlg._selected_deck_id = None
        
        # Load existing reading data
        readings = self.db.get_entry_readings(entry_id)
        if readings:
            reading = readings[0]
            if reading['spread_name']:
                idx = spread_choice.FindString(reading['spread_name'])
                if idx != wx.NOT_FOUND:
                    spread_choice.SetSelection(idx)
            if reading['deck_name']:
                for name, did in self._deck_map.items():
                    if reading['deck_name'] in name:
                        idx = deck_choice.FindString(name)
                        if idx != wx.NOT_FOUND:
                            deck_choice.SetSelection(idx)
                            dlg._selected_deck_id = did
                        break
            if reading['cards_used']:
                cards_used = json.loads(reading['cards_used'])
                deck_cards = {}
                if dlg._selected_deck_id:
                    for card in self.db.get_cards(dlg._selected_deck_id):
                        deck_cards[card['name']] = card['image_path']
                for i, card_name in enumerate(cards_used):
                    dlg._spread_cards[i] = {
                        'name': card_name,
                        'image_path': deck_cards.get(card_name)
                    }
        
        def on_deck_change(event):
            name = deck_choice.GetStringSelection()
            if name in self._deck_map:
                dlg._selected_deck_id = self._deck_map[name]
        
        deck_choice.Bind(wx.EVT_CHOICE, on_deck_change)
        
        def on_spread_change(event):
            dlg._spread_cards = {}
            spread_canvas.Refresh()
        
        spread_choice.Bind(wx.EVT_CHOICE, on_spread_change)
        
        def on_canvas_paint(event):
            dc = wx.PaintDC(spread_canvas)
            dc.SetBackground(wx.Brush(get_wx_color('card_slot')))
            dc.Clear()
            
            spread_name = spread_choice.GetStringSelection()
            if not spread_name or spread_name not in self._spread_map:
                return
            
            spread = self.db.get_spread(self._spread_map[spread_name])
            if not spread:
                return
            
            positions = json.loads(spread['positions'])
            
            for i, pos in enumerate(positions):
                x, y = pos.get('x', 0), pos.get('y', 0)
                w, h = pos.get('width', 80), pos.get('height', 120)
                label = pos.get('label', f'Position {i+1}')
                
                if i in dlg._spread_cards:
                    card_data = dlg._spread_cards[i]
                    image_path = card_data.get('image_path')
                    image_drawn = False
                    
                    if image_path and os.path.exists(image_path):
                        try:
                            from PIL import Image as PILImage
                            pil_img = PILImage.open(image_path)
                            pil_img = pil_img.convert('RGB')
                            
                            orig_w, orig_h = pil_img.size
                            if orig_h > 0:
                                target_h = h - 4
                                scale_factor = target_h / orig_h
                                target_w = int(orig_w * scale_factor)
                                pil_img = pil_img.resize((target_w, target_h), PILImage.LANCZOS)
                                
                                wx_img = wx.Image(target_w, target_h)
                                wx_img.SetData(pil_img.tobytes())
                                bmp = wx.Bitmap(wx_img)
                                img_x = x + (w - target_w) // 2
                                dc.DrawBitmap(bmp, img_x, y + 2)
                                dc.SetBrush(wx.TRANSPARENT_BRUSH)
                                dc.SetPen(wx.Pen(get_wx_color('accent'), 2))
                                dc.DrawRectangle(img_x - 1, y, target_w + 2, h)
                                image_drawn = True
                        except:
                            pass
                    
                    if not image_drawn:
                        dc.SetBrush(wx.Brush(get_wx_color('accent_dim')))
                        dc.SetPen(wx.Pen(get_wx_color('border'), 2))
                        dc.DrawRectangle(x, y, w, h)
                        dc.SetTextForeground(get_wx_color('text_primary'))
                        dc.DrawText(card_data.get('name', label)[:12], x + 5, y + h//2 - 8)
                else:
                    dc.SetBrush(wx.Brush(get_wx_color('bg_tertiary')))
                    dc.SetPen(wx.Pen(get_wx_color('border'), 2))
                    dc.DrawRectangle(x, y, w, h)
                    dc.SetTextForeground(get_wx_color('text_secondary'))
                    dc.DrawText(label, x + 5, y + h//2 - 8)
        
        spread_canvas.Bind(wx.EVT_PAINT, on_canvas_paint)
        
        def on_canvas_click(event):
            spread_name = spread_choice.GetStringSelection()
            if not spread_name or spread_name not in self._spread_map:
                return
            
            if not dlg._selected_deck_id:
                wx.MessageBox("Please select a deck first.", "Select Deck", wx.OK | wx.ICON_INFORMATION)
                return
            
            spread = self.db.get_spread(self._spread_map[spread_name])
            if not spread:
                return
            
            positions = json.loads(spread['positions'])
            click_x, click_y = event.GetX(), event.GetY()
            
            for i, pos in enumerate(positions):
                px, py = pos.get('x', 0), pos.get('y', 0)
                pw, ph = pos.get('width', 80), pos.get('height', 120)
                
                if px <= click_x <= px + pw and py <= click_y <= py + ph:
                    cards = self.db.get_cards(dlg._selected_deck_id)
                    if not cards:
                        return
                    
                    card_names = [c['name'] for c in cards]
                    card_dlg = wx.SingleChoiceDialog(dlg, f"Select card for: {pos.get('label', f'Position {i+1}')}", 
                                                    "Select Card", card_names)
                    if card_dlg.ShowModal() == wx.ID_OK:
                        selected_name = card_dlg.GetStringSelection()
                        for card in cards:
                            if card['name'] == selected_name:
                                dlg._spread_cards[i] = {
                                    'id': card['id'],
                                    'name': card['name'],
                                    'image_path': card['image_path']
                                }
                                break
                        
                        # Update cards label
                        if dlg._spread_cards:
                            names = [c['name'] for c in dlg._spread_cards.values()]
                            cards_label.SetLabel(f"Cards: {', '.join(names)}")
                        
                        spread_canvas.Refresh()
                    card_dlg.Destroy()
                    break
        
        spread_canvas.Bind(wx.EVT_LEFT_DOWN, on_canvas_click)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Save")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)
        
        dlg.SetSizer(sizer)
        
        if dlg.ShowModal() == wx.ID_OK:
            # Save the entry
            title = title_ctrl.GetValue()
            content = content_ctrl.GetValue()
            
            self.db.update_entry(entry_id, title=title, content=content)
            
            # Save reading
            self.db.delete_entry_readings(entry_id)
            
            spread_name = spread_choice.GetStringSelection()
            deck_name = deck_choice.GetStringSelection()
            
            if spread_name or deck_name or dlg._spread_cards:
                spread_id = self._spread_map.get(spread_name)
                deck_id = self._deck_map.get(deck_name)
                
                cartomancy_type = None
                if deck_id:
                    deck = self.db.get_deck(deck_id)
                    if deck:
                        cartomancy_type = deck['cartomancy_type_name']
                
                cards_used = [c['name'] for c in dlg._spread_cards.values()]
                deck_name_clean = deck_name.split(' (')[0] if deck_name else None
                
                self.db.add_entry_reading(
                    entry_id=entry_id,
                    spread_id=spread_id,
                    spread_name=spread_name,
                    deck_id=deck_id,
                    deck_name=deck_name_clean,
                    cartomancy_type=cartomancy_type,
                    cards_used=cards_used
                )
            
            self._refresh_entries_list()
            self.current_entry_id = entry_id
            self._display_entry_in_viewer(entry_id)
        else:
            # If cancelled and was new entry, delete it
            if is_new:
                self.db.delete_entry(entry_id)
        
        dlg.Destroy()
    
    def _on_delete_entry(self, event):
        if not self.current_entry_id:
            return
        
        if wx.MessageBox("Delete this entry?", "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            self.db.delete_entry(self.current_entry_id)
            self.current_entry_id = None
            # Clear viewer
            self.viewer_sizer.Clear(True)
            placeholder = wx.StaticText(self.viewer_panel, label="Select an entry to view")
            placeholder.SetForegroundColour(get_wx_color('text_secondary'))
            placeholder.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
            self.viewer_sizer.Add(placeholder, 0, wx.ALL, 20)
            self.viewer_panel.Layout()
            self._refresh_entries_list()
    
    
    # ═══════════════════════════════════════════
    # EVENT HANDLERS - Library
    # ═══════════════════════════════════════════
    def _on_type_filter(self, event):
        self._refresh_decks_list()
    
    def _on_deck_select(self, event):
        idx = event.GetIndex()
        deck_id = self.deck_list.GetItemData(idx)
        self._refresh_cards_display(deck_id)
    
    def _on_add_deck(self, event):
        dlg = wx.TextEntryDialog(self, "Deck name:", "Add Deck")
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue().strip()
            if name:
                type_dlg = wx.SingleChoiceDialog(self, "Deck type:", "Select Type", ['Tarot', 'Lenormand', 'Oracle'])
                if type_dlg.ShowModal() == wx.ID_OK:
                    type_name = type_dlg.GetStringSelection()
                    types = self.db.get_cartomancy_types()
                    type_id = None
                    for t in types:
                        if t['name'] == type_name:
                            type_id = t['id']
                            break
                    if type_id:
                        self.db.add_deck(name, type_id)
                        self._refresh_decks_list()
                type_dlg.Destroy()
        dlg.Destroy()
    
    def _on_edit_deck(self, event):
        """Edit deck name and suit names"""
        idx = self.deck_list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a deck to edit.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return
        
        deck_id = self.deck_list.GetItemData(idx)
        deck = self.db.get_deck(deck_id)
        if not deck:
            return
        
        suit_names = self.db.get_deck_suit_names(deck_id)
        
        dlg = wx.Dialog(self, title="Edit Deck", size=(450, 350))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Deck name
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(dlg, label="Deck Name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        name_ctrl = wx.TextCtrl(dlg, value=deck['name'])
        name_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        name_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_ctrl, 1)
        sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 15)
        
        # Suit names section
        suit_box = wx.StaticBox(dlg, label="Suit Names (for Tarot decks)")
        suit_box.SetForegroundColour(get_wx_color('accent'))
        suit_sizer = wx.StaticBoxSizer(suit_box, wx.VERTICAL)
        
        suit_note = wx.StaticText(dlg, label="Changing suit names will update all card names in this deck.")
        suit_note.SetForegroundColour(get_wx_color('text_dim'))
        suit_sizer.Add(suit_note, 0, wx.ALL, 10)
        
        suit_ctrls = {}
        for suit_key, default_name in [('wands', 'Wands'), ('cups', 'Cups'), 
                                        ('swords', 'Swords'), ('pentacles', 'Pentacles')]:
            row = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(dlg, label=f"{default_name}:", size=(80, -1))
            label.SetForegroundColour(get_wx_color('text_primary'))
            row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
            
            ctrl = wx.TextCtrl(dlg, value=suit_names.get(suit_key, default_name))
            ctrl.SetBackgroundColour(get_wx_color('bg_input'))
            ctrl.SetForegroundColour(get_wx_color('text_primary'))
            suit_ctrls[suit_key] = ctrl
            row.Add(ctrl, 1)
            
            suit_sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        sizer.Add(suit_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Save")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)
        
        dlg.SetSizer(sizer)
        
        if dlg.ShowModal() == wx.ID_OK:
            new_name = name_ctrl.GetValue().strip()
            new_suit_names = {
                'wands': suit_ctrls['wands'].GetValue().strip() or 'Wands',
                'cups': suit_ctrls['cups'].GetValue().strip() or 'Cups',
                'swords': suit_ctrls['swords'].GetValue().strip() or 'Swords',
                'pentacles': suit_ctrls['pentacles'].GetValue().strip() or 'Pentacles',
            }
            
            # Update deck name
            if new_name and new_name != deck['name']:
                self.db.update_deck(deck_id, name=new_name)
            
            # Update suit names (this also updates card names)
            if new_suit_names != suit_names:
                self.db.update_deck_suit_names(deck_id, new_suit_names, suit_names)
            
            self._refresh_decks_list()
            self._refresh_cards_display(deck_id)
            wx.MessageBox("Deck updated!", "Success", wx.OK | wx.ICON_INFORMATION)
        
        dlg.Destroy()
    
    def _on_import_folder(self, event):
        dlg = wx.DirDialog(self, "Select folder with card images")
        if dlg.ShowModal() == wx.ID_OK:
            folder = dlg.GetPath()
            self._show_import_dialog(folder)
        dlg.Destroy()
    
    def _show_import_dialog(self, folder):
        dlg = wx.Dialog(self, title="Import Deck", size=(650, 600))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Name
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(dlg, label="Deck Name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        name_ctrl = wx.TextCtrl(dlg, value=Path(folder).name)
        name_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        name_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_ctrl, 1)
        sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Preset
        preset_sizer = wx.BoxSizer(wx.HORIZONTAL)
        preset_label = wx.StaticText(dlg, label="Import Preset:")
        preset_label.SetForegroundColour(get_wx_color('text_primary'))
        preset_sizer.Add(preset_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        preset_choice = wx.Choice(dlg, choices=self.presets.get_preset_names())
        preset_choice.SetSelection(0)
        preset_sizer.Add(preset_choice, 0)
        sizer.Add(preset_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        # Suit names section (will be updated based on preset type)
        suit_box = wx.StaticBox(dlg, label="Suit Names")
        suit_box.SetForegroundColour(get_wx_color('accent'))
        suit_box_sizer = wx.StaticBoxSizer(suit_box, wx.HORIZONTAL)
        
        # Create inner panel to hold suit controls (for easy replacement)
        suit_panel = wx.Panel(dlg)
        suit_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        suit_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        suit_panel.SetSizer(suit_panel_sizer)
        suit_box_sizer.Add(suit_panel, 1, wx.EXPAND)
        
        suit_ctrls = {}
        suit_labels = {}
        
        def create_suit_controls(deck_type):
            """Create suit name controls based on deck type"""
            # Clear existing controls
            for child in suit_panel.GetChildren():
                child.Destroy()
            suit_ctrls.clear()
            suit_labels.clear()
            
            if deck_type == 'Lenormand':
                suits = [('hearts', 'Hearts'), ('diamonds', 'Diamonds'), 
                         ('clubs', 'Clubs'), ('spades', 'Spades')]
            else:  # Tarot or Oracle
                suits = [('wands', 'Wands'), ('cups', 'Cups'), 
                         ('swords', 'Swords'), ('pentacles', 'Pentacles')]
            
            new_sizer = wx.BoxSizer(wx.HORIZONTAL)
            for suit_key, default_name in suits:
                col = wx.BoxSizer(wx.VERTICAL)
                label = wx.StaticText(suit_panel, label=f"{default_name}:")
                label.SetForegroundColour(get_wx_color('text_secondary'))
                col.Add(label, 0, wx.BOTTOM, 2)
                suit_labels[suit_key] = label
                
                ctrl = wx.TextCtrl(suit_panel, value=default_name, size=(100, -1))
                ctrl.SetBackgroundColour(get_wx_color('bg_input'))
                ctrl.SetForegroundColour(get_wx_color('text_primary'))
                suit_ctrls[suit_key] = ctrl
                col.Add(ctrl, 0)
                
                new_sizer.Add(col, 0, wx.ALL, 5)
            
            suit_panel.SetSizer(new_sizer)
            suit_panel.Layout()
            dlg.Layout()
            
            # Bind text events for preview updates
            for ctrl in suit_ctrls.values():
                ctrl.Bind(wx.EVT_TEXT, update_preview)
        
        sizer.Add(suit_box_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Preview
        preview_label = wx.StaticText(dlg, label="Preview:")
        preview_label.SetForegroundColour(get_wx_color('text_primary'))
        sizer.Add(preview_label, 0, wx.LEFT | wx.RIGHT, 10)
        preview_list = wx.ListCtrl(dlg, style=wx.LC_REPORT)
        preview_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        preview_list.SetForegroundColour(get_wx_color('text_primary'))
        preview_list.InsertColumn(0, "Filename", width=200)
        preview_list.InsertColumn(1, "Card Name", width=250)
        sizer.Add(preview_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        updating_preview = [False]  # Use list to allow modification in nested function
        current_deck_type = ['Tarot']  # Track current deck type
        
        def update_preview(e=None):
            if updating_preview[0]:
                return
            updating_preview[0] = True
            
            try:
                preview_list.DeleteAllItems()
                
                # Get custom suit names for preview (use whatever keys are currently active)
                custom_suit_names = {}
                for key, ctrl in suit_ctrls.items():
                    custom_suit_names[key] = ctrl.GetValue()
                
                preset_name = preset_choice.GetStringSelection()
                preview = self.presets.preview_import(folder, preset_name, custom_suit_names)
                for orig, mapped, order in preview:
                    idx = preview_list.InsertItem(preview_list.GetItemCount(), orig)
                    preview_list.SetItem(idx, 1, mapped)
            finally:
                updating_preview[0] = False
        
        def on_preset_change(e=None):
            if updating_preview[0]:
                return
            updating_preview[0] = True
            
            try:
                # Get preset info
                preset_name = preset_choice.GetStringSelection()
                preset = self.presets.get_preset(preset_name)
                deck_type = preset.get('type', 'Oracle') if preset else 'Oracle'
                
                # Recreate suit controls if deck type changed
                if deck_type != current_deck_type[0]:
                    current_deck_type[0] = deck_type
                    create_suit_controls(deck_type)
                
                # Update suit control values from preset
                if preset:
                    preset_suits = preset.get('suit_names', {})
                    for suit_key, ctrl in suit_ctrls.items():
                        if suit_key in preset_suits:
                            ctrl.SetValue(preset_suits[suit_key])
                        else:
                            ctrl.SetValue(suit_key.title())
            finally:
                updating_preview[0] = False
            
            # Now update preview with new values
            update_preview()
        
        preset_choice.Bind(wx.EVT_CHOICE, on_preset_change)
        
        # Initial setup
        create_suit_controls('Tarot')  # Start with Tarot controls
        on_preset_change()  # This will update to correct type based on selected preset
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        import_btn = wx.Button(dlg, wx.ID_OK, "Import")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(import_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        dlg.SetSizer(sizer)
        
        if dlg.ShowModal() == wx.ID_OK:
            name = name_ctrl.GetValue().strip()
            if name:
                preset = self.presets.get_preset(preset_choice.GetStringSelection())
                cart_type = preset.get('type', 'Oracle') if preset else 'Oracle'
                
                types = self.db.get_cartomancy_types()
                type_id = types[0]['id']
                for t in types:
                    if t['name'] == cart_type:
                        type_id = t['id']
                        break
                
                # Get suit names (keys depend on deck type)
                suit_names = {}
                for key, ctrl in suit_ctrls.items():
                    suit_names[key] = ctrl.GetValue().strip() or key.title()
                
                deck_id = self.db.add_deck(name, type_id, folder, suit_names)
                
                preview = self.presets.preview_import(folder, preset_choice.GetStringSelection(), suit_names)
                cards = []
                for orig, mapped, order in preview:
                    image_path = os.path.join(folder, orig)
                    cards.append((mapped, image_path, order))
                
                if cards:
                    self.db.bulk_add_cards(deck_id, cards)
                    self.thumb_cache.pregenerate_thumbnails([c[1] for c in cards])
                    wx.MessageBox(f"Imported {len(cards)} cards into '{name}'", "Success", wx.OK | wx.ICON_INFORMATION)
                
                self._refresh_decks_list()
        
        dlg.Destroy()
    
    def _on_delete_deck(self, event):
        idx = self.deck_list.GetFirstSelected()
        if idx == -1:
            return
        
        deck_id = self.deck_list.GetItemData(idx)
        deck = self.db.get_deck(deck_id)
        
        if wx.MessageBox(f"Delete '{deck['name']}' and all cards?", "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            self.db.delete_deck(deck_id)
            self._refresh_decks_list()
            self._refresh_cards_display(None)
    
    def _on_add_card(self, event):
        idx = self.deck_list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a deck first.", "No Deck", wx.OK | wx.ICON_INFORMATION)
            return
        
        deck_id = self.deck_list.GetItemData(idx)
        
        dlg = wx.TextEntryDialog(self, "Card name:", "Add Card")
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue().strip()
            if name:
                file_dlg = wx.FileDialog(self, "Select image (optional)", wildcard="Images|*.jpg;*.jpeg;*.png;*.gif;*.webp")
                image_path = None
                if file_dlg.ShowModal() == wx.ID_OK:
                    image_path = file_dlg.GetPath()
                file_dlg.Destroy()
                
                self.db.add_card(deck_id, name, image_path)
                if image_path:
                    self.thumb_cache.get_thumbnail(image_path)
                self._refresh_cards_display(deck_id)
        dlg.Destroy()
    
    def _on_import_cards(self, event):
        idx = self.deck_list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a deck first.", "No Deck", wx.OK | wx.ICON_INFORMATION)
            return
        
        deck_id = self.deck_list.GetItemData(idx)
        
        dlg = wx.FileDialog(self, "Select images", wildcard="Images|*.jpg;*.jpeg;*.png;*.gif;*.webp",
                           style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            files = dlg.GetPaths()
            existing = self.db.get_cards(deck_id)
            order = len(existing)
            cards = []
            
            for filepath in files:
                name = Path(filepath).stem.replace('_', ' ').replace('-', ' ').title()
                cards.append((name, filepath, order))
                order += 1
            
            self.db.bulk_add_cards(deck_id, cards)
            self.thumb_cache.pregenerate_thumbnails([c[1] for c in cards])
            self._refresh_cards_display(deck_id)
            wx.MessageBox(f"Imported {len(cards)} cards.", "Success", wx.OK | wx.ICON_INFORMATION)
        dlg.Destroy()
    
    def _on_edit_card(self, event, card_id=None):
        if card_id is None:
            # Get first selected card
            if self.selected_card_ids:
                card_id = next(iter(self.selected_card_ids))
            else:
                card_id = None
        
        if not card_id:
            wx.MessageBox("Select a card to edit.", "No Card", wx.OK | wx.ICON_INFORMATION)
            return
        
        idx = self.deck_list.GetFirstSelected()
        if idx == -1:
            return
        deck_id = self.deck_list.GetItemData(idx)
        
        cards = self.db.get_cards(deck_id)
        card = None
        for c in cards:
            if c['id'] == card_id:
                card = c
                break
        
        if not card:
            return
        
        dlg = wx.Dialog(self, title="Edit Card", size=(450, 180))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Name
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(dlg, label="Name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        name_ctrl = wx.TextCtrl(dlg, value=card['name'])
        name_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        name_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_ctrl, 1)
        sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Image
        image_sizer = wx.BoxSizer(wx.HORIZONTAL)
        image_label = wx.StaticText(dlg, label="Image:")
        image_label.SetForegroundColour(get_wx_color('text_primary'))
        image_sizer.Add(image_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        image_ctrl = wx.TextCtrl(dlg, value=card['image_path'] or '')
        image_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        image_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        image_sizer.Add(image_ctrl, 1, wx.RIGHT, 5)
        
        def browse(e):
            file_dlg = wx.FileDialog(dlg, wildcard="Images|*.jpg;*.jpeg;*.png;*.gif;*.webp")
            if file_dlg.ShowModal() == wx.ID_OK:
                image_ctrl.SetValue(file_dlg.GetPath())
            file_dlg.Destroy()
        
        browse_btn = wx.Button(dlg, label="Browse")
        browse_btn.Bind(wx.EVT_BUTTON, browse)
        image_sizer.Add(browse_btn, 0)
        sizer.Add(image_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Save")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        dlg.SetSizer(sizer)
        
        if dlg.ShowModal() == wx.ID_OK:
            new_name = name_ctrl.GetValue().strip()
            new_image = image_ctrl.GetValue().strip() or None
            
            if new_name:
                self.db.update_card(card_id, name=new_name, image_path=new_image)
                if new_image and new_image != card['image_path']:
                    self.thumb_cache.get_thumbnail(new_image)
                self._refresh_cards_display(deck_id)
        
        dlg.Destroy()
    
    def _on_delete_card(self, event):
        if not self.selected_card_ids:
            wx.MessageBox("Select card(s) to delete.", "No Card", wx.OK | wx.ICON_INFORMATION)
            return
        
        idx = self.deck_list.GetFirstSelected()
        if idx == -1:
            return
        deck_id = self.deck_list.GetItemData(idx)
        
        count = len(self.selected_card_ids)
        msg = f"Delete {count} card(s)?" if count > 1 else "Delete this card?"
        
        if wx.MessageBox(msg, "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            for card_id in self.selected_card_ids:
                self.db.delete_card(card_id)
            self.selected_card_ids = set()
            self._refresh_cards_display(deck_id)
    
    # ═══════════════════════════════════════════
    # EVENT HANDLERS - Spreads
    # ═══════════════════════════════════════════
    def _on_spread_select(self, event):
        idx = self.spread_list.GetFirstSelected()
        if idx == -1:
            return
        
        spread_name = self.spread_list.GetItemText(idx)
        spreads = self.db.get_spreads()
        
        for spread in spreads:
            if spread['name'] == spread_name:
                self.editing_spread_id = spread['id']
                self.spread_name_ctrl.SetValue(spread['name'])
                self.spread_desc_ctrl.SetValue(spread['description'] or '')
                self.designer_positions = json.loads(spread['positions'])
                self.designer_canvas.Refresh()
                break
    
    def _on_new_spread(self, event):
        self.editing_spread_id = None
        self.spread_name_ctrl.SetValue('')
        self.spread_desc_ctrl.SetValue('')
        self.designer_positions = []
        self.designer_canvas.Refresh()
    
    def _on_delete_spread(self, event):
        idx = self.spread_list.GetFirstSelected()
        if idx == -1:
            return
        
        spread_name = self.spread_list.GetItemText(idx)
        
        if wx.MessageBox(f"Delete '{spread_name}'?", "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            spreads = self.db.get_spreads()
            for spread in spreads:
                if spread['name'] == spread_name:
                    self.db.delete_spread(spread['id'])
                    break
            self._refresh_spreads_list()
            self._on_new_spread(None)
    
    def _on_save_spread(self, event):
        name = self.spread_name_ctrl.GetValue().strip()
        if not name:
            wx.MessageBox("Please enter a spread name.", "Name Required", wx.OK | wx.ICON_WARNING)
            return
        
        if not self.designer_positions:
            wx.MessageBox("Add at least one card position.", "No Positions", wx.OK | wx.ICON_WARNING)
            return
        
        desc = self.spread_desc_ctrl.GetValue().strip()
        
        if self.editing_spread_id:
            self.db.update_spread(self.editing_spread_id, name=name,
                                 positions=self.designer_positions, description=desc)
        else:
            self.editing_spread_id = self.db.add_spread(name, self.designer_positions, desc)
        
        self._refresh_spreads_list()
        wx.MessageBox("Spread saved!", "Success", wx.OK | wx.ICON_INFORMATION)
    
    def _on_add_position(self, event):
        dlg = wx.TextEntryDialog(self, "Label for this position:", "Add Position")
        if dlg.ShowModal() == wx.ID_OK:
            label = dlg.GetValue().strip()
            if label:
                offset = len(self.designer_positions) * 20
                self.designer_positions.append({
                    'x': 50 + (offset % 400),
                    'y': 50 + (offset // 400) * 140,
                    'width': 80,
                    'height': 120,
                    'label': label
                })
                self.designer_canvas.Refresh()
        dlg.Destroy()
    
    def _on_clear_positions(self, event):
        self.designer_positions = []
        self.designer_canvas.Refresh()
    
    def _on_designer_paint(self, event):
        dc = wx.PaintDC(self.designer_canvas)
        dc.SetBackground(wx.Brush(get_wx_color('card_slot')))
        dc.Clear()
        
        for i, pos in enumerate(self.designer_positions):
            x, y = pos['x'], pos['y']
            w, h = pos.get('width', 80), pos.get('height', 120)
            label = pos.get('label', f'Position {i+1}')
            
            dc.SetBrush(wx.Brush(get_wx_color('bg_tertiary')))
            dc.SetPen(wx.Pen(get_wx_color('accent'), 2))
            dc.DrawRectangle(int(x), int(y), int(w), int(h))
            
            dc.SetTextForeground(get_wx_color('text_primary'))
            dc.DrawText(label, int(x + 5), int(y + h//2 - 8))
            
            dc.SetTextForeground(get_wx_color('text_dim'))
            dc.DrawText(str(i + 1), int(x + 5), int(y + 5))
    
    def _on_designer_left_down(self, event):
        x, y = event.GetX(), event.GetY()
        
        for i, pos in enumerate(self.designer_positions):
            px, py = pos['x'], pos['y']
            pw, ph = pos.get('width', 80), pos.get('height', 120)
            
            if px <= x <= px + pw and py <= y <= py + ph:
                self.drag_data['idx'] = i
                self.drag_data['offset_x'] = x - px
                self.drag_data['offset_y'] = y - py
                self.designer_canvas.CaptureMouse()
                break
    
    def _on_designer_left_up(self, event):
        if self.designer_canvas.HasCapture():
            self.designer_canvas.ReleaseMouse()
        self.drag_data['idx'] = None
    
    def _on_designer_motion(self, event):
        if self.drag_data['idx'] is not None and event.Dragging():
            idx = self.drag_data['idx']
            x = event.GetX() - self.drag_data['offset_x']
            y = event.GetY() - self.drag_data['offset_y']
            
            # Bounds
            w, h = self.designer_canvas.GetSize()
            pw = self.designer_positions[idx].get('width', 80)
            ph = self.designer_positions[idx].get('height', 120)
            x = max(0, min(x, w - pw))
            y = max(0, min(y, h - ph))
            
            self.designer_positions[idx]['x'] = x
            self.designer_positions[idx]['y'] = y
            self.designer_canvas.Refresh()
    
    def _on_designer_right_down(self, event):
        x, y = event.GetX(), event.GetY()
        
        for i, pos in enumerate(self.designer_positions):
            px, py = pos['x'], pos['y']
            pw, ph = pos.get('width', 80), pos.get('height', 120)
            
            if px <= x <= px + pw and py <= y <= py + ph:
                if wx.MessageBox(f"Delete '{pos['label']}'?", "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
                    self.designer_positions.pop(i)
                    self.designer_canvas.Refresh()
                break
    
    # ═══════════════════════════════════════════
    # EVENT HANDLERS - Settings
    # ═══════════════════════════════════════════
    def _on_apply_theme(self, event):
        preset_name = self.theme_choice.GetStringSelection()
        _theme.apply_preset(preset_name)
        _theme.save_theme()
        self._apply_theme_live()
        wx.MessageBox(f"'{preset_name}' theme applied!", "Theme Applied", wx.OK | wx.ICON_INFORMATION)
    
    def _apply_theme_live(self):
        """Apply theme changes without restarting"""
        global COLORS
        COLORS = _theme.get_colors()
        self._update_widget_colors(self)
        self.Refresh()
        self.Update()
    
    def _update_widget_colors(self, widget):
        """Recursively update colors on all widgets"""
        try:
            # Determine appropriate colors based on widget type
            if isinstance(widget, wx.Frame):
                widget.SetBackgroundColour(get_wx_color('bg_primary'))
            elif isinstance(widget, fnb.FlatNotebook):
                widget.SetBackgroundColour(get_wx_color('bg_primary'))
                widget.SetTabAreaColour(get_wx_color('bg_primary'))
                widget.SetActiveTabColour(get_wx_color('bg_tertiary'))
                widget.SetNonActiveTabTextColour(get_wx_color('text_primary'))
                widget.SetActiveTabTextColour(get_wx_color('text_primary'))
                widget.SetGradientColourTo(get_wx_color('bg_tertiary'))
                widget.SetGradientColourFrom(get_wx_color('bg_primary'))
            elif isinstance(widget, wx.Notebook):
                widget.SetBackgroundColour(get_wx_color('bg_secondary'))
                widget.SetForegroundColour(get_wx_color('text_primary'))
            elif isinstance(widget, wx.ListCtrl):
                widget.SetBackgroundColour(get_wx_color('bg_secondary'))
                widget.SetForegroundColour(get_wx_color('text_primary'))
                widget.SetTextColour(get_wx_color('text_primary'))
            elif isinstance(widget, wx.ListBox):
                widget.SetBackgroundColour(get_wx_color('bg_secondary'))
                widget.SetForegroundColour(get_wx_color('text_primary'))
            elif isinstance(widget, wx.TextCtrl):
                widget.SetBackgroundColour(get_wx_color('bg_input'))
                widget.SetForegroundColour(get_wx_color('text_primary'))
            elif isinstance(widget, wx.StaticBox):
                widget.SetForegroundColour(get_wx_color('accent'))
            elif isinstance(widget, wx.StaticText):
                # Check parent background to determine text color
                widget.SetForegroundColour(get_wx_color('text_primary'))
            elif isinstance(widget, wx.Button):
                pass  # Let system handle button colors
            elif isinstance(widget, wx.Choice):
                pass  # Let system handle choice colors
            elif isinstance(widget, wx.SearchCtrl):
                pass  # Let system handle search colors
            elif isinstance(widget, scrolled.ScrolledPanel):
                widget.SetBackgroundColour(get_wx_color('bg_primary'))
            elif isinstance(widget, wx.Panel):
                # Check if it has a special role
                if hasattr(widget, 'card_id'):
                    widget.SetBackgroundColour(get_wx_color('bg_tertiary'))
                else:
                    widget.SetBackgroundColour(get_wx_color('bg_primary'))
            elif isinstance(widget, wx.SplitterWindow):
                widget.SetBackgroundColour(get_wx_color('bg_primary'))
            
            widget.Refresh()
        except Exception:
            pass
        
        # Recurse into children
        if hasattr(widget, 'GetChildren'):
            for child in widget.GetChildren():
                self._update_widget_colors(child)
    
    def _on_customize_theme(self, event):
        """Open theme customization dialog with live preview"""
        dlg = wx.Dialog(self, title="Customize Theme", size=(650, 550))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        title = wx.StaticText(dlg, label="Customize Theme Colors")
        title.SetForegroundColour(get_wx_color('text_primary'))
        title.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL, 15)
        
        note = wx.StaticText(dlg, label="Edit colors using hex values (e.g., #1e2024). Changes apply immediately.")
        note.SetForegroundColour(get_wx_color('text_dim'))
        sizer.Add(note, 0, wx.LEFT | wx.BOTTOM, 15)
        
        # Scrolled panel for colors
        scroll = scrolled.ScrolledPanel(dlg)
        scroll.SetBackgroundColour(get_wx_color('bg_primary'))
        scroll.SetupScrolling()
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        
        color_labels = {
            'bg_primary': 'Main Background',
            'bg_secondary': 'Panel Background',
            'bg_tertiary': 'Hover / Border Background',
            'bg_input': 'Input Field Background',
            'accent': 'Accent Color (buttons, links)',
            'accent_hover': 'Accent Hover',
            'accent_dim': 'Accent Muted (selections)',
            'text_primary': 'Primary Text',
            'text_secondary': 'Secondary Text',
            'text_dim': 'Muted Text',
            'border': 'Border Color',
            'card_slot': 'Card Slot Background',
        }
        
        color_ctrls = {}
        swatches = {}
        
        for key, label in color_labels.items():
            row = wx.BoxSizer(wx.HORIZONTAL)
            
            lbl = wx.StaticText(scroll, label=label + ":", size=(180, -1), style=wx.ALIGN_RIGHT)
            lbl.SetForegroundColour(get_wx_color('text_secondary'))
            row.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
            
            ctrl = wx.TextCtrl(scroll, value=COLORS.get(key, '#000000'), size=(100, -1))
            ctrl.SetBackgroundColour(get_wx_color('bg_input'))
            ctrl.SetForegroundColour(get_wx_color('text_primary'))
            color_ctrls[key] = ctrl
            row.Add(ctrl, 0, wx.RIGHT, 10)
            
            swatch = wx.Panel(scroll, size=(30, 25))
            swatch.SetBackgroundColour(get_wx_color(key))
            swatches[key] = swatch
            row.Add(swatch, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
            
            def make_picker(k=key, c=ctrl, s=swatch):
                def pick(e):
                    current = c.GetValue()
                    try:
                        data = wx.ColourData()
                        data.SetColour(wx.Colour(current))
                        picker = wx.ColourDialog(dlg, data)
                        if picker.ShowModal() == wx.ID_OK:
                            color = picker.GetColourData().GetColour()
                            hex_color = "#{:02x}{:02x}{:02x}".format(color.Red(), color.Green(), color.Blue())
                            c.SetValue(hex_color)
                            s.SetBackgroundColour(color)
                            s.Refresh()
                        picker.Destroy()
                    except:
                        pass
                return pick
            
            pick_btn = wx.Button(scroll, label="Pick", size=(50, -1))
            pick_btn.Bind(wx.EVT_BUTTON, make_picker())
            row.Add(pick_btn, 0)
            
            scroll_sizer.Add(row, 0, wx.EXPAND | wx.ALL, 5)
            
            # Update swatch on text change
            def make_updater(k=key, c=ctrl, s=swatch):
                def update(e):
                    val = c.GetValue()
                    if val.startswith('#') and len(val) == 7:
                        try:
                            s.SetBackgroundColour(wx.Colour(val))
                            s.Refresh()
                        except:
                            pass
                    e.Skip()
                return update
            
            ctrl.Bind(wx.EVT_TEXT, make_updater())
        
        scroll.SetSizer(scroll_sizer)
        sizer.Add(scroll, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        def apply_changes(e=None):
            for key, ctrl in color_ctrls.items():
                val = ctrl.GetValue().strip()
                if val.startswith('#') and len(val) == 7:
                    _theme.set_color(key, val)
            _theme.save_theme()
            self._apply_theme_live()
        
        apply_btn = wx.Button(dlg, label="Apply")
        apply_btn.Bind(wx.EVT_BUTTON, apply_changes)
        btn_sizer.Add(apply_btn, 0, wx.RIGHT, 10)
        
        close_btn = wx.Button(dlg, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda e: dlg.Destroy())
        btn_sizer.Add(close_btn, 0)
        
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)
        
        dlg.SetSizer(sizer)
        dlg.ShowModal()
        dlg.Destroy()
    
    def _on_preset_select(self, event):
        idx = self.presets_list.GetFirstSelected()
        if idx == -1:
            return
        
        preset_name = self.presets_list.GetItemText(idx)
        preset = self.presets.get_preset(preset_name)
        
        if preset:
            details = f"Type: {preset.get('type', 'Unknown')}\n"
            details += f"Description: {preset.get('description', 'No description')}\n\n"
            details += f"Mappings: {len(preset.get('mappings', {}))} entries\n\n"
            
            mappings = preset.get('mappings', {})
            sample = list(mappings.items())[:10]
            if sample:
                details += "Sample mappings:\n"
                for key, value in sample:
                    details += f"  {key} → {value}\n"
                if len(mappings) > 10:
                    details += f"  ... and {len(mappings) - 10} more"
            
            # Show customization status
            if self.presets.is_builtin_preset(preset_name):
                if self.presets.is_preset_customized(preset_name):
                    details += "\n\n(Customized - click 'Delete' to revert to defaults)"
                else:
                    details += "\n\n(Built-in preset - click 'Edit' to customize)"
            else:
                details += "\n\n(Custom preset)"
            
            self.preset_details.SetValue(details)
    
    def _find_listctrl_item(self, listctrl, text):
        """Find item index by text in ListCtrl, returns -1 if not found"""
        for i in range(listctrl.GetItemCount()):
            if listctrl.GetItemText(i) == text:
                return i
        return -1
    
    def _on_new_preset(self, event):
        """Create a new preset with option to clone from existing"""
        dlg = wx.Dialog(self, title="New Preset", size=(400, 180))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Name field
        name_row = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(dlg, label="Preset name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        name_row.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        name_ctrl = wx.TextCtrl(dlg, size=(250, -1))
        name_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        name_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        name_row.Add(name_ctrl, 1)
        sizer.Add(name_row, 0, wx.EXPAND | wx.ALL, 15)
        
        # Clone from dropdown
        clone_row = wx.BoxSizer(wx.HORIZONTAL)
        clone_label = wx.StaticText(dlg, label="Clone from:")
        clone_label.SetForegroundColour(get_wx_color('text_primary'))
        clone_row.Add(clone_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        # Build list of presets to clone from
        clone_choices = ["(Empty preset)"] + self.presets.get_preset_names()
        clone_choice = wx.Choice(dlg, choices=clone_choices)
        clone_choice.SetSelection(0)
        clone_row.Add(clone_choice, 1)
        sizer.Add(clone_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        create_btn = wx.Button(dlg, wx.ID_OK, "Create")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(create_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)
        
        dlg.SetSizer(sizer)
        
        if dlg.ShowModal() == wx.ID_OK:
            name = name_ctrl.GetValue().strip()
            if name:
                clone_from = clone_choice.GetStringSelection()
                
                # Get data from source preset if cloning
                if clone_from == "(Empty preset)":
                    preset_type = 'Oracle'
                    mappings = {}
                    description = ''
                    suit_names = {}
                else:
                    source = self.presets.get_preset(clone_from)
                    if source:
                        preset_type = source.get('type', 'Oracle')
                        mappings = dict(source.get('mappings', {}))
                        description = source.get('description', '')
                        suit_names = dict(source.get('suit_names', {}))
                    else:
                        preset_type = 'Oracle'
                        mappings = {}
                        description = ''
                        suit_names = {}
                
                preset_name = f"Custom: {name}"
                self.presets.add_custom_preset(name, preset_type, mappings, description, suit_names)
                self._refresh_presets_list()
                
                # Select the new preset
                idx = self._find_listctrl_item(self.presets_list, preset_name)
                if idx != -1:
                    self.presets_list.Select(idx)
                
                # Open editor
                self._open_preset_editor(preset_name)
        
        dlg.Destroy()
    
    def _on_edit_preset(self, event):
        """Edit selected preset"""
        idx = self.presets_list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a preset to edit.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return
        
        preset_name = self.presets_list.GetItemText(idx)
        self._open_preset_editor(preset_name)
    
    def _open_preset_editor(self, preset_name):
        """Open the preset editor dialog"""
        preset = self.presets.get_preset(preset_name)
        if not preset:
            return
        
        dlg = wx.Dialog(self, title=f"Edit Preset: {preset_name}", size=(700, 550))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Instructions
        instr = wx.StaticText(dlg, label="Define filename patterns and their corresponding card names.\nPatterns are matched case-insensitively, ignoring spaces, dashes, and underscores.")
        instr.SetForegroundColour(get_wx_color('text_secondary'))
        sizer.Add(instr, 0, wx.ALL, 10)
        
        # Type selection
        type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        type_label = wx.StaticText(dlg, label="Deck Type:")
        type_label.SetForegroundColour(get_wx_color('text_primary'))
        type_sizer.Add(type_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        type_choice = wx.Choice(dlg, choices=['Tarot', 'Lenormand', 'Oracle'])
        current_type = preset.get('type', 'Oracle')
        type_idx = type_choice.FindString(current_type)
        if type_idx != wx.NOT_FOUND:
            type_choice.SetSelection(type_idx)
        else:
            type_choice.SetSelection(2)  # Default to Oracle
        type_sizer.Add(type_choice, 0)
        sizer.Add(type_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # Description
        desc_sizer = wx.BoxSizer(wx.HORIZONTAL)
        desc_label = wx.StaticText(dlg, label="Description:")
        desc_label.SetForegroundColour(get_wx_color('text_primary'))
        desc_sizer.Add(desc_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        desc_ctrl = wx.TextCtrl(dlg, value=preset.get('description', ''))
        desc_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        desc_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        desc_sizer.Add(desc_ctrl, 1)
        sizer.Add(desc_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # Mappings header
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pattern_header = wx.StaticText(dlg, label="Filename Pattern", size=(250, -1))
        pattern_header.SetForegroundColour(get_wx_color('text_primary'))
        pattern_header.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        header_sizer.Add(pattern_header, 0, wx.LEFT, 10)
        
        card_header = wx.StaticText(dlg, label="Card Name")
        card_header.SetForegroundColour(get_wx_color('text_primary'))
        card_header.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        header_sizer.Add(card_header, 0, wx.LEFT, 20)
        sizer.Add(header_sizer, 0, wx.BOTTOM, 5)
        
        # Scrollable mappings area
        scroll = scrolled.ScrolledPanel(dlg)
        scroll.SetBackgroundColour(get_wx_color('bg_secondary'))
        scroll.SetupScrolling()
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        
        mapping_rows = []
        mappings = preset.get('mappings', {})
        
        def add_mapping_row(pattern='', card_name=''):
            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            
            pattern_ctrl = wx.TextCtrl(scroll, value=pattern, size=(230, -1))
            pattern_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
            pattern_ctrl.SetForegroundColour(get_wx_color('text_primary'))
            row_sizer.Add(pattern_ctrl, 0, wx.RIGHT, 10)
            
            arrow = wx.StaticText(scroll, label="→")
            arrow.SetForegroundColour(get_wx_color('text_dim'))
            row_sizer.Add(arrow, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
            
            card_ctrl = wx.TextCtrl(scroll, value=card_name, size=(230, -1))
            card_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
            card_ctrl.SetForegroundColour(get_wx_color('text_primary'))
            row_sizer.Add(card_ctrl, 0, wx.RIGHT, 10)
            
            remove_btn = wx.Button(scroll, label="×", size=(30, -1))
            row_sizer.Add(remove_btn, 0)
            
            scroll_sizer.Add(row_sizer, 0, wx.ALL, 3)
            mapping_rows.append((pattern_ctrl, card_ctrl, row_sizer, remove_btn))
            
            def on_remove(e, rs=row_sizer, row=(pattern_ctrl, card_ctrl, row_sizer, remove_btn)):
                mapping_rows.remove(row)
                scroll_sizer.Remove(rs)
                pattern_ctrl.Destroy()
                card_ctrl.Destroy()
                remove_btn.Destroy()
                scroll.Layout()
                scroll.SetupScrolling()
            
            remove_btn.Bind(wx.EVT_BUTTON, on_remove)
            scroll.Layout()
            scroll.SetupScrolling()
        
        # Load existing mappings
        for pattern, card_name in mappings.items():
            add_mapping_row(pattern, card_name)
        
        # Add some empty rows if none exist
        if not mappings:
            for _ in range(5):
                add_mapping_row()
        
        scroll.SetSizer(scroll_sizer)
        sizer.Add(scroll, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        # Add rows button
        add_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_row_btn = wx.Button(dlg, label="+ Add Row")
        add_row_btn.Bind(wx.EVT_BUTTON, lambda e: add_mapping_row())
        add_btn_sizer.Add(add_row_btn, 0, wx.RIGHT, 10)
        
        add_10_btn = wx.Button(dlg, label="+ Add 10 Rows")
        add_10_btn.Bind(wx.EVT_BUTTON, lambda e: [add_mapping_row() for _ in range(10)])
        add_btn_sizer.Add(add_10_btn, 0)
        sizer.Add(add_btn_sizer, 0, wx.ALL, 10)
        
        # Save/Cancel buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Save")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        dlg.SetSizer(sizer)
        
        if dlg.ShowModal() == wx.ID_OK:
            # Collect mappings
            new_mappings = {}
            for pattern_ctrl, card_ctrl, _, _ in mapping_rows:
                pattern = pattern_ctrl.GetValue().strip()
                card_name = card_ctrl.GetValue().strip()
                if pattern and card_name:
                    new_mappings[pattern] = card_name
            
            new_type = type_choice.GetStringSelection()
            new_desc = desc_ctrl.GetValue().strip()
            
            # Preserve suit_names from original preset
            suit_names = preset.get('suit_names', {})
            
            # Extract the name without "Custom: " prefix
            if preset_name.startswith("Custom: "):
                base_name = preset_name[8:]
            else:
                base_name = preset_name
            
            # Delete old custom preset if it exists, then add new
            self.presets.delete_custom_preset(preset_name)
            self.presets.add_custom_preset(base_name, new_type, new_mappings, new_desc, suit_names)
            
            self._refresh_presets_list()
            
            # Reselect - builtin presets keep their name, custom gets "Custom: " prefix
            if self.presets.is_builtin_preset(base_name):
                new_name = base_name  # Builtin name stays the same
            else:
                new_name = f"Custom: {base_name}"
            
            idx = self._find_listctrl_item(self.presets_list, new_name)
            if idx != -1:
                self.presets_list.Select(idx)
                self._on_preset_select(None)
            
            wx.MessageBox("Preset saved!", "Success", wx.OK | wx.ICON_INFORMATION)
        
        dlg.Destroy()
    
    def _on_delete_preset(self, event):
        idx = self.presets_list.GetFirstSelected()
        if idx == -1:
            return
        
        preset_name = self.presets_list.GetItemText(idx)
        
        # Check if it's a builtin that hasn't been customized
        if self.presets.is_builtin_preset(preset_name) and not self.presets.is_preset_customized(preset_name):
            wx.MessageBox("Built-in presets cannot be deleted.\n\nYou can edit them to customize, then delete to revert.", "Cannot Delete", wx.OK | wx.ICON_WARNING)
            return
        
        # If it's a customized builtin, offer to revert
        if self.presets.is_builtin_preset(preset_name) and self.presets.is_preset_customized(preset_name):
            if wx.MessageBox(f"Revert '{preset_name}' to default settings?", "Confirm Revert", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
                self.presets.delete_custom_preset(preset_name)
                self._refresh_presets_list()
                wx.MessageBox("Preset reverted to defaults.", "Done", wx.OK | wx.ICON_INFORMATION)
            return
        
        # Regular custom preset deletion
        if wx.MessageBox(f"Delete '{preset_name}'?", "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            self.presets.delete_custom_preset(preset_name)
            self._refresh_presets_list()
    
    def _on_clear_cache(self, event):
        if wx.MessageBox("Clear all cached thumbnails?", "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            self.thumb_cache.clear_cache()
            self._update_cache_info()
            wx.MessageBox("Cache cleared.", "Done", wx.OK | wx.ICON_INFORMATION)
    
    def _on_toggle_card_names(self, event):
        """Toggle display of card names under thumbnails"""
        self.show_card_names = event.IsChecked()
        # Refresh the cards display if a deck is selected
        if self._current_deck_id_for_cards:
            self._display_filtered_cards()
    
    def _toggle_card_names_checkbox(self):
        """Helper to toggle checkbox when label is clicked"""
        self.show_card_names_cb.SetValue(not self.show_card_names_cb.GetValue())
        self.show_card_names = self.show_card_names_cb.GetValue()
        if self._current_deck_id_for_cards:
            self._display_filtered_cards()
    
    def _on_stats(self, event):
        stats = self.db.get_stats()
        
        msg = f"""Your Tarot Journey

Total Journal Entries: {stats['total_entries']}
Total Decks: {stats['total_decks']}
Total Cards: {stats['total_cards']}
Saved Spreads: {stats['total_spreads']}

Most Used Decks:
"""
        for deck in stats['top_decks']:
            msg += f"  • {deck[0]}: {deck[1]} readings\n"
        
        msg += "\nMost Used Spreads:\n"
        for spread in stats['top_spreads']:
            msg += f"  • {spread[0]}: {spread[1]} readings\n"
        
        wx.MessageBox(msg, "Statistics", wx.OK | wx.ICON_INFORMATION)


def main():
    app = TarotJournalApp()
    app.MainLoop()


if __name__ == '__main__':
    main()

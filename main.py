#!/usr/bin/env python3
"""
Tarot Journal - A journaling app for cartomancy
wxPython GUI version
"""

import wx
import wx.adv
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
from import_presets import get_presets, BUILTIN_PRESETS, COURT_PRESETS, ARCHETYPE_MAPPING_OPTIONS, DEFAULT_CARD_BACK_PATTERNS
from theme_config import get_theme, PRESET_THEMES
from rich_text_panel import RichTextPanel, RichTextViewer

# Version
VERSION = "0.4.0"

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


class ArchetypeAutocomplete(wx.Panel):
    """
    Autocomplete widget for card archetypes.
    Shows suggestions filtered by cartomancy type.
    For Oracle decks, functions as a simple text field.
    """
    def __init__(self, parent, db, cartomancy_type='Tarot', value=''):
        super().__init__(parent)
        self.SetBackgroundColour(get_wx_color('bg_primary'))
        self.db = db
        self.cartomancy_type = cartomancy_type
        self._popup = None
        self._suppress_popup = False

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.text_ctrl = wx.TextCtrl(self, value=value)
        self.text_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        self.text_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        sizer.Add(self.text_ctrl, 1, wx.EXPAND)

        # Only show dropdown button for non-Oracle types
        if cartomancy_type != 'Oracle':
            self.dropdown_btn = wx.Button(self, label="▼", size=(30, -1))
            self.dropdown_btn.Bind(wx.EVT_BUTTON, self._on_dropdown_click)
            sizer.Add(self.dropdown_btn, 0, wx.LEFT, 2)

            # Bind text events for autocomplete
            self.text_ctrl.Bind(wx.EVT_TEXT, self._on_text_change)
            self.text_ctrl.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
            self.text_ctrl.Bind(wx.EVT_KILL_FOCUS, self._on_focus_lost)

        self.SetSizer(sizer)

    def GetValue(self):
        return self.text_ctrl.GetValue()

    def SetValue(self, value):
        self._suppress_popup = True
        self.text_ctrl.SetValue(value)
        self._suppress_popup = False

    def _on_text_change(self, event):
        if self._suppress_popup:
            event.Skip()
            return

        query = self.text_ctrl.GetValue().strip()
        if len(query) >= 1:
            self._show_suggestions(query)
        else:
            self._hide_popup()
        event.Skip()

    def _on_dropdown_click(self, event):
        # Show all archetypes for this type
        self._show_suggestions('')

    def _on_key_down(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self._hide_popup()
        elif event.GetKeyCode() == wx.WXK_DOWN and self._popup and self._popup.IsShown():
            # Move focus to listbox
            if self._listbox.GetCount() > 0:
                self._listbox.SetSelection(0)
                self._listbox.SetFocus()
        else:
            event.Skip()

    def _on_focus_lost(self, event):
        # Delay hiding to allow click on popup
        wx.CallLater(150, self._check_and_hide_popup)
        event.Skip()

    def _check_and_hide_popup(self):
        if self._popup and not self._listbox.HasFocus():
            self._hide_popup()

    def _show_suggestions(self, query):
        if self.cartomancy_type == 'Oracle':
            return  # No autocomplete for Oracle

        # Get matching archetypes
        if query:
            results = self.db.search_archetypes(query, self.cartomancy_type)
        else:
            results = self.db.get_archetypes(self.cartomancy_type)

        if not results:
            self._hide_popup()
            return

        # Create or update popup
        if not self._popup:
            self._popup = wx.PopupWindow(self.GetTopLevelParent())
            self._popup.SetBackgroundColour(get_wx_color('bg_secondary'))

            popup_sizer = wx.BoxSizer(wx.VERTICAL)
            self._listbox = wx.ListBox(self._popup, style=wx.LB_SINGLE)
            self._listbox.SetBackgroundColour(get_wx_color('bg_secondary'))
            self._listbox.SetForegroundColour(get_wx_color('text_primary'))
            self._listbox.Bind(wx.EVT_LISTBOX_DCLICK, self._on_select)
            self._listbox.Bind(wx.EVT_KEY_DOWN, self._on_listbox_key)
            popup_sizer.Add(self._listbox, 1, wx.EXPAND | wx.ALL, 2)
            self._popup.SetSizer(popup_sizer)

        # Populate listbox
        self._listbox.Clear()
        self._archetype_data = []
        for arch in results:
            # Format display: "Name (Rank - Suit)" or just "Name"
            display = arch['name']
            if arch['rank'] and arch['suit']:
                display = f"{arch['name']} ({arch['rank']} - {arch['suit']})"
            elif arch['rank']:
                display = f"{arch['name']} ({arch['rank']})"
            self._listbox.Append(display)
            self._archetype_data.append(arch)

        # Position popup below text control
        pos = self.text_ctrl.ClientToScreen(wx.Point(0, self.text_ctrl.GetSize().height))
        width = self.text_ctrl.GetSize().width + 32
        height = min(200, 20 * len(results) + 10)

        self._popup.SetPosition(pos)
        self._popup.SetSize(width, height)
        self._listbox.SetSize(width - 4, height - 4)
        self._popup.Show()

    def _hide_popup(self):
        if self._popup:
            self._popup.Hide()

    def _on_select(self, event):
        idx = self._listbox.GetSelection()
        if idx >= 0 and idx < len(self._archetype_data):
            arch = self._archetype_data[idx]
            self._suppress_popup = True
            self.text_ctrl.SetValue(arch['name'])
            self._suppress_popup = False
            self.text_ctrl.SetInsertionPointEnd()
        self._hide_popup()
        self.text_ctrl.SetFocus()

    def _on_listbox_key(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN:
            self._on_select(None)
        elif event.GetKeyCode() == wx.WXK_ESCAPE:
            self._hide_popup()
            self.text_ctrl.SetFocus()
        else:
            event.Skip()

    def GetArchetypeInfo(self):
        """Get the full archetype info if the value matches a known archetype"""
        name = self.text_ctrl.GetValue().strip()
        if name and self.cartomancy_type != 'Oracle':
            return self.db.get_archetype_by_name(name, self.cartomancy_type)
        return None


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
        self.profiles_panel = self._create_profiles_panel()
        self.tags_panel = self._create_tags_panel()
        self.settings_panel = self._create_settings_panel()

        self.notebook.AddPage(self.journal_panel, "Journal")
        self.notebook.AddPage(self.library_panel, "Card Library")
        self.notebook.AddPage(self.spreads_panel, "Spreads")
        self.notebook.AddPage(self.profiles_panel, "Profiles")
        self.notebook.AddPage(self.tags_panel, "Tags")
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
        
        # Entry list (multi-select enabled)
        self.entry_list = wx.ListCtrl(left, style=wx.LC_REPORT)
        self.entry_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.entry_list.SetForegroundColour(get_wx_color('text_primary'))
        self.entry_list.InsertColumn(0, "Date/Time", width=120)
        self.entry_list.InsertColumn(1, "Title", width=180)
        self.entry_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_entry_select)
        left_sizer.Add(self.entry_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Buttons - row 1
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        new_btn = wx.Button(left, label="+ New Entry")
        new_btn.Bind(wx.EVT_BUTTON, self._on_new_entry_dialog)
        btn_sizer.Add(new_btn, 1, wx.RIGHT, 3)

        edit_btn = wx.Button(left, label="Edit")
        edit_btn.Bind(wx.EVT_BUTTON, self._on_edit_entry_dialog)
        btn_sizer.Add(edit_btn, 1, wx.RIGHT, 3)

        del_btn = wx.Button(left, label="Delete")
        del_btn.Bind(wx.EVT_BUTTON, self._on_delete_entry)
        btn_sizer.Add(del_btn, 1)

        left_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Buttons - row 2 (import/export)
        btn_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        export_btn = wx.Button(left, label="Export...")
        export_btn.Bind(wx.EVT_BUTTON, self._on_export_entries)
        btn_sizer2.Add(export_btn, 1, wx.RIGHT, 3)

        import_btn = wx.Button(left, label="Import...")
        import_btn.Bind(wx.EVT_BUTTON, self._on_import_entries)
        btn_sizer2.Add(import_btn, 1)

        left_sizer.Add(btn_sizer2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
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

        # View toggle buttons (List / Images)
        view_toggle_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.deck_list_view_btn = wx.ToggleButton(left, label="List")
        self.deck_list_view_btn.SetValue(True)  # Default to list view
        self.deck_list_view_btn.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._set_deck_view_mode('list'))
        view_toggle_sizer.Add(self.deck_list_view_btn, 0, wx.RIGHT, 5)

        self.deck_image_view_btn = wx.ToggleButton(left, label="Images")
        self.deck_image_view_btn.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._set_deck_view_mode('image'))
        view_toggle_sizer.Add(self.deck_image_view_btn, 0)

        left_sizer.Add(view_toggle_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        # Track deck view mode
        self._deck_view_mode = 'list'
        self._selected_deck_id = None  # Track selected deck across view switches

        # Type filter
        self.type_filter = wx.Choice(left, choices=['All', 'Tarot', 'Lenormand', 'Kipper', 'Oracle'])
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
        self.deck_list.Bind(wx.EVT_LIST_COL_CLICK, self._on_deck_list_col_click)
        left_sizer.Add(self.deck_list, 1, wx.EXPAND | wx.ALL, 5)

        # Deck image view (scrolled panel with card back thumbnails)
        self.deck_image_scroll = scrolled.ScrolledPanel(left)
        self.deck_image_scroll.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.deck_image_scroll.SetupScrolling()
        self.deck_image_sizer = wx.WrapSizer(wx.HORIZONTAL)
        self.deck_image_scroll.SetSizer(self.deck_image_sizer)
        self.deck_image_scroll.Hide()  # Hidden by default, list view shown
        left_sizer.Add(self.deck_image_scroll, 1, wx.EXPAND | wx.ALL, 5)

        # Track deck list sorting state
        self._deck_list_sort_col = 0  # Default sort by name
        self._deck_list_sort_asc = True  # Ascending by default
        self._deck_list_data = []  # Store deck data for sorting
        
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
        btn_sizer.Add(row2, 0, wx.EXPAND | wx.BOTTOM, 5)

        # Export and Import deck on third row
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        export_deck_btn = wx.Button(left, label="Export Deck")
        export_deck_btn.Bind(wx.EVT_BUTTON, self._on_export_deck)
        row3.Add(export_deck_btn, 1, wx.RIGHT, 5)

        import_deck_btn = wx.Button(left, label="Import Deck")
        import_deck_btn.Bind(wx.EVT_BUTTON, self._on_import_deck)
        row3.Add(import_deck_btn, 1)
        btn_sizer.Add(row3, 0, wx.EXPAND)

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

        # Deck types selection
        deck_types_sizer = wx.BoxSizer(wx.HORIZONTAL)
        deck_types_label = wx.StaticText(right, label="Allowed Deck Types:")
        deck_types_label.SetForegroundColour(get_wx_color('text_primary'))
        deck_types_sizer.Add(deck_types_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        # Create checkboxes for each cartomancy type (empty label + StaticText for macOS)
        self.spread_deck_type_checks = {}
        cart_types = self.db.get_cartomancy_types()
        for ct in cart_types:
            cb_sizer = wx.BoxSizer(wx.HORIZONTAL)
            cb = wx.CheckBox(right, label="")
            cb_sizer.Add(cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
            cb_label = wx.StaticText(right, label=ct['name'])
            cb_label.SetForegroundColour(get_wx_color('text_primary'))
            cb_sizer.Add(cb_label, 0, wx.ALIGN_CENTER_VERTICAL)
            self.spread_deck_type_checks[ct['name']] = cb
            deck_types_sizer.Add(cb_sizer, 0, wx.RIGHT, 15)

        # "Any deck" label when none selected
        any_deck_note = wx.StaticText(right, label="(none checked = any deck allowed)")
        any_deck_note.SetForegroundColour(get_wx_color('text_dim'))
        deck_types_sizer.Add(any_deck_note, 0, wx.ALIGN_CENTER_VERTICAL)

        right_sizer.Add(deck_types_sizer, 0, wx.LEFT | wx.BOTTOM, 10)

        # Instructions
        instr = wx.StaticText(right, label="Drag positions to arrange • Right-click to delete")
        instr.SetForegroundColour(get_wx_color('text_dim'))
        right_sizer.Add(instr, 0, wx.LEFT, 10)

        # Legend toggle
        toggle_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.designer_legend_toggle = wx.CheckBox(right, label="")
        self.designer_legend_toggle.Bind(wx.EVT_CHECKBOX, self._on_designer_legend_toggle)
        toggle_sizer.Add(self.designer_legend_toggle, 0, wx.RIGHT, 5)

        designer_legend_label = wx.StaticText(right, label="Show Position Legend")
        designer_legend_label.SetForegroundColour(get_wx_color('text_primary'))
        toggle_sizer.Add(designer_legend_label, 0, wx.ALIGN_CENTER_VERTICAL)

        right_sizer.Add(toggle_sizer, 0, wx.LEFT | wx.TOP, 10)

        # Container for canvas and legend
        canvas_legend_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Designer canvas
        self.designer_canvas = wx.Panel(right, size=(-1, 450))
        self.designer_canvas.SetBackgroundColour(get_wx_color('card_slot'))
        self.designer_canvas.Bind(wx.EVT_PAINT, self._on_designer_paint)
        self.designer_canvas.Bind(wx.EVT_LEFT_DOWN, self._on_designer_left_down)
        self.designer_canvas.Bind(wx.EVT_LEFT_UP, self._on_designer_left_up)
        self.designer_canvas.Bind(wx.EVT_MOTION, self._on_designer_motion)
        self.designer_canvas.Bind(wx.EVT_RIGHT_DOWN, self._on_designer_right_down)
        canvas_legend_sizer.Add(self.designer_canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Legend panel (initially hidden)
        self.designer_legend_panel = wx.Panel(right)
        self.designer_legend_panel.SetBackgroundColour(get_wx_color('bg_secondary'))
        designer_legend_sizer_inner = wx.BoxSizer(wx.VERTICAL)

        legend_title = wx.StaticText(self.designer_legend_panel, label="Position Legend:")
        legend_title.SetForegroundColour(get_wx_color('text_primary'))
        legend_title.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        designer_legend_sizer_inner.Add(legend_title, 0, wx.ALL, 10)

        # Create scrolled window for legend items
        self.designer_legend_scroll = scrolled.ScrolledPanel(self.designer_legend_panel, size=(200, 400))
        self.designer_legend_scroll.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.designer_legend_items_sizer = wx.BoxSizer(wx.VERTICAL)
        self.designer_legend_scroll.SetSizer(self.designer_legend_items_sizer)
        self.designer_legend_scroll.SetupScrolling()
        designer_legend_sizer_inner.Add(self.designer_legend_scroll, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.designer_legend_panel.SetSizer(designer_legend_sizer_inner)
        self.designer_legend_panel.Hide()
        canvas_legend_sizer.Add(self.designer_legend_panel, 0, wx.EXPAND | wx.ALL, 10)

        right_sizer.Add(canvas_legend_sizer, 1, wx.EXPAND)
        
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
    # PROFILES PANEL
    # ═══════════════════════════════════════════
    def _create_profiles_panel(self):
        panel = wx.Panel(self.notebook)
        panel.SetBackgroundColour(get_wx_color('bg_primary'))

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Left side: profiles list
        left_panel = wx.Panel(panel)
        left_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        left_sizer = wx.BoxSizer(wx.VERTICAL)

        list_label = wx.StaticText(left_panel, label="Profiles")
        list_label.SetForegroundColour(get_wx_color('accent'))
        list_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        left_sizer.Add(list_label, 0, wx.ALL, 10)

        self.profiles_list = wx.ListCtrl(left_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.profiles_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.profiles_list.SetForegroundColour(get_wx_color('text_primary'))
        self.profiles_list.InsertColumn(0, "Name", width=150)
        self.profiles_list.InsertColumn(1, "Gender", width=80)
        self.profiles_list.InsertColumn(2, "Birth Date", width=100)
        self.profiles_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_profile_selected)
        left_sizer.Add(self.profiles_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(left_panel, label="Add Profile")
        add_btn.Bind(wx.EVT_BUTTON, self._on_add_profile)
        edit_btn = wx.Button(left_panel, label="Edit")
        edit_btn.Bind(wx.EVT_BUTTON, self._on_edit_profile)
        delete_btn = wx.Button(left_panel, label="Delete")
        delete_btn.Bind(wx.EVT_BUTTON, self._on_delete_profile)

        btn_sizer.Add(add_btn, 1, wx.RIGHT, 5)
        btn_sizer.Add(edit_btn, 1, wx.RIGHT, 5)
        btn_sizer.Add(delete_btn, 1)
        left_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        left_panel.SetSizer(left_sizer)

        # Right side: profile details view
        right_panel = wx.Panel(panel)
        right_panel.SetBackgroundColour(get_wx_color('bg_secondary'))
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        details_label = wx.StaticText(right_panel, label="Profile Details")
        details_label.SetForegroundColour(get_wx_color('accent'))
        details_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        right_sizer.Add(details_label, 0, wx.ALL, 10)

        self.profile_details_text = wx.StaticText(right_panel, label="Select a profile to view details")
        self.profile_details_text.SetForegroundColour(get_wx_color('text_secondary'))
        right_sizer.Add(self.profile_details_text, 1, wx.EXPAND | wx.ALL, 10)

        right_panel.SetSizer(right_sizer)

        sizer.Add(left_panel, 1, wx.EXPAND)
        sizer.Add(right_panel, 1, wx.EXPAND)

        panel.SetSizer(sizer)

        # Load profiles
        self._refresh_profiles_list()

        return panel

    def _refresh_profiles_list(self):
        """Refresh the profiles list"""
        self.profiles_list.DeleteAllItems()
        profiles = self.db.get_profiles()
        for profile in profiles:
            idx = self.profiles_list.InsertItem(self.profiles_list.GetItemCount(), profile['name'])
            self.profiles_list.SetItem(idx, 1, profile['gender'] or '')
            self.profiles_list.SetItem(idx, 2, profile['birth_date'] or '')
            self.profiles_list.SetItemData(idx, profile['id'])

    def _on_profile_selected(self, event):
        """Handle profile selection"""
        idx = self.profiles_list.GetFirstSelected()
        if idx == -1:
            self.profile_details_text.SetLabel("Select a profile to view details")
            return

        profile_id = self.profiles_list.GetItemData(idx)
        profile = self.db.get_profile(profile_id)
        if not profile:
            return

        details = f"Name: {profile['name']}\n\n"
        details += f"Gender: {profile['gender'] or 'Not specified'}\n\n"
        details += f"Birth Date: {profile['birth_date'] or 'Not specified'}\n"
        details += f"Birth Time: {profile['birth_time'] or 'Not specified'}\n\n"
        details += f"Birth Place: {profile['birth_place_name'] or 'Not specified'}\n"
        if profile['birth_place_lat'] and profile['birth_place_lon']:
            details += f"Coordinates: {profile['birth_place_lat']:.4f}, {profile['birth_place_lon']:.4f}"

        self.profile_details_text.SetLabel(details)

    def _on_add_profile(self, event):
        """Add a new profile"""
        self._show_profile_dialog()

    def _on_edit_profile(self, event):
        """Edit selected profile"""
        idx = self.profiles_list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a profile to edit.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return
        profile_id = self.profiles_list.GetItemData(idx)
        self._show_profile_dialog(profile_id)

    def _on_delete_profile(self, event):
        """Delete selected profile"""
        idx = self.profiles_list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a profile to delete.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return

        profile_id = self.profiles_list.GetItemData(idx)
        profile = self.db.get_profile(profile_id)

        result = wx.MessageBox(
            f"Delete profile '{profile['name']}'?\n\nThis will remove the profile from any journal entries that reference it.",
            "Confirm Delete",
            wx.YES_NO | wx.ICON_WARNING
        )
        if result == wx.YES:
            self.db.delete_profile(profile_id)
            self._refresh_profiles_list()
            self.profile_details_text.SetLabel("Select a profile to view details")

    def _show_profile_dialog(self, profile_id=None):
        """Show dialog to add or edit a profile"""
        is_edit = profile_id is not None
        profile = self.db.get_profile(profile_id) if is_edit else None

        dlg = wx.Dialog(self, title="Edit Profile" if is_edit else "Add Profile", size=(450, 400))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Name
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(dlg, label="Name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        name_ctrl = wx.TextCtrl(dlg, value=profile['name'] if profile else "")
        name_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        name_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_ctrl, 1)
        sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Gender
        gender_sizer = wx.BoxSizer(wx.HORIZONTAL)
        gender_label = wx.StaticText(dlg, label="Gender:")
        gender_label.SetForegroundColour(get_wx_color('text_primary'))
        gender_sizer.Add(gender_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        gender_choices = ["", "Male", "Female", "Nonbinary"]
        gender_ctrl = wx.Choice(dlg, choices=gender_choices)
        gender_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        current_gender = profile['gender'] if profile else ""
        if current_gender in gender_choices:
            gender_ctrl.SetSelection(gender_choices.index(current_gender))
        else:
            gender_ctrl.SetSelection(0)
        gender_sizer.Add(gender_ctrl, 1)
        sizer.Add(gender_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Birth Date
        birth_date_sizer = wx.BoxSizer(wx.HORIZONTAL)
        birth_date_label = wx.StaticText(dlg, label="Birth Date:")
        birth_date_label.SetForegroundColour(get_wx_color('text_primary'))
        birth_date_sizer.Add(birth_date_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        birth_date_ctrl = wx.adv.DatePickerCtrl(dlg, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY | wx.adv.DP_ALLOWNONE)
        if profile and profile['birth_date']:
            try:
                dt = datetime.strptime(profile['birth_date'], '%Y-%m-%d')
                wx_date = wx.DateTime()
                wx_date.Set(dt.day, dt.month - 1, dt.year)
                birth_date_ctrl.SetValue(wx_date)
            except:
                pass
        birth_date_sizer.Add(birth_date_ctrl, 1)
        sizer.Add(birth_date_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Birth Time
        birth_time_sizer = wx.BoxSizer(wx.HORIZONTAL)
        birth_time_label = wx.StaticText(dlg, label="Birth Time:")
        birth_time_label.SetForegroundColour(get_wx_color('text_primary'))
        birth_time_sizer.Add(birth_time_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        birth_time_ctrl = wx.TextCtrl(dlg, value=profile['birth_time'] if profile and profile['birth_time'] else "")
        birth_time_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        birth_time_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        birth_time_ctrl.SetHint("HH:MM (24-hour format)")
        birth_time_sizer.Add(birth_time_ctrl, 1)
        sizer.Add(birth_time_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Birth Place
        birth_place_sizer = wx.BoxSizer(wx.HORIZONTAL)
        birth_place_label = wx.StaticText(dlg, label="Birth Place:")
        birth_place_label.SetForegroundColour(get_wx_color('text_primary'))
        birth_place_sizer.Add(birth_place_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        birth_place_ctrl = wx.TextCtrl(dlg, value=profile['birth_place_name'] if profile and profile['birth_place_name'] else "")
        birth_place_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        birth_place_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        birth_place_ctrl.SetHint("City, Country")
        birth_place_sizer.Add(birth_place_ctrl, 1)
        sizer.Add(birth_place_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Birth coordinates (optional, for future astro use)
        coords_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lat_label = wx.StaticText(dlg, label="Latitude:")
        lat_label.SetForegroundColour(get_wx_color('text_secondary'))
        coords_sizer.Add(lat_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        lat_ctrl = wx.TextCtrl(dlg, size=(80, -1), value=str(profile['birth_place_lat']) if profile and profile['birth_place_lat'] else "")
        lat_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        lat_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        coords_sizer.Add(lat_ctrl, 0, wx.RIGHT, 15)

        lon_label = wx.StaticText(dlg, label="Longitude:")
        lon_label.SetForegroundColour(get_wx_color('text_secondary'))
        coords_sizer.Add(lon_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        lon_ctrl = wx.TextCtrl(dlg, size=(80, -1), value=str(profile['birth_place_lon']) if profile and profile['birth_place_lon'] else "")
        lon_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        lon_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        coords_sizer.Add(lon_ctrl, 0)
        sizer.Add(coords_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        coords_note = wx.StaticText(dlg, label="(Coordinates are optional - for future astrological features)")
        coords_note.SetForegroundColour(get_wx_color('text_dim'))
        sizer.Add(coords_note, 0, wx.LEFT | wx.BOTTOM, 10)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Save")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        dlg.SetSizer(sizer)

        if dlg.ShowModal() == wx.ID_OK:
            name = name_ctrl.GetValue().strip()
            if not name:
                wx.MessageBox("Name is required.", "Validation Error", wx.OK | wx.ICON_ERROR)
                dlg.Destroy()
                return

            gender = gender_ctrl.GetStringSelection()
            if gender == "":
                gender = None

            # Get birth date
            birth_date = None
            if birth_date_ctrl.GetValue().IsValid():
                wx_date = birth_date_ctrl.GetValue()
                birth_date = f"{wx_date.GetYear()}-{wx_date.GetMonth()+1:02d}-{wx_date.GetDay():02d}"

            birth_time = birth_time_ctrl.GetValue().strip() or None
            birth_place = birth_place_ctrl.GetValue().strip() or None

            # Parse coordinates
            lat = None
            lon = None
            try:
                lat_str = lat_ctrl.GetValue().strip()
                lon_str = lon_ctrl.GetValue().strip()
                if lat_str:
                    lat = float(lat_str)
                if lon_str:
                    lon = float(lon_str)
            except ValueError:
                pass

            if is_edit:
                self.db.update_profile(profile_id, name=name, gender=gender,
                                       birth_date=birth_date, birth_time=birth_time,
                                       birth_place_name=birth_place,
                                       birth_place_lat=lat, birth_place_lon=lon)
            else:
                self.db.add_profile(name=name, gender=gender,
                                    birth_date=birth_date, birth_time=birth_time,
                                    birth_place_name=birth_place,
                                    birth_place_lat=lat, birth_place_lon=lon)

            self._refresh_profiles_list()
            self.profile_details_text.SetLabel("Select a profile to view details")

        dlg.Destroy()

    # ═══════════════════════════════════════════
    # TAGS PANEL
    # ═══════════════════════════════════════════
    def _create_tags_panel(self):
        """Create the Tags management panel with Deck Tags and Card Tags sections"""
        panel = wx.Panel(self.notebook)
        panel.SetBackgroundColour(get_wx_color('bg_primary'))

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # === Left side: Deck Tags ===
        deck_tags_box = wx.StaticBox(panel, label="Deck Tags")
        deck_tags_box.SetForegroundColour(get_wx_color('accent'))
        deck_tags_sizer = wx.StaticBoxSizer(deck_tags_box, wx.VERTICAL)

        deck_tags_info = wx.StaticText(panel, label="Tags that can be applied to decks.\nCards inherit their deck's tags.")
        deck_tags_info.SetForegroundColour(get_wx_color('text_secondary'))
        deck_tags_sizer.Add(deck_tags_info, 0, wx.ALL, 10)

        self.deck_tags_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.deck_tags_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.deck_tags_list.SetForegroundColour(get_wx_color('text_primary'))
        self.deck_tags_list.InsertColumn(0, "Name", width=150)
        self.deck_tags_list.InsertColumn(1, "Color", width=80)
        self.deck_tags_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_edit_deck_tag)
        deck_tags_sizer.Add(self.deck_tags_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        deck_tags_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_deck_tag_btn = wx.Button(panel, label="+ Add Tag")
        add_deck_tag_btn.Bind(wx.EVT_BUTTON, self._on_add_deck_tag)
        deck_tags_btn_sizer.Add(add_deck_tag_btn, 0, wx.RIGHT, 5)

        edit_deck_tag_btn = wx.Button(panel, label="Edit")
        edit_deck_tag_btn.Bind(wx.EVT_BUTTON, self._on_edit_deck_tag)
        deck_tags_btn_sizer.Add(edit_deck_tag_btn, 0, wx.RIGHT, 5)

        del_deck_tag_btn = wx.Button(panel, label="Delete")
        del_deck_tag_btn.Bind(wx.EVT_BUTTON, self._on_delete_deck_tag)
        deck_tags_btn_sizer.Add(del_deck_tag_btn, 0)

        deck_tags_sizer.Add(deck_tags_btn_sizer, 0, wx.ALL, 10)

        main_sizer.Add(deck_tags_sizer, 1, wx.EXPAND | wx.ALL, 10)

        # === Right side: Card Tags ===
        card_tags_box = wx.StaticBox(panel, label="Card Tags")
        card_tags_box.SetForegroundColour(get_wx_color('accent'))
        card_tags_sizer = wx.StaticBoxSizer(card_tags_box, wx.VERTICAL)

        card_tags_info = wx.StaticText(panel, label="Tags that can be applied to individual cards.\nThese are separate from deck tags.")
        card_tags_info.SetForegroundColour(get_wx_color('text_secondary'))
        card_tags_sizer.Add(card_tags_info, 0, wx.ALL, 10)

        self.card_tags_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.card_tags_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.card_tags_list.SetForegroundColour(get_wx_color('text_primary'))
        self.card_tags_list.InsertColumn(0, "Name", width=150)
        self.card_tags_list.InsertColumn(1, "Color", width=80)
        self.card_tags_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_edit_card_tag)
        card_tags_sizer.Add(self.card_tags_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        card_tags_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_card_tag_btn = wx.Button(panel, label="+ Add Tag")
        add_card_tag_btn.Bind(wx.EVT_BUTTON, self._on_add_card_tag)
        card_tags_btn_sizer.Add(add_card_tag_btn, 0, wx.RIGHT, 5)

        edit_card_tag_btn = wx.Button(panel, label="Edit")
        edit_card_tag_btn.Bind(wx.EVT_BUTTON, self._on_edit_card_tag)
        card_tags_btn_sizer.Add(edit_card_tag_btn, 0, wx.RIGHT, 5)

        del_card_tag_btn = wx.Button(panel, label="Delete")
        del_card_tag_btn.Bind(wx.EVT_BUTTON, self._on_delete_card_tag)
        card_tags_btn_sizer.Add(del_card_tag_btn, 0)

        card_tags_sizer.Add(card_tags_btn_sizer, 0, wx.ALL, 10)

        main_sizer.Add(card_tags_sizer, 1, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(main_sizer)

        # Populate lists
        self._refresh_deck_tags_list()
        self._refresh_card_tags_list()

        return panel

    def _refresh_deck_tags_list(self):
        """Refresh the deck tags list"""
        self.deck_tags_list.DeleteAllItems()
        tags = self.db.get_deck_tags()
        for i, tag in enumerate(tags):
            idx = self.deck_tags_list.InsertItem(i, tag['name'])
            self.deck_tags_list.SetItem(idx, 1, tag['color'])
            self.deck_tags_list.SetItemData(idx, tag['id'])

    def _refresh_card_tags_list(self):
        """Refresh the card tags list"""
        self.card_tags_list.DeleteAllItems()
        tags = self.db.get_card_tags()
        for i, tag in enumerate(tags):
            idx = self.card_tags_list.InsertItem(i, tag['name'])
            self.card_tags_list.SetItem(idx, 1, tag['color'])
            self.card_tags_list.SetItemData(idx, tag['id'])

    def _show_tag_dialog(self, parent, title, name='', color='#6B5B95'):
        """Show dialog to add/edit a tag"""
        dlg = wx.Dialog(parent, title=title, size=(350, 200))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Name field
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(dlg, label="Name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        name_ctrl = wx.TextCtrl(dlg, value=name)
        name_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        name_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_ctrl, 1)
        sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 15)

        # Color field
        color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        color_label = wx.StaticText(dlg, label="Color:")
        color_label.SetForegroundColour(get_wx_color('text_primary'))
        color_sizer.Add(color_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        color_ctrl = wx.ColourPickerCtrl(dlg, colour=wx.Colour(color))
        color_sizer.Add(color_ctrl, 0)
        sizer.Add(color_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

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
            new_color = color_ctrl.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
            dlg.Destroy()
            if new_name:
                return {'name': new_name, 'color': new_color}
        else:
            dlg.Destroy()
        return None

    def _on_add_deck_tag(self, event):
        """Add a new deck tag"""
        result = self._show_tag_dialog(self, "Add Deck Tag")
        if result:
            try:
                self.db.add_deck_tag(result['name'], result['color'])
                self._refresh_deck_tags_list()
            except Exception as e:
                wx.MessageBox(f"Could not add tag: {e}", "Error", wx.OK | wx.ICON_ERROR)

    def _on_edit_deck_tag(self, event):
        """Edit selected deck tag"""
        idx = self.deck_tags_list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a tag to edit.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return
        tag_id = self.deck_tags_list.GetItemData(idx)
        tag = self.db.get_deck_tag(tag_id)
        if not tag:
            return
        result = self._show_tag_dialog(self, "Edit Deck Tag", tag['name'], tag['color'])
        if result:
            try:
                self.db.update_deck_tag(tag_id, result['name'], result['color'])
                self._refresh_deck_tags_list()
            except Exception as e:
                wx.MessageBox(f"Could not update tag: {e}", "Error", wx.OK | wx.ICON_ERROR)

    def _on_delete_deck_tag(self, event):
        """Delete selected deck tag"""
        idx = self.deck_tags_list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a tag to delete.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return
        tag_id = self.deck_tags_list.GetItemData(idx)
        if wx.MessageBox(
            "Delete this tag? It will be removed from all decks.",
            "Confirm Delete",
            wx.YES_NO | wx.ICON_WARNING
        ) == wx.YES:
            self.db.delete_deck_tag(tag_id)
            self._refresh_deck_tags_list()

    def _on_add_card_tag(self, event):
        """Add a new card tag"""
        result = self._show_tag_dialog(self, "Add Card Tag")
        if result:
            try:
                self.db.add_card_tag(result['name'], result['color'])
                self._refresh_card_tags_list()
            except Exception as e:
                wx.MessageBox(f"Could not add tag: {e}", "Error", wx.OK | wx.ICON_ERROR)

    def _on_edit_card_tag(self, event):
        """Edit selected card tag"""
        idx = self.card_tags_list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a tag to edit.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return
        tag_id = self.card_tags_list.GetItemData(idx)
        tag = self.db.get_card_tag(tag_id)
        if not tag:
            return
        result = self._show_tag_dialog(self, "Edit Card Tag", tag['name'], tag['color'])
        if result:
            try:
                self.db.update_card_tag(tag_id, result['name'], result['color'])
                self._refresh_card_tags_list()
            except Exception as e:
                wx.MessageBox(f"Could not update tag: {e}", "Error", wx.OK | wx.ICON_ERROR)

    def _on_delete_card_tag(self, event):
        """Delete selected card tag"""
        idx = self.card_tags_list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a tag to delete.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return
        tag_id = self.card_tags_list.GetItemData(idx)
        if wx.MessageBox(
            "Delete this tag? It will be removed from all cards.",
            "Confirm Delete",
            wx.YES_NO | wx.ICON_WARNING
        ) == wx.YES:
            self.db.delete_card_tag(tag_id)
            self._refresh_card_tags_list()

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

        # Default Decks section
        defaults_box = wx.StaticBox(panel, label="Default Decks")
        defaults_box.SetForegroundColour(get_wx_color('accent'))
        defaults_sizer = wx.StaticBoxSizer(defaults_box, wx.VERTICAL)

        defaults_desc = wx.StaticText(panel, label="Select default decks to use automatically for each type.")
        defaults_desc.SetForegroundColour(get_wx_color('text_primary'))
        defaults_sizer.Add(defaults_desc, 0, wx.ALL, 10)

        # Store default deck choices
        self.default_deck_choices = {}

        # Create dropdown for each cartomancy type
        for cart_type in self.db.get_cartomancy_types():
            type_name = cart_type['name']
            type_sizer = wx.BoxSizer(wx.HORIZONTAL)

            label = wx.StaticText(panel, label=f"{type_name}:")
            label.SetForegroundColour(get_wx_color('text_primary'))
            label.SetMinSize((120, -1))
            type_sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

            # Get decks for this type
            decks = self.db.get_decks(cart_type['id'])
            deck_names = ["(None)"] + [f"{d['name']} ({d['id']})" for d in decks]

            choice = wx.Choice(panel, choices=deck_names)
            choice.SetSelection(0)

            # Load saved default
            default_deck_id = self.db.get_default_deck(type_name)
            if default_deck_id:
                for i, deck in enumerate(decks):
                    if deck['id'] == default_deck_id:
                        choice.SetSelection(i + 1)  # +1 because of "(None)" option
                        break

            # Save on change
            def make_handler(cart_type_name):
                def on_change(event):
                    sel = event.GetEventObject().GetSelection()
                    if sel == 0:  # "(None)" selected
                        self.db.set_setting(f'default_deck_{cart_type_name.lower()}', '')
                    else:
                        # Extract deck ID from "Name (ID)" format
                        choice_text = event.GetEventObject().GetStringSelection()
                        deck_id = choice_text.split('(')[-1].rstrip(')')
                        self.db.set_default_deck(cart_type_name, int(deck_id))
                    wx.MessageBox(f"Default {cart_type_name} deck updated!", "Success", wx.OK | wx.ICON_INFORMATION)
                return on_change

            choice.Bind(wx.EVT_CHOICE, make_handler(type_name))
            self.default_deck_choices[type_name] = choice

            type_sizer.Add(choice, 1, wx.EXPAND | wx.RIGHT, 10)
            defaults_sizer.Add(type_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        sizer.Add(defaults_sizer, 0, wx.EXPAND | wx.ALL, 10)

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
            # Use reading_datetime if available, otherwise created_at
            reading_dt = entry['reading_datetime'] if 'reading_datetime' in entry.keys() and entry['reading_datetime'] else None
            if reading_dt:
                try:
                    dt = datetime.fromisoformat(reading_dt)
                    date_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    date_str = reading_dt[:16] if reading_dt else ''
            elif entry['created_at']:
                date_str = entry['created_at'][:10]
            else:
                date_str = ''
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

        # Store deck data with card counts for sorting
        self._deck_list_data = []
        for deck in decks:
            cards = self.db.get_cards(deck['id'])
            card_back = deck['card_back_image'] if 'card_back_image' in deck.keys() else None
            self._deck_list_data.append({
                'id': deck['id'],
                'name': deck['name'],
                'type': deck['cartomancy_type_name'],
                'count': len(cards),
                'card_back_image': card_back
            })

        # Apply current sort and display based on view mode
        self._sort_and_display_decks()
        self._refresh_deck_image_view()

        self._update_deck_choice()

    def _sort_and_display_decks(self):
        """Sort deck data and display in list"""
        self.deck_list.DeleteAllItems()

        # Sort the data
        if self._deck_list_sort_col == 0:
            key_func = lambda x: x['name'].lower()
        elif self._deck_list_sort_col == 1:
            key_func = lambda x: x['type'].lower()
        else:  # Column 2 - card count
            key_func = lambda x: x['count']

        sorted_data = sorted(self._deck_list_data, key=key_func, reverse=not self._deck_list_sort_asc)

        # Display sorted data
        for deck in sorted_data:
            idx = self.deck_list.InsertItem(self.deck_list.GetItemCount(), deck['name'])
            self.deck_list.SetItem(idx, 1, deck['type'])
            self.deck_list.SetItem(idx, 2, str(deck['count']))
            self.deck_list.SetItemData(idx, deck['id'])

    def _on_deck_list_col_click(self, event):
        """Handle column header click for sorting"""
        col = event.GetColumn()

        # If clicking same column, toggle direction; otherwise, sort ascending
        if col == self._deck_list_sort_col:
            self._deck_list_sort_asc = not self._deck_list_sort_asc
        else:
            self._deck_list_sort_col = col
            self._deck_list_sort_asc = True

        self._sort_and_display_decks()

    def _set_deck_view_mode(self, mode):
        """Switch between list and image view modes"""
        if mode == self._deck_view_mode:
            # Re-select the current button if clicking the already-active mode
            if mode == 'list':
                self.deck_list_view_btn.SetValue(True)
            else:
                self.deck_image_view_btn.SetValue(True)
            return

        self._deck_view_mode = mode

        # Update toggle button states
        self.deck_list_view_btn.SetValue(mode == 'list')
        self.deck_image_view_btn.SetValue(mode == 'image')

        # Show/hide views
        if mode == 'list':
            self.deck_image_scroll.Hide()
            self.deck_list.Show()
        else:
            self.deck_list.Hide()
            self.deck_image_scroll.Show()

        # Refresh layout
        self.deck_list.GetParent().Layout()

        # Restore selection in the new view
        if self._selected_deck_id:
            if mode == 'list':
                self._select_deck_by_id(self._selected_deck_id)
            else:
                self._select_deck_image_by_id(self._selected_deck_id)

    def _refresh_deck_image_view(self):
        """Refresh the deck image grid view"""
        self.deck_image_sizer.Clear(True)

        # Sort data same as list view
        if self._deck_list_sort_col == 0:
            key_func = lambda x: x['name'].lower()
        elif self._deck_list_sort_col == 1:
            key_func = lambda x: x['type'].lower()
        else:
            key_func = lambda x: x['count']

        sorted_data = sorted(self._deck_list_data, key=key_func, reverse=not self._deck_list_sort_asc)

        # Create deck widgets
        for deck in sorted_data:
            widget = self._create_deck_image_widget(deck)
            self.deck_image_sizer.Add(widget, 0, wx.ALL, 5)

        self.deck_image_scroll.Layout()
        self.deck_image_scroll.SetupScrolling(scrollToTop=False)

    def _create_deck_image_widget(self, deck):
        """Create a clickable deck thumbnail with name label"""
        panel = wx.Panel(self.deck_image_scroll)
        panel.SetBackgroundColour(get_wx_color('bg_secondary'))
        panel.deck_id = deck['id']

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Card back image (100x150 for deck thumbnails)
        max_width, max_height = 100, 150
        card_back_path = deck.get('card_back_image')

        if card_back_path and os.path.exists(card_back_path):
            try:
                # Load with PIL to handle EXIF orientation properly
                from PIL import ImageOps
                pil_img = Image.open(card_back_path)
                pil_img = ImageOps.exif_transpose(pil_img)

                # Scale to fit
                w, h = pil_img.size
                scale = min(max_width / w, max_height / h)
                new_w, new_h = int(w * scale), int(h * scale)
                pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

                # Convert to wx.Image
                if pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')
                wx_img = wx.Image(new_w, new_h)
                wx_img.SetData(pil_img.tobytes())
                bitmap = wx.Bitmap(wx_img)
                img_ctrl = wx.StaticBitmap(panel, bitmap=bitmap)
            except Exception:
                img_ctrl = self._create_deck_placeholder(panel, max_width, max_height)
        else:
            img_ctrl = self._create_deck_placeholder(panel, max_width, max_height)

        sizer.Add(img_ctrl, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        # Deck name label (wrap to fit width)
        name_label = wx.StaticText(panel, label=deck['name'])
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        name_label.Wrap(max_width + 10)
        sizer.Add(name_label, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        panel.SetSizer(sizer)

        # Click handlers
        def on_click(e):
            self._on_deck_image_click(deck['id'])

        panel.Bind(wx.EVT_LEFT_DOWN, on_click)
        img_ctrl.Bind(wx.EVT_LEFT_DOWN, on_click)
        name_label.Bind(wx.EVT_LEFT_DOWN, on_click)

        # Double-click to edit
        def on_dclick(e):
            self._selected_deck_id = deck['id']
            self._on_edit_deck(None)

        panel.Bind(wx.EVT_LEFT_DCLICK, on_dclick)
        img_ctrl.Bind(wx.EVT_LEFT_DCLICK, on_dclick)
        name_label.Bind(wx.EVT_LEFT_DCLICK, on_dclick)

        return panel

    def _create_deck_placeholder(self, parent, width, height):
        """Create a placeholder for decks without card back images"""
        placeholder = wx.Panel(parent, size=(width, height))
        placeholder.SetBackgroundColour(get_wx_color('bg_tertiary'))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()
        icon = wx.StaticText(placeholder, label="🂠")
        icon.SetFont(wx.Font(32, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        icon.SetForegroundColour(get_wx_color('text_dim'))
        sizer.Add(icon, 0, wx.ALIGN_CENTER)
        sizer.AddStretchSpacer()
        placeholder.SetSizer(sizer)

        return placeholder

    def _on_deck_image_click(self, deck_id):
        """Handle click on a deck image in image view"""
        self._selected_deck_id = deck_id
        self._highlight_selected_deck_image(deck_id)
        self._refresh_cards_display(deck_id)

    def _highlight_selected_deck_image(self, deck_id):
        """Highlight the selected deck in image view"""
        for child in self.deck_image_scroll.GetChildren():
            if hasattr(child, 'deck_id'):
                if child.deck_id == deck_id:
                    child.SetBackgroundColour(get_wx_color('accent_dim'))
                else:
                    child.SetBackgroundColour(get_wx_color('bg_secondary'))
                child.Refresh()

    def _select_deck_image_by_id(self, deck_id):
        """Select a deck in the image view by its ID"""
        self._highlight_selected_deck_image(deck_id)
        # Scroll to make it visible if needed
        for child in self.deck_image_scroll.GetChildren():
            if hasattr(child, 'deck_id') and child.deck_id == deck_id:
                self.deck_image_scroll.ScrollChildIntoView(child)
                break

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
            name = deck['name']
            self._deck_map[name] = deck['id']

    def _select_deck_by_id(self, deck_id):
        """Select a deck in the list by its ID"""
        for i in range(self.deck_list.GetItemCount()):
            if self.deck_list.GetItemData(i) == deck_id:
                self.deck_list.Select(i)
                self.deck_list.EnsureVisible(i)
                return True
        return False

    def _update_spread_choice(self):
        """Update the spread map for use in dialogs"""
        spreads = self.db.get_spreads()
        self._spread_map = {}
        for spread in spreads:
            self._spread_map[spread['name']] = spread['id']
    
    def _refresh_cards_display(self, deck_id, preserve_scroll=False):
        # Save scroll position if requested
        scroll_pos = None
        if preserve_scroll:
            scroll_pos = self.cards_scroll.GetViewStart()

        self.cards_sizer.Clear(True)
        self.bitmap_cache.clear()
        self.selected_card_ids = set()
        self._card_widgets = {}
        self._current_deck_id_for_cards = deck_id
        self._current_cards_sorted = []
        self._current_cards_categorized = {}
        self._current_suit_names = {}
        self._pending_scroll_pos = scroll_pos  # Store for later restoration

        if not deck_id:
            self.cards_scroll.Layout()
            return

        cards = self.db.get_cards(deck_id)
        deck = self.db.get_deck(deck_id)
        suit_names = self.db.get_deck_suit_names(deck_id)
        self._current_suit_names = suit_names
        self._current_deck_type = deck['cartomancy_type_name'] if deck else 'Tarot'
        
        if deck:
            self.deck_title.SetLabel(deck['name'])
        
        # Update filter dropdown based on deck type
        if self._current_deck_type == 'Kipper':
            # Kipper cards have no suits, just show All
            new_choices = ['All']
        elif self._current_deck_type in ('Lenormand', 'Playing Cards'):
            # Lenormand and Playing Cards use playing card suits
            new_choices = ['All',
                          suit_names.get('hearts', 'Hearts'),
                          suit_names.get('diamonds', 'Diamonds'),
                          suit_names.get('clubs', 'Clubs'),
                          suit_names.get('spades', 'Spades')]
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
        if self._current_deck_type == 'Playing Cards':
            self._current_cards_sorted = self._sort_playing_cards(list(cards), suit_names)
            self._current_cards_categorized = self._categorize_playing_cards(self._current_cards_sorted, suit_names)
        elif self._current_deck_type == 'Lenormand':
            self._current_cards_sorted = self._sort_lenormand_cards(list(cards))
            self._current_cards_categorized = self._categorize_lenormand_cards(self._current_cards_sorted)
        elif self._current_deck_type == 'Kipper':
            self._current_cards_sorted = self._sort_kipper_cards(list(cards))
            self._current_cards_categorized = {'All': self._current_cards_sorted}
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
        elif self._current_deck_type in ('Lenormand', 'Playing Cards'):
            # Lenormand and Playing Cards filtering by playing card suit
            # Map custom suit names back to standard suit keys
            suit_map = {
                self._current_suit_names.get('hearts', 'Hearts'): 'Hearts',
                self._current_suit_names.get('diamonds', 'Diamonds'): 'Diamonds',
                self._current_suit_names.get('clubs', 'Clubs'): 'Clubs',
                self._current_suit_names.get('spades', 'Spades'): 'Spades',
                'Hearts': 'Hearts', 'Diamonds': 'Diamonds',
                'Clubs': 'Clubs', 'Spades': 'Spades',
            }
            standard_suit = suit_map.get(filter_name, filter_name)
            cards_to_show = self._current_cards_categorized.get(standard_suit, [])
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

        self.cards_sizer.Layout()
        self.cards_scroll.FitInside()
        self.cards_scroll.Layout()
        self.cards_scroll.SetupScrolling()
        self.cards_scroll.Refresh()
        self.cards_scroll.Update()

        # Restore scroll position if one was saved
        if hasattr(self, '_pending_scroll_pos') and self._pending_scroll_pos is not None:
            wx.CallAfter(self.cards_scroll.Scroll, self._pending_scroll_pos[0], self._pending_scroll_pos[1])
            self._pending_scroll_pos = None

    def _sort_lenormand_cards(self, cards):
        """Sort Lenormand cards by card_order field (set during import/auto-assign).
        Fallback: traditional order (1-36) based on card name."""
        # Map card names to their traditional order (for fallback)
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
            # Primary: use card_order if set (not 0 or None)
            try:
                card_order = card['card_order']
                if card_order is not None and card_order != 0:
                    return card_order
            except (KeyError, TypeError):
                pass

            # Fallback: parse card name
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

    def _sort_kipper_cards(self, cards):
        """Sort Kipper cards by card_order field (1-36).
        Fallback: traditional order based on card name."""
        kipper_order = {
            'main male': 1, 'hauptperson': 1,
            'main female': 2,
            'marriage': 3, 'union': 3,
            'meeting': 4, 'rendezvous': 4,
            'good gentleman': 5, 'good man': 5,
            'good lady': 6, 'good woman': 6,
            'pleasant letter': 7, 'good news': 7,
            'false person': 8, 'falsity': 8,
            'a change': 9, 'change': 9,
            'a journey': 10, 'journey': 10, 'travel': 10,
            'gain money': 11, 'win money': 11, 'wealth': 11,
            'rich girl': 12, 'wealthy girl': 12,
            'rich man': 13, 'wealthy man': 13,
            'sad news': 14, 'bad news': 14,
            'success in love': 15, 'love success': 15,
            'his thoughts': 16, 'her thoughts': 16, 'thoughts': 16,
            'a gift': 17, 'gift': 17, 'present': 17,
            'a small child': 18, 'small child': 18, 'child': 18,
            'a funeral': 19, 'funeral': 19, 'death': 19,
            'house': 20, 'home': 20,
            'living room': 21, 'parlor': 21, 'room': 21,
            'official person': 22, 'military': 22, 'official': 22,
            'court house': 23, 'courthouse': 23,
            'theft': 24, 'thief': 24, 'stealing': 24,
            'high honors': 25, 'honor': 25, 'achievement': 25,
            'great fortune': 26, 'fortune': 26, 'luck': 26,
            'unexpected money': 27, 'surprise': 27,
            'expectation': 28, 'hope': 28, 'waiting': 28,
            'prison': 29, 'confinement': 29, 'jail': 29,
            'court': 30, 'legal': 30, 'judge': 30, 'judiciary': 30,
            'short illness': 31, 'illness': 31, 'sickness': 31,
            'grief and adversity': 32, 'grief': 32, 'adversity': 32, 'sorrow': 32,
            'gloomy thoughts': 33, 'sadness': 33, 'melancholy': 33,
            'work': 34, 'employment': 34, 'occupation': 34, 'labor': 34,
            'a long way': 35, 'long way': 35, 'long road': 35, 'distance': 35,
            'hope, great water': 36, 'great water': 36, 'water': 36, 'ocean': 36,
        }

        def get_kipper_order(card):
            # Primary: use card_order if set (not 0, 999, or None)
            try:
                card_order = card['card_order']
                if card_order is not None and card_order != 0 and card_order != 999:
                    return card_order
            except (KeyError, TypeError):
                pass

            # Fallback: parse card name
            name = card['name'].lower().strip()
            # Sort by key length to match longer names first
            for key in sorted(kipper_order.keys(), key=len, reverse=True):
                if key in name:
                    return kipper_order[key]
            # Try to extract number from name if present
            match = re.match(r'^(\d+)', name)
            if match:
                return int(match.group(1))
            return 999

        return sorted(cards, key=get_kipper_order)

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

    def _sort_playing_cards(self, cards, suit_names):
        """Sort playing cards by card_order field (set by import/auto-assign).
        Order: Jokers first, then Spades, Hearts, Clubs, Diamonds (2-A within each suit)"""

        def get_sort_key(card):
            # Primary: use card_order if set
            try:
                card_order = card['card_order'] if card['card_order'] is not None else 999
            except (KeyError, TypeError):
                card_order = 999
            if card_order != 999:
                return card_order

            # Fallback: parse card name
            name_lower = card['name'].lower()

            # Jokers come first
            if 'joker' in name_lower:
                if 'red' in name_lower:
                    return 1
                elif 'black' in name_lower:
                    return 2
                else:
                    return 1

            # Suit base values: Spades=100, Hearts=200, Clubs=300, Diamonds=400
            suit_bases = {
                'spades': 100, 'spade': 100,
                'hearts': 200, 'heart': 200,
                'clubs': 300, 'club': 300,
                'diamonds': 400, 'diamond': 400,
            }

            # Rank values: 2=1, 3=2, ..., K=12, A=13
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

            # Find suit
            for suit_name, suit_val in suit_bases.items():
                if suit_name in name_lower:
                    # Find rank
                    for rank_name, rank_val in rank_values.items():
                        if f'{rank_name} of' in name_lower or name_lower.startswith(rank_name + ' '):
                            return suit_val + rank_val
                    return suit_val + 50  # Unknown rank

            return 999  # Unknown cards at end

        return sorted(cards, key=get_sort_key)

    def _categorize_playing_cards(self, cards, suit_names):
        """Categorize playing cards by suit"""

        # Build suit name variations for matching
        suit_variations = {
            'Hearts': [suit_names.get('hearts', 'Hearts').lower(), 'hearts', 'heart'],
            'Diamonds': [suit_names.get('diamonds', 'Diamonds').lower(), 'diamonds', 'diamond'],
            'Clubs': [suit_names.get('clubs', 'Clubs').lower(), 'clubs', 'club'],
            'Spades': [suit_names.get('spades', 'Spades').lower(), 'spades', 'spade'],
        }

        categorized = {
            'Hearts': [],
            'Diamonds': [],
            'Clubs': [],
            'Spades': [],
        }

        for card in cards:
            name_lower = card['name'].lower()

            # Skip jokers - they don't belong to any suit
            if 'joker' in name_lower:
                continue

            for suit_key, variations in suit_variations.items():
                if any(var in name_lower for var in variations):
                    categorized[suit_key].append(card)
                    break

        return categorized
    
    def _sort_cards(self, cards, suit_names):
        """Sort cards by card_order field (set during import/auto-assign).
        Fallback: Major Arcana first (Fool-World), then Wands, Cups, Swords, Pentacles (Ace-King)"""

        # Define sort order for name-based fallback
        major_arcana_order = {
            'the fool': 0, 'fool': 0,
            'the magician': 1, 'magician': 1, 'the magus': 1, 'magus': 1,
            'the high priestess': 2, 'high priestess': 2, 'the priestess': 2, 'priestess': 2,
            'the empress': 3, 'empress': 3,
            'the emperor': 4, 'emperor': 4,
            'the hierophant': 5, 'hierophant': 5,
            'the lovers': 6, 'lovers': 6,
            'the chariot': 7, 'chariot': 7,
            'strength': 8, 'lust': 8,  # Thoth: Lust
            'the hermit': 9, 'hermit': 9,
            'wheel of fortune': 10, 'the wheel': 10, 'wheel': 10, 'fortune': 10,
            'justice': 11, 'adjustment': 11,  # Thoth: Adjustment
            'the hanged man': 12, 'hanged man': 12,
            'death': 13,
            'temperance': 14, 'art': 14,  # Thoth: Art
            'the devil': 15, 'devil': 15,
            'the tower': 16, 'tower': 16,
            'the star': 17, 'star': 17,
            'the moon': 18, 'moon': 18,
            'the sun': 19, 'sun': 19,
            'judgement': 20, 'judgment': 20, 'the aeon': 20, 'aeon': 20,  # Thoth: The Aeon
            'the world': 21, 'world': 21, 'the universe': 21, 'universe': 21,  # Thoth: The Universe
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
            # Primary: use card_order if set (not 0 or None)
            try:
                card_order = card['card_order']
                if card_order is not None and card_order != 0:
                    return (0, card_order, 0)
            except (KeyError, TypeError):
                pass

            # Fallback: parse card name
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

            # Unknown card - put at end but preserve relative order
            return (2, 999, 0)

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
            'the fool', 'fool', 'the magician', 'magician', 'the magus', 'magus',
            'the high priestess', 'high priestess', 'the priestess', 'priestess',
            'the empress', 'empress', 'the emperor', 'emperor',
            'the hierophant', 'hierophant', 'the lovers', 'lovers', 'the chariot',
            'chariot', 'strength', 'lust', 'the hermit', 'hermit', 'wheel of fortune',
            'the wheel', 'wheel', 'fortune', 'justice', 'adjustment', 'the hanged man', 'hanged man',
            'death', 'temperance', 'art', 'the devil', 'devil', 'the tower', 'tower',
            'the star', 'star', 'the moon', 'moon', 'the sun', 'sun',
            'judgement', 'judgment', 'the aeon', 'aeon', 'the world', 'world', 'the universe', 'universe'
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
        # Panel height: thumbnail (120x180 cached) + padding + text
        panel_height = 175
        card_panel = wx.Panel(parent)
        card_panel.SetMinSize((130, panel_height))
        card_panel.SetBackgroundColour(get_wx_color('bg_tertiary'))
        card_panel.card_id = card['id']

        # Add tooltip with card name (uses system default delay, typically ~500ms)
        card_name = card['name'] if 'name' in card.keys() else ''
        card_panel.SetToolTip(card_name)

        # Register widget for later access
        self._card_widgets[card['id']] = card_panel
        
        card_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Thumbnail
        if card['image_path']:
            thumb_path = self.thumb_cache.get_thumbnail_path(card['image_path'])
            if not thumb_path:
                print(f"Failed to generate thumbnail for: {card['name'] if 'name' in card.keys() else 'unknown'}")
                print(f"  Image path: {card['image_path']}")
                print(f"  Path exists: {os.path.exists(card['image_path'])}")
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
                    bmp.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card['id']: self._on_view_card(None, cid))
                except Exception as e:
                    print(f"Error loading thumbnail for card {card['name'] if 'name' in card.keys() else 'unknown'}: {e}")
                    print(f"  Image path: {card['image_path']}")
                    print(f"  Thumbnail path: {thumb_path}")
                    self._add_placeholder(card_panel, card_sizer, card['id'])
            else:
                self._add_placeholder(card_panel, card_sizer, card['id'])
        else:
            self._add_placeholder(card_panel, card_sizer, card['id'])
        
        # Name display is not currently working - disabled for now
        # TODO: Fix card name display feature

        card_panel.SetSizer(card_sizer)

        card_panel.Bind(wx.EVT_LEFT_DOWN, lambda e, cid=card['id']: self._on_card_click(e, cid))
        card_panel.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card['id']: self._on_view_card(None, cid))

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
        placeholder.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card_id: self._on_view_card(None, cid))
    
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
    
    def _refresh_presets_list(self, preserve_scroll=True):
        # Save scroll position of settings panel (if it exists)
        scroll_pos = None
        if preserve_scroll and hasattr(self, 'settings_panel') and self.settings_panel:
            scroll_pos = self.settings_panel.GetViewStart()

        self.presets_list.DeleteAllItems()
        for name in self.presets.get_preset_names():
            self.presets_list.InsertItem(self.presets_list.GetItemCount(), name)

        # Restore scroll position
        if scroll_pos is not None:
            wx.CallAfter(self.settings_panel.Scroll, scroll_pos[0], scroll_pos[1])
    
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
        
        # Date/Time and Location
        reading_dt = entry['reading_datetime'] if 'reading_datetime' in entry.keys() else None
        if reading_dt:
            try:
                dt = datetime.fromisoformat(reading_dt)
                date_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                date_str = reading_dt[:16] if reading_dt else ''
        elif entry['created_at']:
            try:
                dt = datetime.fromisoformat(entry['created_at'])
                date_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                date_str = entry['created_at'][:16]
        else:
            date_str = None

        if date_str:
            date_label = wx.StaticText(self.viewer_panel, label=date_str)
            date_label.SetForegroundColour(get_wx_color('text_secondary'))
            self.viewer_sizer.Add(date_label, 0, wx.LEFT | wx.BOTTOM, 5)

        # Location
        location_name = entry['location_name'] if 'location_name' in entry.keys() else None
        if location_name:
            location_label = wx.StaticText(self.viewer_panel, label=f"Location: {location_name}")
            location_label.SetForegroundColour(get_wx_color('text_secondary'))
            self.viewer_sizer.Add(location_label, 0, wx.LEFT | wx.BOTTOM, 5)

        # Querent and Reader
        querent_id = entry['querent_id'] if 'querent_id' in entry.keys() else None
        reader_id = entry['reader_id'] if 'reader_id' in entry.keys() else None

        people_parts = []
        if querent_id:
            querent = self.db.get_profile(querent_id)
            if querent:
                people_parts.append(f"Querent: {querent['name']}")
        if reader_id:
            reader = self.db.get_profile(reader_id)
            if reader:
                if reader_id == querent_id:
                    people_parts.append("(also Reader)")
                else:
                    people_parts.append(f"Reader: {reader['name']}")

        if people_parts:
            people_label = wx.StaticText(self.viewer_panel, label=" ".join(people_parts))
            people_label.SetForegroundColour(get_wx_color('text_secondary'))
            self.viewer_sizer.Add(people_label, 0, wx.LEFT | wx.BOTTOM, 15)
        elif location_name:
            # Add extra spacing after location if no people info
            self.viewer_sizer.AddSpacer(10)
        else:
            # Add spacing if no location and no people
            self.viewer_sizer.AddSpacer(10)

        # Reading info - display all readings
        readings = self.db.get_entry_readings(entry_id)
        for reading_idx, reading in enumerate(readings):
            # Add separator between multiple readings
            if reading_idx > 0:
                sep = wx.StaticLine(self.viewer_panel)
                self.viewer_sizer.Add(sep, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 15)
                reading_label = wx.StaticText(self.viewer_panel, label=f"Reading {reading_idx + 1}")
                reading_label.SetForegroundColour(get_wx_color('accent'))
                reading_label.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                self.viewer_sizer.Add(reading_label, 0, wx.LEFT | wx.BOTTOM, 15)

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

                # Build lookup for all decks (multi-deck support)
                # deck_id -> {card_name -> {image_path, card_id}}
                all_deck_cards = {}
                for name, did in self._deck_map.items():
                    all_deck_cards[did] = {}
                    for card in self.db.get_cards(did):
                        all_deck_cards[did][card['name']] = {
                            'image_path': card['image_path'],
                            'card_id': card['id']
                        }

                # Also build legacy lookup for backwards compatibility
                deck_cards = {}  # card_name -> image_path
                deck_card_ids = {}  # card_name -> card_id
                default_deck_id = None
                if reading['deck_name']:
                    for name, did in self._deck_map.items():
                        if reading['deck_name'] in name:
                            default_deck_id = did
                            for card in self.db.get_cards(did):
                                deck_cards[card['name']] = card['image_path']
                                deck_card_ids[card['name']] = card['id']
                            break

                def get_card_info(card_data, card_name):
                    """Get image_path and card_id for a card, handling multi-deck format"""
                    # Check if card has deck_id (multi-deck format)
                    if isinstance(card_data, dict) and card_data.get('deck_id'):
                        card_deck_id = card_data['deck_id']
                        if card_deck_id in all_deck_cards:
                            info = all_deck_cards[card_deck_id].get(card_name, {})
                            return info.get('image_path'), info.get('card_id')
                    # Fall back to legacy lookup
                    return deck_cards.get(card_name), deck_card_ids.get(card_name)
                
                # Get spread positions
                spread_positions = []
                if reading['spread_name'] and reading['spread_name'] in self._spread_map:
                    spread = self.db.get_spread(self._spread_map[reading['spread_name']])
                    if spread:
                        spread_positions = json.loads(spread['positions'])
                
                # Create spread display
                if spread_positions:
                    # Calculate bounding box of the spread
                    min_x = min(p.get('x', 0) for p in spread_positions)
                    min_y = min(p.get('y', 0) for p in spread_positions)
                    max_x = max(p.get('x', 0) + p.get('width', 80) for p in spread_positions)
                    max_y = max(p.get('y', 0) + p.get('height', 120) for p in spread_positions)
                    spread_width = max_x - min_x
                    spread_height = max_y - min_y

                    # Panel size with padding, offset to center
                    panel_padding = 20
                    panel_width = spread_width + panel_padding * 2
                    panel_height = spread_height + panel_padding * 2
                    offset_x = panel_padding - min_x
                    offset_y = panel_padding - min_y

                    # Create container for spread and legend
                    spread_container = wx.Panel(self.viewer_panel)
                    spread_container.SetBackgroundColour(get_wx_color('bg_primary'))
                    spread_container_sizer = wx.BoxSizer(wx.VERTICAL)

                    # Legend toggle button with label
                    toggle_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    legend_toggle = wx.CheckBox(spread_container, label="")
                    toggle_sizer.Add(legend_toggle, 0, wx.RIGHT, 5)

                    legend_label = wx.StaticText(spread_container, label="Show Position Legend")
                    legend_label.SetForegroundColour(get_wx_color('text_primary'))
                    toggle_sizer.Add(legend_label, 0, wx.ALIGN_CENTER_VERTICAL)

                    legend_toggle.SetValue(False)
                    spread_container_sizer.Add(toggle_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 5)

                    # Horizontal layout for spread and legend
                    spread_legend_sizer = wx.BoxSizer(wx.HORIZONTAL)

                    # Spread panel
                    spread_panel = wx.Panel(spread_container, size=(panel_width, panel_height))
                    spread_panel.SetBackgroundColour(get_wx_color('card_slot'))

                    # Store references for legend toggle
                    spread_panel._position_labels = []
                    spread_panel._position_numbers = []

                    for i, pos in enumerate(spread_positions):
                        x, y = pos.get('x', 0) + offset_x, pos.get('y', 0) + offset_y
                        w, h = pos.get('width', 80), pos.get('height', 120)
                        label = pos.get('label', f'Position {i+1}')
                        is_position_rotated = pos.get('rotated', False)

                        if i < len(cards_used):
                            # Handle both old format (string) and new format (dict)
                            card_data = cards_used[i]
                            if isinstance(card_data, str):
                                card_name = card_data
                                is_reversed = False
                            else:
                                card_name = card_data.get('name', '')
                                is_reversed = card_data.get('reversed', False)

                            # Get image path and card ID using multi-deck aware function
                            image_path, card_id = get_card_info(card_data, card_name)
                            image_placed = False

                            if image_path and os.path.exists(image_path):
                                try:
                                    from PIL import Image as PILImage
                                    pil_img = PILImage.open(image_path)
                                    pil_img = pil_img.convert('RGB')

                                    # Rotate if position is rotated (for horizontal cards like Celtic Cross challenge)
                                    if is_position_rotated:
                                        pil_img = pil_img.rotate(90, expand=True)

                                    # Rotate if reversed
                                    if is_reversed:
                                        pil_img = pil_img.rotate(180)

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

                                        # Add tooltip with card name and position
                                        tooltip_text = f"{card_name} - {label}"
                                        if is_reversed:
                                            tooltip_text += " (Reversed)"
                                        bmp.SetToolTip(tooltip_text)

                                        # Add double-click to open card info
                                        if card_id:
                                            bmp.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card_id: self._on_view_card(None, cid))

                                        # Add (R) indicator for reversed cards
                                        if is_reversed:
                                            r_label = wx.StaticText(spread_panel, label="(R)")
                                            r_label.SetForegroundColour(get_wx_color('accent'))
                                            r_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                                            r_label.SetPosition((img_x + 2, y + 4))

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

                                # Add tooltip with card name and position
                                tooltip_text = f"{card_name} - {label}"
                                if is_reversed:
                                    tooltip_text += " (Reversed)"
                                slot.SetToolTip(tooltip_text)

                                # Add double-click to open card info
                                if card_id:
                                    slot.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card_id: self._on_view_card(None, cid))
                                    slot_label.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card_id: self._on_view_card(None, cid))

                            # Add position number (hidden by default)
                            pos_num = wx.StaticText(spread_panel, label=str(i + 1))
                            pos_num.SetForegroundColour(get_wx_color('text_secondary'))
                            pos_num.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                            pos_num.SetPosition((x - 12, y - 12))
                            pos_num.Hide()
                            spread_panel._position_numbers.append(pos_num)
                        else:
                            slot = wx.Panel(spread_panel, size=(w, h))
                            slot.SetPosition((x, y))
                            slot.SetBackgroundColour(get_wx_color('bg_tertiary'))
                            slot_label = wx.StaticText(slot, label=label)
                            slot_label.SetForegroundColour(get_wx_color('text_secondary'))
                            slot_label.SetPosition((5, h//2 - 8))

                    spread_legend_sizer.Add(spread_panel, 0, wx.ALL, 5)

                    # Create legend panel (hidden by default)
                    legend_panel = wx.Panel(spread_container)
                    legend_panel.SetBackgroundColour(get_wx_color('bg_secondary'))
                    legend_sizer = wx.BoxSizer(wx.VERTICAL)

                    legend_title = wx.StaticText(legend_panel, label="Position Legend:")
                    legend_title.SetForegroundColour(get_wx_color('text_primary'))
                    legend_title.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                    legend_sizer.Add(legend_title, 0, wx.ALL, 5)

                    for i, pos in enumerate(spread_positions):
                        label = pos.get('label', f'Position {i+1}')
                        legend_item = wx.StaticText(legend_panel, label=f"{i + 1}. {label}")
                        legend_item.SetForegroundColour(get_wx_color('text_primary'))
                        legend_item.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                        legend_sizer.Add(legend_item, 0, wx.LEFT | wx.BOTTOM, 5)

                    legend_panel.SetSizer(legend_sizer)
                    legend_panel.Hide()
                    spread_legend_sizer.Add(legend_panel, 0, wx.ALL, 5)

                    spread_container_sizer.Add(spread_legend_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

                    # Toggle handler
                    def on_legend_toggle(event):
                        show = legend_toggle.GetValue()
                        legend_panel.Show(show)
                        for num in spread_panel._position_numbers:
                            num.Show(show)
                        spread_container.Layout()
                        self.viewer_panel.Layout()
                        self.viewer_panel.SetupScrolling()

                    legend_toggle.Bind(wx.EVT_CHECKBOX, on_legend_toggle)

                    spread_container.SetSizer(spread_container_sizer)
                    self.viewer_sizer.Add(spread_container, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 15)
                else:
                    # No spread - show cards in a row
                    cards_sizer = wx.WrapSizer(wx.HORIZONTAL)
                    for card_info in cards_used:
                        # Handle both old format (string) and new format (dict)
                        if isinstance(card_info, str):
                            card_name = card_info
                            is_reversed = False
                        else:
                            card_name = card_info.get('name', '')
                            is_reversed = card_info.get('reversed', False)

                        # Get image path and card ID using multi-deck aware function
                        image_path, card_id = get_card_info(card_info, card_name)

                        card_panel = wx.Panel(self.viewer_panel, size=(90, 140))
                        card_panel.SetBackgroundColour(get_wx_color('bg_tertiary'))
                        card_sizer_inner = wx.BoxSizer(wx.VERTICAL)

                        # Add tooltip with card name
                        tooltip_text = card_name
                        if is_reversed:
                            tooltip_text += " (Reversed)"
                        card_panel.SetToolTip(tooltip_text)

                        # Add double-click to open card info
                        if card_id:
                            card_panel.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card_id: self._on_view_card(None, cid))

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

        # Add Reading button
        add_reading_btn = wx.Button(self.viewer_panel, label="+ Add Another Reading")
        add_reading_btn.Bind(wx.EVT_BUTTON, lambda e: self._on_add_reading(entry_id))
        self.viewer_sizer.Add(add_reading_btn, 0, wx.LEFT | wx.BOTTOM, 15)

        # Notes
        if entry['content']:
            notes_label = wx.StaticText(self.viewer_panel, label="Notes:")
            notes_label.SetForegroundColour(get_wx_color('accent'))
            notes_label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            self.viewer_sizer.Add(notes_label, 0, wx.LEFT, 15)

            notes_viewer = RichTextViewer(self.viewer_panel, value=entry['content'], min_height=60)
            self.viewer_sizer.Add(notes_viewer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        # Follow-up Notes
        follow_up_notes = self.db.get_follow_up_notes(entry_id)

        follow_up_header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        follow_up_label = wx.StaticText(self.viewer_panel, label="Follow-up Notes:")
        follow_up_label.SetForegroundColour(get_wx_color('accent'))
        follow_up_label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        follow_up_header_sizer.Add(follow_up_label, 0, wx.ALIGN_CENTER_VERTICAL)

        add_follow_up_btn = wx.Button(self.viewer_panel, label="+ Add Note", size=(80, -1))
        add_follow_up_btn.Bind(wx.EVT_BUTTON, lambda e: self._on_add_follow_up_note(entry_id))
        follow_up_header_sizer.Add(add_follow_up_btn, 0, wx.LEFT, 15)

        self.viewer_sizer.Add(follow_up_header_sizer, 0, wx.LEFT | wx.TOP, 15)

        if follow_up_notes:
            for note in follow_up_notes:
                note_panel = wx.Panel(self.viewer_panel)
                note_panel.SetBackgroundColour(get_wx_color('bg_tertiary'))
                note_sizer = wx.BoxSizer(wx.VERTICAL)

                # Date header
                try:
                    dt = datetime.fromisoformat(note['created_at'])
                    date_str = dt.strftime('%B %d, %Y at %I:%M %p')
                except:
                    date_str = note['created_at'][:16] if note['created_at'] else 'Unknown date'

                date_label = wx.StaticText(note_panel, label=date_str)
                date_label.SetForegroundColour(get_wx_color('text_dim'))
                date_label.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
                note_sizer.Add(date_label, 0, wx.ALL, 8)

                # Note content
                note_viewer = RichTextViewer(note_panel, value=note['content'], min_height=40)
                note_sizer.Add(note_viewer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

                # Edit/Delete buttons
                btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
                edit_btn = wx.Button(note_panel, label="Edit", size=(50, -1))
                edit_btn.Bind(wx.EVT_BUTTON, lambda e, nid=note['id'], eid=entry_id: self._on_edit_follow_up_note(nid, eid))
                delete_btn = wx.Button(note_panel, label="Delete", size=(50, -1))
                delete_btn.Bind(wx.EVT_BUTTON, lambda e, nid=note['id'], eid=entry_id: self._on_delete_follow_up_note(nid, eid))
                btn_sizer.Add(edit_btn, 0, wx.RIGHT, 5)
                btn_sizer.Add(delete_btn, 0)
                note_sizer.Add(btn_sizer, 0, wx.LEFT | wx.BOTTOM, 8)

                note_panel.SetSizer(note_sizer)
                self.viewer_sizer.Add(note_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 15)
        else:
            no_notes_label = wx.StaticText(self.viewer_panel, label="No follow-up notes yet")
            no_notes_label.SetForegroundColour(get_wx_color('text_dim'))
            self.viewer_sizer.Add(no_notes_label, 0, wx.LEFT | wx.TOP, 15)

        self.viewer_sizer.AddSpacer(15)

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
    
    def _on_add_follow_up_note(self, entry_id):
        """Add a follow-up note to an entry"""
        dlg = wx.Dialog(self, title="Add Follow-up Note", size=(500, 300))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Instructions
        instr_label = wx.StaticText(dlg, label="Add a follow-up note to record how this reading played out:")
        instr_label.SetForegroundColour(get_wx_color('text_secondary'))
        sizer.Add(instr_label, 0, wx.ALL, 15)

        # Note content
        note_ctrl = RichTextPanel(dlg, value='', min_height=150)
        sizer.Add(note_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

        # Date note
        date_note = wx.StaticText(dlg, label=f"This note will be dated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        date_note.SetForegroundColour(get_wx_color('text_dim'))
        sizer.Add(date_note, 0, wx.ALL, 15)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Add Note")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)

        dlg.SetSizer(sizer)

        if dlg.ShowModal() == wx.ID_OK:
            content = note_ctrl.GetValue().strip()
            if content:
                self.db.add_follow_up_note(entry_id, content)
                self._display_entry_in_viewer(entry_id)

        dlg.Destroy()

    def _on_edit_follow_up_note(self, note_id, entry_id):
        """Edit a follow-up note"""
        # Get the current note content
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM follow_up_notes WHERE id = ?', (note_id,))
        note = cursor.fetchone()
        if not note:
            return

        dlg = wx.Dialog(self, title="Edit Follow-up Note", size=(500, 300))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Date label
        try:
            dt = datetime.fromisoformat(note['created_at'])
            date_str = dt.strftime('%B %d, %Y at %I:%M %p')
        except:
            date_str = note['created_at'][:16] if note['created_at'] else 'Unknown date'

        date_label = wx.StaticText(dlg, label=f"Note from: {date_str}")
        date_label.SetForegroundColour(get_wx_color('text_secondary'))
        sizer.Add(date_label, 0, wx.ALL, 15)

        # Note content
        note_ctrl = RichTextPanel(dlg, value=note['content'], min_height=150)
        sizer.Add(note_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Save")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)

        dlg.SetSizer(sizer)

        if dlg.ShowModal() == wx.ID_OK:
            content = note_ctrl.GetValue().strip()
            if content:
                self.db.update_follow_up_note(note_id, content)
                self._display_entry_in_viewer(entry_id)

        dlg.Destroy()

    def _on_delete_follow_up_note(self, note_id, entry_id):
        """Delete a follow-up note"""
        result = wx.MessageBox(
            "Delete this follow-up note?",
            "Confirm Delete",
            wx.YES_NO | wx.ICON_WARNING
        )
        if result == wx.YES:
            self.db.delete_follow_up_note(note_id)
            self._display_entry_in_viewer(entry_id)

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

        # Main dialog sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Scrolled window for content
        scroll_win = wx.ScrolledWindow(dlg, style=wx.VSCROLL)
        scroll_win.SetScrollRate(0, 20)
        scroll_win.SetBackgroundColour(get_wx_color('bg_primary'))

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Title
        title_sizer = wx.BoxSizer(wx.HORIZONTAL)
        title_label = wx.StaticText(scroll_win, label="Title:")
        title_label.SetForegroundColour(get_wx_color('text_primary'))
        title_sizer.Add(title_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        title_ctrl = wx.TextCtrl(scroll_win)
        title_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        title_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        title_ctrl.SetValue(entry['title'] or '')
        title_sizer.Add(title_ctrl, 1, wx.EXPAND)
        sizer.Add(title_sizer, 0, wx.EXPAND | wx.ALL, 15)

        # Date/Time selection
        datetime_sizer = wx.BoxSizer(wx.HORIZONTAL)

        datetime_label = wx.StaticText(scroll_win, label="Reading Date/Time:")
        datetime_label.SetForegroundColour(get_wx_color('text_primary'))
        datetime_sizer.Add(datetime_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        # Radio buttons for now vs custom (empty labels with separate StaticText for macOS)
        use_now_radio = wx.RadioButton(scroll_win, label="", style=wx.RB_GROUP)
        datetime_sizer.Add(use_now_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
        now_label = wx.StaticText(scroll_win, label="Now")
        now_label.SetForegroundColour(get_wx_color('text_primary'))
        datetime_sizer.Add(now_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)

        use_custom_radio = wx.RadioButton(scroll_win, label="")
        datetime_sizer.Add(use_custom_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
        custom_label = wx.StaticText(scroll_win, label="Custom:")
        custom_label.SetForegroundColour(get_wx_color('text_primary'))
        datetime_sizer.Add(custom_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        # Date picker
        date_picker = wx.adv.DatePickerCtrl(scroll_win, style=wx.adv.DP_DROPDOWN)
        datetime_sizer.Add(date_picker, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        # Time picker (hour:minute)
        time_ctrl = wx.TextCtrl(scroll_win, size=(60, -1))
        time_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        time_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        time_ctrl.SetValue(datetime.now().strftime("%H:%M"))
        datetime_sizer.Add(time_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)

        # Initialize based on existing entry data
        existing_reading_dt = entry['reading_datetime'] if 'reading_datetime' in entry.keys() else None
        if existing_reading_dt and not is_new:
            use_custom_radio.SetValue(True)
            try:
                dt = datetime.fromisoformat(existing_reading_dt)
                wx_date = wx.DateTime()
                wx_date.Set(dt.day, dt.month - 1, dt.year)
                date_picker.SetValue(wx_date)
                time_ctrl.SetValue(dt.strftime("%H:%M"))
            except:
                use_now_radio.SetValue(True)
        else:
            use_now_radio.SetValue(True)

        # Enable/disable date/time controls based on radio selection
        def on_datetime_radio_change(event):
            custom = use_custom_radio.GetValue()
            date_picker.Enable(custom)
            time_ctrl.Enable(custom)

        use_now_radio.Bind(wx.EVT_RADIOBUTTON, on_datetime_radio_change)
        use_custom_radio.Bind(wx.EVT_RADIOBUTTON, on_datetime_radio_change)
        on_datetime_radio_change(None)  # Initial state

        sizer.Add(datetime_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        # Location
        location_sizer = wx.BoxSizer(wx.HORIZONTAL)

        location_label = wx.StaticText(scroll_win, label="Location:")
        location_label.SetForegroundColour(get_wx_color('text_primary'))
        location_sizer.Add(location_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        location_ctrl = wx.TextCtrl(scroll_win, size=(250, -1))
        location_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        location_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        location_ctrl.SetHint("City, Country or address")
        existing_location = entry['location_name'] if 'location_name' in entry.keys() else None
        if existing_location:
            location_ctrl.SetValue(existing_location)
        location_sizer.Add(location_ctrl, 1, wx.EXPAND | wx.RIGHT, 10)

        # Store lat/lon (hidden, for future astrological data)
        dlg._location_lat = entry['location_lat'] if 'location_lat' in entry.keys() else None
        dlg._location_lon = entry['location_lon'] if 'location_lon' in entry.keys() else None

        sizer.Add(location_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        # Querent and Reader selection
        profiles = self.db.get_profiles()
        profile_names = ["(None)"] + [p['name'] for p in profiles]
        profile_ids = [None] + [p['id'] for p in profiles]

        people_sizer = wx.BoxSizer(wx.HORIZONTAL)

        querent_label = wx.StaticText(scroll_win, label="Querent:")
        querent_label.SetForegroundColour(get_wx_color('text_primary'))
        people_sizer.Add(querent_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        querent_choice = wx.Choice(scroll_win, choices=profile_names)
        querent_choice.SetSelection(0)
        people_sizer.Add(querent_choice, 0, wx.RIGHT, 20)

        reader_label = wx.StaticText(scroll_win, label="Reader:")
        reader_label.SetForegroundColour(get_wx_color('text_primary'))
        people_sizer.Add(reader_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        reader_choice = wx.Choice(scroll_win, choices=profile_names)
        reader_choice.SetSelection(0)
        people_sizer.Add(reader_choice, 0, wx.RIGHT, 15)

        # "Same as Querent" checkbox (empty label with separate StaticText for macOS)
        same_as_querent_cb = wx.CheckBox(scroll_win, label="")
        people_sizer.Add(same_as_querent_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
        same_label = wx.StaticText(scroll_win, label="Reader same as Querent")
        same_label.SetForegroundColour(get_wx_color('text_primary'))
        people_sizer.Add(same_label, 0, wx.ALIGN_CENTER_VERTICAL)

        def on_same_as_querent(event):
            if same_as_querent_cb.GetValue():
                reader_choice.SetSelection(querent_choice.GetSelection())
                reader_choice.Enable(False)
            else:
                reader_choice.Enable(True)

        def on_querent_change(event):
            if same_as_querent_cb.GetValue():
                reader_choice.SetSelection(querent_choice.GetSelection())

        same_as_querent_cb.Bind(wx.EVT_CHECKBOX, on_same_as_querent)
        querent_choice.Bind(wx.EVT_CHOICE, on_querent_change)

        # Load existing querent/reader from entry
        existing_querent_id = entry['querent_id'] if 'querent_id' in entry.keys() else None
        existing_reader_id = entry['reader_id'] if 'reader_id' in entry.keys() else None
        if existing_querent_id and existing_querent_id in profile_ids:
            querent_choice.SetSelection(profile_ids.index(existing_querent_id))
        if existing_reader_id and existing_reader_id in profile_ids:
            reader_choice.SetSelection(profile_ids.index(existing_reader_id))
        if existing_querent_id and existing_querent_id == existing_reader_id:
            same_as_querent_cb.SetValue(True)
            on_same_as_querent(None)

        sizer.Add(people_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        # Store profile_ids for later use when saving
        dlg._profile_ids = profile_ids

        # Spread/Deck selection
        select_sizer = wx.BoxSizer(wx.HORIZONTAL)

        spread_label = wx.StaticText(scroll_win, label="Spread:")
        spread_label.SetForegroundColour(get_wx_color('text_primary'))
        select_sizer.Add(spread_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        spread_choice = wx.Choice(scroll_win, choices=list(self._spread_map.keys()))
        select_sizer.Add(spread_choice, 0, wx.RIGHT, 20)

        deck_label = wx.StaticText(scroll_win, label="Default Deck:")
        deck_label.SetForegroundColour(get_wx_color('text_primary'))
        select_sizer.Add(deck_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        deck_choice = wx.Choice(scroll_win, choices=list(self._deck_map.keys()))
        select_sizer.Add(deck_choice, 0, wx.RIGHT, 10)

        # Use Any Deck toggle (empty label + StaticText for macOS)
        use_any_sizer = wx.BoxSizer(wx.HORIZONTAL)
        use_any_deck_cb = wx.CheckBox(scroll_win, label="")
        use_any_sizer.Add(use_any_deck_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
        use_any_label = wx.StaticText(scroll_win, label="Use Any Deck")
        use_any_label.SetForegroundColour(get_wx_color('text_primary'))
        use_any_sizer.Add(use_any_label, 0, wx.ALIGN_CENTER_VERTICAL)
        select_sizer.Add(use_any_sizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        # Hint about multi-deck
        multi_deck_hint = wx.StaticText(scroll_win, label="(You can select different decks per position)")
        multi_deck_hint.SetForegroundColour(get_wx_color('text_dim'))
        multi_deck_hint.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        select_sizer.Add(multi_deck_hint, 0, wx.ALIGN_CENTER_VERTICAL)

        sizer.Add(select_sizer, 0, wx.LEFT | wx.RIGHT, 15)

        # Store full deck info for filtering (deck_name -> {id, cartomancy_type})
        dlg._all_decks = {}
        for deck_name, deck_id in self._deck_map.items():
            deck = self.db.get_deck(deck_id)
            dlg._all_decks[deck_name] = {
                'id': deck_id,
                'cartomancy_type': deck['cartomancy_type_name'] if deck else None
            }
        
        # Spread canvas
        spread_canvas = wx.Panel(scroll_win, size=(-1, 350))
        spread_canvas.SetBackgroundColour(get_wx_color('card_slot'))
        sizer.Add(spread_canvas, 0, wx.EXPAND | wx.ALL, 15)

        # Cards label
        cards_label = wx.StaticText(scroll_win, label="Click positions above to assign cards")
        cards_label.SetForegroundColour(get_wx_color('text_dim'))
        sizer.Add(cards_label, 0, wx.LEFT, 15)

        # Notes
        notes_label = wx.StaticText(scroll_win, label="Notes:")
        notes_label.SetForegroundColour(get_wx_color('text_primary'))
        sizer.Add(notes_label, 0, wx.LEFT | wx.TOP, 15)

        content_ctrl = RichTextPanel(scroll_win, value=entry['content'] or '', min_height=120)
        sizer.Add(content_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        
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
                # Build deck_cards lookup for all decks that might be referenced
                all_deck_cards = {}  # deck_id -> {card_name -> {id, image_path}}
                for did in self._deck_map.values():
                    all_deck_cards[did] = {}
                    for card in self.db.get_cards(did):
                        all_deck_cards[did][card['name']] = {
                            'id': card['id'],
                            'image_path': card['image_path']
                        }

                for i, card_data in enumerate(cards_used):
                    # Handle old format (string), basic dict, and multi-deck format
                    if isinstance(card_data, str):
                        card_name = card_data
                        reversed_state = False
                        card_deck_id = dlg._selected_deck_id
                        card_deck_name = reading.get('deck_name', '')
                    else:
                        card_name = card_data.get('name', '')
                        reversed_state = card_data.get('reversed', False)
                        # Multi-deck format includes deck_id per card
                        card_deck_id = card_data.get('deck_id', dlg._selected_deck_id)
                        card_deck_name = card_data.get('deck_name', reading.get('deck_name', ''))

                    # Get image path from the card's deck
                    image_path = None
                    card_id = None
                    if card_deck_id and card_deck_id in all_deck_cards:
                        card_info = all_deck_cards[card_deck_id].get(card_name, {})
                        image_path = card_info.get('image_path')
                        card_id = card_info.get('id')

                    dlg._spread_cards[i] = {
                        'id': card_id,
                        'name': card_name,
                        'image_path': image_path,
                        'reversed': reversed_state,
                        'deck_id': card_deck_id,
                        'deck_name': card_deck_name
                    }
        else:
            # For new entries, auto-select default deck if a spread is selected
            spread_name = spread_choice.GetStringSelection()
            if spread_name and spread_name in self._spread_map:
                spread = self.db.get_spread(self._spread_map[spread_name])
                if spread and 'cartomancy_type' in spread.keys() and spread['cartomancy_type']:
                    default_deck_id = self.db.get_default_deck(spread['cartomancy_type'])
                    if default_deck_id:
                        # Find and select the default deck in the deck_choice dropdown
                        for name, did in self._deck_map.items():
                            if did == default_deck_id:
                                idx = deck_choice.FindString(name)
                                if idx != wx.NOT_FOUND:
                                    deck_choice.SetSelection(idx)
                                    dlg._selected_deck_id = did
                                break

        def on_deck_change(event):
            name = deck_choice.GetStringSelection()
            if name in dlg._all_decks:
                dlg._selected_deck_id = dlg._all_decks[name]['id']

        deck_choice.Bind(wx.EVT_CHOICE, on_deck_change)

        def update_deck_choices(allowed_types=None):
            """Update deck choices based on allowed cartomancy types"""
            current_selection = deck_choice.GetStringSelection()
            deck_choice.Clear()

            for deck_name, deck_info in dlg._all_decks.items():
                # If no restrictions or "use any deck" is checked, show all
                if not allowed_types or use_any_deck_cb.GetValue():
                    deck_choice.Append(deck_name)
                # Otherwise only show decks matching allowed types
                elif deck_info['cartomancy_type'] in allowed_types:
                    deck_choice.Append(deck_name)

            # Try to restore previous selection
            if current_selection:
                idx = deck_choice.FindString(current_selection)
                if idx != wx.NOT_FOUND:
                    deck_choice.SetSelection(idx)

        def on_spread_change(event):
            dlg._spread_cards = {}
            spread_canvas.Refresh()

            spread_name = spread_choice.GetStringSelection()
            allowed_types = None

            if spread_name and spread_name in self._spread_map:
                spread = self.db.get_spread(self._spread_map[spread_name])
                if spread:
                    # Check for allowed_deck_types (new format)
                    allowed_types_json = spread['allowed_deck_types'] if 'allowed_deck_types' in spread.keys() else None
                    if allowed_types_json:
                        allowed_types = json.loads(allowed_types_json)

                    # Filter deck choices based on allowed types
                    update_deck_choices(allowed_types)

                    # Auto-select default deck based on first allowed type
                    if allowed_types:
                        default_deck_id = self.db.get_default_deck(allowed_types[0])
                        if default_deck_id:
                            for name, info in dlg._all_decks.items():
                                if info['id'] == default_deck_id:
                                    idx = deck_choice.FindString(name)
                                    if idx != wx.NOT_FOUND:
                                        deck_choice.SetSelection(idx)
                                        dlg._selected_deck_id = default_deck_id
                                    break
                    # Fall back to old cartomancy_type field
                    elif 'cartomancy_type' in spread.keys() and spread['cartomancy_type']:
                        default_deck_id = self.db.get_default_deck(spread['cartomancy_type'])
                        if default_deck_id:
                            for name, info in dlg._all_decks.items():
                                if info['id'] == default_deck_id:
                                    idx = deck_choice.FindString(name)
                                    if idx != wx.NOT_FOUND:
                                        deck_choice.SetSelection(idx)
                                        dlg._selected_deck_id = default_deck_id
                                    break
                    else:
                        # No restrictions - show all decks
                        update_deck_choices(None)

            # Store allowed types for card picker
            dlg._spread_allowed_types = allowed_types

        spread_choice.Bind(wx.EVT_CHOICE, on_spread_change)

        def on_use_any_deck_change(event):
            """Re-filter decks when 'use any deck' is toggled"""
            spread_name = spread_choice.GetStringSelection()
            if spread_name and spread_name in self._spread_map:
                spread = self.db.get_spread(self._spread_map[spread_name])
                if spread:
                    allowed_types_json = spread['allowed_deck_types'] if 'allowed_deck_types' in spread.keys() else None
                    if allowed_types_json:
                        allowed_types = json.loads(allowed_types_json)
                        update_deck_choices(allowed_types)
                    else:
                        update_deck_choices(None)
            else:
                update_deck_choices(None)

        use_any_deck_cb.Bind(wx.EVT_CHECKBOX, on_use_any_deck_change)
        
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

            # Calculate spread bounding box for centering
            if positions:
                min_x = min(p.get('x', 0) for p in positions)
                min_y = min(p.get('y', 0) for p in positions)
                max_x = max(p.get('x', 0) + p.get('width', 80) for p in positions)
                max_y = max(p.get('y', 0) + p.get('height', 120) for p in positions)
                spread_width = max_x - min_x
                spread_height = max_y - min_y

                # Calculate offset to center the spread
                canvas_w, canvas_h = spread_canvas.GetSize()
                offset_x = (canvas_w - spread_width) // 2 - min_x
                offset_y = (canvas_h - spread_height) // 2 - min_y
            else:
                offset_x, offset_y = 0, 0

            for i, pos in enumerate(positions):
                x, y = pos.get('x', 0) + offset_x, pos.get('y', 0) + offset_y
                w, h = pos.get('width', 80), pos.get('height', 120)
                label = pos.get('label', f'Position {i+1}')
                is_position_rotated = pos.get('rotated', False)

                if i in dlg._spread_cards:
                    card_data = dlg._spread_cards[i]
                    image_path = card_data.get('image_path')
                    image_drawn = False

                    if image_path and os.path.exists(image_path):
                        try:
                            from PIL import Image as PILImage
                            pil_img = PILImage.open(image_path)
                            pil_img = pil_img.convert('RGB')

                            # Rotate if position is rotated (for horizontal cards like Celtic Cross challenge)
                            if is_position_rotated:
                                pil_img = pil_img.rotate(90, expand=True)

                            # Rotate if card is reversed
                            if card_data.get('reversed', False):
                                pil_img = pil_img.rotate(180)

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

                                # Add (R) indicator for reversed cards
                                if card_data.get('reversed', False):
                                    dc.SetTextForeground(get_wx_color('accent'))
                                    dc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                                    dc.DrawText("(R)", img_x + 2, y + 4)

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

            # Calculate offset for centered spread (same as paint function)
            if positions:
                min_x = min(p.get('x', 0) for p in positions)
                min_y = min(p.get('y', 0) for p in positions)
                max_x = max(p.get('x', 0) + p.get('width', 80) for p in positions)
                max_y = max(p.get('y', 0) + p.get('height', 120) for p in positions)
                spread_width = max_x - min_x
                spread_height = max_y - min_y
                canvas_w, canvas_h = spread_canvas.GetSize()
                offset_x = (canvas_w - spread_width) // 2 - min_x
                offset_y = (canvas_h - spread_height) // 2 - min_y
            else:
                offset_x, offset_y = 0, 0

            click_x, click_y = event.GetX(), event.GetY()

            for i, pos in enumerate(positions):
                px, py = pos.get('x', 0) + offset_x, pos.get('y', 0) + offset_y
                pw, ph = pos.get('width', 80), pos.get('height', 120)

                if px <= click_x <= px + pw and py <= click_y <= py + ph:
                    # Create a card picker dialog with deck selection
                    card_dlg = wx.Dialog(dlg, title=f"Select Card for: {pos.get('label', f'Position {i+1}')}",
                                        size=(450, 550))
                    card_dlg.SetBackgroundColour(get_wx_color('bg_primary'))
                    card_dlg_sizer = wx.BoxSizer(wx.VERTICAL)

                    # Deck selector
                    deck_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    deck_select_label = wx.StaticText(card_dlg, label="Deck:")
                    deck_select_label.SetForegroundColour(get_wx_color('text_primary'))
                    deck_select_sizer.Add(deck_select_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

                    # Build filtered deck list based on spread's allowed types
                    allowed_types = getattr(dlg, '_spread_allowed_types', None)
                    use_any = use_any_deck_cb.GetValue()
                    picker_deck_names = []
                    for deck_name, deck_info in dlg._all_decks.items():
                        if not allowed_types or use_any:
                            picker_deck_names.append(deck_name)
                        elif deck_info['cartomancy_type'] in allowed_types:
                            picker_deck_names.append(deck_name)

                    picker_deck_choice = wx.Choice(card_dlg, choices=picker_deck_names)
                    # Pre-select the default deck
                    if dlg._selected_deck_id:
                        for name, info in dlg._all_decks.items():
                            if info['id'] == dlg._selected_deck_id:
                                idx = picker_deck_choice.FindString(name)
                                if idx != wx.NOT_FOUND:
                                    picker_deck_choice.SetSelection(idx)
                                break
                    deck_select_sizer.Add(picker_deck_choice, 1, wx.EXPAND)
                    card_dlg_sizer.Add(deck_select_sizer, 0, wx.EXPAND | wx.ALL, 10)

                    # Use any deck checkbox in card picker (empty label + StaticText for macOS)
                    picker_use_any_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    picker_use_any_cb = wx.CheckBox(card_dlg, label="")
                    picker_use_any_cb.SetValue(use_any)
                    picker_use_any_sizer.Add(picker_use_any_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
                    picker_use_any_label = wx.StaticText(card_dlg, label="Use Any Deck (override restriction)")
                    picker_use_any_label.SetForegroundColour(get_wx_color('text_dim'))
                    picker_use_any_sizer.Add(picker_use_any_label, 0, wx.ALIGN_CENTER_VERTICAL)
                    card_dlg_sizer.Add(picker_use_any_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

                    # Card list with thumbnails
                    thumb_size = 48
                    card_listctrl = wx.ListCtrl(card_dlg, style=wx.LC_LIST | wx.LC_SINGLE_SEL)
                    card_listctrl.SetBackgroundColour(get_wx_color('bg_input'))
                    card_listctrl.SetForegroundColour(get_wx_color('text_primary'))
                    card_dlg_sizer.Add(card_listctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

                    # Store card data and image list (must keep reference to prevent GC)
                    card_dlg._card_data = []
                    card_dlg._image_list = wx.ImageList(thumb_size, thumb_size)
                    card_listctrl.SetImageList(card_dlg._image_list, wx.IMAGE_LIST_SMALL)

                    # Populate cards from selected deck with thumbnails
                    def populate_cards(deck_id):
                        card_listctrl.DeleteAllItems()
                        card_dlg._card_data = []
                        # Clear and recreate image list
                        card_dlg._image_list.RemoveAll()

                        if deck_id:
                            cards = self.db.get_cards(deck_id)
                            for card in cards:
                                card_dlg._card_data.append(card)
                                # Get thumbnail
                                img_idx = -1
                                if card['image_path']:
                                    thumb_path = self.thumb_cache.get_thumbnail_path(card['image_path'])
                                    if thumb_path:
                                        try:
                                            img = wx.Image(thumb_path, wx.BITMAP_TYPE_ANY)
                                            if img.IsOk():
                                                # Scale to fit the thumbnail size
                                                w, h = img.GetWidth(), img.GetHeight()
                                                if w > 0 and h > 0:
                                                    scale = min(thumb_size / w, thumb_size / h)
                                                    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
                                                    img = img.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
                                                    # Resize canvas to exact thumb_size with dark background
                                                    img.Resize((thumb_size, thumb_size),
                                                              ((thumb_size - new_w) // 2, (thumb_size - new_h) // 2),
                                                              40, 40, 40)
                                                    img_idx = card_dlg._image_list.Add(wx.Bitmap(img))
                                        except Exception:
                                            pass
                                idx = card_listctrl.InsertItem(card_listctrl.GetItemCount(), card['name'], img_idx)
                                card_listctrl.SetItemData(idx, len(card_dlg._card_data) - 1)

                    # Initial populate
                    current_picker_deck_id = dlg._selected_deck_id
                    populate_cards(current_picker_deck_id)

                    def on_picker_deck_change(e):
                        nonlocal current_picker_deck_id
                        name = picker_deck_choice.GetStringSelection()
                        if name in dlg._all_decks:
                            current_picker_deck_id = dlg._all_decks[name]['id']
                            populate_cards(current_picker_deck_id)

                    picker_deck_choice.Bind(wx.EVT_CHOICE, on_picker_deck_change)

                    def on_picker_use_any_change(e):
                        """Re-filter deck choices when 'use any deck' is toggled in picker"""
                        nonlocal current_picker_deck_id
                        current_selection = picker_deck_choice.GetStringSelection()
                        picker_deck_choice.Clear()

                        picker_use_any = picker_use_any_cb.GetValue()
                        for deck_name, deck_info in dlg._all_decks.items():
                            if not allowed_types or picker_use_any:
                                picker_deck_choice.Append(deck_name)
                            elif deck_info['cartomancy_type'] in allowed_types:
                                picker_deck_choice.Append(deck_name)

                        # Try to restore selection
                        if current_selection:
                            idx = picker_deck_choice.FindString(current_selection)
                            if idx != wx.NOT_FOUND:
                                picker_deck_choice.SetSelection(idx)
                            elif picker_deck_choice.GetCount() > 0:
                                picker_deck_choice.SetSelection(0)
                                name = picker_deck_choice.GetStringSelection()
                                if name in dlg._all_decks:
                                    current_picker_deck_id = dlg._all_decks[name]['id']
                                    populate_cards(current_picker_deck_id)

                    picker_use_any_cb.Bind(wx.EVT_CHECKBOX, on_picker_use_any_change)

                    # Buttons
                    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    cancel_btn = wx.Button(card_dlg, wx.ID_CANCEL, "Cancel")
                    select_btn = wx.Button(card_dlg, wx.ID_OK, "Select")
                    btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
                    btn_sizer.Add(select_btn, 0)
                    card_dlg_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

                    card_dlg.SetSizer(card_dlg_sizer)

                    if card_dlg.ShowModal() == wx.ID_OK:
                        sel_idx = card_listctrl.GetFirstSelected()
                        if sel_idx != -1:
                            data_idx = card_listctrl.GetItemData(sel_idx)
                            card = card_dlg._card_data[data_idx]
                            deck_name_full = picker_deck_choice.GetStringSelection()
                            deck_name_clean = deck_name_full.split(' (')[0] if deck_name_full else None

                            dlg._spread_cards[i] = {
                                'id': card['id'],
                                'name': card['name'],
                                'image_path': card['image_path'],
                                'reversed': False,
                                'deck_id': current_picker_deck_id,
                                'deck_name': deck_name_clean
                            }

                            # Update cards label
                            if dlg._spread_cards:
                                names = [c['name'] for c in dlg._spread_cards.values()]
                                cards_label.SetLabel(f"Cards: {', '.join(names)}")

                            spread_canvas.Refresh()
                    card_dlg.Destroy()
                    break

        def on_canvas_right_click(event):
            spread_name = spread_choice.GetStringSelection()
            if not spread_name or spread_name not in self._spread_map:
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
                    # Check if there's a card in this position
                    if i in dlg._spread_cards:
                        # Create context menu
                        menu = wx.Menu()
                        is_reversed = dlg._spread_cards[i].get('reversed', False)

                        toggle_item = menu.Append(wx.ID_ANY, "Upright" if is_reversed else "Reversed")
                        remove_item = menu.Append(wx.ID_ANY, "Remove Card")

                        def on_toggle(e):
                            dlg._spread_cards[i]['reversed'] = not dlg._spread_cards[i].get('reversed', False)
                            spread_canvas.Refresh()

                        def on_remove(e):
                            del dlg._spread_cards[i]
                            if dlg._spread_cards:
                                names = [c['name'] for c in dlg._spread_cards.values()]
                                cards_label.SetLabel(f"Cards: {', '.join(names)}")
                            else:
                                cards_label.SetLabel("Cards: None")
                            spread_canvas.Refresh()

                        spread_canvas.Bind(wx.EVT_MENU, on_toggle, toggle_item)
                        spread_canvas.Bind(wx.EVT_MENU, on_remove, remove_item)

                        spread_canvas.PopupMenu(menu)
                        menu.Destroy()
                    break

        spread_canvas.Bind(wx.EVT_LEFT_DOWN, on_canvas_click)
        spread_canvas.Bind(wx.EVT_RIGHT_DOWN, on_canvas_right_click)

        # Set the scroll window sizer
        scroll_win.SetSizer(sizer)

        # Add scroll window to main sizer
        main_sizer.Add(scroll_win, 1, wx.EXPAND)

        # Buttons (outside scroll area so always visible)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Save")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)

        dlg.SetSizer(main_sizer)

        if dlg.ShowModal() == wx.ID_OK:
            # Save the entry
            title = title_ctrl.GetValue()
            content = content_ctrl.GetValue()

            # Get reading datetime
            if use_now_radio.GetValue():
                reading_datetime = datetime.now().isoformat()
            else:
                wx_date = date_picker.GetValue()
                time_str = time_ctrl.GetValue().strip()
                try:
                    hour, minute = map(int, time_str.split(':'))
                except:
                    hour, minute = 12, 0
                reading_datetime = datetime(
                    wx_date.GetYear(),
                    wx_date.GetMonth() + 1,
                    wx_date.GetDay(),
                    hour, minute
                ).isoformat()

            # Get location
            location_name = location_ctrl.GetValue().strip() or None
            location_lat = dlg._location_lat
            location_lon = dlg._location_lon

            # Get querent and reader
            querent_idx = querent_choice.GetSelection()
            reader_idx = reader_choice.GetSelection()
            querent_id = dlg._profile_ids[querent_idx] if querent_idx > 0 else None
            reader_id = dlg._profile_ids[reader_idx] if reader_idx > 0 else None
            # Use 0 as sentinel for "clear" vs None for "don't update"
            querent_id_param = querent_id if querent_id else 0
            reader_id_param = reader_id if reader_id else 0

            self.db.update_entry(
                entry_id,
                title=title,
                content=content,
                reading_datetime=reading_datetime,
                location_name=location_name,
                location_lat=location_lat,
                location_lon=location_lon,
                querent_id=querent_id_param,
                reader_id=reader_id_param
            )
            
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
                
                # Save cards with reversed state and deck info (multi-deck support)
                cards_used = [
                    {
                        'name': c['name'],
                        'reversed': c.get('reversed', False),
                        'deck_id': c.get('deck_id'),
                        'deck_name': c.get('deck_name')
                    }
                    for c in dlg._spread_cards.values()
                ]
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

    def _on_add_reading(self, entry_id):
        """Add another reading to an existing entry"""
        dlg = wx.Dialog(self, title="Add Reading", size=(700, 500))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Spread/Deck selection
        select_sizer = wx.BoxSizer(wx.HORIZONTAL)

        spread_label = wx.StaticText(dlg, label="Spread:")
        spread_label.SetForegroundColour(get_wx_color('text_primary'))
        select_sizer.Add(spread_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        spread_choice = wx.Choice(dlg, choices=list(self._spread_map.keys()))
        select_sizer.Add(spread_choice, 0, wx.RIGHT, 20)

        deck_label = wx.StaticText(dlg, label="Default Deck:")
        deck_label.SetForegroundColour(get_wx_color('text_primary'))
        select_sizer.Add(deck_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        deck_choice = wx.Choice(dlg, choices=list(self._deck_map.keys()))
        select_sizer.Add(deck_choice, 0, wx.RIGHT, 10)

        # Use Any Deck toggle (empty label + StaticText for macOS)
        use_any_sizer = wx.BoxSizer(wx.HORIZONTAL)
        use_any_deck_cb = wx.CheckBox(dlg, label="")
        use_any_sizer.Add(use_any_deck_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
        use_any_label = wx.StaticText(dlg, label="Use Any Deck")
        use_any_label.SetForegroundColour(get_wx_color('text_primary'))
        use_any_sizer.Add(use_any_label, 0, wx.ALIGN_CENTER_VERTICAL)
        select_sizer.Add(use_any_sizer, 0, wx.ALIGN_CENTER_VERTICAL)

        sizer.Add(select_sizer, 0, wx.ALL, 15)

        # Store full deck info for filtering
        dlg._all_decks = {}
        for deck_name, deck_id in self._deck_map.items():
            deck = self.db.get_deck(deck_id)
            dlg._all_decks[deck_name] = {
                'id': deck_id,
                'cartomancy_type': deck['cartomancy_type_name'] if deck else None
            }

        # Spread canvas
        spread_canvas = wx.Panel(dlg, size=(-1, 300))
        spread_canvas.SetBackgroundColour(get_wx_color('card_slot'))
        sizer.Add(spread_canvas, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

        # Cards label
        cards_label = wx.StaticText(dlg, label="Click positions above to assign cards")
        cards_label.SetForegroundColour(get_wx_color('text_dim'))
        sizer.Add(cards_label, 0, wx.LEFT | wx.TOP, 15)

        # Dialog state
        dlg._spread_cards = {}
        dlg._selected_deck_id = None

        def on_deck_change(event):
            name = deck_choice.GetStringSelection()
            if name in dlg._all_decks:
                dlg._selected_deck_id = dlg._all_decks[name]['id']

        deck_choice.Bind(wx.EVT_CHOICE, on_deck_change)

        def update_deck_choices(allowed_types=None):
            """Update deck choices based on allowed cartomancy types"""
            current_selection = deck_choice.GetStringSelection()
            deck_choice.Clear()

            for deck_name, deck_info in dlg._all_decks.items():
                if not allowed_types or use_any_deck_cb.GetValue():
                    deck_choice.Append(deck_name)
                elif deck_info['cartomancy_type'] in allowed_types:
                    deck_choice.Append(deck_name)

            if current_selection:
                idx = deck_choice.FindString(current_selection)
                if idx != wx.NOT_FOUND:
                    deck_choice.SetSelection(idx)

        def on_spread_change(event):
            dlg._spread_cards = {}
            spread_canvas.Refresh()

            spread_name = spread_choice.GetStringSelection()
            allowed_types = None

            if spread_name and spread_name in self._spread_map:
                spread = self.db.get_spread(self._spread_map[spread_name])
                if spread:
                    allowed_types_json = spread['allowed_deck_types'] if 'allowed_deck_types' in spread.keys() else None
                    if allowed_types_json:
                        allowed_types = json.loads(allowed_types_json)

                    update_deck_choices(allowed_types)

                    if allowed_types:
                        default_deck_id = self.db.get_default_deck(allowed_types[0])
                        if default_deck_id:
                            for name, info in dlg._all_decks.items():
                                if info['id'] == default_deck_id:
                                    idx = deck_choice.FindString(name)
                                    if idx != wx.NOT_FOUND:
                                        deck_choice.SetSelection(idx)
                                        dlg._selected_deck_id = default_deck_id
                                    break
                    elif 'cartomancy_type' in spread.keys() and spread['cartomancy_type']:
                        default_deck_id = self.db.get_default_deck(spread['cartomancy_type'])
                        if default_deck_id:
                            for name, info in dlg._all_decks.items():
                                if info['id'] == default_deck_id:
                                    idx = deck_choice.FindString(name)
                                    if idx != wx.NOT_FOUND:
                                        deck_choice.SetSelection(idx)
                                        dlg._selected_deck_id = default_deck_id
                                    break
                    else:
                        update_deck_choices(None)

            dlg._spread_allowed_types = allowed_types

        spread_choice.Bind(wx.EVT_CHOICE, on_spread_change)

        def on_use_any_deck_change(event):
            spread_name = spread_choice.GetStringSelection()
            if spread_name and spread_name in self._spread_map:
                spread = self.db.get_spread(self._spread_map[spread_name])
                if spread:
                    allowed_types_json = spread['allowed_deck_types'] if 'allowed_deck_types' in spread.keys() else None
                    if allowed_types_json:
                        allowed_types = json.loads(allowed_types_json)
                        update_deck_choices(allowed_types)
                    else:
                        update_deck_choices(None)
            else:
                update_deck_choices(None)

        use_any_deck_cb.Bind(wx.EVT_CHECKBOX, on_use_any_deck_change)

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
            if not positions:
                return

            # Calculate centering offset
            min_x = min(p.get('x', 0) for p in positions)
            min_y = min(p.get('y', 0) for p in positions)
            max_x = max(p.get('x', 0) + p.get('width', 80) for p in positions)
            max_y = max(p.get('y', 0) + p.get('height', 120) for p in positions)
            spread_width = max_x - min_x
            spread_height = max_y - min_y
            canvas_w, canvas_h = spread_canvas.GetSize()
            offset_x = (canvas_w - spread_width) // 2 - min_x
            offset_y = (canvas_h - spread_height) // 2 - min_y

            dc.SetPen(wx.Pen(get_wx_color('border'), 1))
            dc.SetBrush(wx.Brush(get_wx_color('bg_tertiary')))
            dc.SetTextForeground(get_wx_color('text_dim'))

            for i, pos in enumerate(positions):
                x, y = pos.get('x', 0) + offset_x, pos.get('y', 0) + offset_y
                w, h = pos.get('width', 80), pos.get('height', 120)
                label = pos.get('label', f'Position {i+1}')

                if i in dlg._spread_cards:
                    dc.SetBrush(wx.Brush(get_wx_color('accent_dim')))
                    dc.DrawRectangle(x, y, w, h)
                    dc.SetTextForeground(get_wx_color('text_primary'))
                    dc.DrawText(dlg._spread_cards[i]['name'][:12], x + 5, y + h//2 - 8)
                    dc.SetTextForeground(get_wx_color('text_dim'))
                else:
                    dc.SetBrush(wx.Brush(get_wx_color('bg_tertiary')))
                    dc.DrawRectangle(x, y, w, h)
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
            if not positions:
                return

            # Calculate offset
            min_x = min(p.get('x', 0) for p in positions)
            min_y = min(p.get('y', 0) for p in positions)
            max_x = max(p.get('x', 0) + p.get('width', 80) for p in positions)
            max_y = max(p.get('y', 0) + p.get('height', 120) for p in positions)
            spread_width = max_x - min_x
            spread_height = max_y - min_y
            canvas_w, canvas_h = spread_canvas.GetSize()
            offset_x = (canvas_w - spread_width) // 2 - min_x
            offset_y = (canvas_h - spread_height) // 2 - min_y

            click_x, click_y = event.GetX(), event.GetY()

            for i, pos in enumerate(positions):
                px, py = pos.get('x', 0) + offset_x, pos.get('y', 0) + offset_y
                pw, ph = pos.get('width', 80), pos.get('height', 120)

                if px <= click_x <= px + pw and py <= click_y <= py + ph:
                    # Card picker with deck selection
                    card_dlg = wx.Dialog(dlg, title=f"Select Card for: {pos.get('label', f'Position {i+1}')}",
                                        size=(450, 550))
                    card_dlg.SetBackgroundColour(get_wx_color('bg_primary'))
                    card_dlg_sizer = wx.BoxSizer(wx.VERTICAL)

                    deck_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    deck_select_label = wx.StaticText(card_dlg, label="Deck:")
                    deck_select_label.SetForegroundColour(get_wx_color('text_primary'))
                    deck_select_sizer.Add(deck_select_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

                    # Build filtered deck list based on spread's allowed types
                    allowed_types = getattr(dlg, '_spread_allowed_types', None)
                    use_any = use_any_deck_cb.GetValue()
                    picker_deck_names = []
                    for deck_name, deck_info in dlg._all_decks.items():
                        if not allowed_types or use_any:
                            picker_deck_names.append(deck_name)
                        elif deck_info['cartomancy_type'] in allowed_types:
                            picker_deck_names.append(deck_name)

                    picker_deck_choice = wx.Choice(card_dlg, choices=picker_deck_names)
                    if dlg._selected_deck_id:
                        for name, info in dlg._all_decks.items():
                            if info['id'] == dlg._selected_deck_id:
                                idx = picker_deck_choice.FindString(name)
                                if idx != wx.NOT_FOUND:
                                    picker_deck_choice.SetSelection(idx)
                                break
                    deck_select_sizer.Add(picker_deck_choice, 1, wx.EXPAND)
                    card_dlg_sizer.Add(deck_select_sizer, 0, wx.EXPAND | wx.ALL, 10)

                    # Use any deck checkbox in card picker (empty label + StaticText for macOS)
                    picker_use_any_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    picker_use_any_cb = wx.CheckBox(card_dlg, label="")
                    picker_use_any_cb.SetValue(use_any)
                    picker_use_any_sizer.Add(picker_use_any_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
                    picker_use_any_label = wx.StaticText(card_dlg, label="Use Any Deck (override restriction)")
                    picker_use_any_label.SetForegroundColour(get_wx_color('text_dim'))
                    picker_use_any_sizer.Add(picker_use_any_label, 0, wx.ALIGN_CENTER_VERTICAL)
                    card_dlg_sizer.Add(picker_use_any_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

                    # Card list with thumbnails
                    thumb_size = 48
                    card_listctrl = wx.ListCtrl(card_dlg, style=wx.LC_LIST | wx.LC_SINGLE_SEL)
                    card_listctrl.SetBackgroundColour(get_wx_color('bg_input'))
                    card_listctrl.SetForegroundColour(get_wx_color('text_primary'))
                    card_dlg_sizer.Add(card_listctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

                    # Store card data and image list (must keep reference to prevent GC)
                    card_dlg._card_data = []
                    card_dlg._image_list = wx.ImageList(thumb_size, thumb_size)
                    card_listctrl.SetImageList(card_dlg._image_list, wx.IMAGE_LIST_SMALL)

                    current_picker_deck_id = dlg._selected_deck_id

                    def populate_cards(deck_id):
                        card_listctrl.DeleteAllItems()
                        card_dlg._card_data = []
                        # Clear and recreate image list
                        card_dlg._image_list.RemoveAll()

                        if deck_id:
                            cards = self.db.get_cards(deck_id)
                            for card in cards:
                                card_dlg._card_data.append(card)
                                # Get thumbnail
                                img_idx = -1
                                if card['image_path']:
                                    thumb_path = self.thumb_cache.get_thumbnail_path(card['image_path'])
                                    if thumb_path:
                                        try:
                                            img = wx.Image(thumb_path, wx.BITMAP_TYPE_ANY)
                                            if img.IsOk():
                                                # Scale to fit the thumbnail size
                                                w, h = img.GetWidth(), img.GetHeight()
                                                if w > 0 and h > 0:
                                                    scale = min(thumb_size / w, thumb_size / h)
                                                    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
                                                    img = img.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
                                                    # Resize canvas to exact thumb_size with dark background
                                                    img.Resize((thumb_size, thumb_size),
                                                              ((thumb_size - new_w) // 2, (thumb_size - new_h) // 2),
                                                              40, 40, 40)
                                                    img_idx = card_dlg._image_list.Add(wx.Bitmap(img))
                                        except Exception:
                                            pass
                                idx = card_listctrl.InsertItem(card_listctrl.GetItemCount(), card['name'], img_idx)
                                card_listctrl.SetItemData(idx, len(card_dlg._card_data) - 1)

                    populate_cards(current_picker_deck_id)

                    def on_picker_deck_change(e):
                        nonlocal current_picker_deck_id
                        name = picker_deck_choice.GetStringSelection()
                        if name in dlg._all_decks:
                            current_picker_deck_id = dlg._all_decks[name]['id']
                            populate_cards(current_picker_deck_id)

                    picker_deck_choice.Bind(wx.EVT_CHOICE, on_picker_deck_change)

                    def on_picker_use_any_change(e):
                        nonlocal current_picker_deck_id
                        current_selection = picker_deck_choice.GetStringSelection()
                        picker_deck_choice.Clear()

                        picker_use_any = picker_use_any_cb.GetValue()
                        for deck_name, deck_info in dlg._all_decks.items():
                            if not allowed_types or picker_use_any:
                                picker_deck_choice.Append(deck_name)
                            elif deck_info['cartomancy_type'] in allowed_types:
                                picker_deck_choice.Append(deck_name)

                        if current_selection:
                            idx = picker_deck_choice.FindString(current_selection)
                            if idx != wx.NOT_FOUND:
                                picker_deck_choice.SetSelection(idx)
                            elif picker_deck_choice.GetCount() > 0:
                                picker_deck_choice.SetSelection(0)
                                name = picker_deck_choice.GetStringSelection()
                                if name in dlg._all_decks:
                                    current_picker_deck_id = dlg._all_decks[name]['id']
                                    populate_cards(current_picker_deck_id)

                    picker_use_any_cb.Bind(wx.EVT_CHECKBOX, on_picker_use_any_change)

                    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    cancel_btn = wx.Button(card_dlg, wx.ID_CANCEL, "Cancel")
                    select_btn = wx.Button(card_dlg, wx.ID_OK, "Select")
                    btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
                    btn_sizer.Add(select_btn, 0)
                    card_dlg_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

                    card_dlg.SetSizer(card_dlg_sizer)

                    if card_dlg.ShowModal() == wx.ID_OK:
                        sel_idx = card_listctrl.GetFirstSelected()
                        if sel_idx != -1:
                            data_idx = card_listctrl.GetItemData(sel_idx)
                            card = card_dlg._card_data[data_idx]
                            deck_name_full = picker_deck_choice.GetStringSelection()
                            deck_name_clean = deck_name_full.split(' (')[0] if deck_name_full else None

                            dlg._spread_cards[i] = {
                                'id': card['id'],
                                'name': card['name'],
                                'image_path': card['image_path'],
                                'reversed': False,
                                'deck_id': current_picker_deck_id,
                                'deck_name': deck_name_clean
                            }

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
        save_btn = wx.Button(dlg, wx.ID_OK, "Add Reading")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)

        dlg.SetSizer(sizer)

        if dlg.ShowModal() == wx.ID_OK:
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

                cards_used = [
                    {
                        'name': c['name'],
                        'reversed': c.get('reversed', False),
                        'deck_id': c.get('deck_id'),
                        'deck_name': c.get('deck_name')
                    }
                    for c in dlg._spread_cards.values()
                ]
                deck_name_clean = deck_name.split(' (')[0] if deck_name else None

                # Get next position_order
                existing_readings = self.db.get_entry_readings(entry_id)
                next_order = len(existing_readings)

                self.db.add_entry_reading(
                    entry_id=entry_id,
                    spread_id=spread_id,
                    spread_name=spread_name,
                    deck_id=deck_id,
                    deck_name=deck_name_clean,
                    cartomancy_type=cartomancy_type,
                    cards_used=cards_used,
                    position_order=next_order
                )

                self._display_entry_in_viewer(entry_id)

        dlg.Destroy()

    def _on_export_entries(self, event):
        """Show export dialog for journal entries"""
        # Get all selected entry IDs
        selected_entry_ids = []
        idx = self.entry_list.GetFirstSelected()
        while idx != -1:
            selected_entry_ids.append(self.entry_list.GetItemData(idx))
            idx = self.entry_list.GetNextSelected(idx)

        # Create dialog to choose export options
        dlg = wx.Dialog(self, title="Export Entries", size=(400, 250))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Export scope
        scope_label = wx.StaticText(dlg, label="What to export:")
        scope_label.SetForegroundColour(get_wx_color('text_primary'))
        sizer.Add(scope_label, 0, wx.ALL, 10)

        # Radio buttons with separate labels (for proper text color on macOS)
        all_sizer = wx.BoxSizer(wx.HORIZONTAL)
        export_all_radio = wx.RadioButton(dlg, label="", style=wx.RB_GROUP)
        all_sizer.Add(export_all_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        all_label = wx.StaticText(dlg, label="All entries")
        all_label.SetForegroundColour(get_wx_color('text_primary'))
        all_sizer.Add(all_label, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(all_sizer, 0, wx.LEFT, 20)

        selected_sizer = wx.BoxSizer(wx.HORIZONTAL)
        export_selected_radio = wx.RadioButton(dlg, label="")
        selected_sizer.Add(export_selected_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        # Update label based on selection count
        selection_count = len(selected_entry_ids)
        if selection_count == 1:
            selected_text = "Selected entry (1)"
        else:
            selected_text = f"Selected entries ({selection_count})"
        selected_label = wx.StaticText(dlg, label=selected_text)
        selected_label.SetForegroundColour(get_wx_color('text_primary'))
        selected_sizer.Add(selected_label, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(selected_sizer, 0, wx.LEFT | wx.TOP, 20)

        # Disable selected option if no entries selected
        if selection_count == 0:
            export_selected_radio.Enable(False)
            selected_label.SetForegroundColour(get_wx_color('text_dim'))

        sizer.AddSpacer(15)

        # Format selection
        format_label = wx.StaticText(dlg, label="Export format:")
        format_label.SetForegroundColour(get_wx_color('text_primary'))
        sizer.Add(format_label, 0, wx.LEFT, 10)

        json_sizer = wx.BoxSizer(wx.HORIZONTAL)
        json_radio = wx.RadioButton(dlg, label="", style=wx.RB_GROUP)
        json_sizer.Add(json_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        json_label = wx.StaticText(dlg, label="JSON (data only)")
        json_label.SetForegroundColour(get_wx_color('text_primary'))
        json_sizer.Add(json_label, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(json_sizer, 0, wx.LEFT | wx.TOP, 20)

        zip_sizer = wx.BoxSizer(wx.HORIZONTAL)
        zip_radio = wx.RadioButton(dlg, label="")
        zip_sizer.Add(zip_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        zip_label = wx.StaticText(dlg, label="ZIP (data + card images)")
        zip_label.SetForegroundColour(get_wx_color('text_primary'))
        zip_sizer.Add(zip_label, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(zip_sizer, 0, wx.LEFT | wx.TOP, 20)

        sizer.AddStretchSpacer()

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        export_btn = wx.Button(dlg, wx.ID_OK, "Export")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(export_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        dlg.SetSizer(sizer)

        if dlg.ShowModal() == wx.ID_OK:
            # Get selected options
            export_all = export_all_radio.GetValue()
            use_zip = zip_radio.GetValue()

            entry_ids = None if export_all else selected_entry_ids

            # Choose file extension
            if use_zip:
                wildcard = "ZIP files (*.zip)|*.zip"
                default_ext = ".zip"
            else:
                wildcard = "JSON files (*.json)|*.json"
                default_ext = ".json"

            # Show file save dialog
            file_dlg = wx.FileDialog(
                self, "Save Export",
                wildcard=wildcard,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            )
            file_dlg.SetFilename(f"tarot_journal_export{default_ext}")

            if file_dlg.ShowModal() == wx.ID_OK:
                filepath = file_dlg.GetPath()

                try:
                    if use_zip:
                        self.db.export_entries_to_zip(filepath, entry_ids)
                    else:
                        self.db.export_entries_to_file(filepath, entry_ids)

                    wx.MessageBox(
                        f"Export complete!\n\nSaved to: {filepath}",
                        "Export Successful",
                        wx.OK | wx.ICON_INFORMATION
                    )
                except Exception as e:
                    wx.MessageBox(
                        f"Export failed:\n{str(e)}",
                        "Export Error",
                        wx.OK | wx.ICON_ERROR
                    )

            file_dlg.Destroy()

        dlg.Destroy()

    def _on_import_entries(self, event):
        """Show import dialog for journal entries"""
        wildcard = "Journal exports (*.json;*.zip)|*.json;*.zip|JSON files (*.json)|*.json|ZIP files (*.zip)|*.zip"

        file_dlg = wx.FileDialog(
            self, "Import Entries",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if file_dlg.ShowModal() == wx.ID_OK:
            filepath = file_dlg.GetPath()

            try:
                if filepath.lower().endswith('.zip'):
                    result = self.db.import_entries_from_zip(filepath)
                else:
                    result = self.db.import_entries_from_file(filepath)

                wx.MessageBox(
                    f"Import complete!\n\n"
                    f"Entries imported: {result['imported']}\n"
                    f"New tags created: {result['tags_created']}",
                    "Import Successful",
                    wx.OK | wx.ICON_INFORMATION
                )

                self._refresh_entries_list()
                self._refresh_tags_list()

            except Exception as e:
                wx.MessageBox(
                    f"Import failed:\n{str(e)}",
                    "Import Error",
                    wx.OK | wx.ICON_ERROR
                )

        file_dlg.Destroy()


    # ═══════════════════════════════════════════
    # EVENT HANDLERS - Library
    # ═══════════════════════════════════════════
    def _on_type_filter(self, event):
        self._refresh_decks_list()
    
    def _on_deck_select(self, event):
        idx = event.GetIndex()
        deck_id = self.deck_list.GetItemData(idx)
        self._selected_deck_id = deck_id
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
        """Edit deck name, suit names, and custom fields"""
        # Get deck_id based on current view mode
        deck_id = None
        if self._deck_view_mode == 'image':
            # In image view, use _selected_deck_id
            deck_id = self._selected_deck_id
        else:
            # In list view, use list selection
            idx = self.deck_list.GetFirstSelected()
            if idx != -1:
                deck_id = self.deck_list.GetItemData(idx)

        if not deck_id:
            wx.MessageBox("Select a deck to edit.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return
        deck = self.db.get_deck(deck_id)
        if not deck:
            return

        suit_names = self.db.get_deck_suit_names(deck_id)
        custom_fields = [dict(row) for row in self.db.get_deck_custom_fields(deck_id)]

        dlg = wx.Dialog(self, title="Edit Deck", size=(650, 520), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Create notebook for tabs using FlatNotebook for better color control
        style = (fnb.FNB_NO_X_BUTTON | fnb.FNB_NO_NAV_BUTTONS | fnb.FNB_NODRAG)
        notebook = fnb.FlatNotebook(dlg, agwStyle=style)
        notebook.SetBackgroundColour(get_wx_color('bg_primary'))
        notebook.SetTabAreaColour(get_wx_color('bg_primary'))
        notebook.SetActiveTabColour(get_wx_color('bg_tertiary'))
        notebook.SetNonActiveTabTextColour(get_wx_color('text_primary'))
        notebook.SetActiveTabTextColour(get_wx_color('text_primary'))
        notebook.SetGradientColourTo(get_wx_color('bg_tertiary'))
        notebook.SetGradientColourFrom(get_wx_color('bg_secondary'))

        # === General Tab ===
        general_panel = wx.Panel(notebook)
        general_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        general_sizer = wx.BoxSizer(wx.VERTICAL)

        # Deck name
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(general_panel, label="Deck Name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        name_ctrl = wx.TextCtrl(general_panel, value=deck['name'])
        name_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        name_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_ctrl, 1)
        general_sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 15)

        # Suit names section - use appropriate suits based on deck type
        deck_type = deck['cartomancy_type_name']
        if deck_type in ('Lenormand', 'Playing Cards'):
            suits = [('hearts', 'Hearts'), ('diamonds', 'Diamonds'),
                     ('clubs', 'Clubs'), ('spades', 'Spades')]
            suit_box_label = "Suit Names (for Playing Card decks)"
        else:  # Tarot or Oracle
            suits = [('wands', 'Wands'), ('cups', 'Cups'),
                     ('swords', 'Swords'), ('pentacles', 'Pentacles')]
            suit_box_label = "Suit Names (for Tarot decks)"

        suit_box = wx.StaticBox(general_panel, label=suit_box_label)
        suit_box.SetForegroundColour(get_wx_color('accent'))
        suit_sizer = wx.StaticBoxSizer(suit_box, wx.VERTICAL)

        suit_note = wx.StaticText(general_panel, label="Changing suit names will update all card names in this deck.")
        suit_note.SetForegroundColour(get_wx_color('text_dim'))
        suit_sizer.Add(suit_note, 0, wx.ALL, 10)

        suit_ctrls = {}
        for suit_key, default_name in suits:
            row = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(general_panel, label=f"{default_name}:", size=(80, -1))
            label.SetForegroundColour(get_wx_color('text_primary'))
            row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

            ctrl = wx.TextCtrl(general_panel, value=suit_names.get(suit_key, default_name))
            ctrl.SetBackgroundColour(get_wx_color('bg_input'))
            ctrl.SetForegroundColour(get_wx_color('text_primary'))
            suit_ctrls[suit_key] = ctrl
            row.Add(ctrl, 1)

            suit_sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        general_sizer.Add(suit_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

        # Auto-assign metadata button (for Tarot, Lenormand, Kipper, Playing Cards, Oracle)
        if deck_type in ('Tarot', 'Lenormand', 'Kipper', 'Playing Cards', 'Oracle'):
            auto_meta_sizer = wx.BoxSizer(wx.HORIZONTAL)
            auto_meta_btn = wx.Button(general_panel, label="Auto-assign Card Metadata")

            def on_auto_assign(e):
                # For Tarot decks, show preset selection for ordering
                preset_name = None
                if deck_type == 'Tarot':
                    # Build list of Tarot presets
                    tarot_presets = []
                    for name in self.presets.get_preset_names():
                        preset = self.presets.get_preset(name)
                        if preset and preset.get('type') == 'Tarot':
                            tarot_presets.append(name)

                    if tarot_presets:
                        # Show preset selection dialog
                        preset_dlg = wx.SingleChoiceDialog(
                            dlg,
                            "Select the ordering for this deck.\n"
                            "This affects the numbering of Strength/Justice:\n\n"
                            "• RWS Ordering: Strength=VIII, Justice=XI\n"
                            "• Thoth/Pre-Golden Dawn: Strength=XI, Justice=VIII",
                            "Select Deck Ordering",
                            tarot_presets
                        )
                        if preset_dlg.ShowModal() == wx.ID_OK:
                            preset_name = preset_dlg.GetStringSelection()
                        else:
                            preset_dlg.Destroy()
                            return
                        preset_dlg.Destroy()
                elif deck_type == 'Lenormand':
                    # Use Lenormand preset
                    preset_name = "Lenormand (36 cards)"
                elif deck_type == 'Kipper':
                    # Use Kipper preset
                    preset_name = "Kipper (36 cards)"
                elif deck_type == 'Playing Cards':
                    # Use Playing Cards preset
                    preset_name = "Playing Cards with Jokers (54 cards)"
                elif deck_type == 'Oracle':
                    # Use Oracle preset
                    preset_name = "Oracle (filename only)"

                # Create a dialog with overwrite option
                overwrite_dlg = wx.Dialog(dlg, title="Auto-assign Metadata", size=(400, 200))
                overwrite_dlg.SetBackgroundColour(get_wx_color('bg_primary'))
                dlg_sizer = wx.BoxSizer(wx.VERTICAL)

                msg = wx.StaticText(overwrite_dlg,
                    label="This will automatically assign archetype, rank, and suit\n"
                          "to cards based on their names.")
                msg.SetForegroundColour(get_wx_color('text_primary'))
                dlg_sizer.Add(msg, 0, wx.ALL, 15)

                # Use separate checkbox and label because wx.CheckBox doesn't respect
                # SetForegroundColour on macOS
                overwrite_sizer = wx.BoxSizer(wx.HORIZONTAL)
                overwrite_cb = wx.CheckBox(overwrite_dlg, label="")
                overwrite_sizer.Add(overwrite_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
                overwrite_label = wx.StaticText(overwrite_dlg, label="Overwrite existing metadata")
                overwrite_label.SetForegroundColour(get_wx_color('text_primary'))
                overwrite_sizer.Add(overwrite_label, 0, wx.ALIGN_CENTER_VERTICAL)
                dlg_sizer.Add(overwrite_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

                btn_sizer = wx.StdDialogButtonSizer()
                ok_btn = wx.Button(overwrite_dlg, wx.ID_OK, "Continue")
                ok_btn.SetForegroundColour(get_wx_color('text_primary'))
                ok_btn.SetBackgroundColour(get_wx_color('bg_secondary'))
                cancel_btn = wx.Button(overwrite_dlg, wx.ID_CANCEL, "Cancel")
                cancel_btn.SetForegroundColour(get_wx_color('text_primary'))
                cancel_btn.SetBackgroundColour(get_wx_color('bg_secondary'))
                btn_sizer.AddButton(ok_btn)
                btn_sizer.AddButton(cancel_btn)
                btn_sizer.Realize()
                dlg_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)

                overwrite_dlg.SetSizer(dlg_sizer)
                overwrite_dlg.Fit()
                overwrite_dlg.CenterOnParent()

                if overwrite_dlg.ShowModal() == wx.ID_OK:
                    overwrite = overwrite_cb.GetValue()
                    overwrite_dlg.Destroy()
                    updated = self.db.auto_assign_deck_metadata(deck_id, overwrite=overwrite,
                                                                 preset_name=preset_name)
                    # Refresh the cards display to update selection state
                    self._refresh_cards_display(deck_id, preserve_scroll=True)
                    wx.MessageBox(
                        f"Updated metadata for {updated} cards.",
                        "Complete",
                        wx.OK | wx.ICON_INFORMATION
                    )
                else:
                    overwrite_dlg.Destroy()

            auto_meta_btn.Bind(wx.EVT_BUTTON, on_auto_assign)
            auto_meta_sizer.Add(auto_meta_btn, 0)

            auto_meta_note = wx.StaticText(general_panel,
                label="  (Parses card names to fill in archetype/rank/suit)")
            auto_meta_note.SetForegroundColour(get_wx_color('text_dim'))
            auto_meta_sizer.Add(auto_meta_note, 0, wx.ALIGN_CENTER_VERTICAL)

            general_sizer.Add(auto_meta_sizer, 0, wx.ALL, 15)

        general_panel.SetSizer(general_sizer)
        notebook.AddPage(general_panel, "General")

        # === Details Tab ===
        details_panel = wx.Panel(notebook)
        details_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        details_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Left side: Card Back Image
        card_back_panel = wx.Panel(details_panel)
        card_back_panel.SetBackgroundColour(get_wx_color('bg_secondary'))
        card_back_sizer = wx.BoxSizer(wx.VERTICAL)

        card_back_label = wx.StaticText(card_back_panel, label="Card Back")
        card_back_label.SetForegroundColour(get_wx_color('text_primary'))
        card_back_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        card_back_sizer.Add(card_back_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)

        # Image preview (150x225 - half the size of card preview)
        max_back_width, max_back_height = 150, 225
        card_back_path = deck['card_back_image'] if 'card_back_image' in deck.keys() else None

        def load_card_back_image(path):
            """Load and scale card back image"""
            if path and os.path.exists(path):
                try:
                    from PIL import ImageOps
                    pil_img = Image.open(path)
                    pil_img = ImageOps.exif_transpose(pil_img)
                    orig_width, orig_height = pil_img.size
                    scale = min(max_back_width / orig_width, max_back_height / orig_height)
                    new_width = int(orig_width * scale)
                    new_height = int(orig_height * scale)
                    pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    if pil_img.mode != 'RGB':
                        pil_img = pil_img.convert('RGB')
                    wx_img = wx.Image(new_width, new_height)
                    wx_img.SetData(pil_img.tobytes())
                    return wx.Bitmap(wx_img)
                except:
                    pass
            return None

        card_back_bitmap = load_card_back_image(card_back_path)
        if card_back_bitmap:
            card_back_display = wx.StaticBitmap(card_back_panel, bitmap=card_back_bitmap)
        else:
            card_back_display = wx.StaticText(card_back_panel, label="🂠")
            card_back_display.SetFont(wx.Font(48, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            card_back_display.SetForegroundColour(get_wx_color('text_dim'))

        card_back_sizer.Add(card_back_display, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        # Store the current path
        dlg._card_back_path = card_back_path

        def on_select_card_back(e):
            with wx.FileDialog(dlg, "Select Card Back Image",
                              wildcard="Image files (*.png;*.jpg;*.jpeg;*.gif;*.bmp)|*.png;*.jpg;*.jpeg;*.gif;*.bmp",
                              style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as file_dlg:
                if file_dlg.ShowModal() == wx.ID_OK:
                    new_path = file_dlg.GetPath()
                    dlg._card_back_path = new_path
                    # Update preview
                    nonlocal card_back_display
                    new_bitmap = load_card_back_image(new_path)
                    if new_bitmap:
                        if isinstance(card_back_display, wx.StaticText):
                            card_back_display.Destroy()
                            card_back_display = wx.StaticBitmap(card_back_panel, bitmap=new_bitmap)
                            card_back_sizer.Insert(1, card_back_display, 0, wx.ALL | wx.ALIGN_CENTER, 10)
                        else:
                            card_back_display.SetBitmap(new_bitmap)
                        card_back_panel.Layout()

        def on_clear_card_back(e):
            nonlocal card_back_display
            dlg._card_back_path = ""  # Empty string to clear
            if isinstance(card_back_display, wx.StaticBitmap):
                card_back_display.Destroy()
                card_back_display = wx.StaticText(card_back_panel, label="🂠")
                card_back_display.SetFont(wx.Font(48, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                card_back_display.SetForegroundColour(get_wx_color('text_dim'))
                card_back_sizer.Insert(1, card_back_display, 0, wx.ALL | wx.ALIGN_CENTER, 10)
                card_back_panel.Layout()

        # Buttons for card back
        card_back_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_back_btn = wx.Button(card_back_panel, label="Select...")
        select_back_btn.Bind(wx.EVT_BUTTON, on_select_card_back)
        card_back_btn_sizer.Add(select_back_btn, 0, wx.RIGHT, 5)

        clear_back_btn = wx.Button(card_back_panel, label="Clear")
        clear_back_btn.Bind(wx.EVT_BUTTON, on_clear_card_back)
        card_back_btn_sizer.Add(clear_back_btn, 0)

        card_back_sizer.Add(card_back_btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        card_back_panel.SetSizer(card_back_sizer)
        details_sizer.Add(card_back_panel, 0, wx.ALL, 10)

        # Right side: Other details (in a scrolled panel)
        details_fields_scroll = scrolled.ScrolledPanel(details_panel)
        details_fields_scroll.SetBackgroundColour(get_wx_color('bg_primary'))
        details_fields_scroll.SetupScrolling(scroll_x=False)
        details_fields_sizer = wx.BoxSizer(wx.VERTICAL)

        # Date Published
        date_sizer = wx.BoxSizer(wx.HORIZONTAL)
        date_label = wx.StaticText(details_fields_scroll, label="Date Published:")
        date_label.SetForegroundColour(get_wx_color('text_primary'))
        date_sizer.Add(date_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        date_ctrl = wx.TextCtrl(details_fields_scroll, value=deck['date_published'] or '' if 'date_published' in deck.keys() else '')
        date_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        date_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        date_sizer.Add(date_ctrl, 1)
        details_fields_sizer.Add(date_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Publisher
        pub_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pub_label = wx.StaticText(details_fields_scroll, label="Publisher:")
        pub_label.SetForegroundColour(get_wx_color('text_primary'))
        pub_sizer.Add(pub_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        pub_ctrl = wx.TextCtrl(details_fields_scroll, value=deck['publisher'] or '' if 'publisher' in deck.keys() else '')
        pub_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        pub_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        pub_sizer.Add(pub_ctrl, 1)
        details_fields_sizer.Add(pub_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Credits
        credits_label = wx.StaticText(details_fields_scroll, label="Credits:")
        credits_label.SetForegroundColour(get_wx_color('text_primary'))
        details_fields_sizer.Add(credits_label, 0, wx.LEFT | wx.RIGHT, 10)
        credits_ctrl = RichTextPanel(details_fields_scroll,
                                     value=deck['credits'] or '' if 'credits' in deck.keys() else '',
                                     min_height=100)
        details_fields_sizer.Add(credits_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Notes
        notes_label = wx.StaticText(details_fields_scroll, label="Notes:")
        notes_label.SetForegroundColour(get_wx_color('text_primary'))
        details_fields_sizer.Add(notes_label, 0, wx.LEFT | wx.RIGHT, 10)
        deck_notes_ctrl = RichTextPanel(details_fields_scroll,
                                        value=deck['notes'] or '' if 'notes' in deck.keys() else '',
                                        min_height=100)
        details_fields_sizer.Add(deck_notes_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Booklet Info
        booklet_label = wx.StaticText(details_fields_scroll, label="Booklet Info:")
        booklet_label.SetForegroundColour(get_wx_color('text_primary'))
        details_fields_sizer.Add(booklet_label, 0, wx.LEFT | wx.RIGHT, 10)
        booklet_ctrl = RichTextPanel(details_fields_scroll,
                                     value=deck['booklet_info'] or '' if 'booklet_info' in deck.keys() else '',
                                     min_height=100)
        details_fields_sizer.Add(booklet_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        details_fields_scroll.SetSizer(details_fields_sizer)
        details_sizer.Add(details_fields_scroll, 1, wx.EXPAND | wx.ALL, 5)

        details_panel.SetSizer(details_sizer)
        notebook.AddPage(details_panel, "Details")

        # === Tags Tab ===
        tags_panel = wx.Panel(notebook)
        tags_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        tags_sizer = wx.BoxSizer(wx.VERTICAL)

        tags_info = wx.StaticText(tags_panel,
            label="Assign tags to this deck. Cards in this deck will inherit these tags.")
        tags_info.SetForegroundColour(get_wx_color('text_secondary'))
        tags_sizer.Add(tags_info, 0, wx.ALL, 10)

        # Get current deck tags and all available deck tags
        current_deck_tags = {t['id'] for t in self.db.get_tags_for_deck(deck_id)}
        all_deck_tags = list(self.db.get_deck_tags())

        # CheckListBox for tag selection
        tag_choices = [tag['name'] for tag in all_deck_tags]
        deck_tag_checklist = wx.CheckListBox(tags_panel, choices=tag_choices)
        deck_tag_checklist.SetBackgroundColour(get_wx_color('bg_secondary'))
        deck_tag_checklist.SetForegroundColour(get_wx_color('text_primary'))

        # Check the tags that are already assigned
        for i, tag in enumerate(all_deck_tags):
            if tag['id'] in current_deck_tags:
                deck_tag_checklist.Check(i, True)

        tags_sizer.Add(deck_tag_checklist, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Button to add new tag
        def on_add_new_deck_tag(e):
            result = self._show_tag_dialog(dlg, "Add Deck Tag")
            if result:
                try:
                    new_id = self.db.add_deck_tag(result['name'], result['color'])
                    # Refresh the checklist
                    all_deck_tags.append({'id': new_id, 'name': result['name'], 'color': result['color']})
                    deck_tag_checklist.Append(result['name'])
                    deck_tag_checklist.Check(deck_tag_checklist.GetCount() - 1, True)
                    # Also refresh the main tags list if visible
                    self._refresh_deck_tags_list()
                except Exception as ex:
                    wx.MessageBox(f"Could not add tag: {ex}", "Error", wx.OK | wx.ICON_ERROR)

        add_tag_btn = wx.Button(tags_panel, label="+ New Tag")
        add_tag_btn.Bind(wx.EVT_BUTTON, on_add_new_deck_tag)
        tags_sizer.Add(add_tag_btn, 0, wx.ALL, 10)

        tags_panel.SetSizer(tags_sizer)
        notebook.AddPage(tags_panel, "Tags")

        # === Custom Fields Tab ===
        cf_panel = wx.Panel(notebook)
        cf_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        cf_sizer = wx.BoxSizer(wx.VERTICAL)

        cf_info = wx.StaticText(cf_panel,
            label="Define custom fields that apply to all cards in this deck.\nThese fields appear in the card edit dialog.")
        cf_info.SetForegroundColour(get_wx_color('text_secondary'))
        cf_sizer.Add(cf_info, 0, wx.ALL, 10)

        # List control for custom fields
        cf_list = wx.ListCtrl(cf_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        cf_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        cf_list.SetForegroundColour(get_wx_color('text_primary'))
        cf_list.InsertColumn(0, "Field Name", width=150)
        cf_list.InsertColumn(1, "Type", width=100)
        cf_list.InsertColumn(2, "Options", width=150)

        # Populate list
        def refresh_cf_list():
            cf_list.DeleteAllItems()
            for i, field in enumerate(custom_fields):
                idx = cf_list.InsertItem(i, field['field_name'])
                cf_list.SetItem(idx, 1, field['field_type'])
                options_str = ''
                if field['field_options']:
                    try:
                        opts = json.loads(field['field_options'])
                        options_str = ', '.join(opts[:3])
                        if len(opts) > 3:
                            options_str += '...'
                    except:
                        pass
                cf_list.SetItem(idx, 2, options_str)
                cf_list.SetItemData(idx, field['id'])

        refresh_cf_list()
        cf_sizer.Add(cf_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Buttons for custom fields
        cf_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        def on_add_field(e):
            field_data = self._show_custom_field_dialog(dlg)
            if field_data:
                new_id = self.db.add_deck_custom_field(
                    deck_id,
                    field_data['name'],
                    field_data['type'],
                    field_data.get('options'),
                    len(custom_fields)
                )
                custom_fields.append({
                    'id': new_id,
                    'deck_id': deck_id,
                    'field_name': field_data['name'],
                    'field_type': field_data['type'],
                    'field_options': json.dumps(field_data.get('options')) if field_data.get('options') else None,
                    'field_order': len(custom_fields)
                })
                refresh_cf_list()

        def on_edit_field(e):
            sel = cf_list.GetFirstSelected()
            if sel == -1:
                return
            field_id = cf_list.GetItemData(sel)
            field = None
            field_idx = None
            for i, f in enumerate(custom_fields):
                if f['id'] == field_id:
                    field = f
                    field_idx = i
                    break
            if not field:
                return

            # Parse existing options
            existing_options = None
            if field['field_options']:
                try:
                    existing_options = json.loads(field['field_options'])
                except:
                    pass

            field_data = self._show_custom_field_dialog(
                dlg,
                name=field['field_name'],
                field_type=field['field_type'],
                options=existing_options
            )
            if field_data:
                self.db.update_deck_custom_field(
                    field_id,
                    field_name=field_data['name'],
                    field_type=field_data['type'],
                    field_options=field_data.get('options')
                )
                custom_fields[field_idx] = {
                    'id': field_id,
                    'deck_id': deck_id,
                    'field_name': field_data['name'],
                    'field_type': field_data['type'],
                    'field_options': json.dumps(field_data.get('options')) if field_data.get('options') else None,
                    'field_order': field['field_order']
                }
                refresh_cf_list()

        def on_delete_field(e):
            sel = cf_list.GetFirstSelected()
            if sel == -1:
                return
            field_id = cf_list.GetItemData(sel)
            field_name = cf_list.GetItemText(sel)

            if wx.MessageBox(
                f"Delete custom field '{field_name}'?\n\nThis will remove the field from all cards.",
                "Confirm Delete",
                wx.YES_NO | wx.ICON_WARNING
            ) == wx.YES:
                self.db.delete_deck_custom_field(field_id)
                for i, f in enumerate(custom_fields):
                    if f['id'] == field_id:
                        custom_fields.pop(i)
                        break
                refresh_cf_list()

        def on_move_up(e):
            sel = cf_list.GetFirstSelected()
            if sel <= 0:
                return
            # Get the IDs before swapping
            moving_up_id = custom_fields[sel]['id']
            moving_down_id = custom_fields[sel - 1]['id']
            # Swap in local list
            custom_fields[sel], custom_fields[sel - 1] = custom_fields[sel - 1], custom_fields[sel]
            # Update field_order in database (item that moved up goes to sel-1, item that moved down goes to sel)
            self.db.update_deck_custom_field(moving_up_id, field_order=sel - 1)
            self.db.update_deck_custom_field(moving_down_id, field_order=sel)
            # Update field_order in local list
            custom_fields[sel - 1]['field_order'] = sel - 1
            custom_fields[sel]['field_order'] = sel
            refresh_cf_list()
            cf_list.Select(sel - 1)

        def on_move_down(e):
            sel = cf_list.GetFirstSelected()
            if sel == -1 or sel >= len(custom_fields) - 1:
                return
            # Get the IDs before swapping
            moving_down_id = custom_fields[sel]['id']
            moving_up_id = custom_fields[sel + 1]['id']
            # Swap in local list
            custom_fields[sel], custom_fields[sel + 1] = custom_fields[sel + 1], custom_fields[sel]
            # Update field_order in database (item that moved down goes to sel+1, item that moved up goes to sel)
            self.db.update_deck_custom_field(moving_down_id, field_order=sel + 1)
            self.db.update_deck_custom_field(moving_up_id, field_order=sel)
            # Update field_order in local list
            custom_fields[sel]['field_order'] = sel
            custom_fields[sel + 1]['field_order'] = sel + 1
            refresh_cf_list()
            cf_list.Select(sel + 1)

        add_cf_btn = wx.Button(cf_panel, label="+ Add Field")
        add_cf_btn.Bind(wx.EVT_BUTTON, on_add_field)
        cf_btn_sizer.Add(add_cf_btn, 0, wx.RIGHT, 5)

        edit_cf_btn = wx.Button(cf_panel, label="Edit")
        edit_cf_btn.Bind(wx.EVT_BUTTON, on_edit_field)
        cf_btn_sizer.Add(edit_cf_btn, 0, wx.RIGHT, 5)

        del_cf_btn = wx.Button(cf_panel, label="Delete")
        del_cf_btn.Bind(wx.EVT_BUTTON, on_delete_field)
        cf_btn_sizer.Add(del_cf_btn, 0, wx.RIGHT, 15)

        move_up_btn = wx.Button(cf_panel, label="Move Up")
        move_up_btn.Bind(wx.EVT_BUTTON, on_move_up)
        cf_btn_sizer.Add(move_up_btn, 0, wx.RIGHT, 5)

        move_down_btn = wx.Button(cf_panel, label="Move Down")
        move_down_btn.Bind(wx.EVT_BUTTON, on_move_down)
        cf_btn_sizer.Add(move_down_btn, 0)

        cf_sizer.Add(cf_btn_sizer, 0, wx.ALL, 10)

        cf_panel.SetSizer(cf_sizer)
        notebook.AddPage(cf_panel, "Custom Fields")

        main_sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Save")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        dlg.SetSizer(main_sizer)

        if dlg.ShowModal() == wx.ID_OK:
            new_name = name_ctrl.GetValue().strip()
            # Build new_suit_names based on deck type
            new_suit_names = {}
            for suit_key, default_name in suits:
                new_suit_names[suit_key] = suit_ctrls[suit_key].GetValue().strip() or default_name

            # Update deck name
            if new_name and new_name != deck['name']:
                self.db.update_deck(deck_id, name=new_name)

            # Update suit names (this also updates card names)
            if new_suit_names != suit_names:
                self.db.update_deck_suit_names(deck_id, new_suit_names, suit_names)

            # Update deck details
            new_date = date_ctrl.GetValue().strip()
            new_publisher = pub_ctrl.GetValue().strip()
            new_credits = credits_ctrl.GetValue().strip()
            new_notes = deck_notes_ctrl.GetValue().strip()
            new_booklet = booklet_ctrl.GetValue().strip()

            # Update card back image if changed
            new_card_back = dlg._card_back_path
            if new_card_back != card_back_path:
                self.db.update_deck(deck_id, card_back_image=new_card_back if new_card_back else None)

            self.db.update_deck(deck_id,
                                date_published=new_date,
                                publisher=new_publisher,
                                credits=new_credits,
                                notes=new_notes,
                                booklet_info=new_booklet)

            # Update deck tags
            selected_tag_ids = []
            for i in range(deck_tag_checklist.GetCount()):
                if deck_tag_checklist.IsChecked(i):
                    selected_tag_ids.append(all_deck_tags[i]['id'])
            self.db.set_deck_tags(deck_id, selected_tag_ids)

            self._refresh_decks_list()
            # Re-select the deck after refresh
            self._select_deck_by_id(deck_id)
            self._refresh_cards_display(deck_id, preserve_scroll=True)
            wx.MessageBox("Deck updated!", "Success", wx.OK | wx.ICON_INFORMATION)

        dlg.Destroy()

    def _show_custom_field_dialog(self, parent, name='', field_type='text', options=None):
        """Show dialog to add/edit a custom field definition"""
        dlg = wx.Dialog(parent, title="Custom Field", size=(400, 300))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Field name
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(dlg, label="Field Name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        name_ctrl = wx.TextCtrl(dlg, value=name)
        name_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        name_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_ctrl, 1)
        sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Field type
        type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        type_label = wx.StaticText(dlg, label="Field Type:")
        type_label.SetForegroundColour(get_wx_color('text_primary'))
        type_sizer.Add(type_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        field_types = ['text', 'multiline', 'number', 'select', 'checkbox']
        type_ctrl = wx.Choice(dlg, choices=field_types)
        if field_type in field_types:
            type_ctrl.SetSelection(field_types.index(field_type))
        else:
            type_ctrl.SetSelection(0)
        type_sizer.Add(type_ctrl, 1)
        sizer.Add(type_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Options (for select type)
        options_label = wx.StaticText(dlg, label="Options (for 'select' type, one per line):")
        options_label.SetForegroundColour(get_wx_color('text_primary'))
        sizer.Add(options_label, 0, wx.LEFT | wx.TOP, 10)

        options_ctrl = wx.TextCtrl(dlg, style=wx.TE_MULTILINE,
                                   value='\n'.join(options) if options else '')
        options_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        options_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        sizer.Add(options_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Save")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        dlg.SetSizer(sizer)

        result = None
        if dlg.ShowModal() == wx.ID_OK:
            field_name = name_ctrl.GetValue().strip()
            if field_name:
                selected_type = type_ctrl.GetString(type_ctrl.GetSelection())
                opts = None
                if selected_type == 'select':
                    opts_text = options_ctrl.GetValue().strip()
                    if opts_text:
                        opts = [o.strip() for o in opts_text.split('\n') if o.strip()]
                result = {
                    'name': field_name,
                    'type': selected_type,
                    'options': opts
                }

        dlg.Destroy()
        return result
    
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
            
            if deck_type in ('Lenormand', 'Playing Cards'):
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

        # Court Cards section (only shown for Tarot)
        court_box = wx.StaticBox(dlg, label="Court Cards")
        court_box.SetForegroundColour(get_wx_color('accent'))
        court_box_sizer = wx.StaticBoxSizer(court_box, wx.VERTICAL)

        # Court preset dropdown row
        court_preset_sizer = wx.BoxSizer(wx.HORIZONTAL)
        court_preset_label = wx.StaticText(dlg, label="Court Style:")
        court_preset_label.SetForegroundColour(get_wx_color('text_secondary'))
        court_preset_sizer.Add(court_preset_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        court_preset_names = list(COURT_PRESETS.keys())
        court_preset_choice = wx.Choice(dlg, choices=court_preset_names)
        court_preset_choice.SetSelection(0)  # Default to RWS
        court_preset_sizer.Add(court_preset_choice, 0, wx.RIGHT, 20)

        # Archetype mapping dropdown
        archetype_label = wx.StaticText(dlg, label="Archetype Mapping:")
        archetype_label.SetForegroundColour(get_wx_color('text_secondary'))
        court_preset_sizer.Add(archetype_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        archetype_choice = wx.Choice(dlg, choices=ARCHETYPE_MAPPING_OPTIONS)
        archetype_choice.SetSelection(0)  # Default to RWS archetypes
        court_preset_sizer.Add(archetype_choice, 0)

        court_box_sizer.Add(court_preset_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Custom court name controls (hidden by default)
        court_custom_panel = wx.Panel(dlg)
        court_custom_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        court_custom_sizer = wx.BoxSizer(wx.HORIZONTAL)

        court_ctrls = {}
        court_positions = [('page', 'Page'), ('knight', 'Knight'), ('queen', 'Queen'), ('king', 'King')]
        for pos_key, default_name in court_positions:
            col = wx.BoxSizer(wx.VERTICAL)
            label = wx.StaticText(court_custom_panel, label=f"{default_name}:")
            label.SetForegroundColour(get_wx_color('text_secondary'))
            col.Add(label, 0, wx.BOTTOM, 2)

            ctrl = wx.TextCtrl(court_custom_panel, value=default_name, size=(100, -1))
            ctrl.SetBackgroundColour(get_wx_color('bg_input'))
            ctrl.SetForegroundColour(get_wx_color('text_primary'))
            ctrl.Bind(wx.EVT_TEXT, lambda e: update_preview())
            court_ctrls[pos_key] = ctrl
            col.Add(ctrl, 0)

            court_custom_sizer.Add(col, 0, wx.ALL, 5)

        court_custom_panel.SetSizer(court_custom_sizer)
        court_custom_panel.Hide()  # Hidden by default
        court_box_sizer.Add(court_custom_panel, 0, wx.EXPAND)

        sizer.Add(court_box_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Track court section visibility
        court_section_visible = [True]

        def update_court_section_visibility(deck_type):
            """Show/hide court section based on deck type"""
            should_show = deck_type == 'Tarot'
            if should_show != court_section_visible[0]:
                court_section_visible[0] = should_show
                court_box.Show(should_show)
                court_box_sizer.ShowItems(should_show)
                dlg.Layout()

        def on_court_preset_change(e=None):
            """Handle court preset dropdown change"""
            preset_name = court_preset_choice.GetStringSelection()
            preset_values = COURT_PRESETS.get(preset_name)

            if preset_values is None:
                # "Custom..." selected - show text fields
                court_custom_panel.Show()
            else:
                # Preset selected - hide text fields and update values
                court_custom_panel.Hide()
                for pos_key, name in preset_values.items():
                    if pos_key in court_ctrls:
                        court_ctrls[pos_key].SetValue(name)

            dlg.Layout()
            update_preview()

        court_preset_choice.Bind(wx.EVT_CHOICE, on_court_preset_change)
        archetype_choice.Bind(wx.EVT_CHOICE, lambda e: update_preview())

        def get_court_names():
            """Get current court card names from UI"""
            preset_name = court_preset_choice.GetStringSelection()
            preset_values = COURT_PRESETS.get(preset_name)

            if preset_values is None:
                # Custom - use text field values
                return {pos: ctrl.GetValue() for pos, ctrl in court_ctrls.items()}
            else:
                return preset_values.copy()

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

                # Get court card settings if it's a Tarot deck
                custom_court_names = None
                archetype_mapping = None
                if current_deck_type[0] == 'Tarot':
                    custom_court_names = get_court_names()
                    archetype_mapping = archetype_choice.GetStringSelection()

                preset_name = preset_choice.GetStringSelection()
                # Use the metadata-aware preview to show card names with court customization
                preview = self.presets.preview_import_with_metadata(
                    folder, preset_name, custom_suit_names, custom_court_names, archetype_mapping
                )
                for card_info in preview:
                    idx = preview_list.InsertItem(preview_list.GetItemCount(), card_info['filename'])
                    preview_list.SetItem(idx, 1, card_info['name'])
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
                    # Update court section visibility
                    update_court_section_visibility(deck_type)

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

                # Get court card names (only for Tarot)
                court_names = None
                custom_court_names = None
                archetype_mapping = None
                if cart_type == 'Tarot':
                    court_names = get_court_names()
                    custom_court_names = court_names
                    archetype_mapping = archetype_choice.GetStringSelection()

                deck_id = self.db.add_deck(name, type_id, folder, suit_names, court_names)

                # Use the metadata-aware import to get archetype, rank, suit
                preset_name = preset_choice.GetStringSelection()
                preview = self.presets.preview_import_with_metadata(
                    folder, preset_name, suit_names, custom_court_names, archetype_mapping
                )
                cards = []
                for card_info in preview:
                    cards.append({
                        'name': card_info['name'],
                        'image_path': os.path.join(folder, card_info['filename']),
                        'sort_order': card_info['sort_order'],
                        'archetype': card_info['archetype'],
                        'rank': card_info['rank'],
                        'suit': card_info['suit'],
                    })

                # Look for card back image
                card_back_path = self.presets.find_card_back_image(folder, preset_name)
                if card_back_path:
                    self.db.update_deck(deck_id, card_back_image=card_back_path)

                if cards:
                    self.db.bulk_add_cards(deck_id, cards)
                    self.thumb_cache.pregenerate_thumbnails([c['image_path'] for c in cards])
                    card_back_msg = f"\nCard back image: Found" if card_back_path else ""
                    wx.MessageBox(f"Imported {len(cards)} cards into '{name}'{card_back_msg}", "Success", wx.OK | wx.ICON_INFORMATION)

                self._refresh_decks_list()
        
        dlg.Destroy()
    
    def _on_delete_deck(self, event):
        # Get deck_id based on current view mode
        deck_id = None
        if self._deck_view_mode == 'image':
            deck_id = self._selected_deck_id
        else:
            idx = self.deck_list.GetFirstSelected()
            if idx != -1:
                deck_id = self.deck_list.GetItemData(idx)

        if not deck_id:
            return
        deck = self.db.get_deck(deck_id)

        if wx.MessageBox(f"Delete '{deck['name']}' and all cards?", "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            self.db.delete_deck(deck_id)
            self._selected_deck_id = None
            self._refresh_decks_list()
            self._refresh_cards_display(None)

    def _on_export_deck(self, event):
        """Export the selected deck with all metadata to a JSON file."""
        # Get deck_id based on current view mode
        deck_id = None
        if self._deck_view_mode == 'image':
            deck_id = self._selected_deck_id
        else:
            idx = self.deck_list.GetFirstSelected()
            if idx != -1:
                deck_id = self.deck_list.GetItemData(idx)

        if not deck_id:
            wx.MessageBox("Select a deck to export.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return
        deck = self.db.get_deck(deck_id)
        if not deck:
            return

        # File save dialog
        wildcard = "JSON files (*.json)|*.json"
        default_name = f"{deck['name'].replace(' ', '_')}_deck.json"

        file_dlg = wx.FileDialog(
            self, "Export Deck",
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )
        file_dlg.SetFilename(default_name)

        if file_dlg.ShowModal() == wx.ID_OK:
            filepath = file_dlg.GetPath()
            try:
                self.db.export_deck_to_file(deck_id, filepath)
                wx.MessageBox(
                    f"Deck exported successfully!\n\nSaved to: {filepath}",
                    "Export Complete",
                    wx.OK | wx.ICON_INFORMATION
                )
            except Exception as e:
                wx.MessageBox(
                    f"Export failed:\n{str(e)}",
                    "Export Error",
                    wx.OK | wx.ICON_ERROR
                )

        file_dlg.Destroy()

    def _on_import_deck(self, event):
        """Import a deck from a JSON file."""
        wildcard = "JSON files (*.json)|*.json"

        file_dlg = wx.FileDialog(
            self, "Import Deck",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if file_dlg.ShowModal() == wx.ID_OK:
            filepath = file_dlg.GetPath()
            try:
                result = self.db.import_deck_from_file(filepath)
                self._refresh_decks_list()
                wx.MessageBox(
                    f"Deck imported successfully!\n\n"
                    f"Deck: {result['deck_name']}\n"
                    f"Cards: {result['cards_imported']}\n"
                    f"Custom fields: {result['custom_fields_created']}",
                    "Import Complete",
                    wx.OK | wx.ICON_INFORMATION
                )
            except Exception as e:
                wx.MessageBox(
                    f"Import failed:\n{str(e)}",
                    "Import Error",
                    wx.OK | wx.ICON_ERROR
                )

        file_dlg.Destroy()

    def _on_add_card(self, event):
        # Get deck_id based on current view mode
        deck_id = None
        if self._deck_view_mode == 'image':
            deck_id = self._selected_deck_id
        else:
            idx = self.deck_list.GetFirstSelected()
            if idx != -1:
                deck_id = self.deck_list.GetItemData(idx)

        if not deck_id:
            wx.MessageBox("Select a deck first.", "No Deck", wx.OK | wx.ICON_INFORMATION)
            return
        
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
        # Get deck_id based on current view mode
        deck_id = None
        if self._deck_view_mode == 'image':
            deck_id = self._selected_deck_id
        else:
            idx = self.deck_list.GetFirstSelected()
            if idx != -1:
                deck_id = self.deck_list.GetItemData(idx)

        if not deck_id:
            wx.MessageBox("Select a deck first.", "No Deck", wx.OK | wx.ICON_INFORMATION)
            return
        
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

    def _on_view_card(self, event, card_id, return_after_edit=False):
        """Show a card detail view with full-size image and all metadata"""
        if not card_id:
            return

        # Get deck_id based on current view mode
        deck_id = None
        if self._deck_view_mode == 'image':
            deck_id = self._selected_deck_id
        else:
            idx = self.deck_list.GetFirstSelected()
            if idx != -1:
                deck_id = self.deck_list.GetItemData(idx)

        if not deck_id:
            return

        # Get the sorted list of cards for navigation
        card_list = self._current_cards_sorted if hasattr(self, '_current_cards_sorted') else []
        card_ids = [c['id'] for c in card_list]
        current_index = card_ids.index(card_id) if card_id in card_ids else -1

        # Get card with full metadata
        card = self.db.get_card_with_metadata(card_id)
        if not card:
            return

        # Get deck info
        deck = self.db.get_deck(deck_id)
        if not deck:
            return

        cartomancy_type = deck['cartomancy_type_name']

        # Helper to safely get card fields
        def get_field(field_name, default=''):
            try:
                if field_name in card.keys():
                    return card[field_name] if card[field_name] is not None else default
            except:
                pass
            return default

        # Create dialog
        dlg = wx.Dialog(self, title=f"Card: {card['name']}", size=(700, 550), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Content area - horizontal split
        content_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Left side: Full-size image
        image_panel = wx.Panel(dlg)
        image_panel.SetBackgroundColour(get_wx_color('bg_secondary'))
        image_sizer = wx.BoxSizer(wx.VERTICAL)

        image_path = card['image_path']
        if image_path and os.path.exists(image_path):
            try:
                from PIL import ImageOps
                # Load with PIL to handle EXIF orientation properly
                pil_img = Image.open(image_path)
                pil_img = ImageOps.exif_transpose(pil_img)

                # Scale to fit in panel while preserving aspect ratio
                max_width, max_height = 300, 450
                orig_width, orig_height = pil_img.size
                scale = min(max_width / orig_width, max_height / orig_height)
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)
                pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Convert PIL image to wx.Image
                if pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')
                wx_img = wx.Image(new_width, new_height)
                wx_img.SetData(pil_img.tobytes())
                bmp = wx.StaticBitmap(image_panel, bitmap=wx.Bitmap(wx_img))
                image_sizer.Add(bmp, 0, wx.ALL | wx.ALIGN_CENTER, 10)
            except Exception as e:
                no_img = wx.StaticText(image_panel, label="🂠")
                no_img.SetFont(wx.Font(72, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                no_img.SetForegroundColour(get_wx_color('text_dim'))
                image_sizer.Add(no_img, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        else:
            no_img = wx.StaticText(image_panel, label="🂠")
            no_img.SetFont(wx.Font(72, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            no_img.SetForegroundColour(get_wx_color('text_dim'))
            image_sizer.Add(no_img, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        image_panel.SetSizer(image_sizer)
        content_sizer.Add(image_panel, 0, wx.EXPAND | wx.ALL, 10)

        # Right side: Card info
        info_panel = wx.ScrolledWindow(dlg)
        info_panel.SetScrollRate(0, 10)
        info_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        info_sizer = wx.BoxSizer(wx.VERTICAL)

        # Card name (large)
        name_label = wx.StaticText(info_panel, label=card['name'])
        name_label.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        info_sizer.Add(name_label, 0, wx.BOTTOM, 10)

        # Deck name
        deck_label = wx.StaticText(info_panel, label=f"Deck: {deck['name']}")
        deck_label.SetForegroundColour(get_wx_color('text_secondary'))
        info_sizer.Add(deck_label, 0, wx.BOTTOM, 15)

        # Separator
        sep1 = wx.StaticLine(info_panel)
        info_sizer.Add(sep1, 0, wx.EXPAND | wx.BOTTOM, 15)

        # Classification section
        class_title = wx.StaticText(info_panel, label="Classification")
        class_title.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        class_title.SetForegroundColour(get_wx_color('accent'))
        info_sizer.Add(class_title, 0, wx.BOTTOM, 8)

        # Archetype
        archetype = get_field('archetype', '')
        if archetype:
            arch_row = wx.BoxSizer(wx.HORIZONTAL)
            arch_lbl = wx.StaticText(info_panel, label="Archetype: ")
            arch_lbl.SetForegroundColour(get_wx_color('text_secondary'))
            arch_row.Add(arch_lbl, 0)
            arch_val = wx.StaticText(info_panel, label=archetype)
            arch_val.SetForegroundColour(get_wx_color('text_primary'))
            arch_row.Add(arch_val, 0)
            info_sizer.Add(arch_row, 0, wx.BOTTOM, 5)

        # Rank
        rank = get_field('rank', '')
        if rank:
            rank_row = wx.BoxSizer(wx.HORIZONTAL)
            rank_lbl = wx.StaticText(info_panel, label="Rank: ")
            rank_lbl.SetForegroundColour(get_wx_color('text_secondary'))
            rank_row.Add(rank_lbl, 0)
            rank_val = wx.StaticText(info_panel, label=str(rank))
            rank_val.SetForegroundColour(get_wx_color('text_primary'))
            rank_row.Add(rank_val, 0)
            info_sizer.Add(rank_row, 0, wx.BOTTOM, 5)

        # Suit
        suit = get_field('suit', '')
        if suit:
            suit_row = wx.BoxSizer(wx.HORIZONTAL)
            suit_lbl = wx.StaticText(info_panel, label="Suit: ")
            suit_lbl.SetForegroundColour(get_wx_color('text_secondary'))
            suit_row.Add(suit_lbl, 0)
            suit_val = wx.StaticText(info_panel, label=suit)
            suit_val.SetForegroundColour(get_wx_color('text_primary'))
            suit_row.Add(suit_val, 0)
            info_sizer.Add(suit_row, 0, wx.BOTTOM, 5)

        # Sort order
        sort_order = get_field('card_order', 0)
        order_row = wx.BoxSizer(wx.HORIZONTAL)
        order_lbl = wx.StaticText(info_panel, label="Sort Order: ")
        order_lbl.SetForegroundColour(get_wx_color('text_secondary'))
        order_row.Add(order_lbl, 0)
        order_val = wx.StaticText(info_panel, label=str(sort_order))
        order_val.SetForegroundColour(get_wx_color('text_primary'))
        order_row.Add(order_val, 0)
        info_sizer.Add(order_row, 0, wx.BOTTOM, 15)

        # Notes section
        notes = get_field('notes', '')
        if notes:
            sep2 = wx.StaticLine(info_panel)
            info_sizer.Add(sep2, 0, wx.EXPAND | wx.BOTTOM, 15)

            notes_title = wx.StaticText(info_panel, label="Notes")
            notes_title.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            notes_title.SetForegroundColour(get_wx_color('accent'))
            info_sizer.Add(notes_title, 0, wx.BOTTOM, 8)

            notes_text = wx.StaticText(info_panel, label=notes)
            notes_text.SetForegroundColour(get_wx_color('text_primary'))
            notes_text.Wrap(280)
            info_sizer.Add(notes_text, 0, wx.BOTTOM, 15)

        # Custom fields section
        custom_fields_json = get_field('custom_fields', None)
        if custom_fields_json:
            try:
                custom_fields = json.loads(custom_fields_json)
                if custom_fields:
                    sep3 = wx.StaticLine(info_panel)
                    info_sizer.Add(sep3, 0, wx.EXPAND | wx.BOTTOM, 15)

                    cf_title = wx.StaticText(info_panel, label="Custom Fields")
                    cf_title.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                    cf_title.SetForegroundColour(get_wx_color('accent'))
                    info_sizer.Add(cf_title, 0, wx.BOTTOM, 8)

                    for field_name, field_value in custom_fields.items():
                        # Skip empty fields
                        if field_value is None or str(field_value).strip() == '':
                            continue
                        value_str = str(field_value)
                        # Always use vertical layout with wrapping for custom fields
                        # This ensures long text is always readable
                        cf_lbl = wx.StaticText(info_panel, label=f"{field_name}:")
                        cf_lbl.SetForegroundColour(get_wx_color('text_secondary'))
                        info_sizer.Add(cf_lbl, 0, wx.BOTTOM, 3)
                        cf_val = wx.StaticText(info_panel, label=value_str)
                        cf_val.SetForegroundColour(get_wx_color('text_primary'))
                        cf_val.Wrap(280)
                        info_sizer.Add(cf_val, 0, wx.BOTTOM, 10)
            except:
                pass

        # Tags section
        inherited_tags = self.db.get_inherited_tags_for_card(card_id)
        card_tags = self.db.get_tags_for_card(card_id)

        if inherited_tags or card_tags:
            sep4 = wx.StaticLine(info_panel)
            info_sizer.Add(sep4, 0, wx.EXPAND | wx.BOTTOM, 15)

            tags_title = wx.StaticText(info_panel, label="Tags")
            tags_title.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            tags_title.SetForegroundColour(get_wx_color('accent'))
            info_sizer.Add(tags_title, 0, wx.BOTTOM, 8)

            # Deck tags (inherited)
            if inherited_tags:
                deck_tags_row = wx.BoxSizer(wx.HORIZONTAL)
                deck_tags_lbl = wx.StaticText(info_panel, label="Deck Tags: ")
                deck_tags_lbl.SetForegroundColour(get_wx_color('text_secondary'))
                deck_tags_row.Add(deck_tags_lbl, 0)
                deck_tags_val = wx.StaticText(info_panel, label=", ".join([t['name'] for t in inherited_tags]))
                deck_tags_val.SetForegroundColour(get_wx_color('text_primary'))
                deck_tags_row.Add(deck_tags_val, 0)
                info_sizer.Add(deck_tags_row, 0, wx.BOTTOM, 5)

            # Card-specific tags
            if card_tags:
                card_tags_row = wx.BoxSizer(wx.HORIZONTAL)
                card_tags_lbl = wx.StaticText(info_panel, label="Card Tags: ")
                card_tags_lbl.SetForegroundColour(get_wx_color('text_secondary'))
                card_tags_row.Add(card_tags_lbl, 0)
                card_tags_val = wx.StaticText(info_panel, label=", ".join([t['name'] for t in card_tags]))
                card_tags_val.SetForegroundColour(get_wx_color('text_primary'))
                card_tags_row.Add(card_tags_val, 0)
                info_sizer.Add(card_tags_row, 0, wx.BOTTOM, 5)

        info_panel.SetSizer(info_sizer)
        content_sizer.Add(info_panel, 1, wx.EXPAND | wx.ALL, 10)

        main_sizer.Add(content_sizer, 1, wx.EXPAND)

        # Button row
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Navigation buttons on the left
        nav_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Track navigation state
        nav_to_card = [None]  # Use list to allow modification in nested function

        prev_btn = wx.Button(dlg, label="< Prev")
        if current_index <= 0:
            prev_btn.Disable()
        def on_prev(e):
            if current_index > 0:
                nav_to_card[0] = card_ids[current_index - 1]
                dlg.EndModal(wx.ID_BACKWARD)
        prev_btn.Bind(wx.EVT_BUTTON, on_prev)
        nav_sizer.Add(prev_btn, 0, wx.RIGHT, 5)

        next_btn = wx.Button(dlg, label="Next >")
        if current_index < 0 or current_index >= len(card_ids) - 1:
            next_btn.Disable()
        def on_next(e):
            if current_index < len(card_ids) - 1:
                nav_to_card[0] = card_ids[current_index + 1]
                dlg.EndModal(wx.ID_FORWARD)
        next_btn.Bind(wx.EVT_BUTTON, on_next)
        nav_sizer.Add(next_btn, 0)

        btn_sizer.Add(nav_sizer, 0, wx.RIGHT, 20)
        btn_sizer.AddStretchSpacer()

        # Action buttons on the right
        edit_requested = [False]  # Track if edit was requested

        def on_edit(e):
            edit_requested[0] = True
            dlg.EndModal(wx.ID_OK)

        edit_btn = wx.Button(dlg, label="Edit Card")
        edit_btn.Bind(wx.EVT_BUTTON, on_edit)
        btn_sizer.Add(edit_btn, 0, wx.RIGHT, 10)

        close_btn = wx.Button(dlg, wx.ID_CANCEL, "Close")
        btn_sizer.Add(close_btn, 0)

        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 15)

        dlg.SetSizer(main_sizer)
        result = dlg.ShowModal()
        dlg.Destroy()

        # Handle navigation or edit
        if result == wx.ID_BACKWARD or result == wx.ID_FORWARD:
            if nav_to_card[0]:
                self._on_view_card(None, nav_to_card[0])
        elif edit_requested[0]:
            self._on_edit_card(None, card_id, return_to_view=True)

    def _on_edit_card(self, event, card_id=None, return_to_view=False):
        if card_id is None:
            # Get first selected card
            if self.selected_card_ids:
                card_id = next(iter(self.selected_card_ids))
            else:
                card_id = None

        if not card_id:
            wx.MessageBox("Select a card to edit.", "No Card", wx.OK | wx.ICON_INFORMATION)
            return

        # Get deck_id based on current view mode
        deck_id = None
        if self._deck_view_mode == 'image':
            deck_id = self._selected_deck_id
        else:
            idx = self.deck_list.GetFirstSelected()
            if idx != -1:
                deck_id = self.deck_list.GetItemData(idx)

        if not deck_id:
            return

        # Store return_to_view for after dialog closes
        should_return_to_view = return_to_view

        # Get card with full metadata
        card = self.db.get_card_with_metadata(card_id)
        if not card:
            return

        # Get deck info for cartomancy type
        deck = self.db.get_deck(deck_id)
        if not deck:
            return

        cartomancy_type = deck['cartomancy_type_name']

        # Get deck custom fields
        deck_custom_fields = self.db.get_deck_custom_fields(deck_id)

        # Helper to safely get card fields (handles missing columns in older DBs)
        def get_card_field(field_name, default=''):
            try:
                if field_name in card.keys():
                    return card[field_name] if card[field_name] is not None else default
            except:
                pass
            return default

        # Parse existing custom field values from card
        existing_custom_values = {}
        try:
            custom_fields_json = get_card_field('custom_fields', None)
            if custom_fields_json:
                existing_custom_values = json.loads(custom_fields_json)
        except:
            pass

        dlg = wx.Dialog(self, title="Edit Card", size=(750, 580), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Content area: image on left, notebook on right
        content_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Left side: Card image preview (visible on all tabs)
        image_preview_panel = wx.Panel(dlg)
        image_preview_panel.SetBackgroundColour(get_wx_color('bg_secondary'))
        image_preview_sizer = wx.BoxSizer(wx.VERTICAL)

        # Create the image display - same size as card info page (300x450)
        max_width, max_height = 300, 450
        card_image_path = card['image_path']

        def load_preview_image(path):
            """Load and scale image for preview using PIL for EXIF handling"""
            if path and os.path.exists(path):
                try:
                    from PIL import ImageOps
                    # Load with PIL to handle EXIF orientation properly
                    pil_img = Image.open(path)
                    pil_img = ImageOps.exif_transpose(pil_img)

                    # Scale to fit while preserving aspect ratio
                    orig_width, orig_height = pil_img.size
                    scale = min(max_width / orig_width, max_height / orig_height)
                    new_width = int(orig_width * scale)
                    new_height = int(orig_height * scale)
                    pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # Convert PIL image to wx.Bitmap
                    if pil_img.mode != 'RGB':
                        pil_img = pil_img.convert('RGB')
                    wx_img = wx.Image(new_width, new_height)
                    wx_img.SetData(pil_img.tobytes())
                    return wx.Bitmap(wx_img)
                except:
                    pass
            return None

        preview_bitmap = load_preview_image(card_image_path)
        if preview_bitmap:
            image_display = wx.StaticBitmap(image_preview_panel, bitmap=preview_bitmap)
        else:
            image_display = wx.StaticText(image_preview_panel, label="🂠")
            image_display.SetFont(wx.Font(72, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            image_display.SetForegroundColour(get_wx_color('text_dim'))

        image_preview_sizer.Add(image_display, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        image_preview_panel.SetSizer(image_preview_sizer)
        content_sizer.Add(image_preview_panel, 0, wx.ALL, 10)

        def update_preview(path):
            """Update the image preview"""
            nonlocal image_display
            new_bitmap = load_preview_image(path)
            if new_bitmap:
                if isinstance(image_display, wx.StaticText):
                    # Replace text with bitmap
                    image_display.Destroy()
                    image_display = wx.StaticBitmap(image_preview_panel, bitmap=new_bitmap)
                    image_preview_sizer.Insert(0, image_display, 0, wx.ALL | wx.ALIGN_CENTER, 10)
                else:
                    image_display.SetBitmap(new_bitmap)
                image_preview_panel.Layout()

        # Right side: Notebook with tabs
        style = (fnb.FNB_NO_X_BUTTON | fnb.FNB_NO_NAV_BUTTONS | fnb.FNB_NODRAG)
        notebook = fnb.FlatNotebook(dlg, agwStyle=style)
        notebook.SetBackgroundColour(get_wx_color('bg_primary'))
        notebook.SetTabAreaColour(get_wx_color('bg_primary'))
        notebook.SetActiveTabColour(get_wx_color('bg_tertiary'))
        notebook.SetNonActiveTabTextColour(get_wx_color('text_primary'))
        notebook.SetActiveTabTextColour(get_wx_color('text_primary'))
        notebook.SetGradientColourTo(get_wx_color('bg_tertiary'))
        notebook.SetGradientColourFrom(get_wx_color('bg_secondary'))

        # === Basic Info Tab ===
        basic_panel = wx.Panel(notebook)
        basic_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        basic_sizer = wx.BoxSizer(wx.VERTICAL)

        # Name
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(basic_panel, label="Name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        name_ctrl = wx.TextCtrl(basic_panel, value=card['name'])
        name_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        name_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        name_sizer.Add(name_ctrl, 1)
        basic_sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Image path
        image_path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        image_label = wx.StaticText(basic_panel, label="Image:")
        image_label.SetForegroundColour(get_wx_color('text_primary'))
        image_path_sizer.Add(image_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        image_ctrl = wx.TextCtrl(basic_panel, value=card['image_path'] or '')
        image_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        image_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        image_path_sizer.Add(image_ctrl, 1, wx.RIGHT, 5)

        def browse(e):
            file_dlg = wx.FileDialog(dlg, wildcard="Images|*.jpg;*.jpeg;*.png;*.gif;*.webp")
            if file_dlg.ShowModal() == wx.ID_OK:
                new_path = file_dlg.GetPath()
                image_ctrl.SetValue(new_path)
                update_preview(new_path)
            file_dlg.Destroy()

        browse_btn = wx.Button(basic_panel, label="Browse")
        browse_btn.Bind(wx.EVT_BUTTON, browse)
        image_path_sizer.Add(browse_btn, 0)
        basic_sizer.Add(image_path_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Sort order
        order_sizer = wx.BoxSizer(wx.HORIZONTAL)
        order_label = wx.StaticText(basic_panel, label="Sort Order:")
        order_label.SetForegroundColour(get_wx_color('text_primary'))
        order_sizer.Add(order_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        order_ctrl = wx.SpinCtrl(basic_panel, min=0, max=999, initial=get_card_field('card_order', 0) or 0)
        order_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
        order_ctrl.SetForegroundColour(get_wx_color('text_primary'))
        order_sizer.Add(order_ctrl, 0)
        basic_sizer.Add(order_sizer, 0, wx.EXPAND | wx.ALL, 10)

        basic_panel.SetSizer(basic_sizer)
        notebook.AddPage(basic_panel, "Basic Info")

        # === Classification Tab ===
        class_panel = wx.Panel(notebook)
        class_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        class_sizer = wx.BoxSizer(wx.VERTICAL)

        # Archetype (with autocomplete for non-Oracle)
        arch_sizer = wx.BoxSizer(wx.HORIZONTAL)
        arch_label = wx.StaticText(class_panel, label="Archetype:")
        arch_label.SetForegroundColour(get_wx_color('text_primary'))
        arch_sizer.Add(arch_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        archetype_ctrl = ArchetypeAutocomplete(
            class_panel, self.db, cartomancy_type,
            value=get_card_field('archetype', '')
        )
        arch_sizer.Add(archetype_ctrl, 1, wx.EXPAND)
        class_sizer.Add(arch_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Rank and Suit (varies by type)
        rank_ctrl = None
        suit_ctrl = None

        if cartomancy_type == 'Tarot':
            # Tarot: Rank dropdown and Suit dropdown
            rank_sizer = wx.BoxSizer(wx.HORIZONTAL)
            rank_label = wx.StaticText(class_panel, label="Rank:")
            rank_label.SetForegroundColour(get_wx_color('text_primary'))
            rank_sizer.Add(rank_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

            tarot_ranks = ['', 'Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
                          'Eight', 'Nine', 'Ten',
                          'Page / Knave / Princess / Court Rank 1',
                          'Knight / Prince / Court Rank 2',
                          'Queen / Court Rank 3',
                          'King / Court Rank 4',
                          '0', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX',
                          'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII',
                          'XIX', 'XX', 'XXI']
            rank_ctrl = wx.Choice(class_panel, choices=tarot_ranks)
            current_rank = get_card_field('rank', '')
            if current_rank in tarot_ranks:
                rank_ctrl.SetSelection(tarot_ranks.index(current_rank))
            else:
                rank_ctrl.SetSelection(0)
            rank_sizer.Add(rank_ctrl, 1)
            class_sizer.Add(rank_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

            suit_sizer = wx.BoxSizer(wx.HORIZONTAL)
            suit_label = wx.StaticText(class_panel, label="Suit:")
            suit_label.SetForegroundColour(get_wx_color('text_primary'))
            suit_sizer.Add(suit_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

            tarot_suits = ['', 'Major Arcana', 'Wands', 'Cups', 'Swords', 'Pentacles']
            suit_ctrl = wx.Choice(class_panel, choices=tarot_suits)
            current_suit = get_card_field('suit', '')
            if current_suit in tarot_suits:
                suit_ctrl.SetSelection(tarot_suits.index(current_suit))
            else:
                suit_ctrl.SetSelection(0)
            suit_sizer.Add(suit_ctrl, 1)
            class_sizer.Add(suit_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        elif cartomancy_type == 'Playing Cards':
            # Playing Cards: Rank dropdown and Suit dropdown
            rank_sizer = wx.BoxSizer(wx.HORIZONTAL)
            rank_label = wx.StaticText(class_panel, label="Rank:")
            rank_label.SetForegroundColour(get_wx_color('text_primary'))
            rank_sizer.Add(rank_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

            playing_ranks = ['', 'Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
                           'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King', 'Joker']
            rank_ctrl = wx.Choice(class_panel, choices=playing_ranks)
            current_rank = get_card_field('rank', '')
            if current_rank in playing_ranks:
                rank_ctrl.SetSelection(playing_ranks.index(current_rank))
            else:
                rank_ctrl.SetSelection(0)
            rank_sizer.Add(rank_ctrl, 1)
            class_sizer.Add(rank_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

            suit_sizer = wx.BoxSizer(wx.HORIZONTAL)
            suit_label = wx.StaticText(class_panel, label="Suit:")
            suit_label.SetForegroundColour(get_wx_color('text_primary'))
            suit_sizer.Add(suit_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

            playing_suits = ['', 'Hearts', 'Diamonds', 'Clubs', 'Spades']
            suit_ctrl = wx.Choice(class_panel, choices=playing_suits)
            current_suit = get_card_field('suit', '')
            if current_suit in playing_suits:
                suit_ctrl.SetSelection(playing_suits.index(current_suit))
            else:
                suit_ctrl.SetSelection(0)
            suit_sizer.Add(suit_ctrl, 1)
            class_sizer.Add(suit_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        elif cartomancy_type == 'Lenormand':
            # Lenormand: Playing card rank (6-10, Jack, Queen, King, Ace)
            rank_sizer = wx.BoxSizer(wx.HORIZONTAL)
            rank_label = wx.StaticText(class_panel, label="Playing Card Rank:")
            rank_label.SetForegroundColour(get_wx_color('text_primary'))
            rank_sizer.Add(rank_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

            lenormand_ranks = ['', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace']
            rank_ctrl = wx.Choice(class_panel, choices=lenormand_ranks)
            rank_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
            rank_ctrl.SetForegroundColour(get_wx_color('text_primary'))
            card_rank = get_card_field('rank', '')
            if card_rank in lenormand_ranks:
                rank_ctrl.SetSelection(lenormand_ranks.index(card_rank))
            else:
                rank_ctrl.SetSelection(0)
            rank_sizer.Add(rank_ctrl, 1)
            class_sizer.Add(rank_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

            # Lenormand: Playing card suit
            suit_sizer = wx.BoxSizer(wx.HORIZONTAL)
            suit_label = wx.StaticText(class_panel, label="Playing Card Suit:")
            suit_label.SetForegroundColour(get_wx_color('text_primary'))
            suit_sizer.Add(suit_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

            lenormand_suits = ['', 'Hearts', 'Diamonds', 'Clubs', 'Spades']
            suit_ctrl = wx.Choice(class_panel, choices=lenormand_suits)
            suit_ctrl.SetBackgroundColour(get_wx_color('bg_input'))
            suit_ctrl.SetForegroundColour(get_wx_color('text_primary'))
            card_suit = get_card_field('suit', '')
            if card_suit in lenormand_suits:
                suit_ctrl.SetSelection(lenormand_suits.index(card_suit))
            else:
                suit_ctrl.SetSelection(0)
            suit_sizer.Add(suit_ctrl, 1)
            class_sizer.Add(suit_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Oracle: No rank/suit fields shown

        # Helper text
        if cartomancy_type == 'Oracle':
            help_text = wx.StaticText(class_panel,
                label="Oracle decks use free-text archetypes.\nNo predefined ranks or suits.")
            help_text.SetForegroundColour(get_wx_color('text_secondary'))
            class_sizer.Add(help_text, 0, wx.ALL, 10)

        class_panel.SetSizer(class_sizer)
        notebook.AddPage(class_panel, "Classification")

        # === Notes Tab ===
        notes_scroll = scrolled.ScrolledPanel(notebook)
        notes_scroll.SetBackgroundColour(get_wx_color('bg_primary'))
        notes_scroll.SetupScrolling(scroll_x=False)
        notes_sizer = wx.BoxSizer(wx.VERTICAL)

        notes_label = wx.StaticText(notes_scroll, label="Personal Notes / Interpretations:")
        notes_label.SetForegroundColour(get_wx_color('text_primary'))
        notes_sizer.Add(notes_label, 0, wx.ALL, 10)

        notes_ctrl = RichTextPanel(notes_scroll, value=get_card_field('notes', ''), min_height=150)
        notes_sizer.Add(notes_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        notes_scroll.SetSizer(notes_sizer)
        notebook.AddPage(notes_scroll, "Notes")

        # === Tags Tab ===
        card_tags_panel = wx.Panel(notebook)
        card_tags_panel.SetBackgroundColour(get_wx_color('bg_primary'))
        card_tags_sizer = wx.BoxSizer(wx.VERTICAL)

        # Inherited tags from deck (read-only)
        inherited_tags = self.db.get_inherited_tags_for_card(card_id)
        if inherited_tags:
            inherited_label = wx.StaticText(card_tags_panel, label="Inherited from deck:")
            inherited_label.SetForegroundColour(get_wx_color('text_secondary'))
            card_tags_sizer.Add(inherited_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

            inherited_tags_text = ", ".join([t['name'] for t in inherited_tags])
            inherited_display = wx.StaticText(card_tags_panel, label=inherited_tags_text)
            inherited_display.SetForegroundColour(get_wx_color('text_dim'))
            card_tags_sizer.Add(inherited_display, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Card-specific tags
        card_tags_label = wx.StaticText(card_tags_panel, label="Card Tags:")
        card_tags_label.SetForegroundColour(get_wx_color('text_primary'))
        card_tags_sizer.Add(card_tags_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # Get current card tags and all available card tags
        current_card_tags = {t['id'] for t in self.db.get_tags_for_card(card_id)}
        all_card_tags = list(self.db.get_card_tags())

        # CheckListBox for tag selection
        card_tag_choices = [tag['name'] for tag in all_card_tags]
        card_tag_checklist = wx.CheckListBox(card_tags_panel, choices=card_tag_choices)
        card_tag_checklist.SetBackgroundColour(get_wx_color('bg_secondary'))
        card_tag_checklist.SetForegroundColour(get_wx_color('text_primary'))

        # Check the tags that are already assigned
        for i, tag in enumerate(all_card_tags):
            if tag['id'] in current_card_tags:
                card_tag_checklist.Check(i, True)

        card_tags_sizer.Add(card_tag_checklist, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Button to add new card tag
        def on_add_new_card_tag(e):
            result = self._show_tag_dialog(dlg, "Add Card Tag")
            if result:
                try:
                    new_id = self.db.add_card_tag(result['name'], result['color'])
                    # Refresh the checklist
                    all_card_tags.append({'id': new_id, 'name': result['name'], 'color': result['color']})
                    card_tag_checklist.Append(result['name'])
                    card_tag_checklist.Check(card_tag_checklist.GetCount() - 1, True)
                    # Also refresh the main tags list if visible
                    self._refresh_card_tags_list()
                except Exception as ex:
                    wx.MessageBox(f"Could not add tag: {ex}", "Error", wx.OK | wx.ICON_ERROR)

        add_card_tag_btn = wx.Button(card_tags_panel, label="+ New Tag")
        add_card_tag_btn.Bind(wx.EVT_BUTTON, on_add_new_card_tag)
        card_tags_sizer.Add(add_card_tag_btn, 0, wx.ALL, 10)

        card_tags_panel.SetSizer(card_tags_sizer)
        notebook.AddPage(card_tags_panel, "Tags")

        # === Custom Fields Tab ===
        custom_scroll = scrolled.ScrolledPanel(notebook)
        custom_scroll.SetBackgroundColour(get_wx_color('bg_primary'))
        custom_scroll.SetupScrolling(scroll_x=False)
        custom_sizer = wx.BoxSizer(wx.VERTICAL)

        custom_field_ctrls = {}

        if deck_custom_fields:
            custom_label = wx.StaticText(custom_scroll, label="Deck Custom Fields:")
            custom_label.SetForegroundColour(get_wx_color('text_primary'))
            custom_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            custom_sizer.Add(custom_label, 0, wx.ALL, 10)

            for field in deck_custom_fields:
                field_name = field['field_name']
                field_type = field['field_type']
                field_options = None
                if field['field_options']:
                    try:
                        field_options = json.loads(field['field_options'])
                    except:
                        pass

                current_value = existing_custom_values.get(field_name, '')

                # Use vertical layout for multiline fields, horizontal for others
                if field_type == 'multiline':
                    field_sizer = wx.BoxSizer(wx.VERTICAL)
                    f_label = wx.StaticText(custom_scroll, label=f"{field_name}:")
                    f_label.SetForegroundColour(get_wx_color('text_primary'))
                    field_sizer.Add(f_label, 0, wx.BOTTOM, 5)
                    ctrl = RichTextPanel(custom_scroll, value=str(current_value), min_height=120)
                    field_sizer.Add(ctrl, 0, wx.EXPAND)
                else:
                    field_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    f_label = wx.StaticText(custom_scroll, label=f"{field_name}:")
                    f_label.SetForegroundColour(get_wx_color('text_primary'))
                    field_sizer.Add(f_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

                if field_type == 'text':
                    ctrl = wx.TextCtrl(custom_scroll, value=str(current_value))
                    ctrl.SetBackgroundColour(get_wx_color('bg_input'))
                    ctrl.SetForegroundColour(get_wx_color('text_primary'))
                    field_sizer.Add(ctrl, 1)

                elif field_type == 'number':
                    try:
                        num_val = int(current_value) if current_value else 0
                    except:
                        num_val = 0
                    ctrl = wx.SpinCtrl(custom_scroll, min=-9999, max=9999, initial=num_val)
                    ctrl.SetBackgroundColour(get_wx_color('bg_input'))
                    ctrl.SetForegroundColour(get_wx_color('text_primary'))
                    field_sizer.Add(ctrl, 0)

                elif field_type == 'select' and field_options:
                    ctrl = wx.Choice(custom_scroll, choices=[''] + field_options)
                    if current_value in field_options:
                        ctrl.SetSelection(field_options.index(current_value) + 1)
                    else:
                        ctrl.SetSelection(0)
                    field_sizer.Add(ctrl, 1)

                elif field_type == 'checkbox':
                    ctrl = wx.CheckBox(custom_scroll, label="")
                    ctrl.SetValue(bool(current_value))
                    field_sizer.Add(ctrl, 0)

                elif field_type == 'multiline':
                    pass  # Already handled above

                else:
                    ctrl = wx.TextCtrl(custom_scroll, value=str(current_value))
                    ctrl.SetBackgroundColour(get_wx_color('bg_input'))
                    ctrl.SetForegroundColour(get_wx_color('text_primary'))
                    field_sizer.Add(ctrl, 1)

                custom_field_ctrls[field_name] = (ctrl, field_type)
                # Give multiline fields more vertical space
                if field_type == 'multiline':
                    custom_sizer.Add(field_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
                else:
                    custom_sizer.Add(field_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        else:
            no_fields_label = wx.StaticText(custom_scroll,
                label="No custom fields defined for this deck.\nEdit the deck to add custom fields.")
            no_fields_label.SetForegroundColour(get_wx_color('text_secondary'))
            custom_sizer.Add(no_fields_label, 0, wx.ALL, 10)

        custom_scroll.SetSizer(custom_sizer)
        notebook.AddPage(custom_scroll, "Custom Fields")

        content_sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(content_sizer, 1, wx.EXPAND)

        # Get the sorted list of cards for navigation
        card_list = self._current_cards_sorted if hasattr(self, '_current_cards_sorted') else []
        card_ids = [c['id'] for c in card_list]
        current_index = card_ids.index(card_id) if card_id in card_ids else -1

        # Track navigation state
        nav_to_card = [None]

        # Function to save card data
        def save_card_data():
            new_name = name_ctrl.GetValue().strip()
            new_image = image_ctrl.GetValue().strip() or None
            new_order = order_ctrl.GetValue()

            # Get archetype value
            new_archetype = archetype_ctrl.GetValue().strip() or None

            # Get rank value based on control type
            new_rank = None
            if rank_ctrl:
                if isinstance(rank_ctrl, wx.SpinCtrl):
                    new_rank = str(rank_ctrl.GetValue())
                elif isinstance(rank_ctrl, wx.Choice):
                    sel = rank_ctrl.GetSelection()
                    if sel > 0:
                        new_rank = rank_ctrl.GetString(sel)

            # Get suit value
            new_suit = None
            if suit_ctrl:
                sel = suit_ctrl.GetSelection()
                if sel > 0:
                    new_suit = suit_ctrl.GetString(sel)

            # Get notes
            new_notes = notes_ctrl.GetValue().strip() or None

            # Get custom field values
            new_custom_fields = {}
            for field_name, (ctrl, field_type) in custom_field_ctrls.items():
                if field_type == 'checkbox':
                    new_custom_fields[field_name] = ctrl.GetValue()
                elif field_type == 'number':
                    new_custom_fields[field_name] = ctrl.GetValue()
                elif field_type == 'select':
                    sel = ctrl.GetSelection()
                    if sel > 0:
                        new_custom_fields[field_name] = ctrl.GetString(sel)
                    else:
                        new_custom_fields[field_name] = ''
                else:
                    new_custom_fields[field_name] = ctrl.GetValue()

            if new_name:
                # Update basic card info
                self.db.update_card(card_id, name=new_name, image_path=new_image,
                                   card_order=new_order)

                # Update metadata
                self.db.update_card_metadata(
                    card_id,
                    archetype=new_archetype,
                    rank=new_rank,
                    suit=new_suit,
                    notes=new_notes,
                    custom_fields=new_custom_fields if new_custom_fields else None
                )

                # Update card tags
                selected_card_tag_ids = []
                for i in range(card_tag_checklist.GetCount()):
                    if card_tag_checklist.IsChecked(i):
                        selected_card_tag_ids.append(all_card_tags[i]['id'])
                self.db.set_card_tags(card_id, selected_card_tag_ids)

                if new_image and new_image != card['image_path']:
                    self.thumb_cache.get_thumbnail(new_image)
                return True
            return False

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Navigation buttons on the left
        nav_sizer = wx.BoxSizer(wx.HORIZONTAL)

        prev_btn = wx.Button(dlg, label="< Prev")
        if current_index <= 0:
            prev_btn.Disable()
        def on_prev(e):
            if current_index > 0:
                if save_card_data():
                    nav_to_card[0] = card_ids[current_index - 1]
                    dlg.EndModal(wx.ID_BACKWARD)
        prev_btn.Bind(wx.EVT_BUTTON, on_prev)
        nav_sizer.Add(prev_btn, 0, wx.RIGHT, 5)

        next_btn = wx.Button(dlg, label="Next >")
        if current_index < 0 or current_index >= len(card_ids) - 1:
            next_btn.Disable()
        def on_next(e):
            if current_index < len(card_ids) - 1:
                if save_card_data():
                    nav_to_card[0] = card_ids[current_index + 1]
                    dlg.EndModal(wx.ID_FORWARD)
        next_btn.Bind(wx.EVT_BUTTON, on_next)
        nav_sizer.Add(next_btn, 0)

        btn_sizer.Add(nav_sizer, 0, wx.RIGHT, 20)
        btn_sizer.AddStretchSpacer()

        # Save/Cancel buttons on the right
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
        save_btn = wx.Button(dlg, wx.ID_OK, "Save")
        btn_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(save_btn, 0)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        dlg.SetSizer(main_sizer)

        result = dlg.ShowModal()

        # Handle navigation (save already done in nav button handlers)
        if result == wx.ID_BACKWARD or result == wx.ID_FORWARD:
            self._refresh_cards_display(deck_id, preserve_scroll=True)
            dlg.Destroy()
            if nav_to_card[0]:
                self._on_edit_card(None, nav_to_card[0], return_to_view=should_return_to_view)
            return

        if result == wx.ID_OK:
            if save_card_data():
                self._refresh_cards_display(deck_id, preserve_scroll=True)

        dlg.Destroy()

        # Return to card view if requested
        if should_return_to_view:
            self._on_view_card(None, card_id)

    def _on_delete_card(self, event):
        if not self.selected_card_ids:
            wx.MessageBox("Select card(s) to delete.", "No Card", wx.OK | wx.ICON_INFORMATION)
            return

        # Get deck_id based on current view mode
        deck_id = None
        if self._deck_view_mode == 'image':
            deck_id = self._selected_deck_id
        else:
            idx = self.deck_list.GetFirstSelected()
            if idx != -1:
                deck_id = self.deck_list.GetItemData(idx)

        if not deck_id:
            return
        
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

                # Load allowed deck types
                for cb in self.spread_deck_type_checks.values():
                    cb.SetValue(False)
                allowed_types_json = spread['allowed_deck_types'] if 'allowed_deck_types' in spread.keys() else None
                if allowed_types_json:
                    allowed_types = json.loads(allowed_types_json)
                    for deck_type in allowed_types:
                        if deck_type in self.spread_deck_type_checks:
                            self.spread_deck_type_checks[deck_type].SetValue(True)

                self._update_designer_legend()
                self.designer_canvas.Refresh()
                break

    def _on_new_spread(self, event):
        self.editing_spread_id = None
        self.spread_name_ctrl.SetValue('')
        self.spread_desc_ctrl.SetValue('')
        self.designer_positions = []
        # Clear deck type checkboxes
        for cb in self.spread_deck_type_checks.values():
            cb.SetValue(False)
        self._update_designer_legend()
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

        # Collect allowed deck types
        allowed_deck_types = [
            deck_type for deck_type, cb in self.spread_deck_type_checks.items()
            if cb.GetValue()
        ]

        if self.editing_spread_id:
            self.db.update_spread(self.editing_spread_id, name=name,
                                 positions=self.designer_positions, description=desc,
                                 allowed_deck_types=allowed_deck_types if allowed_deck_types else None)
        else:
            self.editing_spread_id = self.db.add_spread(name, self.designer_positions, desc,
                                                        allowed_deck_types=allowed_deck_types if allowed_deck_types else None)

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
                self._update_designer_legend()
                self.designer_canvas.Refresh()
        dlg.Destroy()
    
    def _on_clear_positions(self, event):
        self.designer_positions = []
        self._update_designer_legend()
        self.designer_canvas.Refresh()

    def _on_designer_legend_toggle(self, event):
        """Toggle legend visibility in spread designer"""
        show = self.designer_legend_toggle.GetValue()
        self.designer_legend_panel.Show(show)
        if show:
            self._update_designer_legend()
        self.designer_canvas.GetParent().Layout()
        self.designer_canvas.Refresh()

    def _update_designer_legend(self):
        """Update the legend panel with current positions"""
        # Clear existing legend items
        self.designer_legend_items_sizer.Clear(True)

        # Add legend items for each position
        for i, pos in enumerate(self.designer_positions):
            label = pos.get('label', f'Position {i+1}')
            legend_item = wx.StaticText(self.designer_legend_scroll, label=f"{i + 1}. {label}")
            legend_item.SetForegroundColour(get_wx_color('text_primary'))
            legend_item.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            self.designer_legend_items_sizer.Add(legend_item, 0, wx.ALL, 5)

        self.designer_legend_scroll.SetupScrolling()
        self.designer_legend_panel.Layout()

    def _on_designer_paint(self, event):
        dc = wx.PaintDC(self.designer_canvas)
        dc.SetBackground(wx.Brush(get_wx_color('card_slot')))
        dc.Clear()
        
        for i, pos in enumerate(self.designer_positions):
            x, y = pos['x'], pos['y']
            w, h = pos.get('width', 80), pos.get('height', 120)
            label = pos.get('label', f'Position {i+1}')
            is_rotated = pos.get('rotated', False)

            # Draw rectangle with different color if rotated
            if is_rotated:
                dc.SetBrush(wx.Brush(get_wx_color('accent_dim')))
                dc.SetPen(wx.Pen(get_wx_color('accent'), 3))
            else:
                dc.SetBrush(wx.Brush(get_wx_color('bg_tertiary')))
                dc.SetPen(wx.Pen(get_wx_color('accent'), 2))

            dc.DrawRectangle(int(x), int(y), int(w), int(h))

            # Show position number and label based on legend toggle
            show_legend = self.designer_legend_toggle.GetValue()

            if show_legend:
                # Show only position number when legend is visible
                dc.SetTextForeground(get_wx_color('text_secondary'))
                dc.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                dc.DrawText(str(i + 1), int(x - 12), int(y - 12))
            else:
                # Show label inside card when legend is hidden
                dc.SetTextForeground(get_wx_color('text_primary'))
                dc.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                dc.DrawText(label, int(x + 5), int(y + h//2 - 8))

                dc.SetTextForeground(get_wx_color('text_dim'))
                dc.DrawText(str(i + 1), int(x + 5), int(y + 5))

            # Show rotation indicator
            if is_rotated:
                dc.SetTextForeground(get_wx_color('accent'))
                dc.DrawText("↻", int(x + w - 20), int(y + 5))
    
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
                menu = wx.Menu()

                # Rotate option
                is_rotated = pos.get('rotated', False)
                rotate_item = menu.Append(wx.ID_ANY, "Unrotate Card" if is_rotated else "Rotate Card 90°")
                menu.Bind(wx.EVT_MENU, lambda e: self._toggle_position_rotation(i), rotate_item)

                menu.AppendSeparator()

                # Delete option
                delete_item = menu.Append(wx.ID_ANY, f"Delete '{pos['label']}'")
                menu.Bind(wx.EVT_MENU, lambda e: self._delete_position(i), delete_item)

                self.designer_canvas.PopupMenu(menu)
                menu.Destroy()
                break

    def _toggle_position_rotation(self, idx):
        """Toggle the rotation of a position"""
        current = self.designer_positions[idx].get('rotated', False)
        self.designer_positions[idx]['rotated'] = not current

        # Swap width and height when rotating
        w = self.designer_positions[idx].get('width', 80)
        h = self.designer_positions[idx].get('height', 120)
        self.designer_positions[idx]['width'] = h
        self.designer_positions[idx]['height'] = w

        self._update_designer_legend()
        self.designer_canvas.Refresh()

    def _delete_position(self, idx):
        """Delete a position from the spread"""
        pos = self.designer_positions[idx]
        if wx.MessageBox(f"Delete '{pos['label']}'?", "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            self.designer_positions.pop(idx)
            self._update_designer_legend()
            self.designer_canvas.Refresh()
    
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

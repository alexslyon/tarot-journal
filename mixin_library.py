"""Library panel mixin for MainFrame (decks, cards, search)."""

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb
from PIL import Image
import json
import os
import re
from pathlib import Path

from ui_helpers import logger, _cfg, get_wx_color
from import_presets import COURT_PRESETS, ARCHETYPE_MAPPING_OPTIONS
from card_dialogs import CardViewDialog, CardEditDialog, BatchEditDialog
from rich_text_panel import RichTextPanel


class LibraryMixin:
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
        self.type_filter = wx.Choice(left, choices=['All', 'Tarot', 'Lenormand', 'I Ching', 'Kipper', 'Playing Cards', 'Oracle'])
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

        # Search row
        search_row = wx.BoxSizer(wx.HORIZONTAL)

        # Search control
        self.card_search_ctrl = wx.SearchCtrl(right, size=(200, -1))
        self.card_search_ctrl.SetDescriptiveText("Search cards...")
        self.card_search_ctrl.ShowCancelButton(True)
        self.card_search_ctrl.Bind(wx.EVT_TEXT, self._on_card_search)
        self.card_search_ctrl.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_card_search_clear)
        search_row.Add(self.card_search_ctrl, 1, wx.EXPAND | wx.RIGHT, 10)

        # Scope toggle (Current Deck / All Decks) - empty labels per CLAUDE.md
        self.search_scope_current = wx.RadioButton(right, label="", style=wx.RB_GROUP)
        search_row.Add(self.search_scope_current, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
        current_label = wx.StaticText(right, label="Current Deck")
        current_label.SetForegroundColour(get_wx_color('text_primary'))
        search_row.Add(current_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)

        self.search_scope_all = wx.RadioButton(right, label="")
        search_row.Add(self.search_scope_all, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
        all_label = wx.StaticText(right, label="All Decks")
        all_label.SetForegroundColour(get_wx_color('text_primary'))
        search_row.Add(all_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.search_scope_current.SetValue(True)
        self.search_scope_current.Bind(wx.EVT_RADIOBUTTON, self._on_search_scope_change)
        self.search_scope_all.Bind(wx.EVT_RADIOBUTTON, self._on_search_scope_change)

        # Advanced search toggle button
        self.advanced_search_btn = wx.Button(right, label="Advanced")
        self.advanced_search_btn.Bind(wx.EVT_BUTTON, self._on_toggle_advanced_search)
        search_row.Add(self.advanced_search_btn, 0, wx.ALIGN_CENTER_VERTICAL)

        right_sizer.Add(search_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # Advanced search panel (initially hidden)
        self.advanced_search_panel = wx.Panel(right)
        self.advanced_search_panel.SetBackgroundColour(get_wx_color('bg_secondary'))
        adv_sizer = wx.BoxSizer(wx.VERTICAL)

        # Row 1: Field-specific searches
        adv_row1 = wx.BoxSizer(wx.HORIZONTAL)

        name_label = wx.StaticText(self.advanced_search_panel, label="Name:")
        name_label.SetForegroundColour(get_wx_color('text_primary'))
        adv_row1.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.adv_name_ctrl = wx.TextCtrl(self.advanced_search_panel, size=(100, -1))
        adv_row1.Add(self.adv_name_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)

        arch_label = wx.StaticText(self.advanced_search_panel, label="Archetype:")
        arch_label.SetForegroundColour(get_wx_color('text_primary'))
        adv_row1.Add(arch_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.adv_archetype_ctrl = wx.TextCtrl(self.advanced_search_panel, size=(100, -1))
        adv_row1.Add(self.adv_archetype_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)

        notes_label = wx.StaticText(self.advanced_search_panel, label="Notes contain:")
        notes_label.SetForegroundColour(get_wx_color('text_primary'))
        adv_row1.Add(notes_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.adv_notes_ctrl = wx.TextCtrl(self.advanced_search_panel, size=(100, -1))
        adv_row1.Add(self.adv_notes_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)

        adv_sizer.Add(adv_row1, 0, wx.EXPAND | wx.ALL, 8)

        # Row 2: Filter dropdowns
        adv_row2 = wx.BoxSizer(wx.HORIZONTAL)

        deck_type_label = wx.StaticText(self.advanced_search_panel, label="Deck Type:")
        deck_type_label.SetForegroundColour(get_wx_color('text_primary'))
        adv_row2.Add(deck_type_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        deck_types = ['Any', 'Tarot', 'Lenormand', 'I Ching', 'Kipper', 'Playing Cards', 'Oracle']
        self.adv_deck_type = wx.Choice(self.advanced_search_panel, choices=deck_types)
        self.adv_deck_type.SetSelection(0)
        adv_row2.Add(self.adv_deck_type, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)

        cat_label = wx.StaticText(self.advanced_search_panel, label="Category:")
        cat_label.SetForegroundColour(get_wx_color('text_primary'))
        adv_row2.Add(cat_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        categories = ['Any', 'Major Arcana', 'Minor Arcana', 'Court Cards']
        self.adv_category = wx.Choice(self.advanced_search_panel, choices=categories)
        self.adv_category.SetSelection(0)
        adv_row2.Add(self.adv_category, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)

        suit_label = wx.StaticText(self.advanced_search_panel, label="Suit:")
        suit_label.SetForegroundColour(get_wx_color('text_primary'))
        adv_row2.Add(suit_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        suits = ['Any', 'Wands', 'Cups', 'Swords', 'Pentacles', 'Hearts', 'Diamonds', 'Clubs', 'Spades']
        self.adv_suit = wx.Choice(self.advanced_search_panel, choices=suits)
        self.adv_suit.SetSelection(0)
        adv_row2.Add(self.adv_suit, 0, wx.ALIGN_CENTER_VERTICAL)

        adv_sizer.Add(adv_row2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Row 3: Boolean filters and buttons
        adv_row3 = wx.BoxSizer(wx.HORIZONTAL)

        # Has notes checkbox (empty label + StaticText per CLAUDE.md)
        self.adv_has_notes_cb = wx.CheckBox(self.advanced_search_panel, label="")
        adv_row3.Add(self.adv_has_notes_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
        has_notes_label = wx.StaticText(self.advanced_search_panel, label="Has notes")
        has_notes_label.SetForegroundColour(get_wx_color('text_primary'))
        adv_row3.Add(has_notes_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)

        # Has image checkbox
        self.adv_has_image_cb = wx.CheckBox(self.advanced_search_panel, label="")
        adv_row3.Add(self.adv_has_image_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
        has_image_label = wx.StaticText(self.advanced_search_panel, label="Has image")
        has_image_label.SetForegroundColour(get_wx_color('text_primary'))
        adv_row3.Add(has_image_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 25)

        # Sort by
        sort_label = wx.StaticText(self.advanced_search_panel, label="Sort by:")
        sort_label.SetForegroundColour(get_wx_color('text_primary'))
        adv_row3.Add(sort_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        sort_options = ['Name', 'Deck', 'Card Order']
        self.adv_sort_by = wx.Choice(self.advanced_search_panel, choices=sort_options)
        self.adv_sort_by.SetSelection(0)
        adv_row3.Add(self.adv_sort_by, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)

        # Search and Clear buttons
        adv_search_btn = wx.Button(self.advanced_search_panel, label="Search")
        adv_search_btn.Bind(wx.EVT_BUTTON, self._on_advanced_search)
        adv_row3.Add(adv_search_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        adv_clear_btn = wx.Button(self.advanced_search_panel, label="Clear")
        adv_clear_btn.Bind(wx.EVT_BUTTON, self._on_advanced_search_clear)
        adv_row3.Add(adv_clear_btn, 0, wx.ALIGN_CENTER_VERTICAL)

        adv_sizer.Add(adv_row3, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.advanced_search_panel.SetSizer(adv_sizer)
        self.advanced_search_panel.Hide()
        right_sizer.Add(self.advanced_search_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

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
        self._filter_group_map = {}  # Map filter index -> group_id
        self.card_filter_choice = wx.Choice(right, choices=self.card_filter_names)
        self.card_filter_choice.SetSelection(0)
        self.card_filter_choice.Bind(wx.EVT_CHOICE, self._on_card_filter_change)
        header_row.Add(self.card_filter_choice, 0, wx.ALIGN_CENTER_VERTICAL)

        self.groups_btn = wx.Button(right, label="Groups...")
        self.groups_btn.SetBackgroundColour(get_wx_color('bg_secondary'))
        self.groups_btn.SetForegroundColour(get_wx_color('text_primary'))
        self.groups_btn.Bind(wx.EVT_BUTTON, self._on_manage_groups)
        header_row.Add(self.groups_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)

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
        
        splitter.SplitVertically(left, right, _cfg.get('panels', 'cards_splitter', 280))
        
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(splitter, 1, wx.EXPAND)
        panel.SetSizer(panel_sizer)
        
        return panel

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
                'type': deck.get('cartomancy_type_names', deck['cartomancy_type_name']),
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

        # Card back image for deck thumbnails
        _deck_back_sz = _cfg.get('images', 'deck_back_max', [100, 150])
        max_width, max_height = _deck_back_sz[0], _deck_back_sz[1]
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

    def _select_deck_by_id(self, deck_id):
        """Select a deck in the list by its ID"""
        for i in range(self.deck_list.GetItemCount()):
            if self.deck_list.GetItemData(i) == deck_id:
                self.deck_list.Select(i)
                self.deck_list.EnsureVisible(i)
                return True
        return False

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

        cards = list(self.db.get_cards(deck_id))  # Convert to list immediately to avoid iterator exhaustion
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
            # Check if this is a Gnostic/Eternal Tarot deck (cards have "Minor Arcana" as suit)
            is_gnostic = any(card['suit'] == 'Minor Arcana' for card in cards)
            if is_gnostic:
                # Gnostic/Eternal Tarot uses Major Arcana + Minor Arcana
                new_choices = ['All', 'Major Arcana', 'Minor Arcana']
            else:
                # Standard Tarot uses Major Arcana + tarot suits
                new_choices = ['All', 'Major Arcana',
                              suit_names.get('wands', 'Wands'),
                              suit_names.get('cups', 'Cups'),
                              suit_names.get('swords', 'Swords'),
                              suit_names.get('pentacles', 'Pentacles')]

        # Append custom groups for this deck
        self._filter_group_map = {}
        groups = self.db.get_card_groups(deck_id)
        if groups:
            new_choices.append("───────────")
            for group in groups:
                self._filter_group_map[len(new_choices)] = group['id']
                new_choices.append(group['name'])

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
            self._current_cards_sorted = self._sort_playing_cards(cards, suit_names)
            self._current_cards_categorized = self._categorize_playing_cards(self._current_cards_sorted, suit_names)
        elif self._current_deck_type == 'Lenormand':
            self._current_cards_sorted = self._sort_lenormand_cards(cards)
            self._current_cards_categorized = self._categorize_lenormand_cards(self._current_cards_sorted)
        elif self._current_deck_type == 'Kipper':
            self._current_cards_sorted = self._sort_kipper_cards(cards)
            self._current_cards_categorized = {'All': self._current_cards_sorted}
        else:
            self._current_cards_sorted = self._sort_cards(cards, suit_names)
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
        elif filter_name == "───────────":
            # Separator line — treat as "All"
            cards_to_show = self._current_cards_sorted
        elif hasattr(self, '_filter_group_map') and filter_idx in self._filter_group_map:
            # Custom group filter
            group_id = self._filter_group_map[filter_idx]
            group_card_ids = set(self.db.get_cards_in_group(group_id))
            cards_to_show = [c for c in self._current_cards_sorted if c['id'] in group_card_ids]
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
            elif filter_name == 'Minor Arcana':
                # Gnostic/Eternal Tarot uses Minor Arcana as a category
                cards_to_show = self._current_cards_categorized.get('Minor Arcana', [])
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
        # Check if this is a Gnostic/Eternal Tarot deck
        is_gnostic = any(card['suit'] == 'Minor Arcana' for card in cards)

        if is_gnostic:
            # Gnostic/Eternal Tarot: categorize by suit field (Major Arcana / Minor Arcana)
            categorized = {
                'Major Arcana': [],
                'Minor Arcana': [],
            }
            for card in cards:
                suit = card['suit'] or ''
                if suit == 'Major Arcana':
                    categorized['Major Arcana'].append(card)
                elif suit == 'Minor Arcana':
                    categorized['Minor Arcana'].append(card)
            return categorized

        # Standard Tarot categorization
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
            card_suit = card['suit'].lower() if card['suit'] else ''

            # First check the suit field directly
            if card_suit == 'major arcana':
                categorized['Major Arcana'].append(card)
                continue

            # Check if suit field matches a tarot suit
            if card_suit in suit_map:
                categorized[suit_map[card_suit]].append(card)
                continue

            # Fallback: Check major arcana by name
            if name_lower in major_arcana_names:
                categorized['Major Arcana'].append(card)
                continue

            # Check suits by name pattern
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
                logger.warning(
                    f"Failed to generate thumbnail for: {card.get('name', 'unknown')} "
                    f"(path: {card['image_path']}, exists: {os.path.exists(card['image_path'])})"
                )
            if thumb_path:
                try:
                    img = wx.Image(thumb_path, wx.BITMAP_TYPE_ANY)
                    # Scale to fit while preserving aspect ratio
                    _gallery_sz = _cfg.get('images', 'card_gallery_max', [200, 300])
                    max_width, max_height = _gallery_sz[0], _gallery_sz[1]
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
                    logger.warning(
                        f"Error loading thumbnail for card {card.get('name', 'unknown')}: {e} "
                        f"(image: {card['image_path']}, thumb: {thumb_path})"
                    )
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
            # Skip separator selection — reset to "All"
            filter_idx = self.card_filter_choice.GetSelection()
            if 0 <= filter_idx < len(self.card_filter_names):
                if self.card_filter_names[filter_idx] == "───────────":
                    self.card_filter_choice.SetSelection(0)
            self._display_filtered_cards()
        event.Skip()

    # ═══════════════════════════════════════════
    # CARD GROUP MANAGEMENT
    # ═══════════════════════════════════════════

    def _on_manage_groups(self, event):
        """Open the group management dialog for the current deck"""
        deck_id = self._current_deck_id_for_cards
        if not deck_id:
            wx.MessageBox("Select a deck first.", "No Deck", wx.OK | wx.ICON_INFORMATION)
            return

        deck = self.db.get_deck(deck_id)
        deck_name = deck['name'] if deck else "Deck"

        dlg = wx.Dialog(self, title=f"Manage Groups — {deck_name}", size=(500, 350))
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))
        sizer = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(dlg, label="Custom card groupings for this deck.\nCards can belong to multiple groups.")
        info.SetForegroundColour(get_wx_color('text_secondary'))
        sizer.Add(info, 0, wx.ALL, 10)

        groups_list = wx.ListCtrl(dlg, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        groups_list.SetBackgroundColour(get_wx_color('bg_secondary'))
        groups_list.SetTextColour(get_wx_color('text_primary'))
        groups_list.InsertColumn(0, "Name", width=200)
        groups_list.InsertColumn(1, "Color", width=80)
        groups_list.InsertColumn(2, "Cards", width=60)
        sizer.Add(groups_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        def refresh_list():
            groups_list.DeleteAllItems()
            groups = self.db.get_card_groups(deck_id)
            for i, group in enumerate(groups):
                idx = groups_list.InsertItem(i, group['name'])
                groups_list.SetItem(idx, 1, group['color'])
                count = len(self.db.get_cards_in_group(group['id']))
                groups_list.SetItem(idx, 2, str(count))
                groups_list.SetItemData(idx, group['id'])

        refresh_list()

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        add_btn = wx.Button(dlg, label="+ Add Group")
        add_btn.SetBackgroundColour(get_wx_color('bg_secondary'))
        add_btn.SetForegroundColour(get_wx_color('text_primary'))
        def on_add(evt):
            result = self._show_tag_dialog(dlg, "Add Group")
            if result:
                try:
                    self.db.add_card_group(deck_id, result['name'], result['color'])
                    refresh_list()
                except Exception as e:
                    wx.MessageBox(f"Could not add group: {e}", "Error", wx.OK | wx.ICON_ERROR)
        add_btn.Bind(wx.EVT_BUTTON, on_add)
        btn_sizer.Add(add_btn, 0, wx.RIGHT, 5)

        edit_btn = wx.Button(dlg, label="Edit")
        edit_btn.SetBackgroundColour(get_wx_color('bg_secondary'))
        edit_btn.SetForegroundColour(get_wx_color('text_primary'))
        def on_edit(evt):
            sel = groups_list.GetFirstSelected()
            if sel == -1:
                wx.MessageBox("Select a group to edit.", "No Selection", wx.OK | wx.ICON_INFORMATION)
                return
            group_id = groups_list.GetItemData(sel)
            group = self.db.get_card_group(group_id)
            if not group:
                return
            result = self._show_tag_dialog(dlg, "Edit Group", group['name'], group['color'])
            if result:
                try:
                    self.db.update_card_group(group_id, result['name'], result['color'])
                    refresh_list()
                except Exception as e:
                    wx.MessageBox(f"Could not update group: {e}", "Error", wx.OK | wx.ICON_ERROR)
        edit_btn.Bind(wx.EVT_BUTTON, on_edit)
        groups_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, on_edit)
        btn_sizer.Add(edit_btn, 0, wx.RIGHT, 5)

        delete_btn = wx.Button(dlg, label="Delete")
        delete_btn.SetBackgroundColour(get_wx_color('bg_secondary'))
        delete_btn.SetForegroundColour(get_wx_color('text_primary'))
        def on_delete(evt):
            sel = groups_list.GetFirstSelected()
            if sel == -1:
                wx.MessageBox("Select a group to delete.", "No Selection", wx.OK | wx.ICON_INFORMATION)
                return
            group_id = groups_list.GetItemData(sel)
            if wx.MessageBox(
                "Delete this group? Cards will be removed from it but not deleted.",
                "Confirm Delete",
                wx.YES_NO | wx.ICON_WARNING
            ) == wx.YES:
                self.db.delete_card_group(group_id)
                refresh_list()
        delete_btn.Bind(wx.EVT_BUTTON, on_delete)
        btn_sizer.Add(delete_btn, 0)

        btn_sizer.AddSpacer(20)

        up_btn = wx.Button(dlg, label="\u25B2 Up")
        up_btn.SetBackgroundColour(get_wx_color('bg_secondary'))
        up_btn.SetForegroundColour(get_wx_color('text_primary'))
        def on_move_up(evt):
            sel = groups_list.GetFirstSelected()
            if sel <= 0:
                return
            id_sel = groups_list.GetItemData(sel)
            id_above = groups_list.GetItemData(sel - 1)
            self.db.swap_card_group_order(id_sel, id_above)
            refresh_list()
            groups_list.Select(sel - 1)
            groups_list.EnsureVisible(sel - 1)
        up_btn.Bind(wx.EVT_BUTTON, on_move_up)
        btn_sizer.Add(up_btn, 0, wx.RIGHT, 5)

        down_btn = wx.Button(dlg, label="\u25BC Down")
        down_btn.SetBackgroundColour(get_wx_color('bg_secondary'))
        down_btn.SetForegroundColour(get_wx_color('text_primary'))
        def on_move_down(evt):
            sel = groups_list.GetFirstSelected()
            if sel == -1 or sel >= groups_list.GetItemCount() - 1:
                return
            id_sel = groups_list.GetItemData(sel)
            id_below = groups_list.GetItemData(sel + 1)
            self.db.swap_card_group_order(id_sel, id_below)
            refresh_list()
            groups_list.Select(sel + 1)
            groups_list.EnsureVisible(sel + 1)
        down_btn.Bind(wx.EVT_BUTTON, on_move_down)
        btn_sizer.Add(down_btn, 0)

        sizer.Add(btn_sizer, 0, wx.ALL, 10)

        close_btn = wx.Button(dlg, wx.ID_CLOSE, "Close")
        close_btn.SetBackgroundColour(get_wx_color('bg_secondary'))
        close_btn.SetForegroundColour(get_wx_color('text_primary'))
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: dlg.EndModal(wx.ID_CLOSE))
        sizer.Add(close_btn, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)

        dlg.SetSizer(sizer)
        dlg.ShowModal()
        dlg.Destroy()

        # Refresh the filter dropdown to reflect group changes
        if self._current_deck_id_for_cards:
            self._refresh_cards_display(self._current_deck_id_for_cards)

    # ═══════════════════════════════════════════
    # CARD SEARCH METHODS
    # ═══════════════════════════════════════════

    def _on_card_search(self, event):
        """Handle card search input - real-time filtering"""
        query = self.card_search_ctrl.GetValue().strip()

        if not query:
            # Empty search - restore normal view
            if self.search_scope_current.GetValue():
                if hasattr(self, '_current_deck_id_for_cards') and self._current_deck_id_for_cards:
                    self._refresh_cards_display(self._current_deck_id_for_cards)
            else:
                self._clear_search_results()
            return

        if self.search_scope_all.GetValue():
            self._perform_all_decks_search(query)
        else:
            self._perform_current_deck_search(query)

    def _on_card_search_clear(self, event):
        """Handle clearing the search"""
        self.card_search_ctrl.SetValue("")
        if self.search_scope_current.GetValue():
            if hasattr(self, '_current_deck_id_for_cards') and self._current_deck_id_for_cards:
                self._refresh_cards_display(self._current_deck_id_for_cards)
        else:
            self._clear_search_results()

    def _on_search_scope_change(self, event):
        """Handle scope toggle change"""
        query = self.card_search_ctrl.GetValue().strip()
        if query:
            self._on_card_search(None)
        else:
            if self.search_scope_current.GetValue():
                if hasattr(self, '_current_deck_id_for_cards') and self._current_deck_id_for_cards:
                    self._refresh_cards_display(self._current_deck_id_for_cards)

    def _on_toggle_advanced_search(self, event):
        """Toggle advanced search panel visibility"""
        if self.advanced_search_panel.IsShown():
            self.advanced_search_panel.Hide()
            self.advanced_search_btn.SetLabel("Advanced")
        else:
            self.advanced_search_panel.Show()
            self.advanced_search_btn.SetLabel("Simple")

        # Refresh layout
        self.advanced_search_panel.GetParent().Layout()

    def _on_advanced_search(self, event):
        """Perform advanced search with all filters"""
        # Get simple search query if present
        query = self.card_search_ctrl.GetValue().strip() or None

        # Also check advanced text fields
        name_query = self.adv_name_ctrl.GetValue().strip()
        archetype_query = self.adv_archetype_ctrl.GetValue().strip() or None
        notes_query = self.adv_notes_ctrl.GetValue().strip()

        # Combine simple search with name field
        if name_query:
            query = name_query

        # If notes query provided, add to general query
        if notes_query and query:
            query = query  # Notes are searched via general query
        elif notes_query:
            query = notes_query

        # Deck ID (None for all decks when scope is "All")
        deck_id = None
        if self.search_scope_current.GetValue() and hasattr(self, '_current_deck_id_for_cards'):
            deck_id = self._current_deck_id_for_cards

        # Deck type
        deck_type_idx = self.adv_deck_type.GetSelection()
        deck_type = None if deck_type_idx == 0 else self.adv_deck_type.GetString(deck_type_idx)

        # Category
        cat_idx = self.adv_category.GetSelection()
        category = None if cat_idx == 0 else self.adv_category.GetString(cat_idx)

        # Suit
        suit_idx = self.adv_suit.GetSelection()
        suit = None if suit_idx == 0 else self.adv_suit.GetString(suit_idx)

        # Boolean filters
        has_notes = True if self.adv_has_notes_cb.GetValue() else None
        has_image = True if self.adv_has_image_cb.GetValue() else None

        # Sort
        sort_options = ['name', 'deck', 'card_order']
        sort_by = sort_options[self.adv_sort_by.GetSelection()]

        # Perform search
        cards = self.db.search_cards(
            query=query,
            deck_id=deck_id,
            deck_type=deck_type,
            card_category=category,
            archetype=archetype_query,
            suit=suit,
            has_notes=has_notes,
            has_image=has_image,
            sort_by=sort_by
        )

        # Display results
        show_deck_name = self.search_scope_all.GetValue() or deck_id is None
        self._display_search_results(cards, show_deck_name=show_deck_name)

    def _on_advanced_search_clear(self, event):
        """Clear all advanced search fields"""
        self.adv_name_ctrl.SetValue("")
        self.adv_archetype_ctrl.SetValue("")
        self.adv_notes_ctrl.SetValue("")
        self.adv_deck_type.SetSelection(0)
        self.adv_category.SetSelection(0)
        self.adv_suit.SetSelection(0)
        self.adv_has_notes_cb.SetValue(False)
        self.adv_has_image_cb.SetValue(False)
        self.adv_sort_by.SetSelection(0)

        # Clear simple search too
        self.card_search_ctrl.SetValue("")

        # Refresh display
        if hasattr(self, '_current_deck_id_for_cards') and self._current_deck_id_for_cards:
            self._refresh_cards_display(self._current_deck_id_for_cards)

    def _perform_current_deck_search(self, query):
        """Search within current deck"""
        if not hasattr(self, '_current_deck_id_for_cards') or not self._current_deck_id_for_cards:
            return

        cards = self.db.search_cards(
            query=query,
            deck_id=self._current_deck_id_for_cards
        )

        self._display_search_results(cards, show_deck_name=False)

    def _perform_all_decks_search(self, query):
        """Search across all decks"""
        cards = self.db.search_cards(query=query)
        self._display_search_results(cards, show_deck_name=True)

    def _clear_search_results(self):
        """Clear search results and show default message"""
        self.cards_scroll.DestroyChildren()
        self.cards_sizer = wx.WrapSizer(wx.HORIZONTAL)
        self.cards_scroll.SetSizer(self.cards_sizer)
        self._card_widgets = {}

        self.deck_title.SetLabel("Select a deck or search all decks")
        self.cards_scroll.Layout()

    def _display_search_results(self, cards, show_deck_name=False):
        """Display search results with optional deck name labels"""
        self.cards_scroll.DestroyChildren()
        self.cards_sizer = wx.WrapSizer(wx.HORIZONTAL)
        self.cards_scroll.SetSizer(self.cards_sizer)
        self._card_widgets = {}
        self.selected_card_ids = set()

        result_count = len(cards)
        self.deck_title.SetLabel(f"Search Results ({result_count} card{'s' if result_count != 1 else ''})")

        if not cards:
            no_results = wx.StaticText(self.cards_scroll, label="No cards found matching your search.")
            no_results.SetForegroundColour(get_wx_color('text_secondary'))
            self.cards_sizer.Add(no_results, 0, wx.ALL, 20)
            self.cards_scroll.Layout()
            return

        for card in cards:
            self._create_search_result_widget(card, show_deck_name)

        self.cards_scroll.Layout()
        self.cards_scroll.FitInside()
        self.cards_scroll.SetupScrolling(scrollToTop=True)

    def _create_search_result_widget(self, card, show_deck_name=False):
        """Create a card widget for search results"""
        panel_height = 195 if show_deck_name else 175
        card_panel = wx.Panel(self.cards_scroll)
        card_panel.SetMinSize((130, panel_height))
        card_panel.SetBackgroundColour(get_wx_color('bg_tertiary'))
        card_panel.card_id = card['id']
        card_panel.deck_id = card['deck_id']

        card_sizer = wx.BoxSizer(wx.VERTICAL)

        # Thumbnail
        if card['image_path']:
            thumb_path = self.thumb_cache.get_thumbnail_path(card['image_path'])
            if thumb_path:
                try:
                    img = wx.Image(thumb_path, wx.BITMAP_TYPE_ANY)
                    if img.IsOk():
                        orig_width, orig_height = img.GetWidth(), img.GetHeight()
                        max_width, max_height = 120, 140
                        scale = min(max_width / orig_width, max_height / orig_height)
                        new_width = int(orig_width * scale)
                        new_height = int(orig_height * scale)
                        img = img.Scale(new_width, new_height, wx.IMAGE_QUALITY_HIGH)
                        bmp = wx.StaticBitmap(card_panel, bitmap=wx.Bitmap(img))
                        card_sizer.Add(bmp, 0, wx.ALL | wx.ALIGN_CENTER, 4)
                        bmp.Bind(wx.EVT_LEFT_DOWN, lambda e, c=card: self._on_search_result_click(e, c))
                        bmp.Bind(wx.EVT_LEFT_DCLICK, lambda e, c=card: self._on_search_result_dblclick(e, c))
                    else:
                        self._add_search_placeholder(card_panel, card_sizer, card)
                except Exception:
                    self._add_search_placeholder(card_panel, card_sizer, card)
            else:
                self._add_search_placeholder(card_panel, card_sizer, card)
        else:
            self._add_search_placeholder(card_panel, card_sizer, card)

        # Deck name label (for all-decks search)
        if show_deck_name:
            deck_label = wx.StaticText(card_panel, label=card['deck_name'][:20])
            deck_label.SetForegroundColour(get_wx_color('text_secondary'))
            font = deck_label.GetFont()
            font.SetPointSize(9)
            deck_label.SetFont(font)
            card_sizer.Add(deck_label, 0, wx.ALIGN_CENTER | wx.TOP, 2)
            deck_label.Bind(wx.EVT_LEFT_DOWN, lambda e, c=card: self._on_search_result_click(e, c))
            deck_label.Bind(wx.EVT_LEFT_DCLICK, lambda e, c=card: self._on_search_result_dblclick(e, c))

        # Card name tooltip
        card_panel.SetToolTip(card['name'])

        card_panel.SetSizer(card_sizer)
        card_panel.Bind(wx.EVT_LEFT_DOWN, lambda e, c=card: self._on_search_result_click(e, c))
        card_panel.Bind(wx.EVT_LEFT_DCLICK, lambda e, c=card: self._on_search_result_dblclick(e, c))

        self._card_widgets[card['id']] = card_panel
        self.cards_sizer.Add(card_panel, 0, wx.ALL, 6)

    def _add_search_placeholder(self, parent, sizer, card):
        """Add placeholder for card without image in search results"""
        placeholder = wx.StaticText(parent, label="🂠", size=(100, 120))
        placeholder.SetFont(wx.Font(48, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        placeholder.SetForegroundColour(get_wx_color('text_dim'))
        sizer.Add(placeholder, 0, wx.ALL | wx.ALIGN_CENTER, 4)
        placeholder.Bind(wx.EVT_LEFT_DOWN, lambda e, c=card: self._on_search_result_click(e, c))
        placeholder.Bind(wx.EVT_LEFT_DCLICK, lambda e, c=card: self._on_search_result_dblclick(e, c))

    def _on_search_result_click(self, event, card):
        """Handle click on search result - select card"""
        card_id = card['id']

        # Clear previous selection
        for cid, widget in self._card_widgets.items():
            widget.SetBackgroundColour(get_wx_color('bg_tertiary'))
            widget.Refresh()

        # Highlight selected
        self.selected_card_ids = {card_id}
        if card_id in self._card_widgets:
            self._card_widgets[card_id].SetBackgroundColour(get_wx_color('accent_dim'))
            self._card_widgets[card_id].Refresh()

    def _on_search_result_dblclick(self, event, card):
        """Handle double-click on search result - navigate to card's deck and view"""
        deck_id = card['deck_id']
        card_id = card['id']

        # Clear search
        self.card_search_ctrl.SetValue("")
        self.search_scope_current.SetValue(True)

        # Select deck in list
        self._select_deck_by_id(deck_id)

        # View the card
        self._on_view_card(None, card_id)

    def _select_deck_by_id(self, deck_id):
        """Select a deck in the deck list by ID"""
        if hasattr(self, '_deck_view_mode') and self._deck_view_mode == 'image':
            # Image view mode
            if hasattr(self, '_deck_image_widgets'):
                for did, widget in self._deck_image_widgets.items():
                    if did == deck_id:
                        # Simulate click
                        self._selected_deck_id = deck_id
                        self._current_deck_id_for_cards = deck_id
                        self._refresh_cards_display(deck_id)
                        break
        else:
            # List view mode
            for i in range(self.deck_list.GetItemCount()):
                if self.deck_list.GetItemData(i) == deck_id:
                    self.deck_list.Select(i)
                    self.deck_list.EnsureVisible(i)
                    self._selected_deck_id = deck_id
                    self._current_deck_id_for_cards = deck_id
                    self._refresh_cards_display(deck_id)
                    break

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

                # Create a dialog with options
                overwrite_dlg = wx.Dialog(dlg, title="Auto-assign Metadata", size=(450, 280))
                overwrite_dlg.SetBackgroundColour(get_wx_color('bg_primary'))
                dlg_sizer = wx.BoxSizer(wx.VERTICAL)

                msg = wx.StaticText(overwrite_dlg,
                    label="This will automatically assign archetype, rank, and suit\n"
                          "to cards based on the selected method.")
                msg.SetForegroundColour(get_wx_color('text_primary'))
                dlg_sizer.Add(msg, 0, wx.ALL, 15)

                # Assignment method radio buttons
                # NOTE: wx.RadioButton labels don't support custom colors on macOS
                # Use empty-label radio buttons with separate StaticText labels
                method_box = wx.StaticBox(overwrite_dlg, label="Assignment Method")
                method_box.SetForegroundColour(get_wx_color('accent'))
                method_sizer = wx.StaticBoxSizer(method_box, wx.VERTICAL)

                method_name_sizer = wx.BoxSizer(wx.HORIZONTAL)
                method_name_rb = wx.RadioButton(overwrite_dlg, label="", style=wx.RB_GROUP)
                method_name_rb.SetValue(True)
                method_name_sizer.Add(method_name_rb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
                method_name_label = wx.StaticText(overwrite_dlg, label="By card name (parse names for rank/suit)")
                method_name_label.SetForegroundColour(get_wx_color('text_primary'))
                method_name_sizer.Add(method_name_label, 0, wx.ALIGN_CENTER_VERTICAL)
                method_sizer.Add(method_name_sizer, 0, wx.ALL, 5)

                method_order_sizer = wx.BoxSizer(wx.HORIZONTAL)
                method_order_rb = wx.RadioButton(overwrite_dlg, label="")
                method_order_sizer.Add(method_order_rb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
                method_order_label = wx.StaticText(overwrite_dlg, label="By sort order (assign sequentially 1, 2, 3...)")
                method_order_label.SetForegroundColour(get_wx_color('text_primary'))
                method_order_sizer.Add(method_order_label, 0, wx.ALIGN_CENTER_VERTICAL)
                method_sizer.Add(method_order_sizer, 0, wx.ALL, 5)

                dlg_sizer.Add(method_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

                # Overwrite checkbox - use separate checkbox and label for macOS
                overwrite_sizer = wx.BoxSizer(wx.HORIZONTAL)
                overwrite_cb = wx.CheckBox(overwrite_dlg, label="")
                overwrite_sizer.Add(overwrite_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
                overwrite_label = wx.StaticText(overwrite_dlg, label="Overwrite existing metadata")
                overwrite_label.SetForegroundColour(get_wx_color('text_primary'))
                overwrite_sizer.Add(overwrite_label, 0, wx.ALIGN_CENTER_VERTICAL)
                dlg_sizer.Add(overwrite_sizer, 0, wx.ALL, 15)

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
                    use_sort_order = method_order_rb.GetValue()
                    overwrite_dlg.Destroy()
                    updated = self.db.auto_assign_deck_metadata(deck_id, overwrite=overwrite,
                                                                 preset_name=preset_name,
                                                                 use_sort_order=use_sort_order)
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

        # Deck Types section - allow multiple types per deck
        deck_types_box = wx.StaticBox(general_panel, label="Deck Types")
        deck_types_box.SetForegroundColour(get_wx_color('accent'))
        deck_types_sizer = wx.StaticBoxSizer(deck_types_box, wx.VERTICAL)

        types_info = wx.StaticText(general_panel, label="Select one or more cartomancy types for this deck:")
        types_info.SetForegroundColour(get_wx_color('text_secondary'))
        deck_types_sizer.Add(types_info, 0, wx.ALL, 10)

        # Get all cartomancy types and current deck types
        all_cart_types = self.db.get_cartomancy_types()
        current_type_ids = {t['id'] for t in deck.get('cartomancy_types', [])}

        # Create checkboxes for each type (empty label + StaticText for macOS)
        dlg._deck_type_checks = {}
        types_grid = wx.FlexGridSizer(cols=2, hgap=20, vgap=5)
        for ct in all_cart_types:
            cb_sizer = wx.BoxSizer(wx.HORIZONTAL)
            cb = wx.CheckBox(general_panel, label="")
            cb.SetValue(ct['id'] in current_type_ids)
            cb_sizer.Add(cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            cb_label = wx.StaticText(general_panel, label=ct['name'])
            cb_label.SetForegroundColour(get_wx_color('text_primary'))
            cb_sizer.Add(cb_label, 0, wx.ALIGN_CENTER_VERTICAL)
            types_grid.Add(cb_sizer, 0, wx.EXPAND)
            dlg._deck_type_checks[ct['id']] = cb

        deck_types_sizer.Add(types_grid, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        general_sizer.Add(deck_types_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

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
        _back_preview_sz = _cfg.get('images', 'deck_back_preview_max', [150, 225])
        max_back_width, max_back_height = _back_preview_sz[0], _back_preview_sz[1]
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
                except Exception as e:
                    logger.debug("Could not convert image to bitmap: %s", e)
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
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning("Failed to parse field_options in list: %s", e)
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
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning("Failed to parse existing field_options: %s", e)

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

            # Update deck types (multiple types per deck)
            selected_type_ids = []
            for type_id, cb in dlg._deck_type_checks.items():
                if cb.GetValue():
                    selected_type_ids.append(type_id)
            if selected_type_ids:
                self.db.set_deck_types(deck_id, selected_type_ids)
            else:
                # At least one type must be selected - keep original
                wx.MessageBox("At least one deck type must be selected.\nTypes were not changed.",
                             "Warning", wx.OK | wx.ICON_WARNING)

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

                # Create custom fields defined by the preset
                preset_name = preset_choice.GetStringSelection()
                if preset and preset.get('custom_fields'):
                    for idx, field_def in enumerate(preset['custom_fields']):
                        self.db.add_deck_custom_field(
                            deck_id,
                            field_def['name'],
                            field_def.get('type', 'text'),
                            field_def.get('options'),
                            idx
                        )

                # Use the metadata-aware import to get archetype, rank, suit
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
                        'custom_fields': card_info.get('custom_fields'),
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

    def _show_fullsize_image(self, image_path, title="Image"):
        """Show a full-size image in a resizable dialog"""
        from PIL import ImageOps

        try:
            pil_img = Image.open(image_path)
            pil_img = ImageOps.exif_transpose(pil_img)
            orig_width, orig_height = pil_img.size
        except Exception as e:
            wx.MessageBox(f"Could not load image: {e}", "Error", wx.OK | wx.ICON_ERROR)
            return

        # Get screen size to limit dialog size
        display = wx.Display(wx.Display.GetFromWindow(self))
        screen_rect = display.GetClientArea()
        max_dlg_width = int(screen_rect.width * 0.85)
        max_dlg_height = int(screen_rect.height * 0.85)

        # Calculate initial size - fit image to screen with some padding
        padding = 60
        scale = min((max_dlg_width - padding) / orig_width, (max_dlg_height - padding) / orig_height, 1.0)
        initial_width = int(orig_width * scale) + padding
        initial_height = int(orig_height * scale) + padding

        dlg = wx.Dialog(self, title=title, size=(initial_width, initial_height),
                       style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        dlg.SetBackgroundColour(get_wx_color('bg_primary'))

        # Use a scrolled window to allow viewing full image if larger than dialog
        scroll = wx.ScrolledWindow(dlg)
        scroll.SetBackgroundColour(get_wx_color('bg_primary'))
        scroll.SetScrollRate(10, 10)

        # Store original image for resizing
        dlg._pil_img = pil_img
        dlg._scroll = scroll
        dlg._bitmap = None

        def update_image():
            """Update the displayed image based on dialog size"""
            dlg_width, dlg_height = dlg.GetClientSize()
            img_width, img_height = dlg._pil_img.size

            # Scale image to fit dialog while preserving aspect ratio
            scale = min((dlg_width - 20) / img_width, (dlg_height - 20) / img_height, 1.0)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            # Resize and convert
            scaled_img = dlg._pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            if scaled_img.mode != 'RGB':
                scaled_img = scaled_img.convert('RGB')

            wx_img = wx.Image(new_width, new_height)
            wx_img.SetData(scaled_img.tobytes())

            # Update or create bitmap
            if dlg._bitmap:
                dlg._bitmap.SetBitmap(wx.Bitmap(wx_img))
            else:
                dlg._bitmap = wx.StaticBitmap(scroll, bitmap=wx.Bitmap(wx_img))

            scroll.SetVirtualSize((new_width, new_height))
            scroll.Refresh()

        # Initial display
        update_image()

        # Update on resize
        def on_resize(e):
            update_image()
            e.Skip()
        dlg.Bind(wx.EVT_SIZE, on_resize)

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(scroll, 1, wx.EXPAND)
        dlg.SetSizer(sizer)

        # Close on Escape
        def on_key(e):
            if e.GetKeyCode() == wx.WXK_ESCAPE:
                dlg.Close()
            else:
                e.Skip()
        dlg.Bind(wx.EVT_CHAR_HOOK, on_key)

        dlg.ShowModal()
        dlg.Destroy()

    def _on_view_card(self, event, card_id, return_after_edit=False):
        """Show a card detail view with full-size image and all metadata"""
        if not card_id:
            return

        # Get the sorted list of cards for navigation
        card_list = self._current_cards_sorted if hasattr(self, '_current_cards_sorted') else []
        card_ids = [c['id'] for c in card_list]

        # Create and show the dialog
        dlg = CardViewDialog(
            self, self.db, self.thumb_cache, card_id,
            card_ids=card_ids,
            on_fullsize_callback=self._show_fullsize_image
        )

        result = dlg.ShowModal()
        final_card_id = dlg.get_current_card_id()
        edit_requested = dlg.edit_requested
        dlg.Destroy()

        # Handle edit request
        if edit_requested:
            self._on_edit_card(None, final_card_id, return_to_view=True)

    def _on_edit_card(self, event, card_id=None, return_to_view=False, selected_tab=0, dialog_pos=None, dialog_size=None):
        """Edit a card using the CardEditDialog, or BatchEditDialog for multiple cards"""
        # Batch edit: multiple cards selected and no specific card_id passed
        if card_id is None and len(self.selected_card_ids) > 1:
            # Sort selected cards in deck order so thumbnails appear consistently
            card_list = self._current_cards_sorted if hasattr(self, '_current_cards_sorted') else []
            deck_order = [c['id'] for c in card_list]
            sorted_ids = sorted(self.selected_card_ids, key=lambda cid: deck_order.index(cid) if cid in deck_order else cid)

            # Get deck_id from the first selected card
            first_card = self.db.get_card_with_metadata(sorted_ids[0])
            if not first_card:
                return
            deck_id = first_card['deck_id']

            dlg = BatchEditDialog(self, self.db, self.thumb_cache, sorted_ids, deck_id)
            result = dlg.ShowModal()
            applied = dlg.applied
            dlg.Destroy()

            if applied:
                self._refresh_cards_display(deck_id, preserve_scroll=True)
            return

        if card_id is None:
            # Get first selected card
            if self.selected_card_ids:
                card_id = next(iter(self.selected_card_ids))
            else:
                card_id = None

        if not card_id:
            wx.MessageBox("Select a card to edit.", "No Card", wx.OK | wx.ICON_INFORMATION)
            return

        # Get card with full metadata first
        card = self.db.get_card_with_metadata(card_id)
        if not card:
            return

        deck_id = card['deck_id']
        if not deck_id:
            return

        # Get the sorted list of cards for navigation
        card_list = self._current_cards_sorted if hasattr(self, '_current_cards_sorted') else []
        card_ids = [c['id'] for c in card_list]

        # Create refresh callback
        def refresh_callback():
            self._refresh_cards_display(deck_id, preserve_scroll=True)

        # Create and show the dialog
        dlg = CardEditDialog(
            self, self.db, self.thumb_cache, card_id,
            card_ids=card_ids,
            on_refresh_callback=refresh_callback,
            selected_tab=selected_tab
        )

        result = dlg.ShowModal()
        final_card_id = dlg.get_current_card_id()
        save_requested = dlg.save_requested
        dlg.Destroy()

        # Refresh display after save
        if save_requested:
            self._refresh_cards_display(deck_id, preserve_scroll=True)

        # Return to card view if requested
        if return_to_view:
            self._on_view_card(None, final_card_id)

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


"""Journal panel and event handlers mixin for MainFrame."""

import json
import os
from datetime import datetime

import wx
import wx.lib.scrolledpanel as scrolled

from ui_helpers import logger, _cfg, get_wx_color
from rich_text_panel import RichTextPanel, RichTextViewer
from image_utils import load_and_scale_image, load_for_spread_display


class JournalMixin:
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

        splitter.SplitVertically(left, self.viewer_panel, _cfg.get('panels', 'journal_splitter', 300))

        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(splitter, 1, wx.EXPAND)
        panel.SetSizer(panel_sizer)

        return panel

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
                except (ValueError, TypeError) as e:
                    logger.debug("Could not parse reading datetime: %s", e)
                    date_str = reading_dt[:16] if reading_dt else ''
            elif entry['created_at']:
                date_str = entry['created_at'][:10]
            else:
                date_str = ''
            title = entry['title'] or '(Untitled)'
            idx = self.entry_list.InsertItem(self.entry_list.GetItemCount(), date_str)
            self.entry_list.SetItem(idx, 1, title)
            self.entry_list.SetItemData(idx, entry['id'])


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


    def _update_spread_choice(self):
        """Update the spread map for use in dialogs"""
        spreads = self.db.get_spreads()
        self._spread_map = {}
        for spread in spreads:
            self._spread_map[spread['name']] = spread['id']


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
            except (ValueError, TypeError) as e:
                logger.debug("Could not parse reading datetime: %s", e)
                date_str = reading_dt[:16] if reading_dt else ''
        elif entry['created_at']:
            try:
                dt = datetime.fromisoformat(entry['created_at'])
                date_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except (ValueError, TypeError) as e:
                logger.debug("Could not parse entry created_at: %s", e)
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

                        # Find card for this position - check position_index first, fall back to array index
                        card_data = None
                        for cd in cards_used:
                            if isinstance(cd, dict) and cd.get('position_index') == i:
                                card_data = cd
                                break
                        # Fall back to array index for old entries without position_index
                        if card_data is None and i < len(cards_used):
                            cd = cards_used[i]
                            # Only use array index if no position_index fields exist in any card
                            if not any(isinstance(c, dict) and 'position_index' in c for c in cards_used):
                                card_data = cd

                        if card_data is not None:
                            # Handle both old format (string) and new format (dict)
                            if isinstance(card_data, str):
                                card_name = card_data
                                is_reversed = False
                            else:
                                card_name = card_data.get('name', '')
                                is_reversed = card_data.get('reversed', False)

                            # Get image path and card ID using multi-deck aware function
                            image_path, card_id = get_card_info(card_data, card_name)
                            image_placed = False

                            wx_img = load_for_spread_display(
                                image_path, (w, h),
                                is_reversed=is_reversed,
                                is_position_rotated=is_position_rotated
                            )
                            if wx_img:
                                target_w, target_h = wx_img.GetWidth(), wx_img.GetHeight()
                                bmp = wx.StaticBitmap(spread_panel, bitmap=wx.Bitmap(wx_img))
                                img_x = x + (w - target_w) // 2
                                img_y = y + (h - target_h) // 2
                                bmp.SetPosition((img_x, img_y))

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
                                    if card_id:
                                        r_label.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card_id: self._on_view_card(None, cid))

                                image_placed = True

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

                            # Add position number for empty slots too
                            pos_num = wx.StaticText(spread_panel, label=str(i + 1))
                            pos_num.SetForegroundColour(get_wx_color('text_secondary'))
                            pos_num.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                            pos_num.SetPosition((x - 12, y - 12))
                            pos_num.Hide()
                            spread_panel._position_numbers.append(pos_num)

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

                        wx_bitmap = load_and_scale_image(image_path, (80, 110), as_wx_bitmap=True)
                        if wx_bitmap:
                            bmp = wx.StaticBitmap(card_panel, bitmap=wx_bitmap)
                            card_sizer_inner.Add(bmp, 0, wx.ALL | wx.ALIGN_CENTER, 2)
                            # Bind double-click on image too
                            if card_id:
                                bmp.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card_id: self._on_view_card(None, cid))

                        name_label = wx.StaticText(card_panel, label=card_name[:15])
                        name_label.SetForegroundColour(get_wx_color('text_primary'))
                        name_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                        card_sizer_inner.Add(name_label, 0, wx.ALL | wx.ALIGN_CENTER, 2)
                        # Bind double-click on label too
                        if card_id:
                            name_label.Bind(wx.EVT_LEFT_DCLICK, lambda e, cid=card_id: self._on_view_card(None, cid))

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
                except (ValueError, TypeError) as e:
                    logger.debug("Could not parse note date: %s", e)
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
        except (ValueError, TypeError) as e:
            logger.debug("Could not parse note date: %s", e)
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
            except (ValueError, TypeError) as e:
                logger.debug("Could not parse existing reading datetime: %s", e)
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

        # Load existing querent/reader from entry, or apply defaults for new entries
        existing_querent_id = entry['querent_id'] if 'querent_id' in entry.keys() else None
        existing_reader_id = entry['reader_id'] if 'reader_id' in entry.keys() else None

        if existing_querent_id and existing_querent_id in profile_ids:
            querent_choice.SetSelection(profile_ids.index(existing_querent_id))
        elif is_new:
            # Apply default querent for new entries
            default_querent_id = self.db.get_default_querent()
            if default_querent_id and default_querent_id in profile_ids:
                querent_choice.SetSelection(profile_ids.index(default_querent_id))

        if existing_reader_id and existing_reader_id in profile_ids:
            reader_choice.SetSelection(profile_ids.index(existing_reader_id))
        elif is_new:
            # Apply default reader for new entries
            default_reader_id = self.db.get_default_reader()
            if default_reader_id and default_reader_id in profile_ids:
                reader_choice.SetSelection(profile_ids.index(default_reader_id))

        # Check "same as querent" checkbox
        if existing_querent_id and existing_querent_id == existing_reader_id:
            same_as_querent_cb.SetValue(True)
            on_same_as_querent(None)
        elif is_new and self.db.get_default_reader_same_as_querent():
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
                        card_deck_name = reading['deck_name'] if reading['deck_name'] else ''
                    else:
                        card_name = card_data.get('name', '')
                        reversed_state = card_data.get('reversed', False)
                        # Multi-deck format includes deck_id per card
                        card_deck_id = card_data.get('deck_id', dlg._selected_deck_id)
                        card_deck_name = card_data.get('deck_name', reading['deck_name'] if reading['deck_name'] else '')

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

                    # First, check for spread-specific default deck
                    spread_default_deck_id = spread['default_deck_id'] if 'default_deck_id' in spread.keys() else None
                    if spread_default_deck_id:
                        for name, info in dlg._all_decks.items():
                            if info['id'] == spread_default_deck_id:
                                idx = deck_choice.FindString(name)
                                if idx != wx.NOT_FOUND:
                                    deck_choice.SetSelection(idx)
                                    dlg._selected_deck_id = spread_default_deck_id
                                break
                    # Fall back to global default based on first allowed type
                    elif allowed_types:
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

                    is_reversed = card_data.get('reversed', False)
                    wx_img = load_for_spread_display(
                        image_path, (w, h),
                        is_reversed=is_reversed,
                        is_position_rotated=is_position_rotated
                    )
                    if wx_img:
                        target_w, target_h = wx_img.GetWidth(), wx_img.GetHeight()
                        bmp = wx.Bitmap(wx_img)
                        img_x = x + (w - target_w) // 2
                        img_y = y + (h - target_h) // 2
                        dc.DrawBitmap(bmp, img_x, img_y)
                        dc.SetBrush(wx.TRANSPARENT_BRUSH)
                        dc.SetPen(wx.Pen(get_wx_color('accent'), 2))
                        dc.DrawRectangle(img_x - 1, img_y - 1, target_w + 2, target_h + 2)

                        # Add (R) indicator for reversed cards
                        if is_reversed:
                            dc.SetTextForeground(get_wx_color('accent'))
                            dc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                            dc.DrawText("(R)", img_x + 2, img_y + 2)

                        image_drawn = True

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
                except (ValueError, TypeError) as e:
                    logger.debug("Could not parse time '%s': %s", time_str, e)
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

                # Save cards with reversed state, deck info, and position index
                cards_used = [
                    {
                        'name': c['name'],
                        'reversed': c.get('reversed', False),
                        'deck_id': c.get('deck_id'),
                        'deck_name': c.get('deck_name'),
                        'position_index': pos_idx
                    }
                    for pos_idx, c in dlg._spread_cards.items()
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

                    # First, check for spread-specific default deck
                    spread_default_deck_id = spread['default_deck_id'] if 'default_deck_id' in spread.keys() else None
                    if spread_default_deck_id:
                        for name, info in dlg._all_decks.items():
                            if info['id'] == spread_default_deck_id:
                                idx = deck_choice.FindString(name)
                                if idx != wx.NOT_FOUND:
                                    deck_choice.SetSelection(idx)
                                    dlg._selected_deck_id = spread_default_deck_id
                                break
                    # Fall back to global default based on first allowed type
                    elif allowed_types:
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
                        'deck_name': c.get('deck_name'),
                        'position_index': pos_idx
                    }
                    for pos_idx, c in dlg._spread_cards.items()
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


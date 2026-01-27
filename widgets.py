"""
Custom widgets for Tarot Journal wxPython GUI.
"""

import wx
from ui_helpers import get_wx_color


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
            from wx.lib.buttons import GenButton
            self.dropdown_btn = GenButton(self, label="\u25bc", size=(30, -1))
            self.dropdown_btn.SetBezelWidth(0)
            self.dropdown_btn.SetUseFocusIndicator(False)
            self.dropdown_btn.SetBackgroundColour(get_wx_color('bg_secondary'))
            self.dropdown_btn.SetForegroundColour(get_wx_color('text_primary'))
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
        # Toggle popup - if showing, hide it; otherwise show all archetypes
        if self._popup and self._popup.IsShown():
            self._hide_popup()
        else:
            self._show_suggestions('')
            # Keep focus handling happy
            if self._popup:
                self._listbox.SetFocus()

    def _on_key_down(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self._hide_popup()
        elif event.GetKeyCode() == wx.WXK_DOWN and self._popup and self._popup.IsShown():
            # Move focus to listbox
            if self._listbox.GetItemCount() > 0:
                self._listbox.Select(0)
                self._listbox.SetFocus()
        else:
            event.Skip()

    def _on_focus_lost(self, event):
        # Delay hiding to allow click on popup or dropdown button
        wx.CallLater(200, self._check_and_hide_popup)
        event.Skip()

    def _check_and_hide_popup(self):
        # Don't hide if listbox or dropdown button has focus
        if self._popup and self._popup.IsShown():
            if hasattr(self, '_listbox') and self._listbox.HasFocus():
                return
            if hasattr(self, 'dropdown_btn') and self.dropdown_btn.HasFocus():
                return
            # Check if mouse is over the popup
            mouse_pos = wx.GetMousePosition()
            popup_rect = self._popup.GetScreenRect()
            if popup_rect.Contains(mouse_pos):
                return
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
            # Use ListCtrl for better color support on macOS
            self._listbox = wx.ListCtrl(self._popup, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER)
            self._listbox.SetBackgroundColour(get_wx_color('bg_secondary'))
            self._listbox.SetTextColour(get_wx_color('text_primary'))
            self._listbox.InsertColumn(0, "", width=300)
            # Single click to select (like a normal dropdown)
            self._listbox.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
            self._listbox.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_select)
            self._listbox.Bind(wx.EVT_KEY_DOWN, self._on_listbox_key)
            popup_sizer.Add(self._listbox, 1, wx.EXPAND | wx.ALL, 2)
            self._popup.SetSizer(popup_sizer)

        # Populate listbox
        self._listbox.DeleteAllItems()
        self._archetype_data = []
        for idx, arch in enumerate(results):
            # Format display: "Name (Rank - Suit)" or just "Name"
            display = arch['name']
            if arch['rank'] and arch['suit']:
                display = f"{arch['name']} ({arch['rank']} - {arch['suit']})"
            elif arch['rank']:
                display = f"{arch['name']} ({arch['rank']})"
            self._listbox.InsertItem(idx, display)
            self._archetype_data.append(arch)

        # Position popup below text control
        pos = self.text_ctrl.ClientToScreen(wx.Point(0, self.text_ctrl.GetSize().height))
        width = self.text_ctrl.GetSize().width + 32
        height = min(200, 24 * len(results) + 10)

        self._popup.SetPosition(pos)
        self._popup.SetSize(width, height)
        self._listbox.SetSize(width - 4, height - 4)
        self._listbox.SetColumnWidth(0, width - 24)  # Account for scrollbar
        self._popup.Show()

    def _hide_popup(self):
        if self._popup:
            self._popup.Hide()

    def _on_select(self, event):
        idx = self._listbox.GetFirstSelected()
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

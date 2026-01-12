"""
Rich text editing panel with WYSIWYG toolbar for the Tarot Journal app.
Uses wx.richtext.RichTextCtrl with dark theme support.
"""

import wx
import wx.richtext as rt
import wx.lib.buttons as buttons
import io
from theme_config import get_theme


def get_wx_color(key):
    """Get a wx.Colour from theme"""
    colors = get_theme().get_colors()
    hex_color = colors.get(key, '#000000').lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return wx.Colour(*rgb)


def is_rich_text(content):
    """Check if content is XML-formatted rich text"""
    if not content:
        return False
    stripped = content.strip()
    return stripped.startswith('<?xml') or stripped.startswith('<richtext')


class RichTextPanel(wx.Panel):
    """
    Reusable rich text editor panel with formatting toolbar.

    Features:
    - Bold, italic, underline formatting
    - Text alignment (left, center, right)
    - Bullet and numbered lists
    - Dark theme integration
    - XML serialization for storage
    - Backward compatible with plain text
    """

    def __init__(self, parent, value='', min_height=120):
        super().__init__(parent)
        self.SetBackgroundColour(get_wx_color('bg_primary'))

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Toolbar
        self.toolbar = self._create_toolbar()
        sizer.Add(self.toolbar, 0, wx.EXPAND | wx.BOTTOM, 2)

        # Rich text control
        self.rtc = rt.RichTextCtrl(
            self,
            style=wx.VSCROLL | wx.HSCROLL | wx.NO_BORDER | wx.WANTS_CHARS
        )
        self.rtc.SetBackgroundColour(get_wx_color('bg_input'))
        self.rtc.SetMinSize((-1, min_height))

        # Set default text styling for dark theme
        self._apply_default_style()

        sizer.Add(self.rtc, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Load initial value
        if value:
            self.SetValue(value)

    def _apply_default_style(self):
        """Apply default styling for dark theme"""
        attr = rt.RichTextAttr()
        attr.SetTextColour(get_wx_color('text_primary'))
        attr.SetBackgroundColour(get_wx_color('bg_input'))
        self.rtc.SetBasicStyle(attr)
        self.rtc.SetDefaultStyle(attr)

    def _create_toolbar(self):
        """Create formatting toolbar"""
        panel = wx.Panel(self)
        panel.SetBackgroundColour(get_wx_color('bg_secondary'))
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        btn_size = (32, 26)

        def make_button(parent, label, tooltip, font=None):
            """Create a GenButton with proper dark theme colors"""
            btn = buttons.GenButton(parent, label=label, size=btn_size)
            btn.SetBackgroundColour(get_wx_color('bg_tertiary'))
            btn.SetForegroundColour(get_wx_color('text_primary'))
            if font:
                btn.SetFont(font)
            btn.SetToolTip(tooltip)
            return btn

        # Bold button
        bold_font = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.bold_btn = make_button(panel, "B", "Bold (Ctrl+B)", bold_font)
        self.bold_btn.Bind(wx.EVT_BUTTON, self._on_bold)
        sizer.Add(self.bold_btn, 0, wx.ALL, 2)

        # Italic button
        italic_font = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)
        self.italic_btn = make_button(panel, "I", "Italic (Ctrl+I)", italic_font)
        self.italic_btn.Bind(wx.EVT_BUTTON, self._on_italic)
        sizer.Add(self.italic_btn, 0, wx.ALL, 2)

        # Underline button
        underline_font = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, underline=True)
        self.underline_btn = make_button(panel, "U", "Underline (Ctrl+U)", underline_font)
        self.underline_btn.Bind(wx.EVT_BUTTON, self._on_underline)
        sizer.Add(self.underline_btn, 0, wx.ALL, 2)

        # Separator
        sep1 = wx.StaticLine(panel, style=wx.LI_VERTICAL)
        sizer.Add(sep1, 0, wx.EXPAND | wx.ALL, 4)

        # Align left button
        self.left_btn = make_button(panel, "\u2630", "Align Left")
        self.left_btn.Bind(wx.EVT_BUTTON, lambda e: self._on_align(wx.TEXT_ALIGNMENT_LEFT))
        sizer.Add(self.left_btn, 0, wx.ALL, 2)

        # Align center button
        self.center_btn = make_button(panel, "\u2261", "Align Center")
        self.center_btn.Bind(wx.EVT_BUTTON, lambda e: self._on_align(wx.TEXT_ALIGNMENT_CENTER))
        sizer.Add(self.center_btn, 0, wx.ALL, 2)

        # Align right button
        self.right_btn = make_button(panel, "\u2630", "Align Right")
        self.right_btn.Bind(wx.EVT_BUTTON, lambda e: self._on_align(wx.TEXT_ALIGNMENT_RIGHT))
        sizer.Add(self.right_btn, 0, wx.ALL, 2)

        # Separator
        sep2 = wx.StaticLine(panel, style=wx.LI_VERTICAL)
        sizer.Add(sep2, 0, wx.EXPAND | wx.ALL, 4)

        # Bullet list button
        self.bullet_btn = make_button(panel, "\u2022", "Bullet List")
        self.bullet_btn.Bind(wx.EVT_BUTTON, self._on_bullet_list)
        sizer.Add(self.bullet_btn, 0, wx.ALL, 2)

        # Numbered list button
        self.number_btn = make_button(panel, "1.", "Numbered List")
        self.number_btn.Bind(wx.EVT_BUTTON, self._on_numbered_list)
        sizer.Add(self.number_btn, 0, wx.ALL, 2)

        panel.SetSizer(sizer)
        return panel

    def _on_bold(self, event):
        """Toggle bold on selection"""
        self.rtc.ApplyBoldToSelection()
        self.rtc.SetFocus()

    def _on_italic(self, event):
        """Toggle italic on selection"""
        self.rtc.ApplyItalicToSelection()
        self.rtc.SetFocus()

    def _on_underline(self, event):
        """Toggle underline on selection"""
        self.rtc.ApplyUnderlineToSelection()
        self.rtc.SetFocus()

    def _on_align(self, alignment):
        """Set paragraph alignment"""
        self.rtc.ApplyAlignmentToSelection(alignment)
        self.rtc.SetFocus()

    def _on_bullet_list(self, event):
        """Toggle bullet list"""
        if self.rtc.HasSelection():
            range_sel = self.rtc.GetSelectionRange()
        else:
            range_sel = rt.RichTextRange(self.rtc.GetInsertionPoint(), self.rtc.GetInsertionPoint())

        # Check if already has bullet
        attr = rt.RichTextAttr()
        if self.rtc.GetStyleForRange(range_sel, attr):
            if attr.HasBulletStyle() and attr.GetBulletStyle() != 0:
                # Remove bullet
                attr.SetBulletStyle(wx.TEXT_ATTR_BULLET_STYLE_NONE)
                attr.SetLeftIndent(0, 0)
                attr.SetFlags(wx.TEXT_ATTR_BULLET_STYLE | wx.TEXT_ATTR_LEFT_INDENT)
                self.rtc.SetStyleEx(range_sel, attr, rt.RICHTEXT_SETSTYLE_WITH_UNDO | rt.RICHTEXT_SETSTYLE_PARAGRAPHS_ONLY)
            else:
                # Add bullet
                attr.SetBulletStyle(wx.TEXT_ATTR_BULLET_STYLE_STANDARD)
                attr.SetLeftIndent(40, 20)
                attr.SetFlags(wx.TEXT_ATTR_BULLET_STYLE | wx.TEXT_ATTR_LEFT_INDENT)
                self.rtc.SetStyleEx(range_sel, attr, rt.RICHTEXT_SETSTYLE_WITH_UNDO | rt.RICHTEXT_SETSTYLE_PARAGRAPHS_ONLY)
        self.rtc.SetFocus()

    def _on_numbered_list(self, event):
        """Toggle numbered list"""
        if self.rtc.HasSelection():
            range_sel = self.rtc.GetSelectionRange()
        else:
            range_sel = rt.RichTextRange(self.rtc.GetInsertionPoint(), self.rtc.GetInsertionPoint())

        # Check if already has numbering
        attr = rt.RichTextAttr()
        if self.rtc.GetStyleForRange(range_sel, attr):
            if attr.HasBulletStyle() and (attr.GetBulletStyle() & wx.TEXT_ATTR_BULLET_STYLE_ARABIC):
                # Remove numbering
                attr.SetBulletStyle(wx.TEXT_ATTR_BULLET_STYLE_NONE)
                attr.SetLeftIndent(0, 0)
                attr.SetFlags(wx.TEXT_ATTR_BULLET_STYLE | wx.TEXT_ATTR_LEFT_INDENT)
                self.rtc.SetStyleEx(range_sel, attr, rt.RICHTEXT_SETSTYLE_WITH_UNDO | rt.RICHTEXT_SETSTYLE_PARAGRAPHS_ONLY)
            else:
                # Add numbering
                attr.SetBulletStyle(wx.TEXT_ATTR_BULLET_STYLE_ARABIC | wx.TEXT_ATTR_BULLET_STYLE_PERIOD)
                attr.SetBulletNumber(1)
                attr.SetLeftIndent(40, 20)
                attr.SetFlags(wx.TEXT_ATTR_BULLET_STYLE | wx.TEXT_ATTR_BULLET_NUMBER | wx.TEXT_ATTR_LEFT_INDENT)
                self.rtc.SetStyleEx(range_sel, attr, rt.RICHTEXT_SETSTYLE_WITH_UNDO | rt.RICHTEXT_SETSTYLE_PARAGRAPHS_ONLY | rt.RICHTEXT_SETSTYLE_RENUMBER)
        self.rtc.SetFocus()

    def GetValue(self):
        """Return content as XML string for storage"""
        # Use a memory stream to export XML
        stream = io.BytesIO()
        handler = rt.RichTextXMLHandler()
        handler.SetFlags(rt.RICHTEXT_HANDLER_INCLUDE_STYLESHEET)

        buffer = self.rtc.GetBuffer()
        # We need to save to a wx.OutputStream, so we use a file-like approach
        success = buffer.SaveFile(stream, rt.RICHTEXT_TYPE_XML)

        if success:
            return stream.getvalue().decode('utf-8')
        else:
            # Fallback to plain text
            return self.rtc.GetValue()

    def SetValue(self, value):
        """Load content, auto-detecting format (XML or plain text)"""
        self.rtc.Clear()

        if not value:
            self._apply_default_style()
            return

        if is_rich_text(value):
            # Load as XML
            try:
                stream = io.BytesIO(value.encode('utf-8'))
                handler = rt.RichTextXMLHandler()
                buffer = self.rtc.GetBuffer()
                buffer.LoadFile(stream, rt.RICHTEXT_TYPE_XML)
                self.rtc.Refresh()
            except Exception as e:
                # Fallback to plain text if XML parsing fails
                self._apply_default_style()
                self.rtc.SetValue(value)
        else:
            # Load as plain text
            self._apply_default_style()
            self.rtc.SetValue(value)

    def GetPlainText(self):
        """Return plain text without formatting"""
        return self.rtc.GetValue()

    def IsModified(self):
        """Check if content has been modified"""
        return self.rtc.IsModified()

    def SetFocus(self):
        """Set focus to the rich text control"""
        self.rtc.SetFocus()


class RichTextViewer(wx.Panel):
    """
    Read-only display of rich text content.
    Used for viewing formatted text without editing.
    """

    def __init__(self, parent, value='', min_height=60):
        super().__init__(parent)
        self.SetBackgroundColour(get_wx_color('bg_primary'))

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Rich text control in read-only mode
        self.rtc = rt.RichTextCtrl(
            self,
            style=wx.VSCROLL | wx.NO_BORDER | wx.TE_READONLY
        )
        self.rtc.SetBackgroundColour(get_wx_color('bg_primary'))
        self.rtc.SetMinSize((-1, min_height))

        # Set default text styling
        self._apply_default_style()

        sizer.Add(self.rtc, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Load initial value
        if value:
            self.SetValue(value)

    def _apply_default_style(self):
        """Apply default styling for dark theme"""
        attr = rt.RichTextAttr()
        attr.SetTextColour(get_wx_color('text_primary'))
        attr.SetBackgroundColour(get_wx_color('bg_primary'))
        self.rtc.SetBasicStyle(attr)
        self.rtc.SetDefaultStyle(attr)

    def SetValue(self, value):
        """Load content, auto-detecting format"""
        self.rtc.Clear()

        if not value:
            return

        if is_rich_text(value):
            # Load as XML
            try:
                stream = io.BytesIO(value.encode('utf-8'))
                handler = rt.RichTextXMLHandler()
                buffer = self.rtc.GetBuffer()
                buffer.LoadFile(stream, rt.RICHTEXT_TYPE_XML)
                self.rtc.Refresh()
            except Exception:
                # Fallback to plain text
                self._apply_default_style()
                self.rtc.SetValue(value)
        else:
            # Load as plain text
            self._apply_default_style()
            self.rtc.SetValue(value)

    def GetValue(self):
        """Return the displayed content"""
        return self.rtc.GetValue()

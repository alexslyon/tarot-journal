# Tarot Journal - Development Notes

## wxPython Styling Rules (Dark Theme)

This app uses a custom dark theme. When creating UI elements:

1. **All widgets need explicit colors** - wxPython defaults assume a light background
   - Always call `SetForegroundColour(get_wx_color('text_primary'))` on text-displaying widgets
   - For buttons and inputs, also call `SetBackgroundColour(get_wx_color('bg_secondary'))`

2. **wx.CheckBox labels don't support custom colors on macOS**
   - Do NOT use: `wx.CheckBox(parent, label="Some text")` with `SetForegroundColour()`
   - Instead, use an empty-label checkbox with a separate StaticText:
     ```python
     cb_sizer = wx.BoxSizer(wx.HORIZONTAL)
     cb = wx.CheckBox(parent, label="")
     cb_sizer.Add(cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
     cb_label = wx.StaticText(parent, label="Your label text")
     cb_label.SetForegroundColour(get_wx_color('text_primary'))
     cb_sizer.Add(cb_label, 0, wx.ALIGN_CENTER_VERTICAL)
     ```

3. **Common color keys:**
   - `text_primary` - main text color (white/light)
   - `text_secondary` - dimmer text
   - `text_dim` - subtle text
   - `bg_primary` - main background
   - `bg_secondary` - slightly lighter background (for inputs, buttons)
   - `bg_input` - input field background

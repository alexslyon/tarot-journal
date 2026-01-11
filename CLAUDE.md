# Tarot Journal - Development Notes

## wxPython Styling Rules (Dark Theme)

This app uses a custom dark theme. When creating UI elements:

1. **All widgets need explicit colors** - wxPython defaults assume a light background
   - Always call `SetForegroundColour(get_wx_color('text_primary'))` on text-displaying widgets
   - For buttons and inputs, also call `SetBackgroundColour(get_wx_color('bg_secondary'))`

2. **CRITICAL: wx.CheckBox labels don't support custom colors on macOS**
   - **NEVER** use: `wx.CheckBox(parent, label="Some text")` - the label will be BLACK and unreadable on the dark background
   - `SetForegroundColour()` does NOT work on checkbox labels on macOS
   - **ALWAYS** use an empty-label checkbox with a separate StaticText:
     ```python
     cb_sizer = wx.BoxSizer(wx.HORIZONTAL)
     cb = wx.CheckBox(parent, label="")  # Empty label!
     cb_sizer.Add(cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
     cb_label = wx.StaticText(parent, label="Your label text")
     cb_label.SetForegroundColour(get_wx_color('text_primary'))
     cb_sizer.Add(cb_label, 0, wx.ALIGN_CENTER_VERTICAL)
     ```
   - This applies to ALL checkboxes in the app, including those in dialogs

3. **Common color keys:**
   - `text_primary` - main text color (white/light)
   - `text_secondary` - dimmer text
   - `text_dim` - subtle text
   - `bg_primary` - main background
   - `bg_secondary` - slightly lighter background (for inputs, buttons)
   - `bg_input` - input field background

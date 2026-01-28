"""
Convert wxPython RichTextCtrl XML content to HTML.

The wxPython RichTextCtrl stores content as XML with <richtext> root,
<paragraphlayout> container, <paragraph> elements, and <text> elements
with font attributes (weight, style, underline).

New entries from the React frontend are stored as HTML (Tiptap output).
This module converts XML to HTML on-the-fly when serving to the frontend.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import re
from html import escape


def convert_content_to_html(content: str | None) -> str:
    """Convert stored content to HTML for the frontend.

    Handles three formats:
    - wxPython XML (starts with <?xml or <richtext>) → converted to HTML
    - HTML (starts with <) → passed through unchanged
    - Plain text → wrapped in <p> tags
    """
    if not content or not content.strip():
        return ''

    stripped = content.strip()

    # wxPython rich text XML
    if stripped.startswith('<?xml') or stripped.startswith('<richtext'):
        try:
            return _convert_xml_to_html(stripped)
        except Exception:
            # Fallback: strip tags and wrap as plain text
            plain = re.sub(r'<[^>]+>', '', stripped)
            return _plain_text_to_html(plain)

    # Already HTML (starts with a tag but not XML declaration)
    if stripped.startswith('<'):
        return content

    # Plain text
    return _plain_text_to_html(stripped)


def _plain_text_to_html(text: str) -> str:
    """Wrap plain text in <p> tags, preserving line breaks."""
    lines = text.split('\n')
    paragraphs = []
    for line in lines:
        escaped = escape(line)
        paragraphs.append(f'<p>{escaped}</p>' if escaped else '<p><br></p>')
    return ''.join(paragraphs)


def _convert_xml_to_html(xml_content: str) -> str:
    """Parse wxPython RichTextCtrl XML and convert to HTML."""
    # Strip XML declaration if present
    if xml_content.startswith('<?xml'):
        # Find end of XML declaration
        decl_end = xml_content.find('?>')
        if decl_end >= 0:
            xml_content = xml_content[decl_end + 2:].strip()

    # Remove namespace declarations that may cause parsing issues
    xml_content = re.sub(r'\s+xmlns="[^"]*"', '', xml_content)

    root = ET.fromstring(xml_content)
    html_parts = []

    # The structure is typically:
    # <richtext> -> <paragraphlayout> -> <paragraph> -> <text>
    # or <richtext> -> <paragraph> -> <text>

    paragraphs = root.findall('.//paragraph')
    if not paragraphs:
        # Try direct children
        paragraphs = list(root)

    # Track list state for bullet/numbered list grouping
    in_bullet_list = False
    in_numbered_list = False

    for para in paragraphs:
        if para.tag != 'paragraph':
            continue

        # Check for list attributes
        bullet_style = para.get('bulletstyle', '0')
        bullet_style_int = int(bullet_style) if bullet_style.isdigit() else 0

        is_bullet = bool(bullet_style_int & 0x20)  # TEXT_ATTR_BULLET_STYLE_STANDARD = 0x20
        is_numbered = bool(bullet_style_int & 0x10)  # TEXT_ATTR_BULLET_STYLE_ARABIC = 0x10

        # Handle list transitions
        if is_bullet and not in_bullet_list:
            if in_numbered_list:
                html_parts.append('</ol>')
                in_numbered_list = False
            html_parts.append('<ul>')
            in_bullet_list = True
        elif is_numbered and not in_numbered_list:
            if in_bullet_list:
                html_parts.append('</ul>')
                in_bullet_list = False
            html_parts.append('<ol>')
            in_numbered_list = True
        elif not is_bullet and not is_numbered:
            if in_bullet_list:
                html_parts.append('</ul>')
                in_bullet_list = False
            if in_numbered_list:
                html_parts.append('</ol>')
                in_numbered_list = False

        # Build paragraph content
        inline_html = _convert_paragraph_content(para)

        # Determine alignment
        alignment = para.get('alignment', '')
        style = ''
        if alignment == '1':  # center
            style = ' style="text-align: center"'
        elif alignment == '2':  # right
            style = ' style="text-align: right"'

        if is_bullet or is_numbered:
            html_parts.append(f'<li{style}>{inline_html}</li>')
        else:
            html_parts.append(f'<p{style}>{inline_html}</p>')

    # Close any open lists
    if in_bullet_list:
        html_parts.append('</ul>')
    if in_numbered_list:
        html_parts.append('</ol>')

    result = ''.join(html_parts)
    return result if result else '<p></p>'


def _convert_paragraph_content(para) -> str:
    """Convert <text> elements within a paragraph to inline HTML."""
    parts = []

    for elem in para:
        if elem.tag == 'text':
            text = escape(elem.text or '')

            # Check font attributes for formatting
            weight = elem.get('fontweight', '')
            style = elem.get('fontstyle', '')
            underline = elem.get('fontunderlined', '0')

            # Also check nested <font> element attributes
            font_weight = weight
            font_style = style
            font_underline = underline

            # Apply formatting tags (innermost to outermost)
            if font_underline == '1':
                text = f'<u>{text}</u>'
            if font_style == '93':  # wx.FONTSTYLE_ITALIC
                text = f'<em>{text}</em>'
            if font_weight == '92' or font_weight == '700':  # wx.FONTWEIGHT_BOLD
                text = f'<strong>{text}</strong>'

            parts.append(text)
        elif elem.tag == 'symbol':
            # Symbol elements (line breaks, etc.)
            parts.append('<br>')

    # If paragraph had no text elements, check for direct text content
    if not parts and para.text:
        parts.append(escape(para.text))

    return ''.join(parts) if parts else '<br>'

#!/usr/bin/env python3
"""
Tarot Journal - A journaling app for cartomancy
Main application with modern GUI
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import json
import os
from datetime import datetime
from pathlib import Path
from database import Database, create_default_spreads, create_default_decks
from thumbnail_cache import get_cache, ThumbnailCache
from import_presets import get_presets, ImportPresets, BUILTIN_PRESETS
from theme_config import get_theme, get_colors, get_fonts, PRESET_THEMES
from logger_config import get_logger

logger = get_logger('app_tk')

# === Load Theme Configuration ===
_theme = get_theme()
COLORS = _theme.get_colors()
_fonts_config = _theme.get_fonts()

FONTS = {
    'title': (_fonts_config['family_display'], _fonts_config['size_title'], 'bold'),
    'heading': (_fonts_config['family_display'], _fonts_config['size_heading'], 'bold'),
    'body': (_fonts_config['family_text'], _fonts_config['size_body']),
    'small': (_fonts_config['family_text'], _fonts_config['size_small']),
    'mono': (_fonts_config['family_mono'], 11),
}

# Fallback fonts for systems without SF Pro
FONT_FALLBACKS = {
    'SF Pro Display': ('Helvetica Neue', 'Helvetica', 'Arial'),
    'SF Pro Text': ('Helvetica Neue', 'Helvetica', 'Arial'),
    'SF Mono': ('Menlo', 'Monaco', 'Consolas'),
}


class TarotJournalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tarot Journal")
        self.root.geometry("1400x900")
        self.root.configure(bg=COLORS['bg_primary'])
        
        # Initialize systems
        self.db = Database()
        create_default_spreads(self.db)
        create_default_decks(self.db)
        self.thumb_cache = get_cache()
        self.presets = get_presets()
        logger.info("Database and systems initialized")

        # State
        self.current_entry_id = None
        self.current_spread_cards = {}
        self.selected_deck_id = None
        self.selected_spread_id = None
        self.selected_card_id = None
        self.card_frames = {}
        self.photo_refs = {}  # Keep references to prevent garbage collection
        
        # Configure styles
        self._configure_styles()
        
        # Build UI
        self._build_ui()
        
        # Load initial data
        self._refresh_all()
    
    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame styles
        style.configure('TFrame', background=COLORS['bg_primary'])
        style.configure('Card.TFrame', background=COLORS['bg_secondary'])
        
        # Label styles
        style.configure('TLabel', 
                       background=COLORS['bg_primary'], 
                       foreground=COLORS['text_primary'],
                       font=FONTS['body'])
        style.configure('Heading.TLabel',
                       font=FONTS['heading'],
                       foreground=COLORS['text_primary'])
        style.configure('Dim.TLabel',
                       foreground=COLORS['text_secondary'])
        
        # Button styles
        style.configure('TButton',
                       background=COLORS['bg_tertiary'],
                       foreground=COLORS['text_primary'],
                       padding=(12, 6),
                       font=FONTS['body'])
        style.map('TButton',
                 background=[('active', COLORS['bg_input']),
                            ('pressed', COLORS['accent_dim'])],
                 foreground=[('active', COLORS['text_primary'])])
        
        style.configure('Accent.TButton',
                       background=COLORS['accent'],
                       foreground='white',
                       padding=(16, 8),
                       font=FONTS['body'])
        style.map('Accent.TButton',
                 background=[('active', COLORS['accent_hover']),
                            ('pressed', COLORS['accent_dim'])])
        
        style.configure('Danger.TButton',
                       background=COLORS['danger'],
                       foreground='white')
        
        # Notebook styles
        style.configure('TNotebook',
                       background=COLORS['bg_primary'],
                       borderwidth=0)
        style.configure('TNotebook.Tab',
                       background=COLORS['bg_secondary'],
                       foreground=COLORS['text_secondary'],
                       padding=(20, 10),
                       font=FONTS['body'])
        style.map('TNotebook.Tab',
                 background=[('selected', COLORS['bg_tertiary'])],
                 foreground=[('selected', COLORS['text_primary'])])
        
        # Treeview styles
        style.configure('Treeview',
                       background=COLORS['bg_secondary'],
                       foreground=COLORS['text_primary'],
                       fieldbackground=COLORS['bg_secondary'],
                       borderwidth=0,
                       rowheight=32,
                       font=FONTS['body'])
        style.configure('Treeview.Heading',
                       background=COLORS['bg_tertiary'],
                       foreground=COLORS['text_secondary'],
                       font=FONTS['small'])
        style.map('Treeview',
                 background=[('selected', COLORS['accent_dim'])],
                 foreground=[('selected', COLORS['text_primary'])])
        
        # Entry styles
        style.configure('TEntry',
                       fieldbackground=COLORS['bg_input'],
                       foreground=COLORS['text_primary'],
                       insertcolor=COLORS['text_primary'])
        
        # Combobox styles
        style.configure('TCombobox',
                       fieldbackground=COLORS['bg_input'],
                       background=COLORS['bg_tertiary'],
                       foreground=COLORS['text_primary'],
                       arrowcolor=COLORS['text_secondary'])
        style.map('TCombobox',
                 fieldbackground=[('readonly', COLORS['bg_input'])],
                 selectbackground=[('readonly', COLORS['accent_dim'])])
        
        # Scrollbar
        style.configure('TScrollbar',
                       background=COLORS['bg_tertiary'],
                       troughcolor=COLORS['bg_secondary'],
                       arrowcolor=COLORS['text_secondary'])
        
        # LabelFrame
        style.configure('TLabelframe',
                       background=COLORS['bg_primary'],
                       foreground=COLORS['text_primary'])
        style.configure('TLabelframe.Label',
                       background=COLORS['bg_primary'],
                       foreground=COLORS['accent'],
                       font=FONTS['heading'])
        
        # PanedWindow
        style.configure('TPanedwindow', background=COLORS['bg_primary'])
    
    def _build_ui(self):
        # Main container with padding
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Header
        self._build_header(main)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Create tab frames
        self.journal_frame = ttk.Frame(self.notebook)
        self.library_frame = ttk.Frame(self.notebook)
        self.spreads_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.journal_frame, text='  Journal  ')
        self.notebook.add(self.library_frame, text='  Card Library  ')
        self.notebook.add(self.spreads_frame, text='  Spreads  ')
        self.notebook.add(self.settings_frame, text='  Settings  ')
        
        # Build tabs
        self._build_journal_tab()
        self._build_library_tab()
        self._build_spreads_tab()
        self._build_settings_tab()
    
    def _build_header(self, parent):
        header = tk.Frame(parent, bg=COLORS['bg_primary'])
        header.pack(fill=tk.X, pady=(0, 5))
        
        title = tk.Label(header,
                        text="Tarot Journal",
                        font=FONTS['title'],
                        bg=COLORS['bg_primary'],
                        fg=COLORS['text_primary'])
        title.pack(side=tk.LEFT)
        
        # Stats button
        stats_btn = ttk.Button(header, text="Stats", command=self._show_stats)
        stats_btn.pack(side=tk.RIGHT, padx=5)
    
    # ═══════════════════════════════════════════
    # JOURNAL TAB
    # ═══════════════════════════════════════════
    def _build_journal_tab(self):
        paned = ttk.PanedWindow(self.journal_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Entry list
        left = ttk.Frame(paned, width=300)
        paned.add(left, weight=1)
        
        # Search bar
        search_frame = tk.Frame(left, bg=COLORS['bg_primary'])
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.search_var = tk.StringVar()
        self._search_after_id = None
        
        def debounced_search(*args):
            # Cancel previous scheduled search
            if self._search_after_id:
                self.root.after_cancel(self._search_after_id)
            # Schedule new search after 300ms of no typing
            self._search_after_id = self.root.after(300, self._refresh_entries_list)
        
        self.search_var.trace('w', debounced_search)
        
        search_entry = tk.Entry(search_frame,
                               textvariable=self.search_var,
                               bg=COLORS['bg_input'],
                               fg=COLORS['text_primary'],
                               insertbackground=COLORS['text_primary'],
                               relief=tk.FLAT,
                               font=FONTS['body'])
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        search_entry.insert(0, "")
        
        # Filter dropdown
        self.filter_tag_var = tk.StringVar(value="All Tags")
        self.filter_tag_combo = ttk.Combobox(search_frame,
                                            textvariable=self.filter_tag_var,
                                            width=15,
                                            state='readonly')
        self.filter_tag_combo.pack(side=tk.RIGHT, padx=(10, 0))
        self.filter_tag_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_entries_list())
        
        # Entries treeview
        tree_frame = tk.Frame(left, bg=COLORS['bg_secondary'])
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.entries_tree = ttk.Treeview(tree_frame,
                                        columns=('date', 'title'),
                                        show='headings',
                                        height=20)
        self.entries_tree.heading('date', text='Date')
        self.entries_tree.heading('title', text='Title')
        self.entries_tree.column('date', width=90, minwidth=90)
        self.entries_tree.column('title', width=180)
        self.entries_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.entries_tree.bind('<<TreeviewSelect>>', self._on_entry_select)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                 command=self.entries_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.entries_tree.configure(yscrollcommand=scrollbar.set)
        
        # Buttons
        btn_frame = tk.Frame(left, bg=COLORS['bg_primary'])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="+ New Entry",
                  command=self._new_entry,
                  style='Accent.TButton').pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Delete",
                  command=self._delete_entry).pack(side=tk.LEFT, padx=(10, 0))
        
        # Right panel - Editor
        right = ttk.Frame(paned)
        paned.add(right, weight=3)
        
        self._build_editor(right)
    
    def _build_editor(self, parent):
        # Scrollable container
        canvas = tk.Canvas(parent, bg=COLORS['bg_primary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        editor_frame = tk.Frame(canvas, bg=COLORS['bg_primary'])
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas_window = canvas.create_window((0, 0), window=editor_frame, anchor='nw')
        
        def configure_scroll(e):
            canvas.configure(scrollregion=canvas.bbox('all'))
            canvas.itemconfig(canvas_window, width=e.width)
        
        editor_frame.bind('<Configure>', configure_scroll)
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        # Title row
        title_frame = tk.Frame(editor_frame, bg=COLORS['bg_primary'])
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.title_var = tk.StringVar()
        title_entry = tk.Entry(title_frame,
                              textvariable=self.title_var,
                              bg=COLORS['bg_input'],
                              fg=COLORS['text_primary'],
                              insertbackground=COLORS['text_primary'],
                              font=('SF Pro Display', 18),
                              relief=tk.FLAT,
                              bd=0)
        title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, ipadx=10)
        
        self.date_label = tk.Label(title_frame,
                                  text="",
                                  bg=COLORS['bg_primary'],
                                  fg=COLORS['text_secondary'],
                                  font=FONTS['small'])
        self.date_label.pack(side=tk.RIGHT, padx=10)
        
        # Reading section
        reading_frame = tk.LabelFrame(editor_frame,
                                     text=" Reading ",
                                     bg=COLORS['bg_primary'],
                                     fg=COLORS['accent'],
                                     font=FONTS['heading'],
                                     bd=1,
                                     relief=tk.FLAT)
        reading_frame.pack(fill=tk.X, pady=(0, 15), ipady=10, ipadx=10)
        
        # Spread & Deck selection
        select_row = tk.Frame(reading_frame, bg=COLORS['bg_primary'])
        select_row.pack(fill=tk.X, pady=(5, 10))
        
        tk.Label(select_row, text="Spread:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                font=FONTS['small']).pack(side=tk.LEFT)
        
        self.spread_var = tk.StringVar()
        self.spread_combo = ttk.Combobox(select_row,
                                        textvariable=self.spread_var,
                                        width=20,
                                        state='readonly')
        self.spread_combo.pack(side=tk.LEFT, padx=(5, 20))
        self.spread_combo.bind('<<ComboboxSelected>>', self._on_spread_select)
        
        tk.Label(select_row, text="Deck:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                font=FONTS['small']).pack(side=tk.LEFT)
        
        self.deck_var = tk.StringVar()
        self.deck_combo = ttk.Combobox(select_row,
                                      textvariable=self.deck_var,
                                      width=25,
                                      state='readonly')
        self.deck_combo.pack(side=tk.LEFT, padx=5)
        self.deck_combo.bind('<<ComboboxSelected>>', self._on_deck_select)
        
        # Spread canvas
        canvas_container = tk.Frame(reading_frame, bg=COLORS['card_slot'])
        canvas_container.pack(fill=tk.X, pady=10)
        
        self.spread_canvas = tk.Canvas(canvas_container,
                                       bg=COLORS['card_slot'],
                                       height=350,
                                       highlightthickness=0)
        self.spread_canvas.pack(fill=tk.X, expand=True)
        self.spread_canvas.bind('<Button-1>', self._on_canvas_click)
        
        # Cards used label
        self.cards_label = tk.Label(reading_frame,
                                   text="Click positions above to assign cards",
                                   bg=COLORS['bg_primary'],
                                   fg=COLORS['text_dim'],
                                   font=FONTS['small'])
        self.cards_label.pack(pady=(0, 5))
        
        # Journal content
        content_frame = tk.LabelFrame(editor_frame,
                                     text=" Notes ",
                                     bg=COLORS['bg_primary'],
                                     fg=COLORS['accent'],
                                     font=FONTS['heading'],
                                     bd=1,
                                     relief=tk.FLAT)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.content_text = tk.Text(content_frame,
                                   bg=COLORS['bg_input'],
                                   fg=COLORS['text_primary'],
                                   insertbackground=COLORS['text_primary'],
                                   font=FONTS['body'],
                                   wrap=tk.WORD,
                                   relief=tk.FLAT,
                                   padx=12,
                                   pady=12,
                                   height=10)
        self.content_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tags row
        tags_row = tk.Frame(editor_frame, bg=COLORS['bg_primary'])
        tags_row.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(tags_row, text="Tags:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                font=FONTS['small']).pack(side=tk.LEFT)
        
        self.tags_container = tk.Frame(tags_row, bg=COLORS['bg_primary'])
        self.tags_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        ttk.Button(tags_row, text="+ Tag",
                  command=self._add_tag_to_entry).pack(side=tk.RIGHT)
        
        # Save button
        save_row = tk.Frame(editor_frame, bg=COLORS['bg_primary'])
        save_row.pack(fill=tk.X)
        
        ttk.Button(save_row, text="Save Entry",
                  command=self._save_entry,
                  style='Accent.TButton').pack(side=tk.RIGHT)
    
    # ═══════════════════════════════════════════
    # LIBRARY TAB
    # ═══════════════════════════════════════════
    def _build_library_tab(self):
        paned = ttk.PanedWindow(self.library_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left - Deck list
        left = ttk.Frame(paned, width=280)
        paned.add(left, weight=1)
        
        tk.Label(left, text="Decks",
                font=FONTS['heading'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(anchor='w', pady=(0, 10))
        
        # Type filter
        filter_row = tk.Frame(left, bg=COLORS['bg_primary'])
        filter_row.pack(fill=tk.X, pady=(0, 10))
        
        self.type_filter_var = tk.StringVar(value="All")
        self.type_filter_combo = ttk.Combobox(filter_row,
                                             textvariable=self.type_filter_var,
                                             values=['All', 'Tarot', 'Lenormand', 'Oracle'],
                                             width=15,
                                             state='readonly')
        self.type_filter_combo.pack(side=tk.LEFT)
        self.type_filter_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_decks_list())
        
        # Decks tree
        tree_frame = tk.Frame(left, bg=COLORS['bg_secondary'])
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.decks_tree = ttk.Treeview(tree_frame,
                                      columns=('name', 'type', 'count'),
                                      show='headings',
                                      height=15)
        self.decks_tree.heading('name', text='Name')
        self.decks_tree.heading('type', text='Type')
        self.decks_tree.heading('count', text='#')
        self.decks_tree.column('name', width=140)
        self.decks_tree.column('type', width=80)
        self.decks_tree.column('count', width=40)
        self.decks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.decks_tree.bind('<<TreeviewSelect>>', self._on_deck_tree_select)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                 command=self.decks_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.decks_tree.configure(yscrollcommand=scrollbar.set)
        
        # Buttons
        btn_frame = tk.Frame(left, bg=COLORS['bg_primary'])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="+ Add",
                  command=self._add_deck).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Import Folder",
                  command=self._import_deck_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete",
                  command=self._delete_deck).pack(side=tk.LEFT)
        
        # Right - Cards grid
        right = ttk.Frame(paned)
        paned.add(right, weight=3)
        
        self.deck_title_label = tk.Label(right,
                                        text="Select a deck",
                                        font=FONTS['heading'],
                                        bg=COLORS['bg_primary'],
                                        fg=COLORS['text_primary'])
        self.deck_title_label.pack(anchor='w', pady=(0, 10))
        
        # Cards container with scrolling
        cards_outer = tk.Frame(right, bg=COLORS['bg_secondary'])
        cards_outer.pack(fill=tk.BOTH, expand=True)
        
        self.cards_canvas = tk.Canvas(cards_outer,
                                     bg=COLORS['bg_secondary'],
                                     highlightthickness=0)
        cards_scroll = ttk.Scrollbar(cards_outer, orient=tk.VERTICAL,
                                    command=self.cards_canvas.yview)
        self.cards_inner = tk.Frame(self.cards_canvas, bg=COLORS['bg_secondary'])
        
        self.cards_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cards_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.cards_canvas.configure(yscrollcommand=cards_scroll.set)
        self.cards_window = self.cards_canvas.create_window((0, 0),
                                                           window=self.cards_inner,
                                                           anchor='nw')
        
        self.cards_inner.bind('<Configure>',
                             lambda e: self.cards_canvas.configure(
                                 scrollregion=self.cards_canvas.bbox('all')))
        self.cards_canvas.bind('<Configure>',
                              lambda e: self.cards_canvas.itemconfig(
                                  self.cards_window, width=e.width))
        
        # Card buttons
        card_btn_frame = tk.Frame(right, bg=COLORS['bg_primary'])
        card_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(card_btn_frame, text="+ Add Card",
                  command=self._add_card).pack(side=tk.LEFT)
        ttk.Button(card_btn_frame, text="Import Images",
                  command=self._import_cards).pack(side=tk.LEFT, padx=5)
        ttk.Button(card_btn_frame, text="Edit Selected",
                  command=self._edit_card).pack(side=tk.LEFT, padx=5)
        ttk.Button(card_btn_frame, text="Delete Selected",
                  command=self._delete_card).pack(side=tk.LEFT)
    
    # ═══════════════════════════════════════════
    # SPREADS TAB
    # ═══════════════════════════════════════════
    def _build_spreads_tab(self):
        paned = ttk.PanedWindow(self.spreads_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left - Spread list
        left = ttk.Frame(paned, width=250)
        paned.add(left, weight=1)
        
        tk.Label(left, text="Spreads",
                font=FONTS['heading'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(anchor='w', pady=(0, 10))
        
        self.spreads_list = tk.Listbox(left,
                                      bg=COLORS['bg_secondary'],
                                      fg=COLORS['text_primary'],
                                      selectbackground=COLORS['accent_dim'],
                                      selectforeground=COLORS['text_primary'],
                                      font=FONTS['body'],
                                      relief=tk.FLAT,
                                      bd=0,
                                      height=20)
        self.spreads_list.pack(fill=tk.BOTH, expand=True)
        self.spreads_list.bind('<<ListboxSelect>>', self._on_spread_list_select)
        
        btn_frame = tk.Frame(left, bg=COLORS['bg_primary'])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="+ New",
                  command=self._new_spread).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Delete",
                  command=self._delete_spread).pack(side=tk.LEFT, padx=5)
        
        # Right - Designer
        right = ttk.Frame(paned)
        paned.add(right, weight=3)
        
        # Name & description
        meta_frame = tk.Frame(right, bg=COLORS['bg_primary'])
        meta_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(meta_frame, text="Name:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                font=FONTS['small']).pack(side=tk.LEFT)
        
        self.spread_name_var = tk.StringVar()
        tk.Entry(meta_frame,
                textvariable=self.spread_name_var,
                bg=COLORS['bg_input'],
                fg=COLORS['text_primary'],
                insertbackground=COLORS['text_primary'],
                relief=tk.FLAT,
                width=25).pack(side=tk.LEFT, padx=5, ipady=4)
        
        tk.Label(meta_frame, text="Description:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                font=FONTS['small']).pack(side=tk.LEFT, padx=(20, 0))
        
        self.spread_desc_var = tk.StringVar()
        tk.Entry(meta_frame,
                textvariable=self.spread_desc_var,
                bg=COLORS['bg_input'],
                fg=COLORS['text_primary'],
                insertbackground=COLORS['text_primary'],
                relief=tk.FLAT,
                width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True, ipady=4)
        
        # Designer canvas
        designer_container = tk.Frame(right, bg=COLORS['card_slot'])
        designer_container.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(designer_container,
                text="Drag positions to arrange • Right-click to delete",
                bg=COLORS['card_slot'],
                fg=COLORS['text_dim'],
                font=FONTS['small']).pack(anchor='w', padx=10, pady=5)
        
        self.designer_canvas = tk.Canvas(designer_container,
                                        bg=COLORS['card_slot'],
                                        height=450,
                                        highlightthickness=0)
        self.designer_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Drag state
        self.drag_data = {'item': None, 'pos_idx': None, 'x': 0, 'y': 0}
        
        # Bind drag events
        self.designer_canvas.bind('<Button-1>', self._on_designer_press)
        self.designer_canvas.bind('<B1-Motion>', self._on_designer_drag)
        self.designer_canvas.bind('<ButtonRelease-1>', self._on_designer_release)
        self.designer_canvas.bind('<Button-2>', self._on_designer_right_click)
        self.designer_canvas.bind('<Button-3>', self._on_designer_right_click)
        
        self.designer_positions = []
        self.editing_spread_id = None
        
        # Buttons
        btn_frame2 = tk.Frame(right, bg=COLORS['bg_primary'])
        btn_frame2.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame2, text="+ Add Position",
                  command=self._add_spread_position).pack(side=tk.LEFT)
        ttk.Button(btn_frame2, text="Clear All",
                  command=self._clear_spread_positions).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame2, text="Save Spread",
                  command=self._save_spread,
                  style='Accent.TButton').pack(side=tk.RIGHT)
    
    # ═══════════════════════════════════════════
    # SETTINGS TAB
    # ═══════════════════════════════════════════
    def _build_settings_tab(self):
        # Create a canvas for scrolling
        settings_canvas = tk.Canvas(self.settings_frame, bg=COLORS['bg_primary'], highlightthickness=0)
        settings_scroll = ttk.Scrollbar(self.settings_frame, orient=tk.VERTICAL, command=settings_canvas.yview)
        container = tk.Frame(settings_canvas, bg=COLORS['bg_primary'])
        
        settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        settings_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        settings_canvas.configure(yscrollcommand=settings_scroll.set)
        settings_window = settings_canvas.create_window((0, 0), window=container, anchor='nw')
        
        def configure_settings_scroll(e):
            settings_canvas.configure(scrollregion=settings_canvas.bbox('all'))
            settings_canvas.itemconfig(settings_window, width=settings_canvas.winfo_width() - 4)
        
        container.bind('<Configure>', configure_settings_scroll)
        settings_canvas.bind('<Configure>', lambda e: settings_canvas.itemconfig(settings_window, width=e.width - 4))
        
        inner = tk.Frame(container, bg=COLORS['bg_primary'])
        inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # ─── Theme Section ───
        theme_frame = tk.LabelFrame(inner,
                                   text=" Appearance ",
                                   bg=COLORS['bg_primary'],
                                   fg=COLORS['accent'],
                                   font=FONTS['heading'])
        theme_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Preset selector
        preset_row = tk.Frame(theme_frame, bg=COLORS['bg_primary'])
        preset_row.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(preset_row, text="Theme Preset:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                font=FONTS['body']).pack(side=tk.LEFT)
        
        self.theme_preset_var = tk.StringVar(value="Dark (Default)")
        theme_preset_combo = ttk.Combobox(preset_row,
                                         textvariable=self.theme_preset_var,
                                         values=list(PRESET_THEMES.keys()),
                                         width=20,
                                         state='readonly')
        theme_preset_combo.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(preset_row, text="Apply Preset",
                  command=self._apply_theme_preset).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(preset_row, text="Customize...",
                  command=self._open_theme_editor).pack(side=tk.LEFT, padx=5)
        
        tk.Label(theme_frame,
                text="Note: Theme changes require restarting the app to take full effect.",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_dim'],
                font=FONTS['small']).pack(anchor='w', padx=10, pady=(0, 10))
        
        # ─── Import Presets Section ───
        presets_frame = tk.LabelFrame(inner,
                                     text=" Import Presets ",
                                     bg=COLORS['bg_primary'],
                                     fg=COLORS['accent'],
                                     font=FONTS['heading'])
        presets_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(presets_frame,
                text="Configure how filenames are mapped to card names during import.",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                font=FONTS['body']).pack(anchor='w', padx=10, pady=(10, 5))
        
        presets_inner = tk.Frame(presets_frame, bg=COLORS['bg_primary'])
        presets_inner.pack(fill=tk.X, padx=10, pady=10)
        
        # Preset list
        list_frame = tk.Frame(presets_inner, bg=COLORS['bg_primary'])
        list_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(list_frame, text="Available Presets:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                font=FONTS['small']).pack(anchor='w')
        
        self.presets_listbox = tk.Listbox(list_frame,
                                         bg=COLORS['bg_secondary'],
                                         fg=COLORS['text_primary'],
                                         selectbackground=COLORS['accent_dim'],
                                         font=FONTS['body'],
                                         width=30,
                                         height=8,
                                         relief=tk.FLAT)
        self.presets_listbox.pack(fill=tk.Y, expand=True, pady=5)
        self.presets_listbox.bind('<<ListboxSelect>>', self._on_preset_select)
        
        preset_btns = tk.Frame(list_frame, bg=COLORS['bg_primary'])
        preset_btns.pack(fill=tk.X)
        
        ttk.Button(preset_btns, text="+ New Preset",
                  command=self._create_preset).pack(side=tk.LEFT)
        ttk.Button(preset_btns, text="Delete",
                  command=self._delete_preset).pack(side=tk.LEFT, padx=5)
        
        # Preset details
        details_frame = tk.Frame(presets_inner, bg=COLORS['bg_primary'])
        details_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 0))
        
        tk.Label(details_frame, text="Preset Details:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                font=FONTS['small']).pack(anchor='w')
        
        self.preset_details = tk.Text(details_frame,
                                     bg=COLORS['bg_secondary'],
                                     fg=COLORS['text_primary'],
                                     font=FONTS['small'],
                                     height=10,
                                     width=50,
                                     relief=tk.FLAT,
                                     state=tk.DISABLED)
        self.preset_details.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Cache Section
        cache_frame = tk.LabelFrame(inner,
                                   text=" Thumbnail Cache ",
                                   bg=COLORS['bg_primary'],
                                   fg=COLORS['accent'],
                                   font=FONTS['heading'])
        cache_frame.pack(fill=tk.X, pady=(0, 20))
        
        cache_inner = tk.Frame(cache_frame, bg=COLORS['bg_primary'])
        cache_inner.pack(fill=tk.X, padx=10, pady=10)
        
        self.cache_info_label = tk.Label(cache_inner,
                                        text="",
                                        bg=COLORS['bg_primary'],
                                        fg=COLORS['text_secondary'],
                                        font=FONTS['body'])
        self.cache_info_label.pack(side=tk.LEFT)
        
        ttk.Button(cache_inner, text="Clear Cache",
                  command=self._clear_cache).pack(side=tk.RIGHT)
        ttk.Button(cache_inner, text="Refresh",
                  command=self._update_cache_info).pack(side=tk.RIGHT, padx=5)
        
        # About Section
        about_frame = tk.LabelFrame(inner,
                                   text=" About ",
                                   bg=COLORS['bg_primary'],
                                   fg=COLORS['accent'],
                                   font=FONTS['heading'])
        about_frame.pack(fill=tk.X)
        
        tk.Label(about_frame,
                text="Tarot Journal v0.2.1\nA journaling app for tarot, lenormand, and oracle readings.",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                font=FONTS['body'],
                justify=tk.LEFT).pack(anchor='w', padx=10, pady=10)
        
        # Initialize settings data
        self._refresh_presets_list()
        self._update_cache_info()
    
    # ═══════════════════════════════════════════
    # DATA REFRESH METHODS
    # ═══════════════════════════════════════════
    def _refresh_all(self):
        self._refresh_entries_list()
        self._refresh_decks_list()
        self._refresh_spreads_list()
        self._refresh_tags_list()
    
    def _refresh_entries_list(self):
        self.entries_tree.delete(*self.entries_tree.get_children())
        
        search = self.search_var.get() if hasattr(self, 'search_var') else None
        tag_name = self.filter_tag_var.get() if hasattr(self, 'filter_tag_var') else 'All Tags'
        
        tag_ids = None
        if tag_name != 'All Tags':
            tags = self.db.get_tags()
            for tag in tags:
                if tag['name'] == tag_name:
                    tag_ids = [tag['id']]
                    break
        
        if search or tag_ids:
            entries = self.db.search_entries(query=search if search else None, tag_ids=tag_ids)
        else:
            entries = self.db.get_entries()
        
        for entry in entries:
            date_str = entry['created_at'][:10] if entry['created_at'] else ''
            title = entry['title'] or '(Untitled)'
            self.entries_tree.insert('', 'end', iid=entry['id'], values=(date_str, title))
    
    def _refresh_decks_list(self):
        self.decks_tree.delete(*self.decks_tree.get_children())
        
        type_filter = self.type_filter_var.get() if hasattr(self, 'type_filter_var') else 'All'
        
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
            self.decks_tree.insert('', 'end', iid=deck['id'],
                                  values=(deck['name'], deck['cartomancy_type_name'], len(cards)))
        
        self._update_deck_combo()
    
    def _update_deck_combo(self):
        decks = self.db.get_decks()
        deck_names = [f"{d['name']} ({d['cartomancy_type_name']})" for d in decks]
        self.deck_combo['values'] = deck_names
        self._deck_id_map = {f"{d['name']} ({d['cartomancy_type_name']})": d['id'] for d in decks}
    
    def _refresh_spreads_list(self):
        self.spreads_list.delete(0, tk.END)
        spreads = self.db.get_spreads()
        for spread in spreads:
            self.spreads_list.insert(tk.END, spread['name'])
        
        spread_names = [s['name'] for s in spreads]
        self.spread_combo['values'] = spread_names
        self._spread_id_map = {s['name']: s['id'] for s in spreads}
    
    def _refresh_tags_list(self):
        tags = self.db.get_tags()
        tag_names = ['All Tags'] + [t['name'] for t in tags]
        self.filter_tag_combo['values'] = tag_names
        self._tags_cache = {t['name']: t for t in tags}
    
    def _refresh_cards_display(self, deck_id):
        # Clear existing
        for widget in self.cards_inner.winfo_children():
            widget.destroy()
        self.photo_refs.clear()
        self.selected_card_id = None
        
        if not deck_id:
            return
        
        cards = self.db.get_cards(deck_id)
        deck = self.db.get_deck(deck_id)
        
        if deck:
            self.deck_title_label.config(text=f"{deck['name']} ({deck['cartomancy_type_name']})")
        
        # Store card frames for selection highlighting
        self.card_frames = {}
        
        # Create card grid
        cols = 5
        for i, card in enumerate(cards):
            row = i // cols
            col = i % cols
            
            # Use a Button-like frame for better click handling
            card_frame = tk.Frame(self.cards_inner,
                                 bg=COLORS['bg_tertiary'],
                                 padx=2, pady=2,
                                 cursor='hand2')
            card_frame.grid(row=row, column=col, padx=6, pady=6, sticky='nsew')
            card_frame.card_id = card['id']  # Store card ID on frame
            
            self.card_frames[card['id']] = card_frame
            
            # Single click handler on frame that captures all clicks
            def on_click(e, cid=card['id']):
                self._select_card(cid)
                return "break"
            
            def on_double(e, cid=card['id']):
                self._edit_card(cid)
                return "break"
            
            card_frame.bind('<Button-1>', on_click)
            card_frame.bind('<Double-Button-1>', on_double)
            
            # Use thumbnail cache
            if card['image_path']:
                thumb_path = self.thumb_cache.get_thumbnail_path(card['image_path'])
                if thumb_path:
                    try:
                        img = Image.open(thumb_path)
                        # Scale to fit while preserving aspect ratio
                        max_width, max_height = 200, 300
                        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        self.photo_refs[card['id']] = photo

                        img_label = tk.Label(card_frame, image=photo,
                                           bg=COLORS['bg_tertiary'])
                        img_label.pack(padx=4, pady=4)
                        # Propagate clicks to parent frame
                        img_label.bind('<Button-1>', on_click)
                        img_label.bind('<Double-Button-1>', on_double)
                    except Exception:
                        self._create_placeholder(card_frame, card['id'])
                else:
                    self._create_placeholder(card_frame, card['id'])
            else:
                self._create_placeholder(card_frame, card['id'])
            
            name_label = tk.Label(card_frame,
                                 text=card['name'],
                                 bg=COLORS['bg_tertiary'],
                                 fg=COLORS['text_primary'],
                                 font=FONTS['small'],
                                 wraplength=100)
            name_label.pack(pady=(0, 4))
            # Propagate clicks to parent frame
            name_label.bind('<Button-1>', on_click)
            name_label.bind('<Double-Button-1>', on_double)
        
        # Configure grid weights
        for i in range(cols):
            self.cards_inner.columnconfigure(i, weight=1)
    
    def _select_card(self, card_id):
        """Select a card and highlight it"""
        # Unhighlight previous selection
        if self.selected_card_id and self.selected_card_id in self.card_frames:
            old_frame = self.card_frames[self.selected_card_id]
            old_frame.configure(bg=COLORS['bg_tertiary'])
            for widget in old_frame.winfo_children():
                try:
                    widget.configure(bg=COLORS['bg_tertiary'])
                except tk.TclError as e:
                    logger.debug("Could not update widget background: %s", e)
        
        # Highlight new selection
        self.selected_card_id = card_id
        if card_id in self.card_frames:
            new_frame = self.card_frames[card_id]
            new_frame.configure(bg=COLORS['accent_dim'])
            for widget in new_frame.winfo_children():
                try:
                    widget.configure(bg=COLORS['accent_dim'])
                except tk.TclError as e:
                    logger.debug("Could not update widget background: %s", e)
    
    def _create_placeholder(self, parent, card_id=None):
        placeholder = tk.Label(parent,
                              text="🂠",
                              font=('Arial', 48),
                              bg=COLORS['bg_tertiary'],
                              fg=COLORS['text_dim'],
                              width=5, height=2)
        placeholder.pack(padx=4, pady=4)
        if card_id:
            def on_click(e, cid=card_id):
                self._select_card(cid)
                return "break"
            def on_double(e, cid=card_id):
                self._edit_card(cid)
                return "break"
            placeholder.bind('<Button-1>', on_click)
            placeholder.bind('<Double-Button-1>', on_double)
    
    def _refresh_presets_list(self):
        self.presets_listbox.delete(0, tk.END)
        for name in self.presets.get_preset_names():
            self.presets_listbox.insert(tk.END, name)
    
    def _update_cache_info(self):
        count = self.thumb_cache.get_cache_count()
        size_mb = self.thumb_cache.get_cache_size() / (1024 * 1024)
        self.cache_info_label.config(text=f"{count} thumbnails cached ({size_mb:.1f} MB)")
    
    # ═══════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════
    def _on_entry_select(self, event):
        selection = self.entries_tree.selection()
        if not selection:
            return
        self._load_entry(int(selection[0]))
    
    def _load_entry(self, entry_id):
        self.current_entry_id = entry_id
        entry = self.db.get_entry(entry_id)
        
        if not entry:
            return
        
        self.title_var.set(entry['title'] or '')
        self.content_text.delete('1.0', tk.END)
        self.content_text.insert('1.0', entry['content'] or '')
        
        if entry['created_at']:
            try:
                dt = datetime.fromisoformat(entry['created_at'])
                self.date_label.config(text=dt.strftime('%B %d, %Y'))
            except (ValueError, TypeError) as e:
                logger.debug("Could not parse entry date: %s", e)
                self.date_label.config(text=entry['created_at'][:10])
        
        # Load readings
        readings = self.db.get_entry_readings(entry_id)
        if readings:
            reading = readings[0]
            if reading['spread_name']:
                self.spread_var.set(reading['spread_name'])
                self._draw_spread()
            if reading['deck_name']:
                for name, did in self._deck_id_map.items():
                    if reading['deck_name'] in name:
                        self.deck_var.set(name)
                        self.selected_deck_id = did
                        break
            
            if reading['cards_used']:
                cards_used = json.loads(reading['cards_used'])
                self.current_spread_cards = {}
                for i, card_name in enumerate(cards_used):
                    self.current_spread_cards[i] = {'name': card_name}
                self._update_cards_label()
                self._draw_spread()
        
        self._refresh_entry_tags()
    
    def _refresh_entry_tags(self):
        for widget in self.tags_container.winfo_children():
            widget.destroy()
        
        if not self.current_entry_id:
            return
        
        tags = self.db.get_entry_tags(self.current_entry_id)
        for tag in tags:
            tag_frame = tk.Frame(self.tags_container, bg=COLORS['accent_dim'])
            tag_frame.pack(side=tk.LEFT, padx=2, pady=2)
            
            tk.Label(tag_frame,
                    text=tag['name'],
                    bg=COLORS['accent_dim'],
                    fg=COLORS['text_primary'],
                    font=FONTS['small'],
                    padx=6, pady=2).pack(side=tk.LEFT)
            
            tk.Button(tag_frame,
                     text="×",
                     bg=COLORS['accent_dim'],
                     fg=COLORS['text_primary'],
                     font=FONTS['small'],
                     bd=0, padx=2,
                     command=lambda tid=tag['id']: self._remove_tag_from_entry(tid)).pack(side=tk.LEFT)
    
    def _on_spread_select(self, event):
        spread_name = self.spread_var.get()
        if spread_name and spread_name in self._spread_id_map:
            self.selected_spread_id = self._spread_id_map[spread_name]
            self.current_spread_cards = {}
            self._draw_spread()
    
    def _on_deck_select(self, event):
        deck_name = self.deck_var.get()
        if deck_name and deck_name in self._deck_id_map:
            self.selected_deck_id = self._deck_id_map[deck_name]
    
    def _draw_spread(self):
        self.spread_canvas.delete('all')
        
        spread_name = self.spread_var.get()
        if not spread_name or spread_name not in self._spread_id_map:
            return
        
        spread = self.db.get_spread(self._spread_id_map[spread_name])
        if not spread:
            return
        
        positions = json.loads(spread['positions'])
        
        for i, pos in enumerate(positions):
            x = pos.get('x', 0)
            y = pos.get('y', 0)
            w = pos.get('width', 80)
            h = pos.get('height', 120)
            label = pos.get('label', f'Position {i+1}')
            
            # Different fill for assigned vs empty
            if i in self.current_spread_cards:
                fill = COLORS['accent_dim']
                text_color = COLORS['text_primary']
                display = self.current_spread_cards[i].get('name', label)[:12]
            else:
                fill = COLORS['bg_tertiary']
                text_color = COLORS['text_secondary']
                display = label
            
            self.spread_canvas.create_rectangle(x, y, x + w, y + h,
                                               fill=fill,
                                               outline=COLORS['border'],
                                               width=2,
                                               tags=f'pos_{i}')
            
            self.spread_canvas.create_text(x + w/2, y + h/2,
                                          text=display,
                                          fill=text_color,
                                          font=FONTS['small'],
                                          width=w - 10,
                                          tags=f'text_{i}')
    
    def _on_canvas_click(self, event):
        spread_name = self.spread_var.get()
        if not spread_name or spread_name not in self._spread_id_map:
            return
        
        spread = self.db.get_spread(self._spread_id_map[spread_name])
        if not spread:
            return
        
        positions = json.loads(spread['positions'])
        
        for i, pos in enumerate(positions):
            x, y = pos.get('x', 0), pos.get('y', 0)
            w, h = pos.get('width', 80), pos.get('height', 120)
            
            if x <= event.x <= x + w and y <= event.y <= y + h:
                self._assign_card_to_position(i, pos.get('label', f'Position {i+1}'))
                break
    
    def _assign_card_to_position(self, pos_idx, pos_label):
        if not self.selected_deck_id:
            messagebox.showinfo("Select Deck", "Please select a deck first.")
            return
        
        cards = self.db.get_cards(self.selected_deck_id)
        if not cards:
            messagebox.showinfo("No Cards", "This deck has no cards.")
            return
        
        # Card selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Select: {pos_label}")
        dialog.geometry("350x450")
        dialog.configure(bg=COLORS['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog,
                text=f"Select card for: {pos_label}",
                font=FONTS['heading'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=15)
        
        # Search
        search_var = tk.StringVar()
        search_entry = tk.Entry(dialog,
                               textvariable=search_var,
                               bg=COLORS['bg_input'],
                               fg=COLORS['text_primary'],
                               insertbackground=COLORS['text_primary'],
                               relief=tk.FLAT)
        search_entry.pack(fill=tk.X, padx=20, ipady=6)
        search_entry.focus()
        
        # Listbox
        list_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        listbox = tk.Listbox(list_frame,
                            bg=COLORS['bg_secondary'],
                            fg=COLORS['text_primary'],
                            selectbackground=COLORS['accent_dim'],
                            font=FONTS['body'],
                            relief=tk.FLAT)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        def populate_list(*args):
            listbox.delete(0, tk.END)
            search_term = search_var.get().lower()
            for card in cards:
                if search_term in card['name'].lower():
                    listbox.insert(tk.END, card['name'])
        
        search_var.trace('w', populate_list)
        populate_list()
        
        def on_select(e=None):
            selection = listbox.curselection()
            if selection:
                card_name = listbox.get(selection[0])
                for card in cards:
                    if card['name'] == card_name:
                        self.current_spread_cards[pos_idx] = {
                            'id': card['id'],
                            'name': card['name'],
                            'image_path': card['image_path']
                        }
                        break
                self._draw_spread()
                self._update_cards_label()
                dialog.destroy()
        
        listbox.bind('<Double-Button-1>', on_select)
        
        ttk.Button(dialog,
                  text="Select",
                  command=on_select,
                  style='Accent.TButton').pack(pady=15)
    
    def _update_cards_label(self):
        if self.current_spread_cards:
            names = [c['name'] for c in self.current_spread_cards.values()]
            self.cards_label.config(text=f"Cards: {', '.join(names)}")
        else:
            self.cards_label.config(text="Click positions above to assign cards")
    
    def _on_deck_tree_select(self, event):
        selection = self.decks_tree.selection()
        if selection:
            self._refresh_cards_display(int(selection[0]))
    
    def _on_spread_list_select(self, event):
        selection = self.spreads_list.curselection()
        if not selection:
            return
        
        spread_name = self.spreads_list.get(selection[0])
        spreads = self.db.get_spreads()
        
        for spread in spreads:
            if spread['name'] == spread_name:
                self.editing_spread_id = spread['id']
                self.spread_name_var.set(spread['name'])
                self.spread_desc_var.set(spread['description'] or '')
                self.designer_positions = json.loads(spread['positions'])
                self._redraw_designer()
                break
    
    def _on_designer_press(self, event):
        """Handle mouse press - start dragging if on a position"""
        for i, pos in enumerate(self.designer_positions):
            x, y = pos['x'], pos['y']
            w, h = pos.get('width', 80), pos.get('height', 120)
            
            if x <= event.x <= x + w and y <= event.y <= y + h:
                # Start dragging this position
                self.drag_data['pos_idx'] = i
                self.drag_data['x'] = event.x - x
                self.drag_data['y'] = event.y - y
                # Change cursor
                self.designer_canvas.config(cursor='fleur')
                break
    
    def _on_designer_drag(self, event):
        """Handle mouse drag - move the position"""
        if self.drag_data['pos_idx'] is not None:
            idx = self.drag_data['pos_idx']
            
            # Calculate new position
            new_x = event.x - self.drag_data['x']
            new_y = event.y - self.drag_data['y']
            
            # Keep within canvas bounds
            canvas_width = self.designer_canvas.winfo_width()
            canvas_height = self.designer_canvas.winfo_height()
            w = self.designer_positions[idx].get('width', 80)
            h = self.designer_positions[idx].get('height', 120)
            
            new_x = max(0, min(new_x, canvas_width - w))
            new_y = max(0, min(new_y, canvas_height - h))
            
            # Update position
            self.designer_positions[idx]['x'] = new_x
            self.designer_positions[idx]['y'] = new_y
            
            # Redraw
            self._redraw_designer()
    
    def _on_designer_release(self, event):
        """Handle mouse release - stop dragging"""
        self.drag_data['pos_idx'] = None
        self.drag_data['x'] = 0
        self.drag_data['y'] = 0
        self.designer_canvas.config(cursor='')
    
    def _add_spread_position(self):
        """Add a new card position to the spread"""
        label = simpledialog.askstring("Position Label",
                                      "Enter label for this position:",
                                      parent=self.root)
        if label:
            # Find a good starting position (offset from existing cards)
            offset = len(self.designer_positions) * 20
            start_x = 50 + (offset % 400)
            start_y = 50 + (offset // 400) * 140
            
            self.designer_positions.append({
                'x': start_x,
                'y': start_y,
                'width': 80,
                'height': 120,
                'label': label
            })
            self._redraw_designer()
    
    def _on_designer_right_click(self, event):
        for i, pos in enumerate(self.designer_positions):
            x, y = pos['x'], pos['y']
            w, h = pos.get('width', 80), pos.get('height', 120)
            
            if x <= event.x <= x + w and y <= event.y <= y + h:
                if messagebox.askyesno("Delete", f"Delete '{pos['label']}'?"):
                    self.designer_positions.pop(i)
                    self._redraw_designer()
                break
    
    def _redraw_designer(self):
        self.designer_canvas.delete('all')
        
        for i, pos in enumerate(self.designer_positions):
            x, y = pos['x'], pos['y']
            w, h = pos.get('width', 80), pos.get('height', 120)
            label = pos.get('label', f'Position {i+1}')
            
            # Highlight if being dragged
            if self.drag_data['pos_idx'] == i:
                outline_color = COLORS['accent_hover']
                outline_width = 3
            else:
                outline_color = COLORS['accent']
                outline_width = 2
            
            # Draw card slot
            self.designer_canvas.create_rectangle(x, y, x + w, y + h,
                                                 fill=COLORS['bg_tertiary'],
                                                 outline=outline_color,
                                                 width=outline_width,
                                                 tags=f'pos_{i}')
            
            # Draw label
            self.designer_canvas.create_text(x + w/2, y + h/2,
                                            text=label,
                                            fill=COLORS['text_primary'],
                                            font=FONTS['small'],
                                            width=w - 10,
                                            tags=f'text_{i}')
            
            # Draw position number in corner
            self.designer_canvas.create_text(x + 12, y + 12,
                                            text=str(i + 1),
                                            fill=COLORS['text_dim'],
                                            font=FONTS['small'],
                                            tags=f'num_{i}')
    
    def _on_preset_select(self, event):
        selection = self.presets_listbox.curselection()
        if not selection:
            return
        
        preset_name = self.presets_listbox.get(selection[0])
        preset = self.presets.get_preset(preset_name)
        
        if preset:
            self.preset_details.config(state=tk.NORMAL)
            self.preset_details.delete('1.0', tk.END)
            
            details = f"Type: {preset.get('type', 'Unknown')}\n"
            details += f"Description: {preset.get('description', 'No description')}\n\n"
            details += f"Mappings: {len(preset.get('mappings', {}))} entries\n\n"
            
            # Show sample mappings
            mappings = preset.get('mappings', {})
            sample = list(mappings.items())[:10]
            if sample:
                details += "Sample mappings:\n"
                for key, value in sample:
                    details += f"  {key} → {value}\n"
                if len(mappings) > 10:
                    details += f"  ... and {len(mappings) - 10} more"
            
            self.preset_details.insert('1.0', details)
            self.preset_details.config(state=tk.DISABLED)
    
    # ═══════════════════════════════════════════
    # ACTION METHODS
    # ═══════════════════════════════════════════
    def _new_entry(self):
        entry_id = self.db.add_entry(title="New Entry")
        self._refresh_entries_list()
        self.current_entry_id = entry_id
        self.current_spread_cards = {}
        self.title_var.set("New Entry")
        self.content_text.delete('1.0', tk.END)
        self.date_label.config(text=datetime.now().strftime('%B %d, %Y'))
        self.spread_var.set('')
        self.deck_var.set('')
        self.spread_canvas.delete('all')
        self._refresh_entry_tags()
        
        self.entries_tree.selection_set(entry_id)
        self.entries_tree.see(entry_id)
    
    def _save_entry(self):
        if not self.current_entry_id:
            self._new_entry()
        
        title = self.title_var.get()
        content = self.content_text.get('1.0', tk.END).strip()
        
        self.db.update_entry(self.current_entry_id, title=title, content=content)
        
        # Save reading
        self.db.delete_entry_readings(self.current_entry_id)
        
        spread_name = self.spread_var.get()
        deck_name = self.deck_var.get()
        
        if spread_name or deck_name or self.current_spread_cards:
            spread_id = self._spread_id_map.get(spread_name)
            deck_id = self._deck_id_map.get(deck_name)
            
            cartomancy_type = None
            if deck_id:
                deck = self.db.get_deck(deck_id)
                if deck:
                    cartomancy_type = deck['cartomancy_type_name']
            
            cards_used = [c['name'] for c in self.current_spread_cards.values()]
            deck_name_clean = deck_name.split(' (')[0] if deck_name else None
            
            self.db.add_entry_reading(
                entry_id=self.current_entry_id,
                spread_id=spread_id,
                spread_name=spread_name,
                deck_id=deck_id,
                deck_name=deck_name_clean,
                cartomancy_type=cartomancy_type,
                cards_used=cards_used
            )
            
            # Auto-tags
            auto_tags = []
            if spread_name:
                auto_tags.append(f"Spread: {spread_name}")
            if deck_name_clean:
                auto_tags.append(f"Deck: {deck_name_clean}")
            if cartomancy_type:
                auto_tags.append(cartomancy_type)
            
            for tag_name in auto_tags:
                if tag_name not in self._tags_cache:
                    self.db.add_tag(tag_name)
                    self._refresh_tags_list()
                
                if tag_name in self._tags_cache:
                    self.db.add_entry_tag(self.current_entry_id, self._tags_cache[tag_name]['id'])
        
        self._refresh_entries_list()
        self._refresh_entry_tags()
        messagebox.showinfo("Saved", "Entry saved successfully!")
    
    def _delete_entry(self):
        if not self.current_entry_id:
            return
        
        if messagebox.askyesno("Delete Entry", "Delete this entry?"):
            self.db.delete_entry(self.current_entry_id)
            self.current_entry_id = None
            self.title_var.set('')
            self.content_text.delete('1.0', tk.END)
            self._refresh_entries_list()
    
    def _add_tag_to_entry(self):
        if not self.current_entry_id:
            messagebox.showinfo("No Entry", "Create or select an entry first.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Tag")
        dialog.geometry("300x400")
        dialog.configure(bg=COLORS['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog,
                text="Select or create a tag",
                font=FONTS['heading'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=15)
        
        tags = self.db.get_tags()
        listbox = tk.Listbox(dialog,
                            bg=COLORS['bg_secondary'],
                            fg=COLORS['text_primary'],
                            selectbackground=COLORS['accent_dim'],
                            font=FONTS['body'],
                            height=10,
                            relief=tk.FLAT)
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        for tag in tags:
            listbox.insert(tk.END, tag['name'])
        
        def select_tag():
            selection = listbox.curselection()
            if selection:
                tag = tags[selection[0]]
                self.db.add_entry_tag(self.current_entry_id, tag['id'])
                self._refresh_entry_tags()
            dialog.destroy()
        
        ttk.Button(dialog, text="Select", command=select_tag).pack(pady=5)
        
        tk.Label(dialog,
                text="Or create new:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary']).pack(pady=(15, 5))
        
        new_tag_var = tk.StringVar()
        tk.Entry(dialog,
                textvariable=new_tag_var,
                bg=COLORS['bg_input'],
                fg=COLORS['text_primary'],
                relief=tk.FLAT).pack(padx=20, fill=tk.X, ipady=4)
        
        def create_tag():
            name = new_tag_var.get().strip()
            if name:
                tag_id = self.db.add_tag(name)
                self.db.add_entry_tag(self.current_entry_id, tag_id)
                self._refresh_tags_list()
                self._refresh_entry_tags()
                dialog.destroy()
        
        ttk.Button(dialog, text="Create & Add", command=create_tag).pack(pady=15)
    
    def _remove_tag_from_entry(self, tag_id):
        if self.current_entry_id:
            self.db.remove_entry_tag(self.current_entry_id, tag_id)
            self._refresh_entry_tags()
    
    def _add_deck(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Deck")
        dialog.geometry("400x200")
        dialog.configure(bg=COLORS['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Deck Name:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary']).pack(pady=(20, 5))
        
        name_var = tk.StringVar()
        tk.Entry(dialog,
                textvariable=name_var,
                bg=COLORS['bg_input'],
                fg=COLORS['text_primary'],
                relief=tk.FLAT,
                width=40).pack(ipady=4)
        
        tk.Label(dialog, text="Type:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary']).pack(pady=(10, 5))
        
        type_var = tk.StringVar(value='Tarot')
        type_combo = ttk.Combobox(dialog,
                                 textvariable=type_var,
                                 values=['Tarot', 'Lenormand', 'Oracle'],
                                 state='readonly',
                                 width=20)
        type_combo.pack()
        
        def save():
            name = name_var.get().strip()
            if name:
                types = self.db.get_cartomancy_types()
                type_id = None
                for t in types:
                    if t['name'] == type_var.get():
                        type_id = t['id']
                        break
                if type_id:
                    self.db.add_deck(name, type_id)
                    self._refresh_decks_list()
                    dialog.destroy()
        
        ttk.Button(dialog,
                  text="Add Deck",
                  command=save,
                  style='Accent.TButton').pack(pady=20)
    
    def _import_deck_folder(self):
        folder = filedialog.askdirectory(title="Select folder with card images")
        if not folder:
            return
        
        # Import dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Import Deck")
        dialog.geometry("600x500")
        dialog.configure(bg=COLORS['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog,
                text="Import Deck from Folder",
                font=FONTS['heading'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=15)
        
        # Deck name
        name_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        name_frame.pack(fill=tk.X, padx=20)
        
        tk.Label(name_frame, text="Deck Name:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        
        name_var = tk.StringVar(value=Path(folder).name)
        tk.Entry(name_frame,
                textvariable=name_var,
                bg=COLORS['bg_input'],
                fg=COLORS['text_primary'],
                relief=tk.FLAT,
                width=30).pack(side=tk.LEFT, padx=10, ipady=4)
        
        # Preset selection
        preset_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        preset_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(preset_frame, text="Import Preset:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        
        preset_var = tk.StringVar(value="Standard Tarot (78 cards)")
        preset_combo = ttk.Combobox(preset_frame,
                                   textvariable=preset_var,
                                   values=self.presets.get_preset_names(),
                                   width=30,
                                   state='readonly')
        preset_combo.pack(side=tk.LEFT, padx=10)
        
        # Preview area
        tk.Label(dialog, text="Preview:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary']).pack(anchor='w', padx=20, pady=(10, 5))
        
        preview_frame = tk.Frame(dialog, bg=COLORS['bg_secondary'])
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        preview_list = tk.Listbox(preview_frame,
                                 bg=COLORS['bg_secondary'],
                                 fg=COLORS['text_primary'],
                                 font=FONTS['small'],
                                 relief=tk.FLAT)
        preview_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL,
                                 command=preview_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        preview_list.configure(yscrollcommand=scrollbar.set)
        
        def update_preview(*args):
            preview_list.delete(0, tk.END)
            preview = self.presets.preview_import(folder, preset_var.get())
            for orig, mapped, order in preview:
                preview_list.insert(tk.END, f"{orig} → {mapped}")
        
        preset_combo.bind('<<ComboboxSelected>>', update_preview)
        update_preview()
        
        def do_import():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Name Required", "Please enter a deck name.")
                return
            
            preset = self.presets.get_preset(preset_var.get())
            cart_type = preset.get('type', 'Oracle') if preset else 'Oracle'
            
            # Get type ID
            types = self.db.get_cartomancy_types()
            type_id = None
            for t in types:
                if t['name'] == cart_type:
                    type_id = t['id']
                    break
            
            if not type_id:
                type_id = types[0]['id']  # Fallback
            
            # Create deck
            deck_id = self.db.add_deck(name, type_id, folder)
            
            # Import cards
            preview = self.presets.preview_import(folder, preset_var.get())
            cards = []
            
            for orig_filename, mapped_name, order in preview:
                image_path = os.path.join(folder, orig_filename)
                cards.append((mapped_name, image_path, order))
            
            if cards:
                self.db.bulk_add_cards(deck_id, cards)
                
                # Pre-generate thumbnails
                image_paths = [c[1] for c in cards]
                self.thumb_cache.pregenerate_thumbnails(image_paths)
                
                messagebox.showinfo("Import Complete",
                                   f"Imported {len(cards)} cards into '{name}'")
            
            self._refresh_decks_list()
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(btn_frame, text="Cancel",
                  command=dialog.destroy).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Import",
                  command=do_import,
                  style='Accent.TButton').pack(side=tk.RIGHT)
    
    def _delete_deck(self):
        selection = self.decks_tree.selection()
        if not selection:
            return
        
        deck_id = int(selection[0])
        deck = self.db.get_deck(deck_id)
        
        if messagebox.askyesno("Delete Deck", f"Delete '{deck['name']}' and all cards?"):
            self.db.delete_deck(deck_id)
            self._refresh_decks_list()
            self._refresh_cards_display(None)
    
    def _add_card(self):
        selection = self.decks_tree.selection()
        if not selection:
            messagebox.showinfo("Select Deck", "Please select a deck first.")
            return
        
        deck_id = int(selection[0])
        
        name = simpledialog.askstring("Card Name", "Enter card name:", parent=self.root)
        if not name:
            return
        
        image_path = filedialog.askopenfilename(
            title="Select card image (optional)",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.gif *.webp")]
        )
        
        self.db.add_card(deck_id, name, image_path if image_path else None)
        
        if image_path:
            self.thumb_cache.get_thumbnail(image_path)
        
        self._refresh_cards_display(deck_id)
    
    def _import_cards(self):
        selection = self.decks_tree.selection()
        if not selection:
            messagebox.showinfo("Select Deck", "Please select a deck first.")
            return
        
        deck_id = int(selection[0])
        
        files = filedialog.askopenfilenames(
            title="Select card images",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.gif *.webp")]
        )
        
        if not files:
            return
        
        existing = self.db.get_cards(deck_id)
        order = len(existing)
        cards = []
        
        for filepath in files:
            name = Path(filepath).stem.replace('_', ' ').replace('-', ' ').title()
            cards.append((name, filepath, order))
            order += 1
        
        self.db.bulk_add_cards(deck_id, cards)
        
        # Pre-generate thumbnails
        self.thumb_cache.pregenerate_thumbnails([c[1] for c in cards])
        
        self._refresh_cards_display(deck_id)
        messagebox.showinfo("Import Complete", f"Imported {len(cards)} cards.")
    
    def _edit_card(self, card_id=None):
        """Edit a card's name and image"""
        if card_id is None:
            card_id = self.selected_card_id
        
        if not card_id:
            messagebox.showinfo("Select Card", "Please select a card to edit.")
            return
        
        # Get current deck
        selection = self.decks_tree.selection()
        if not selection:
            return
        deck_id = int(selection[0])
        
        # Find the card
        cards = self.db.get_cards(deck_id)
        card = None
        for c in cards:
            if c['id'] == card_id:
                card = c
                break
        
        if not card:
            return
        
        # Edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Card")
        dialog.geometry("450x200")
        dialog.configure(bg=COLORS['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog,
                text="Edit Card",
                font=FONTS['heading'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=15)
        
        # Name field
        name_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        name_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(name_frame, text="Name:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                width=12,
                anchor='e').pack(side=tk.LEFT)
        
        name_var = tk.StringVar(value=card['name'])
        name_entry = tk.Entry(name_frame,
                             textvariable=name_var,
                             bg=COLORS['bg_input'],
                             fg=COLORS['text_primary'],
                             relief=tk.FLAT,
                             width=30)
        name_entry.pack(side=tk.LEFT, padx=10, ipady=4)
        name_entry.focus()
        name_entry.select_range(0, tk.END)
        
        # Image path field
        image_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        image_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(image_frame, text="Image:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                width=12,
                anchor='e').pack(side=tk.LEFT)
        
        image_var = tk.StringVar(value=card['image_path'] or '')
        image_entry = tk.Entry(image_frame,
                              textvariable=image_var,
                              bg=COLORS['bg_input'],
                              fg=COLORS['text_primary'],
                              relief=tk.FLAT,
                              width=25)
        image_entry.pack(side=tk.LEFT, padx=10, ipady=4)
        
        def browse_image():
            path = filedialog.askopenfilename(
                title="Select card image",
                filetypes=[("Images", "*.jpg *.jpeg *.png *.gif *.webp")]
            )
            if path:
                image_var.set(path)
        
        ttk.Button(image_frame, text="Browse",
                  command=browse_image).pack(side=tk.LEFT)
        
        def save_changes():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("Name Required", "Card name cannot be empty.")
                return
            
            new_image = image_var.get().strip() or None
            
            self.db.update_card(card_id, name=new_name, image_path=new_image)
            
            # Regenerate thumbnail if image changed
            if new_image and new_image != card['image_path']:
                self.thumb_cache.get_thumbnail(new_image)
            
            self._refresh_cards_display(deck_id)
            dialog.destroy()
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        btn_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Button(btn_frame, text="Cancel",
                  command=dialog.destroy).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Save",
                  command=save_changes,
                  style='Accent.TButton').pack(side=tk.RIGHT)
        
        # Bind Enter key to save
        dialog.bind('<Return>', lambda e: save_changes())
    
    def _delete_card(self):
        """Delete the selected card"""
        if not self.selected_card_id:
            messagebox.showinfo("Select Card", "Please select a card to delete.")
            return
        
        selection = self.decks_tree.selection()
        if not selection:
            return
        deck_id = int(selection[0])
        
        # Find card name for confirmation
        cards = self.db.get_cards(deck_id)
        card_name = "this card"
        for c in cards:
            if c['id'] == self.selected_card_id:
                card_name = c['name']
                break
        
        if messagebox.askyesno("Delete Card", f"Delete '{card_name}'?"):
            self.db.delete_card(self.selected_card_id)
            self.selected_card_id = None
            self._refresh_cards_display(deck_id)
    
    def _new_spread(self):
        self.editing_spread_id = None
        self.spread_name_var.set('')
        self.spread_desc_var.set('')
        self.designer_positions = []
        self._redraw_designer()
    
    def _save_spread(self):
        name = self.spread_name_var.get().strip()
        if not name:
            messagebox.showwarning("Name Required", "Please enter a spread name.")
            return
        
        if not self.designer_positions:
            messagebox.showwarning("No Positions", "Add at least one card position.")
            return
        
        desc = self.spread_desc_var.get().strip()
        
        if self.editing_spread_id:
            self.db.update_spread(self.editing_spread_id, name=name,
                                 positions=self.designer_positions, description=desc)
        else:
            self.editing_spread_id = self.db.add_spread(name, self.designer_positions, desc)
        
        self._refresh_spreads_list()
        messagebox.showinfo("Saved", "Spread saved!")
    
    def _delete_spread(self):
        selection = self.spreads_list.curselection()
        if not selection:
            return
        
        spread_name = self.spreads_list.get(selection[0])
        
        if messagebox.askyesno("Delete Spread", f"Delete '{spread_name}'?"):
            spreads = self.db.get_spreads()
            for spread in spreads:
                if spread['name'] == spread_name:
                    self.db.delete_spread(spread['id'])
                    break
            
            self._refresh_spreads_list()
            self._new_spread()
    
    def _clear_spread_positions(self):
        self.designer_positions = []
        self._redraw_designer()
    
    def _create_preset(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Import Preset")
        dialog.geometry("600x550")
        dialog.configure(bg=COLORS['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog,
                text="Create Custom Import Preset",
                font=FONTS['heading'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=15)
        
        # Name
        name_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        name_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(name_frame, text="Name:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                width=12,
                anchor='e').pack(side=tk.LEFT)
        
        name_var = tk.StringVar()
        tk.Entry(name_frame,
                textvariable=name_var,
                bg=COLORS['bg_input'],
                fg=COLORS['text_primary'],
                relief=tk.FLAT,
                width=35).pack(side=tk.LEFT, padx=10, ipady=4)
        
        # Type
        type_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        type_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(type_frame, text="Type:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                width=12,
                anchor='e').pack(side=tk.LEFT)
        
        type_var = tk.StringVar(value='Oracle')
        ttk.Combobox(type_frame,
                    textvariable=type_var,
                    values=['Tarot', 'Lenormand', 'Oracle'],
                    state='readonly',
                    width=15).pack(side=tk.LEFT, padx=10)
        
        # Description
        desc_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        desc_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(desc_frame, text="Description:",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                width=12,
                anchor='e').pack(side=tk.LEFT)
        
        desc_var = tk.StringVar()
        tk.Entry(desc_frame,
                textvariable=desc_var,
                bg=COLORS['bg_input'],
                fg=COLORS['text_primary'],
                relief=tk.FLAT,
                width=35).pack(side=tk.LEFT, padx=10, ipady=4)
        
        # Mappings section
        tk.Label(dialog,
                text="Filename Mappings",
                font=FONTS['heading'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(anchor='w', padx=20, pady=(15, 5))
        
        tk.Label(dialog,
                text="Map filename patterns (without extension) to card names",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_dim'],
                font=FONTS['small']).pack(anchor='w', padx=20)
        
        # Mappings container with scrolling
        mappings_outer = tk.Frame(dialog, bg=COLORS['bg_secondary'])
        mappings_outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        mappings_canvas = tk.Canvas(mappings_outer,
                                   bg=COLORS['bg_secondary'],
                                   highlightthickness=0)
        mappings_scroll = ttk.Scrollbar(mappings_outer, orient=tk.VERTICAL,
                                       command=mappings_canvas.yview)
        mappings_inner = tk.Frame(mappings_canvas, bg=COLORS['bg_secondary'])
        
        mappings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mappings_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        mappings_canvas.configure(yscrollcommand=mappings_scroll.set)
        mappings_window = mappings_canvas.create_window((0, 0),
                                                       window=mappings_inner,
                                                       anchor='nw')
        
        def configure_mappings_scroll(e):
            mappings_canvas.configure(scrollregion=mappings_canvas.bbox('all'))
            mappings_canvas.itemconfig(mappings_window, width=mappings_canvas.winfo_width() - 4)
        
        mappings_inner.bind('<Configure>', configure_mappings_scroll)
        mappings_canvas.bind('<Configure>', lambda e: mappings_canvas.itemconfig(
            mappings_window, width=e.width - 4))
        
        # Header row
        header_frame = tk.Frame(mappings_inner, bg=COLORS['bg_secondary'])
        header_frame.pack(fill=tk.X, padx=5, pady=(5, 2))
        
        tk.Label(header_frame, text="Filename Pattern",
                bg=COLORS['bg_secondary'],
                fg=COLORS['text_secondary'],
                font=FONTS['small'],
                width=20,
                anchor='w').pack(side=tk.LEFT, padx=(5, 20))
        
        tk.Label(header_frame, text="Card Name",
                bg=COLORS['bg_secondary'],
                fg=COLORS['text_secondary'],
                font=FONTS['small'],
                width=25,
                anchor='w').pack(side=tk.LEFT)
        
        # Store mapping rows
        mapping_rows = []
        
        def add_mapping_row(filename='', cardname=''):
            row_frame = tk.Frame(mappings_inner, bg=COLORS['bg_secondary'])
            row_frame.pack(fill=tk.X, padx=5, pady=2)
            
            filename_var = tk.StringVar(value=filename)
            filename_entry = tk.Entry(row_frame,
                                     textvariable=filename_var,
                                     bg=COLORS['bg_input'],
                                     fg=COLORS['text_primary'],
                                     relief=tk.FLAT,
                                     width=20)
            filename_entry.pack(side=tk.LEFT, padx=(5, 10), ipady=3)
            
            tk.Label(row_frame, text="→",
                    bg=COLORS['bg_secondary'],
                    fg=COLORS['text_dim'],
                    font=FONTS['body']).pack(side=tk.LEFT, padx=5)
            
            cardname_var = tk.StringVar(value=cardname)
            cardname_entry = tk.Entry(row_frame,
                                     textvariable=cardname_var,
                                     bg=COLORS['bg_input'],
                                     fg=COLORS['text_primary'],
                                     relief=tk.FLAT,
                                     width=25)
            cardname_entry.pack(side=tk.LEFT, padx=(10, 5), ipady=3)
            
            def remove_row():
                row_frame.destroy()
                mapping_rows.remove(row_data)
            
            remove_btn = tk.Button(row_frame,
                                  text="×",
                                  bg=COLORS['bg_secondary'],
                                  fg=COLORS['danger'],
                                  font=FONTS['body'],
                                  bd=0,
                                  padx=8,
                                  command=remove_row)
            remove_btn.pack(side=tk.LEFT, padx=5)
            
            row_data = {'filename': filename_var, 'cardname': cardname_var, 'frame': row_frame}
            mapping_rows.append(row_data)
            return row_data
        
        # Add initial empty rows
        for _ in range(5):
            add_mapping_row()
        
        # Add row button
        add_btn_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        add_btn_frame.pack(fill=tk.X, padx=20)
        
        ttk.Button(add_btn_frame, text="+ Add Row",
                  command=lambda: add_mapping_row()).pack(side=tk.LEFT)
        
        ttk.Button(add_btn_frame, text="+ Add 10 Rows",
                  command=lambda: [add_mapping_row() for _ in range(10)]).pack(side=tk.LEFT, padx=10)
        
        def save_preset():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Name Required", "Please enter a preset name.")
                return
            
            # Collect mappings
            mappings = {}
            for row in mapping_rows:
                filename = row['filename'].get().strip()
                cardname = row['cardname'].get().strip()
                if filename and cardname:
                    # Normalize the filename key
                    key = filename.lower().replace(' ', '').replace('_', '').replace('-', '')
                    mappings[key] = cardname
            
            self.presets.add_custom_preset(
                name,
                type_var.get(),
                mappings,
                desc_var.get().strip()
            )
            
            self._refresh_presets_list()
            dialog.destroy()
        
        # Bottom buttons
        btn_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        btn_frame.pack(fill=tk.X, padx=20, pady=15)
        
        ttk.Button(btn_frame, text="Cancel",
                  command=dialog.destroy).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Save Preset",
                  command=save_preset,
                  style='Accent.TButton').pack(side=tk.RIGHT)
    
    def _delete_preset(self):
        selection = self.presets_listbox.curselection()
        if not selection:
            return
        
        preset_name = self.presets_listbox.get(selection[0])
        
        if not preset_name.startswith("Custom:"):
            messagebox.showwarning("Cannot Delete", "Built-in presets cannot be deleted.")
            return
        
        if messagebox.askyesno("Delete Preset", f"Delete '{preset_name}'?"):
            self.presets.delete_custom_preset(preset_name)
            self._refresh_presets_list()
    
    def _clear_cache(self):
        if messagebox.askyesno("Clear Cache",
                              "Clear all cached thumbnails? They will be regenerated as needed."):
            self.thumb_cache.clear_cache()
            self._update_cache_info()
            messagebox.showinfo("Cache Cleared", "Thumbnail cache cleared.")
    
    def _apply_theme_preset(self):
        """Apply a theme preset and save it"""
        preset_name = self.theme_preset_var.get()
        _theme.apply_preset(preset_name)
        _theme.save_theme()
        messagebox.showinfo("Theme Applied", 
                           f"'{preset_name}' theme applied.\n\nPlease restart the app for changes to take full effect.")
    
    def _open_theme_editor(self):
        """Open the theme customization dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Customize Theme")
        dialog.geometry("700x600")
        dialog.configure(bg=COLORS['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog,
                text="Customize Theme",
                font=FONTS['title'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=15)
        
        tk.Label(dialog,
                text="Edit colors using hex values (e.g., #1e2024). Changes require app restart.",
                bg=COLORS['bg_primary'],
                fg=COLORS['text_dim'],
                font=FONTS['small']).pack()
        
        # Create notebook for colors and fonts
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Colors tab
        colors_frame = tk.Frame(notebook, bg=COLORS['bg_primary'])
        notebook.add(colors_frame, text="  Colors  ")
        
        # Fonts tab
        fonts_frame = tk.Frame(notebook, bg=COLORS['bg_primary'])
        notebook.add(fonts_frame, text="  Fonts  ")
        
        # === Colors Tab Content ===
        colors_canvas = tk.Canvas(colors_frame, bg=COLORS['bg_primary'], highlightthickness=0)
        colors_scroll = ttk.Scrollbar(colors_frame, orient=tk.VERTICAL, command=colors_canvas.yview)
        colors_inner = tk.Frame(colors_canvas, bg=COLORS['bg_primary'])
        
        colors_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        colors_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        colors_canvas.configure(yscrollcommand=colors_scroll.set)
        colors_window = colors_canvas.create_window((0, 0), window=colors_inner, anchor='nw')
        
        colors_inner.bind('<Configure>', lambda e: colors_canvas.configure(scrollregion=colors_canvas.bbox('all')))
        colors_canvas.bind('<Configure>', lambda e: colors_canvas.itemconfig(colors_window, width=e.width - 4))
        
        # Color descriptions
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
            'success': 'Success (green)',
            'warning': 'Warning (orange)',
            'danger': 'Danger (red)',
            'card_slot': 'Card Slot Background',
        }
        
        color_vars = {}
        current_colors = _theme.get_colors()
        
        for i, (key, label) in enumerate(color_labels.items()):
            row = tk.Frame(colors_inner, bg=COLORS['bg_primary'])
            row.pack(fill=tk.X, padx=10, pady=4)
            
            tk.Label(row, text=label + ":",
                    bg=COLORS['bg_primary'],
                    fg=COLORS['text_secondary'],
                    font=FONTS['body'],
                    width=25,
                    anchor='e').pack(side=tk.LEFT)
            
            var = tk.StringVar(value=current_colors.get(key, '#000000'))
            color_vars[key] = var
            
            entry = tk.Entry(row,
                           textvariable=var,
                           bg=COLORS['bg_input'],
                           fg=COLORS['text_primary'],
                           relief=tk.FLAT,
                           width=10,
                           font=FONTS['mono'])
            entry.pack(side=tk.LEFT, padx=10, ipady=3)
            
            # Color preview swatch
            swatch = tk.Label(row, text="    ", bg=current_colors.get(key, '#000000'), width=4)
            swatch.pack(side=tk.LEFT, padx=5)
            
            # Update swatch when entry changes
            def update_swatch(sv=var, sw=swatch):
                try:
                    color = sv.get()
                    if color.startswith('#') and len(color) == 7:
                        sw.configure(bg=color)
                except (tk.TclError, ValueError) as e:
                    logger.debug("Could not update color swatch: %s", e)
            
            var.trace('w', lambda *args, sv=var, sw=swatch: update_swatch(sv, sw))
            
            # Color picker button
            def pick_color(v=var, s=swatch):
                from tkinter import colorchooser
                color = colorchooser.askcolor(color=v.get(), title="Choose Color")
                if color[1]:
                    v.set(color[1])
            
            ttk.Button(row, text="Pick", command=lambda v=var, s=swatch: pick_color(v, s)).pack(side=tk.LEFT, padx=5)
        
        # === Fonts Tab Content ===
        font_vars = {}
        current_fonts = _theme.get_fonts()
        
        # Font family section
        tk.Label(fonts_frame, text="Font Families",
                font=FONTS['heading'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(anchor='w', padx=10, pady=(10, 5))
        
        font_families = [
            ('family_display', 'Display Font (titles)'),
            ('family_text', 'Text Font (body)'),
            ('family_mono', 'Monospace Font'),
        ]
        
        common_fonts = ['SF Pro Display', 'SF Pro Text', 'SF Mono', 'Helvetica Neue', 
                       'Helvetica', 'Arial', 'Georgia', 'Times New Roman', 
                       'Menlo', 'Monaco', 'Consolas', 'Courier New']
        
        for key, label in font_families:
            row = tk.Frame(fonts_frame, bg=COLORS['bg_primary'])
            row.pack(fill=tk.X, padx=10, pady=4)
            
            tk.Label(row, text=label + ":",
                    bg=COLORS['bg_primary'],
                    fg=COLORS['text_secondary'],
                    font=FONTS['body'],
                    width=20,
                    anchor='e').pack(side=tk.LEFT)
            
            var = tk.StringVar(value=current_fonts.get(key, 'Arial'))
            font_vars[key] = var
            
            combo = ttk.Combobox(row, textvariable=var, values=common_fonts, width=20)
            combo.pack(side=tk.LEFT, padx=10)
        
        # Font size section
        tk.Label(fonts_frame, text="Font Sizes",
                font=FONTS['heading'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(anchor='w', padx=10, pady=(20, 5))
        
        font_sizes = [
            ('size_title', 'Title Size'),
            ('size_heading', 'Heading Size'),
            ('size_body', 'Body Size'),
            ('size_small', 'Small Text Size'),
        ]
        
        for key, label in font_sizes:
            row = tk.Frame(fonts_frame, bg=COLORS['bg_primary'])
            row.pack(fill=tk.X, padx=10, pady=4)
            
            tk.Label(row, text=label + ":",
                    bg=COLORS['bg_primary'],
                    fg=COLORS['text_secondary'],
                    font=FONTS['body'],
                    width=20,
                    anchor='e').pack(side=tk.LEFT)
            
            var = tk.IntVar(value=current_fonts.get(key, 12))
            font_vars[key] = var
            
            spin = tk.Spinbox(row, from_=8, to=48, textvariable=var, width=5,
                            bg=COLORS['bg_input'], fg=COLORS['text_primary'])
            spin.pack(side=tk.LEFT, padx=10)
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=COLORS['bg_primary'])
        btn_frame.pack(fill=tk.X, padx=20, pady=15)
        
        def save_theme():
            # Save colors
            for key, var in color_vars.items():
                _theme.set_color(key, var.get())
            
            # Save fonts
            for key, var in font_vars.items():
                if isinstance(var, tk.IntVar):
                    _theme.set_font(key, var.get())
                else:
                    _theme.set_font(key, var.get())
            
            _theme.save_theme()
            messagebox.showinfo("Theme Saved", 
                               "Theme saved successfully.\n\nPlease restart the app for changes to take full effect.")
            dialog.destroy()
        
        def export_theme():
            """Export theme as JSON for sharing"""
            filepath = filedialog.asksaveasfilename(
                title="Export Theme",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
            if filepath:
                import json
                theme_data = {
                    'colors': {k: v.get() for k, v in color_vars.items()},
                    'fonts': {k: (v.get() if isinstance(v, tk.StringVar) else v.get()) for k, v in font_vars.items()}
                }
                with open(filepath, 'w') as f:
                    json.dump(theme_data, f, indent=2)
                messagebox.showinfo("Exported", f"Theme exported to {filepath}")
        
        def import_theme():
            """Import theme from JSON"""
            filepath = filedialog.askopenfilename(
                title="Import Theme",
                filetypes=[("JSON files", "*.json")]
            )
            if filepath:
                try:
                    import json
                    with open(filepath, 'r') as f:
                        theme_data = json.load(f)
                    
                    if 'colors' in theme_data:
                        for key, value in theme_data['colors'].items():
                            if key in color_vars:
                                color_vars[key].set(value)
                    
                    if 'fonts' in theme_data:
                        for key, value in theme_data['fonts'].items():
                            if key in font_vars:
                                if isinstance(font_vars[key], tk.IntVar):
                                    font_vars[key].set(int(value))
                                else:
                                    font_vars[key].set(value)
                    
                    messagebox.showinfo("Imported", "Theme imported. Click Save to apply.")
                except Exception as e:
                    messagebox.showerror("Import Error", f"Failed to import theme: {e}")
        
        ttk.Button(btn_frame, text="Import...", command=import_theme).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Export...", command=export_theme).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="Save Theme", command=save_theme, style='Accent.TButton').pack(side=tk.RIGHT)
    
    def _show_stats(self):
        stats = self.db.get_stats()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Statistics")
        dialog.geometry("400x350")
        dialog.configure(bg=COLORS['bg_primary'])
        dialog.transient(self.root)
        
        tk.Label(dialog,
                text="Your Tarot Journey",
                font=FONTS['title'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=20)
        
        stats_text = f"""
Total Journal Entries: {stats['total_entries']}
Total Decks: {stats['total_decks']}
Total Cards: {stats['total_cards']}
Saved Spreads: {stats['total_spreads']}

Most Used Decks:
"""
        for deck in stats['top_decks']:
            stats_text += f"  • {deck[0]}: {deck[1]} readings\n"
        
        stats_text += "\nMost Used Spreads:\n"
        for spread in stats['top_spreads']:
            stats_text += f"  • {spread[0]}: {spread[1]} readings\n"
        
        tk.Label(dialog,
                text=stats_text,
                font=FONTS['body'],
                bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary'],
                justify=tk.LEFT).pack(padx=20, pady=10)
        
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=15)
    
    def run(self):
        self.root.mainloop()
        self.thumb_cache.stop_background_worker()
        self.db.close()


def main():
    logger.info("Tarot Journal (tkinter) starting")
    root = tk.Tk()
    app = TarotJournalApp(root)
    app.run()
    logger.info("Tarot Journal (tkinter) shutting down")


if __name__ == '__main__':
    main()

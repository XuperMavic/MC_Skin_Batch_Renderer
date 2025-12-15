import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
from PIL import Image, ImageTk
import os
import subprocess
import threading
import time

class SkinRendererApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MC Skin Batch Renderer")
        self.root.geometry("650x750")
        self.root.resizable(True, True)  # Allow window resizing
        self.root.minsize(450, 450)  # Set minimum window size: 450px width, 450px height
        
        # Set global theme colors
        self.bg_color = "#f0f0f0"
        self.card_bg = "#ffffff"
        self.text_color = "#333333"
        self.heading_color = "#2c3e50"
        self.accent_color = "#3498db"
        self.accent_hover = "#2980b9"
        self.success_color = "#27ae60"
        self.warning_color = "#f39c12"
        self.error_color = "#e74c3c"
        self.render_bg_color = '#00000000'  # Render background color (RGBA format, transparent)
        
        # Set window background color
        self.root.configure(bg=self.bg_color)
        
        # Initialize variables
        self.blender_file = ""
        self.skin_files = []  # Format: [{'path': 'skin_path', 'model': 'standard'}]
        self.output_dir = ""
        self.blender_path = ""
        self.is_rendering = False
        self.model_options = ['standard', 'slim']  # Available model options
        self.aspect_ratios = {'1:1': (1024, 1024), '4:3': (1024, 768), '3:4': (768, 1024), '16:9': (1024, 576), '9:16': (576, 1024)}
        self.selected_aspect_ratio = '1:1'
        self.render_devices = ['CPU', 'GPU']  # Available render devices
        self.selected_device = 'CPU'  # Default to CPU
        self.model_nums = ['1', '2', '3', '4', '5', 'a']  # Available model numbers
        # Model display names mapping
        self.model_names = {
            '1': '1-Front/Back_Right Hand on Hip',
            '2': '2-Front/Back_Running',
            '3': '3-Front/Back_Taekwondo Starting Position',
            '4': '4-Front/Back_Left Hand on Hip',
            '5': '5-Front_Twisting Waist with Hands Behind Back',
            'a': 'a-Scene_Desert Hut Villager Camel'
        }
        self.selected_model_num = '1'  # Default to model 1
        self.view_mode = 'list'  # 'list' or 'icon' view mode
        
        # Background image variables
        self.use_background_image = False
        self.background_image_path = ""
        self.background_image_var = tk.StringVar()
        self.background_image_var.set("No background image selected")
        self.background_image_check_var = tk.BooleanVar(value=self.use_background_image)
        
        # Icon view related variables
        self.icon_rows = []  # Store all row components in icon view
        self.icon_images = []  # Store PhotoImage objects to prevent GC
        self.selected_icon_index = None  # Currently selected icon index (single selection mode)
        self.selected_icon_indices = set()  # Store multiple selected icon indices
        self.icon_frame_window = None  # Canvas window object ID
        
        # Create main scrollable frame
        self.create_scrollable_frame()
        # Create interface
        self.create_widgets()
        # Create context menu
        self.create_context_menu()
        
    def create_scrollable_frame(self):
        """Create main frame with scrollbar"""
        # Create main frame
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create scrollbar style
        style = ttk.Style()
        style.configure("Modern.Vertical.TScrollbar", 
                       gripcount=0,
                       background=self.accent_color,
                       troughcolor="#e0e0e0",
                       arrowcolor=self.heading_color)
        
        # Create scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, style="Modern.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas
        self.canvas = tk.Canvas(main_frame, yscrollcommand=scrollbar.set, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=self.canvas.yview)
        
        # Create scrollable content frame
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_color)
        # Save window item ID
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        
        # Bind content change event
        def on_frame_configure(event):
            # Update scroll area
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        
        # Bind window resize event to make content adapt to width
        def on_window_resize(event):
            # Get main frame width
            new_width = main_frame.winfo_width() - 20  # Subtract scrollbar width
            # Update canvas width
            self.canvas.itemconfigure(self.canvas_window, width=new_width)
        
        # Bind window resize event
        self.root.bind("<Configure>", on_window_resize)
        
        # Bind mouse wheel events
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel events"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def create_widgets(self):
        # Set global style
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('TLabel', font=('Arial', 10))
        
        # Title
        title_label = tk.Label(self.scrollable_frame, text="MC Skin Batch Renderer", font= ("Arial", 18, "bold"), fg="#336699")
        title_label.pack(pady=15)
        
        # Add separator
        ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # Blender Path Settings
        path_frame = tk.Frame(self.scrollable_frame, 
                              relief=tk.FLAT, 
                              borderwidth=0,
                              bg=self.bg_color)
        path_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # Create card container
        path_card = tk.Frame(path_frame, 
                            bg=self.card_bg,
                            relief=tk.FLAT,
                            borderwidth=1,
                            padx=20,
                            pady=15)
        path_card.pack(fill=tk.X, padx=5, pady=5)
        
        # Add rounded corners (implemented via Canvas)
        self.add_rounded_corners(path_card, 10)
        
        tk.Label(path_card, 
                 text="Blender Path", 
                 font= ("Arial", 12, "bold"),
                 fg=self.heading_color,
                 bg=self.card_bg).pack(anchor=tk.W)
        
        # Add hint text
        tk.Label(path_card, 
                 text="Note: Select blender.exe file", 
                 font= ("Arial", 9, "italic"),
                 fg="#7f8c8d",
                 bg=self.card_bg).pack(anchor=tk.W, pady=(0, 10))
        
        path_row = tk.Frame(path_card, bg=self.card_bg)
        path_row.pack(fill=tk.X, pady=5)
        
        self.path_entry = tk.Entry(path_row, 
                                  font=("Arial", 10), 
                                  relief=tk.FLAT,
                                  borderwidth=1,
                                  bg="#f8f9fa",
                                  fg=self.text_color,
                                  highlightthickness=2,
                                  highlightcolor=self.accent_color,
                                  highlightbackground="#ddd")
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_path_btn = ttk.Button(path_row, 
                                    text="Browse", 
                                    command=self.browse_blender_path,
                                    style='TButton')
        browse_path_btn.pack(side=tk.RIGHT)
        
        # Add separator
        ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # Skin File Selection
        skin_frame = tk.Frame(self.scrollable_frame, 
                              bg=self.bg_color)
        skin_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Create card container
        skin_card = tk.Frame(skin_frame, 
                            bg=self.card_bg,
                            relief=tk.FLAT,
                            borderwidth=1,
                            padx=20,
                            pady=15)
        skin_card.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add rounded corners
        self.add_rounded_corners(skin_card, 10)
        
        # Set grid layout
        skin_card.grid_rowconfigure(0, weight=0)
        skin_card.grid_rowconfigure(1, weight=0)
        skin_card.grid_rowconfigure(2, weight=0)
        skin_card.grid_rowconfigure(3, weight=0)
        skin_card.grid_rowconfigure(4, weight=1)  # List area is expandable
        skin_card.grid_rowconfigure(5, weight=0)
        skin_card.grid_rowconfigure(6, weight=0)
        skin_card.grid_columnconfigure(0, weight=1)
        
        # Skin header
        skin_header = tk.Frame(skin_card, bg=self.card_bg)
        skin_header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        tk.Label(skin_header, 
                text="Skin Management", 
                font=("Arial", 12, "bold"), 
                fg=self.heading_color,
                bg=self.card_bg).pack(anchor=tk.W)
        
        # Skin operation buttons
        skin_buttons = tk.Frame(skin_card, bg=self.card_bg)
        skin_buttons.grid(row=1, column=0, sticky='ew', pady=5)
        
        browse_skins_btn = ttk.Button(skin_buttons, 
                                     text="Batch Select Skins", 
                                     command=self.browse_skin_files,
                                     style='TButton')
        browse_skins_btn.pack(side=tk.LEFT, padx=5)
        
        clear_skins_btn = ttk.Button(skin_buttons, 
                                    text="Clear All", 
                                    command=self.clear_skin_files,
                                    style='TButton')
        clear_skins_btn.pack(side=tk.LEFT, padx=5)
        
        delete_skin_btn = ttk.Button(skin_buttons, 
                                    text="Delete Selected", 
                                    command=self.delete_selected_skins,
                                    style='TButton')
        delete_skin_btn.pack(side=tk.LEFT, padx=5)
        
        # Hint information
        self.tip_label = tk.Label(skin_card, 
                text="Note: Right-click to select model type [Standard]/[Slim]", 
                font=('Arial', 9, 'italic'), 
                fg="#7f8c8d",
                bg=self.card_bg)
        self.tip_label.grid(row=2, column=0, sticky='w', pady=(5, 10))
        
        # View switch buttons
        view_frame = tk.Frame(skin_card, bg=self.card_bg)
        view_frame.grid(row=3, column=0, sticky='e', pady=(0, 5))
        
        self.list_view_btn = ttk.Button(view_frame, 
                                       text="List View", 
                                       command=lambda: self.switch_view('list'),
                                       style='TButton')
        self.list_view_btn.pack(side=tk.LEFT, padx=5)
        
        self.icon_view_btn = ttk.Button(view_frame, 
                                       text="Icon View", 
                                       command=lambda: self.switch_view('icon'),
                                       style='TButton')
        self.icon_view_btn.pack(side=tk.LEFT, padx=5)
        
        # Skin file list and model selection
        list_frame = tk.Frame(skin_card, bg=self.card_bg)
        list_frame.grid(row=4, column=0, sticky='nsew', pady=(0, 2))
        self.list_frame = list_frame
        
        # Add draggable divider (moved below file table)
        self.divider = tk.Frame(skin_card, height=5, bg='#cccccc', cursor='sb_v_double_arrow')
        self.divider.grid(row=5, column=0, sticky='ew', pady=2)
        
        # Bind mouse events for divider
        self.divider.bind('<Button-1>', self.start_resize)
        self.divider.bind('<B1-Motion>', self.on_resize)
        self.divider.bind('<ButtonRelease-1>', self.stop_resize)
        
        # Record initial state
        self.is_resizing = False
        self.initial_y = 0
        self.min_list_height = 100
        self.max_list_height = 500
        
        # Add size change event listener for skin_card
        skin_card.bind('<Configure>', self.on_skin_card_resize)
        
        # Create Treeview to display skins and model selection (list view)
        columns = ('#1', '#2', '#3')
        
        # Set Treeview style
        self.style.configure("Modern.Treeview",
                           background="white",
                           foreground=self.text_color,
                           rowheight=25,
                           fieldbackground="white",
                           font=('Arial', 10))
        
        self.style.configure("Modern.Treeview.Heading",
                           background="white",
                           foreground="black",
                           font=('Arial', 10, 'bold'),
                           padding=6)
        
        self.skin_tree = ttk.Treeview(list_frame, 
                                     columns=columns, 
                                     show='headings', 
                                     selectmode='extended',
                                     style="Modern.Treeview")
        
        self.skin_tree.heading('#1', text='No.')
        self.skin_tree.heading('#2', text='Skin Filename')
        self.skin_tree.heading('#3', text='Model Type')
        
        # Set column widths
        self.skin_tree.column('#1', width=50, anchor='center', stretch=False)
        self.skin_tree.column('#2', width=300, anchor='w', stretch=True)
        self.skin_tree.column('#3', width=150, anchor='center', stretch=False)
        
        # Only add vertical scrollbar, remove unnecessary horizontal scrollbar
        self.list_scrollbar = ttk.Scrollbar(list_frame, 
                                           orient=tk.VERTICAL, 
                                           command=self.skin_tree.yview,
                                           style="Modern.Vertical.TScrollbar")
        self.skin_tree.configure(yscrollcommand=self.list_scrollbar.set)
        
        # Layout - Ensure Treeview fills the space
        self.skin_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Icon view uses Canvas for scrolling
        self.icon_canvas = tk.Canvas(list_frame, bg=self.card_bg, highlightthickness=0)
        self.icon_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.icon_canvas.pack_forget()  # Initially hide icon view
        
        # Icon view container (placed inside Canvas)
        self.icon_frame = tk.Frame(self.icon_canvas, bg=self.card_bg)
        # Save window ID
        self.icon_frame_window = self.icon_canvas.create_window((0, 0), window=self.icon_frame, anchor="nw")
        
        # Icon view scrollbar
        self.icon_scrollbar = ttk.Scrollbar(list_frame, 
                                           orient=tk.VERTICAL, 
                                           command=self.icon_canvas.yview,
                                           style="Modern.Vertical.TScrollbar")
        self.icon_canvas.configure(yscrollcommand=self.icon_scrollbar.set)
        self.icon_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.icon_scrollbar.pack_forget()  # Initially hide icon view scrollbar
        
        # Bind Canvas scroll events
        self.icon_frame.bind("<Configure>", lambda e: self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all")))
        self.icon_canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # Listen to Canvas size changes to adjust icon_frame width
        self.icon_canvas.bind("<Configure>", self.on_canvas_resize)
        
        # Bind left click event
        self.skin_tree.bind("<Button-1>", self.on_treeview_click)
        
        # Bind right-click menu event
        self.skin_tree.bind("<Button-3>", self.show_context_menu)
        
        # Create context menu
        
        # Add separator
        ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # Output directory
        output_frame = tk.Frame(self.scrollable_frame, 
                               bg=self.bg_color)
        output_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # Create card container
        output_card = tk.Frame(output_frame, 
                              bg=self.card_bg,
                              relief=tk.FLAT,
                              borderwidth=1,
                              padx=20,
                              pady=15)
        output_card.pack(fill=tk.X, padx=5, pady=5)
        
        # Add rounded corners
        self.add_rounded_corners(output_card, 10)
        
        tk.Label(output_card, 
                text="Output Directory:", 
                font=("Arial", 12, "bold"), 
                fg=self.heading_color,
                bg=self.card_bg).pack(anchor=tk.W, pady=(0, 10))
        
        output_row = tk.Frame(output_card, bg=self.card_bg)
        output_row.pack(fill=tk.X, pady=5)
        
        self.output_entry = tk.Entry(output_row, 
                                    font=("Arial", 10), 
                                    relief=tk.FLAT,
                                    borderwidth=1,
                                    bg="#f8f9fa",
                                    fg=self.text_color,
                                    highlightthickness=2,
                                    highlightcolor=self.accent_color,
                                    highlightbackground="#ddd")
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_output_btn = ttk.Button(output_row, 
                                      text="Browse", 
                                      command=self.browse_output_dir,
                                      style='TButton')
        browse_output_btn.pack(side=tk.RIGHT)
        
        # Add separator
        ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # Render control area
        render_frame = tk.Frame(self.scrollable_frame, 
                               bg=self.bg_color)
        render_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # Create card container
        render_card = tk.Frame(render_frame, 
                              bg=self.card_bg,
                              relief=tk.FLAT,
                              borderwidth=1,
                              padx=20,
                              pady=15)
        render_card.pack(fill=tk.X, padx=5, pady=5)
        
        # Add rounded corners
        self.add_rounded_corners(render_card, 10)
        
        tk.Label(render_card, 
                text="Render Control", 
                font= ("Arial", 12, "bold"), 
                fg=self.heading_color,
                bg=self.card_bg).pack(anchor=tk.W, pady=(0, 15))
        
        # Image ratio selection
        ratio_row = tk.Frame(render_card, bg=self.card_bg)
        ratio_row.pack(fill=tk.X, pady=10)
        
        tk.Label(ratio_row, 
                text="Output Image Ratio:", 
                font= ("Arial", 10), 
                fg=self.text_color,
                bg=self.card_bg).pack(side=tk.LEFT, padx=5)
        
        self.ratio_var = tk.StringVar(value=self.selected_aspect_ratio)
        ratio_menu = ttk.Combobox(ratio_row, 
                                 textvariable=self.ratio_var,
                                 values=list(self.aspect_ratios.keys()),
                                 state="readonly",
                                 font= ("Arial", 10))
        ratio_menu.pack(side=tk.LEFT, padx=5)
        ratio_menu.bind("<<ComboboxSelected>>", self.on_ratio_selected)
        
        # Render device selection
        device_row = tk.Frame(render_card, bg=self.card_bg)
        device_row.pack(fill=tk.X, pady=10)
        
        tk.Label(device_row, 
                text="Render Device:", 
                font= ("Arial", 10), 
                fg=self.text_color,
                bg=self.card_bg).pack(side=tk.LEFT, padx=5)
        
        self.device_var = tk.StringVar(value=self.selected_device)
        device_menu = ttk.Combobox(device_row, 
                                 textvariable=self.device_var,
                                 values=self.render_devices,
                                 state="readonly",
                                 font= ("Arial", 10))
        device_menu.pack(side=tk.LEFT, padx=5)
        
        # Model number selection
        model_num_row = tk.Frame(render_card, bg=self.card_bg)
        model_num_row.pack(fill=tk.X, pady=10)
        
        tk.Label(model_num_row, 
                text="Model Type:", 
                font= ("Arial", 10), 
                fg=self.text_color,
                bg=self.card_bg).pack(side=tk.LEFT, padx=5)
        
        self.model_num_var = tk.StringVar(value=self.selected_model_num)
        # Create display names list
        model_display_names = [self.model_names[num] for num in self.model_nums]
        model_num_menu = ttk.Combobox(model_num_row, 
                                    textvariable=self.model_num_var,
                                    values=model_display_names,
                                    state="readonly",
                                    font= ("Arial", 10),
                                    width=40)
        model_num_menu.pack(side=tk.LEFT, padx=5)
        
        # Bind selection event to convert display name back to model number
        def on_model_select(event):
            selected_name = model_num_menu.get()
            for num, name in self.model_names.items():
                if name == selected_name:
                    self.model_num_var.set(num)
                    self.selected_model_num = num
                    break
        model_num_menu.bind("<<ComboboxSelected>>", on_model_select)
        
        # Render background color settings
        color_row = tk.Frame(render_card, bg=self.card_bg)
        color_row.pack(fill=tk.X, pady=10)
        
        tk.Label(color_row, 
                text="Render Background Color:", 
                font=("Arial", 10), 
                fg=self.text_color,
                bg=self.card_bg).pack(side=tk.LEFT, padx=5)
        
        # Current background color display
        self.color_display = tk.Label(color_row, 
                                     width=10, 
                                     bg="#FFFFFF" if self.render_bg_color == "#00000000" else self.render_bg_color, 
                                     relief=tk.RAISED,
                                     borderwidth=1)
        self.color_display.pack(side=tk.LEFT, padx=5)
        
        # Color selection button
        color_btn = ttk.Button(color_row, 
                              text="Choose Color", 
                              command=self.choose_bg_color)
        color_btn.pack(side=tk.LEFT, padx=5)
        
        # No background color button
        no_bg_btn = ttk.Button(color_row, 
                             text="No Background", 
                             command=self.set_no_bg_color)
        no_bg_btn.pack(side=tk.LEFT, padx=5)
        
        # Background image settings
        bg_image_row = tk.Frame(render_card, bg=self.card_bg)
        bg_image_row.pack(fill=tk.X, pady=10)
        
        # Use background image checkbox
        self.bg_image_check = tk.Checkbutton(bg_image_row, 
                                           text="Use Background Image:", 
                                           variable=self.background_image_check_var,
                                           command=self.toggle_background_image,
                                           font= ("Arial", 10), 
                                           fg=self.text_color,
                                           bg=self.card_bg)
        self.bg_image_check.pack(side=tk.LEFT, padx=5)
        
        # Background image path display
        self.bg_image_path_label = tk.Label(bg_image_row, 
                                           textvariable=self.background_image_var,
                                           font=("Arial", 10), 
                                           fg=self.text_color,
                                           bg="#f8f9fa",
                                           relief=tk.SUNKEN,
                                           borderwidth=1,
                                           anchor=tk.W,
                                           padx=5)
        self.bg_image_path_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Browse background image button
        browse_bg_btn = ttk.Button(bg_image_row, 
                                 text="Browse", 
                                 command=self.browse_background_image)
        browse_bg_btn.pack(side=tk.LEFT, padx=5)
        
        # Render button
        btn_row = tk.Frame(render_card, bg=self.card_bg)
        btn_row.pack(fill=tk.X, pady=10)
        
        self.render_btn = ttk.Button(btn_row, 
                                   text="Start Batch Render", 
                                   command=self.start_rendering, 
                                   style='Accent.TButton')
        self.render_btn.pack(fill=tk.X, ipady=2)
        
        # Progress bar
        progress_row = tk.Frame(render_card, bg=self.card_bg)
        progress_row.pack(fill=tk.X, pady=10)
        
        # Set progress bar style
        self.style.configure("Modern.Horizontal.TProgressbar",
                           background=self.accent_color,
                           troughcolor="#e0e0e0",
                           borderwidth=0,
                           relief=tk.FLAT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_row, 
                                           variable=self.progress_var, 
                                           maximum=100, 
                                           length=200,
                                           style="Modern.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X)
        
        # Status label
        status_row = tk.Frame(render_card, bg=self.card_bg)
        status_row.pack(fill=tk.X, pady=10)
        
        self.status_var = tk.StringVar()
        # Initial state is empty, don't show "Ready"
        self.status_var.set("")
        self.status_label = tk.Label(status_row, 
                                    textvariable=self.status_var, 
                                    font= ("Arial", 10, "bold"), 
                                    fg=self.success_color,
                                    bg=self.card_bg)
        self.status_label.pack(anchor=tk.W)
        
        # Render time prediction label
        time_row = tk.Frame(render_card, bg=self.card_bg)
        time_row.pack(fill=tk.X, pady=10)
        
        self.time_var = tk.StringVar()
        self.time_var.set("")
        self.time_label = tk.Label(time_row, 
                                  textvariable=self.time_var, 
                                  font= ("Arial", 10), 
                                  fg=self.text_color,
                                  bg=self.card_bg)
        self.time_label.pack(anchor=tk.W)
        
        # Bottom padding
        tk.Frame(self.scrollable_frame, height=20, bg=self.bg_color).pack()
        
    def add_rounded_corners(self, widget, radius):
        """Add rounded corners to widgets"""
        # Get widget dimensions
        x, y, width, height = widget.bbox("all")
        
        # Create a canvas as background
        canvas = tk.Canvas(widget, width=width, height=height, bg=self.bg_color, highlightthickness=0)
        canvas.place(x=0, y=0)
        
        # Draw rounded rectangle
        r = radius
        points = [r, 0, width-r, 0,
                 width, 0, width, r,
                 width, height-r, width, height,
                 width-r, height, r, height,
                 0, height, 0, height-r,
                 0, r, 0, 0]
        canvas.create_polygon(points, fill=self.card_bg, outline="")
        
        # Lift widget above canvas
        widget.lift()
    
    def browse_blender_path(self):
        """Browse and select Blender executable path"""
        file_path = filedialog.askopenfilename(
            title="Select Blender Executable",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if file_path:
            self.blender_path = file_path
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, file_path)
    
    def select_model(self, model_type):
        """Select preset model type"""
        # This method is now mainly for compatibility, actual model selection has been moved to each skin
        messagebox.showinfo("Note", "Now use right-click menu to select model type for each skin individually")
    
    def browse_blender_file(self):
        """Browse and select custom Blender file"""
        # This method is now mainly for compatibility, actual model selection has been moved to each skin
        messagebox.showinfo("Note", "Now use right-click menu to select model type for each skin individually")
    
    def browse_skin_files(self):
        """Batch select skin images"""
        files = filedialog.askopenfilenames(
            title="Select Skin Images",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg"), ("All Files", "*.*")]
        )
        if files:
            # Add newly selected skins, default to standard model
            for file in files:
                self.skin_files.append({'path': file, 'model': 'standard'})
            self.update_skin_list()
    
    def clear_skin_files(self):
        """Clear all selected skin images"""
        self.skin_files = []
        self.update_skin_list()
    
    def delete_selected_skins(self):
        """Delete selected skins, support multi-select"""
        if self.view_mode == 'list':
            selected_items = self.skin_tree.selection()
            if not selected_items:
                messagebox.showinfo("Note", "Please select skins to delete first")
                return
            
            # Delete from largest index to smallest to avoid index confusion
            indices_to_delete = sorted([int(item.split('_')[-1]) for item in selected_items], reverse=True)
        else:
            # Icon view, check if any icons are selected
            if not hasattr(self, 'selected_icon_indices') or not self.selected_icon_indices:
                messagebox.showinfo("Note", "Please select skins to delete first")
                return
            
            # Delete from largest index to smallest to avoid index confusion
            indices_to_delete = sorted(self.selected_icon_indices, reverse=True)
        
        for idx in indices_to_delete:
            if 0 <= idx < len(self.skin_files):
                del self.skin_files[idx]
        
        # Reset selection status
        if hasattr(self, 'selected_icon_index'):
            self.selected_icon_index = None
        if hasattr(self, 'selected_icon_indices'):
            self.selected_icon_indices.clear()
        
        self.update_skin_list()
        messagebox.showinfo("Completed", f"Deleted {len(indices_to_delete)} selected skins")
    
    def on_ratio_selected(self, event):
        """Handle user selected image ratio"""
        self.selected_aspect_ratio = self.ratio_var.get()
        print(f"Selected ratio: {self.selected_aspect_ratio}")
    
    def choose_bg_color(self):
        """Choose render background color"""
        # Open color picker
        color_code = colorchooser.askcolor(title="Choose Render Background Color")
        if color_code and color_code[1]:
            # Update render background color
            self.render_bg_color = color_code[1]
            self.color_display.configure(bg=self.render_bg_color)
            # Clear transparent text
            self.color_display.config(text="")
    
    def set_no_bg_color(self):
        """Set transparent background color"""
        self.render_bg_color = "#00000000"  # Transparent background
        self.color_display.configure(bg="#ffffff")
        self.color_display.config(text="Transparent")
    
    def toggle_background_image(self):
        """Toggle background image usage"""
        self.use_background_image = self.background_image_check_var.get()
        
        # If using background image, automatically set render background to transparent
        if self.use_background_image:
            self.set_no_bg_color()
    
    def browse_background_image(self):
        """Browse and select background image"""
        file_path = filedialog.askopenfilename(
            title="Select Background Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All Files", "*.*")]
        )
        if file_path:
            self.background_image_path = file_path
            self.background_image_var.set(os.path.basename(file_path))
            # Automatically enable background image checkbox if an image is selected
            self.background_image_check_var.set(True)
            self.use_background_image = True
            # Set render background to transparent when background image is selected
            self.set_no_bg_color()
    
    def create_context_menu(self):
        """Create context menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Use Standard Model (Steve)", command=lambda: self.change_model('standard'))
        self.context_menu.add_command(label="Use Slim Model (Alex)", command=lambda: self.change_model('slim'))
    

    
    def on_treeview_click(self, event):
        """Handle Treeview left-click events, support multi-select toggle"""
        # Get clicked region and item
        region = self.skin_tree.identify_region(event.x, event.y)
        item = self.skin_tree.identify_row(event.y)
        
        # Toggle selection status on click
        if region == "cell" and item:
            if item in self.skin_tree.selection():
                # If already selected, deselect
                self.skin_tree.selection_remove(item)
            else:
                # If not selected, select
                self.skin_tree.selection_add(item)
    
    def change_model(self, model_type):
        """Change model type for selected skins, support multi-select"""
        if self.view_mode == 'list':
            selected_items = self.skin_tree.selection()
            if not selected_items:
                messagebox.showinfo("Note", "Please select skins to modify first")
                return
            
            for item in selected_items:
                # Get skin index
                skin_index = int(item.split('_')[-1])
                if 0 <= skin_index < len(self.skin_files):
                    # Update model type
                    self.skin_files[skin_index]['model'] = model_type
        else:
            # Icon view, check if any icons are selected
            if not hasattr(self, 'selected_icon_indices') or not self.selected_icon_indices:
                messagebox.showinfo("Note", "Please select skins to modify first")
                return
            
            for idx in self.selected_icon_indices:
                if 0 <= idx < len(self.skin_files):
                    # Update model type
                    self.skin_files[idx]['model'] = model_type
        
        self.update_skin_list()
        messagebox.showinfo("Completed", f"Changed selected skins model type to {model_type}")
    
    def switch_view(self, view_mode):
        """Switch between list view and icon view"""
        self.view_mode = view_mode
        
        if self.view_mode == 'list':
            # Show list view, hide icon view
            self.skin_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.skin_tree.bind("<Button-1>", self.on_treeview_click)
            self.skin_tree.bind("<Button-3>", self.show_context_menu)
            self.icon_canvas.pack_forget()
            self.icon_scrollbar.pack_forget()
        else:
            # Show icon view, hide list view
            self.skin_tree.pack_forget()
            self.list_scrollbar.pack_forget()
            self.skin_tree.unbind("<Button-1>")
            self.skin_tree.unbind("<Button-3>")
            self.icon_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.icon_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Update display
        self.update_skin_list()
    
    def on_skin_card_resize(self, event):
        """Update layout when skin_card size changes"""
        # Don't perform auto-adjustment if currently resizing
        if self.is_resizing:
            return
        
        # Ensure list area has minimum height
        if self.list_frame.winfo_height() < self.min_list_height:
            self.list_frame.master.grid_rowconfigure(4, minsize=self.min_list_height)
    
    def start_resize(self, event):
        """Start resizing"""
        self.is_resizing = True
        self.initial_y = event.y_root
        self.initial_list_height = self.list_frame.winfo_height()
        self.list_frame.master.grid_rowconfigure(4, minsize=0)  # Temporarily remove minimum height restriction
    
    def on_resize(self, event):
        """During resizing"""
        if not self.is_resizing:
            return
        
        # Calculate height change
        delta_y = event.y_root - self.initial_y
        
        # Calculate new height, ensuring it's between min and max height
        new_height = max(self.min_list_height, min(self.initial_list_height + delta_y, self.max_list_height))
        
        # Adjust list area height
        self.list_frame.master.grid_rowconfigure(4, minsize=new_height, weight=1)
        
        # Force layout update
        self.list_frame.master.update_idletasks()
    
    def stop_resize(self, event):
        """Stop resizing"""
        self.is_resizing = False
        # Keep final height as new minimum height
        final_height = max(self.min_list_height, self.list_frame.winfo_height())
        self.list_frame.master.grid_rowconfigure(4, minsize=final_height, weight=1)
    
    def on_canvas_resize(self, event):
        """Adjust icon_frame width when Canvas size changes"""
        # Get Canvas width
        canvas_width = event.width
        # Subtract scrollbar width if visible
        if self.icon_scrollbar.winfo_ismapped():
            canvas_width -= self.icon_scrollbar.winfo_width()
        
        # Update window width in Canvas
        self.icon_canvas.itemconfigure(self.icon_frame_window, width=canvas_width)
        # Update icon_frame width
        self.icon_frame.configure(width=canvas_width)
        
        # Update scroll region
        self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all"))
        
        # Force layout update
        self.icon_frame.update_idletasks()
    
    def update_skin_list(self):
        """Update skin file list display"""
        if self.view_mode == 'list':
            # Clear Treeview
            for item in self.skin_tree.get_children():
                self.skin_tree.delete(item)
            
            # Add skin information
            for i, skin in enumerate(self.skin_files):
                filename = os.path.basename(skin['path'])
                model_name = skin['model']
                self.skin_tree.insert('', tk.END, iid=f'skin_{i}', values=(i+1, filename, model_name))
        else:
            # Clear icon view
            for widget in self.icon_frame.winfo_children():
                widget.destroy()
            
            # Set table layout for icon view
            self.icon_frame.grid_columnconfigure(0, weight=0, minsize=50)  # Index column - fixed width
            self.icon_frame.grid_columnconfigure(1, weight=0, minsize=80)  # Image column - fixed width
            self.icon_frame.grid_columnconfigure(2, weight=1, minsize=200)  # Filename - adaptive width (reduced minimum width)
            self.icon_frame.grid_columnconfigure(3, weight=0, minsize=100)  # Model type - fixed width (reduced minimum width)
            
            # Add table headers
            header_bg = "white"
            header_font = ('Arial', 10, 'bold')
            
            # Index header
            tk.Label(self.icon_frame, text="No.", bg=header_bg, font=header_font, relief=tk.RIDGE, padx=5).grid(
                row=0, column=0, sticky='nsew')
            # Image header
            tk.Label(self.icon_frame, text="Image", bg=header_bg, font=header_font, relief=tk.RIDGE, padx=5).grid(
                row=0, column=1, sticky='nsew')
            # Filename header
            tk.Label(self.icon_frame, text="Skin Filename", bg=header_bg, font=header_font, relief=tk.RIDGE, padx=5).grid(
                row=0, column=2, sticky='nsew')
            # Model type header
            tk.Label(self.icon_frame, text="Model", bg=header_bg, font=header_font, relief=tk.RIDGE, padx=5).grid(
                row=0, column=3, sticky='nsew')
            
            # Add skin data rows
            self.icon_images = []  # Store PhotoImage objects to prevent GC
            self.icon_rows = []  # Store all components related to rows
            
            for i, skin in enumerate(self.skin_files):
                filename = os.path.basename(skin['path'])
                model_name = skin['model']
                skin_path = skin['path']
                
                # Alternating row background color
                row_bg = "white" if i % 2 == 0 else "#f0f0f0"
                
                # Store all components for current row
                row_widgets = []
                
                # Index column
                number_label = tk.Label(self.icon_frame, text=str(i+1), bg=row_bg, font=('Arial', 10), relief=tk.RIDGE, padx=5, anchor='center')
                number_label.grid(row=i+1, column=0, sticky='nsew')
                row_widgets.append(number_label)
                
                # Image column
                try:
                    # Load skin image
                    image = Image.open(skin_path)
                    # Resize image to appropriate thumbnail size
                    image.thumbnail((60, 60), Image.LANCZOS)
                    # Create PhotoImage object
                    photo = ImageTk.PhotoImage(image)
                    
                    # Store PhotoImage object to prevent GC
                    self.icon_images.append(photo)
                    
                    # Add image preview
                    image_label = tk.Label(self.icon_frame, image=photo, bg=row_bg, relief=tk.RIDGE, padx=5)
                    image_label.grid(row=i+1, column=1, sticky='nsew', padx=1, pady=1)
                    row_widgets.append(image_label)
                    
                except Exception as e:
                    # If failed to load image, show placeholder
                    placeholder_label = tk.Label(self.icon_frame, text="Failed to Load", bg=row_bg, font=('Arial', 10), relief=tk.RIDGE, padx=5, anchor='center')
                    placeholder_label.grid(row=i+1, column=1, sticky='nsew', padx=1, pady=1)
                    row_widgets.append(placeholder_label)
                
                # Filename column
                name_label = tk.Label(self.icon_frame, text=filename, bg=row_bg, font=('Arial', 10), relief=tk.RIDGE, padx=5, anchor='w')
                name_label.grid(row=i+1, column=2, sticky='nsew', padx=1, pady=1)
                row_widgets.append(name_label)
                
                # Model type column
                model_label = tk.Label(self.icon_frame, text=model_name, bg=row_bg, font=('Arial', 10), 
                                      relief=tk.RIDGE, padx=5, anchor='center')
                model_label.grid(row=i+1, column=3, sticky='nsew', padx=1, pady=1)
                row_widgets.append(model_label)
                
                # Bind click events for all components in current row
                for widget in row_widgets:
                    widget.bind("<Button-1>", lambda event, idx=i: self.select_icon(idx))
                    widget.bind("<Button-3>", lambda event, idx=i: self.show_context_menu(event, idx))
                
                # Store all components for current row
                self.icon_rows.append(row_widgets)
            
            # Update scroll region
            self.icon_frame.update_idletasks()
            self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all"))
    
    def select_icon(self, idx):
        """Select skin in icon view, support multi-select toggle"""
        # Toggle selection status
        if idx in self.selected_icon_indices:
            # If already selected, deselect
            self.selected_icon_indices.remove(idx)
        else:
            # If not selected, select
            self.selected_icon_indices.add(idx)
        
        # Update selection status for all rows
        for row_idx, row_widgets in enumerate(self.icon_rows):
            # Restore row background color
            row_bg = "white" if row_idx % 2 == 0 else "#f0f0f0"
            for widget in row_widgets:
                if row_idx in self.selected_icon_indices:
                    # Highlight selected rows
                    widget.configure(bg="#a0c4ff", borderwidth=2, relief=tk.SUNKEN, highlightthickness=2)
                else:
                # Restore unselected state
                    widget.configure(bg=row_bg, borderwidth=1, relief=tk.RIDGE)
        
        # Trigger delete button status update
        if hasattr(self, 'delete_button'):
            if self.selected_icon_indices:
                self.delete_button.config(state=tk.NORMAL)
            else:
                self.delete_button.config(state=tk.DISABLED)
    
    def show_context_menu(self, event, idx=None):
        """Show context menu"""
        # If it's icon view, get clicked icon index
        if idx is not None:
            self.selected_icon_index = idx
        else:
            # List view, get clicked item
            item = self.skin_tree.identify_row(event.y)
            if item:
                self.skin_tree.selection_set(item)
        
        # Show menu
        self.context_menu.post(event.x_root, event.y_root)
    
    def browse_output_dir(self):
        """Browse and select output directory"""
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        if dir_path:
            self.output_dir = dir_path
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, dir_path)
    
    def validate_inputs(self):
        """Validate inputs are complete"""
        if not self.blender_path:
            messagebox.showerror("Error", "Please select Blender executable path")
            return False
        if not self.skin_files:
            messagebox.showerror("Error", "Please select skin images")
            return False
        if not self.output_dir:
            messagebox.showerror("Error", "Please select output directory")
            return False
        return True
    
    def start_rendering(self):
        """Start batch rendering"""
        if not self.validate_inputs():
            return
        
        if self.is_rendering:
            messagebox.showinfo("Note", "Rendering is already in progress")
            return
        
        self.is_rendering = True
        self.render_btn.config(state=tk.DISABLED, text="Rendering...")
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Execute rendering in new thread to avoid blocking GUI
        threading.Thread(target=self.render_batch).start()
    
    def render_batch(self):
        """Batch render skins"""
        import datetime
        import time
        
        total_skins = len(self.skin_files)
        render_times = []
        batch_start_time = time.time()
        
        for i, skin_info in enumerate(self.skin_files):
            # Record single skin render start time
            skin_start_time = time.time()
            
            # Calculate progress
            progress = (i + 1) / total_skins * 100
            self.progress_var.set(progress)
            
            # Update status
            skin_name = os.path.basename(skin_info['path'])
            self.status_var.set(f"Rendering: {skin_name} ({i+1}/{total_skins})")
            
            # Record rendering start time
            render_time = datetime.datetime.now()
            time_str = render_time.strftime("%Y-%m-%d-%H%M")
            
            # Generate output filename (ensure no conflict)
            base_name = os.path.splitext(skin_name)[0]
            # Convert ratio format from '1:1' to '11', '4:3' to '43', etc.
            ratio_code = self.selected_aspect_ratio.replace(':', '')
            output_file = os.path.join(self.output_dir, f"{time_str}_{base_name}_{skin_info['model']}_{ratio_code}_render.png")
            
            # Ensure filename doesn't conflict
            counter = 1
            while os.path.exists(output_file):
                output_file = os.path.join(self.output_dir, f"{time_str}_{base_name}_{skin_info['model']}_render_{counter}.png")
                counter += 1
            
            # Execute Blender rendering
            self.render_single_skin(skin_info, output_file)
            
            # Record single skin render end time and duration
            skin_end_time = time.time()
            skin_render_time = skin_end_time - skin_start_time
            render_times.append(skin_render_time)
            
            # Calculate prediction time
            if i > 0:
                avg_time = sum(render_times) / len(render_times)
                remaining_skins = total_skins - (i + 1)
                remaining_time = avg_time * remaining_skins
                
                # Format time
                hours = int(remaining_time // 3600)
                minutes = int((remaining_time % 3600) // 60)
                seconds = int(remaining_time % 60)
                
                if hours > 0:
                    time_str = f"Estimated remaining time: {hours}h{minutes}m{seconds}s"
                elif minutes > 0:
                    time_str = f"Estimated remaining time: {minutes}m{seconds}s"
                else:
                    time_str = f"Estimated remaining time: {seconds}s"
                
                # Update prediction time display
                self.time_var.set(time_str)
        
        # Rendering completed
        total_time = time.time() - batch_start_time
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        seconds = int(total_time % 60)
        
        if hours > 0:
            total_time_str = f"Total time: {hours}h{minutes}m{seconds}s"
        elif minutes > 0:
            total_time_str = f"Total time: {minutes}m{seconds}s"
        else:
            total_time_str = f"Total time: {seconds}s"
        
        self.status_var.set("Rendering Completed!")
        self.time_var.set(total_time_str)
        self.render_btn.config(state=tk.NORMAL, text="Start Batch Render")
        self.is_rendering = False
        messagebox.showinfo("Completed", f"Successfully rendered {total_skins} skins")
    
    def render_single_skin(self, skin_info, output_file):
        """Render a single skin"""
        skin_file = skin_info['path']
        model_type = skin_info['model']
        
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"Current script directory: {script_dir}")
        
        # Select corresponding blender file based on model type
        model_dir = os.path.join(script_dir, "model")
        model_num = self.model_num_var.get()
        if model_num == 'a':
            # For model a (original model 4), use the original skin file
            if model_type == 'standard':
                model_file = os.path.join(model_dir, f"Steve-model{model_num}.blend")  # Use original model 4 file (now model a)
            else:
                model_file = os.path.join(model_dir, f"Alex-model{model_num}.blend")  # Use original model 4 file (now model a)
        else:
            if model_type == 'standard':
                model_file = os.path.join(model_dir, f"Steve-model{model_num}.blend")
            else:
                model_file = os.path.join(model_dir, f"Alex-model{model_num}.blend")
        
        print(f"Using model file: {model_file}")
        
        # Use standalone Blender script
        script_path = os.path.join(script_dir, "blender_render_script.py")
        
        # Get selected ratio
        width, height = self.aspect_ratios[self.selected_aspect_ratio]
        
        # Convert hex color to RGB float values between 0-1
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                # RGB format
                r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
                a = 1.0  # Default opacity
            elif len(hex_color) == 8:
                # RGBA format
                r, g, b, a = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4, 6))
            else:
                # Default transparent
                r, g, b, a = 0.0, 0.0, 0.0, 0.0
            return f"{r},{g},{b},{a}"
        
        # Build Blender command
        cmd = [
            self.blender_path,
            '--background',
            model_file,
            '--python',
            script_path,
            '--',
            skin_file,
            output_file,
            str(width),
            str(height),
            self.device_var.get(),
            hex_to_rgb(self.render_bg_color)
        ]
        
        print(f"Executing command: {' '.join(cmd)}")
        
        # Execute command
        print(f"Blender path: {self.blender_path}")
        print(f"Command exists: {os.path.exists(self.blender_path)}")
        print(f"Model file exists: {os.path.exists(model_file)}")
        print(f"Script file exists: {os.path.exists(script_path)}")
        print(f"Skin file exists: {os.path.exists(skin_file)}")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
            print(f"Blender output:\n{result.stdout}")
            if result.stderr:
                print(f"Blender warnings/errors:\n{result.stderr}")
            print(f"Successfully rendered to: {output_file}")
            
            # Apply background image if enabled
            if self.use_background_image and self.background_image_path and os.path.exists(output_file):
                self.apply_background_image(output_file)
                print(f"Successfully applied background image to: {output_file}")
                
        except subprocess.CalledProcessError as e:
            # Rendering error, but continue with next skin
            print(f"Error rendering {skin_file}: {e}")
            print(f"Command return code: {e.returncode}")
            print(f"Command output: {e.stdout}")
            print(f"Command error: {e.stderr}")
        except subprocess.TimeoutExpired:
            print(f"Rendering {skin_file} timed out")
        except Exception as e:
            print(f"Unknown error rendering {skin_file}: {e}")
    
    def apply_background_image(self, rendered_image_path):
        """Apply background image to rendered transparent image"""
        try:
            from PIL import Image
            
            print(f"Starting background image application process")
            print(f"  Rendered image: {rendered_image_path}")
            print(f"  Background image: {self.background_image_path}")
            
            # Open rendered image with transparent background
            rendered_img = Image.open(rendered_image_path).convert("RGBA")
            print(f"  Rendered image size: {rendered_img.size}")
            
            # Open background image
            bg_img = Image.open(self.background_image_path).convert("RGBA")
            print(f"  Background image original size: {bg_img.size}")
            
            # Calculate scaling factors to maintain aspect ratio
            render_width, render_height = rendered_img.size
            bg_width, bg_height = bg_img.size
            
            # Calculate scaling factor for width and height
            scale_x = render_width / bg_width
            scale_y = render_height / bg_height
            
            # Use the larger scaling factor to ensure the entire background is covered
            scale = max(scale_x, scale_y)
            
            # Calculate new background image dimensions
            new_bg_width = int(bg_width * scale)
            new_bg_height = int(bg_height * scale)
            
            # Resize background image while maintaining aspect ratio
            bg_img = bg_img.resize((new_bg_width, new_bg_height), Image.LANCZOS)
            print(f"  Background image resized to: {bg_img.size} with scale factor {scale:.2f}")
            
            # Create a new image with rendered size
            bg_opaque = Image.new("RGBA", rendered_img.size, (255, 255, 255, 255))
            
            # Calculate position to center the background image (may be cropped)
            x_offset = (render_width - new_bg_width) // 2
            y_offset = (render_height - new_bg_height) // 2
            
            # Paste the resized background image onto the opaque background
            bg_opaque.paste(bg_img, (x_offset, y_offset), bg_img)
            print(f"  Background image centered at ({x_offset}, {y_offset})")
            
            # Composite the rendered image on top of the opaque background
            result_img = Image.alpha_composite(bg_opaque, rendered_img)
            print(f"  Completed image compositing")
            
            # Save the result (overwrite the original rendered image)
            result_img.save(rendered_image_path, "PNG")
            print(f"  Background image applied successfully")
            
        except Exception as e:
            print(f"Error applying background image: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    root = tk.Tk()
    app = SkinRendererApp(root)
    root.mainloop()

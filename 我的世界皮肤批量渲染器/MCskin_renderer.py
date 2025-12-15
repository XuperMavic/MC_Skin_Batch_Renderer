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
        self.root.title("我的世界皮肤批量渲染器")
        self.root.geometry("650x750")
        self.root.resizable(True, True)  # 允许调整窗口大小
        self.root.minsize(450, 450)  # 设置窗口最小尺寸：宽度450像素，高度450像素
        
        # 设置全局主题颜色
        self.bg_color = "#f0f0f0"
        self.card_bg = "#ffffff"
        self.text_color = "#333333"
        self.heading_color = "#2c3e50"
        self.accent_color = "#3498db"
        self.accent_hover = "#2980b9"
        self.success_color = "#27ae60"
        self.warning_color = "#f39c12"
        self.error_color = "#e74c3c"
        self.render_bg_color = "#00000000"  # 渲染背景颜色（RGBA格式，透明）
        
        # 设置窗口背景色
        self.root.configure(bg=self.bg_color)
        
        # 初始化变量
        self.blender_file = ""
        self.skin_files = []  # 格式: [{'path': '皮肤路径', 'model': 'standard'}]
        self.output_dir = ""
        self.blender_path = ""
        self.is_rendering = False
        self.model_options = ['standard', 'slim']  # 可用的模型选项
        self.aspect_ratios = {'1:1': (1024, 1024), '4:3': (1024, 768), '3:4': (768, 1024), '16:9': (1024, 576), '9:16': (576, 1024)}
        self.selected_aspect_ratio = '1:1'
        self.render_devices = ['CPU', 'GPU']  # 可用的渲染设备
        self.selected_device = 'CPU'  # 默认使用CPU
        
        # 可用的模型编号和对应的显示名称
        self.model_nums = ['1', '2', '3', '4', '5', 'a']  # 模型实际值，顺序为[1,2,3,4,5,a]
        self.model_names = {
            '1': '1-正背_右手叉腰',
            '2': '2-正背_奔跑',
            '3': '3-正背_跆拳道起手式',
            '4': '4-正背_左手叉腰',
            '5': '5-正_双手背后扭腰歪头',
            'a': 'a-场景_沙漠小家村民骆驼'
        }
        self.selected_model_num = '1'  # 默认使用模型1
        self.view_mode = 'list'  # 'list' 或 'icon' 视图模式
        
        # 背景图片变量
        self.use_background_image = False
        self.background_image_path = ""
        self.background_image_var = tk.StringVar()
        self.background_image_var.set("未选择背景图片")
        self.background_image_check_var = tk.BooleanVar(value=self.use_background_image)
        
        # 图标视图相关变量
        self.icon_rows = []  # 存储图标视图中所有行的组件
        self.icon_images = []  # 存储PhotoImage对象，防止被GC回收
        self.selected_icon_index = None  # 当前选中的图标索引（单选模式）
        self.selected_icon_indices = set()  # 存储多选的图标索引
        self.icon_frame_window = None  # Canvas窗口对象ID
        
        # 创建主滚动框架
        self.create_scrollable_frame()
        # 创建界面
        self.create_widgets()
        # 创建右键菜单
        self.create_context_menu()
        
    def create_scrollable_frame(self):
        """创建带滚动条的主框架"""
        # 创建主框架
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建滚动条样式
        style = ttk.Style()
        style.configure("Modern.Vertical.TScrollbar", 
                       gripcount=0,
                       background=self.accent_color,
                       troughcolor="#e0e0e0",
                       arrowcolor=self.heading_color)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, style="Modern.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建画布
        self.canvas = tk.Canvas(main_frame, yscrollcommand=scrollbar.set, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置滚动条
        scrollbar.config(command=self.canvas.yview)
        
        # 创建可滚动的内容框架
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_color)
        # 保存窗口项目的ID
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        
        # 绑定内容变化事件
        def on_frame_configure(event):
            # 更新滚动区域
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        
        # 绑定窗口大小变化事件，使内容自适应宽度
        def on_window_resize(event):
            # 获取主框架宽度
            new_width = main_frame.winfo_width() - 20  # 减去滚动条的宽度
            # 更新画布宽度
            self.canvas.itemconfigure(self.canvas_window, width=new_width)
        
        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", on_window_resize)
        
        # 绑定鼠标滚轮事件
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def create_widgets(self):
        # 设置全局样式
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('TLabel', font=('Arial', 10))
        
        # 标题
        title_label = tk.Label(self.scrollable_frame, text="我的世界皮肤批量渲染器", font=("Arial", 18, "bold"), fg="#336699")
        title_label.pack(pady=15)
        
        # 添加分隔线
        ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # Blender路径设置
        path_frame = tk.Frame(self.scrollable_frame, 
                              relief=tk.FLAT, 
                              borderwidth=0,
                              bg=self.bg_color)
        path_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # 创建卡片式容器
        path_card = tk.Frame(path_frame, 
                            bg=self.card_bg,
                            relief=tk.FLAT,
                            borderwidth=1,
                            padx=20,
                            pady=15)
        path_card.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加圆角效果（通过Canvas实现）
        self.add_rounded_corners(path_card, 10)
        
        tk.Label(path_card, 
                 text="Blender路径", 
                 font= ("Arial", 12, "bold"),
                 fg=self.heading_color,
                 bg=self.card_bg).pack(anchor=tk.W)
        
        # 添加提示文字
        tk.Label(path_card, 
                 text="提示：选择blender.exe文件", 
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
                                    text="浏览", 
                                    command=self.browse_blender_path,
                                    style='TButton')
        browse_path_btn.pack(side=tk.RIGHT)
        
        # 添加分隔线
        ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # 皮肤文件选择
        skin_frame = tk.Frame(self.scrollable_frame, 
                              bg=self.bg_color)
        skin_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # 创建卡片式容器
        skin_card = tk.Frame(skin_frame, 
                            bg=self.card_bg,
                            relief=tk.FLAT,
                            borderwidth=1,
                            padx=20,
                            pady=15)
        skin_card.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加圆角效果
        self.add_rounded_corners(skin_card, 10)
        
        # 设置grid布局
        skin_card.grid_rowconfigure(0, weight=0)
        skin_card.grid_rowconfigure(1, weight=0)
        skin_card.grid_rowconfigure(2, weight=0)
        skin_card.grid_rowconfigure(3, weight=0)
        skin_card.grid_rowconfigure(4, weight=1)  # 列表区域可扩展
        skin_card.grid_rowconfigure(5, weight=0)
        skin_card.grid_rowconfigure(6, weight=0)
        skin_card.grid_columnconfigure(0, weight=1)
        
        # 皮肤头部
        skin_header = tk.Frame(skin_card, bg=self.card_bg)
        skin_header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        tk.Label(skin_header, 
                text="皮肤管理", 
                font=("Arial", 12, "bold"), 
                fg=self.heading_color,
                bg=self.card_bg).pack(anchor=tk.W)
        
        # 皮肤操作按钮
        skin_buttons = tk.Frame(skin_card, bg=self.card_bg)
        skin_buttons.grid(row=1, column=0, sticky='ew', pady=5)
        
        browse_skins_btn = ttk.Button(skin_buttons, 
                                     text="批量选择皮肤", 
                                     command=self.browse_skin_files,
                                     style='TButton')
        browse_skins_btn.pack(side=tk.LEFT, padx=5)
        
        clear_skins_btn = ttk.Button(skin_buttons, 
                                    text="清除所有", 
                                    command=self.clear_skin_files,
                                    style='TButton')
        clear_skins_btn.pack(side=tk.LEFT, padx=5)
        
        delete_skin_btn = ttk.Button(skin_buttons, 
                                    text="删除选中", 
                                    command=self.delete_selected_skins,
                                    style='TButton')
        delete_skin_btn.pack(side=tk.LEFT, padx=5)
        
        # 提示信息
        self.tip_label = tk.Label(skin_card, 
                text="提示：右键可以选择体型【标准】/【slim】", 
                font=('Arial', 9, 'italic'), 
                fg="#7f8c8d",
                bg=self.card_bg)
        self.tip_label.grid(row=2, column=0, sticky='w', pady=(5, 10))
        
        # 视图切换按钮
        view_frame = tk.Frame(skin_card, bg=self.card_bg)
        view_frame.grid(row=3, column=0, sticky='e', pady=(0, 5))
        
        self.list_view_btn = ttk.Button(view_frame, 
                                       text="列表视图", 
                                       command=lambda: self.switch_view('list'),
                                       style='TButton')
        self.list_view_btn.pack(side=tk.LEFT, padx=5)
        
        self.icon_view_btn = ttk.Button(view_frame, 
                                       text="图标视图", 
                                       command=lambda: self.switch_view('icon'),
                                       style='TButton')
        self.icon_view_btn.pack(side=tk.LEFT, padx=5)
        
        # 皮肤文件列表和模型选择
        list_frame = tk.Frame(skin_card, bg=self.card_bg)
        list_frame.grid(row=4, column=0, sticky='nsew', pady=(0, 2))
        self.list_frame = list_frame
        
        # 添加可拖动分隔线（移到文件表格下方）
        self.divider = tk.Frame(skin_card, height=5, bg='#cccccc', cursor='sb_v_double_arrow')
        self.divider.grid(row=5, column=0, sticky='ew', pady=2)
        
        # 绑定分隔线的鼠标事件
        self.divider.bind('<Button-1>', self.start_resize)
        self.divider.bind('<B1-Motion>', self.on_resize)
        self.divider.bind('<ButtonRelease-1>', self.stop_resize)
        
        # 记录初始状态
        self.is_resizing = False
        self.initial_y = 0
        self.min_list_height = 100
        self.max_list_height = 500
        
        # 为skin_card添加大小变化事件监听
        skin_card.bind('<Configure>', self.on_skin_card_resize)
        
        # 创建Treeview来显示皮肤和模型选择（列表视图）
        columns = ('#1', '#2', '#3')
        
        # 设置Treeview样式
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
        
        self.skin_tree.heading('#1', text='序号')
        self.skin_tree.heading('#2', text='皮肤文件名')
        self.skin_tree.heading('#3', text='体型')
        
        # 设置列宽
        self.skin_tree.column('#1', width=50, anchor='center', stretch=False)
        self.skin_tree.column('#2', width=300, anchor='w', stretch=True)
        self.skin_tree.column('#3', width=150, anchor='center', stretch=False)
        
        # 只添加垂直滚动条，移除不必要的水平滚动条
        self.list_scrollbar = ttk.Scrollbar(list_frame, 
                                           orient=tk.VERTICAL, 
                                           command=self.skin_tree.yview,
                                           style="Modern.Vertical.TScrollbar")
        self.skin_tree.configure(yscrollcommand=self.list_scrollbar.set)
        
        # 布局 - 确保Treeview占满空间
        self.skin_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 图标视图使用Canvas实现滚动
        self.icon_canvas = tk.Canvas(list_frame, bg=self.card_bg, highlightthickness=0)
        self.icon_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.icon_canvas.pack_forget()  # 初始隐藏图标视图
        
        # 图标视图容器（放置在Canvas内部）
        self.icon_frame = tk.Frame(self.icon_canvas, bg=self.card_bg)
        # 保存窗口ID
        self.icon_frame_window = self.icon_canvas.create_window((0, 0), window=self.icon_frame, anchor="nw")
        
        # 图标视图的滚动条
        self.icon_scrollbar = ttk.Scrollbar(list_frame, 
                                           orient=tk.VERTICAL, 
                                           command=self.icon_canvas.yview,
                                           style="Modern.Vertical.TScrollbar")
        self.icon_canvas.configure(yscrollcommand=self.icon_scrollbar.set)
        self.icon_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.icon_scrollbar.pack_forget()  # 初始隐藏图标视图滚动条
        
        # 绑定Canvas的滚动事件
        self.icon_frame.bind("<Configure>", lambda e: self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all")))
        self.icon_canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # 监听Canvas大小变化，调整icon_frame宽度
        self.icon_canvas.bind("<Configure>", self.on_canvas_resize)
        
        # 绑定左键点击事件
        self.skin_tree.bind("<Button-1>", self.on_treeview_click)
        
        # 绑定右键菜单事件
        self.skin_tree.bind("<Button-3>", self.show_context_menu)
        
        # 创建右键菜单
        self.create_context_menu()
        
        # 添加分隔线
        ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # 输出目录
        output_frame = tk.Frame(self.scrollable_frame, 
                               bg=self.bg_color)
        output_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # 创建卡片式容器
        output_card = tk.Frame(output_frame, 
                              bg=self.card_bg,
                              relief=tk.FLAT,
                              borderwidth=1,
                              padx=20,
                              pady=15)
        output_card.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加圆角效果
        self.add_rounded_corners(output_card, 10)
        
        tk.Label(output_card, 
                text="输出目录:", 
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
                                      text="浏览", 
                                      command=self.browse_output_dir,
                                      style='TButton')
        browse_output_btn.pack(side=tk.RIGHT)
        
        # 添加分隔线
        ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # 渲染控制区域
        render_frame = tk.Frame(self.scrollable_frame, 
                               bg=self.bg_color)
        render_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # 创建卡片式容器
        render_card = tk.Frame(render_frame, 
                              bg=self.card_bg,
                              relief=tk.FLAT,
                              borderwidth=1,
                              padx=20,
                              pady=15)
        render_card.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加圆角效果
        self.add_rounded_corners(render_card, 10)
        
        tk.Label(render_card, 
                text="渲染控制", 
                font=("Arial", 12, "bold"), 
                fg=self.heading_color,
                bg=self.card_bg).pack(anchor=tk.W, pady=(0, 15))
        
        # 图片比例选择
        ratio_row = tk.Frame(render_card, bg=self.card_bg)
        ratio_row.pack(fill=tk.X, pady=10)
        
        tk.Label(ratio_row, 
                text="输出图片比例:", 
                font=("Arial", 10), 
                fg=self.text_color,
                bg=self.card_bg).pack(side=tk.LEFT, padx=5)
        
        self.ratio_var = tk.StringVar(value=self.selected_aspect_ratio)
        ratio_menu = ttk.Combobox(ratio_row, 
                                 textvariable=self.ratio_var,
                                 values=list(self.aspect_ratios.keys()),
                                 state="readonly",
                                 font=("Arial", 10))
        ratio_menu.pack(side=tk.LEFT, padx=5)
        ratio_menu.bind("<<ComboboxSelected>>", self.on_ratio_selected)
        
        # 渲染设备选择
        device_row = tk.Frame(render_card, bg=self.card_bg)
        device_row.pack(fill=tk.X, pady=10)
        
        tk.Label(device_row, 
                text="渲染设备:", 
                font=("Arial", 10), 
                fg=self.text_color,
                bg=self.card_bg).pack(side=tk.LEFT, padx=5)
        
        self.device_var = tk.StringVar(value=self.selected_device)
        device_menu = ttk.Combobox(device_row, 
                                 textvariable=self.device_var,
                                 values=self.render_devices,
                                 state="readonly",
                                 font=('Arial', 10))
        device_menu.pack(side=tk.LEFT, padx=5)
        
        # 模型编号选择
        model_num_row = tk.Frame(render_card, bg=self.card_bg)
        model_num_row.pack(fill=tk.X, pady=10)
        
        tk.Label(model_num_row, 
                text="模型类型:", 
                font=('Arial', 10), 
                fg=self.text_color,
                bg=self.card_bg).pack(side=tk.LEFT, padx=5)
        
        # 创建模型类型下拉菜单
        self.model_num_var = tk.StringVar(value=self.selected_model_num)
        
        # 显示名称列表
        model_display_names = [self.model_names[num] for num in self.model_nums]
        
        # 创建Combobox
        model_num_menu = ttk.Combobox(model_num_row, 
                                    values=model_display_names,
                                    state="readonly",
                                    font=('Arial', 10))
        
        # 设置默认选中项（根据selected_model_num）
        default_index = self.model_nums.index(self.selected_model_num)
        model_num_menu.current(default_index)
        
        # 确保model_num_var初始化为正确的数字值
        self.model_num_var.set(self.selected_model_num)
        
        # 绑定选择事件，将显示名称转换为实际值
        def on_model_select(event):
            selected_name = model_num_menu.get()
            # 找到对应的实际值
            for num, name in self.model_names.items():
                if name == selected_name:
                    self.model_num_var.set(num)
                    self.selected_model_num = num
                    break
        
        model_num_menu.bind("<<ComboboxSelected>>", on_model_select)
        model_num_menu.pack(side=tk.LEFT, padx=5)
        
        # 渲染背景颜色设置
        color_row = tk.Frame(render_card, bg=self.card_bg)
        color_row.pack(fill=tk.X, pady=10)
        
        tk.Label(color_row, 
                text="渲染背景颜色:", 
                font=("Arial", 10), 
                fg=self.text_color,
                bg=self.card_bg).pack(side=tk.LEFT, padx=5)
        
        # 当前背景颜色显示
        self.color_display = tk.Label(color_row, 
                                     width=10, 
                                     bg="#FFFFFF" if self.render_bg_color == "#00000000" else self.render_bg_color, 
                                     relief=tk.RAISED,
                                     borderwidth=1)
        self.color_display.pack(side=tk.LEFT, padx=5)
        
        # 颜色选择按钮
        color_btn = ttk.Button(color_row, 
                              text="选择颜色", 
                              command=self.choose_bg_color)
        color_btn.pack(side=tk.LEFT, padx=5)
        
        # 无背景颜色按钮
        no_bg_btn = ttk.Button(color_row, 
                              text="无背景颜色", 
                              command=self.set_no_bg_color)
        no_bg_btn.pack(side=tk.LEFT, padx=5)
        
        # 背景图片设置
        bg_image_row = tk.Frame(render_card, bg=self.card_bg)
        bg_image_row.pack(fill=tk.X, pady=10)
        
        # 使用背景图片复选框
        self.bg_image_check = tk.Checkbutton(bg_image_row, 
                                           text="使用背景图片:", 
                                           variable=self.background_image_check_var,
                                           command=self.toggle_background_image,
                                           font= ("Arial", 10), 
                                           fg=self.text_color,
                                           bg=self.card_bg)
        self.bg_image_check.pack(side=tk.LEFT, padx=5)
        
        # 背景图片路径显示
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
        
        # 浏览背景图片按钮
        browse_bg_btn = ttk.Button(bg_image_row, 
                                 text="浏览", 
                                 command=self.browse_background_image)
        browse_bg_btn.pack(side=tk.LEFT, padx=5)
        
        # 渲染按钮
        btn_row = tk.Frame(render_card, bg=self.card_bg)
        btn_row.pack(fill=tk.X, pady=10)
        
        self.render_btn = ttk.Button(btn_row, 
                                   text="开始批量渲染", 
                                   command=self.start_rendering, 
                                   style='Accent.TButton')
        self.render_btn.pack(fill=tk.X, ipady=2)
        
        # 进度条
        progress_row = tk.Frame(render_card, bg=self.card_bg)
        progress_row.pack(fill=tk.X, pady=10)
        
        # 设置进度条样式
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
        
        # 状态标签
        status_row = tk.Frame(render_card, bg=self.card_bg)
        status_row.pack(fill=tk.X, pady=10)
        
        self.status_var = tk.StringVar()
        # 初始状态为空，不显示"就绪"二字
        self.status_var.set("")
        self.status_label = tk.Label(status_row, 
                                    textvariable=self.status_var, 
                                    font=("Arial", 10, "bold"), 
                                    fg=self.success_color,
                                    bg=self.card_bg)
        self.status_label.pack(anchor=tk.W)
        
        # 渲染时间预测标签
        time_row = tk.Frame(render_card, bg=self.card_bg)
        time_row.pack(fill=tk.X, pady=10)
        
        self.time_var = tk.StringVar()
        self.time_var.set("")
        self.time_label = tk.Label(time_row, 
                                  textvariable=self.time_var, 
                                  font=("Arial", 10), 
                                  fg=self.text_color,
                                  bg=self.card_bg)
        self.time_label.pack(anchor=tk.W)
        
        # 底部填充
        tk.Frame(self.scrollable_frame, height=20, bg=self.bg_color).pack()
        
    def add_rounded_corners(self, widget, radius):
        """为控件添加圆角效果"""
        # 获取控件位置
        x, y, width, height = widget.bbox("all")
        
        # 创建一个canvas作为背景
        canvas = tk.Canvas(widget, width=width, height=height, bg=self.bg_color, highlightthickness=0)
        canvas.place(x=0, y=0)
        
        # 绘制圆角矩形
        r = radius
        points = [r, 0, width-r, 0,
                 width, 0, width, r,
                 width, height-r, width, height,
                 width-r, height, r, height,
                 0, height, 0, height-r,
                 0, r, 0, 0]
        canvas.create_polygon(points, fill=self.card_bg, outline="")
        
        # 将控件提升到canvas上方
        widget.lift()
    
    def browse_blender_path(self):
        """浏览选择Blender可执行文件路径"""
        file_path = filedialog.askopenfilename(
            title="选择Blender可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if file_path:
            self.blender_path = file_path
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, file_path)
    
    def select_model(self, model_type):
        """选择预设的模型类型"""
        # 这个方法现在主要用于兼容性，实际模型选择已移至每个皮肤
        messagebox.showinfo("提示", "已改用右键菜单为每个皮肤单独选择模型类型")
    
    def browse_blender_file(self):
        """浏览选择自定义Blender文件"""
        # 这个方法现在主要用于兼容性，实际模型选择已移至每个皮肤
        messagebox.showinfo("提示", "已改用右键菜单为每个皮肤单独选择模型类型")
    
    def browse_skin_files(self):
        """批量选择皮肤图片"""
        files = filedialog.askopenfilenames(
            title="选择皮肤图片",
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg"), ("所有文件", "*.*")]
        )
        if files:
            # 添加新选择的皮肤，默认使用standard模型
            for file in files:
                self.skin_files.append({'path': file, 'model': 'standard'})
            self.update_skin_list()
    
    def clear_skin_files(self):
        """清除已选择的皮肤图片"""
        self.skin_files = []
        self.update_skin_list()
    
    def delete_selected_skins(self):
        """删除选中的皮肤，支持多选"""
        if self.view_mode == 'list':
            selected_items = self.skin_tree.selection()
            if not selected_items:
                messagebox.showinfo("提示", "请先选择要删除的皮肤")
                return
            
            # 按索引从大到小删除，避免索引混乱
            indices_to_delete = sorted([int(item.split('_')[-1]) for item in selected_items], reverse=True)
        else:
            # 图标视图，检查是否有选中的图标
            if not hasattr(self, 'selected_icon_indices') or not self.selected_icon_indices:
                messagebox.showinfo("提示", "请先选择要删除的皮肤")
                return
            
            # 按索引从大到小删除，避免索引混乱
            indices_to_delete = sorted(self.selected_icon_indices, reverse=True)
        
        for idx in indices_to_delete:
            if 0 <= idx < len(self.skin_files):
                del self.skin_files[idx]
        
        # 重置选中状态
        if hasattr(self, 'selected_icon_index'):
            self.selected_icon_index = None
        if hasattr(self, 'selected_icon_indices'):
            self.selected_icon_indices.clear()
        
        self.update_skin_list()
        messagebox.showinfo("完成", f"已删除 {len(indices_to_delete)} 个选中的皮肤")
    
    def on_ratio_selected(self, event):
        """处理用户选择的图片比例"""
        self.selected_aspect_ratio = self.ratio_var.get()
        print(f"Selected ratio: {self.selected_aspect_ratio}")
    
    def choose_bg_color(self):
        """选择渲染背景颜色"""
        # 打开颜色选择器
        color_code = colorchooser.askcolor(title="选择渲染背景颜色")
        if color_code and color_code[1]:
            # 更新渲染背景颜色
            self.render_bg_color = color_code[1]
            # 更新颜色显示
            self.color_display.configure(bg=self.render_bg_color)
            # 清除透明文本
            self.color_display.config(text="")
    
    def set_no_bg_color(self):
        """设置无背景颜色（透明）"""
        self.render_bg_color = "#00000000"  # 完全透明
        # 更新颜色显示为白色（表示透明）
        self.color_display.configure(bg="#ffffff")
        # 显示透明提示
        self.color_display.config(text="透明")
    
    def toggle_background_image(self):
        """切换背景图片使用状态"""
        self.use_background_image = self.background_image_check_var.get()
        
        # 如果使用背景图片，自动设置渲染背景为透明
        if self.use_background_image:
            self.set_no_bg_color()
    
    def browse_background_image(self):
        """浏览并选择背景图片"""
        file_path = filedialog.askopenfilename(
            title="选择背景图片",
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.bmp"), ("所有文件", "*.*")]
        )
        if file_path:
            self.background_image_path = file_path
            self.background_image_var.set(os.path.basename(file_path))
            # 如果选择了图片，自动启用背景图片复选框
            self.background_image_check_var.set(True)
            self.use_background_image = True
            # 选择背景图片时，将渲染背景设置为透明
            self.set_no_bg_color()
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="使用标准体型 (Steve)", command=lambda: self.change_model('standard'))
        self.context_menu.add_command(label="使用Slim体型 (Alex)", command=lambda: self.change_model('slim'))
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 获取点击的项
        item = self.skin_tree.identify_row(event.y)
        if item:
            # 选择当前项
            self.skin_tree.selection_set(item)
            # 显示右键菜单
            self.context_menu.post(event.x_root, event.y_root)
    
    def on_treeview_click(self, event):
        """处理Treeview的左键点击事件，支持多选切换"""
        # 获取点击的区域和项
        region = self.skin_tree.identify_region(event.x, event.y)
        item = self.skin_tree.identify_row(event.y)
        
        # 点击时切换选择状态
        if region == "cell" and item:
            if item in self.skin_tree.selection():
                # 如果已经选中，则取消选中
                self.skin_tree.selection_remove(item)
            else:
                # 如果未选中，则选中
                self.skin_tree.selection_add(item)
    
    def change_model(self, model_type):
        """更改选中皮肤的体型，支持多选"""
        if self.view_mode == 'list':
            selected_items = self.skin_tree.selection()
            if not selected_items:
                messagebox.showinfo("提示", "请先选择要修改的皮肤")
                return
            
            for item in selected_items:
                # 获取皮肤索引
                skin_index = int(item.split('_')[-1])
                if 0 <= skin_index < len(self.skin_files):
                    # 更新体型
                    self.skin_files[skin_index]['model'] = model_type
        else:
            # 图标视图，检查是否有选中的图标
            if not hasattr(self, 'selected_icon_indices') or not self.selected_icon_indices:
                messagebox.showinfo("提示", "请先选择要修改的皮肤")
                return
            
            for idx in self.selected_icon_indices:
                if 0 <= idx < len(self.skin_files):
                    # 更新体型
                    self.skin_files[idx]['model'] = model_type
        
        self.update_skin_list()
        messagebox.showinfo("完成", f"已将选中皮肤的体型更改为 {model_type}")
    
    def switch_view(self, view_mode):
        """切换列表视图和图标视图"""
        self.view_mode = view_mode
        
        if view_mode == 'list':
            # 显示列表视图，隐藏图标视图
            self.skin_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.skin_tree.bind("<Button-1>", self.on_treeview_click)
            self.skin_tree.bind("<Button-3>", self.show_context_menu)
            self.icon_canvas.pack_forget()
            self.icon_scrollbar.pack_forget()
        else:
            # 显示图标视图，隐藏列表视图
            self.skin_tree.pack_forget()
            self.list_scrollbar.pack_forget()
            self.skin_tree.unbind("<Button-1>")
            self.skin_tree.unbind("<Button-3>")
            self.icon_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.icon_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 更新显示
        self.update_skin_list()
    
    def on_skin_card_resize(self, event):
        """当skin_card大小变化时，更新布局"""
        # 如果正在调整大小，则不执行自动调整
        if self.is_resizing:
            return
        
        # 确保列表区域有最小高度
        if self.list_frame.winfo_height() < self.min_list_height:
            self.list_frame.master.grid_rowconfigure(4, minsize=self.min_list_height)
    
    def start_resize(self, event):
        """开始调整大小"""
        self.is_resizing = True
        self.initial_y = event.y_root
        self.initial_list_height = self.list_frame.winfo_height()
        self.list_frame.master.grid_rowconfigure(4, minsize=0)  # 临时移除最小高度限制
    
    def on_resize(self, event):
        """调整大小过程中"""
        if not self.is_resizing:
            return
        
        # 计算高度变化
        delta_y = event.y_root - self.initial_y
        
        # 计算新的高度，确保在最小和最大高度之间
        new_height = max(self.min_list_height, min(self.initial_list_height + delta_y, self.max_list_height))
        
        # 调整列表区域的高度
        self.list_frame.master.grid_rowconfigure(4, minsize=new_height, weight=1)
        
        # 强制更新布局
        self.list_frame.master.update_idletasks()
    
    def stop_resize(self, event):
        """停止调整大小"""
        self.is_resizing = False
        # 保留最终高度作为新的最小高度
        final_height = max(self.min_list_height, self.list_frame.winfo_height())
        self.list_frame.master.grid_rowconfigure(4, minsize=final_height, weight=1)
    
    def on_canvas_resize(self, event):
        """当Canvas大小变化时，调整icon_frame的宽度"""
        # 获取Canvas的宽度
        canvas_width = event.width
        # 减去滚动条的宽度（如果显示的话）
        if self.icon_scrollbar.winfo_ismapped():
            canvas_width -= self.icon_scrollbar.winfo_width()
        
        # 更新Canvas中的窗口宽度
        self.icon_canvas.itemconfigure(self.icon_frame_window, width=canvas_width)
        # 更新icon_frame的宽度
        self.icon_frame.configure(width=canvas_width)
        
        # 更新滚动区域
        self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all"))
        
        # 强制更新布局
        self.icon_frame.update_idletasks()
    
    def update_skin_list(self):
        """更新皮肤文件列表显示"""
        if self.view_mode == 'list':
            # 清空Treeview
            for item in self.skin_tree.get_children():
                self.skin_tree.delete(item)
            
            # 添加皮肤信息
            for i, skin in enumerate(self.skin_files):
                filename = os.path.basename(skin['path'])
                model_name = skin['model']
                self.skin_tree.insert('', tk.END, iid=f'skin_{i}', values=(i+1, filename, model_name))
        else:
            # 清空图标视图
            for widget in self.icon_frame.winfo_children():
                widget.destroy()
            
            # 设置图标视图的表格布局
            self.icon_frame.grid_columnconfigure(0, weight=0, minsize=50)  # 序号列 - 固定宽度
            self.icon_frame.grid_columnconfigure(1, weight=0, minsize=80)  # 图片列 - 固定宽度
            self.icon_frame.grid_columnconfigure(2, weight=1, minsize=200)  # 文件名 - 自适应宽度（减小了最小宽度）
            self.icon_frame.grid_columnconfigure(3, weight=0, minsize=100)  # 体型 - 固定宽度（减小了最小宽度）
            
            # 添加表头
            header_bg = "white"
            header_font = ('Arial', 10, 'bold')
            
            # 序号表头
            tk.Label(self.icon_frame, text="序号", bg=header_bg, font=header_font, relief=tk.RIDGE, padx=5).grid(
                row=0, column=0, sticky='nsew')
            # 图片表头
            tk.Label(self.icon_frame, text="图片", bg=header_bg, font=header_font, relief=tk.RIDGE, padx=5).grid(
                row=0, column=1, sticky='nsew')
            # 文件名列头
            tk.Label(self.icon_frame, text="皮肤文件名", bg=header_bg, font=header_font, relief=tk.RIDGE, padx=5).grid(
                row=0, column=2, sticky='nsew')
            # 体型表头
            tk.Label(self.icon_frame, text="体型", bg=header_bg, font=header_font, relief=tk.RIDGE, padx=5).grid(
                row=0, column=3, sticky='nsew')
            
            # 添加皮肤数据行
            self.icon_images = []  # 存储PhotoImage对象，防止被GC回收
            self.icon_rows = []  # 存储行相关的所有组件
            
            for i, skin in enumerate(self.skin_files):
                filename = os.path.basename(skin['path'])
                model_name = skin['model']
                skin_path = skin['path']
                
                # 行背景色交替
                row_bg = "white" if i % 2 == 0 else "#f0f0f0"
                
                # 存储当前行的所有组件
                row_widgets = []
                
                # 序号列
                number_label = tk.Label(self.icon_frame, text=str(i+1), bg=row_bg, font=('Arial', 10), relief=tk.RIDGE, padx=5, anchor='center')
                number_label.grid(row=i+1, column=0, sticky='nsew')
                row_widgets.append(number_label)
                
                # 图片列
                try:
                    # 加载皮肤图片
                    image = Image.open(skin_path)
                    # 调整图片大小为合适的缩略图尺寸
                    image.thumbnail((60, 60), Image.LANCZOS)
                    # 创建PhotoImage对象
                    photo = ImageTk.PhotoImage(image)
                    
                    # 存储PhotoImage对象，防止被GC回收
                    self.icon_images.append(photo)
                    
                    # 添加图片预览
                    image_label = tk.Label(self.icon_frame, image=photo, bg=row_bg, relief=tk.RIDGE, padx=5)
                    image_label.grid(row=i+1, column=1, sticky='nsew', padx=1, pady=1)
                    row_widgets.append(image_label)
                    
                except Exception as e:
                    # 如果无法加载图片，显示占位符
                    placeholder_label = tk.Label(self.icon_frame, text="无法加载", bg=row_bg, font=('Arial', 10), relief=tk.RIDGE, padx=5, anchor='center')
                    placeholder_label.grid(row=i+1, column=1, sticky='nsew', padx=1, pady=1)
                    row_widgets.append(placeholder_label)
                
                # 文件名列
                name_label = tk.Label(self.icon_frame, text=filename, bg=row_bg, font=('Arial', 10), relief=tk.RIDGE, padx=5, anchor='w')
                name_label.grid(row=i+1, column=2, sticky='nsew', padx=1, pady=1)
                row_widgets.append(name_label)
                
                # 体型列
                model_label = tk.Label(self.icon_frame, text=model_name, bg=row_bg, font=('Arial', 10), 
                                      relief=tk.RIDGE, padx=5, anchor='center')
                model_label.grid(row=i+1, column=3, sticky='nsew', padx=1, pady=1)
                row_widgets.append(model_label)
                
                # 为当前行的所有组件绑定点击事件
                for widget in row_widgets:
                    widget.bind("<Button-1>", lambda event, idx=i: self.select_icon(idx))
                    widget.bind("<Button-3>", lambda event, idx=i: self.show_context_menu(event, idx))
                
                # 存储当前行的所有组件
                self.icon_rows.append(row_widgets)
            
            # 更新滚动区域
            self.icon_frame.update_idletasks()
            self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all"))
    
    def select_icon(self, idx):
        """选择图标视图中的皮肤，支持多选切换"""
        # 切换选中状态
        if idx in self.selected_icon_indices:
            # 如果已经选中，则取消选中
            self.selected_icon_indices.remove(idx)
        else:
            # 如果未选中，则选中
            self.selected_icon_indices.add(idx)
        
        # 更新所有行的选中状态
        for row_idx, row_widgets in enumerate(self.icon_rows):
            # 恢复行背景色
            row_bg = "white" if row_idx % 2 == 0 else "#f0f0f0"
            for widget in row_widgets:
                if row_idx in self.selected_icon_indices:
                    # 高亮选中的行
                    widget.configure(bg="#a0c4ff", borderwidth=2, relief=tk.SUNKEN, highlightthickness=2)
                else:
                    # 恢复未选中状态
                    widget.configure(bg=row_bg, borderwidth=1, relief=tk.RIDGE)
        
        # 触发删除按钮状态更新
        if hasattr(self, 'delete_button'):
            if self.selected_icon_indices:
                self.delete_button.config(state=tk.NORMAL)
            else:
                self.delete_button.config(state=tk.DISABLED)
    
    def show_context_menu(self, event, idx=None):
        """显示右键菜单"""
        # 如果是图标视图，获取点击的图标索引
        if idx is not None:
            self.selected_icon_index = idx
        else:
            # 列表视图，获取点击的项
            item = self.skin_tree.identify_row(event.y)
            if item:
                self.skin_tree.selection_set(item)
        
        # 显示菜单
        self.context_menu.post(event.x_root, event.y_root)
    
    def browse_output_dir(self):
        """浏览选择输出目录"""
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_dir = dir_path
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, dir_path)
    
    def validate_inputs(self):
        """验证输入是否完整"""
        if not self.blender_path:
            messagebox.showerror("错误", "请选择Blender可执行文件路径")
            return False
        if not self.skin_files:
            messagebox.showerror("错误", "请选择皮肤图片")
            return False
        if not self.output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            return False
        return True
    
    def start_rendering(self):
        """开始批量渲染"""
        if not self.validate_inputs():
            return
        
        if self.is_rendering:
            messagebox.showinfo("提示", "渲染正在进行中")
            return
        
        self.is_rendering = True
        self.render_btn.config(state=tk.DISABLED, text="渲染中...")
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 在新线程中执行渲染，避免阻塞GUI
        threading.Thread(target=self.render_batch).start()
    
    def render_batch(self):
        """批量渲染皮肤"""
        import datetime
        import time
        
        total_skins = len(self.skin_files)
        render_times = []
        batch_start_time = time.time()
        
        for i, skin_info in enumerate(self.skin_files):
            # 记录单个皮肤渲染开始时间
            skin_start_time = time.time()
            
            # 计算进度
            progress = (i + 1) / total_skins * 100
            self.progress_var.set(progress)
            
            # 更新状态
            skin_name = os.path.basename(skin_info['path'])
            self.status_var.set(f"正在渲染: {skin_name} ({i+1}/{total_skins})")
            
            # 记录渲染开始时间
            render_time = datetime.datetime.now()
            time_str = render_time.strftime("%Y-%m-%d-%H%M")
            
            # 生成输出文件名（确保不冲突）
            base_name = os.path.splitext(skin_name)[0]
            # 将比例格式从'1:1'转换为'11'，'4:3'转换为'43'等
            ratio_code = self.selected_aspect_ratio.replace(':', '')
            output_file = os.path.join(self.output_dir, f"{time_str}_{base_name}_{skin_info['model']}_{ratio_code}_render.png")
            
            # 确保文件名不冲突
            counter = 1
            while os.path.exists(output_file):
                output_file = os.path.join(self.output_dir, f"{time_str}_{base_name}_{skin_info['model']}_render_{counter}.png")
                counter += 1
            
            # 执行Blender渲染
            self.render_single_skin(skin_info, output_file)
            
            # 记录单个皮肤渲染结束时间和耗时
            skin_end_time = time.time()
            skin_render_time = skin_end_time - skin_start_time
            render_times.append(skin_render_time)
            
            # 计算预测时间
            if i > 0:
                avg_time = sum(render_times) / len(render_times)
                remaining_skins = total_skins - (i + 1)
                remaining_time = avg_time * remaining_skins
                
                # 格式化时间
                hours = int(remaining_time // 3600)
                minutes = int((remaining_time % 3600) // 60)
                seconds = int(remaining_time % 60)
                
                if hours > 0:
                    time_str = f"预计剩余时间: {hours}小时{minutes}分钟{seconds}秒"
                elif minutes > 0:
                    time_str = f"预计剩余时间: {minutes}分钟{seconds}秒"
                else:
                    time_str = f"预计剩余时间: {seconds}秒"
                
                # 更新预测时间显示
                self.time_var.set(time_str)
            
        # 渲染完成
        total_time = time.time() - batch_start_time
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        seconds = int(total_time % 60)
        
        if hours > 0:
            total_time_str = f"总耗时: {hours}小时{minutes}分钟{seconds}秒"
        elif minutes > 0:
            total_time_str = f"总耗时: {minutes}分钟{seconds}秒"
        else:
            total_time_str = f"总耗时: {seconds}秒"
        
        self.status_var.set("渲染完成！")
        self.time_var.set(total_time_str)
        self.render_btn.config(state=tk.NORMAL, text="开始批量渲染")
        self.is_rendering = False
        messagebox.showinfo("完成", f"已成功渲染 {total_skins} 个皮肤")
    
    def render_single_skin(self, skin_info, output_file):
        """渲染单个皮肤"""
        skin_file = skin_info['path']
        model_type = skin_info['model']
        
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"当前脚本目录: {script_dir}")
        
        # 根据模型类型选择对应的blender文件
        model_dir = os.path.join(script_dir, "model")
        model_num = self.model_num_var.get()
        if model_num == 'a':
            # For model a (original model 4), use the original skin file as requested
            if model_type == 'standard':
                model_file = os.path.join(model_dir, f"Steve-model{model_num}.blend")  # Use original model 4 file (now model a)
            else:
                model_file = os.path.join(model_dir, f"Alex-model{model_num}.blend")  # Use original model 4 file (now model a)
        else:
            if model_type == 'standard':
                model_file = os.path.join(model_dir, f"Steve-model{model_num}.blend")
            else:
                model_file = os.path.join(model_dir, f"Alex-model{model_num}.blend")
        
        print(f"使用模型文件: {model_file}")
        
        # 使用独立的Blender脚本
        script_path = os.path.join(script_dir, "blender_render_script.py")
        
        # 获取选中的比例
        width, height = self.aspect_ratios[self.selected_aspect_ratio]
        
        # 将十六进制颜色转换为0-1之间的浮点数RGB
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                # RGB格式
                r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
                a = 1.0  # 默认不透明
            elif len(hex_color) == 8:
                # RGBA格式
                r, g, b, a = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4, 6))
            else:
                # 默认黑色透明
                r, g, b, a = 0.0, 0.0, 0.0, 0.0
            return f"{r},{g},{b},{a}"
        
        # 构建Blender命令
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
        
        print(f"执行命令: {' '.join(cmd)}")
        
        # 执行命令
        print(f"Blender路径: {self.blender_path}")
        print(f"命令是否存在: {os.path.exists(self.blender_path)}")
        print(f"模型文件是否存在: {os.path.exists(model_file)}")
        print(f"脚本文件是否存在: {os.path.exists(script_path)}")
        print(f"皮肤文件是否存在: {os.path.exists(skin_file)}")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', timeout=60)
            print(f"Blender输出:\n{result.stdout}")
            if result.stderr:
                print(f"Blender警告/错误:\n{result.stderr}")
            print(f"成功渲染到: {output_file}")
        except subprocess.CalledProcessError as e:
            # 渲染出错，但继续处理下一个皮肤
            print(f"渲染 {skin_file} 时出错: {e}")
            print(f"命令返回码: {e.returncode}")
            print(f"命令输出: {e.stdout}")
            print(f"命令错误: {e.stderr}")
        except subprocess.TimeoutExpired:
            print(f"渲染 {skin_file} 时超时")
        except Exception as e:
            print(f"渲染 {skin_file} 时发生未知错误: {e}")
        finally:
            # 应用背景图片（如果启用）
            if self.use_background_image and self.background_image_path and os.path.exists(output_file):
                self.apply_background_image(output_file)
                print(f"成功应用背景图片到: {output_file}")

    def apply_background_image(self, rendered_image_path):
        """将背景图片应用到渲染后的透明图片上"""
        try:
            from PIL import Image
            
            print(f"开始应用背景图片")
            print(f"  渲染图片: {rendered_image_path}")
            print(f"  背景图片: {self.background_image_path}")
            
            # 打开渲染后的透明图片
            rendered_img = Image.open(rendered_image_path).convert("RGBA")
            print(f"  渲染图片尺寸: {rendered_img.size}")
            
            # 打开背景图片
            bg_img = Image.open(self.background_image_path).convert("RGBA")
            print(f"  背景图片原始尺寸: {bg_img.size}")
            
            # 计算缩放因子以保持宽高比
            render_width, render_height = rendered_img.size
            bg_width, bg_height = bg_img.size
            
            # 计算宽度和高度的缩放因子
            scale_x = render_width / bg_width
            scale_y = render_height / bg_height
            
            # 使用较大的缩放因子确保整个背景被覆盖
            scale = max(scale_x, scale_y)
            
            # 计算背景图片新尺寸
            new_bg_width = int(bg_width * scale)
            new_bg_height = int(bg_height * scale)
            
            # 调整背景图片大小并保持宽高比
            bg_img = bg_img.resize((new_bg_width, new_bg_height), Image.LANCZOS)
            print(f"  背景图片调整为: {bg_img.size}，缩放因子 {scale:.2f}")
            
            # 创建与渲染图片尺寸相同的不透明背景
            bg_opaque = Image.new("RGBA", rendered_img.size, (255, 255, 255, 255))
            
            # 计算背景图片居中位置（可能会被裁剪）
            x_offset = (render_width - new_bg_width) // 2
            y_offset = (render_height - new_bg_height) // 2
            
            # 将调整大小的背景图片粘贴到不透明背景上
            bg_opaque.paste(bg_img, (x_offset, y_offset), bg_img)
            print(f"  背景图片居中位置: ({x_offset}, {y_offset})")
            
            # 将渲染图片合成到不透明背景上
            result_img = Image.alpha_composite(bg_opaque, rendered_img)
            print(f"  完成图片合成")
            
            # 保存结果（覆盖原始渲染图片）
            result_img.save(rendered_image_path, "PNG")
            print(f"  背景图片应用成功")
            
        except Exception as e:
            print(f"应用背景图片时出错: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    root = tk.Tk()
    app = SkinRendererApp(root)
    root.mainloop()

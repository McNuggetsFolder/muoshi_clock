import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import time
import psutil
import requests
from PIL import Image, ImageTk, ImageDraw
import win32gui
import win32con
import sys
import os
import winshell
from win32com.client import Dispatch
import threading
import json
import configparser
from datetime import datetime
import webbrowser
import tkinter.ttk as ttk  # 添加导入 tkinter.ttk 模块

class DesktopClock:
    def __init__(self, master):
        self.master = master
        self.config_file = "config.ini"
        self.load_settings()
        self.master.overrideredirect(True)
        self.master.attributes("-topmost", self.topmost)
        self.master.attributes("-transparentcolor", "#ab23ff")  # Transparent color for background

        self.background_image_path = None
        self.cropped_image_path = None
        self.skin_mode = "light"
        self.orientation = "horizontal"
        self.transparent_color = "#ab23ff"
        self.transparency_level = 1.0
        self.show_shadow = False
        self.show_details = True  # Default value for show_details

        self.load_skin()
        self.create_widgets()
        self.create_context_menu()

        self.update_clock()
        self.weather_info = "N/A"
        self.update_weather_thread()

        # Mouse drag variables
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_start_width = 0
        self.resize_start_height = 0
        self.resizing = False
        self.edge_threshold = 8  # Threshold to detect edge

        # Bind mouse events for dragging and resizing
        self.master.bind("<ButtonPress-1>", self.on_drag_or_resize_start)
        self.master.bind("<B1-Motion>", self.on_drag_or_resize_motion)
        self.master.bind("<ButtonRelease-1>", self.on_drag_or_resize_release)

        # Ensure mos directory and subdirectories exist
        self.ensure_mos_directory_structure()
        self.load_window_position_from_config()
        self.load_settings_from_config()

        # Initialize more settings window
        self.more_settings_window = None

    def load_settings(self):
        self.config_file = "config.ini"
        self.ensure_mos_directory_structure()
        self.load_settings_from_config()

    def load_skin(self):
        if self.skin_mode == "dark":
            self.bg_color = "#2c2f33"
            self.fg_color = "#ffffff"
        else:
            self.bg_color = "#ffffff"
            self.fg_color = "#000000"

        self.master.configure(bg=self.bg_color)

    def create_widgets(self):
        # Create four frames for different time information
        self.hour_frame = tk.Frame(self.master, bg=self.bg_color)
        self.minute_frame = tk.Frame(self.master, bg=self.bg_color)
        self.second_frame = tk.Frame(self.master, bg=self.bg_color)
        self.info_frame = tk.Frame(self.master, bg=self.bg_color)

        # Place frames using grid layout manager
        self.hour_frame.grid(row=0, column=0, sticky="nsew")
        self.minute_frame.grid(row=0, column=1, sticky="nsew")
        self.second_frame.grid(row=0, column=2, sticky="nsew")
        self.info_frame.grid(row=0, column=3, sticky="nsew")

        # Configure grid weights to make frames resize proportionally
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_columnconfigure(2, weight=1)
        self.master.grid_columnconfigure(3, weight=1)

        # Initialize time labels
        self.hour_label = tk.Label(self.hour_frame, font=("Arial", 48), bg=self.bg_color, fg=self.fg_color)
        self.minute_label = tk.Label(self.minute_frame, font=("Arial", 48), bg=self.bg_color, fg=self.fg_color)
        self.second_label = tk.Label(self.second_frame, font=("Arial", 48), bg=self.bg_color, fg=self.fg_color)
        self.info_label = tk.Label(self.info_frame, font=("Arial", 16), bg=self.bg_color, fg=self.fg_color)

        # Pack time labels into corresponding frames
        self.hour_label.pack(expand=True)
        self.minute_label.pack(expand=True)
        self.second_label.pack(expand=True)
        self.info_label.pack(expand=True)

        # Initially hide the info frame if show_details is False
        if not self.show_details:
            self.info_frame.grid_remove()

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.master, tearoff=0)
        self.context_menu.add_command(label="设置背景", command=self.set_background)
        self.context_menu.add_command(label="切换皮肤", command=self.toggle_skin)
        self.context_menu.add_command(label="切换方向", command=self.toggle_orientation)
        self.context_menu.add_command(label="鼠标穿透", command=self.toggle_mouse_through)
        self.context_menu.add_command(label="显示阴影", command=self.toggle_shadow)
        self.context_menu.add_separator()
        self.context_menu.add_checkbutton(label="窗口置顶", variable=tk.BooleanVar(value=self.topmost), command=self.toggle_topmost)
        self.context_menu.add_checkbutton(label="显示详细信息", variable=tk.BooleanVar(value=self.show_details), command=self.toggle_show_details)
        self.context_menu.add_checkbutton(label="记住最后运行位置", variable=tk.BooleanVar(value=self.remember_position), command=self.toggle_remember_position)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="更多设置", command=self.show_more_settings)
        self.context_menu.add_command(label="开机自启动", command=self.setup_startup)
        self.context_menu.add_command(label="退出", command=self.exit_app)

        self.master.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def set_background(self):
        self.background_image_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.jpg *.jpeg *.png")])
        if self.background_image_path:
            cropped_image_path = self.crop_and_save_image(self.background_image_path)
            if cropped_image_path:
                self.cropped_image_path = cropped_image_path
                photo = ImageTk.PhotoImage(Image.open(cropped_image_path))
                self.background_image = photo
                canvas = tk.Canvas(self.master, bg=self.bg_color, highlightthickness=0)
                canvas.pack(fill=tk.BOTH, expand=True)
                canvas.create_image(0, 0, anchor=tk.NW, image=self.background_image)
                canvas.image = self.background_image  # Keep a reference to avoid garbage collection

    def crop_and_save_image(self, image_path):
        original_image = Image.open(image_path)
        width, height = original_image.size
        target_width, target_height = 850, 250  # Adjusted size for the entire window

        # Calculate aspect ratios
        orig_aspect_ratio = width / height
        target_aspect_ratio = target_width / target_height

        if orig_aspect_ratio > target_aspect_ratio:
            # Original is wider than target
            new_width = int(height * target_aspect_ratio)
            left = (width - new_width) / 2
            right = (width + new_width) / 2
            top = 0
            bottom = height
        else:
            # Original is taller than target
            new_height = int(width / target_aspect_ratio)
            left = 0
            right = width
            top = (height - new_height) / 2
            bottom = (height + new_height) / 2

        cropped_image = original_image.crop((left, top, right, bottom))
        cropped_image = cropped_image.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # Save the cropped image in the muoshi directory
        filename = os.path.basename(image_path)
        cropped_filename = f"cropped_{filename}"
        cropped_image_path = os.path.join("muoshi", cropped_filename)
        cropped_image.save(cropped_image_path)

        return cropped_image_path

    def toggle_skin(self):
        self.skin_mode = "dark" if self.skin_mode == "light" else "light"
        self.load_skin()
        self.hour_label.config(bg=self.bg_color, fg=self.fg_color)
        self.minute_label.config(bg=self.bg_color, fg=self.fg_color)
        self.second_label.config(bg=self.bg_color, fg=self.fg_color)
        self.info_label.config(bg=self.bg_color, fg=self.fg_color)
        self.save_settings_to_config()

    def toggle_orientation(self):
        self.orientation = "vertical" if self.orientation == "horizontal" else "horizontal"
        self.master.geometry("850x250" if self.orientation == "horizontal" else "250x850")
        if self.background_image_path:
            self.set_background()
        self.save_settings_to_config()

    def toggle_mouse_through(self):
        hwnd = win32gui.GetParent(self.master.winfo_id())
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if self.master.attributes('-disabled'):
            style &= ~win32con.WS_EX_LAYERED & ~win32con.WS_EX_TRANSPARENT
            self.master.attributes('-disabled', False)
        else:
            style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            self.master.attributes('-disabled', True)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
        self.save_settings_to_config()

    def toggle_shadow(self):
        hwnd = win32gui.GetParent(self.master.winfo_id())
        if self.show_shadow:
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
            self.show_shadow = False
        else:
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
            self.show_shadow = True
        self.save_settings_to_config()

    def toggle_topmost(self):
        self.topmost = not self.topmost
        self.master.attributes("-topmost", self.topmost)
        self.save_settings_to_config()

    def toggle_show_details(self):
        self.show_details = not self.show_details
        if self.show_details:
            self.info_frame.grid()
        else:
            self.info_frame.grid_remove()
        self.save_settings_to_config()

    def toggle_remember_position(self):
        self.remember_position = not self.remember_position
        self.save_settings_to_config()

    def update_clock(self):
        current_time = time.strftime("%H:%M:%S")
        hour_str = current_time.split(":")[0]
        minute_str = current_time.split(":")[1]
        second_str = current_time.split(":")[2]

        self.hour_label.config(text=hour_str)
        self.minute_label.config(text=minute_str)
        self.second_label.config(text=second_str)
        self.master.after(1000, self.update_clock)

    def update_system_info(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent

        info_text = f"日期: {time.strftime('%Y-%m-%d')}\nCPU: {cpu_usage}%\n内存: {memory_usage}%\n天气: {self.weather_info}"
        self.info_label.config(text=info_text)

        self.master.after(5000, self.update_system_info)

    def get_weather_info(self):
        city = "北京"
        url = f"http://whrch.cn/weather_mini?city={city}"

        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                weather_data = response.json()
                weather_desc = weather_data.get('weather', 'N/A')
            else:
                weather_desc = "N/A"
        except Exception as e:
            weather_desc = "N/A"

        return weather_desc

    def update_weather_thread(self):
        thread = threading.Thread(target=self.fetch_weather)
        thread.daemon = True
        thread.start()

    def fetch_weather(self):
        while True:
            self.weather_info = self.get_weather_info()
            time.sleep(600)  # Update every 10 minutes

    def setup_startup(self):
        path = os.path.join(os.getcwd(), "desktop_clock.pyw")
        startup_folder = winshell.startup()
        shortcut_path = os.path.join(startup_folder, "桌面时钟.lnk")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = path
        shortcut.Description = "桌面时钟应用程序"
        shortcut.Save()
        
        messagebox.showinfo("提示", "已设置开机自启动")

    def exit_app(self):
        if self.remember_position:
            self.save_window_position_to_config()
        self.save_settings_to_config()
        self.master.destroy()

    def save_window_position_to_config(self):
        position = {
            "x": self.master.winfo_x(),
            "y": self.master.winfo_y(),
            "width": self.master.winfo_width(),
            "height": self.master.winfo_height()
        }
        config = configparser.ConfigParser()
        config.read(self.config_file)
        config['Window'] = position
        with open(self.config_file, 'w') as configfile:
            config.write(configfile)

    def load_window_position_from_config(self):
        if self.remember_position:
            config = configparser.ConfigParser()
            config.read(self.config_file)
            if config.has_section('Window'):
                try:
                    x = int(config['Window'].get('x', 0))
                    y = int(config['Window'].get('y', 0))
                    width = int(config['Window'].get('width', 850))
                    height = int(config['Window'].get('height', 250))
                    self.master.geometry(f"{width}x{height}+{x}+{y}")
                except ValueError:
                    print("Invalid window position or size in config file. Using default values.")

    def save_settings_to_config(self):
        settings = {
            "skin_mode": self.skin_mode,
            "orientation": self.orientation,
            "transparent_color": self.transparent_color,
            "show_shadow": str(self.show_shadow).lower(),
            "topmost": str(self.topmost).lower(),
            "show_details": str(self.show_details).lower(),
            "remember_position": str(self.remember_position).lower()
        }
        config = configparser.ConfigParser()
        config.read(self.config_file)
        config['Settings'] = settings
        with open(self.config_file, 'w') as configfile:
            config.write(configfile)

    def load_settings_from_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file)
        if config.has_section('Settings'):
            self.skin_mode = config['Settings'].get('skin_mode', 'light')
            self.orientation = config['Settings'].get('orientation', 'horizontal')
            self.transparent_color = config['Settings'].get('transparent_color', '#ab23ff')
            self.show_shadow = config['Settings'].getboolean('show_shadow', False)
            self.topmost = config['Settings'].getboolean('topmost', True)
            self.show_details = config['Settings'].getboolean('show_details', True)
            self.remember_position = config['Settings'].getboolean('remember_position', True)
        else:
            self.skin_mode = "light"
            self.orientation = "horizontal"
            self.transparent_color = "#ab23ff"
            self.show_shadow = False
            self.topmost = True
            self.show_details = True
            self.remember_position = True

    def ensure_mos_directory_structure(self):
        mos_dir = "mos"
        if not os.path.exists(mos_dir):
            os.makedirs(mos_dir)
            print(f"Created directory: {mos_dir}")

        for i in range(4):
            subdir = os.path.join(mos_dir, str(i))
            if not os.path.exists(subdir):
                os.makedirs(subdir)
                print(f"Created directory: {subdir}")

            config_file = os.path.join(subdir, "config.ini")
            if not os.path.exists(config_file):
                self.create_default_config(config_file)
                print(f"Created default config file: {config_file}")
            else:
                self.config_file = config_file
                print(f"Loaded config file: {config_file}")

    def create_default_config(self, config_path):
        config = configparser.ConfigParser()
        config['DEFAULT'] = {
            'Setting1': 'Value1',
            'Setting2': 'Value2'
        }
        config['Settings'] = {
            'skin_mode': 'light',
            'orientation': 'horizontal',
            'transparent_color': '#ab23ff',
            'show_shadow': 'False',
            'topmost': 'True',
            'show_details': 'True',
            'remember_position': 'True'
        }
        with open(config_path, 'w') as configfile:
            config.write(configfile)

    def on_drag_or_resize_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        width = self.master.winfo_width()
        height = self.master.winfo_height()

        if event.x < self.edge_threshold:
            if event.y < self.edge_threshold:
                self.resizing_corner = 'nw'
            elif event.y > height - self.edge_threshold:
                self.resizing_corner = 'sw'
            else:
                self.resizing_corner = 'w'
        elif event.x > width - self.edge_threshold:
            if event.y < self.edge_threshold:
                self.resizing_corner = 'ne'
            elif event.y > height - self.edge_threshold:
                self.resizing_corner = 'se'
            else:
                self.resizing_corner = 'e'
        elif event.y < self.edge_threshold:
            self.resizing_corner = 'n'
        elif event.y > height - self.edge_threshold:
            self.resizing_corner = 's'
        else:
            self.resizing_corner = 'move'

        if self.resizing_corner != 'move':
            self.resizing = True
            self.resize_start_x = event.x
            self.resize_start_y = event.y
            self.resize_start_width = width
            self.resize_start_height = height

    def on_drag_or_resize_motion(self, event):
        if self.resizing:
            new_width = self.resize_start_width + event.x - self.resize_start_x
            new_height = self.resize_start_height + event.y - self.resize_start_y

            if self.resizing_corner == 'nw':
                x = self.master.winfo_x() + event.x - self.resize_start_x
                y = self.master.winfo_y() + event.y - self.resize_start_y
                scale_factor = min(new_width / self.resize_start_width, new_height / self.resize_start_height)
                new_width = int(self.resize_start_width * scale_factor)
                new_height = int(self.resize_start_height * scale_factor)
                self.master.geometry(f"+{x}+{y}")
                self.master.geometry(f"{new_width}x{new_height}")
            elif self.resizing_corner == 'ne':
                y = self.master.winfo_y() + event.y - self.resize_start_y
                scale_factor = min(new_width / self.resize_start_width, new_height / self.resize_start_height)
                new_width = int(self.resize_start_width * scale_factor)
                new_height = int(self.resize_start_height * scale_factor)
                self.master.geometry(f"+{self.master.winfo_x()}+{y}")
                self.master.geometry(f"{new_width}x{new_height}")
            elif self.resizing_corner == 'sw':
                x = self.master.winfo_x() + event.x - self.resize_start_x
                scale_factor = min(new_width / self.resize_start_width, new_height / self.resize_start_height)
                new_width = int(self.resize_start_width * scale_factor)
                new_height = int(self.resize_start_height * scale_factor)
                self.master.geometry(f"+{x}+{self.master.winfo_y()}")
                self.master.geometry(f"{new_width}x{new_height}")
            elif self.resizing_corner == 'se':
                scale_factor = min(new_width / self.resize_start_width, new_height / self.resize_start_height)
                new_width = int(self.resize_start_width * scale_factor)
                new_height = int(self.resize_start_height * scale_factor)
                self.master.geometry(f"{new_width}x{new_height}")
            elif self.resizing_corner == 'n':
                y = self.master.winfo_y() + event.y - self.resize_start_y
                scale_factor = min(new_width / self.resize_start_width, new_height / self.resize_start_height)
                new_height = int(self.resize_start_height * scale_factor)
                self.master.geometry(f"+{self.master.winfo_x()}+{y}")
                self.master.geometry(f"{self.master.winfo_width()}x{new_height}")
            elif self.resizing_corner == 's':
                scale_factor = min(new_width / self.resize_start_width, new_height / self.resize_start_height)
                new_height = int(self.resize_start_height * scale_factor)
                self.master.geometry(f"{self.master.winfo_width()}x{new_height}")
            elif self.resizing_corner == 'w':
                x = self.master.winfo_x() + event.x - self.resize_start_x
                scale_factor = min(new_width / self.resize_start_width, new_height / self.resize_start_height)
                new_width = int(self.resize_start_width * scale_factor)
                self.master.geometry(f"+{x}+{self.master.winfo_y()}")
                self.master.geometry(f"{new_width}x{self.master.winfo_height()}")
            elif self.resizing_corner == 'e':
                scale_factor = min(new_width / self.resize_start_width, new_height / self.resize_start_height)
                new_width = int(self.resize_start_width * scale_factor)
                self.master.geometry(f"{new_width}x{self.master.winfo_height()}")
        else:
            x = self.master.winfo_x() + event.x - self.drag_start_x
            y = self.master.winfo_y() + event.y - self.drag_start_y
            self.master.geometry(f"+{x}+{y}")

    def on_drag_or_resize_release(self, event):
        self.resizing = False
        if self.remember_position:
            self.save_window_position_to_config()

    def async_weather_and_system_monitor(self, weather_func, system_func, update_ui_func):
        def worker():
            while True:
                try:
                    weather_data = weather_func()
                    system_data = system_func()
                    update_ui_func(weather_data, system_data)
                except Exception as e:
                    print(f"Async worker error: {e}")
                time.sleep(2)  # 每2秒更新一次
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def apply_rounded_corners(self, image_path, radius):
        try:
            image = Image.open(image_path).convert("RGBA")
            mask = Image.new("L", image.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0) + image.size, fill=255, radius=radius)
            result = Image.new("RGBA", image.size)
            result.paste(image, mask=mask)
            return result
        except Exception as e:
            print(f"Error applying rounded corners: {e}")
            return Image.open(image_path)

    def create_more_settings_window(self):
        if self.more_settings_window is None or not self.more_settings_window.winfo_exists():
            self.more_settings_window = tk.Toplevel(self.master)
            self.more_settings_window.title("更多设置")
            self.more_settings_window.geometry("800x600")
            self.more_settings_window.transient(self.master)
            self.more_settings_window.grab_set()

            # 创建 Notebook 容器
            self.notebook = tk.ttk.Notebook(self.more_settings_window)
            self.notebook.pack(fill=tk.BOTH, expand=True)
            
            # 详细设置选项卡
            self.detailed_settings_frame = tk.ttk.Frame(self.notebook)
            self.notebook.add(self.detailed_settings_frame, text="详细设置")
            
            # 天气功能集成选项卡
            self.weather_integration_frame = tk.ttk.Frame(self.notebook)
            self.notebook.add(self.weather_integration_frame, text="天气功能集成")
            
            # 窗口设置选项卡
            self.window_settings_frame = tk.ttk.Frame(self.notebook)
            self.notebook.add(self.window_settings_frame, text="窗口设置")
            
            # 配置文件管理选项卡
            self.config_manager_frame = tk.ttk.Frame(self.notebook)
            self.notebook.add(self.config_manager_frame, text="配置文件管理")
            
            # 关于页面选项卡
            self.about_frame = tk.ttk.Frame(self.notebook)
            self.notebook.add(self.about_frame, text="关于")
            
            # 初始化各选项卡内容
            self.setup_detailed_settings()
            self.setup_weather_integration()
            self.setup_window_settings()
            self.setup_config_manager()
            self.setup_about_page()

            # 启动异步数据更新
            self.async_weather_and_system_monitor(
                self.get_weather_data,
                self.get_system_data,
                self.update_ui_data
            )

    def setup_detailed_settings(self):
        # 详细设置内容
        tk.ttk.Label(self.detailed_settings_frame, text="详细设置内容").grid(row=0, column=0, padx=10, pady=10)
        
        # 添加更多控件...
        self.opacity_scale = tk.ttk.Scale(self.detailed_settings_frame, from_=0.3, to=1.0)
        self.opacity_scale.grid(row=1, column=0, padx=10, pady=10)

    def setup_weather_integration(self):
        # 天气功能集成内容
        tk.ttk.Label(self.weather_integration_frame, text="天气功能集成").grid(row=0, column=0, padx=10, pady=10)
        
        # 天气请求次数限制
        self.weather_limit_var = tk.BooleanVar(value=True)
        tk.ttk.Checkbutton(self.weather_integration_frame, text="限制天气请求次数", variable=self.weather_limit_var).grid(row=1, column=0, padx=10, pady=5)
        
        self.request_limit_spinbox = tk.ttk.Spinbox(self.weather_integration_frame, from_=1, to=20)
        self.request_limit_spinbox.grid(row=1, column=1, padx=10, pady=5)
        
        # 显示当前日期格式
        tk.ttk.Label(self.weather_integration_frame, text="日期格式:").grid(row=2, column=0, padx=10, pady=5)
        self.date_format_entry = tk.ttk.Entry(self.weather_integration_frame)
        self.date_format_entry.insert(0, "%Y年%m月%d日")
        self.date_format_entry.grid(row=2, column=1, padx=10, pady=5)
        
        # 实时系统监控
        self.cpu_label = tk.ttk.Label(self.weather_integration_frame, text="CPU: --%")
        self.cpu_label.grid(row=3, column=0, padx=10, pady=5)
        
        self.memory_label = tk.ttk.Label(self.weather_integration_frame, text="内存: --%")
        self.memory_label.grid(row=3, column=1, padx=10, pady=5)
        
        # 天气数据显示区（绿色边框+圆角）
        self.weather_display = tk.Canvas(self.weather_integration_frame, bg="#e0ffe0", highlightthickness=2, highlightbackground="#4CAF50")
        self.weather_display.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        # 圆角效果
        self.weather_display.create_rectangle(0, 0, 400, 100, outline="#4CAF50", fill="#e0ffe0", width=2, tags="bg_rect")
        self.weather_display.lower("bg_rect")

    def setup_window_settings(self):
        # 窗口设置内容
        tk.ttk.Label(self.window_settings_frame, text="窗口设置").grid(row=0, column=0, padx=10, pady=10)
        
        # 背景不透明度
        tk.ttk.Label(self.window_settings_frame, text="背景不透明度:").grid(row=1, column=0, padx=10, pady=5)
        self.bg_opacity_scale = tk.ttk.Scale(self.window_settings_frame, from_=0.3, to=1.0)
        self.bg_opacity_scale.grid(row=1, column=1, padx=10, pady=5)
        
        # 圆角程度
        tk.ttk.Label(self.window_settings_frame, text="圆角程度:").grid(row=2, column=0, padx=10, pady=5)
        self.corner_radius_spinbox = tk.ttk.Spinbox(self.window_settings_frame, from_=0, to=20)
        self.corner_radius_spinbox.grid(row=2, column=1, padx=10, pady=5)
        
        # 背景图片选择
        tk.ttk.Button(self.window_settings_frame, text="选择背景图片", command=self.select_background).grid(row=3, column=0, columnspan=2, padx=10, pady=10)

    def select_background(self):
        file_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.jpg *.jpeg *.png")])
        if file_path:
            try:
                radius = int(self.corner_radius_spinbox.get())
                radius = max(0, min(radius, 20))  # 限制范围
                self.background_image = self.apply_rounded_corners(file_path, radius)
                self.update_background()
            except Exception as e:
                messagebox.showerror("错误", f"设置背景图片失败: {e}")

    def update_background(self):
        if self.background_image:
            photo = ImageTk.PhotoImage(self.background_image)
            self.master.configure(bg="white")
            # 更新背景...

    def setup_config_manager(self):
        # 配置文件管理内容
        tk.ttk.Label(self.config_manager_frame, text="配置文件管理").grid(row=0, column=0, padx=10, pady=10)
        
        # 配置文件列表
        self.config_tree = tk.ttk.Treeview(self.config_manager_frame, columns=("Name"), show="headings")
        self.config_tree.heading("Name", text="配置文件")
        self.config_tree.grid(row=1, column=0, padx=10, pady=10)
        
        # 按钮组
        button_frame = tk.ttk.Frame(self.config_manager_frame)
        button_frame.grid(row=2, column=0, padx=10, pady=10)
        
        tk.ttk.Button(button_frame, text="新建配置", command=self.create_new_config).grid(row=0, column=0, padx=5)
        tk.ttk.Button(button_frame, text="重命名配置", command=self.rename_config).grid(row=0, column=1, padx=5)
        tk.ttk.Button(button_frame, text="删除配置", command=self.delete_config).grid(row=0, column=2, padx=5)

    def create_new_config(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        config_name = f"config_{timestamp}.json"
        
        # 特殊字符校验
        if any(c in '\/:*?"<>|' for c in config_name):
            messagebox.showerror("错误", "配置文件名包含非法字符")
            return
        
        try:
            with open(config_name, 'w') as f:
                json.dump({}, f)
            self.config_tree.insert("", tk.END, values=(config_name,))
        except Exception as e:
            messagebox.showerror("错误", f"创建配置文件失败: {e}")

    def rename_config(self):
        selected = self.config_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要重命名的配置文件")
            return
        
        old_name = self.config_tree.item(selected[0])["values"][0]
        new_name = simpledialog.askstring("重命名", "输入新名称:", initialvalue=old_name)
        
        if new_name:
            # 特殊字符校验
            if any(c in '\/:*?"<>|' for c in new_name):
                messagebox.showerror("错误", "配置文件名包含非法字符")
                return
            
            if new_name.endswith(".json"):
                try:
                    os.rename(old_name, new_name)
                    self.config_tree.item(selected[0], values=(new_name,))
                except Exception as e:
                    messagebox.showerror("错误", f"重命名失败: {e}")
            else:
                messagebox.showerror("错误", "配置文件必须以 .json 结尾")

    def delete_config(self):
        selected = self.config_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要删除的配置文件")
            return
        
        if messagebox.askyesno("确认", "确定要删除选中的配置文件吗?"):
            config_name = self.config_tree.item(selected[0])["values"][0]
            try:
                os.remove(config_name)
                self.config_tree.delete(selected[0])
            except Exception as e:
                messagebox.showerror("错误", f"删除配置文件失败: {e}")

    def setup_about_page(self):
        # 关于页面内容
        tk.ttk.Label(self.about_frame, text="程序名称：木偶时钟", font=("Arial", 16, "bold")).grid(row=0, column=0, padx=10, pady=10)
        tk.ttk.Label(self.about_frame, text="作者信息：在改了的鸡块").grid(row=1, column=0, padx=10, pady=10)
        
        # 超链接
        link = tk.ttk.Label(self.about_frame, text="说明文档：此代码完全由AI编写", foreground="blue", cursor="hand2")
        link.grid(row=2, column=0, padx=10, pady=10)
        link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com"))

    def show_more_settings(self):
        self.create_more_settings_window()

    def get_weather_data(self):
        # 模拟天气数据获取
        return {
            "temperature": 25,
            "condition": "晴",
            "cold_risk": 10
        }

    def get_system_data(self):
        # 获取系统监控数据
        return {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent
        }

    def update_ui_data(self, weather_data, system_data):
        # 更新UI显示
        self.cpu_label.config(text=f"CPU: {system_data['cpu_usage']:.1f}%")
        self.memory_label.config(text=f"内存: {system_data['memory_usage']:.1f}%")
        
        # 更新天气显示
        self.weather_display.delete("weather_text")
        self.weather_display.create_text(
            200, 50,
            text=f"温度: {weather_data['temperature']}°C\n状况: {weather_data['condition']}\n感冒概率: {weather_data['cold_risk']}%",
            tags="weather_text"
        )

    def load_configuration(self):
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # 加载配置...
        except FileNotFoundError:
            print("配置文件不存在，使用默认设置")
        except json.JSONDecodeError:
            print("配置文件解析错误，使用默认设置")

def main():
    root = tk.Tk()
    desktop_clock = DesktopClock(root)
    root.mainloop()

if __name__ == "__main__":
    main()
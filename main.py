import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from ttkthemes import ThemedTk
from PIL import Image, ImageTk
import pillow_heif
import os
import subprocess
import shutil
import threading
import sys
from pathlib import Path

# 注册 HEIF 和 AVIF 格式支持
try:
    pillow_heif.register_heif_opener()
    pillow_heif.register_avif_opener()
except ImportError:
    print("pillow_heif 未安装，HEIC/AVIF 格式支持不可用")
except Exception as e:
    print(f"初始化 HEIC/AVIF 支持时出错: {e}")

# 常量定义
THUMBNAIL_SIZE = 120
PADDING = 5
SCROLLBAR_WIDTH = 20
DEFAULT_COMPRESSION = 100


class ImageProcessor:
    """处理图片的核心逻辑"""

    def __init__(self):
        self.image_paths = []
        self.output_folder = ""
        self.thumbnail_cache = {}
        self.selected_thumbnails = []
        self.image_info = {}

    def select_images(self):
        """选择图片文件"""
        self.selected_thumbnails.clear()
        self.image_paths = list(
            filedialog.askopenfilenames(
                filetypes=[
                    ("Image files", "*.jpg;*.jpeg;*.png;*.heic;*.heif;*.webp;*.avif")
                ]
            )
        )
        if self.image_paths:
            self.image_info = {path: os.path.getsize(path) for path in self.image_paths}
            self.show_thumbnails()

    def show_thumbnails(self):
        """显示缩略图"""
        for widget in thumbnail_frame.winfo_children():
            widget.destroy()

        if not self.image_paths:
            return

        frame_width = thumbnail_frame.winfo_width() or 600
        columns = max(
            1, (frame_width - PADDING - SCROLLBAR_WIDTH) // (THUMBNAIL_SIZE + PADDING)
        )

        canvas = tk.Canvas(thumbnail_frame)
        scrollbar = ttk.Scrollbar(
            thumbnail_frame, orient="vertical", command=canvas.yview
        )
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.update_idletasks()
        scrollable_frame.config(width=frame_width - SCROLLBAR_WIDTH)

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", on_configure)

        # 绑定鼠标滚轮事件
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for index, image_path in enumerate(self.image_paths):
            self.create_thumbnail(
                scrollable_frame, image_path, index, columns, THUMBNAIL_SIZE, PADDING
            )

        for index, image_path in enumerate(self.image_paths):
            self.create_thumbnail(
                scrollable_frame, image_path, index, columns, THUMBNAIL_SIZE, PADDING
            )

        thumbnail_frame.update_idletasks()

    def create_thumbnail(self, parent, image_path, index, columns, thumbnail_size, padding):
        """创建单个缩略图"""
        row = index // columns
        col = index % columns

        frame = ttk.Frame(parent, style="TFrame", padding=3)
        frame.grid(row=row, column=col, padx=padding, pady=padding)
        frame.image_path = image_path

        file_name = os.path.basename(image_path)
        file_name = file_name[:12] + "..." if len(file_name) > 15 else file_name
        file_size = self.image_info[image_path]
        size_str = self.format_file_size(file_size)

        thumbnail_label = ttk.Label(frame, text="加载中...", width=thumbnail_size // 10)
        thumbnail_label.pack()

        text_label = ttk.Label(
            frame,
            text=f"{file_name} ({size_str})",
            wraplength=thumbnail_size,
            justify="center",
            padding=(0, 2, 0, 2),
            style="TLabel",
        )
        text_label.pack()

        self.load_thumbnail_async(thumbnail_label, image_path)

        frame.bind("<Button-1>", lambda event: self.on_thumbnail_click(event, frame))
        thumbnail_label.bind("<Button-1>", lambda event: self.on_thumbnail_click(event, frame))
        text_label.bind("<Button-1>", lambda event: self.on_thumbnail_click(event, frame))

    def load_thumbnail_async(self, thumbnail_label, image_path):
        """异步加载缩略图"""
        def load_thumbnail():
            try:
                if image_path in self.thumbnail_cache:
                    img_tk = self.thumbnail_cache[image_path]
                else:
                    with Image.open(image_path) as img:
                        img.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE))
                        img_tk = ImageTk.PhotoImage(img)
                        self.thumbnail_cache[image_path] = img_tk

                def update_thumbnail():
                    thumbnail_label.configure(image=img_tk, text="")
                    thumbnail_label.image = img_tk

                root.after(0, update_thumbnail)
            except Exception as e:
                print(f"加载缩略图失败: {e}")

                def show_error():
                    thumbnail_label.configure(text="加载失败")

                root.after(0, show_error)

        threading.Thread(target=load_thumbnail, daemon=True).start()

    def on_thumbnail_click(self, event, frame):
        """处理缩略图点击事件"""
        if event.state & 0x4:  # Ctrl键按下
            if frame in self.selected_thumbnails:
                self.selected_thumbnails.remove(frame)
                frame.config(style="TFrame")
                for child in frame.winfo_children():
                    if isinstance(child, ttk.Label):
                        child.config(style="TLabel")
            else:
                self.selected_thumbnails.append(frame)
                frame.config(style="Selected.TFrame")
                for child in frame.winfo_children():
                    if isinstance(child, ttk.Label):
                        child.config(style="Selected.TLabel")
        else:
            for f in self.selected_thumbnails:
                f.config(style="TFrame")
                for child in f.winfo_children():
                    if isinstance(child, ttk.Label):
                        child.config(style="TLabel")
            self.selected_thumbnails.clear()
            self.selected_thumbnails.append(frame)
            frame.config(style="Selected.TFrame")
            for child in frame.winfo_children():
                if isinstance(child, ttk.Label):
                    child.config(style="Selected.TLabel")

    def format_file_size(self, file_size):
        """格式化文件大小"""
        if file_size < 1024:
            return f"{file_size} B"
        elif file_size < 1024 * 1024:
            return f"{file_size / 1024:.1f} KB"
        else:
            return f"{file_size / (1024 * 1024):.1f} MB"

    def start_processing(self):
        """开始处理图片"""
        if not self.validate_processing():
            return
        output_format = output_format_var.get()
        total_images = len(self.image_paths)

        thread = threading.Thread(
            target=self.process_images, args=(output_format, total_images)
        )
        thread.start()

    def process_images(self, output_format, total_images):
        """批量处理图片"""
        for i, image_path in enumerate(self.image_paths, start=1):
            self.process_single_image(image_path, output_format, i, total_images)
        self.reset_progress()
        if messagebox.askyesno("完成", "图片处理完成，是否打开输出目录？"):
            self.open_output_folder()

    def open_output_folder(self):
        """打开输出文件夹"""
        if os.name == "nt":  # Windows
            os.startfile(self.output_folder)
        elif os.name == "posix":  # macOS 或 Linux
            if sys.platform == "darwin":  # macOS
                subprocess.Popen(["open", self.output_folder])
            else:  # Linux
                subprocess.Popen(["xdg-open", self.output_folder])

    def validate_processing(self):
        """验证处理条件"""
        if not self.image_paths:
            messagebox.showerror("错误", "请选择要处理的图片")
            return False
        if not self.output_folder:
            messagebox.showerror("错误", "请选择输出位置")
            return False
        return True

    def process_single_image(self, image_path, output_format, current, total):
        """处理单张图片"""
        try:
            file_name = os.path.splitext(os.path.basename(image_path))[0]
            compression_quality = int(compression_scale.get())

            output_path = self.get_output_path(image_path, output_format, file_name)

            if os.path.exists(output_path):
                action = self.handle_file_conflict(output_path)
                if action == "skip":
                    self.update_progress(current, total)
                    return
                elif action == "cancel":
                    raise Exception("操作已取消")

            if output_format == "original" and compression_quality == 100:
                shutil.copy2(image_path, output_path)
            else:
                self.save_image(image_path, output_path, output_format, compression_quality)

            self.update_progress(current, total)
        except PermissionError:
            messagebox.showerror("错误", f"没有权限访问文件: {image_path}")
        except Exception as e:
            messagebox.showerror("错误", f"处理图片 {image_path} 时出错: {str(e)}")

    def get_output_path(self, image_path, output_format, file_name):
        """获取输出路径"""
        if output_format == "original":
            return Path(self.output_folder) / os.path.basename(image_path)
        else:
            return Path(self.output_folder) / f"{file_name}.{output_format}"

    def save_image(self, image_path, output_path, output_format, compression_quality):
        """保存图片"""
        with Image.open(image_path) as img:
            exif_data = img.info.get("exif")
            if compression_quality < 100:
                img.save(output_path, quality=compression_quality, exif=exif_data) if output_format == "webp" else img.save(output_path, quality=compression_quality)
            else:
                img.save(output_path, lossless=True, exif=exif_data) if output_format == "webp" else img.save(output_path, lossless=True)

    def handle_file_conflict(self, file_path):
        """处理文件冲突"""
        class ConflictDialog(tk.Toplevel):
            def __init__(self, parent):
                super().__init__(parent)
                self.result = None
                self.apply_to_all = tk.BooleanVar()

                self.title("文件已存在")
                self.geometry("400x150")
                self.resizable(False, False)

                message = f"文件 '{os.path.basename(file_path)}' 已存在，要如何处理？"
                ttk.Label(self, text=message, wraplength=380).pack(pady=10, padx=10)

                ttk.Checkbutton(
                    self, text="应用到所有文件", variable=self.apply_to_all
                ).pack()

                btn_frame = ttk.Frame(self)
                btn_frame.pack(pady=10)

                ttk.Button(
                    btn_frame, text="覆盖", command=lambda: self.set_result("overwrite")
                ).pack(side=tk.LEFT, padx=5)
                ttk.Button(
                    btn_frame, text="跳过", command=lambda: self.set_result("skip")
                ).pack(side=tk.LEFT, padx=5)
                ttk.Button(
                    btn_frame, text="取消", command=lambda: self.set_result("cancel")
                ).pack(side=tk.LEFT, padx=5)

                self.transient(parent)
                self.grab_set()
                parent.wait_window(self)

            def set_result(self, value):
                self.result = (value, self.apply_to_all.get())
                self.destroy()

        if hasattr(self.handle_file_conflict, "global_action"):
            return self.handle_file_conflict.global_action

        dialog = ConflictDialog(root)
        if dialog.result is None:
            return "cancel"

        action, apply_to_all = dialog.result

        if apply_to_all:
            self.handle_file_conflict.global_action = action

        return action

    def update_progress(self, current, total):
        """更新进度条"""
        progress = (current / total) * 100
        progress_bar["value"] = progress
        progress_label.config(text=f"{current}/{total} ({progress:.1f}%)")
        root.update_idletasks()

    def reset_progress(self):
        """重置进度条"""
        progress_bar["value"] = 0
        progress_label.config(text="0/0 (0.0%)")

    def select_output_folder(self):
        """选择输出文件夹"""
        self.output_folder = filedialog.askdirectory()
        if self.output_folder:
            output_folder_label.config(
                text=f"输出位置: {self.output_folder}", wraplength=300
            )

    def delete_selected_image(self):
        """删除选中的图片"""
        if self.selected_thumbnails:
            for frame in self.selected_thumbnails:
                image_path = frame.image_path
                self.image_paths.remove(image_path)
                self.thumbnail_cache.pop(image_path, None)
                frame.destroy()
            self.selected_thumbnails.clear()
            self.show_thumbnails()

    def clear_all_images(self):
        """清除所有图片"""
        self.image_paths = []
        self.show_thumbnails()


class ImageConverterApp:
    """图片转换应用的 UI 部分"""

    def __init__(self, root):
        self.root = root
        self.image_processor = ImageProcessor()
        self.setup_ui()

    def setup_ui(self):
        """设置 UI 布局"""
        self.root.title("图片格式转换工具")
        self.root.geometry("800x700")
        self.root.minsize(600, 700)

        style = ttk.Style()
        style.configure("TFrame", padding=5)
        style.configure(
            "Selected.TFrame",
            background="#e5f3ff",
            bordercolor="#0078d4",
            borderwidth=1,
            relief="solid",
            padding=3,
        )
        style.configure(
            "TLabel",
            background=style.lookup("TFrame", "background"),
            padding=2,
        )
        style.configure(
            "Selected.TLabel", background="#e5f3ff", padding=2
        )

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.LabelFrame(main_frame, text="操作区", padding="5")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.setup_file_frame(control_frame)
        self.setup_buttons_frame(control_frame)
        self.setup_output_frame(control_frame)
        self.setup_progress_frame(control_frame)

        preview_frame = ttk.LabelFrame(main_frame, text="图片预览", padding="5")
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        global thumbnail_frame
        thumbnail_frame = ttk.Frame(preview_frame)
        thumbnail_frame.pack(fill=tk.BOTH, expand=True)

    def setup_file_frame(self, parent):
        """设置文件选择区域"""
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=tk.X, pady=(0, 10))

        select_images_button = ttk.Button(
            file_frame, text="选择图片", command=self.image_processor.select_images
        )
        select_images_button.pack(fill=tk.X, pady=2)

        global image_count_label
        image_count_label = ttk.Label(file_frame, text="未选择图片")
        image_count_label.pack(fill=tk.X, pady=2)

    def setup_buttons_frame(self, parent):
        """设置按钮区域"""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill=tk.X, pady=5)

        delete_button = ttk.Button(
            buttons_frame, text="删除选中图片", command=self.image_processor.delete_selected_image
        )
        delete_button.pack(fill=tk.X, pady=2)

        clear_button = ttk.Button(
            buttons_frame, text="清除所有所选", command=self.image_processor.clear_all_images
        )
        clear_button.pack(fill=tk.X, pady=2)

    def setup_output_frame(self, parent):
        """设置输出选项区域"""
        output_frame = ttk.LabelFrame(parent, text="输出选项", padding="5")
        output_frame.pack(fill=tk.X, pady=10)

        formats = ["original", "jpg", "heic", "heif", "webp", "avif"]
        global output_format_var
        output_format_var = tk.StringVar(value="original")
        for format in formats:
            ttk.Radiobutton(
                output_frame,
                text="原始格式" if format == "original" else format.upper(),
                variable=output_format_var,
                value=format,
            ).pack(anchor=tk.W, pady=2)

        select_output_folder_button = ttk.Button(
            output_frame, text="选择输出位置", command=self.image_processor.select_output_folder
        )
        select_output_folder_button.pack(fill=tk.X, pady=5)

        global output_folder_label
        output_folder_label = ttk.Label(
            output_frame, text="未选择输出位置", anchor=tk.W, width=20
        )
        output_folder_label.pack(fill=tk.X)

        self.create_tooltip(output_folder_label)

        compression_label = ttk.Label(output_frame, text="压缩质量 (100% 不压缩):")
        compression_label.pack(fill=tk.X, pady=2)

        global compression_scale, compression_value_label
        compression_scale = ttk.Scale(output_frame, from_=25, to=100, orient=tk.HORIZONTAL)
        compression_scale.set(DEFAULT_COMPRESSION)
        compression_scale.pack(side=tk.TOP, fill=tk.X, expand=True)

        compression_value_label = ttk.Label(output_frame, text=f"{DEFAULT_COMPRESSION}%")
        compression_value_label.pack(side=tk.BOTTOM)

        compression_scale.bind("<Motion>", self.update_compression_value)
        compression_scale.bind("<ButtonRelease-1>", self.update_compression_value)

        start_button = ttk.Button(
            output_frame, text="开始处理", command=self.image_processor.start_processing
        )
        start_button.pack(fill=tk.X, pady=10)

    def setup_progress_frame(self, parent):
        """设置进度条区域"""
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, pady=5)

        global progress_bar, progress_label
        progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        progress_bar.pack(fill=tk.X)

        progress_label = ttk.Label(progress_frame, text="0/0 (0.0%)")
        progress_label.pack()

    def create_tooltip(self, widget):
        """创建工具提示"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

            label = ttk.Label(
                tooltip,
                text=widget.cget("text"),
                background="#ffffe0",
                relief="solid",
                borderwidth=1,
            )
            label.pack()

            def hide_tooltip():
                tooltip.destroy()

            widget.tooltip = tooltip
            widget.bind("<Leave>", lambda e: hide_tooltip())
            tooltip.bind("<Leave>", lambda e: hide_tooltip())

        widget.bind("<Enter>", show_tooltip)

    def update_compression_value(self, event):
        """更新压缩质量显示"""
        value = int(compression_scale.get())
        compression_value_label.config(text=f"{value}%")


if __name__ == "__main__":
    root = ThemedTk(theme="yaru")
    app = ImageConverterApp(root)
    root.mainloop()
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from ttkthemes import ThemedTk
import math
from PIL import Image, ImageTk
import pillow_heif
import pillow_jxl
import os
import subprocess
import shutil
import threading

pillow_heif.register_heif_opener()

class ImageProcessor:
    def __init__(self):
        self.image_paths = []
        self.output_folder = ""
        self.thumbnail_cache = {}
        self.selected_thumbnails = []
        self.image_info = {}
    
    def select_images(self):
        self.image_paths = list(filedialog.askopenfilenames(filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.heic;*.heif;*.webp;*.jxl")]))
        if self.image_paths:
            self.image_info = {path: os.path.getsize(path) for path in self.image_paths}
            image_count_label.config(text=f"已选择 {len(self.image_paths)} 张图片")
            self.show_thumbnails()

    def show_thumbnails(self):
        for widget in thumbnail_frame.winfo_children():
            widget.destroy()

        if not self.image_paths:
            return

        thumbnail_size = 120
        padding = 10
        frame_width = thumbnail_frame.winfo_width() or 600
        columns = max(1, (frame_width - padding) // (thumbnail_size + padding))

        canvas = tk.Canvas(thumbnail_frame)
        scrollbar = ttk.Scrollbar(thumbnail_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # 将 scrollable_frame 添加到 canvas
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 配置滚动区域
        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", on_configure)

        # 确保 canvas 和 scrollable_frame 不阻止事件传递
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 创建缩略图
        for index, image_path in enumerate(self.image_paths):
            self.create_thumbnail(scrollable_frame, image_path, index, columns, thumbnail_size, padding)

    def create_thumbnail(self, parent, image_path, index, columns, thumbnail_size, padding):
        row = index // columns
        col = index % columns

        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col, padx=padding, pady=padding)
        frame.image_path = image_path

        file_name = os.path.basename(image_path)
        file_name = file_name[:12] + "..." if len(file_name) > 15 else file_name
        file_size = self.image_info[image_path]
        size_str = f"{file_size} B" if file_size < 1024 else f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f} MB"

        thumbnail_label = ttk.Label(frame, text="加载中...", width=thumbnail_size//10)
        thumbnail_label.pack()

        text_label = ttk.Label(frame, text=f"{file_name} ({size_str})", wraplength=thumbnail_size)
        text_label.pack()

        def load_thumbnail():
            try:
                if image_path in self.thumbnail_cache:
                    img_tk = self.thumbnail_cache[image_path]
                else:
                    with Image.open(image_path) as img:
                        img.thumbnail((thumbnail_size, thumbnail_size))
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

        def on_thumbnail_click(event):
            if event.state & 0x4:  # 检查Ctrl键是否被按下
                if frame in self.selected_thumbnails:
                    self.selected_thumbnails.remove(frame)
                    frame.config(style='TFrame')
                else:
                    self.selected_thumbnails.append(frame)
                    frame.config(style='Selected.TFrame')
            else:
                if frame not in self.selected_thumbnails:
                    self.selected_thumbnails.clear()
                    for f in self.selected_thumbnails:
                        f.config(style='TFrame')
                    self.selected_thumbnails.append(frame)
                    frame.config(style='Selected.TFrame')
                else:
                    self.selected_thumbnails.clear()
                    frame.config(style='TFrame')

        # 绑定点击事件到 frame
        frame.bind("<Button-1>", on_thumbnail_click)
        thumbnail_label.bind("<Button-1>", on_thumbnail_click)  # 同时绑定到缩略图标签
        text_label.bind("<Button-1>", on_thumbnail_click)  # 同时绑定到文本标签

        def on_thumbnail_click(event):
            if event.state & 0x4:
                if frame in self.selected_thumbnails:
                    self.selected_thumbnails.remove(frame)
                    frame.config(style='TFrame')
                else:
                    self.selected_thumbnails.append(frame)
                    frame.config(style='Selected.TFrame')
            else:
                if frame not in self.selected_thumbnails:
                    self.selected_thumbnails.clear()
                    self.selected_thumbnails.append(frame)
                    frame.config(style='Selected.TFrame')
                else:
                    self.selected_thumbnails.clear()
                    frame.config(style='TFrame')

        frame.bind("<Button-1>", on_thumbnail_click)

    def start_processing(self):
        if not self.validate_processing():
            return
        output_format = output_format_var.get()
        total_images = len(self.image_paths)

        thread = threading.Thread(target=self.process_images, args=(output_format, total_images))
        thread.start()

    def process_images(self, output_format, total_images):
        for i, image_path in enumerate(self.image_paths, start=1):
            self.process_single_image(image_path, output_format, i, total_images)
        self.reset_progress()
        if messagebox.askyesno("完成", "图片处理完成，是否打开输出目录？"):
            if os.name == 'nt':
                os.startfile(self.output_folder)
            else:
                subprocess.Popen(['open', self.output_folder] if os.name == 'posix' else ['xdg-open', self.output_folder])

    def validate_processing(self):
        if not self.image_paths:
            messagebox.showerror("错误", "请选择要处理的图片")
            return False
        if not self.output_folder:
            messagebox.showerror("错误", "请选择输出位置")
            return False
        return True

    def process_single_image(self, image_path, output_format, current, total):
        try:
            file_name = os.path.splitext(os.path.basename(image_path))[0]
            compression_quality = int(compression_scale.get())

            if output_format == "original":
                output_path = os.path.join(self.output_folder, os.path.basename(image_path))
            else:
                output_path = os.path.join(self.output_folder, f"{file_name}.{output_format}")

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
                with Image.open(image_path) as img:
                    if compression_quality < 100:
                        img.save(output_path, quality=compression_quality)
                    else:
                        img.save(output_path)

            self.update_progress(current, total)
        except Exception as e:
            messagebox.showerror("错误", f"处理图片 {image_path} 时出错: {str(e)}")

    def handle_file_conflict(self, file_path):
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

                ttk.Checkbutton(self, text="应用到所有文件", variable=self.apply_to_all).pack()

                btn_frame = ttk.Frame(self)
                btn_frame.pack(pady=10)

                ttk.Button(btn_frame, text="覆盖", command=lambda: self.set_result("overwrite")).pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame, text="跳过", command=lambda: self.set_result("skip")).pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame, text="取消", command=lambda: self.set_result("cancel")).pack(side=tk.LEFT, padx=5)

                self.transient(parent)
                self.grab_set()
                parent.wait_window(self)

            def set_result(self, value):
                self.result = (value, self.apply_to_all.get())
                self.destroy()

        if hasattr(self.handle_file_conflict, 'global_action'):
            return self.handle_file_conflict.global_action

        dialog = ConflictDialog(root)
        if dialog.result is None:
            return "cancel"

        action, apply_to_all = dialog.result

        if apply_to_all:
            self.handle_file_conflict.global_action = action

        return action

    def update_progress(self, current, total):
        progress = (current / total) * 100
        progress_bar["value"] = progress
        progress_label.config(text=f"{current}/{total} ({progress:.1f}%)")
        root.update_idletasks()

    def reset_progress(self):
        progress_bar["value"] = 0
        progress_label.config(text="0/0 (0.0%)")

    def select_output_folder(self):
        self.output_folder = filedialog.askdirectory()
        if self.output_folder:
            output_folder_label.config(text=f"输出位置: {self.output_folder}", wraplength=300)

    def delete_selected_image(self):
        if self.selected_thumbnails:
            for frame in self.selected_thumbnails:
                image_path = frame.image_path
                self.image_paths.remove(image_path)
                self.thumbnail_cache.pop(image_path, None)
                frame.destroy()
            self.selected_thumbnails.clear()
            self.show_thumbnails()
            image_count_label.config(text=f"已选择 {len(self.image_paths)} 张图片")

    def clear_all_images(self):
        self.image_paths = []
        self.show_thumbnails()
        image_count_label.config(text="未选择图片")

def create_tooltip(widget):
    def show_tooltip(event):
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

        label = ttk.Label(tooltip, text=widget.cget("text"), background="#ffffe0", relief="solid", borderwidth=1)
        label.pack()

        def hide_tooltip():
            tooltip.destroy()

        widget.tooltip = tooltip
        widget.bind('<Leave>', lambda e: hide_tooltip())
        tooltip.bind('<Leave>', lambda e: hide_tooltip())

    widget.bind('<Enter>', show_tooltip)

def update_compression_value(event):
    value = int(compression_scale.get())
    compression_value_label.config(text=f"{value}%")

root = ThemedTk(theme="yaru")
root.title("图片格式转换工具")
root.geometry("800x650")
root.minsize(600, 650)

style = ttk.Style()
style.configure('Selected.TFrame', background='#add8e6', borderwidth=2, relief='solid', bordercolor='#0000ff')
style.map('Selected.TFrame', background=[('selected', '#add8e6')], bordercolor=[('selected', '#0000ff')])

image_processor = ImageProcessor()

main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=tk.BOTH, expand=True)

control_frame = ttk.LabelFrame(main_frame, text="操作区", padding="5")
control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

file_frame = ttk.Frame(control_frame)
file_frame.pack(fill=tk.X, pady=(0, 10))
select_images_button = ttk.Button(file_frame, text="选择图片", command=image_processor.select_images)
select_images_button.pack(fill=tk.X, pady=2)

image_count_label = ttk.Label(file_frame, text="未选择图片")
image_count_label.pack(fill=tk.X, pady=2)

buttons_frame = ttk.Frame(control_frame)
buttons_frame.pack(fill=tk.X, pady=5)
delete_button = ttk.Button(buttons_frame, text="删除选中图片", command=image_processor.delete_selected_image)
delete_button.pack(fill=tk.X, pady=2)

clear_button = ttk.Button(buttons_frame, text="清除所有所选", command=image_processor.clear_all_images)
clear_button.pack(fill=tk.X, pady=2)

output_frame = ttk.LabelFrame(control_frame, text="输出选项", padding="5")
output_frame.pack(fill=tk.X, pady=10)

formats = ["original", "jpg", "heic", "heif", "webp", "jxl"]
output_format_var = tk.StringVar(value="heic")
for format in formats:
    ttk.Radiobutton(
        output_frame,
        text="原始格式" if format == "original" else format.upper(),
        variable=output_format_var,
        value=format
    ).pack(anchor=tk.W, pady=2)
select_output_folder_button = ttk.Button(output_frame, text="选择输出位置", command=image_processor.select_output_folder)
select_output_folder_button.pack(fill=tk.X, pady=5)

output_folder_label = ttk.Label(output_frame, text="未选择输出位置", anchor=tk.W, width=20)
output_folder_label.pack(fill=tk.X)

create_tooltip(output_folder_label)

compression_label = ttk.Label(output_frame, text="压缩质量 (100% 不压缩):")
compression_label.pack(fill=tk.X, pady=2)

compression_scale = ttk.Scale(output_frame, from_=25, to=100, orient=tk.HORIZONTAL)
compression_scale.set(100)
compression_scale.pack(side=tk.TOP, fill=tk.X, expand=True)

compression_value_label = ttk.Label(output_frame, text="100%")
compression_value_label.pack(side=tk.BOTTOM)

compression_scale.bind("<Motion>", update_compression_value)
compression_scale.bind("<ButtonRelease-1>", update_compression_value)

start_button = ttk.Button(control_frame, text="开始处理", command=image_processor.start_processing)
start_button.pack(fill=tk.X, pady=10)

progress_frame = ttk.Frame(control_frame)
progress_frame.pack(fill=tk.X, pady=5)
progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
progress_bar.pack(fill=tk.X)

progress_label = ttk.Label(progress_frame, text="0/0 (0.0%)")
progress_label.pack()

preview_frame = ttk.LabelFrame(main_frame, text="图片预览", padding="5")
preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

thumbnail_frame = ttk.Frame(preview_frame)
thumbnail_frame.pack(fill=tk.BOTH, expand=True)

root.mainloop()
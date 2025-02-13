import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from ttkthemes import ThemedTk
import math
from PIL import Image, ImageTk
import pillow_heif
import pillow_jxl
import os
import subprocess  # 用于跨平台打开目录
import shutil
import threading

pillow_heif.register_heif_opener()
thumbnail_cache = {}  # 全局变量用于缓存缩略图
# 全局变量用于存储选中的缩略图
selected_thumbnails = []

def select_images():
    global image_paths, image_info
    image_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.heic;*.heif;*.webp;*.jxl")])
    if image_paths:
        image_info = {path: os.path.getsize(path) for path in image_paths}  # 预加载文件大小
        image_count_label.config(text=f"已选择 {len(image_paths)} 张图片")
        show_thumbnails()

def show_thumbnails():
    for widget in thumbnail_frame.winfo_children():
        widget.destroy()

    if not image_paths:
        return

    thumbnail_size = 120
    padding = 10
    frame_width = thumbnail_frame.winfo_width() or 600
    columns = max(1, (frame_width - padding) // (thumbnail_size + padding))

    canvas = tk.Canvas(thumbnail_frame)
    scrollbar = ttk.Scrollbar(thumbnail_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    scrollable_frame.bind("<Configure>", on_configure)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    for index, image_path in enumerate(image_paths):
        create_thumbnail(scrollable_frame, image_path, index, columns, thumbnail_size, padding)

def create_thumbnail(parent, image_path, index, columns, thumbnail_size, padding):
    row = index // columns
    col = index % columns

    frame = ttk.Frame(parent)
    frame.grid(row=row, column=col, padx=padding, pady=padding)
    frame.image_path = image_path  # 将图片路径存储在 frame 的属性中
    # 先创建并显示文件名和大小标签
    file_name = os.path.basename(image_path)
    file_name = file_name[:12] + "..." if len(file_name) > 15 else file_name
    file_size = image_info[image_path]
    if file_size < 1024:
        size_str = f"{file_size} B"
    elif file_size < 1024 * 1024:
        size_str = f"{file_size / 1024:.1f} KB"
    else:
        size_str = f"{file_size / (1024 * 1024):.1f} MB"

    # 创建一个临时的占位标签
    thumbnail_label = ttk.Label(frame, text="加载中...", width=thumbnail_size//10)
    thumbnail_label.pack()
    
    text_label = ttk.Label(frame, text=f"{file_name} ({size_str})", wraplength=thumbnail_size)
    text_label.pack()

    # 使用线程异步加载缩略图
    def load_thumbnail():
        try:
            if image_path in thumbnail_cache:
                img_tk = thumbnail_cache[image_path]
            else:
                with Image.open(image_path) as img:
                    img.thumbnail((thumbnail_size, thumbnail_size))
                    img_tk = ImageTk.PhotoImage(img)
                    thumbnail_cache[image_path] = img_tk

            # 使用 after 方法在主线程中更新 UI
            def update_thumbnail():
                thumbnail_label.configure(image=img_tk, text="")
                thumbnail_label.image = img_tk
            
            root.after(0, update_thumbnail)
        except Exception:
            def show_error():
                thumbnail_label.configure(text="加载失败")
            root.after(0, show_error)

    threading.Thread(target=load_thumbnail, daemon=True).start()
     # 添加鼠标点击事件处理
    def on_thumbnail_click(event):
        if event.state & 0x4:  # 检查Ctrl键是否被按下
            if frame in selected_thumbnails:
                selected_thumbnails.remove(frame)
                frame.config(style='TFrame')  # 恢复默认样式
            else:
                selected_thumbnails.append(frame)
                frame.config(style='Selected.TFrame')  # 应用选中样式
        else:
            if frame not in selected_thumbnails:
                selected_thumbnails.clear()
                selected_thumbnails.append(frame)
                frame.config(style='Selected.TFrame')  # 应用选中样式
            else:
                selected_thumbnails.clear()
                frame.config(style='TFrame')  # 恢复默认样式

    frame.bind("<Button-1>", on_thumbnail_click)
def start_processing():
    if not validate_processing():
        return
    output_format = output_format_var.get()
    total_images = len(image_paths)

    # 使用多线程处理图片
    thread = threading.Thread(target=process_images, args=(output_format, total_images))
    thread.start()

def process_images(output_format, total_images):
    for i, image_path in enumerate(image_paths, start=1):
        process_single_image(image_path, output_format, i, total_images)
    reset_progress()
    # 合并提示信息和询问信息
    if messagebox.askyesno("完成", "图片处理完成，是否打开输出目录？"):
        if os.name == 'nt':  # Windows
            os.startfile(output_folder)
        else:  # macOS 或 Linux
            subprocess.Popen(['open', output_folder] if os.name == 'posix' else ['xdg-open', output_folder])

def validate_processing():
    if not image_paths:
        messagebox.showerror("错误", "请选择要处理的图片")
        return False
    if not output_folder:
        messagebox.showerror("错误", "请选择输出位置")
        return False
    return True

# 修改 process_single_image 函数，添加压缩逻辑
def process_single_image(image_path, output_format, current, total):
    try:
        file_name = os.path.splitext(os.path.basename(image_path))[0]
        compression_quality = int(compression_scale.get())

        if output_format == "original":
            output_path = os.path.join(output_folder, os.path.basename(image_path))
        else:
            output_path = os.path.join(output_folder, f"{file_name}.{output_format}")

        # 检查文件是否已存在
        if os.path.exists(output_path):
            action = handle_file_conflict(output_path)
            if action == "skip":
                update_progress(current, total)
                return
            elif action == "cancel":
                raise Exception("操作已取消")
            # action == "overwrite" 时继续执行

        if output_format == "original" and compression_quality == 100:
            shutil.copy2(image_path, output_path)
        else:
            with Image.open(image_path) as img:
                if compression_quality < 100:
                    img.save(output_path, quality=compression_quality)
                else:
                    img.save(output_path)

        update_progress(current, total)
    except Exception as e:
        messagebox.showerror("错误", f"处理图片 {image_path} 时出错: {str(e)}")

def handle_file_conflict(file_path):
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

    # 如果已经有全局决定，直接返回
    if hasattr(handle_file_conflict, 'global_action'):
        return handle_file_conflict.global_action

    # 显示对话框
    dialog = ConflictDialog(root)
    if dialog.result is None:
        return "cancel"
    
    action, apply_to_all = dialog.result
    
    # 如果选择了"应用到所有文件"，保存全局决定
    if apply_to_all:
        handle_file_conflict.global_action = action
    
    return action

def update_progress(current, total):
    progress = (current / total) * 100
    progress_bar["value"] = progress
    progress_label.config(text=f"{current}/{total} ({progress:.1f}%)")
    root.update_idletasks()

def reset_progress():
    progress_bar["value"] = 0
    progress_label.config(text="0/0 (0.0%)")

def select_output_folder():
    global output_folder
    output_folder = filedialog.askdirectory()
    if output_folder:
        output_folder_label.config(text=f"输出位置: {output_folder}", wraplength=300)  # 设置 wraplength 控制换行

def delete_selected_image():
    global selected_thumbnails
    if selected_thumbnails:
        for frame in selected_thumbnails:
            # 获取图片路径
            image_path = frame.image_path  # 假设你在创建缩略图时将图片路径存储在frame的属性中
            image_paths.remove(image_path)
            thumbnail_cache.pop(image_path, None)
            frame.destroy()
        selected_thumbnails.clear()
        show_thumbnails()
        image_count_label.config(text=f"已选择 {len(image_paths)} 张图片")

def clear_all_images():
    global image_paths
    image_paths = []
    show_thumbnails()
    image_count_label.config(text="未选择图片")

image_paths = []
output_folder = ""

# root = tk.Tk()
root=ThemedTk(theme="yaru")  # 使用 ttkthemes 库设置主题
root.title("图片格式转换工具")
root.geometry("800x650")
root.minsize(600, 650)

# 在主程序中定义选中样式
style = ttk.Style()
style.configure('Selected.TFrame', background='blue')  # 选中时的背景颜色


main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=tk.BOTH, expand=True)

control_frame = ttk.LabelFrame(main_frame, text="操作区", padding="5")
control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

file_frame = ttk.Frame(control_frame)
file_frame.pack(fill=tk.X, pady=(0, 10))
select_images_button = ttk.Button(file_frame, text="选择图片", command=select_images)
select_images_button.pack(fill=tk.X, pady=2)

image_count_label = ttk.Label(file_frame, text="未选择图片")
image_count_label.pack(fill=tk.X, pady=2)

buttons_frame = ttk.Frame(control_frame)
buttons_frame.pack(fill=tk.X, pady=5)
delete_button = ttk.Button(buttons_frame, text="删除选中图片", command=delete_selected_image)
delete_button.pack(fill=tk.X, pady=2)

clear_button = ttk.Button(buttons_frame, text="清除所有所选", command=clear_all_images)
clear_button.pack(fill=tk.X, pady=2)

output_frame = ttk.LabelFrame(control_frame, text="输出选项", padding="5")
output_frame.pack(fill=tk.X, pady=10)

formats = ["original", "jpg", "heic","heif", "webp", "jxl"]
output_format_var = tk.StringVar(value="heic")
for format in formats:
    ttk.Radiobutton(
        output_frame,
        text="原始格式" if format == "original" else format.upper(),
        variable=output_format_var,
        value=format
    ).pack(anchor=tk.W, pady=2)
select_output_folder_button = ttk.Button(output_frame, text="选择输出位置", command=select_output_folder)
select_output_folder_button.pack(fill=tk.X, pady=5)

output_folder_label = ttk.Label(output_frame, text="未选择输出位置", anchor=tk.W, width=20)  # 设置 wraplength 控制换行
output_folder_label.pack(fill=tk.X)

# 创建工具提示
def create_tooltip(widget):
    def show_tooltip(event):
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)  # 移除窗口边框
        tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

        label = ttk.Label(tooltip, text=widget.cget("text"), background="#ffffe0", relief="solid", borderwidth=1)
        label.pack()

        def hide_tooltip():
            tooltip.destroy()

        widget.tooltip = tooltip
        widget.bind('<Leave>', lambda e: hide_tooltip())
        tooltip.bind('<Leave>', lambda e: hide_tooltip())

    widget.bind('<Enter>', show_tooltip)

create_tooltip(output_folder_label)

# 在 output_frame 中添加滑块控件
compression_label = ttk.Label(output_frame, text="压缩质量 (100% 不压缩):")
compression_label.pack(fill=tk.X, pady=2)

# 添加滑块
compression_scale = ttk.Scale(output_frame, from_=25, to=100, orient=tk.HORIZONTAL)
compression_scale.set(100)  # 默认设置为100% (不压缩)
compression_scale.pack(side=tk.TOP, fill=tk.X, expand=True)  # 滑块占据整个宽度

# 添加百分比值标签，放在滑块的下方
compression_value_label = ttk.Label(output_frame, text="100%")
compression_value_label.pack(side=tk.BOTTOM)  # 放在滑块的下方

# 定义一个函数用于更新滑块值的显示
def update_compression_value(event):
    value = int(compression_scale.get())
    compression_value_label.config(text=f"{value}%")

# 绑定滑块的滑动事件
compression_scale.bind("<Motion>", update_compression_value)
compression_scale.bind("<ButtonRelease-1>", update_compression_value)

start_button = ttk.Button(control_frame, text="开始处理", command=start_processing)
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
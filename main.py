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

    try:
        # 检查缓存中是否已有缩略图
        if image_path in thumbnail_cache:
            img_tk = thumbnail_cache[image_path]
        else:
            with Image.open(image_path) as img:
                img.thumbnail((thumbnail_size, thumbnail_size))
                img_tk = ImageTk.PhotoImage(img)
                thumbnail_cache[image_path] = img_tk  # 缓存缩略图

        thumbnail_label = ttk.Label(frame, image=img_tk)
        thumbnail_label.image = img_tk
        thumbnail_label.pack()

        # 获取文件大小并格式化
        file_size = image_info[image_path]  # 使用预加载的文件大小
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"

        file_name = os.path.basename(image_path)
        file_name = file_name[:12] + "..." if len(file_name) > 15 else file_name
        ttk.Label(frame, text=f"{file_name} ({size_str})", wraplength=thumbnail_size).pack()
    except Exception:
        ttk.Label(frame, text="加载失败").pack()

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
    messagebox.showinfo("完成", "图片处理完成")
    reset_progress()
    # 弹出提示框，询问是否打开输出目录
    if messagebox.askyesno("打开目录", "图片处理完成，是否打开输出目录？"):
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
        compression_quality = int(compression_scale.get())  # 获取滑块的值

        if output_format == "original":
            output_path = os.path.join(output_folder, os.path.basename(image_path))
            shutil.copy2(image_path, output_path)
        else:
            with Image.open(image_path) as img:
                output_path = os.path.join(output_folder, f"{file_name}.{output_format}")
                if compression_quality < 100:  # 如果压缩质量小于100%，则进行压缩
                    img.save(output_path, quality=compression_quality)
                else:
                    img.save(output_path)  # 否则不压缩

        update_progress(current, total)
    except Exception as e:
        messagebox.showerror("错误", f"处理图片 {image_path} 时出错: {str(e)}")

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
    if image_paths:
        image_paths.pop()
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
root=ThemedTk(theme="arc")  # 使用 ttkthemes 库设置主题
root.title("图片格式转换工具")
root.geometry("800x650")
root.minsize(600, 500)

# style = ttk.Style()
# style.theme_use("xpnative")

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

formats = ["original", "jpg", "heic", "webp", "png", "jxl"]
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

# 在 output_frame 中添加滑块控件
compression_label = ttk.Label(output_frame, text="压缩质量 (100% 不压缩):")
compression_label.pack(fill=tk.X, pady=2)

# 创建一个框架用于放置滑块和百分比值
compression_row_frame = ttk.Frame(output_frame)
compression_row_frame.pack(fill=tk.X, pady=5)

# 添加滑块到框架中
compression_scale = ttk.Scale(compression_row_frame, from_=25, to=100, orient=tk.HORIZONTAL)
compression_scale.set(100)  # 默认设置为100% (不压缩)
compression_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)  # 滑块靠左，填充剩余空间

# 添加百分比值标签到框架中，放在滑块的右侧
compression_value_label = ttk.Label(compression_row_frame, text="100%")
compression_value_label.pack(side=tk.RIGHT, padx=(10, 0))  # 标签靠右，并添加一些左边距

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
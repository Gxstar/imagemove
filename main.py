import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image
import pillow_heif
import pillow_jxl
import os

# 注册HEIF和JXL插件
pillow_heif.register_heif_opener()

def select_images():
    global image_paths
    image_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.heic;*.heif;*.webp;*.jxl")])
    if image_paths:
        image_count_label.config(text=f"已选择 {len(image_paths)} 张图片")

def select_output_folder():
    global output_folder
    output_folder = filedialog.askdirectory()
    if output_folder:
        output_folder_label.config(text=f"输出位置: {output_folder}")

def start_processing():
    if not image_paths:
        messagebox.showerror("错误", "请选择要处理的图片")
        return
    if not output_folder:
        messagebox.showerror("错误", "请选择输出位置")
        return

    output_format = output_format_var.get()
    total_images = len(image_paths)

    for i, image_path in enumerate(image_paths, start=1):
        try:
            img = Image.open(image_path)
            file_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = os.path.join(output_folder, f"{file_name}.{output_format}")
            img.save(output_path)

            # 更新进度条
            progress = (i / total_images) * 100
            progress_bar["value"] = progress
            progress_label.config(text=f"{i}/{total_images} ({progress:.2f}%)")
            root.update_idletasks()
        except Exception as e:
            messagebox.showerror("错误", f"处理图片 {image_path} 时出错: {str(e)}")

    messagebox.showinfo("完成", "图片处理完成")

# 初始化全局变量
image_paths = []
output_folder = ""

# 创建主窗口
root = tk.Tk()
root.title("图片格式转换工具")

# 选择图片按钮
select_images_button = tk.Button(root, text="选择图片", command=select_images)
select_images_button.pack(pady=10)

# 显示已选择图片数量
image_count_label = tk.Label(root, text="未选择图片")
image_count_label.pack(pady=5)

# 选择输出格式
output_format_var = tk.StringVar(root)
output_format_var.set("jpg")  # 默认输出格式为JPG
output_format_menu = tk.OptionMenu(root, output_format_var, "jpg", "heic", "webp", "png", "jxl")
output_format_menu.pack(pady=10)

# 选择输出位置按钮
select_output_folder_button = tk.Button(root, text="选择输出位置", command=select_output_folder)
select_output_folder_button.pack(pady=10)

# 显示输出位置
output_folder_label = tk.Label(root, text="未选择输出位置")
output_folder_label.pack(pady=5)

# 开始处理按钮
start_button = tk.Button(root, text="开始处理", command=start_processing)
start_button.pack(pady=20)

# 进度条
progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.pack(pady=10)

# 进度标签
progress_label = tk.Label(root, text="0/0 (0.00%)")
progress_label.pack(pady=5)

# 运行主循环
root.mainloop()
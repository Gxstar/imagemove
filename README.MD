# 图像格式转换工具

## 项目简介

本工具是一款基于Python的GUI图像处理软件，支持批量图片格式转换和压缩处理。提供直观的缩略图预览界面，支持多种主流图片格式（JPG/PNG/WEBP/HEIC/JXL等），具备智能缓存机制和多线程处理能力。

## 功能特性

- 支持格式转换：JPG/PNG/WEBP/HEIC/JXL/保持原格式
- 可视化压缩质量调节（25%-100%）
- 响应式缩略图预览界面（自动适应窗口大小）
- 多线程处理技术提升转换效率
- 智能缓存机制加速重复加载
- 实时进度显示和完成提醒
- 原生支持Windows/macOS/Linux系统

## 运行环境要求

### 系统要求

- Windows 7+/macOS 10.12+/Linux（需GUI环境）
- Python 3.8+

### 安装依赖库

```bash
### 打包命令

nuitka --standalone --follow-imports --enable-plugin=tk-inter --include-module=PIL --include-package-data=ttkthemes --include-package=ttkthemes --windows-console-mode=disable --onefile --output-dir=out --output-filename=imagemove --remove-output main.py

### 依赖库

pip install pillow ttkthemes pillow_heif


# YT-DLP Custom UI (MP4 Video Downloader)

A lightweight, portable Windows desktop GUI built with **CustomTkinter** that wraps `yt-dlp` and `ffmpeg` to fetch video metadata, download streams, and convert/remux them into `.mp4` files with live progress tracking and local library management.

> [!IMPORTANT]
> **Required External Executables (`yt-dlp.exe` & FFmpeg Essentials)**
> This app does **not** bundle `yt-dlp.exe` or `ffmpeg.exe` inside the repository or `.exe`. Before running the app, make sure **`yt-dlp.exe`** and all **FFmpeg essentials executables** (`ffmpeg.exe`, `ffprobe.exe`, and `ffplay.exe` from the `bin/` folder of the FFmpeg essentials package) are placed **in the exact same folder** as `ytdlp_cutom_ui.exe` (or `yt-dlp_custom_ui.py`), **or** added to your Windows system `PATH`. Without `ffmpeg.exe`, merging high-resolution video/audio streams and converting to `.mp4` will fail.

---

## Table of Contents

- [Features](#features)
- [Step-by-Step Setup Guide](#step-by-step-setup-guide)
- [Where to Download Required Files](#where-to-download-required-files)
- [Folder Setup (Portable Mode)](#folder-setup-portable-mode)
- [Project Structure](#project-structure)
- [Acknowledgements & Citations](#acknowledgements--citations)
- [Disclaimer](#disclaimer)

---

## Features

- **Automatic Metadata Preview:** Validates video URLs and automatically fetches the video title, resolution, duration, and estimated file size before downloading.
- **Custom Output Folder & Naming:** Pick a destination folder with a built-in folder validation warning, and optionally rename the output file before saving.
- **Duplicate File Protection:** Prompts for confirmation before overwriting an existing `.mp4` file with the same name.
- **Live Download Progress:** Smooth progress bar with real-time percentage, download speed, downloaded/total size, estimated remaining time, FFmpeg merging status, and elapsed timer.
- **Local MP4 Library Tab:** View all `.mp4` files in your selected folder along with total file count and combined storage size.
- **Dark & Light Themes:** Toggle between Dark and Light modes directly from the top bar.
- **Portable Binary Detection:** Automatically locates `yt-dlp.exe` and `ffmpeg.exe` in the application folder first, then falls back to your system `PATH`.

---

## Step-by-Step Setup Guide

1. **Download the `.exe`:** [Download ytdlp_cutom_ui.exe from GitHub Releases](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/releases/latest) and save it into a dedicated folder (for example, `YT-DLP Custom UI`).
2. **Download `yt-dlp`:** Visit [yt-dlp Official GitHub Releases](https://github.com/yt-dlp/yt-dlp/releases) and download **`yt-dlp.exe`** from the latest release assets.
3. **Download FFmpeg:** Visit [gyan.dev FFmpeg Builds](https://www.gyan.dev/ffmpeg/builds/) (linked via [FFmpeg Official Downloads](https://ffmpeg.org/download.html)) and download the **essentials** build (`ffmpeg-release-essentials.zip` or `ffmpeg-release-essentials.7z`).
4. **Extract and place all files in the same folder:** Extract the FFmpeg archive, open its **`bin/`** folder, and move **`ffmpeg.exe`**, **`ffprobe.exe`**, and **`ffplay.exe`**—along with **`yt-dlp.exe`**—into the same folder as **`ytdlp_cutom_ui.exe`** (or add them to your Windows `PATH`).
5. **Launch and download:** Double-click **`ytdlp_cutom_ui.exe`**, choose your output folder, paste a valid video URL to preview metadata, and click **Download MP4**.

---

## Where to Download Required Files

Download these required files before running the application:

1. **Application Executable (`ytdlp_cutom_ui.exe`)**
   - **Download Link:** [Download ytdlp_cutom_ui.exe (Latest Release)](https://github.com/wijayawilly/yt-dlp-desktop-gui/releases/latest) *(or direct asset link once tagged: `https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/releases/download/v1.0.0/ytdlp_cutom_ui.exe`)*

2. **`yt-dlp` (`yt-dlp.exe`)**
   - **Download Link:** [yt-dlp Official GitHub Releases](https://github.com/yt-dlp/yt-dlp/releases)
   - **Instructions:** Scroll to the **Assets** section of the latest release, download **`yt-dlp.exe`**, and place it in the same folder as this application (or in a folder on your Windows `PATH`).

3. **FFmpeg Essentials (`ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe`)**
   - **Official FFmpeg Website:** [FFmpeg Official Downloads](https://ffmpeg.org/download.html)
   - **Windows Essentials Builds (Gyan Doshi / CODEX FFMPEG):** [gyan.dev FFmpeg Builds](https://www.gyan.dev/ffmpeg/builds/)
   - **Instructions:** Download **`ffmpeg-release-essentials.zip`** (or `.7z`), extract the archive, open the **`bin/`** subfolder, and copy **`ffmpeg.exe`**, **`ffprobe.exe`**, and **`ffplay.exe`** into the same folder as `ytdlp_cutom_ui.exe` (or add that `bin/` folder to your Windows `PATH`).

---

## Folder Setup (Portable Mode)

Your application folder should look like this when running in portable mode:

```text
Your_App_Folder/
├── ytdlp_cutom_ui.exe    # Standalone Windows GUI executable (from GitHub Releases)
├── yt-dlp.exe            # Required: downloaded from yt-dlp releases
├── ffmpeg.exe            # Required: extracted from FFmpeg essentials bin/
├── ffprobe.exe           # Essential FFmpeg media analyzer (from FFmpeg essentials bin/)
└── ffplay.exe            # Essential FFmpeg media player (from FFmpeg essentials bin/)
```

---

## Project Structure

```text
Custom_UI_YTDLP/
├── yt-dlp_custom_ui.py   # Main GUI application source code
├── icon.ico              # Custom application & window icon
├── .gitignore            # Excludes build/dist/cache folders from Git
└── README.md             # Project documentation
```

---

## Acknowledgements & Citations

Full credit and respect go to the open-source developers and maintainers whose tools make this project possible:

- **yt-dlp Contributors** — *yt-dlp: A feature-rich command-line audio/video downloader.*  
  Repository & Releases: [https://github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **FFmpeg Developers** — *FFmpeg: A complete, cross-platform solution to record, convert and stream audio and video.*  
  Official Project: [https://ffmpeg.org/](https://ffmpeg.org/)
- **Gyan Doshi (CODEX FFMPEG)** — *Windows Release & Essentials Builds for FFmpeg.*  
  Builds Page: [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
- **Tom Schimansky** — *CustomTkinter: A modern and customizable Python UI-library based on Tkinter.*  
  Repository: [https://github.com/TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)

---

## Disclaimer

This application is intended solely for downloading content you own or have explicit permission to save (such as personal videos, Creative Commons works, or public domain media). Please respect copyright laws and the terms of service of any website you use.

# YT-DLP Custom UI (MP4 Video Downloader)

A lightweight, portable Windows desktop GUI built with **CustomTkinter** that wraps `yt-dlp` and `ffmpeg` to fetch video metadata, download streams, and convert/remux them into `.mp4` files with live progress tracking and local library management[cite: 7].

> [!IMPORTANT]
> **Required External Executables (`yt-dlp.exe` & FFmpeg Essentials)**
> This app does **not** bundle `yt-dlp.exe` or `ffmpeg.exe` inside the repository or `.exe`. Before running the app, make sure **`yt-dlp.exe`** and all **FFmpeg essentials executables** (`ffmpeg.exe`, `ffprobe.exe`, and `ffplay.exe` from the `bin/` folder of the FFmpeg essentials package) are placed **in the exact same folder** as `ytdlp_cutom_ui.exe` (or `yt-dlp_custom_ui.py`), **or** added to your Windows system `PATH`. Without `ffmpeg.exe`, merging high-resolution video/audio streams and converting to `.mp4` will fail.

---

## Table of Contents

- [Features](#features)
- [Where to Download Required Files](#where-to-download-required-files)
- [Folder Setup (Portable Mode)](#folder-setup-portable-mode)
- [Quick Start for `.exe` Users (GitHub Releases)](#quick-start-for-exe-users-github-releases)
- [Running from Python Source](#running-from-python-source)
- [Building the Standalone `.exe`](#building-the-standalone-exe)
- [Project Structure](#project-structure)
- [Acknowledgements & Citations](#acknowledgements--citations)
- [Disclaimer](#disclaimer)

---

## Features

- **Automatic Metadata Preview:** Validates video URLs and automatically fetches the video title, resolution, duration, and estimated file size before downloading[cite: 7].
- **Custom Output Folder & Naming:** Pick a destination folder with a built-in folder validation warning, and optionally rename the output file before saving[cite: 7].
- **Duplicate File Protection:** Prompts for confirmation before overwriting an existing `.mp4` file with the same name.
- **Live Download Progress:** Smooth progress bar with real-time percentage, download speed, downloaded/total size, estimated remaining time, FFmpeg merging status, and elapsed timer[cite: 7].
- **Local MP4 Library Tab:** View all `.mp4` files in your selected folder along with total file count and combined storage size[cite: 7].
- **Dark & Light Themes:** Toggle between Dark and Light modes from the top bar[cite: 7].
- **Portable Binary Detection:** Automatically locates `yt-dlp.exe` and `ffmpeg.exe` in the application folder first, then falls back to your system `PATH`[cite: 7].

---

## Where to Download Required Files

Download these official upstream tools before running the application:

1. **`yt-dlp` (`yt-dlp.exe`)**
   - **Download Link:** [yt-dlp Official GitHub Releases](https://github.com/yt-dlp/yt-dlp/releases)
   - **Instructions:** Scroll to the **Assets** section of the latest release, download **`yt-dlp.exe`**, and place it in the same folder as this application (or in a folder on your Windows `PATH`).

2. **FFmpeg Essentials (`ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe`)**
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

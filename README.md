# YT-DLP Custom UI (MP4 Video Downloader)

A lightweight, portable Windows desktop GUI built with **CustomTkinter** that wraps `yt-dlp` and `ffmpeg` to download and convert online videos directly into `.mp4` files.

## Features

- **Automatic Metadata Preview:** Validates video URLs and automatically fetches the video title, resolution, duration, and estimated file size before downloading.
- **Custom Output Folder & Naming:** Pick a destination folder with a built-in folder validation warning, and optionally rename the output file before saving.
- **Live Download Progress:** Smooth progress bar with real-time percentage, download speed, downloaded size, estimated remaining time, and elapsed timer.
- **Local MP4 Library Tab:** View all `.mp4` files in your selected folder along with total file count and combined storage size.
- **Dark & Light Themes:** Toggle between Dark and Light modes from the top bar.
- **Portable Binary Detection:** Automatically locates `yt-dlp.exe` and `ffmpeg.exe` in the application folder or your system `PATH`.

## Project Structure

```text
Custom_UI_YTDLP/
├── yt-dlp_custom_ui.py   # Main GUI application source code
├── icon.ico              # Custom application & window icon
├── .gitignore            # Excludes build/dist/cache folders from Git
└── README.md             # Project documentation
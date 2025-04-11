import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import subprocess
import os
import sys
import re
from urllib.parse import urlparse, parse_qs

class YouTubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Downloader")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        # Set theme colors
        self.bg_color = "#f0f0f0"
        self.accent_color = "#ff0000"  # YouTube red
        self.text_color = "#333333"
        
        self.root.configure(bg=self.bg_color)
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL input
        ttk.Label(self.main_frame, text="YouTube URL(s):", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        self.url_frame = ttk.Frame(self.main_frame)
        self.url_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        
        self.url_input = scrolledtext.ScrolledText(self.url_frame, height=5, wrap=tk.WORD)
        self.url_input.pack(fill=tk.BOTH, expand=True)
        self.url_input.bind("<Control-v>", self.paste_clipboard)
        
        # Output directory selection
        self.dir_frame = ttk.Frame(self.main_frame)
        self.dir_frame.pack(fill=tk.X, expand=False, pady=(0, 10))
        
        ttk.Label(self.dir_frame, text="Save to:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        
        self.output_dir = tk.StringVar()
        self.output_dir.set(os.path.join(os.path.expanduser("~"), "Downloads"))
        
        self.dir_entry = ttk.Entry(self.dir_frame, textvariable=self.output_dir, width=50)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.browse_btn = ttk.Button(self.dir_frame, text="Browse", command=self.browse_output_dir)
        self.browse_btn.pack(side=tk.RIGHT)
        
        # Quality selection
        self.quality_frame = ttk.Frame(self.main_frame)
        self.quality_frame.pack(fill=tk.X, expand=False, pady=(0, 10))
        
        ttk.Label(self.quality_frame, text="Quality:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        
        self.quality = tk.StringVar()
        quality_options = [
            "Best Quality (Video+Audio)",
            "1080p Max",
            "720p Max",
            "480p Max",
            "Audio Only (Best)",
            "Custom Format"
        ]
        self.quality.set(quality_options[0])
        
        self.quality_menu = ttk.Combobox(self.quality_frame, textvariable=self.quality, values=quality_options, state="readonly", width=25)
        self.quality_menu.pack(side=tk.LEFT, padx=(0, 5))
        self.quality_menu.bind("<<ComboboxSelected>>", self.toggle_custom_format)
        
        self.custom_format = tk.StringVar()
        self.custom_format.set("bestvideo+bestaudio/best")
        self.custom_format_entry = ttk.Entry(self.quality_frame, textvariable=self.custom_format, width=30)
        self.custom_format_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.custom_format_entry.config(state=tk.DISABLED)
        
        # Download button
        self.download_btn = ttk.Button(self.main_frame, text="Download", command=self.start_download)
        self.download_btn.pack(fill=tk.X, pady=(0, 10))
        
        # Progress area
        ttk.Label(self.main_frame, text="Progress:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        self.progress_frame = ttk.Frame(self.main_frame)
        self.progress_frame.pack(fill=tk.BOTH, expand=True)
        
        self.progress_text = scrolledtext.ScrolledText(self.progress_frame, wrap=tk.WORD, height=10)
        self.progress_text.pack(fill=tk.BOTH, expand=True)
        self.progress_text.config(state=tk.DISABLED)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Check for dependencies
        self.check_dependencies()

    def check_dependencies(self):
        """Check if required dependencies are installed."""
        self.log_message("Checking dependencies...")
        
        # Check for yt-dlp
        try:
            subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, check=True)
            self.log_message("yt-dlp is installed.")
        except (subprocess.SubprocessError, FileNotFoundError):
            self.log_message("ERROR: yt-dlp is not installed or not in PATH.")
            self.log_message("Install it with: pip install yt-dlp")
            self.status_var.set("Error: yt-dlp not found")
        
        # Check for FFmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
            self.log_message("FFmpeg is installed.")
        except (subprocess.SubprocessError, FileNotFoundError):
            self.log_message("WARNING: FFmpeg is not installed or not in PATH.")
            self.log_message("Some features may not work correctly.")
            self.status_var.set("Warning: FFmpeg not found")

    def paste_clipboard(self, event=None):
        """Handle pasting from clipboard and attempt to clean/parse URLs."""
        clipboard = self.root.clipboard_get()
        
        # Try to extract YouTube URLs from clipboard text
        urls = self.extract_youtube_urls(clipboard)
        
        if urls:
            current_text = self.url_input.get("1.0", tk.END).strip()
            if current_text:
                # Append to existing URLs
                self.url_input.insert(tk.END, "\n" + "\n".join(urls))
            else:
                # Set as new content
                self.url_input.delete("1.0", tk.END)
                self.url_input.insert("1.0", "\n".join(urls))
            
            self.status_var.set(f"Added {len(urls)} YouTube URLs")
        else:
            # Just do a normal paste if no URLs detected
            return

    def extract_youtube_urls(self, text):
        """Extract and clean YouTube URLs from text."""
        # Regular expression for YouTube URLs
        youtube_regex = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+'
        
        # Find all matches
        matches = re.findall(youtube_regex, text)
        
        if not matches:
            return []
        
        # Reconstruct and clean URLs
        urls = []
        for match in re.finditer(youtube_regex, text):
            url = match.group(0)
            
            # Ensure it has https:// prefix
            if not url.startswith('http'):
                url = 'https://' + url
                
            # Parse URL to extract video ID and rebuild clean URL
            parsed_url = urlparse(url)
            if 'youtube.com' in parsed_url.netloc:
                query_params = parse_qs(parsed_url.query)
                if 'v' in query_params:
                    video_id = query_params['v'][0]
                    clean_url = f'https://www.youtube.com/watch?v={video_id}'
                    urls.append(clean_url)
            elif 'youtu.be' in parsed_url.netloc:
                video_id = parsed_url.path.lstrip('/')
                clean_url = f'https://www.youtube.com/watch?v={video_id}'
                urls.append(clean_url)
                
        return urls

    def browse_output_dir(self):
        """Open directory browser dialog."""
        directory = filedialog.askdirectory(initialdir=self.output_dir.get())
        if directory:
            self.output_dir.set(directory)

    def toggle_custom_format(self, event=None):
        """Enable/disable custom format entry based on selection."""
        if self.quality.get() == "Custom Format":
            self.custom_format_entry.config(state=tk.NORMAL)
        else:
            self.custom_format_entry.config(state=tk.DISABLED)

    def get_format_string(self):
        """Get the yt-dlp format string based on quality selection."""
        quality = self.quality.get()
        
        if quality == "Best Quality (Video+Audio)":
            return "bestvideo+bestaudio/best"
        elif quality == "1080p Max":
            return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        elif quality == "720p Max":
            return "bestvideo[height<=720]+bestaudio/best[height<=720]"
        elif quality == "480p Max":
            return "bestvideo[height<=480]+bestaudio/best[height<=480]"
        elif quality == "Audio Only (Best)":
            return "bestaudio/best"
        elif quality == "Custom Format":
            return self.custom_format.get()
        
        # Default
        return "bestvideo+bestaudio/best"

    def log_message(self, message):
        """Add message to log window."""
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END)
        self.progress_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def download_video(self, url, output_dir, format_string):
        """Download a single video using yt-dlp."""
        try:
            self.log_message(f"Processing: {url}")
            
            # Build the command
            cmd = [
                "yt-dlp",
                "-f", format_string,
                "-o", os.path.join(output_dir, "%(title)s.%(ext)s"),
                "--no-mtime",
                url
            ]
            
            # Run the command and capture output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream output to log
            for line in process.stdout:
                self.log_message(line.strip())
            
            process.wait()
            
            if process.returncode == 0:
                self.log_message(f"Successfully downloaded: {url}")
                return True
            else:
                self.log_message(f"Error downloading: {url}")
                return False
                
        except Exception as e:
            self.log_message(f"Error: {e}")
            return False

    def start_download(self):
        """Start the download process in a separate thread."""
        urls = self.url_input.get("1.0", tk.END).strip().split("\n")
        urls = [url for url in urls if url.strip()]
        
        if not urls:
            self.status_var.set("No URLs provided")
            self.log_message("Please enter at least one YouTube URL")
            return
            
        output_dir = self.output_dir.get()
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                self.status_var.set("Invalid output directory")
                self.log_message(f"Error creating output directory: {e}")
                return
                
        format_string = self.get_format_string()
        
        # Disable UI during download
        self.download_btn.config(state=tk.DISABLED)
        self.status_var.set("Downloading...")
        
        # Create and start download thread
        download_thread = threading.Thread(
            target=self.download_thread,
            args=(urls, output_dir, format_string)
        )
        download_thread.daemon = True
        download_thread.start()

    def download_thread(self, urls, output_dir, format_string):
        """Thread function to handle downloads."""
        total = len(urls)
        successful = 0
        
        self.log_message(f"Starting download of {total} videos to {output_dir}")
        self.log_message(f"Using format: {format_string}")
        
        for i, url in enumerate(urls, 1):
            self.status_var.set(f"Downloading {i}/{total}: {url}")
            if self.download_video(url, output_dir, format_string):
                successful += 1
                
        # Re-enable UI
        self.download_btn.config(state=tk.NORMAL)
        self.status_var.set(f"Completed: {successful}/{total} downloads successful")
        self.log_message(f"Download process completed. {successful}/{total} videos downloaded successfully.")

def main():
    root = tk.Tk()
    app = YouTubeDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
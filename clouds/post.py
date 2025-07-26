#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import tempfile
import shutil
import ffmpeg
from pathlib import Path

class DreamStyleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dream Style Video Processor")
        self.root.geometry("700x800")
        self.root.configure(bg='#f0f0f0')
        
        # Variables
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.brightness = tk.DoubleVar(value=0.2)
        self.vibrance = tk.DoubleVar(value=2.0)
        self.denoise = tk.IntVar(value=300)
        self.bilateral = tk.IntVar(value=100)
        self.noise = tk.IntVar(value=40)
        self.processing = False
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Dream Style Video Processor", 
                               font=('Arial', 20, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Input file
        ttk.Label(file_frame, text="Input Video:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        input_frame = ttk.Frame(file_frame)
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_file, width=50)
        self.input_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(input_frame, text="Browse", 
                  command=self.browse_input_file).grid(row=0, column=1)
        
        # Output file
        ttk.Label(file_frame, text="Output Video:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        output_frame = ttk.Frame(file_frame)
        output_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_file, width=50)
        self.output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(output_frame, text="Browse", 
                  command=self.browse_output_file).grid(row=0, column=1)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Dream Style Settings", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        settings_frame.columnconfigure(1, weight=1)
        
        # Brightness
        ttk.Label(settings_frame, text="Brightness:").grid(row=0, column=0, sticky=tk.W, pady=5)
        brightness_scale = ttk.Scale(settings_frame, from_=-0.5, to=0.5, 
                                   variable=self.brightness, orient=tk.HORIZONTAL)
        brightness_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        self.brightness_label = ttk.Label(settings_frame, text="0.2")
        self.brightness_label.grid(row=0, column=2, pady=5)
        brightness_scale.configure(command=self.update_brightness_label)
        
        # Vibrance
        ttk.Label(settings_frame, text="Vibrance:").grid(row=1, column=0, sticky=tk.W, pady=5)
        vibrance_scale = ttk.Scale(settings_frame, from_=0, to=5, 
                                 variable=self.vibrance, orient=tk.HORIZONTAL)
        vibrance_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        self.vibrance_label = ttk.Label(settings_frame, text="2.0")
        self.vibrance_label.grid(row=1, column=2, pady=5)
        vibrance_scale.configure(command=self.update_vibrance_label)
        
        # Denoise
        ttk.Label(settings_frame, text="Denoise:").grid(row=2, column=0, sticky=tk.W, pady=5)
        denoise_scale = ttk.Scale(settings_frame, from_=100, to=500, 
                                variable=self.denoise, orient=tk.HORIZONTAL)
        denoise_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        self.denoise_label = ttk.Label(settings_frame, text="300")
        self.denoise_label.grid(row=2, column=2, pady=5)
        denoise_scale.configure(command=self.update_denoise_label)
        
        # Bilateral
        ttk.Label(settings_frame, text="Bilateral:").grid(row=3, column=0, sticky=tk.W, pady=5)
        bilateral_scale = ttk.Scale(settings_frame, from_=50, to=200, 
                                  variable=self.bilateral, orient=tk.HORIZONTAL)
        bilateral_scale.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        self.bilateral_label = ttk.Label(settings_frame, text="100")
        self.bilateral_label.grid(row=3, column=2, pady=5)
        bilateral_scale.configure(command=self.update_bilateral_label)
        
        # Noise
        ttk.Label(settings_frame, text="Noise:").grid(row=4, column=0, sticky=tk.W, pady=5)
        noise_scale = ttk.Scale(settings_frame, from_=10, to=80, 
                              variable=self.noise, orient=tk.HORIZONTAL)
        noise_scale.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        self.noise_label = ttk.Label(settings_frame, text="40")
        self.noise_label.grid(row=4, column=2, pady=5)
        noise_scale.configure(command=self.update_noise_label)
        
        # Preset buttons
        preset_frame = ttk.Frame(settings_frame)
        preset_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Button(preset_frame, text="Dream Recorder Default", 
                  command=self.load_dream_preset).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(preset_frame, text="Soft Dream", 
                  command=self.load_soft_preset).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(preset_frame, text="Heavy Dream", 
                  command=self.load_heavy_preset).pack(side=tk.LEFT)
        
        # Process button
        self.process_button = ttk.Button(main_frame, text="Process Video", 
                                        command=self.process_video, style='Accent.TButton')
        self.process_button.grid(row=3, column=0, columnspan=3, pady=(0, 20))
        
        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.status_label = ttk.Label(progress_frame, text="Ready to process")
        self.status_label.grid(row=1, column=0)
        
        # Configure column weights
        main_frame.columnconfigure(0, weight=1)
        file_frame.columnconfigure(0, weight=1)
        
    def update_brightness_label(self, value):
        self.brightness_label.config(text=f"{float(value):.1f}")
        
    def update_vibrance_label(self, value):
        self.vibrance_label.config(text=f"{float(value):.1f}")
        
    def update_denoise_label(self, value):
        self.denoise_label.config(text=f"{int(float(value))}")
        
    def update_bilateral_label(self, value):
        self.bilateral_label.config(text=f"{int(float(value))}")
        
    def update_noise_label(self, value):
        self.noise_label.config(text=f"{int(float(value))}")
    
    def browse_input_file(self):
        filename = filedialog.askopenfilename(
            title="Select input video",
            filetypes=[
                ("Video files", "*.mp4 *.webm *.mov *.avi *.mkv"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.input_file.set(filename)
            # Auto-generate output filename
            if not self.output_file.get():
                path = Path(filename)
                output_path = path.parent / f"{path.stem}_dream_style{path.suffix}"
                self.output_file.set(str(output_path))
    
    def browse_output_file(self):
        filename = filedialog.asksaveasfilename(
            title="Save processed video as",
            filetypes=[
                ("MP4 files", "*.mp4"),
                ("WebM files", "*.webm"),
                ("MOV files", "*.mov"),
                ("AVI files", "*.avi"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.output_file.set(filename)
    
    def load_dream_preset(self):
        """Load Dream Recorder default settings"""
        self.brightness.set(0.2)
        self.vibrance.set(2.0)
        self.denoise.set(300)
        self.bilateral.set(100)
        self.noise.set(40)
        self.update_all_labels()
    
    def load_soft_preset(self):
        """Load soft dreamy settings"""
        self.brightness.set(0.1)
        self.vibrance.set(1.0)
        self.denoise.set(200)
        self.bilateral.set(75)
        self.noise.set(20)
        self.update_all_labels()
    
    def load_heavy_preset(self):
        """Load heavy dreamy settings"""
        self.brightness.set(0.3)
        self.vibrance.set(3.5)
        self.denoise.set(400)
        self.bilateral.set(150)
        self.noise.set(60)
        self.update_all_labels()
    
    def update_all_labels(self):
        self.brightness_label.config(text=f"{self.brightness.get():.1f}")
        self.vibrance_label.config(text=f"{self.vibrance.get():.1f}")
        self.denoise_label.config(text=f"{self.denoise.get()}")
        self.bilateral_label.config(text=f"{self.bilateral.get()}")
        self.noise_label.config(text=f"{self.noise.get()}")
    
    def apply_dream_style(self, input_path, output_path):
        """Apply the Dream Recorder visual style to any video."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Apply FFmpeg filters
            stream = ffmpeg.input(input_path)
            
            # Apply dream style filters with current settings
            stream = ffmpeg.filter(stream, 'eq', brightness=self.brightness.get())
            stream = ffmpeg.filter(stream, 'vibrance', intensity=self.vibrance.get())
            stream = ffmpeg.filter(stream, 'vaguedenoiser', threshold=self.denoise.get())
            stream = ffmpeg.filter(stream, 'bilateral', sigmaS=self.bilateral.get())
            stream = ffmpeg.filter(stream, 'noise', all_strength=self.noise.get())
            
            # Configure output based on file extension
            output_ext = Path(output_path).suffix.lower()
            if output_ext == '.webm':
                stream = ffmpeg.output(stream, temp_path, vcodec='libvpx-vp9', acodec='libopus')
            else:
                stream = ffmpeg.output(stream, temp_path)
            
            # Run FFmpeg
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            # Move processed file to final location
            shutil.move(temp_path, output_path)
            
            return True
            
        except Exception as e:
            # Clean up temp file if it exists
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e
    
    def process_video_thread(self):
        """Process video in a separate thread"""
        try:
            input_path = self.input_file.get()
            output_path = self.output_file.get()
            
            if not input_path or not output_path:
                messagebox.showerror("Error", "Please select input and output files")
                return
            
            if not os.path.exists(input_path):
                messagebox.showerror("Error", f"Input file not found: {input_path}")
                return
            
            # Update UI
            self.root.after(0, lambda: self.status_label.config(text="Processing video..."))
            self.root.after(0, self.progress_bar.start)
            
            # Process the video
            self.apply_dream_style(input_path, output_path)
            
            # Success
            self.root.after(0, self.progress_bar.stop)
            self.root.after(0, lambda: self.status_label.config(text="Processing complete!"))
            self.root.after(0, lambda: messagebox.showinfo("Success", 
                                                           f"Dream style applied successfully!\nOutput saved to: {output_path}"))
            
        except Exception as e:
            self.root.after(0, self.progress_bar.stop)
            self.root.after(0, lambda: self.status_label.config(text="Error occurred"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to process video:\n{str(e)}"))
        
        finally:
            self.processing = False
            self.root.after(0, lambda: self.process_button.config(state='normal', text='Process Video'))
    
    def process_video(self):
        """Start video processing"""
        if self.processing:
            return
        
        self.processing = True
        self.process_button.config(state='disabled', text='Processing...')
        self.status_label.config(text="Starting processing...")
        
        # Start processing in a separate thread
        thread = threading.Thread(target=self.process_video_thread, daemon=True)
        thread.start()

def main():
    # Check if ffmpeg-python is available
    try:
        import ffmpeg
    except ImportError:
        print("Error: ffmpeg-python is required.")
        print("Install it with: pip install ffmpeg-python")
        sys.exit(1)
    
    root = tk.Tk()
    app = DreamStyleGUI(root)
    
    # Configure style
    style = ttk.Style()
    style.theme_use('clam')
    
    root.mainloop()

if __name__ == "__main__":
    main()
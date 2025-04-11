import tkinter as tk
from tkinter import filedialog, ttk
import os
import subprocess
import threading

class FFmpegHapConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("HAP Video Converter")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        self.input_files = []
        self.output_directory = ""
        
        # Setup UI components
        self.setup_ui()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input Files Section
        input_frame = ttk.LabelFrame(main_frame, text="Input Files", padding="10")
        input_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        input_btn = ttk.Button(input_frame, text="Select Files", command=self.select_files)
        input_btn.pack(side=tk.TOP, anchor=tk.W, pady=5)
        
        # Files list with scrollbar
        list_frame = ttk.Frame(input_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.files_listbox = tk.Listbox(list_frame, height=10)
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.files_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.files_listbox.yview)
        
        # Clear selection button
        clear_btn = ttk.Button(input_frame, text="Clear Selection", command=self.clear_selection)
        clear_btn.pack(side=tk.TOP, anchor=tk.W, pady=5)
        
        # Output Directory Section
        output_frame = ttk.LabelFrame(main_frame, text="Output Directory", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_var, width=50)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        output_btn = ttk.Button(output_frame, text="Browse", command=self.select_output_dir)
        output_btn.pack(side=tk.RIGHT)
        
        # HAP Format Options
        options_frame = ttk.LabelFrame(main_frame, text="Conversion Options", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        
        # HAP variant selection
        ttk.Label(options_frame, text="HAP Variant:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.hap_variant = tk.StringVar(value="hap")
        variant_combo = ttk.Combobox(options_frame, textvariable=self.hap_variant)
        variant_combo['values'] = ('hap', 'hap_alpha', 'hap_q')
        variant_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Chunks selection
        ttk.Label(options_frame, text="Chunks:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.chunks_var = tk.StringVar(value="4")
        chunks_combo = ttk.Combobox(options_frame, textvariable=self.chunks_var, width=5)
        chunks_combo['values'] = ('1', '2', '4', '8', '16')
        chunks_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Additional FFmpeg parameters
        ttk.Label(options_frame, text="Additional Parameters:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.additional_params = tk.StringVar()
        params_entry = ttk.Entry(options_frame, textvariable=self.additional_params, width=40)
        params_entry.grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(fill=tk.X, pady=2)
        
        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        convert_btn = ttk.Button(button_frame, text="Convert", command=self.start_conversion)
        convert_btn.pack(side=tk.RIGHT, padx=5)
        
        quit_btn = ttk.Button(button_frame, text="Quit", command=self.root.destroy)
        quit_btn.pack(side=tk.RIGHT, padx=5)
    
    def select_files(self):
        """Open file dialog to select input video files"""
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=(
                ("Video files", "*.mp4 *.mov *.avi *.mkv"),
                ("All files", "*.*")
            )
        )
        if files:
            self.input_files.extend(files)
            self.update_files_list()
    
    def update_files_list(self):
        """Update the listbox with selected files"""
        self.files_listbox.delete(0, tk.END)
        for file in self.input_files:
            self.files_listbox.insert(tk.END, os.path.basename(file))
    
    def clear_selection(self):
        """Clear the selected files list"""
        self.input_files = []
        self.files_listbox.delete(0, tk.END)
    
    def select_output_dir(self):
        """Open dialog to select output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_directory = directory
            self.output_var.set(directory)
    
    def start_conversion(self):
        """Start the conversion process in a separate thread"""
        if not self.input_files:
            self.status_var.set("No input files selected")
            return
        
        if not self.output_directory:
            self.status_var.set("No output directory selected")
            return
        
        # Start conversion in a separate thread to keep UI responsive
        conversion_thread = threading.Thread(target=self.convert_files)
        conversion_thread.daemon = True
        conversion_thread.start()
    
    def convert_files(self):
        """Convert all selected files to HAP format"""
        total_files = len(self.input_files)
        self.progress['maximum'] = total_files
        self.progress['value'] = 0
        
        for i, input_file in enumerate(self.input_files):
            self.status_var.set(f"Converting {os.path.basename(input_file)} ({i+1}/{total_files})")
            
            # Prepare output filename
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = os.path.join(self.output_directory, f"{base_name}.mov")
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-c:v', 'hap',
                '-format', self.hap_variant.get(),
                '-chunks', self.chunks_var.get()
            ]
            
            # Add additional parameters if specified
            if self.additional_params.get():
                cmd.extend(self.additional_params.get().split())
                
            cmd.append(output_file)
            
            try:
                # Run FFmpeg command
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                stdout, stderr = process.communicate()
                
                # Update progress
                self.progress['value'] = i + 1
                self.root.update_idletasks()
                
                if process.returncode != 0:
                    print(f"Error converting {input_file}: {stderr}")
                    self.status_var.set(f"Error converting {os.path.basename(input_file)}")
                
            except Exception as e:
                print(f"Exception during conversion: {e}")
                self.status_var.set(f"Error: {str(e)}")
        
        self.status_var.set("Conversion completed")


if __name__ == "__main__":
    root = tk.Tk()
    app = FFmpegHapConverter(root)
    root.mainloop()
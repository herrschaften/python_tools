import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
from PIL import Image, ImageTk
import shutil

class ImageOptimizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Optimizer for Live Visuals")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        # Check if ffmpeg is installed
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            messagebox.showerror("Error", "FFmpeg is not installed or not in PATH. Please install FFmpeg before using this application.")
            root.destroy()
            return
            
        # Variables
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.size_limit = tk.StringVar(value="2")  # Default 2MB
        self.current_file = tk.StringVar()
        self.progress_value = tk.DoubleVar()
        self.status = tk.StringVar(value="Ready")
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Folder selection
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding="10")
        folder_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(folder_frame, text="Input Folder:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(folder_frame, textvariable=self.input_folder, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(folder_frame, text="Browse...", command=self.browse_input_folder).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(folder_frame, text="Output Folder:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(folder_frame, textvariable=self.output_folder, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(folder_frame, text="Browse...", command=self.browse_output_folder).grid(row=1, column=2, padx=5, pady=5)
        
        # Settings
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(settings_frame, text="Maximum File Size (MB):").grid(row=0, column=0, sticky=tk.W, pady=5)
        size_spinbox = ttk.Spinbox(settings_frame, from_=0.1, to=100, increment=0.1, textvariable=self.size_limit, width=10)
        size_spinbox.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(progress_frame, text="Current File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(progress_frame, textvariable=self.current_file).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_value, length=100, mode="determinate")
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(progress_frame, text="Status:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(progress_frame, textvariable=self.status).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Preview section
        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create a canvas for image preview
        self.preview_canvas = tk.Canvas(preview_frame, bg="black")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Process Images", command=self.start_processing).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Exit", command=self.root.destroy).pack(side=tk.RIGHT, padx=5)
    
    def browse_input_folder(self):
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            self.input_folder.set(folder)
    
    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)
    
    def start_processing(self):
        input_folder = self.input_folder.get()
        output_folder = self.output_folder.get()
        
        if not input_folder or not os.path.isdir(input_folder):
            messagebox.showerror("Error", "Please select a valid input folder.")
            return
            
        if not output_folder or not os.path.isdir(output_folder):
            messagebox.showerror("Error", "Please select a valid output folder.")
            return
            
        try:
            size_limit = float(self.size_limit.get())
            if size_limit <= 0:
                messagebox.showerror("Error", "Size limit must be greater than 0.")
                return
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for the size limit.")
            return
            
        # Start processing in a separate thread to keep the UI responsive
        threading.Thread(target=self.process_images, daemon=True).start()
    
    def process_images(self):
        input_folder = self.input_folder.get()
        output_folder = self.output_folder.get()
        size_limit_mb = float(self.size_limit.get())
        size_limit_bytes = size_limit_mb * 1024 * 1024  # Convert MB to bytes
        
        # Get list of image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
        image_files = []
        
        for file in os.listdir(input_folder):
            file_path = os.path.join(input_folder, file)
            if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in image_extensions):
                image_files.append(file)
        
        total_files = len(image_files)
        if total_files == 0:
            self.status.set("No image files found in the input folder.")
            messagebox.showinfo("Info", "No image files found in the input folder.")
            return
            
        # Update UI
        self.status.set(f"Processing {total_files} images...")
        self.progress_value.set(0)
        
        # Process each file
        for i, file in enumerate(image_files):
            input_path = os.path.join(input_folder, file)
            self.current_file.set(file)
            
            # Update preview
            self.update_preview(input_path)
            
            # Get file size
            file_size = os.path.getsize(input_path)
            
            # Get file extension without the dot
            filename, _ = os.path.splitext(file)
            output_path = os.path.join(output_folder, f"{filename}.png")
            
            # First convert to PNG with maximum compression to see if it's already under the limit
            temp_output_path = os.path.join(output_folder, f"{filename}_temp.png")
            
            try:
                # Get original image dimensions
                img = Image.open(input_path)
                orig_width, orig_height = img.size
                img.close()
                
                # Initial conversion with high compression and no resize
                cmd = [
                    "ffmpeg",
                    "-i", input_path,
                    "-compression_level", "9",  # Maximum compression for PNG
                    "-y",
                    temp_output_path
                ]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                
                # Check if the output file is under the size limit after initial conversion
                current_size = os.path.getsize(temp_output_path)
                
                if current_size <= size_limit_bytes:
                    # If already under the limit, just rename the temp file
                    self.status.set(f"Converting {file} (already under size limit)...")
                    os.rename(temp_output_path, output_path)
                else:
                    # Need to resize with an iterative approach
                    self.status.set(f"Resizing {file} to meet size limit...")
                    
                    # Try several resize factors until we get under the limit
                    resize_factors = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
                    success = False
                    
                    for factor in resize_factors:
                        new_width = int(orig_width * factor)
                        new_height = int(orig_height * factor)
                        
                        # Ensure dimensions are even (required by some FFmpeg filters)
                        new_width = max(2, new_width - (new_width % 2))
                        new_height = max(2, new_height - (new_height % 2))
                        
                        # Use FFmpeg to resize with high compression
                        cmd = [
                            "ffmpeg",
                            "-i", input_path,
                            "-vf", f"scale={new_width}:{new_height}",
                            "-compression_level", "9",  # Maximum compression
                            "-y",
                            temp_output_path
                        ]
                        
                        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                        
                        # Check if we're now under the limit
                        current_size = os.path.getsize(temp_output_path)
                        if current_size <= size_limit_bytes:
                            os.rename(temp_output_path, output_path)
                            success = True
                            break
                    
                    # If we tried all factors and still couldn't get under the limit,
                    # use the smallest resize with optimized compression options
                    if not success:
                        self.status.set(f"Using advanced compression for {file}...")
                        
                        # Last resort: most aggressive resize and optimized PNG settings
                        smallest_width = max(2, int(orig_width * 0.1))
                        smallest_height = max(2, int(orig_height * 0.1))
                        
                        # Ensure dimensions are even
                        smallest_width = smallest_width - (smallest_width % 2)
                        smallest_height = smallest_height - (smallest_height % 2)
                        
                        # Try pngquant optimization through FFmpeg
                        cmd = [
                            "ffmpeg",
                            "-i", input_path,
                            "-vf", f"scale={smallest_width}:{smallest_height}",
                            "-compression_level", "9",
                            "-pred", "mixed",    # Mixed prediction
                            "-y",
                            temp_output_path
                        ]
                        
                        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                        
                        # If we still can't get under the limit, inform the user
                        current_size = os.path.getsize(temp_output_path)
                        if current_size <= size_limit_bytes:
                            os.rename(temp_output_path, output_path)
                        else:
                            # Image is still too large, but we'll use our best attempt
                            os.rename(temp_output_path, output_path)
                            self.status.set(f"Warning: {file} could not be reduced below the size limit")
                            messagebox.showwarning("Size Limit Warning", 
                                f"Image {file} could not be reduced below the size limit of {size_limit_mb}MB.\n"
                                f"Best result: {current_size / (1024 * 1024):.2f}MB")
            except Exception as e:
                self.status.set(f"Error processing {file}: {str(e)}")
                messagebox.showerror("Error", f"Error processing {file}: {str(e)}")
                # Clean up temp file if it exists
                if os.path.exists(temp_output_path):
                    try:
                        os.remove(temp_output_path)
                    except:
                        pass
            
            # Update progress
            progress_percent = (i + 1) / total_files * 100
            self.progress_value.set(progress_percent)
            self.root.update_idletasks()
            
            # Clean up any leftover temp files
            if os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except:
                    pass
        
        self.status.set("Processing complete!")
        messagebox.showinfo("Success", "All images have been processed!")
    
    def update_preview(self, image_path):
        try:
            # Open and resize image for preview
            img = Image.open(image_path)
            
            # Get canvas dimensions
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                # Canvas not yet realized, use default dimensions
                canvas_width = 400
                canvas_height = 300
            
            # Calculate resize dimensions while maintaining aspect ratio
            img_width, img_height = img.size
            ratio = min(canvas_width / img_width, canvas_height / img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            
            # Resize image for display
            img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage for Tkinter
            self.tk_img = ImageTk.PhotoImage(img_resized)
            
            # Clear previous image and draw new one
            self.preview_canvas.delete("all")
            
            # Center the image on canvas
            x_position = (canvas_width - new_width) // 2
            y_position = (canvas_height - new_height) // 2
            
            self.preview_canvas.create_image(x_position, y_position, anchor=tk.NW, image=self.tk_img)
        except Exception as e:
            print(f"Error updating preview: {str(e)}")

def main():
    root = tk.Tk()
    app = ImageOptimizerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
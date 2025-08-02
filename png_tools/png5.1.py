import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QFileDialog, QSpinBox, QColorDialog,
                           QListWidget, QListWidgetItem, QGridLayout, QLineEdit,
                           QProgressBar, QMessageBox, QScrollArea, QCheckBox, QComboBox,
                           QGroupBox, QFrame, QDoubleSpinBox)
from PyQt5.QtGui import QPixmap, QImage, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import threading
from PIL import Image as PILImage  # Renamed to avoid namespace conflicts
import numpy as np

class ImageProcessor(QThread):
    progress_updated = pyqtSignal(int)
    processing_complete = pyqtSignal(list)
    
    def __init__(self, file_paths, num_colors, downscale_factor=None, output_folder=None, 
                 custom_palette=None, use_dithering=True, upscale_factor=None, upscale_method="NEAREST", 
                 upscale_dithering=False, downscale_method="LANCZOS"):
        super().__init__()
        self.file_paths = file_paths
        self.num_colors = num_colors
        self.downscale_factor = downscale_factor
        self.output_folder = output_folder
        self.custom_palette = custom_palette
        # Store dithering as boolean - we'll convert to int only when passing to quantize
        self.use_dithering = use_dithering
        self.upscale_factor = upscale_factor
        self.upscale_method = upscale_method
        self.upscale_dithering = upscale_dithering
        self.downscale_method = downscale_method
        self.batch_processed_files = []
        self.batch_total_files = 0
        self.batch_current_file = 0
        self.batch_custom_palette = None
        self.batch_color_threads = []
        print(f"ImageProcessor initialized with dithering: {self.use_dithering}, upscale method: {self.upscale_method}, upscale dithering: {self.upscale_dithering}, downscale method: {self.downscale_method}")
        
        # Debug custom palette information
        if self.custom_palette:
            print(f"Custom palette provided with {len(self.custom_palette)} colors:")
            for idx, color in self.custom_palette[:5]:  # Print first 5 colors
                print(f"  Color {idx}: RGB{color}")
            if len(self.custom_palette) > 5:
                print(f"  ... and {len(self.custom_palette)-5} more colors")
        else:
            print("No custom palette provided, will generate one during processing")

    ##################################################################################        
    def generate_standard_palette(self, img):
        """Generate a palette without black color"""
        # Convert to RGB to ensure consistent processing
        img_rgb = img.convert("RGB")
        
        # Quantize to slightly more colors than requested to have room for removal
        palette_img = img_rgb.quantize(colors=self.num_colors + 1, dither=0)
        
        # Get the full palette
        full_palette = palette_img.getpalette()
        
        # Create a new palette without black
        new_palette_data = []
        used_colors = set()
        
        # Collect non-black colors, ensuring we get exactly the number of colors requested
        for i in range(len(full_palette) // 3):
            r = full_palette[i*3]
            g = full_palette[i*3 + 1]
            b = full_palette[i*3 + 2]
            
            # Skip pure black and already used colors
            if (r, g, b) != (0, 0, 0) and (r, g, b) not in used_colors:
                new_palette_data.extend([r, g, b])
                used_colors.add((r, g, b))
            
            # Stop when we have exactly the number of colors requested
            if len(new_palette_data) // 3 == self.num_colors:
                break
        
        # If we don't have enough colors, pad with variations of existing colors
        while len(new_palette_data) // 3 < self.num_colors:
            # Add slightly modified version of an existing color
            last_color = (new_palette_data[-3], new_palette_data[-2], new_palette_data[-1])
            new_r = min(255, last_color[0] + 1)
            new_g = min(255, last_color[1] + 1)
            new_b = min(255, last_color[2] + 1)
            new_palette_data.extend([new_r, new_g, new_b])
        
        # Fill the rest of the palette with zeros
        remaining_colors = 256 - self.num_colors
        new_palette_data.extend([0] * (remaining_colors * 3))
        
        # Create a new palette image
        new_palette_img = PILImage.new('P', (1, 1))
        new_palette_img.putpalette(new_palette_data)
        
        # Apply the palette with or without dithering
        dither_value = 1 if self.use_dithering else 0
        
        return img_rgb.quantize(
            colors=self.num_colors, 
            palette=new_palette_img, 
            dither=dither_value
        )
        
    ##################################################################################


    def run(self):
        processed_files = []
        total_files = len(self.file_paths)
        
        for i, file_path in enumerate(self.file_paths):
            try:
                # Get output filename
                basename = os.path.basename(file_path)
                name, _ = os.path.splitext(basename)
                
                if self.output_folder and os.path.isdir(self.output_folder):
                    output_path = os.path.join(self.output_folder, f"{name}_indexed.png")
                else:
                    dirname = os.path.dirname(file_path)
                    output_path = os.path.join(dirname, f"{name}_indexed.png")
                
                print(f"Processing image {i+1}/{total_files}: {basename}")
                
                # Process the image
                img = PILImage.open(file_path)
                
                # Store original dimensions for potential upscaling later
                original_width, original_height = img.size
                
                # Get downscale method
                downscale_method = getattr(PILImage, self.downscale_method)
                
                # Resize if downscale_factor is specified
                if self.downscale_factor and self.downscale_factor < 1.0:
                    width, height = img.size
                    new_width = int(width * self.downscale_factor)
                    new_height = int(height * self.downscale_factor)
                    img = img.resize((new_width, new_height), downscale_method)
                
                # Convert to RGB to ensure consistent processing
                img = img.convert("RGB")
                
                # Use custom palette if provided
                if self.custom_palette:
                    try:
                        # Create a palette image
                        palette_img = PILImage.new('P', (1, 1))
                        palette_data = []
                        
                        # Flatten the palette data
                        for idx, color in self.custom_palette:
                            r, g, b = color
                            palette_data.extend([r, g, b])
                        
                        # Fill the rest of the 256-color palette with zeros
                        remaining_colors = 256 - len(self.custom_palette)
                        palette_data.extend([0] * (remaining_colors * 3))
                        
                        # Set the palette
                        palette_img.putpalette(palette_data)
                        
                        # Convert boolean to int for dithering (1=True, 0=False)
                        dither_value = 1 if self.use_dithering else 0
                        print(f"Applying quantize with custom palette, dither={dither_value}")
                        
                        # Force conversion to RGB to ensure consistent palette application
                        img_rgb = img.convert("RGB")
                        
                        # Apply the palette with or without dithering
                        img_indexed = img_rgb.quantize(
                            colors=len(self.custom_palette), 
                            palette=palette_img, 
                            dither=dither_value
                        )
                        
                        # Debug palette verification
                        if file_path == self.file_paths[0]:  # First image only
                            applied_palette = img_indexed.getpalette()
                            print("Verification of applied palette:")
                            for i in range(min(5, len(self.custom_palette))):
                                idx, color = self.custom_palette[i]
                                print(f"  Requested: Color {idx}: RGB{color}")
                                actual_r = applied_palette[i*3]
                                actual_g = applied_palette[i*3+1]
                                actual_b = applied_palette[i*3+2]
                                print(f"  Applied: Color {i}: RGB({actual_r}, {actual_g}, {actual_b})")
                    
                    except Exception as e:
                        print(f"Error applying custom palette: {e}")
                        # Fall back to standard palette generation
                        print("Falling back to standard palette generation...")
                        img_indexed = self.generate_standard_palette(img)
                else:
                    # Generate a standard palette if no custom palette is provided
                    img_indexed = self.generate_standard_palette(img)
                
                # Upscale if specified
                if self.upscale_factor and self.upscale_factor > 1.0:
                    # Calculate dimensions for upscaling
                    current_width, current_height = img_indexed.size
                    new_width = int(current_width * self.upscale_factor)
                    new_height = int(current_height * self.upscale_factor)
                    
                    # Select upscale method
                    upscale_method = getattr(PILImage, self.upscale_method)

                    # If upscale dithering is enabled, convert to RGB, upscale, and then re-index
                    if self.upscale_dithering and img_indexed.mode == 'P':
                        # Get the palette data for reuse
                        original_palette = img_indexed.getpalette()
                        
                        # Convert to RGB for better interpolation
                        rgb_img = img_indexed.convert('RGB')
                        
                        # Upscale using selected method
                        upscaled_rgb = rgb_img.resize((new_width, new_height), upscale_method)
                        
                        # Re-index with the same palette, applying dithering
                        palette_img = PILImage.new('P', (1, 1))
                        palette_img.putpalette(original_palette)
                        
                        # Quantize the upscaled RGB image with dithering
                        dither_value = 1 if self.use_dithering else 0
                        img_indexed = upscaled_rgb.quantize(
                            colors=min(256, self.num_colors),
                            palette=palette_img,
                            dither=dither_value
                        )
                    else:
                        # Standard upscale without re-dithering
                        img_indexed = img_indexed.resize((new_width, new_height), upscale_method)
                
                # Save the processed image
                img_indexed.save(output_path)
                
                processed_files.append(output_path)
                
                # Update progress
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                
        self.processing_complete.emit(processed_files)

class ColorEditorThread(QThread):
    progress_updated = pyqtSignal(int)
    processing_complete = pyqtSignal(str)
    
    def __init__(self, input_path, output_path, color_mapping, use_dithering=True, 
                 upscale_factor=None, upscale_method="NEAREST", upscale_dithering=False, downscale_method="LANCZOS"):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.color_mapping = color_mapping
        # Convert boolean to integer for consistency
        self.use_dithering = 1 if use_dithering else 0
        self.upscale_factor = upscale_factor
        self.upscale_method = upscale_method
        self.upscale_dithering = upscale_dithering
        self.downscale_method = downscale_method
        print(f"ColorEditorThread initialized with dithering: {self.use_dithering}, upscale method: {self.upscale_method}, upscale dithering: {self.upscale_dithering}, downscale method: {self.downscale_method}")
        
    def run(self):
        try:
            # Disable PIL's warning temporarily
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            
            # Open the image - make sure to use a copy to avoid modifying the original
            with PILImage.open(self.input_path) as original_img:
                img = original_img.copy()
            
            # Re-enable warnings
            warnings.resetwarnings()
            
            # Get the palette
            if img.mode != 'P':
                # If not indexed, convert it
                # No need to apply dithering here as we're just doing a direct conversion
                img = img.convert('P', palette=PILImage.ADAPTIVE, colors=len(self.color_mapping))
                
            palette = img.getpalette()
            
            # If there's no palette, this isn't an indexed image
            if not palette:
                self.processing_complete.emit("Error: Not an indexed image")
                return
            
            # Make a copy of the palette for modification
            new_palette = palette.copy()
            
            # Check if all color indices in color_mapping exist in the palette
            for index, new_color in self.color_mapping.items():
                if index * 3 + 2 >= len(new_palette):
                    print(f"Warning: Color index {index} out of range (palette length: {len(new_palette)//3})")
                    continue
                    
                r, g, b = new_color
                new_palette[index*3] = r
                new_palette[index*3 + 1] = g
                new_palette[index*3 + 2] = b
            
            # Apply the new palette
            new_img = img.copy()
            new_img.putpalette(new_palette)
            
            # Upscale if specified
            if self.upscale_factor and self.upscale_factor > 1.0:
                # Calculate dimensions for upscaling
                current_width, current_height = new_img.size
                new_width = int(current_width * self.upscale_factor)
                new_height = int(current_height * self.upscale_factor)
                
                # Select upscale method
                upscale_method = getattr(PILImage, self.upscale_method)
                
                # If upscale dithering is enabled, convert to RGB, upscale, and then re-index
                if self.upscale_dithering and new_img.mode == 'P':
                    # Store the palette for reuse
                    original_palette = new_img.getpalette()
                    
                    # Convert to RGB for better interpolation
                    rgb_img = new_img.convert('RGB')
                    
                    # Upscale using selected method
                    upscaled_rgb = rgb_img.resize((new_width, new_height), upscale_method)
                    
                    # Re-index with the same palette, applying dithering
                    palette_img = PILImage.new('P', (1, 1))
                    palette_img.putpalette(original_palette)
                    
                    # Quantize the upscaled RGB image with dithering if specified
                    new_img = upscaled_rgb.quantize(
                        colors=256,  # Use all palette entries
                        palette=palette_img,
                        dither=self.use_dithering  # Apply dithering if enabled
                    )
                else:
                    # Standard upscale without re-dithering
                    new_img = new_img.resize((new_width, new_height), upscale_method)
            
            # Save the image
            new_img.save(self.output_path)
            
            self.progress_updated.emit(100)
            self.processing_complete.emit(self.output_path)
            
        except Exception as e:
            print(f"Color editor thread error: {str(e)}")
            self.processing_complete.emit(f"Error: {str(e)}")

class IndexedColorConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Indexed Color PNG Converter")
        self.setMinimumSize(1000, 800)
        
        # Main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create main layout for central widget
        main_layout = QVBoxLayout()
        self.central_widget.setLayout(main_layout)
        
        # Setup the unified interface
        self.setup_unified_interface(main_layout)
        
        # Initialize state variables
        self.current_image_path = None
        self.current_indexed_image_path = None
        self.current_palette = []
        self.use_dithering = True
        self.saved_version_count = {}  # Dictionary to track saved versions of files
        
    def setup_unified_interface(self, main_layout):
        # Top section: Image selection and conversion
        top_layout = QHBoxLayout()
        
        # Left panel for controls
        left_panel = QVBoxLayout()
        
        # Single Image Controls Group
        single_image_group = QGroupBox("Single Image Controls")
        single_image_layout = QVBoxLayout()
        
        # Image selection
        self.select_image_btn = QPushButton("Select Image")
        self.select_image_btn.clicked.connect(self.select_single_image)
        single_image_layout.addWidget(self.select_image_btn)
        
        # Convert button
        self.convert_btn = QPushButton("Convert to Indexed PNG")
        self.convert_btn.clicked.connect(self.convert_single_image)
        self.convert_btn.setEnabled(False)
        single_image_layout.addWidget(self.convert_btn)
        
        # Refresh settings button
        self.refresh_settings_btn = QPushButton("Refresh Settings")
        self.refresh_settings_btn.clicked.connect(self.refresh_settings)
        single_image_layout.addWidget(self.refresh_settings_btn)
        
        # Progress bar for single image
        self.single_progress = QProgressBar()
        single_image_layout.addWidget(self.single_progress)
        
        single_image_group.setLayout(single_image_layout)
        left_panel.addWidget(single_image_group)
        
        # Batch Processing Group
        batch_group = QGroupBox("Batch Processing")
        batch_layout = QVBoxLayout()
        
        # Input folder
        input_folder_layout = QHBoxLayout()
        input_folder_layout.addWidget(QLabel("Input Folder:"))
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setReadOnly(True)
        input_folder_layout.addWidget(self.folder_path_edit)
        self.select_folder_btn = QPushButton("Browse...")
        self.select_folder_btn.clicked.connect(self.select_folder)
        input_folder_layout.addWidget(self.select_folder_btn)
        batch_layout.addLayout(input_folder_layout)
        
        # Output folder
        output_folder_layout = QHBoxLayout()
        output_folder_layout.addWidget(QLabel("Output Folder:"))
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setReadOnly(True)
        self.output_folder_edit.setPlaceholderText("Same as input folder if not specified")
        output_folder_layout.addWidget(self.output_folder_edit)
        self.select_output_btn = QPushButton("Browse...")
        self.select_output_btn.clicked.connect(self.select_output_folder)
        output_folder_layout.addWidget(self.select_output_btn)
        batch_layout.addLayout(output_folder_layout)
        
        # Process button
        self.process_batch_btn = QPushButton("Process Folder")
        self.process_batch_btn.clicked.connect(self.process_batch)
        self.process_batch_btn.setEnabled(False)
        batch_layout.addWidget(self.process_batch_btn)
        
        # Progress bar for batch
        self.batch_progress = QProgressBar()
        batch_layout.addWidget(self.batch_progress)
        
        batch_group.setLayout(batch_layout)
        left_panel.addWidget(batch_group)
        
        # Settings Group
        settings_group = QGroupBox("Image Processing Settings")
        settings_layout = QGridLayout()
        
        # Number of colors
        settings_layout.addWidget(QLabel("Number of Colors:"), 0, 0)
        self.num_colors_spin = QSpinBox()
        self.num_colors_spin.setRange(2, 256)
        self.num_colors_spin.setValue(16)
        settings_layout.addWidget(self.num_colors_spin, 0, 1)
        
        # Downscale factor
        settings_layout.addWidget(QLabel("Downscale Factor:"), 1, 0)
        self.downscale_factor_spin = QDoubleSpinBox()
        self.downscale_factor_spin.setRange(0.0001, 100.0)
        self.downscale_factor_spin.setValue(1.0)
        self.downscale_factor_spin.setSingleStep(0.0001)
        self.downscale_factor_spin.setDecimals(5)
        self.downscale_factor_spin.setSpecialValueText("No Resize")
        settings_layout.addWidget(self.downscale_factor_spin, 1, 1)
        
        # Downscale method dropdown
        settings_layout.addWidget(QLabel("Downscale Method:"), 2, 0)
        self.downscale_method_combo = QComboBox()
        self.downscale_method_combo.addItems(["LANCZOS", "BICUBIC", "BILINEAR", "NEAREST"])
        settings_layout.addWidget(self.downscale_method_combo, 2, 1)
        
        # Upscale factor
        settings_layout.addWidget(QLabel("Upscale Factor:"), 3, 0)
        self.upscale_factor_spin = QDoubleSpinBox()
        self.upscale_factor_spin.setRange(0.000, 100.0)
        self.upscale_factor_spin.setValue(2.0)
        self.upscale_factor_spin.setSingleStep(0.01)
        self.upscale_factor_spin.setDecimals(5)
        self.upscale_factor_spin.setSpecialValueText("No Upscale")
        settings_layout.addWidget(self.upscale_factor_spin, 3, 1)
        
        # Upscale method dropdown
        settings_layout.addWidget(QLabel("Upscale Method:"), 4, 0)
        self.upscale_method_combo = QComboBox()
        self.upscale_method_combo.addItems(["NEAREST", "BILINEAR", "BICUBIC"])
        settings_layout.addWidget(self.upscale_method_combo, 4, 1)
        
        # Dithering options
        self.dithering_checkbox = QCheckBox("Use Diffusion Dithering (color reduction)")
        self.dithering_checkbox.setChecked(True)
        self.dithering_checkbox.stateChanged.connect(self.toggle_dithering)
        settings_layout.addWidget(self.dithering_checkbox, 5, 0, 1, 2)
        
        # Upscale dithering option
        self.upscale_dithering_checkbox = QCheckBox("Apply Dithering During Upscale")
        self.upscale_dithering_checkbox.setChecked(False)
        settings_layout.addWidget(self.upscale_dithering_checkbox, 6, 0, 1, 2)
        
        settings_group.setLayout(settings_layout)
        left_panel.addWidget(settings_group)
        
        # Spacer
        left_panel.addStretch(1)
        
        top_layout.addLayout(left_panel, 1)
        
        # Right panel for image previews
        right_panel = QVBoxLayout()
        
        # Original image preview
        right_panel.addWidget(QLabel("Original Image:"))
        self.original_image_label = QLabel()
        self.original_image_label.setAlignment(Qt.AlignCenter)
        self.original_image_label.setMinimumSize(400, 300)  # Larger preview
        self.original_image_label.setStyleSheet("border: 1px solid #cccccc;")
        
        # Create scroll area for the original image
        orig_scroll = QScrollArea()
        orig_scroll.setWidgetResizable(True)
        orig_scroll.setWidget(self.original_image_label)
        right_panel.addWidget(orig_scroll)
        
        # Indexed/preview image
        right_panel.addWidget(QLabel("Processed Image (Downscaled + Upscaled):"))
        self.indexed_image_label = QLabel()
        self.indexed_image_label.setAlignment(Qt.AlignCenter)
        self.indexed_image_label.setMinimumSize(400, 300)  # Larger preview
        self.indexed_image_label.setStyleSheet("border: 1px solid #cccccc;")
        
        # Create scroll area for the indexed image
        indexed_scroll = QScrollArea()
        indexed_scroll.setWidgetResizable(True)
        indexed_scroll.setWidget(self.indexed_image_label)
        right_panel.addWidget(indexed_scroll)
        
        top_layout.addLayout(right_panel, 2)
        
        main_layout.addLayout(top_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # Bottom section: Color editing
        bottom_layout = QVBoxLayout()
        
        # Color editor group
        color_editor_group = QGroupBox("Color Palette Editor")
        color_editor_layout = QVBoxLayout()
        
        color_editor_layout.addWidget(QLabel("Edit Colors (double-click to change):"))
        
        # Color list
        self.color_list = QListWidget()
        self.color_list.setMinimumHeight(150)
        self.color_list.itemDoubleClicked.connect(self.edit_color)
        color_editor_layout.addWidget(self.color_list)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Render button
        self.render_btn = QPushButton("Save with New Colors")
        self.render_btn.clicked.connect(self.render_with_new_colors)
        self.render_btn.setEnabled(False)
        buttons_layout.addWidget(self.render_btn)
        
        color_editor_layout.addLayout(buttons_layout)
        color_editor_group.setLayout(color_editor_layout)
        bottom_layout.addWidget(color_editor_group)
        
        # Results section
        results_group = QGroupBox("Batch Processing Results")
        results_layout = QVBoxLayout()
        
        # Results list
        self.results_list = QListWidget()
        results_layout.addWidget(self.results_list)
        
        results_group.setLayout(results_layout)
        bottom_layout.addWidget(results_group)
        
        main_layout.addLayout(bottom_layout)
    
    def refresh_settings(self):
        """Refresh image processing settings without resetting the color palette"""
        # Only proceed if there is a current image loaded
        if not self.current_image_path:
            QMessageBox.warning(self, "Warning", "No image is currently loaded. Please select an image first.")
            return
            
        # Keep the current palette
        saved_palette = self.current_palette
        
        # Re-process the image with current settings
        self.convert_single_image()
        
        # Restore the palette after conversion completes (via signal/slot)
        # We'll connect a one-time handler to the processing_complete signal
        self.processor.processing_complete.connect(lambda _: self.restore_saved_palette(saved_palette))
        
    def restore_saved_palette(self, saved_palette):
        """Restore a saved color palette after reprocessing"""
        # Disconnect the one-time handler to avoid multiple connections
        try:
            self.processor.processing_complete.disconnect(self.restore_saved_palette)
        except:
            pass  # Ignore if not connected
            
        # Set the saved palette
        self.current_palette = saved_palette
        
        # Update the UI to reflect the saved palette
        self.update_color_list_ui()
        
    def update_color_list_ui(self):
        """Update the color list UI to reflect the current palette"""
        # Clear the list first
        self.color_list.clear()
        
        for idx, color in self.current_palette:
            r, g, b = color
            
            # Create list item
            item = QListWidgetItem(f"Color {idx}: RGB({r}, {g}, {b})")
            
            # Set background color
            item.setBackground(QColor(r, g, b))
            
            # Set text color for better visibility
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            text_color = QColor(0, 0, 0) if brightness > 128 else QColor(255, 255, 255)
            item.setForeground(text_color)
            
            self.color_list.addItem(item)
    
    def select_single_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        
        if file_path:
            self.current_image_path = file_path
            self.load_image_preview(file_path, self.original_image_label)
            self.convert_btn.setEnabled(True)
            
    def load_image_preview(self, image_path, label):
        pixmap = QPixmap(image_path)
        
        # Scale down if needed to fit in the label
        if pixmap.width() > 400 or pixmap.height() > 300:
            pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
        label.setPixmap(pixmap)
    
    def convert_single_image(self):
        if not self.current_image_path:
            return
            
        self.convert_btn.setEnabled(False)
        self.single_progress.setValue(0)
        
        # Get output path
        dir_name = os.path.dirname(self.current_image_path)
        basename = os.path.basename(self.current_image_path)
        name, _ = os.path.splitext(basename)
        output_path = os.path.join(dir_name, f"{name}_indexed.png")
        
        # Get scaling factors
        downscale_factor = self.downscale_factor_spin.value()
        if downscale_factor >= 1.0:
            downscale_factor = None
        
        upscale_factor = self.upscale_factor_spin.value() 
        if upscale_factor <= 1.0:
            upscale_factor = None
        
        # Get upscale and downscale methods
        upscale_method = self.upscale_method_combo.currentText()
        downscale_method = self.downscale_method_combo.currentText()
        
        # Get dithering states
        use_dithering = self.dithering_checkbox.isChecked()
        upscale_dithering = self.upscale_dithering_checkbox.isChecked()
        
        print(f"Single image conversion - Dithering: {use_dithering}, Upscale Method: {upscale_method}, Downscale Method: {downscale_method}, Upscale Dithering: {upscale_dithering}")
        
        # Setup processor thread with new options
        self.processor = ImageProcessor(
            [self.current_image_path], 
            self.num_colors_spin.value(),
            downscale_factor=downscale_factor,
            use_dithering=use_dithering,
            upscale_factor=upscale_factor,
            upscale_method=upscale_method,
            upscale_dithering=upscale_dithering,
            downscale_method=downscale_method
        )
        self.processor.progress_updated.connect(self.single_progress.setValue)
        self.processor.processing_complete.connect(self.on_single_conversion_complete)
        
        # Start processing
        self.processor.start()
    
    def on_single_conversion_complete(self, processed_files):
        if processed_files:
            self.current_indexed_image_path = processed_files[0]
            self.load_image_preview(self.current_indexed_image_path, self.indexed_image_label)
            self.load_color_palette(self.current_indexed_image_path)
            self.render_btn.setEnabled(True)
        
        self.convert_btn.setEnabled(True)
    
    def load_color_palette(self, indexed_image_path):
        try:
            # Clear the list
            self.color_list.clear()
            self.current_palette = []
            
            # Open the image and get its palette
            img = PILImage.open(indexed_image_path)
            
            if img.mode == 'P':
                palette = img.getpalette()
                
                if palette:
                    # Find the unique colors in use
                    img_array = np.array(img)
                    unique_indices = np.unique(img_array)
                    
                    for idx in unique_indices:
                        r = palette[idx*3]
                        g = palette[idx*3 + 1]
                        b = palette[idx*3 + 2]
                        color = (r, g, b)
                        self.current_palette.append((idx, color))
                        
                        # Create list item
                        item = QListWidgetItem(f"Color {idx}: RGB({r}, {g}, {b})")
                        
                        # Set background color
                        item.setBackground(QColor(r, g, b))
                        
                        # Set text color for better visibility
                        brightness = (r * 299 + g * 587 + b * 114) / 1000
                        text_color = QColor(0, 0, 0) if brightness > 128 else QColor(255, 255, 255)
                        item.setForeground(text_color)
                        
                        self.color_list.addItem(item)
            else:
                QMessageBox.warning(self, "Warning", "The image is not in indexed color mode.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load color palette: {str(e)}")
    
    def edit_color(self, item):
        row = self.color_list.row(item)
        if row < len(self.current_palette):
            idx, old_color = self.current_palette[row]
            
            # Open color dialog
            color = QColorDialog.getColor(QColor(*old_color), self, f"Change Color {idx}")
            
            if color.isValid():
                new_color = (color.red(), color.green(), color.blue())
                self.current_palette[row] = (idx, new_color)
                
                # Update list item
                item.setText(f"Color {idx}: RGB({new_color[0]}, {new_color[1]}, {new_color[2]})")
                item.setBackground(color)
                
                # Set text color for better visibility
                brightness = (new_color[0] * 299 + new_color[1] * 587 + new_color[2] * 114) / 1000
                text_color = QColor(0, 0, 0) if brightness > 128 else QColor(255, 255, 255)
                item.setForeground(text_color)
    
    def toggle_dithering(self, state):
        """Toggle dithering on/off"""
        self.use_dithering = state == Qt.Checked
    
    def get_incremented_filename(self, original_path):
        """
        Generate incremented filename to avoid overwriting existing files
        Returns a path like "name_1.png", "name_2.png", etc.
        """
        dir_name = os.path.dirname(original_path)
        base_name = os.path.basename(original_path)
        name, ext = os.path.splitext(base_name)
        
        # Extract the original name without any existing numbering
        if "_" in name:
            parts = name.split("_")
            # Check if the last part is a number
            if parts[-1].isdigit():
                # Remove the number part
                name = "_".join(parts[:-1])
        
        # Get the current count for this base filename
        if name not in self.saved_version_count:
            self.saved_version_count[name] = 0
        
        # Increment the counter
        self.saved_version_count[name] += 1
        count = self.saved_version_count[name]
        
        # Create new filename with incremented number
        new_filename = f"{name}_{count}{ext}"
        return os.path.join(dir_name, new_filename)
    
    def render_with_new_colors(self):
        if not self.current_indexed_image_path or not self.current_palette:
            return
            
        # Prepare color mapping dictionary
        color_mapping = {idx: color for idx, color in self.current_palette}
        
        # Generate an incremented output path
        dir_name = os.path.dirname(self.current_indexed_image_path)
        basename = os.path.basename(self.current_indexed_image_path)
        name, ext = os.path.splitext(basename)
        base_output_path = os.path.join(dir_name, f"{name}{ext}")
        output_path = self.get_incremented_filename(base_output_path)
        
        # Get upscale factor
        upscale_factor = self.upscale_factor_spin.value() 
        if upscale_factor <= 1.0:
            upscale_factor = None
        
        # Get upscale and downscale methods
        upscale_method = self.upscale_method_combo.currentText()
        downscale_method = self.downscale_method_combo.currentText()
        
        # Get dithering states
        dithering_state = self.dithering_checkbox.isChecked()
        upscale_dithering = self.upscale_dithering_checkbox.isChecked()
        
        print(f"Render with new colors - Dithering: {dithering_state}, Upscale Method: {upscale_method}, Downscale Method: {downscale_method}, Upscale Dithering: {upscale_dithering}")
        
        # Disable button while processing
        self.render_btn.setEnabled(False)
        self.single_progress.setValue(0)
        
        try:
            # Setup thread with new options
            self.color_editor = ColorEditorThread(
                self.current_indexed_image_path, 
                output_path, 
                color_mapping,
                use_dithering=dithering_state,
                upscale_factor=upscale_factor,
                upscale_method=upscale_method,
                upscale_dithering=upscale_dithering,
                downscale_method=downscale_method
            )
            self.color_editor.progress_updated.connect(self.single_progress.setValue)
            self.color_editor.processing_complete.connect(self.on_recolor_complete)
            
            # Start processing
            self.color_editor.start()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error starting color editor: {str(e)}")
            self.render_btn.setEnabled(True)
            print(f"Error in render_with_new_colors: {str(e)}")
    
    def on_recolor_complete(self, result):
        if os.path.isfile(result):
            self.current_indexed_image_path = result
            self.load_image_preview(result, self.indexed_image_label)
            QMessageBox.information(self, "Success", f"Image recolored and saved to:\n{result}")
        else:
            QMessageBox.critical(self, "Error", result)
            
        self.render_btn.setEnabled(True)
    
    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        
        if folder_path:
            self.folder_path_edit.setText(folder_path)
            self.process_batch_btn.setEnabled(True)
    
    def select_output_folder(self):
        """Select output folder for batch processing"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        
        if folder_path:
            self.output_folder_edit.setText(folder_path)
            
    def process_batch(self):
        folder_path = self.folder_path_edit.text()
        
        if not folder_path or not os.path.isdir(folder_path):
            return
            
        # Get all image files in the folder
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']
        file_paths = []
        
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path) and os.path.splitext(file_path)[1].lower() in image_extensions:
                file_paths.append(file_path)
        
        if not file_paths:
            QMessageBox.warning(self, "Warning", "No image files found in the selected folder.")
            return
            
        # Check if we have a processed single image first
        if not self.current_indexed_image_path or not self.current_palette:
            reply = QMessageBox.question(
                self, 
                "No Reference Image",
                "No single image has been processed to use as a reference. \n"
                "Would you like to process a single image first to ensure consistent results?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                return
        
        # Disable button while processing
        self.process_batch_btn.setEnabled(False)
        self.batch_progress.setValue(0)
        self.results_list.clear()
        
        # Get output folder
        output_folder = self.output_folder_edit.text()
        if not output_folder or not os.path.isdir(output_folder):
            output_folder = folder_path
        
        # Get scaling factors
        downscale_factor = self.downscale_factor_spin.value()
        if downscale_factor >= 1.0:
            downscale_factor = None
            
        # Get upscale factor
        upscale_factor = self.upscale_factor_spin.value() 
        if upscale_factor <= 1.0:
            upscale_factor = None
        
        # Get upscale and downscale methods
        upscale_method = self.upscale_method_combo.currentText()
        downscale_method = self.downscale_method_combo.currentText()
        
        # Store processed files to track progress
        self.batch_processed_files = []
        self.batch_total_files = len(file_paths)
        self.batch_current_file = 0
        
        # Always use the current palette from the single image processing
        self.batch_custom_palette = self.current_palette if self.current_palette else None
        
        # Start the first stage: Convert to indexed PNGs
        self.start_batch_indexing(file_paths, downscale_factor, upscale_factor, 
                                upscale_method, downscale_method, 
                                self.dithering_checkbox.isChecked(), 
                                self.upscale_dithering_checkbox.isChecked(), 
                                output_folder)

    def start_batch_indexing(self, file_paths, downscale_factor, upscale_factor, 
                            upscale_method, downscale_method, 
                            dithering_state, upscale_dithering, 
                            output_folder):
        """First stage of batch processing: Convert images to indexed PNGs"""
        print(f"Starting batch indexing for {len(file_paths)} files")
        
        # Setup processor thread to convert to indexed PNGs
        self.batch_processor = ImageProcessor(
            file_paths, 
            self.num_colors_spin.value(),
            downscale_factor=downscale_factor,
            output_folder=output_folder,
            use_dithering=dithering_state,
            upscale_factor=upscale_factor,
            upscale_method=upscale_method,
            upscale_dithering=upscale_dithering,
            downscale_method=downscale_method
        )
        self.batch_processor.progress_updated.connect(self.batch_progress.setValue)
        self.batch_processor.processing_complete.connect(self.on_batch_indexing_complete)
        
        # Start processing
        self.batch_processor.start()

    def on_batch_indexing_complete(self, processed_files):
        """Callback after converting images to indexed PNGs"""
        print(f"Batch indexing complete. Processed {len(processed_files)} files.")
        
        # Store processed files for next stage
        self.batch_processed_files = processed_files
        
        # If we have a custom palette, start the recoloring stage
        if self.batch_custom_palette:
            self.start_batch_recoloring()
        else:
            # Finish batch processing if no custom palette
            self.finalize_batch_processing()

    def start_batch_recoloring(self):
        """Second stage of batch processing: Apply custom palette to indexed PNGs"""
        print(f"Starting batch recoloring for {len(self.batch_processed_files)} files")
        
        # Reset progress
        self.batch_current_file = 0
        self.batch_progress.setValue(0)
        
        # Prepare color mapping dictionary
        color_mapping = {idx: color for idx, color in self.batch_custom_palette}
        
        # Setup threads for each file
        self.batch_color_threads = []
        self.indexed_files_to_delete = [] # Track files to delete after recoloring
        
        for input_path in self.batch_processed_files:
            # Prepare output path with the new naming scheme
            dir_name = os.path.dirname(input_path)
            basename = os.path.basename(input_path)
            name, ext = os.path.splitext(basename)
            
            # Remove "_indexed" suffix if it exists
            if name.endswith("_indexed"):
                name = name[:-8]  # Remove "_indexed"
                
            # Generate proper incremental filename
            base_output_path = os.path.join(dir_name, f"{name}{ext}")
            output_path = self.get_incremented_filename(base_output_path)
            
            # Keep track of the indexed file to delete later
            self.indexed_files_to_delete.append(input_path)
            
            # Create color editor thread
            color_thread = ColorEditorThread(
                input_path, 
                output_path, 
                color_mapping,
                use_dithering=self.dithering_checkbox.isChecked(),
                upscale_factor=self.upscale_factor_spin.value() if self.upscale_factor_spin.value() > 1.0 else None,
                upscale_method=self.upscale_method_combo.currentText(),
                upscale_dithering=self.upscale_dithering_checkbox.isChecked(),
                downscale_method=self.downscale_method_combo.currentText()
            )
            
            # Connect signals
            color_thread.processing_complete.connect(self.on_batch_recolor_file_complete)
            
            # Store and start thread
            self.batch_color_threads.append(color_thread)
            color_thread.start()

    def on_batch_recolor_file_complete(self, result):
        """Callback for each completed recoloring thread"""
        self.batch_current_file += 1
        
        # Update progress
        progress = int((self.batch_current_file / self.batch_total_files) * 100)
        self.batch_progress.setValue(progress)
        
        # Add to results list if successful
        if os.path.isfile(result):
            self.results_list.addItem(result)
        
        # Check if all files are processed
        if self.batch_current_file >= self.batch_total_files:
            self.finalize_batch_processing()

    def finalize_batch_processing(self):
        """Final cleanup after batch processing"""
        # Delete the indexed files if recoloring was done
        if hasattr(self, 'indexed_files_to_delete') and self.indexed_files_to_delete:
            for file_path in self.indexed_files_to_delete:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Deleted intermediate file: {file_path}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
        
        # Show completion message
        QMessageBox.information(
            self, 
            "Batch Processing Complete", 
            f"Successfully processed {self.batch_current_file} images."
        )
        
        # Re-enable the process button
        self.process_batch_btn.setEnabled(True)
        
        # Clear temporary storage
        self.batch_processed_files = []
        self.batch_color_threads = []
        if hasattr(self, 'indexed_files_to_delete'):
            self.indexed_files_to_delete = []

def main():
    app = QApplication(sys.argv)
    window = IndexedColorConverter()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
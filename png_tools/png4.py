import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QFileDialog, QSpinBox, QColorDialog,
                           QListWidget, QListWidgetItem, QGridLayout, QLineEdit,
                           QProgressBar, QMessageBox, QScrollArea, QCheckBox, QComboBox,
                           QGroupBox, QFrame)
from PyQt5.QtGui import QPixmap, QImage, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import threading
from PIL import Image as PILImage  # Renamed to avoid namespace conflicts
from palette_processor import ConsistentPaletteProcessor, patch_indexed_color_converter
import numpy as np

class ImageProcessor(QThread):
    progress_updated = pyqtSignal(int)
    processing_complete = pyqtSignal(list)
    
    def __init__(self, file_paths, num_colors, max_size=None, max_length=None, output_folder=None, 
                 custom_palette=None, use_dithering=True, upscale_size=None, upscale_method="NEAREST", 
                 upscale_dithering=False, downscale_method="LANCZOS"):
        super().__init__()
        self.file_paths = file_paths
        self.num_colors = num_colors
        self.max_size = max_size
        self.max_length = max_length
        self.output_folder = output_folder
        self.custom_palette = custom_palette
        # Store dithering as boolean - we'll convert to int only when passing to quantize
        self.use_dithering = use_dithering
        self.upscale_size = upscale_size
        self.upscale_method = upscale_method
        self.upscale_dithering = upscale_dithering
        self.downscale_method = downscale_method
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
    def generate_standard_palette(self, img):
        """Generate a standard palette using the two-step process"""
        # Step 1: Generate a palette without dithering
        print("Generating a palette without dithering first...")
        palette_img = img.quantize(colors=self.num_colors, dither=0)
        
        # Extract palette data
        palette_data = palette_img.getpalette()
        
        # Find used colors
        img_array = np.array(palette_img)
        unique_indices = np.unique(img_array)
        print(f"Found {len(unique_indices)} unique colors in use")
        
        # Create a new palette image
        new_palette_img = PILImage.new('P', (1, 1))
        new_palette_data = []
        
        # Flatten the palette data for used colors
        for idx in unique_indices:
            r = palette_data[idx*3]
            g = palette_data[idx*3 + 1]
            b = palette_data[idx*3 + 2]
            new_palette_data.extend([r, g, b])
        
        # Fill the rest of the palette with zeros
        remaining_colors = 256 - len(unique_indices)
        new_palette_data.extend([0] * (remaining_colors * 3))
        
        # Set the palette
        new_palette_img.putpalette(new_palette_data)
        
        # Step 2: Apply the palette with dithering
        dither_value = 1 if self.use_dithering else 0
        print(f"Applying quantize with generated palette, dither={dither_value}")
        return img.quantize(colors=len(unique_indices), palette=new_palette_img, dither=dither_value)
    
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
                
                # Resize if max_size is specified (this handles the "longest side" constraint)
                if self.max_size:
                    width, height = img.size
                    if width > height:
                        if width > self.max_size:
                            new_width = self.max_size
                            new_height = int(height * (self.max_size / width))
                            img = img.resize((new_width, new_height), downscale_method)
                    else:
                        if height > self.max_size:
                            new_height = self.max_size
                            new_width = int(width * (self.max_size / height))
                            img = img.resize((new_width, new_height), downscale_method)
                            
                # Resize if max_length is specified (this handles the "fixed length" constraint)
                if self.max_length:
                    width, height = img.size
                    # Calculate new dimensions while maintaining aspect ratio
                    aspect_ratio = width / height
                    if aspect_ratio >= 1:  # Landscape or square
                        new_width = self.max_length
                        new_height = int(new_width / aspect_ratio)
                    else:  # Portrait
                        new_height = self.max_length
                        new_width = int(new_height * aspect_ratio)
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
                if self.upscale_size:
                    # Calculate dimensions for upscaling
                    current_width, current_height = img_indexed.size
                    scale_factor = self.upscale_size / max(current_width, current_height)
                    upscale_width = int(current_width * scale_factor)
                    upscale_height = int(current_height * scale_factor)
                    
                    # Select upscale method
                    upscale_method = getattr(PILImage, self.upscale_method)

                    # If upscale dithering is enabled, convert to RGB, upscale, and then re-index
                    if self.upscale_dithering and img_indexed.mode == 'P':
                        # Get the palette data for reuse
                        original_palette = img_indexed.getpalette()
                        
                        # Convert to RGB for better interpolation
                        rgb_img = img_indexed.convert('RGB')
                        
                        # Upscale using selected method
                        upscaled_rgb = rgb_img.resize((upscale_width, upscale_height), upscale_method)
                        
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
                        img_indexed = img_indexed.resize((upscale_width, upscale_height), upscale_method)
                
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
    preview_ready = pyqtSignal(QImage)
    
    def __init__(self, input_path, output_path, color_mapping, preview_only=False, use_dithering=True, 
                 upscale_size=None, upscale_method="NEAREST", upscale_dithering=False, downscale_method="LANCZOS"):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.color_mapping = color_mapping
        self.preview_only = preview_only
        # Convert boolean to integer for consistency
        self.use_dithering = 1 if use_dithering else 0
        self.upscale_size = upscale_size
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
            if self.upscale_size:
                # Calculate dimensions for upscaling
                current_width, current_height = new_img.size
                scale_factor = self.upscale_size / max(current_width, current_height)
                upscale_width = int(current_width * scale_factor)
                upscale_height = int(current_height * scale_factor)
                
                # Select upscale method
                upscale_method = getattr(PILImage, self.upscale_method)
                
                # If upscale dithering is enabled, convert to RGB, upscale, and then re-index
                if self.upscale_dithering and new_img.mode == 'P':
                    # Store the palette for reuse
                    original_palette = new_img.getpalette()
                    
                    # Convert to RGB for better interpolation
                    rgb_img = new_img.convert('RGB')
                    
                    # Upscale using selected method
                    upscaled_rgb = rgb_img.resize((upscale_width, upscale_height), upscale_method)
                    
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
                    new_img = new_img.resize((upscale_width, upscale_height), upscale_method)
            
            # If we're just generating a preview
            if self.preview_only:
                try:
                    # Convert PIL image to QImage for preview
                    if new_img.mode == 'P':
                        # Convert to RGB for QImage compatibility
                        new_img = new_img.convert('RGB')
                    
                    # Get the image data
                    img_data = new_img.tobytes("raw", "RGB")
                    
                    # Create a QImage with the correct dimensions
                    width, height = new_img.size
                    qimg = QImage(img_data, width, height, width * 3, QImage.Format_RGB888)
                    
                    if not qimg.isNull():
                        self.preview_ready.emit(qimg)
                        self.progress_updated.emit(100)
                        self.processing_complete.emit("Preview generated")
                    else:
                        print("Warning: Generated QImage is null")
                        self.processing_complete.emit("Error: Generated null image")
                except Exception as e:
                    print(f"Preview conversion error: {str(e)}")
                    self.processing_complete.emit(f"Preview error: {str(e)}")
                return
            
            # Save the image if not preview only
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
        
        # Downscale pixel length
        settings_layout.addWidget(QLabel("Downscale Long Side (px):"), 1, 0)
        self.pixel_length_spin = QSpinBox()
        self.pixel_length_spin.setRange(0, 10000)
        self.pixel_length_spin.setValue(0)
        self.pixel_length_spin.setSpecialValueText("No Resize")
        settings_layout.addWidget(self.pixel_length_spin, 1, 1)
        
        # Downscale method dropdown
        settings_layout.addWidget(QLabel("Downscale Method:"), 2, 0)
        self.downscale_method_combo = QComboBox()
        self.downscale_method_combo.addItems(["LANCZOS", "BICUBIC", "BILINEAR", "NEAREST"])
        settings_layout.addWidget(self.downscale_method_combo, 2, 1)
        
        # Upscale pixel length
        settings_layout.addWidget(QLabel("Upscale Long Side (px):"), 3, 0)
        self.upscale_length_spin = QSpinBox()
        self.upscale_length_spin.setRange(0, 10000)
        self.upscale_length_spin.setValue(512)
        self.upscale_length_spin.setSpecialValueText("No Upscale")
        settings_layout.addWidget(self.upscale_length_spin, 3, 1)
        
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
        
        # Preview button
        self.preview_btn = QPushButton("Preview Changes")
        self.preview_btn.clicked.connect(self.preview_changes)
        self.preview_btn.setEnabled(False)
        buttons_layout.addWidget(self.preview_btn)
        
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
        
        # Get pixel length for downscale
        pixel_length = self.pixel_length_spin.value()
        if pixel_length == 0:
            pixel_length = None
        
        # Get upscale size
        upscale_size = self.upscale_length_spin.value()
        if upscale_size == 0:
            upscale_size = None
        
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
            max_length=pixel_length,
            use_dithering=use_dithering,
            upscale_size=upscale_size,
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
            self.preview_btn.setEnabled(True)
        
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
                
                # Enable the preview button
                self.preview_btn.setEnabled(True)
    
    def preview_changes(self):
        """Generate a preview of color changes without saving the image"""
        if not self.current_indexed_image_path or not self.current_palette:
            return
        
        # Disable buttons while processing
        self.preview_btn.setEnabled(False)
        self.render_btn.setEnabled(False)
        self.single_progress.setValue(0)
        
        # Prepare color mapping dictionary
        color_mapping = {idx: color for idx, color in self.current_palette}
        
        # Get upscale size
        upscale_size = self.upscale_length_spin.value()
        if upscale_size == 0:
            upscale_size = None
        
        # Get upscale and downscale methods
        upscale_method = self.upscale_method_combo.currentText()
        downscale_method = self.downscale_method_combo.currentText()
        
        # Get dithering states
        dithering_state = self.dithering_checkbox.isChecked()
        upscale_dithering = self.upscale_dithering_checkbox.isChecked()
        
        print(f"Preview changes - Dithering: {dithering_state}, Upscale Method: {upscale_method}, Downscale Method: {downscale_method}, Upscale Dithering: {upscale_dithering}")
        
        try:
            # Setup thread for preview only with new options
            self.color_editor = ColorEditorThread(
                self.current_indexed_image_path, 
                "", # No output path needed for preview
                color_mapping,
                preview_only=True,
                use_dithering=dithering_state,
                upscale_size=upscale_size,
                upscale_method=upscale_method,
                upscale_dithering=upscale_dithering,
                downscale_method=downscale_method
            )
            self.color_editor.progress_updated.connect(self.single_progress.setValue)
            self.color_editor.preview_ready.connect(self.update_preview)
            self.color_editor.processing_complete.connect(self.on_preview_complete)
            
            # Start processing
            self.color_editor.start()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error starting preview: {str(e)}")
            self.preview_btn.setEnabled(True)
            self.render_btn.setEnabled(True)
            print(f"Error in preview_changes: {str(e)}")
    
    def update_preview(self, qimage):
        """Update the preview image label with new image"""
        pixmap = QPixmap.fromImage(qimage)
        
        # Scale down if needed to fit in the label, but preserve the pixelated look
        if pixmap.width() > 400 or pixmap.height() > 300:
            pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.FastTransformation)
            
        self.indexed_image_label.setPixmap(pixmap)
    
    def on_preview_complete(self, result):
        """Handler for preview completion"""
        self.render_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        if result.startswith("Error"):
            print(f"Preview error: {result}")
            # Don't show error to user for previews, just log it
    
    def toggle_dithering(self, state):
        """Toggle dithering on/off"""
        self.use_dithering = state == Qt.Checked
    
    def render_with_new_colors(self):
        if not self.current_indexed_image_path or not self.current_palette:
            return
            
        # Prepare color mapping dictionary
        color_mapping = {idx: color for idx, color in self.current_palette}
        
        # Get output path
        dir_name = os.path.dirname(self.current_indexed_image_path)
        basename = os.path.basename(self.current_indexed_image_path)
        name, ext = os.path.splitext(basename)
        output_path = os.path.join(dir_name, f"{name}_recolored{ext}")
        
        # Get upscale size
        upscale_size = self.upscale_length_spin.value()
        if upscale_size == 0:
            upscale_size = None
        
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
                preview_only=False,
                use_dithering=dithering_state,
                upscale_size=upscale_size,
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
            output_folder = None
        
        # Use settings from the single image interface
        
        # Get max dimension (for downscale)
        pixel_length = self.pixel_length_spin.value()
        if pixel_length == 0:
            pixel_length = None
            
        # Get upscale size
        upscale_size = self.upscale_length_spin.value()
        if upscale_size == 0:
            upscale_size = None
        
        # Get upscale and downscale methods
        upscale_method = self.upscale_method_combo.currentText()
        downscale_method = self.downscale_method_combo.currentText()
        
        # Always use the current palette from the single image processing
        custom_palette = self.current_palette if self.current_palette else None
        
        if custom_palette:
            print(f"Using palette with {len(custom_palette)} colors for batch processing:")
            for idx, color in custom_palette:
                print(f"  Color {idx}: RGB{color}")
        else:
            print("No custom palette available for batch processing")
            
        # Get dithering states
        dithering_state = self.dithering_checkbox.isChecked()
        upscale_dithering = self.upscale_dithering_checkbox.isChecked()
        
        print(f"Batch processing - Using current settings - Dithering: {dithering_state}, Custom Palette: {bool(custom_palette)}")
        print(f"Batch processing - Upscale Method: {upscale_method}, Downscale Method: {downscale_method}, Upscale Dithering: {upscale_dithering}")
            
        # Setup processor thread with settings from single image UI
        self.batch_processor = ImageProcessor(
            file_paths, 
            self.num_colors_spin.value(),
            max_size=pixel_length,
            max_length=None,  # We only use one resize method at a time
            output_folder=output_folder,
            custom_palette=custom_palette,
            use_dithering=dithering_state,
            upscale_size=upscale_size,
            upscale_method=upscale_method,
            upscale_dithering=upscale_dithering,
            downscale_method=downscale_method
        )
        self.batch_processor.progress_updated.connect(self.batch_progress.setValue)
        self.batch_processor.processing_complete.connect(self.on_batch_complete)
        
        # Start processing
        self.batch_processor.start()
    
    def on_batch_complete(self, processed_files):
        # Add processed files to the results list
        for file_path in processed_files:
            self.results_list.addItem(file_path)
            
        # Show completion message
        QMessageBox.information(
            self, 
            "Batch Processing Complete", 
            f"Successfully processed {len(processed_files)} images."
        )
        
        # Re-enable the process button
        self.process_batch_btn.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    window = IndexedColorConverter()
    window = patch_indexed_color_converter(window)  # Apply the patch
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
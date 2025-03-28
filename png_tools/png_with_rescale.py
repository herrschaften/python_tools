import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QFileDialog, QSpinBox, QColorDialog,
                           QListWidget, QListWidgetItem, QTabWidget, QGridLayout, QLineEdit,
                           QProgressBar, QMessageBox, QScrollArea, QCheckBox)
from PyQt5.QtGui import QPixmap, QImage, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
import threading
from PIL import Image
import numpy as np

class ImageProcessor(QThread):
    progress_updated = pyqtSignal(int)
    processing_complete = pyqtSignal(list)
    
    def __init__(self, file_paths, num_colors, max_size=None, max_length=None, output_folder=None, 
                 custom_palette=None, use_dithering=True, upscale_size=None):
        super().__init__()
        self.file_paths = file_paths
        self.num_colors = num_colors
        self.max_size = max_size
        self.max_length = max_length
        self.output_folder = output_folder
        self.custom_palette = custom_palette
        self.use_dithering = use_dithering
        self.upscale_size = upscale_size
        
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
                
                # Process the image
                img = Image.open(file_path)
                
                # Store original dimensions for potential upscaling later
                original_width, original_height = img.size
                
                # Resize if max_size is specified (this handles the "longest side" constraint)
                if self.max_size:
                    width, height = img.size
                    if width > height:
                        if width > self.max_size:
                            new_width = self.max_size
                            new_height = int(height * (self.max_size / width))
                            img = img.resize((new_width, new_height), Image.LANCZOS)
                    else:
                        if height > self.max_size:
                            new_height = self.max_size
                            new_width = int(width * (self.max_size / height))
                            img = img.resize((new_width, new_height), Image.LANCZOS)
                            
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
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert to indexed color mode
                img = img.convert("RGB")
                
                # Use custom palette if provided
                if self.custom_palette:
                    # Create a palette image
                    palette_img = Image.new('P', (1, 1))
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
                    
                    # Convert the image using the custom palette
                    dither_method = Image.FLOYDSTEINBERG if self.use_dithering else Image.NONE
                    img_indexed = img.quantize(colors=len(self.custom_palette), palette=palette_img, dither=dither_method)
                else:
                    # Use automatic palette generation with the specified number of colors
                    dither_method = Image.FLOYDSTEINBERG if self.use_dithering else Image.NONE
                    img_indexed = img.quantize(colors=self.num_colors, dither=dither_method)
                
                # Upscale with nearest neighbor if specified
                if self.upscale_size:
                    # Calculate dimensions for upscaling
                    current_width, current_height = img_indexed.size
                    scale_factor = self.upscale_size / max(current_width, current_height)
                    upscale_width = int(current_width * scale_factor)
                    upscale_height = int(current_height * scale_factor)
                    
                    # Upscale using nearest neighbor for that pixelated look
                    img_indexed = img_indexed.resize((upscale_width, upscale_height), Image.NEAREST)
                
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
    
    def __init__(self, input_path, output_path, color_mapping, preview_only=False, use_dithering=True, upscale_size=None):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.color_mapping = color_mapping
        self.preview_only = preview_only
        self.use_dithering = use_dithering
        self.upscale_size = upscale_size
        
    def run(self):
        try:
            # Disable PIL's warning temporarily
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            
            # Open the image - make sure to use a copy to avoid modifying the original
            with Image.open(self.input_path) as original_img:
                img = original_img.copy()
            
            # Re-enable warnings
            warnings.resetwarnings()
            
            # Get the palette
            if img.mode != 'P':
                # If not indexed, convert it
                img = img.convert('P', palette=Image.ADAPTIVE, colors=len(self.color_mapping))
                
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
            
            # Upscale with nearest neighbor if specified
            if self.upscale_size:
                # Calculate dimensions for upscaling
                current_width, current_height = new_img.size
                scale_factor = self.upscale_size / max(current_width, current_height)
                upscale_width = int(current_width * scale_factor)
                upscale_height = int(current_height * scale_factor)
                
                # Upscale using nearest neighbor for that pixelated look
                new_img = new_img.resize((upscale_width, upscale_height), Image.NEAREST)
            
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
        self.setMinimumSize(900, 700)
        
        # Main layout
        self.central_widget = QTabWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create tabs
        self.single_image_tab = QWidget()
        self.batch_tab = QWidget()
        
        self.central_widget.addTab(self.single_image_tab, "Single Image")
        self.central_widget.addTab(self.batch_tab, "Batch Processing")
        
        # Setup the single image tab
        self.setup_single_image_tab()
        
        # Setup the batch tab
        self.setup_batch_tab()
        
        # Initialize state variables
        self.current_image_path = None
        self.current_indexed_image_path = None
        self.current_palette = []
        self.use_dithering = True
        
    def setup_single_image_tab(self):
        layout = QVBoxLayout()
        
        # Top section: Image selection and conversion
        top_layout = QHBoxLayout()
        
        # Left panel for controls
        left_panel = QVBoxLayout()
        
        # Image selection
        self.select_image_btn = QPushButton("Select Image")
        self.select_image_btn.clicked.connect(self.select_single_image)
        left_panel.addWidget(self.select_image_btn)
        
        # Number of colors
        colors_layout = QHBoxLayout()
        colors_layout.addWidget(QLabel("Number of Colors:"))
        self.num_colors_spin = QSpinBox()
        self.num_colors_spin.setRange(2, 256)
        self.num_colors_spin.setValue(16)
        colors_layout.addWidget(self.num_colors_spin)
        left_panel.addLayout(colors_layout)
        
        # Downscale pixel length
        pixel_length_layout = QHBoxLayout()
        pixel_length_layout.addWidget(QLabel("Downscale Long Side (px):"))
        self.pixel_length_spin = QSpinBox()
        self.pixel_length_spin.setRange(0, 10000)
        self.pixel_length_spin.setValue(0)
        self.pixel_length_spin.setSpecialValueText("No Resize")
        pixel_length_layout.addWidget(self.pixel_length_spin)
        left_panel.addLayout(pixel_length_layout)
        
        # Upscale pixel length (new!)
        upscale_layout = QHBoxLayout()
        upscale_layout.addWidget(QLabel("Upscale Long Side (px):"))
        self.upscale_length_spin = QSpinBox()
        self.upscale_length_spin.setRange(0, 10000)
        self.upscale_length_spin.setValue(512)
        self.upscale_length_spin.setSpecialValueText("No Upscale")
        upscale_layout.addWidget(self.upscale_length_spin)
        left_panel.addLayout(upscale_layout)
        
        # Dithering option
        self.dithering_checkbox = QCheckBox("Use Diffusion Dithering")
        self.dithering_checkbox.setChecked(True)
        self.dithering_checkbox.stateChanged.connect(self.toggle_dithering)
        left_panel.addWidget(self.dithering_checkbox)
        
        # Convert button
        self.convert_btn = QPushButton("Convert to Indexed PNG")
        self.convert_btn.clicked.connect(self.convert_single_image)
        self.convert_btn.setEnabled(False)
        left_panel.addWidget(self.convert_btn)
        
        # Progress bar
        self.single_progress = QProgressBar()
        left_panel.addWidget(self.single_progress)
        
        # Save palette for batch button
        self.save_palette_btn = QPushButton("Use This Palette for Batch Processing")
        self.save_palette_btn.clicked.connect(self.save_palette_for_batch)
        self.save_palette_btn.setEnabled(False)
        left_panel.addWidget(self.save_palette_btn)
        
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
        
        layout.addLayout(top_layout)
        
        # Bottom section: Color editing
        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(QLabel("Edit Colors (double-click to change):"))
        
        # Color list
        self.color_list = QListWidget()
        self.color_list.setMinimumHeight(150)
        self.color_list.itemDoubleClicked.connect(self.edit_color)
        bottom_layout.addWidget(self.color_list)
        
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
        
        bottom_layout.addLayout(buttons_layout)
        
        layout.addLayout(bottom_layout)
        
        self.single_image_tab.setLayout(layout)
        
    def setup_batch_tab(self):
        layout = QVBoxLayout()
        
        # Input/Output folder selection
        io_layout = QGridLayout()
        
        # Input folder
        io_layout.addWidget(QLabel("Input Folder:"), 0, 0)
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setReadOnly(True)
        io_layout.addWidget(self.folder_path_edit, 0, 1)
        self.select_folder_btn = QPushButton("Browse...")
        self.select_folder_btn.clicked.connect(self.select_folder)
        io_layout.addWidget(self.select_folder_btn, 0, 2)
        
        # Output folder
        io_layout.addWidget(QLabel("Output Folder:"), 1, 0)
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setReadOnly(True)
        self.output_folder_edit.setPlaceholderText("Same as input folder if not specified")
        io_layout.addWidget(self.output_folder_edit, 1, 1)
        self.select_output_btn = QPushButton("Browse...")
        self.select_output_btn.clicked.connect(self.select_output_folder)
        io_layout.addWidget(self.select_output_btn, 1, 2)
        
        layout.addLayout(io_layout)
        
        # Settings
        settings_layout = QGridLayout()
        
        # Use custom palette
        self.use_custom_palette_checkbox = QCheckBox("Use Custom Palette from Single Image")
        self.use_custom_palette_checkbox.setEnabled(False)
        settings_layout.addWidget(self.use_custom_palette_checkbox, 0, 0, 1, 2)
        
        # Dithering option
        self.batch_dithering_checkbox = QCheckBox("Use Diffusion Dithering")
        self.batch_dithering_checkbox.setChecked(True)
        settings_layout.addWidget(self.batch_dithering_checkbox, 1, 0, 1, 2)
        
        # Number of colors
        settings_layout.addWidget(QLabel("Number of Colors:"), 2, 0)
        self.batch_num_colors_spin = QSpinBox()
        self.batch_num_colors_spin.setRange(2, 256)
        self.batch_num_colors_spin.setValue(16)
        settings_layout.addWidget(self.batch_num_colors_spin, 2, 1)
        
        # Max dimension (longest side) for downscale
        settings_layout.addWidget(QLabel("Downscale Longest Side (px):"), 3, 0)
        self.max_dimension_spin = QSpinBox()
        self.max_dimension_spin.setRange(0, 10000)
        self.max_dimension_spin.setValue(0)
        self.max_dimension_spin.setSpecialValueText("No Downscale")
        settings_layout.addWidget(self.max_dimension_spin, 3, 1)
        
        # Fixed length dimension
        settings_layout.addWidget(QLabel("Fixed Length (px):"), 4, 0)
        self.max_length_spin = QSpinBox()
        self.max_length_spin.setRange(0, 10000)
        self.max_length_spin.setValue(0)
        self.max_length_spin.setSpecialValueText("No Fixed Length")
        settings_layout.addWidget(self.max_length_spin, 4, 1)
        
        # Upscale size (new!)
        settings_layout.addWidget(QLabel("Upscale Longest Side (px):"), 5, 0)
        self.batch_upscale_spin = QSpinBox()
        self.batch_upscale_spin.setRange(0, 10000)
        self.batch_upscale_spin.setValue(512)
        self.batch_upscale_spin.setSpecialValueText("No Upscale")
        settings_layout.addWidget(self.batch_upscale_spin, 5, 1)
        
        layout.addLayout(settings_layout)
        
        # Process button
        self.process_batch_btn = QPushButton("Process Folder")
        self.process_batch_btn.clicked.connect(self.process_batch)
        self.process_batch_btn.setEnabled(False)
        layout.addWidget(self.process_batch_btn)
        
        # Progress bar
        self.batch_progress = QProgressBar()
        layout.addWidget(self.batch_progress)
        
        # Results list
        layout.addWidget(QLabel("Processed Files:"))
        self.results_list = QListWidget()
        layout.addWidget(self.results_list)
        
        self.batch_tab.setLayout(layout)
    
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
        
        # Setup processor thread with dithering option
        self.processor = ImageProcessor(
            [self.current_image_path], 
            self.num_colors_spin.value(),
            max_length=pixel_length,
            use_dithering=self.use_dithering,
            upscale_size=upscale_size
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
            self.save_palette_btn.setEnabled(True)
        
        self.convert_btn.setEnabled(True)
    
    def load_color_palette(self, indexed_image_path):
        try:
            # Clear the list
            self.color_list.clear()
            self.current_palette = []
            
            # Open the image and get its palette
            img = Image.open(indexed_image_path)
            
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
        
        try:
            # Disable PIL's warning temporarily
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            
            # Open the original indexed image
            with Image.open(self.current_indexed_image_path) as img:
                img_copy = img.copy()
                
                # Re-enable warnings
                warnings.resetwarnings()
                
                # Get the palette
                if img_copy.mode != 'P':
                    # If not indexed, convert it
                    img_copy = img_copy.convert('P', palette=Image.ADAPTIVE, colors=len(self.current_palette))
                    
                palette = img_copy.getpalette()
                
                if palette:
                    # Make a copy of the palette for modification
                    new_palette = palette.copy()
                    
                    # Update the palette with new colors
                    for idx, color in self.current_palette:
                        r, g, b = color
                        if idx * 3 + 2 < len(new_palette):
                            new_palette[idx*3] = r
                            new_palette[idx*3 + 1] = g
                            new_palette[idx*3 + 2] = b
                    
                    # Apply the new palette
                    img_copy.putpalette(new_palette)
                    
                    # Apply upscaling if needed
                    upscale_size = self.upscale_length_spin.value()
                    if upscale_size > 0:
                        # Calculate dimensions for upscaling
                        current_width, current_height = img_copy.size
                        scale_factor = upscale_size / max(current_width, current_height)
                        upscale_width = int(current_width * scale_factor)
                        upscale_height = int(current_height * scale_factor)
                        
                        # Upscale using nearest neighbor for that pixelated look
                        img_copy = img_copy.resize((upscale_width, upscale_height), Image.NEAREST)
                    
                    # Convert to RGB for display
                    img_rgb = img_copy.convert('RGB')
                    
                    # Create a temporary file to hold the preview image
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        temp_path = temp_file.name
                        img_rgb.save(temp_path)
                        
                        # Load the preview image
                        pixmap = QPixmap(temp_path)
                        
                        # Scale down if needed to fit in the label, but preserve the pixelated look
                        if pixmap.width() > 400 or pixmap.height() > 300:
                            pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.FastTransformation)
                            
                        self.indexed_image_label.setPixmap(pixmap)
                        
                        # Delete the temporary file
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
            
            self.single_progress.setValue(100)
            
        except Exception as e:
            print(f"Preview error: {str(e)}")
            QMessageBox.warning(self, "Preview Error", f"Could not generate preview: {str(e)}")
        
        # Re-enable buttons
        self.preview_btn.setEnabled(True)
        self.render_btn.setEnabled(True)
    
    def update_preview(self, qimage):
        """Update the preview image label with new image"""
        pixmap = QPixmap.fromImage(qimage)
        
        # Scale down if needed to fit in the label, but preserve the pixelated look
        if pixmap.width() > 400 or pixmap.height() > 300:
            pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.FastTransformation)
            
        self.indexed_image_label.setPixmap(pixmap)
    
    def toggle_dithering(self, state):
        """Toggle dithering on/off"""
        self.use_dithering = state == Qt.Checked
        
    def save_palette_for_batch(self):
        """Save the current palette for use in batch processing"""
        if self.current_palette:
            self.use_custom_palette_checkbox.setEnabled(True)
            self.use_custom_palette_checkbox.setChecked(True)
            QMessageBox.information(
                self, 
                "Palette Saved", 
                "The current palette has been saved for batch processing."
            )
    
    def select_output_folder(self):
        """Select output folder for batch processing"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        
        if folder_path:
            self.output_folder_edit.setText(folder_path)
    
    def render_with_new_colors(self, preview_only=False):
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
        
        # Disable button while processing
        self.render_btn.setEnabled(False)
        self.single_progress.setValue(0)
        
        try:
            # Setup thread
            self.color_editor = ColorEditorThread(
                self.current_indexed_image_path, 
                output_path, 
                color_mapping,
                preview_only=preview_only,
                use_dithering=self.use_dithering,
                upscale_size=upscale_size
            )
            self.color_editor.progress_updated.connect(self.single_progress.setValue)
            
            if preview_only:
                # For preview, use a simpler approach
                self.color_editor.preview_ready.connect(self.update_preview)
                self.color_editor.processing_complete.connect(self.on_preview_complete)
            else:
                # For actual rendering
                self.color_editor.processing_complete.connect(self.on_recolor_complete)
            
            # Start processing
            self.color_editor.start()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error starting color editor: {str(e)}")
            self.render_btn.setEnabled(True)
            print(f"Error in render_with_new_colors: {str(e)}")
    
    def on_preview_complete(self, result):
        """Handler for preview completion"""
        self.render_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        if result.startswith("Error"):
            print(f"Preview error: {result}")
            # Don't show error to user for previews, just log it
    
    def on_recolor_complete(self, result):
        if os.path.isfile(result):
            self.current_indexed_image_path = result
            self.load_image_preview(result, self.indexed_image_label)
            QMessageBox.information(self, "Success", f"Image recolored and saved to:\n{result}")
        else:
            QMessageBox.critical(self, "Error", result)
            
        self.render_btn.setEnabled(True)
    
    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        
        if folder_path:
            self.folder_path_edit.setText(folder_path)
            self.process_batch_btn.setEnabled(True)
    
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
            
        # Disable button while processing
        self.process_batch_btn.setEnabled(False)
        self.batch_progress.setValue(0)
        self.results_list.clear()
        
        # Get output folder
        output_folder = self.output_folder_edit.text()
        if not output_folder or not os.path.isdir(output_folder):
            output_folder = None
        
        # Get max dimension (longest side)
        max_dimension = self.max_dimension_spin.value()
        if max_dimension == 0:
            max_dimension = None
            
        # Get max length (fixed length)
        max_length = self.max_length_spin.value()
        if max_length == 0:
            max_length = None
        
        # Get upscale size
        upscale_size = self.batch_upscale_spin.value()
        if upscale_size == 0:
            upscale_size = None
        
        # Get custom palette if selected
        custom_palette = None
        if self.use_custom_palette_checkbox.isChecked() and self.current_palette:
            custom_palette = self.current_palette
            
        # Get dithering setting
        use_dithering = self.batch_dithering_checkbox.isChecked()
            
        # Setup processor thread
        self.batch_processor = ImageProcessor(
            file_paths, 
            self.batch_num_colors_spin.value(),
            max_size=max_dimension,
            max_length=max_length,
            output_folder=output_folder,
            custom_palette=custom_palette,
            use_dithering=use_dithering,
            upscale_size=upscale_size
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
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
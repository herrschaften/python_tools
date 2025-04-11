import sys
import os
import traceback
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QFileDialog, QSpinBox, QColorDialog,
                           QListWidget, QListWidgetItem, QGridLayout, QLineEdit,
                           QProgressBar, QMessageBox, QScrollArea, QCheckBox, QComboBox,
                           QGroupBox, QFrame)
from PyQt5.QtGui import QPixmap, QImage, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import threading
from PIL import Image as PILImage  # Renamed to avoid namespace conflicts
import numpy as np

class ConsistentPaletteProcessor(QThread):
    """A processor that applies the palette consistently like the ColorEditorThread"""
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
        self.use_dithering = use_dithering
        self.upscale_size = upscale_size
        self.upscale_method = upscale_method
        self.upscale_dithering = upscale_dithering
        self.downscale_method = downscale_method
        print(f"ConsistentPaletteProcessor initialized with dithering: {self.use_dithering}, "
              f"upscale method: {self.upscale_method}, upscale dithering: {self.upscale_dithering}, "
              f"downscale method: {self.downscale_method}")
        
        # Debug custom palette information
        if self.custom_palette:
            print(f"Custom palette provided with {len(self.custom_palette)} colors:")
            for idx, color in self.custom_palette[:5]:  # Print first 5 colors
                print(f"  Color {idx}: RGB{color}")
            if len(self.custom_palette) > 5:
                print(f"  ... and {len(self.custom_palette)-5} more colors")
        else:
            print("No custom palette provided, will generate one during processing")
    
    def apply_palette_directly(self, img, custom_palette):
        """Apply the palette directly, preserving index structure like in color editing"""
        # Prepare the color mapping from our custom palette
        color_mapping = {idx: color for idx, color in custom_palette}
        print(f"Applying palette with {len(color_mapping)} colors directly")
        
        # First quantize to the right number of colors if not already indexed
        if img.mode != 'P':
            print(f"Converting to indexed color mode with {self.num_colors} colors")
            img = img.quantize(colors=self.num_colors, dither=1 if self.use_dithering else 0)
        
        # Get the current palette
        palette = img.getpalette()
        if not palette:
            print("Warning: Image has no palette, creating new palette")
            return self.generate_standard_palette(img)
        
        # Create a modified palette with our colors at the specified indices
        new_palette = palette.copy()
        
        # Fill all entries with gray to prevent black pixels
        for i in range(0, len(new_palette), 3):
            new_palette[i] = 240    # R
            new_palette[i+1] = 240  # G
            new_palette[i+2] = 240  # B
        
        # Apply our custom colors at the specific indices
        for idx, new_color in color_mapping.items():
            if idx * 3 + 2 >= len(new_palette):
                print(f"Warning: Color index {idx} out of range (palette length: {len(new_palette)//3})")
                continue
                
            r, g, b = new_color
            new_palette[idx*3] = r
            new_palette[idx*3 + 1] = g
            new_palette[idx*3 + 2] = b
        
        # Apply the palette directly
        new_img = img.copy()
        new_img.putpalette(new_palette)
        
        # To prevent palette shifts during upscaling
        img_array = np.array(new_img)
        unique_indices = np.unique(img_array)
        print(f"Image uses {len(unique_indices)} unique color indices: {sorted(unique_indices)[:10]}...")
        
        return new_img
    
    def generate_standard_palette(self, img):
        """Generate a standard palette using the two-step process"""
        # Step 1: Generate a palette without dithering
        print("Generating a palette without dithering first...")
        img_rgb = img.convert("RGB")
        palette_img = img_rgb.quantize(colors=self.num_colors, dither=0)
        
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
        
        # Fill the rest of the palette with light gray instead of zeros
        remaining_colors = 256 - len(unique_indices)
        for _ in range(remaining_colors):
            new_palette_data.extend([240, 240, 240])  # Light gray
        
        # Set the palette
        new_palette_img.putpalette(new_palette_data)
        
        # Step 2: Apply the palette with dithering
        dither_value = 1 if self.use_dithering else 0
        print(f"Applying quantize with generated palette, dither={dither_value}")
        return img_rgb.quantize(colors=len(unique_indices), palette=new_palette_img, dither=dither_value)
    
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
                
                # Resize if max_size is specified (handles the "longest side" constraint)
                if self.max_size:
                    width, height = img.size
                    if width > height:
                        if width > self.max_size:
                            new_width = self.max_size
                            new_height = int(height * (self.max_size / width))
                            downscale_method = getattr(PILImage, self.downscale_method)
                            img = img.resize((new_width, new_height), downscale_method)
                    else:
                        if height > self.max_size:
                            new_height = self.max_size
                            new_width = int(width * (self.max_size / height))
                            downscale_method = getattr(PILImage, self.downscale_method)
                            img = img.resize((new_width, new_height), downscale_method)
                
                # Convert to RGB mode for consistent processing
                img = img.convert("RGB")
                
                # Use custom palette if provided
                if self.custom_palette:
                    try:
                        # Use the direct palette application method
                        # First we do a standard quantize for the initial indexed image
                        img_quantized = img.quantize(colors=self.num_colors, dither=1 if self.use_dithering else 0)
                        
                        # Then apply our palette directly like ColorEditorThread does
                        img_indexed = self.apply_palette_directly(img_quantized, self.custom_palette)
                        
                    except Exception as e:
                        print(f"Error applying custom palette: {str(e)}")
                        traceback.print_exc()
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
                            colors=256,  # Use all available colors
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
                traceback.print_exc()
                
        self.processing_complete.emit(processed_files)

# This function patches the IndexedColorConverter class to use the new processor
def patch_indexed_color_converter(app_instance):
    """Patch the process_batch method to use ConsistentPaletteProcessor"""
    original_process_batch = app_instance.process_batch
    
    def patched_process_batch(self):
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
        # Use the new ConsistentPaletteProcessor instead of ImageProcessor
        self.batch_processor = ConsistentPaletteProcessor(
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
    
    # Replace the original method with our patched version
    app_instance.process_batch = patched_process_batch.__get__(app_instance, type(app_instance))
    print("Successfully patched process_batch method to use ConsistentPaletteProcessor")
    
    return app_instance

# Example usage in your main function:
# def main():
#     app = QApplication(sys.argv)
#     window = IndexedColorConverter()
#     window = patch_indexed_color_converter(window) # <-- Add this line
#     window.show()
#     sys.exit(app.exec_())
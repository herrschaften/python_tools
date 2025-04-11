import sys
import numpy as np
from PIL import Image, ImagePalette

def create_gradient_image():
    """
    Create and return a gradient image
    """
    # Create a 400x400 pixel gradient image
    img = Image.new('RGB', (400, 400), color='white')
    
    for x in range(400):
        for y in range(400):
            # Create a multi-color gradient
            r = int(255 * x / 400)  # Red increases from left to right
            g = int(255 * y / 400)  # Green increases from top to bottom
            b = int(255 * (1 - x / 400) * (1 - y / 400))  # Blue decreases diagonally
            
            img.putpixel((x, y), (r, g, b))
    
    return img

def detailed_image_analysis(img):
    """
    Perform a comprehensive analysis of Pillow's color quantization
    """
    # Convert to RGB to ensure consistent processing
    img_rgb = img.convert('RGB')
    
    print("\n=== Image Quantization Analysis ===")
    print(f"Original Image Mode: {img.mode}")
    print(f"Image Size: {img.size}")
    
    # Quantization tests with different parameters
    for num_colors in [2, 4, 8, 16]:
        print(f"\n--- Quantization Test with {num_colors} Colors ---")
        
        # Quantize without dithering
        quantized_img_no_dither = img_rgb.quantize(colors=num_colors, dither=0)
        
        # Analyze palette
        full_palette = quantized_img_no_dither.getpalette()
        
        # Ensure the palette is the full 256 * 3 length
        if full_palette is None:
            print("No palette found!")
            continue
        
        # Pad the palette if it's shorter than 256 * 3
        if len(full_palette) < 256 * 3:
            full_palette.extend([0] * (256 * 3 - len(full_palette)))
        
        print("Palette Colors:")
        used_colors = []
        
        # Analyze unique colors used in the image
        img_array = np.array(quantized_img_no_dither)
        unique_indices = np.unique(img_array)
        
        print("Unique Color Indices Used:", unique_indices)
        print("Number of Unique Color Indices:", len(unique_indices))
        
        print("\nActual Colors Used:")
        for idx in unique_indices:
            r = full_palette[idx*3]
            g = full_palette[idx*3 + 1]
            b = full_palette[idx*3 + 2]
            print(f"Color Index {idx}: RGB({r}, {g}, {b})")
        
        # Save the quantized image
        quantized_img_no_dither.save(f"quantized_{num_colors}_colors.png")

def main():
    # Create gradient image
    gradient_img = create_gradient_image()
    
    # Save the original gradient
    gradient_img.save("original_gradient.png")
    
    # Run analysis on the gradient image
    detailed_image_analysis(gradient_img)

if __name__ == "__main__":
    main()
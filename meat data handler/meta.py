def convert_to_jpeg_if_needed(self, image_path):
    """Convert non-JPEG images to JPEG format for metadata support"""
    try:
        file_ext = image_path.lower()
        
        # If it's already JPEG, no conversion needed
        if file_ext.endswith(('.jpg', '.jpeg')):
            return image_path
        
        # Create new JPEG filename
        base_name = os.path.splitext(image_path)[0]
        jpeg_path = base_name + '.jpg'
        
        # Handle filename conflicts
        counter = 1
        original_jpeg_path = jpeg_path
        while os.path.exists(jpeg_path):
            jpeg_path = f"{base_name}_{counter}.jpg"
            counter += 1
        
        self.log_message(f"  Converting {os.path.basename(image_path)} to JPEG for metadata support...")
        
        # Open and convert to JPEG
        with Image.open(image_path) as img:
            # Handle transparency for PNG/WebP/GIF
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as high-quality JPEG
            img.save(jpeg_path, 'JPEG', quality=95, optimize=True)
        
        # Verify the converted image
        with Image.open(jpeg_path) as test_img:
            test_img.verify()
        
        # Remove the original file
        os.remove(image_path)
        
        self.log_message(f"  ✓ Converted to: {os.path.basename(jpeg_path)}")
        return jpeg_path
        
    except Exception as e:
        self.log_message(f"  ✗ Conversion failed: {str(e)}")
        return image_path  # Return original path if conversion fails

def add_metadata_to_image(self, image_path, source_url, comment):
    """Add custom metadata to image - with automatic JPEG conversion"""
    try:
        # Create a backup copy first
        backup_path = image_path + ".backup"
        import shutil
        shutil.copy2(image_path, backup_path)
        
        # Read the image to verify it's valid
        try:
            with Image.open(image_path) as img:
                # Verify the image can be opened
                img.verify()
        except Exception as verify_error:
            self.log_message(f"⚠ Image verification failed for {os.path.basename(image_path)}: {str(verify_error)}")
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return
        
        # Convert to JPEG if needed for metadata support
        final_image_path = self.convert_to_jpeg_if_needed(image_path)
        
        # Update backup path if conversion happened
        if final_image_path != image_path:
            if os.path.exists(backup_path):
                os.remove(backup_path)  # Remove old backup
            backup_path = final_image_path + ".backup"
            shutil.copy2(final_image_path, backup_path)
        
        # Now add EXIF metadata (we know it's JPEG now)
        try:
            # Try to load existing EXIF
            try:
                exif_dict = piexif.load(final_image_path)
            except:
                # Create new EXIF structure
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            # Add our custom data to EXIF
            metadata_string = f"Source: {source_url}"
            if comment:
                metadata_string += f" | Comment: {comment}"
            
            # Limit metadata string length to avoid EXIF issues
            if len(metadata_string) > 500:
                metadata_string = metadata_string[:497] + "..."
            
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = metadata_string.encode('utf-8')
            
            # Add source URL to ImageDescription
            if len(source_url) > 200:
                source_url_truncated = source_url[:197] + "..."
            else:
                source_url_truncated = source_url
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = source_url_truncated.encode('utf-8')
            
            # Add comment to Artist field if provided
            if comment:
                if len(comment) > 100:
                    comment_truncated = comment[:97] + "..."
                else:
                    comment_truncated = comment
                exif_dict["0th"][piexif.ImageIFD.Artist] = comment_truncated.encode('utf-8')
            
            # Save with new EXIF
            exif_bytes = piexif.dump(exif_dict)
            
            # Re-open and save with metadata
            with Image.open(backup_path) as img:
                img.save(final_image_path, 'JPEG', exif=exif_bytes, quality=95, optimize=False)
            
            # Verify the saved image can be opened
            with Image.open(final_image_path) as test_img:
                test_img.verify()
            
            # Remove backup if successful
            os.remove(backup_path)
            
            conversion_note = " (converted to JPEG)" if final_image_path != image_path else ""
            self.log_message(f"✓ Added metadata to {os.path.basename(final_image_path)}{conversion_note}")
            
        except Exception as exif_error:
            # Restore from backup if EXIF processing failed
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, final_image_path)
                os.remove(backup_path)
            self.log_message(f"⚠ EXIF metadata failed for {os.path.basename(final_image_path)}, image preserved: {str(exif_error)}")
                    
    except Exception as e:
        # Try to restore from backup if it exists
        backup_path = image_path + ".backup"
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, image_path)
                os.remove(backup_path)
                self.log_message(f"⚠ Metadata processing failed for {os.path.basename(image_path)}, image restored from backup")
            except:
                self.log_message(f"✗ Failed to restore {os.path.basename(image_path)} from backup")
        else:
            self.log_message(f"✗ Failed to add metadata to {os.path.basename(image_path)}: {str(e)}")
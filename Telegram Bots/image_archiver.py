#!/usr/bin/env python3
"""
Telegram Historical Image Archiver - Enhanced Version
Archives selected images from your Telegram history with full customization
"""

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, InputMessagesFilterPhotos, Channel, Chat, User
import asyncio
from datetime import datetime
import json
import os

# Configuration - REPLACE WITH YOUR VALUES
API_ID = 25601421  # Replace with your API ID (number from Telegram)
API_HASH = 'e50f1c1c32ee2933ed33222ed8382e51'  # Replace with your API Hash (string from Telegram)
PHONE_NUMBER = '+4917672508751'  # Replace with your phone number (include country code)

# Archive destination - change this to your group name or ID
ARCHIVE_DESTINATION = 'Arch'  # Group name or chat ID where images will be sent

class TelegramImageArchiver:
    def __init__(self):
        self.client = TelegramClient('image_archiver', API_ID, API_HASH)
        self.archived_count = 0
        self.progress_file = 'archive_progress.json'
        self.config_file = 'archive_config.json'
        self.processed_chats = self.load_progress()
        self.config = self.load_config()
    
    def load_progress(self):
        """Load progress to resume interrupted archiving"""
        try:
            with open(self.progress_file, 'r') as f:
                return json.load(f).get('processed_chats', {})
        except FileNotFoundError:
            return {}
    
    def load_config(self):
        """Load archiving configuration"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'included_chats': [],
                'excluded_chats': [],
                'include_private_chats': True,
                'include_groups': True,
                'include_channels': True,
                'include_bots': False,
                'date_filter': None,  # {'after': 'YYYY-MM-DD', 'before': 'YYYY-MM-DD'}
                'last_updated': None
            }
    
    def save_config(self):
        """Save archiving configuration"""
        self.config['last_updated'] = datetime.now().isoformat()
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def save_progress(self):
        """Save archiving progress"""
        with open(self.progress_file, 'w') as f:
            json.dump({
                'processed_chats': self.processed_chats,
                'last_updated': datetime.now().isoformat(),
                'total_archived': self.archived_count
            }, f, indent=2)
    
    def get_chat_type(self, entity):
        """Determine the type of chat"""
        if isinstance(entity, User):
            return 'private' if not entity.bot else 'bot'
        elif isinstance(entity, Chat):
            return 'group'
        elif isinstance(entity, Channel):
            return 'channel' if entity.broadcast else 'supergroup'
        return 'unknown'
    
    def should_include_chat(self, chat_info):
        """Determine if a chat should be included based on configuration"""
        chat_id = str(chat_info['id'])
        chat_type = chat_info['type']
        
        # Check explicit inclusions/exclusions first
        if chat_id in self.config['excluded_chats']:
            return False
        if chat_id in self.config['included_chats']:
            return True
        
        # Check type-based filters
        if chat_type == 'private' and not self.config['include_private_chats']:
            return False
        if chat_type in ['group', 'supergroup'] and not self.config['include_groups']:
            return False
        if chat_type == 'channel' and not self.config['include_channels']:
            return False
        if chat_type == 'bot' and not self.config['include_bots']:
            return False
        
        return True
    
    async def get_all_chats(self):
        """Get all your chats with type information"""
        chats = []
        
        print("📋 Getting all your chats...")
        
        async for dialog in self.client.iter_dialogs():
            entity = dialog.entity
            chat_type = self.get_chat_type(entity)
            
            chat_info = {
                'entity': entity,
                'title': dialog.title,
                'id': dialog.id,
                'type': chat_type,
                'unread_count': dialog.unread_count,
                'last_message_date': dialog.date
            }
            chats.append(chat_info)
        
        print(f"✅ Found {len(chats)} total chats")
        return chats
    
    async def show_chat_selection_menu(self, chats):
        """Interactive menu to select which chats to include/exclude"""
        print("\n" + "="*60)
        print("📂 CHAT SELECTION MENU")
        print("="*60)
        
        # Categorize chats
        categories = {
            'private': [],
            'group': [],
            'supergroup': [],
            'channel': [],
            'bot': []
        }
        
        for chat in chats:
            chat_type = chat['type']
            if chat_type in categories:
                categories[chat_type].append(chat)
        
        # Show current settings
        print(f"\n🔧 Current Settings:")
        print(f"   Private chats: {'✅' if self.config['include_private_chats'] else '❌'}")
        print(f"   Groups: {'✅' if self.config['include_groups'] else '❌'}")
        print(f"   Channels: {'✅' if self.config['include_channels'] else '❌'}")
        print(f"   Bots: {'✅' if self.config['include_bots'] else '❌'}")
        
        while True:
            print(f"\n📋 Options:")
            print("1. Toggle private chats")
            print("2. Toggle groups/supergroups")
            print("3. Toggle channels")
            print("4. Toggle bots")
            print("5. Select specific chats to include")
            print("6. Select specific chats to exclude")
            print("7. Set date filter")
            print("8. Show included chats summary")
            print("9. Continue with current settings")
            print("0. Save settings and exit")
            
            choice = input("\nChoice (0-9): ").strip()
            
            if choice == "1":
                self.config['include_private_chats'] = not self.config['include_private_chats']
                print(f"Private chats: {'✅ Enabled' if self.config['include_private_chats'] else '❌ Disabled'}")
            
            elif choice == "2":
                self.config['include_groups'] = not self.config['include_groups']
                print(f"Groups: {'✅ Enabled' if self.config['include_groups'] else '❌ Disabled'}")
            
            elif choice == "3":
                self.config['include_channels'] = not self.config['include_channels']
                print(f"Channels: {'✅ Enabled' if self.config['include_channels'] else '❌ Disabled'}")
            
            elif choice == "4":
                self.config['include_bots'] = not self.config['include_bots']
                print(f"Bots: {'✅ Enabled' if self.config['include_bots'] else '❌ Disabled'}")
            
            elif choice == "5":
                await self.select_specific_chats(chats, mode='include')
            
            elif choice == "6":
                await self.select_specific_chats(chats, mode='exclude')
            
            elif choice == "7":
                self.set_date_filter()
            
            elif choice == "8":
                self.show_included_summary(chats)
            
            elif choice == "9":
                break
            
            elif choice == "0":
                self.save_config()
                print("💾 Settings saved!")
                return False  # Don't continue with archiving
        
        self.save_config()
        return True
    
    async def select_specific_chats(self, chats, mode='include'):
        """Select specific chats to include or exclude"""
        action = "include" if mode == 'include' else "exclude"
        current_list = self.config['included_chats'] if mode == 'include' else self.config['excluded_chats']
        
        print(f"\n📋 Select chats to {action}:")
        print("Enter chat numbers separated by commas, or 'done' when finished")
        
        # Show chats in pages
        page_size = 20
        total_pages = (len(chats) + page_size - 1) // page_size
        current_page = 0
        
        while True:
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(chats))
            
            print(f"\n--- Page {current_page + 1}/{total_pages} ---")
            for i in range(start_idx, end_idx):
                chat = chats[i]
                status = ""
                if str(chat['id']) in current_list:
                    status = f" [ALREADY {action.upper()}ED]"
                elif str(chat['id']) in (self.config['included_chats'] if mode == 'exclude' else self.config['excluded_chats']):
                    other_action = "INCLUDED" if mode == 'exclude' else "EXCLUDED"
                    status = f" [{other_action}]"
                
                print(f"{i+1:3d}. {chat['title'][:40]} ({chat['type']}){status}")
            
            print(f"\nCommands: numbers (e.g., 1,3,5), 'next', 'prev', 'done'")
            selection = input("Selection: ").strip().lower()
            
            if selection == 'done':
                break
            elif selection == 'next' and current_page < total_pages - 1:
                current_page += 1
            elif selection == 'prev' and current_page > 0:
                current_page -= 1
            else:
                try:
                    # Parse numbers
                    numbers = [int(x.strip()) for x in selection.split(',') if x.strip().isdigit()]
                    for num in numbers:
                        if 1 <= num <= len(chats):
                            chat_id = str(chats[num-1]['id'])
                            if chat_id not in current_list:
                                current_list.append(chat_id)
                                print(f"✅ Added: {chats[num-1]['title']}")
                            else:
                                current_list.remove(chat_id)
                                print(f"❌ Removed: {chats[num-1]['title']}")
                except ValueError:
                    print("❌ Invalid input. Use numbers separated by commas.")
    
    def set_date_filter(self):
        """Set date filter for archiving"""
        print(f"\n📅 Date Filter Settings")
        print("Current filter:", self.config.get('date_filter', 'None'))
        
        print("\n1. No date filter (archive all)")
        print("2. Archive from specific date")
        print("3. Archive until specific date")
        print("4. Archive between dates")
        
        choice = input("Choice (1-4): ").strip()
        
        if choice == "1":
            self.config['date_filter'] = None
            print("✅ Date filter removed")
        
        elif choice == "2":
            date_str = input("Archive from date (YYYY-MM-DD): ").strip()
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                self.config['date_filter'] = {'after': date_str}
                print(f"✅ Will archive images from {date_str} onwards")
            except ValueError:
                print("❌ Invalid date format")
        
        elif choice == "3":
            date_str = input("Archive until date (YYYY-MM-DD): ").strip()
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                self.config['date_filter'] = {'before': date_str}
                print(f"✅ Will archive images until {date_str}")
            except ValueError:
                print("❌ Invalid date format")
        
        elif choice == "4":
            after_date = input("Archive from date (YYYY-MM-DD): ").strip()
            before_date = input("Archive until date (YYYY-MM-DD): ").strip()
            try:
                datetime.strptime(after_date, '%Y-%m-%d')
                datetime.strptime(before_date, '%Y-%m-%d')
                self.config['date_filter'] = {'after': after_date, 'before': before_date}
                print(f"✅ Will archive images between {after_date} and {before_date}")
            except ValueError:
                print("❌ Invalid date format")
    
    def show_included_summary(self, chats):
        """Show summary of what will be included"""
        included_chats = [chat for chat in chats if self.should_include_chat(chat)]
        
        print(f"\n📊 ARCHIVE SUMMARY")
        print(f"Total chats that will be processed: {len(included_chats)}")
        
        # Group by type
        by_type = {}
        for chat in included_chats:
            chat_type = chat['type']
            if chat_type not in by_type:
                by_type[chat_type] = []
            by_type[chat_type].append(chat)
        
        for chat_type, type_chats in by_type.items():
            print(f"  {chat_type.title()}s: {len(type_chats)}")
        
        if self.config.get('date_filter'):
            print(f"Date filter: {self.config['date_filter']}")
    
    def passes_date_filter(self, message_date):
        """Check if message passes date filter"""
        if not self.config.get('date_filter'):
            return True
        
        date_filter = self.config['date_filter']
        msg_date = message_date.date()
        
        if 'after' in date_filter:
            after_date = datetime.strptime(date_filter['after'], '%Y-%m-%d').date()
            if msg_date < after_date:
                return False
        
        if 'before' in date_filter:
            before_date = datetime.strptime(date_filter['before'], '%Y-%m-%d').date()
            if msg_date > before_date:
                return False
        
        return True
    
    async def send_chat_separator(self, chat_title, image_count=None):
        """Send separator message between different chats"""
        separator = "═" * 50
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        if image_count is not None:
            message = f"{separator}\n📸 **{chat_title}** ({image_count} images)\n📅 {date_str}\n{separator}"
        else:
            message = f"{separator}\n📸 **Starting: {chat_title}**\n📅 {date_str}\n{separator}"
        
        await self.client.send_message(ARCHIVE_DESTINATION, message)
    
    async def archive_chat_images(self, chat_info, limit=None):
        """Archive all images from a specific chat"""
        entity = chat_info['entity']
        chat_title = chat_info['title']
        chat_id = str(chat_info['id'])
        
        # Skip if already processed (for resuming)
        if chat_id in self.processed_chats:
            print(f"⏭️  Skipping {chat_title} (already processed)")
            return
        
        print(f"📸 Processing images from: {chat_title}")
        
        try:
            # Send initial separator
            await self.send_chat_separator(chat_title)
            
            # Use takeout for better rate limits when bulk downloading
            async with self.client.takeout(finalize=True) as takeout:
                chat_image_count = 0
                
                # Get only photo messages using filter
                async for message in takeout.iter_messages(
                    entity, 
                    filter=InputMessagesFilterPhotos,
                    limit=limit
                ):
                    try:
                        # Check date filter
                        if not self.passes_date_filter(message.date):
                            continue
                        
                        # Forward the image without extra text
                        await self.client.forward_messages(ARCHIVE_DESTINATION, message)
                        
                        chat_image_count += 1
                        self.archived_count += 1
                        
                        if chat_image_count % 25 == 0:
                            print(f"   📊 Archived {chat_image_count} images from {chat_title}")
                        
                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.1)
                    
                    except Exception as e:
                        print(f"   ❌ Error archiving image: {e}")
                        continue
                
                # Send completion separator with count
                if chat_image_count > 0:
                    completion_msg = f"✅ **Completed: {chat_title}** - {chat_image_count} images archived"
                    await self.client.send_message(ARCHIVE_DESTINATION, completion_msg)
                
                # Mark chat as processed
                self.processed_chats[chat_id] = {
                    'title': chat_title,
                    'images_archived': chat_image_count,
                    'processed_date': datetime.now().isoformat()
                }
                
                print(f"✅ Completed {chat_title}: {chat_image_count} images archived")
                
        except Exception as e:
            print(f"❌ Error processing {chat_title}: {e}")
        
        # Save progress after each chat
        self.save_progress()
    
    async def create_archive_index(self):
        """Create an index of all archived images"""
        index_message = "🖼️ **TELEGRAM IMAGE ARCHIVE COMPLETE**\n\n"
        index_message += f"📊 **Total Images Archived: {self.archived_count}**\n"
        index_message += f"📅 **Archive Completed: {datetime.now().strftime('%Y-%m-%d %H:%M')}**\n\n"
        
        index_message += "📂 **Processed Chats:**\n"
        
        total_chats_with_images = 0
        for chat_id, info in self.processed_chats.items():
            if info['images_archived'] > 0:
                total_chats_with_images += 1
                index_message += f"• {info['title']}: {info['images_archived']} images\n"
        
        index_message += f"\n📈 **Summary:**\n"
        index_message += f"• {total_chats_with_images} chats had images\n"
        index_message += f"• {len(self.processed_chats)} total chats processed\n"
        
        if self.config.get('date_filter'):
            index_message += f"• Date filter applied: {self.config['date_filter']}\n"
        
        await self.client.send_message(ARCHIVE_DESTINATION, index_message)
        print("📋 Archive index sent to archive destination")
    
    async def estimate_archive_size(self):
        """Estimate how many images will be archived"""
        print("🔍 Estimating archive size...")
        
        chats = await self.get_all_chats()
        included_chats = [chat for chat in chats if self.should_include_chat(chat)]
        
        print(f"📊 Will process {len(included_chats)} out of {len(chats)} total chats")
        
        total_estimate = 0
        sample_size = min(5, len(included_chats))
        
        for i, chat_info in enumerate(included_chats[:sample_size]):
            try:
                entity = chat_info['entity']
                count = 0
                async for message in self.client.iter_messages(entity, filter=InputMessagesFilterPhotos, limit=50):
                    if self.passes_date_filter(message.date):
                        count += 1
                
                total_estimate += count
                print(f"   📊 {chat_info['title']}: ~{count} images (sampled)")
                
            except Exception as e:
                print(f"   ❌ Couldn't estimate {chat_info['title']}: {e}")
        
        if sample_size > 0:
            average_per_chat = total_estimate / sample_size
            total_estimated = average_per_chat * len(included_chats)
            print(f"\n📈 Estimated total images: {total_estimated:.0f}")
        
        return total_estimate
    
    async def run_archive(self, estimate_only=False, limit_per_chat=None, configure=True):
        """Run the complete archiving process"""
        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(PHONE_NUMBER)
            await self.client.sign_in(PHONE_NUMBER, input('Enter the code: '))
        
        print("🚀 Telegram Image Archiver Started!")
        print("📱 Connected to Telegram")
        
        # Get all chats first
        chats = await self.get_all_chats()
        
        # Configuration menu
        if configure:
            continue_archiving = await self.show_chat_selection_menu(chats)
            if not continue_archiving:
                return
        
        # Filter chats based on configuration
        included_chats = [chat for chat in chats if self.should_include_chat(chat)]
        
        if estimate_only:
            await self.estimate_archive_size()
            return
        
        print(f"\n🎯 Will process {len(included_chats)} chats")
        confirm = input("Continue with archiving? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Archiving cancelled")
            return
        
        # Verify archive destination exists
        try:
            archive_entity = await self.client.get_entity(ARCHIVE_DESTINATION)
            print(f"📁 Archive destination: {archive_entity.title if hasattr(archive_entity, 'title') else ARCHIVE_DESTINATION}")
        except Exception as e:
            print(f"❌ Cannot access archive destination '{ARCHIVE_DESTINATION}': {e}")
            return
        
        # Create initial archive message
        start_message = f"🗃️ **IMAGE ARCHIVE SESSION STARTED**\n"
        start_message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        start_message += f"🎯 Archiving {len(included_chats)} selected chats\n"
        start_message += f"📊 Estimated images: Processing..."
        await self.client.send_message(ARCHIVE_DESTINATION, start_message)
        
        # Process each included chat
        for i, chat_info in enumerate(included_chats, 1):
            print(f"\n📂 Processing chat {i}/{len(included_chats)}")
            await self.archive_chat_images(chat_info, limit=limit_per_chat)
            
            # Progress update every 10 chats
            if i % 10 == 0:
                progress_msg = f"📊 **Archive Progress**: {i}/{len(included_chats)} chats processed, {self.archived_count} images archived"
                await self.client.send_message(ARCHIVE_DESTINATION, progress_msg)
        
        # Create final index
        await self.create_archive_index()
        
        print(f"\n🎉 ARCHIVING COMPLETE!")
        print(f"📊 Total images archived: {self.archived_count}")
        print(f"📁 Check the '{ARCHIVE_DESTINATION}' group to see your organized archive!")

# Usage
async def main():
    archiver = TelegramImageArchiver()
    
    print("🖼️  Telegram Image Archiver - Enhanced")
    print("=" * 50)
    
    mode = input("Choose mode:\n1. Configure settings and estimate\n2. Start archiving (test - 10 images per chat)\n3. Full archive with configuration\n4. Resume interrupted archive\n5. Quick archive (use existing settings)\nChoice (1-5): ")
    
    if mode == "1":
        await archiver.run_archive(estimate_only=True, configure=True)
    elif mode == "2":
        await archiver.run_archive(limit_per_chat=10, configure=True)
    elif mode == "3":
        await archiver.run_archive(configure=True)
    elif mode == "4":
        await archiver.run_archive(configure=False)
    elif mode == "5":
        await archiver.run_archive(configure=False)
    
    await archiver.client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
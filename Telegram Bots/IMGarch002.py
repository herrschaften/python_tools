#!/usr/bin/env python3
"""
Telegram Image Archiver - GUI Interface (Lambda-Free Version)
Completely eliminates lambda closure issues
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import asyncio
import threading
import json
from datetime import datetime
import os
from functools import partial

# Try to import telethon
try:
    from telethon import TelegramClient
    from telethon.tl.types import MessageMediaPhoto, InputMessagesFilterPhotos, Channel, Chat, User
except ImportError:
    print("Error: Please install telethon with: pip install telethon")
    exit(1)

# Configuration
API_ID = 25601421
API_HASH = 'e50f1c1c32ee2933ed33222ed8382e51'
PHONE_NUMBER = '+4917672508751'
ARCHIVE_DESTINATION = 'Arch'

class TelegramArchiverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Image Archiver")
        self.root.geometry("1200x800")
        
        # Initialize variables
        self.client = None
        self.chats = []
        self.config = self.load_config()
        self.is_connected = False
        self.archive_running = False
        self.client_loop = None  # Store the event loop used for connection
        
        # UI Variables
        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="all")
        self.status_var = tk.StringVar(value="Ready to connect...")
        
        self.create_ui()
        
    def load_config(self):
        """Load configuration from file"""
        try:
            with open('archive_config_gui.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'included_chats': [],
                'excluded_chats': [],
                'include_private_chats': True,
                'include_groups': True,
                'include_channels': True,
                'include_bots': False,
                'date_filter': None,
                'archive_destination': ARCHIVE_DESTINATION
            }
    
    def save_config(self):
        """Save configuration to file"""
        self.config['last_updated'] = datetime.now().isoformat()
        with open('archive_config_gui.json', 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def thread_safe_update(self, method, *args):
        """Thread-safe UI update without lambdas"""
        self.root.after(0, method, *args)
    
    def update_status(self, message):
        """Update status bar"""
        self.status_var.set(message)
    
    def show_error(self, title, message):
        """Show error dialog"""
        messagebox.showerror(title, message)
    
    def show_info(self, title, message):
        """Show info dialog"""
        messagebox.showinfo(title, message)
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        full_message = f"[{timestamp}] {message}\n"
        self.log_text.insert('end', full_message)
        self.log_text.see('end')
        self.root.update_idletasks()
    
    def enable_connect_button(self):
        """Enable connect button"""
        self.connect_btn.config(state='normal')
    
    def disable_connect_button(self):
        """Disable connect button"""
        self.connect_btn.config(state='disabled')
    
    def enable_start_button(self):
        """Enable start button"""
        self.start_btn.config(state='normal')
    
    def disable_start_button(self):
        """Disable start button"""
        self.start_btn.config(state='disabled')
    
    def enable_stop_button(self):
        """Enable stop button"""
        self.stop_btn.config(state='normal')
    
    def disable_stop_button(self):
        """Disable stop button"""
        self.stop_btn.config(state='disabled')
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_var.set(value)
    
    def update_progress_text(self, text):
        """Update progress text"""
        self.progress_text_var.set(text)
    
    def update_archive_summary(self, text):
        """Update archive summary"""
        self.archive_summary_var.set(text)
    
    def create_ui(self):
        """Create the main UI"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Connection
        self.connection_frame = ttk.Frame(notebook)
        notebook.add(self.connection_frame, text="🔗 Connection")
        self.create_connection_tab()
        
        # Tab 2: Chat Selection
        self.selection_frame = ttk.Frame(notebook)
        notebook.add(self.selection_frame, text="📋 Chat Selection")
        self.create_selection_tab()
        
        # Tab 3: Run Archive
        self.run_frame = ttk.Frame(notebook)
        notebook.add(self.run_frame, text="🚀 Run Archive")
        self.create_run_tab()
        
        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill='x', padx=10, pady=(0, 10))
        ttk.Label(status_frame, textvariable=self.status_var).pack(side='left')
        
    def create_connection_tab(self):
        """Create connection tab"""
        # Connection section
        conn_group = ttk.LabelFrame(self.connection_frame, text="Telegram Connection", padding=10)
        conn_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(conn_group, text="API ID:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.api_id_var = tk.StringVar(value=str(API_ID))
        ttk.Entry(conn_group, textvariable=self.api_id_var, width=20).grid(row=0, column=1, sticky='w')
        
        ttk.Label(conn_group, text="API Hash:").grid(row=1, column=0, sticky='w', padx=(0, 10))
        self.api_hash_var = tk.StringVar(value=API_HASH)
        ttk.Entry(conn_group, textvariable=self.api_hash_var, width=40, show="*").grid(row=1, column=1, sticky='w')
        
        ttk.Label(conn_group, text="Phone:").grid(row=2, column=0, sticky='w', padx=(0, 10))
        self.phone_var = tk.StringVar(value=PHONE_NUMBER)
        ttk.Entry(conn_group, textvariable=self.phone_var, width=20).grid(row=2, column=1, sticky='w')
        
        self.connect_btn = ttk.Button(conn_group, text="Connect to Telegram", command=self.connect_telegram)
        self.connect_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Archive destination
        dest_group = ttk.LabelFrame(self.connection_frame, text="Archive Destination", padding=10)
        dest_group.pack(fill='x', pady=(0, 10))
        
        ttk.Label(dest_group, text="Group/Chat Name:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.dest_var = tk.StringVar(value=self.config.get('archive_destination', ARCHIVE_DESTINATION))
        ttk.Entry(dest_group, textvariable=self.dest_var, width=30).grid(row=0, column=1, sticky='w')
        
        # Global filters
        filter_group = ttk.LabelFrame(self.connection_frame, text="Chat Type Filters", padding=10)
        filter_group.pack(fill='x')
        
        self.private_var = tk.BooleanVar(value=self.config.get('include_private_chats', True))
        self.group_var = tk.BooleanVar(value=self.config.get('include_groups', True))
        self.supergroup_var = tk.BooleanVar(value=self.config.get('include_supergroups', True))
        self.channel_var = tk.BooleanVar(value=self.config.get('include_channels', True))
        self.bot_var = tk.BooleanVar(value=self.config.get('include_bots', False))
        
        ttk.Checkbutton(filter_group, text="Private Chats", variable=self.private_var).grid(row=0, column=0, sticky='w')
        ttk.Checkbutton(filter_group, text="Groups", variable=self.group_var).grid(row=0, column=1, sticky='w')
        ttk.Checkbutton(filter_group, text="Supergroups", variable=self.supergroup_var).grid(row=0, column=2, sticky='w')
        ttk.Checkbutton(filter_group, text="Channels", variable=self.channel_var).grid(row=1, column=0, sticky='w')
        ttk.Checkbutton(filter_group, text="Bots", variable=self.bot_var).grid(row=1, column=1, sticky='w')
        
        # Test mode
        test_group = ttk.LabelFrame(self.connection_frame, text="Test Mode", padding=10)
        test_group.pack(fill='x', pady=(10, 0))
        
        self.test_mode_var = tk.BooleanVar()
        ttk.Checkbutton(test_group, text="Test Mode (10 images per chat only)", variable=self.test_mode_var).pack(anchor='w')
        
    def create_selection_tab(self):
        """Create chat selection tab"""
        # Search controls
        control_frame = ttk.Frame(self.selection_frame)
        control_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(control_frame, text="Search:").pack(side='left', padx=(0, 5))
        search_entry = ttk.Entry(control_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side='left', padx=(0, 10))
        search_entry.bind('<KeyRelease>', self.filter_chats)
        
        ttk.Label(control_frame, text="Filter:").pack(side='left', padx=(10, 5))
        filter_combo = ttk.Combobox(control_frame, textvariable=self.filter_var, width=15, state='readonly')
        filter_combo['values'] = ('all', 'private', 'group', 'supergroup', 'channel', 'bot', 'included', 'excluded')
        filter_combo.pack(side='left', padx=(0, 10))
        filter_combo.bind('<<ComboboxSelected>>', self.filter_chats)
        
        # Bulk actions
        action_frame = ttk.Frame(control_frame)
        action_frame.pack(side='right')
        
        ttk.Button(action_frame, text="Include All Visible", command=self.include_all_visible).pack(side='left', padx=2)
        ttk.Button(action_frame, text="Exclude All Visible", command=self.exclude_all_visible).pack(side='left', padx=2)
        ttk.Button(action_frame, text="Clear All Visible", command=self.clear_all_visible).pack(side='left', padx=2)
        
        # Chat list
        list_frame = ttk.Frame(self.selection_frame)
        list_frame.pack(fill='both', expand=True)
        
        self.chat_tree = ttk.Treeview(list_frame, columns=('type', 'status', 'last_msg'), show='tree headings', height=20)
        self.chat_tree.heading('#0', text='Chat Name')
        self.chat_tree.heading('type', text='Type')
        self.chat_tree.heading('status', text='Status')
        self.chat_tree.heading('last_msg', text='Last Message')
        
        self.chat_tree.column('#0', width=300)
        self.chat_tree.column('type', width=100)
        self.chat_tree.column('status', width=100)
        self.chat_tree.column('last_msg', width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.chat_tree.yview)
        self.chat_tree.configure(yscrollcommand=scrollbar.set)
        
        self.chat_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Double-click to toggle
        self.chat_tree.bind('<Double-1>', self.toggle_chat_status)
        
        # Right-click context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="✅ Include", command=lambda: self.set_single_chat_status('include'))
        self.context_menu.add_command(label="❌ Exclude", command=lambda: self.set_single_chat_status('exclude'))
        self.context_menu.add_command(label="🔄 Auto (Clear)", command=lambda: self.set_single_chat_status('clear'))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copy Chat Name", command=self.copy_chat_name)
        
        self.chat_tree.bind('<Button-3>', self.show_context_menu)  # Right click
        self.chat_tree.bind('<Control-Button-1>', self.show_context_menu)  # Ctrl+click for Mac
        
        # Summary
        summary_frame = ttk.LabelFrame(self.selection_frame, text="Selection Summary", padding=10)
        summary_frame.pack(fill='x', pady=(10, 0))
        
        self.summary_var = tk.StringVar(value="Connect to Telegram to see chats")
        ttk.Label(summary_frame, textvariable=self.summary_var, wraplength=800).pack()
        
    def create_run_tab(self):
        """Create run archive tab"""
        # Summary
        summary_group = ttk.LabelFrame(self.run_frame, text="Archive Summary", padding=10)
        summary_group.pack(fill='x', pady=(0, 10))
        
        self.archive_summary_var = tk.StringVar(value="Configure settings and connect to see summary")
        ttk.Label(summary_group, textvariable=self.archive_summary_var, wraplength=800).pack()
        
        ttk.Button(summary_group, text="🔍 Estimate Archive Size", command=self.estimate_archive).pack(pady=5)
        ttk.Button(summary_group, text="📋 List My Groups", command=self.list_groups).pack(pady=5)
        
        # Progress
        progress_group = ttk.LabelFrame(self.run_frame, text="Archive Progress", padding=10)
        progress_group.pack(fill='both', expand=True, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_group, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', pady=(0, 10))
        
        self.progress_text_var = tk.StringVar(value="Ready to start archiving")
        ttk.Label(progress_group, textvariable=self.progress_text_var).pack()
        
        # Log
        log_frame = ttk.Frame(progress_group)
        log_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        self.log_text = tk.Text(log_frame, height=10, wrap='word')
        log_scroll = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scroll.pack(side='right', fill='y')
        
        # Buttons
        button_frame = ttk.Frame(self.run_frame)
        button_frame.pack(fill='x')
        
        self.start_btn = ttk.Button(button_frame, text="🚀 Start Archive", command=self.start_archive)
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="⏹️ Stop Archive", command=self.stop_archive, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="📋 Clear Log", command=self.clear_log).pack(side='left', padx=5)
        ttk.Button(button_frame, text="💾 Save Settings", command=self.save_settings).pack(side='right', padx=5)
        
    def connect_telegram(self):
        """Connect to Telegram"""
        if self.is_connected:
            self.show_info("Info", "Already connected!")
            return
            
        def connect_worker():
            try:
                # Update UI in thread-safe way
                self.thread_safe_update(self.update_status, "Connecting to Telegram...")
                self.thread_safe_update(self.disable_connect_button)
                
                api_id = int(self.api_id_var.get())
                api_hash = self.api_hash_var.get()
                phone = self.phone_var.get()
                
                # Create and store the event loop
                self.client_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.client_loop)
                
                self.client = TelegramClient('telegram_archiver_gui', api_id, api_hash)
                self.client_loop.run_until_complete(self.client.connect())
                
                if not self.client_loop.run_until_complete(self.client.is_user_authorized()):
                    self.thread_safe_update(self.update_status, "Verification code sent to your Telegram")
                    self.client_loop.run_until_complete(self.client.send_code_request(phone))
                    
                    # Ask for code in main thread
                    def ask_for_code():
                        return simpledialog.askstring("Verification", "Enter the code from Telegram:")
                    
                    code = None
                    def get_code():
                        nonlocal code
                        code = ask_for_code()
                    
                    self.thread_safe_update(get_code)
                    
                    # Wait for code
                    import time
                    while code is None:
                        time.sleep(0.1)
                    
                    if code:
                        self.client_loop.run_until_complete(self.client.sign_in(phone, code))
                
                # Load chats
                self.thread_safe_update(self.update_status, "Loading chats...")
                chats = []
                
                async def load_chats():
                    async for dialog in self.client.iter_dialogs():
                        entity = dialog.entity
                        chat_type = self.get_chat_type(entity)
                        
                        chat_info = {
                            'entity': entity,
                            'title': dialog.title,
                            'id': dialog.id,
                            'type': chat_type,
                            'last_message_date': dialog.date.strftime('%Y-%m-%d') if dialog.date else 'Unknown'
                        }
                        chats.append(chat_info)
                    return chats
                
                self.chats = self.client_loop.run_until_complete(load_chats())
                
                # Update UI
                self.thread_safe_update(self.populate_chat_list)
                status_message = f"Connected! Found {len(self.chats)} chats"
                self.thread_safe_update(self.update_status, status_message)
                self.is_connected = True
                
            except Exception as ex:
                error_message = str(ex)
                connection_error = f"Connection failed: {error_message}"
                self.thread_safe_update(self.show_error, "Error", connection_error)
                self.thread_safe_update(self.update_status, "Connection failed")
            finally:
                self.thread_safe_update(self.enable_connect_button)
        
        thread = threading.Thread(target=connect_worker)
        thread.daemon = True
        thread.start()
    
    def get_chat_type(self, entity):
        """Get chat type"""
        if isinstance(entity, User):
            return 'bot' if entity.bot else 'private'
        elif isinstance(entity, Chat):
            return 'group'
        elif isinstance(entity, Channel):
            return 'channel' if entity.broadcast else 'supergroup'
        return 'unknown'
    
    def populate_chat_list(self):
        """Populate the chat list"""
        for item in self.chat_tree.get_children():
            self.chat_tree.delete(item)
        
        for chat in self.chats:
            chat_id = str(chat['id'])
            status = self.get_chat_selection_status(chat_id)
            
            tags = []
            if status == 'include':
                tags = ['included']
            elif status == 'exclude':
                tags = ['excluded']
            
            self.chat_tree.insert('', 'end', 
                                text=chat['title'],
                                values=(chat['type'], status or 'auto', chat['last_message_date']),
                                tags=tags)
        
        self.chat_tree.tag_configure('included', background='#d4edda')
        self.chat_tree.tag_configure('excluded', background='#f8d7da')
        
        self.filter_chats()
        self.update_summary()
    
    def get_chat_selection_status(self, chat_id):
        """Get selection status"""
        if chat_id in self.config.get('included_chats', []):
            return 'include'
        elif chat_id in self.config.get('excluded_chats', []):
            return 'exclude'
        return None
    
    def filter_chats(self, event=None):
        """Filter chats"""
        search_term = self.search_var.get().lower()
        filter_type = self.filter_var.get()
        
        for item in self.chat_tree.get_children():
            chat_name = self.chat_tree.item(item, 'text').lower()
            chat_type = self.chat_tree.item(item, 'values')[0]
            chat_status = self.chat_tree.item(item, 'values')[1]
            
            show = search_term in chat_name
            
            if show and filter_type != 'all':
                if filter_type in ['included', 'excluded']:
                    show = chat_status == filter_type
                else:
                    show = chat_type == filter_type
            
            if show:
                self.chat_tree.reattach(item, '', 'end')
            else:
                self.chat_tree.detach(item)
    
    def show_context_menu(self, event):
        """Show context menu on right click"""
        # Select the item under cursor
        item = self.chat_tree.identify_row(event.y)
        if item:
            self.chat_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def copy_chat_name(self):
        """Copy selected chat name to clipboard"""
        selection = self.chat_tree.selection()
        if selection:
            chat_name = self.chat_tree.item(selection[0], 'text')
            self.root.clipboard_clear()
            self.root.clipboard_append(chat_name)
    
    def set_single_chat_status(self, status):
        """Set status for currently selected chat"""
        selection = self.chat_tree.selection()
        if selection:
            self.set_chat_status(status, selection)
    
    def toggle_chat_status(self, event):
        """Toggle chat status on double click"""
        selection = self.chat_tree.selection()
        if selection:
            current_status = self.chat_tree.item(selection[0], 'values')[1]
            if current_status == 'include':
                self.set_chat_status('exclude', selection)
            elif current_status == 'exclude':
                self.set_chat_status('clear', selection)
            else:
                self.set_chat_status('include', selection)
    
    def include_all_visible(self):
        visible_items = [item for item in self.chat_tree.get_children() if self.chat_tree.parent(item) == '']
        self.set_chat_status('include', visible_items)
    
    def exclude_all_visible(self):
        visible_items = [item for item in self.chat_tree.get_children() if self.chat_tree.parent(item) == '']
        self.set_chat_status('exclude', visible_items)
    
    def clear_all_visible(self):
        visible_items = [item for item in self.chat_tree.get_children() if self.chat_tree.parent(item) == '']
        self.set_chat_status('clear', visible_items)
    
    def set_chat_status(self, status, items):
        """Set status for chat items"""
        for item in items:
            chat_name = self.chat_tree.item(item, 'text')
            chat_id = None
            
            # Find chat by name (more reliable matching)
            for chat in self.chats:
                if chat['title'] == chat_name:
                    chat_id = str(chat['id'])
                    break
            
            if chat_id:
                # Initialize lists if they don't exist
                if 'included_chats' not in self.config:
                    self.config['included_chats'] = []
                if 'excluded_chats' not in self.config:
                    self.config['excluded_chats'] = []
                
                # Remove from both lists first
                if chat_id in self.config['included_chats']:
                    self.config['included_chats'].remove(chat_id)
                if chat_id in self.config['excluded_chats']:
                    self.config['excluded_chats'].remove(chat_id)
                
                # Add to appropriate list
                if status == 'include':
                    self.config['included_chats'].append(chat_id)
                    new_status = 'include'
                    tags = ['included']
                elif status == 'exclude':
                    self.config['excluded_chats'].append(chat_id)
                    new_status = 'exclude'
                    tags = ['excluded']
                else:  # clear
                    new_status = 'auto'
                    tags = []
                
                # Update tree item immediately
                values = list(self.chat_tree.item(item, 'values'))
                if len(values) >= 2:
                    values[1] = new_status
                    self.chat_tree.item(item, values=values, tags=tags)
        
        # Update summary and save config
        self.update_summary()
        self.save_config()
        
        # Debug logging (only for config changes, not during archive start)
        included_count = len(self.config.get('included_chats', []))
        excluded_count = len(self.config.get('excluded_chats', []))
        # Removed the slow log message that was causing performance issues
    
    def update_summary(self):
        """Update selection summary"""
        if not self.chats:
            return
        
        total_chats = len(self.chats)
        included_count = len(self.config.get('included_chats', []))
        excluded_count = len(self.config.get('excluded_chats', []))
        
        will_process = 0
        for chat in self.chats:
            if self.should_include_chat(chat):
                will_process += 1
        
        summary = f"📊 Total: {total_chats} chats | Will process: {will_process} chats\n"
        summary += f"🎯 Explicitly included: {included_count} | Excluded: {excluded_count}"
        
        self.summary_var.set(summary)
    
    def should_include_chat(self, chat):
        """Check if chat should be included - FAST VERSION"""
        chat_id = str(chat['id'])
        chat_type = chat['type']
        
        # 1. EXPLICIT EXCLUSION takes priority
        if chat_id in self.config.get('excluded_chats', []):
            return False
        
        # 2. EXPLICIT INCLUSION takes priority over type filters
        if chat_id in self.config.get('included_chats', []):
            return True
        
        # 3. Check type-based filters (only if not explicitly set)
        if chat_type == 'private' and self.private_var.get():
            return True
        elif chat_type == 'group' and self.group_var.get():
            return True
        elif chat_type == 'supergroup' and self.supergroup_var.get():
            return True
        elif chat_type == 'channel' and self.channel_var.get():
            return True
        elif chat_type == 'bot' and self.bot_var.get():
            return True
        
        return False
    
    def save_settings(self):
        """Save current settings"""
        self.config['include_private_chats'] = self.private_var.get()
        self.config['include_groups'] = self.group_var.get()
        self.config['include_supergroups'] = self.supergroup_var.get()
        self.config['include_channels'] = self.channel_var.get()
        self.config['include_bots'] = self.bot_var.get()
        self.config['archive_destination'] = self.dest_var.get()
        
        self.save_config()
        self.show_info("Success", "Settings saved!")
        self.update_summary()
    
    def list_groups(self):
        """List all groups to help find the right one"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to Telegram first!")
            return
        
        def list_worker():
            try:
                self.thread_safe_update(self.log_message, "📋 Listing your groups...")
                
                asyncio.set_event_loop(self.client_loop)
                
                groups = []
                for chat in self.chats:
                    if chat['type'] in ['group', 'supergroup']:
                        groups.append(chat)
                
                self.thread_safe_update(self.log_message, f"📊 Found {len(groups)} groups:")
                
                for group in groups:
                    group_info = f"   • {group['title']} (ID: {group['id']})"
                    self.thread_safe_update(self.log_message, group_info)
                
                self.thread_safe_update(self.log_message, "💡 Copy the ID of your 'Arch' group and paste it in the destination field")
                
            except Exception as ex:
                error_msg = f"❌ Failed to list groups: {str(ex)}"
                self.thread_safe_update(self.log_message, error_msg)
        
        thread = threading.Thread(target=list_worker)
        thread.daemon = True
        thread.start()
    
    def estimate_archive(self):
        """Estimate archive size"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to Telegram first!")
            return
        
        def estimate_worker():
            try:
                self.thread_safe_update(self.log_message, "🔍 Estimating archive size...")
                
                # Use the same event loop that was used for connection
                asyncio.set_event_loop(self.client_loop)
                
                included_chats = [chat for chat in self.chats if self.should_include_chat(chat)]
                log_msg = f"📊 Will process {len(included_chats)} out of {len(self.chats)} chats"
                self.thread_safe_update(self.log_message, log_msg)
                
                total_estimate = 0
                sample_size = min(5, len(included_chats))
                
                for chat_info in included_chats[:sample_size]:
                    try:
                        entity = chat_info['entity']
                        count = 0
                        
                        async def count_photos():
                            nonlocal count
                            # Use regular API instead of takeout for estimation
                            async for message in self.client.iter_messages(entity, filter=InputMessagesFilterPhotos, limit=50):
                                count += 1
                        
                        self.client_loop.run_until_complete(count_photos())
                        total_estimate += count
                        
                        estimate_msg = f"   📊 {chat_info['title']}: ~{count} images (sampled)"
                        self.thread_safe_update(self.log_message, estimate_msg)
                        
                    except Exception as ex:
                        error_msg = f"   ❌ Couldn't estimate {chat_info['title']}: {str(ex)}"
                        self.thread_safe_update(self.log_message, error_msg)
                
                if sample_size > 0:
                    average_per_chat = total_estimate / sample_size
                    total_estimated = average_per_chat * len(included_chats)
                    total_msg = f"📈 Estimated total images: {total_estimated:.0f}"
                    self.thread_safe_update(self.log_message, total_msg)
                    
                    summary = f"📊 Archive Estimate:\n"
                    summary += f"• Total chats to process: {len(included_chats)}\n"
                    summary += f"• Estimated images: {total_estimated:.0f}\n"
                    summary += f"• Archive destination: {self.dest_var.get()}\n"
                    if self.test_mode_var.get():
                        summary += f"• Test mode: 10 images per chat\n"
                    
                    self.thread_safe_update(self.update_archive_summary, summary)
                
            except Exception as ex:
                error_msg = f"❌ Estimation failed: {str(ex)}"
                self.thread_safe_update(self.log_message, error_msg)
        
        thread = threading.Thread(target=estimate_worker)
        thread.daemon = True
        thread.start()
    
    def start_archive(self):
        """Start archiving"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to Telegram first!")
            return
        
        self.save_settings()
        
        # Fast calculation of included chats
        included_chats = [chat for chat in self.chats if self.should_include_chat(chat)]
        
        if not included_chats:
            messagebox.showwarning("Warning", "No chats selected for archiving!")
            return
        
        # Brief summary without spam
        self.log_message(f"📊 Will process {len(included_chats)} out of {len(self.chats)} total chats")
        
        confirm_msg = f"Start archiving {len(included_chats)} chats to '{self.dest_var.get()}'?"
        if not messagebox.askyesno("Confirm", confirm_msg):
            return
        
        self.disable_start_button()
        self.enable_stop_button()
        self.archive_running = True
        
        def archive_worker():
            try:
                # Use the same event loop that was used for connection
                asyncio.set_event_loop(self.client_loop)
                
                self.thread_safe_update(self.log_message, "🚀 Starting archive process...")
                
                # Verify destination
                try:
                    dest_name = self.dest_var.get()
                    
                    # Try to convert to int if it looks like a group ID
                    if dest_name.lstrip('-').isdigit():
                        dest_entity = int(dest_name)
                    else:
                        dest_entity = dest_name
                    
                    archive_entity = self.client_loop.run_until_complete(self.client.get_entity(dest_entity))
                    actual_dest_name = getattr(archive_entity, 'title', dest_name)
                    dest_msg = f"📁 Archive destination: {actual_dest_name}"
                    self.thread_safe_update(self.log_message, dest_msg)
                except Exception as ex:
                    error_msg = f"❌ Cannot access destination '{self.dest_var.get()}': {str(ex)}"
                    self.thread_safe_update(self.log_message, error_msg)
                    return
                
                # Send start message
                start_message = f"🗃️ **IMAGE ARCHIVE SESSION STARTED**\n"
                start_message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                start_message += f"🎯 Archiving {len(included_chats)} selected chats\n"
                start_message += f"🔧 GUI Version - Telegram Image Archiver"
                
                # Convert destination for sending messages
                dest_for_sending = int(self.dest_var.get()) if self.dest_var.get().lstrip('-').isdigit() else self.dest_var.get()
                self.client_loop.run_until_complete(self.client.send_message(dest_for_sending, start_message))
                
                # Process chats
                total_archived = 0
                for i, chat_info in enumerate(included_chats):
                    if not self.archive_running:
                        break
                    
                    progress = (i / len(included_chats)) * 100
                    self.thread_safe_update(self.update_progress, progress)
                    
                    progress_text = f"Processing {i+1}/{len(included_chats)}: {chat_info['title'][:30]}..."
                    self.thread_safe_update(self.update_progress_text, progress_text)
                    
                    archived_count = self.client_loop.run_until_complete(self.archive_chat_images(chat_info))
                    total_archived += archived_count
                    
                    result_msg = f"✅ {chat_info['title']}: {archived_count} images archived"
                    self.thread_safe_update(self.log_message, result_msg)
                
                # Final summary
                if self.archive_running:
                    completion_message = f"🎉 **ARCHIVE COMPLETE!**\n\n"
                    completion_message += f"📊 **Final Stats:**\n"
                    completion_message += f"• Total images archived: {total_archived}\n"
                    completion_message += f"• Chats processed: {len(included_chats)}\n"
                    completion_message += f"• Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    completion_message += f"🔍 All images are now in this group!"
                    
                    self.client_loop.run_until_complete(self.client.send_message(dest_for_sending, completion_message))
                    
                    final_msg = f"🎉 Archive complete! {total_archived} images archived"
                    self.thread_safe_update(self.log_message, final_msg)
                    self.thread_safe_update(self.update_progress, 100)
                    self.thread_safe_update(self.update_progress_text, "Archive completed successfully!")
                else:
                    self.thread_safe_update(self.log_message, "⏹️ Archive stopped by user")
                    self.thread_safe_update(self.update_progress_text, "Archive stopped")
                
            except Exception as ex:
                error_msg = f"❌ Archive failed: {str(ex)}"
                self.thread_safe_update(self.log_message, error_msg)
                self.thread_safe_update(self.show_error, "Error", f"Archive failed: {str(ex)}")
            finally:
                self.thread_safe_update(self.enable_start_button)
                self.thread_safe_update(self.disable_stop_button)
                self.archive_running = False
        
        thread = threading.Thread(target=archive_worker)
        thread.daemon = True
        thread.start()
    
    async def archive_chat_images(self, chat_info):
        """Archive images from a single chat"""
        entity = chat_info['entity']
        chat_title = chat_info['title']
        
        try:
            # Convert destination for sending messages
            dest_for_sending = int(self.dest_var.get()) if self.dest_var.get().lstrip('-').isdigit() else self.dest_var.get()
            
            # Send separator
            separator = "═" * 50
            date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
            separator_message = f"{separator}\n📸 **Starting: {chat_title}**\n📅 {date_str}\n{separator}"
            
            await self.client.send_message(dest_for_sending, separator_message)
            
            # Archive images WITHOUT takeout (to avoid rate limits)
            chat_image_count = 0
            limit = 10 if self.test_mode_var.get() else None  # No artificial limit - process all images
            processed_message_ids = set()  # Track processed messages to avoid duplicates
            messages_processed = 0
            consecutive_no_new_messages = 0
            
            # Use regular message iteration instead of takeout
            async for telegram_message in self.client.iter_messages(entity, filter=InputMessagesFilterPhotos, limit=limit):
                if not self.archive_running:
                    break
                
                messages_processed += 1
                
                # Skip if we've already processed this message (shouldn't happen but safety check)
                if telegram_message.id in processed_message_ids:
                    consecutive_no_new_messages += 1
                    # If we see too many duplicates, something's wrong - break out
                    if consecutive_no_new_messages > 10:
                        self.thread_safe_update(self.log_message, f"   ⚠️ {chat_title}: Stopping due to duplicate detection")
                        break
                    continue
                
                processed_message_ids.add(telegram_message.id)
                consecutive_no_new_messages = 0  # Reset counter
                
                try:
                    await self.client.forward_messages(dest_for_sending, telegram_message)
                    chat_image_count += 1
                    
                    # Log progress every 10 images
                    if chat_image_count % 10 == 0:
                        progress_msg = f"   📸 {chat_title}: {chat_image_count} images archived..."
                        self.thread_safe_update(self.log_message, progress_msg)
                    
                    # Delay for regular API to avoid flood limits
                    await asyncio.sleep(0.3)
                    
                except Exception as forward_ex:
                    # Log individual message errors but continue
                    error_detail = f"   ⚠️ {chat_title}: Skipped message {telegram_message.id} - {str(forward_ex)}"
                    self.thread_safe_update(self.log_message, error_detail)
                    continue
            
            # The async for loop naturally ends when all messages are processed
            # Send appropriate completion message
            if chat_image_count > 0:
                completion_msg = f"✅ **Completed: {chat_title}** - {chat_image_count} images archived (processed {messages_processed} total messages)"
                await self.client.send_message(dest_for_sending, completion_msg)
                final_log = f"✅ {chat_title}: {chat_image_count} images archived successfully"
            else:
                # Handle chats with no images clearly
                no_images_msg = f"ℹ️ **{chat_title}** - No images found (checked {messages_processed} messages)"
                await self.client.send_message(dest_for_sending, no_images_msg)
                final_log = f"ℹ️ {chat_title}: No images found (this is normal for some chats)"
            
            self.thread_safe_update(self.log_message, final_log)
            return chat_image_count
            
        except Exception as ex:
            error_msg = f"❌ Error processing {chat_title}: {str(ex)}"
            self.thread_safe_update(self.log_message, error_msg)
            return 0
    
    def stop_archive(self):
        """Stop the archiving process"""
        self.archive_running = False
        self.log_message("⏹️ Stopping archive...")
        self.disable_stop_button()
    
    def clear_log(self):
        """Clear the log text"""
        self.log_text.delete(1.0, 'end')

def main():
    """Main function"""
    try:
        root = tk.Tk()
        app = TelegramArchiverGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"Error starting GUI: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
"""
AI Chat Popup for ScrapMaster GUI
"""

import customtkinter as ctk
import os
import requests
import json
import threading
import keyring

# ======================
# AI Chat Configuration
# ======================

def get_ai_config():
    """Get AI configuration from settings"""
    from app.database import db
    settings = db.get_settings()
    api_key = keyring.get_password("scrapmaster", "openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")

    return {
        'api_key': api_key,
        'default_model': settings.ai_default_model,
        'enabled': settings.ai_enabled,
        'tool_calling': settings.ai_tool_calling
    }

# ======================
# Chat Popup Window
# ======================

class AIChatPopup(ctk.CTkToplevel):
    """AI Chat popup window"""
    
    def __init__(self, parent, api_key: str = None):
        super().__init__(parent)

        # Get AI configuration
        self.config = get_ai_config()
        self.api_key = api_key or self.config['api_key']

        # Check if AI is enabled
        if not self.config['enabled']:
            from tkinter import messagebox
            messagebox.showwarning("AI Disabled", "AI Assistant is disabled in settings")
            self.destroy()
            return
        
        # Window settings
        self.title("AI Assistant")
        self.geometry("800x700")
        self.resizable(True, True)
        self.minsize(600, 500)
        self.attributes('-topmost', True)
        self.lift()
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        
        self._create_ui()
        
        # Center window
        self.center()
        
        print("AI Chat Popup opened")
    
    def center(self):
        """Center window on screen"""
        self.update_idletasks()
        width = 800
        height = 700
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_ui(self):
        """Create ChatGPT-like chat UI"""
        # Header with title and model selector
        header_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=0, height=60)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="AI Assistant",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("gray20", "gray80")
        )
        title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        # Clear chat button
        clear_btn = ctk.CTkButton(
            header_frame,
            text="🗑",
            command=self._clear_chat,
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            font=ctk.CTkFont(size=14)
        )
        clear_btn.grid(row=0, column=2, padx=(0, 10), pady=15, sticky="e")

        # Model selector
        self.model_var = ctk.StringVar(value=self.config['default_model'])
        model_combo = ctk.CTkComboBox(
            header_frame,
            values=[
                "google/gemini-flash-1.5",
                "meta-llama/llama-3.2-1b-instruct",
                "mistralai/mistral-7b-instruct",
                "openai/gpt-4o-mini",
                "openai/gpt-4o",
                "anthropic/claude-3.5-sonnet"
            ],
            variable=self.model_var,
            width=200,
            height=32,
            font=ctk.CTkFont(size=11)
        )
        model_combo.grid(row=0, column=1, padx=10, pady=15, sticky="e")

        # Main chat area
        chat_container = ctk.CTkFrame(self, fg_color=("gray95", "gray8"))
        chat_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        chat_container.grid_rowconfigure(0, weight=1)
        chat_container.grid_columnconfigure(0, weight=1)

        # Scrollable chat area
        self.chat_frame = ctk.CTkScrollableFrame(
            chat_container,
            fg_color="transparent",
            corner_radius=0
        )
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        # Welcome message
        self._add_message("assistant", "Hello! I'm your AI assistant. How can I help you today?")

        # Typing indicator (hidden initially)
        self.typing_indicator = ctk.CTkFrame(self.chat_frame, fg_color="transparent", height=40)
        self.typing_label = ctk.CTkLabel(
            self.typing_indicator,
            text="🤖 AI is typing...",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60")
        )
        self.typing_indicator.pack_forget()  # Hidden initially

        # Bottom input area
        input_container = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=0, height=80)
        input_container.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        input_container.grid_columnconfigure(0, weight=1)

        # Input frame
        input_frame = ctk.CTkFrame(input_container, fg_color="transparent")
        input_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=12)
        input_frame.grid_columnconfigure(0, weight=1)

        # Chat input (single line like ChatGPT)
        self.chat_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type your message...",
            font=ctk.CTkFont(size=13),
            height=40
        )
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        # Bind Enter key for sending, Shift+Enter for new line
        self.chat_input.bind("<Return>", lambda e: self._send_message())
        self.chat_input.bind("<KeyRelease>", lambda e: self._update_send_button())  # Update send button state

        # Initial send button state
        self._update_send_button()

        # Send button
        self.send_btn = ctk.CTkButton(
            input_frame,
            text="➤",
            command=self._send_message,
            width=40,
            height=40,
            fg_color=("gray70", "gray40"),
            hover_color=("gray60", "gray50"),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.send_btn.grid(row=0, column=1, sticky="e")

        # Status label (bottom right)
        self.status_label = ctk.CTkLabel(
            input_container,
            text="Ready",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60")
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=(0, 5), sticky="se")

        # Auto-scroll to bottom when new messages are added
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def _show_typing_indicator(self):
        """Show typing indicator"""
        self.typing_indicator.pack(fill="x", pady=8, padx=10)
        self.status_label.configure(text="AI is thinking...")
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def _hide_typing_indicator(self):
        """Hide typing indicator"""
        self.typing_indicator.pack_forget()
        self.status_label.configure(text="Ready")
        self.send_btn.configure(state="normal", fg_color=("gray70", "gray40"))

    def _clear_chat(self):
        """Clear all chat messages"""
        # Keep only the welcome message
        for widget in self.chat_frame.winfo_children():
            widget.destroy()

        # Re-add welcome message
        self._add_message("assistant", "Hello! I'm your AI assistant. How can I help you today?")
        self.status_label.configure(text="Chat cleared")

    def _format_message_text(self, text: str) -> str:
        """Format message text for better display"""
        # Handle tool results
        if '[Tool Result:' in text:
            lines = text.split('\n')
            formatted_lines = []

            for line in lines:
                if line.startswith('[Tool Result:'):
                    # Format tool result header
                    tool_name = line.split(']')[0].replace('[Tool Result:', '').strip()
                    formatted_lines.append(f"🔧 Tool: {tool_name}")
                    formatted_lines.append("")  # Empty line for spacing
                else:
                    formatted_lines.append(line)

            return '\n'.join(formatted_lines)
        else:
            return text
    
    def _add_message(self, role: str, text: str, is_typing=False):
        """Add ChatGPT-like message bubble"""
        is_user = role == "user"

        # Main message container
        msg_container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        msg_container.pack(fill="x", pady=8, padx=10)
        msg_container.grid_columnconfigure(1, weight=1)

        # Avatar
        avatar_label = ctk.CTkLabel(
            msg_container,
            text="👤" if is_user else "🤖",
            font=ctk.CTkFont(size=16)
        )
        avatar_label.grid(row=0, column=0, padx=(0, 12), pady=2, sticky="nw")

        # Message bubble container
        bubble_container = ctk.CTkFrame(msg_container, fg_color="transparent")
        bubble_container.grid(row=0, column=1, sticky="ew")
        bubble_container.grid_columnconfigure(0, weight=1)

        # Message bubble
        bubble_color = ("#007AFF", "#0A84FF") if is_user else ("#E9ECEF", "#2D3748")
        text_color = ("white", "white") if is_user else ("black", "white")

        if is_typing:
            # Typing indicator
            bubble = ctk.CTkFrame(
                bubble_container,
                fg_color=bubble_color,
                corner_radius=18,
                height=40
            )
            bubble.grid(row=0, column=0, sticky="w", pady=2)

            typing_text = ctk.CTkLabel(
                bubble,
                text="AI is typing...",
                font=ctk.CTkFont(size=12, slant="italic"),
                text_color=text_color
            )
            typing_text.pack(padx=16, pady=10)
        else:
            # Regular message bubble
            bubble = ctk.CTkFrame(
                bubble_container,
                fg_color=bubble_color,
                corner_radius=18
            )
            bubble.grid(row=0, column=0, sticky="ew" if not is_user else "e", pady=2)

            # Format text for better display
            formatted_text = self._format_message_text(text)

            # Split text into lines for better wrapping
            lines = formatted_text.split('\n')
            for i, line in enumerate(lines):
                if line.strip():  # Skip empty lines
                    # Check if this is a tool result header
                    is_tool_header = line.startswith('[Tool Result:')
                    is_code_block = line.startswith('```')

                    if is_tool_header:
                        # Tool result header styling
                        msg_label = ctk.CTkLabel(
                            bubble,
                            text=line,
                            font=ctk.CTkFont(size=11, weight="bold"),
                            text_color=("gray60", "gray40") if not is_user else text_color,
                            justify="left",
                            anchor="w"
                        )
                    elif is_code_block:
                        # Code block styling
                        msg_label = ctk.CTkLabel(
                            bubble,
                            text=line,
                            font=ctk.CTkFont(family="Courier", size=11),
                            text_color=("gray20", "gray80") if not is_user else text_color,
                            justify="left",
                            anchor="w"
                        )
                    else:
                        # Regular text
                        msg_label = ctk.CTkLabel(
                            bubble,
                            text=line,
                            font=ctk.CTkFont(size=13),
                            text_color=text_color,
                            wraplength=400,  # Max width before wrapping
                            justify="left",
                            anchor="w"
                        )

                    padding_top = 10 if i == 0 else 2
                    padding_bottom = 10 if i == len(lines)-1 else 2

                    msg_label.pack(padx=16, pady=(padding_top, padding_bottom), anchor="w")

        # Auto-scroll to bottom
        self.chat_frame._parent_canvas.after(100, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))

        return msg_container
    
    def _send_message(self):
        """Send message to AI"""
        message = self.chat_input.get().strip()

        if not message:
            return

        # Clear input
        self.chat_input.delete(0, "end")

        # Disable send button and show loading state
        self.send_btn.configure(state="disabled", fg_color=("gray50", "gray60"))
        self.status_label.configure(text="Sending...")

        # Add user message
        self._add_message("user", message)

        # Show typing indicator
        self._show_typing_indicator()

        # Send in thread
        thread = threading.Thread(target=self._get_response, args=(message,), daemon=True)
        thread.start()
    
    def _get_tools(self):
        """Get available tools for the AI"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_job_count",
                    "description": "Get the total number of scraping jobs",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_recent_jobs",
                    "description": "Get recent scraping jobs (last 5)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of jobs to return (default 5)",
                                "default": 5
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_job_status",
                    "description": "Get status of a specific job",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "The job ID to check"
                            }
                        },
                        "required": ["job_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_job",
                    "description": "Run a scraping job",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "The job ID to run"
                            }
                        },
                        "required": ["job_id"]
                    }
                }
            }
        ]

    def _execute_tool(self, tool_call):
        """Execute a tool function"""
        from app.database import db
        from app.scraper.scraper_engine import scraper_engine
        import asyncio

        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])

        try:
            if function_name == "get_job_count":
                jobs = db.get_all_jobs()
                return f"Total jobs: {len(jobs)}"

            elif function_name == "get_recent_jobs":
                limit = arguments.get("limit", 5)
                jobs = db.get_all_jobs()[:limit]
                result = f"Recent {len(jobs)} jobs:\n"
                for job in jobs:
                    result += f"- {job.name} ({job.id[:8]}): {job.status.value}\n"
                return result

            elif function_name == "get_job_status":
                job_id = arguments.get("job_id")
                job = db.get_job(job_id)
                if job:
                    return f"Job '{job.name}' status: {job.status.value}"
                else:
                    return f"Job not found: {job_id}"

            elif function_name == "run_job":
                job_id = arguments.get("job_id")
                job = db.get_job(job_id)
                if job:
                    job.status = "RUNNING"
                    db.update_job(job)
                    # Note: In a real implementation, you'd start the job asynchronously
                    return f"Started job '{job.name}'"
                else:
                    return f"Job not found: {job_id}"

        except Exception as e:
            return f"Error executing tool: {str(e)}"

    def _get_response(self, message: str):
        """Get AI response"""
        def sync_call():
            try:
                model = self.model_var.get()

                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": message}]
                }

                # Add tools if enabled
                if self.config['tool_calling']:
                    payload["tools"] = self._get_tools()
                    payload["tool_choice"] = "auto"
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    message_data = result["choices"][0]["message"]

                    response_text = message_data.get("content", "")

                    # Handle tool calls
                    if message_data.get("tool_calls"):
                        for tool_call in message_data["tool_calls"]:
                            tool_result = self._execute_tool(tool_call)
                            response_text += f"\n\n[Tool Result: {tool_call['function']['name']}]\n{tool_result}"

                    self.after(0, lambda: self._hide_typing_indicator())
                    self.after(0, lambda: self._add_message("assistant", response_text or "Tool executed successfully"))
                    self.after(0, lambda: self.status_label.configure(text=f"Model: {model}"))
                else:
                    self.after(0, lambda: self._hide_typing_indicator())
                    self.after(0, lambda: self._add_message("assistant", f"Error: {response.status_code}"))
                    self.after(0, lambda: self.status_label.configure(text="Error"))

            except Exception as e:
                self.after(0, lambda: self._hide_typing_indicator())
                self.after(0, lambda: self._add_message("assistant", f"Error: {str(e)}"))
                self.after(0, lambda: self.status_label.configure(text="Error"))
        
        sync_call()

# ======================
# Open from Main Window
# ======================

def open_ai_chat(parent):
    """Open AI chat popup"""
    popup = AIChatPopup(parent)
    return popup


# ======================
# Test
# ======================

if __name__ == "__main__":
    import sys
    
    api_key = sys.argv[1] if len(sys.argv) > 1 else None
    
    ctk.set_appearance_mode("dark")
    
    app = ctk.CTk()
    app.title("ScrapMaster Test")
    app.geometry("400x300")
    
    # Add button to open chat
    btn = ctk.CTkButton(
        app,
        text="Open AI Chat",
        command=lambda: open_ai_chat(app)
    )
    btn.pack(pady=50)
    
    app.mainloop()
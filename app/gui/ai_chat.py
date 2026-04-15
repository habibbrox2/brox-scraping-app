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

API_KEY = keyring.get_password("scrapmaster", "openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = "google/gemini-flash-1.5"

# ======================
# Chat Popup Window
# ======================

class AIChatPopup(ctk.CTkToplevel):
    """AI Chat popup window"""
    
    def __init__(self, parent, api_key: str = None):
        super().__init__(parent)
        
        self.api_key = api_key or API_KEY
        
        # Window settings
        self.title("AI Assistant")
        self.geometry("600x500")
        self.resizable(True, True)
        
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
        width = 600
        height = 500
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_ui(self):
        """Create chat UI"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="🤖 AI Assistant",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Model selector
        self.model_var = ctk.StringVar(value=DEFAULT_MODEL)
        
        model_frame = ctk.CTkFrame(self, fg_color="transparent")
        model_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="e")
        
        ctk.CTkLabel(model_frame, text="Model:").pack(side="left", padx=5)
        
        model_combo = ctk.CTkComboBox(
            model_frame,
            values=[
                "google/gemini-flash-1.5",
                "meta-llama/llama-3.2-1b-instruct",
                "mistralai/mistral-7b-instruct"
            ],
            variable=self.model_var,
            width=200
        )
        model_combo.pack(side="left", padx=5)
        
        # Chat history (scrollable)
        self.chat_frame = ctk.CTkScrollableFrame(
            self,
            label_text="Chat History"
        )
        self.chat_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Welcome message
        self._add_message("assistant", "Hello! I'm your AI assistant. How can I help you today?")
        
        # Model info label
        self.info_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.info_label.grid(row=2, column=0, padx=20, pady=(0, 5), sticky="w")
        
        # Input frame
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Chat input
        self.chat_input = ctk.CTkTextbox(
            input_frame,
            height=80,
            font=ctk.CTkFont(size=12)
        )
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # Bind Enter key
        self.chat_input.bind("<Return>", lambda e: self._send_message())
        
        # Send button
        send_btn = ctk.CTkButton(
            input_frame,
            text="Send",
            command=self._send_message,
            width=100
        )
        send_btn.grid(row=0, column=1, sticky="e")
    
    def _add_message(self, role: str, text: str):
        """Add message to chat"""
        is_user = role == "user"
        
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        msg_frame.pack(fill="x", pady=5)
        
        # Avatar
        icon = "👤" if is_user else "🤖"
        
        # Label
        label = ctk.CTkLabel(
            msg_frame,
            text=f"{icon} {text}",
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            fg_color=("gray80", "gray20") if is_user else ("blue", "blue")
        )
        label.pack(fill="x", padx=10, pady=5)
    
    def _send_message(self):
        """Send message to AI"""
        message = self.chat_input.get("1.0", "end").strip()
        
        if not message:
            return
        
        # Clear input
        self.chat_input.delete("1.0", "end")
        
        # Add user message
        self._add_message("user", message)
        
        # Show loading
        self.info_label.configure(text="Thinking...")
        self.update()
        
        # Send in thread
        thread = threading.Thread(target=self._get_response, args=(message,), daemon=True)
        thread.start()
    
    def _get_response(self, message: str):
        """Get AI response"""
        def sync_call():
            try:
                model = self.model_var.get()
                
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": message}]
                }
                
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
                    text = result["choices"][0]["message"]["content"]
                    self.after(0, lambda: self._add_message("assistant", text))
                    self.after(0, lambda: self.info_label.configure(text=f"Model: {model}"))
                else:
                    self.after(0, lambda: self._add_message("assistant", f"Error: {response.status_code}"))
            
            except Exception as e:
                self.after(0, lambda: self._add_message("assistant", f"Error: {str(e)}"))
            
            finally:
                self.after(0, lambda: self.info_label.configure(text=""))
        
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
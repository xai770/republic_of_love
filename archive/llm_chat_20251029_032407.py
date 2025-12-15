#!/usr/bin/env python3
"""
Conversational LLM interface for Arden
Allows multi-turn dialogue with local LLMs to develop/test prompts
"""

import sys
import subprocess
import json
from pathlib import Path

class LLMConversation:
    def __init__(self, model="phi3:latest"):
        self.model = model
        self.conversation_file = Path(f"temp/conversation_{model.replace(':', '_').replace('.', '_')}.json")
        self.conversation_file.parent.mkdir(exist_ok=True)
        self.history = []
        self.load_conversation()
    
    def load_conversation(self):
        """Load existing conversation or start fresh"""
        if self.conversation_file.exists():
            with open(self.conversation_file, 'r') as f:
                self.history = json.load(f)
    
    def save_conversation(self):
        """Save conversation to file"""
        with open(self.conversation_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def clear_conversation(self):
        """Start fresh conversation"""
        self.history = []
        self.save_conversation()
        print(f"✨ Started fresh conversation with {self.model}")
    
    def send_message(self, message):
        """Send message to LLM and get response"""
        # Build full context
        context = "\n\n".join([
            f"{'USER' if turn['role'] == 'user' else 'ASSISTANT'}: {turn['content']}"
            for turn in self.history
        ])
        
        if context:
            full_prompt = f"{context}\n\nUSER: {message}\n\nASSISTANT:"
        else:
            full_prompt = message
        
        # Send to LLM
        print("━" * 80)
        print(f"💬 ARDEN → {self.model}")
        print("━" * 80)
        print(message)
        print()
        
        try:
            result = subprocess.run(
                ['ollama', 'run', self.model],
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )
            response = result.stdout.strip()
        except subprocess.TimeoutExpired:
            response = "⏰ Timeout - model took too long to respond (5 min limit)"
        except Exception as e:
            response = f"❌ Error: {e}"
        
        print("━" * 80)
        print(f"🤖 {self.model} → ARDEN")
        print("━" * 80)
        print(response)
        print()
        
        # Save to history
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": response})
        self.save_conversation()
        
        return response
    
    def show_history(self):
        """Display conversation history"""
        print("━" * 80)
        print(f"📜 CONVERSATION HISTORY WITH {self.model}")
        print("━" * 80)
        for turn in self.history:
            role = "💬 ARDEN" if turn['role'] == 'user' else f"🤖 {self.model}"
            print(f"\n{role}:")
            print(turn['content'])
            print()
        print("━" * 80)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 llm_chat.py <model> <command> [message]")
        print()
        print("Commands:")
        print("  send 'message'  - Send a message")
        print("  show            - Show conversation history")
        print("  clear           - Start fresh conversation")
        print()
        print("Example:")
        print("  python3 llm_chat.py phi3:latest send 'Hello, introduce yourself'")
        print("  python3 llm_chat.py phi3:latest send 'What is 2+2?'")
        print("  python3 llm_chat.py phi3:latest show")
        sys.exit(1)
    
    model = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else 'help'
    
    chat = LLMConversation(model)
    
    if command == 'send':
        if len(sys.argv) < 4:
            print("❌ Error: Need a message to send")
            sys.exit(1)
        message = sys.argv[3]
        chat.send_message(message)
    
    elif command == 'show':
        chat.show_history()
    
    elif command == 'clear':
        chat.clear_conversation()
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: send, show, clear")
        sys.exit(1)

if __name__ == '__main__':
    main()

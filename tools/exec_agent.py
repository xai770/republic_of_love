#!/usr/bin/env python3
"""
ExecAgent - Command execution for LLMs
Inspired by Gopher (Internet before WWW)

Allows LLMs to embed commands in their responses:
  {ExecAgent search <topic>}
  {ExecAgent curl <URL>}
  {ExecAgent ask <model> <question>}
  {ExecAgent add log <message>}
  {ExecAgent read log}

Version: 1.1
Created: 2025-11-16
Updated: 2025-11-16 (added 'ask' command for Ollama models)
"""

import sys
import re
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple


class ExecAgent:
    def __init__(self, log_file: str = "logs/exec_agent.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
        self.command_pattern = r'\{ExecAgent\s+([^}]+)\}'
        
    def get_banner(self) -> str:
        """Return the ExecAgent banner/help text"""
        return """
ExecAgent v1.2 - 2025-Dec-07

Welcome! You can include the following commands in your response. ExecAgent will execute them and return the result to you.

{ExecAgent search <topic>} (Example: {ExecAgent search "postgres data visualisation"})
{ExecAgent curl <URL>} (Example: {ExecAgent curl "https://example.com"})
{ExecAgent ask <model> <question>} (Example: {ExecAgent ask qwen3-vl "What are best practices for SQL indexing?"})
{ExecAgent add log <message>} (Example: {ExecAgent add log "08:15 Started workflow 1121"})
{ExecAgent read log} (No options, displays recent log entries)
{ExecAgent sql <query>} (Example: {ExecAgent sql "SELECT COUNT(*) FROM entities"})
{ExecAgent sql! <query>} (WRITE mode - allows INSERT/UPDATE. Example: {ExecAgent sql! "UPDATE entities SET status='merged' WHERE entity_id=123"})
"""
    
    def search_duckduckgo(self, query: str) -> str:
        """Search DuckDuckGo and return results"""
        try:
            # Use ddgr (DuckDuckGo command-line tool)
            # Format: ddgr --json <query>
            result = subprocess.run(
                ['ddgr', '--json', '--num', '5', query],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                results = json.loads(result.stdout)
                output = f"🔍 Search results for: {query}\n\n"
                
                for i, item in enumerate(results[:5], 1):
                    title = item.get('title', 'No title')
                    url = item.get('url', 'No URL')
                    abstract = item.get('abstract', 'No description')
                    output += f"{i}. {title}\n   {url}\n   {abstract}\n\n"
                
                return output
            else:
                # Fallback: use curl with DuckDuckGo Lite
                return self._search_ddg_fallback(query)
                
        except FileNotFoundError:
            # ddgr not installed, use fallback
            return self._search_ddg_fallback(query)
        except Exception as e:
            return f"❌ Search failed: {str(e)}"
    
    def _search_ddg_fallback(self, query: str) -> str:
        """Fallback search using curl to DuckDuckGo Lite"""
        try:
            url = f"https://lite.duckduckgo.com/lite/?q={query.replace(' ', '+')}"
            result = subprocess.run(
                ['curl', '-s', '-L', url],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse HTML (very basic)
                html = result.stdout
                # Extract result snippets (between <a> tags)
                links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
                
                output = f"🔍 Search results for: {query}\n\n"
                for i, (url, title) in enumerate(links[:5], 1):
                    if url.startswith('http') and title.strip():
                        output += f"{i}. {title.strip()}\n   {url}\n\n"
                
                return output if len(links) > 0 else f"No results found for: {query}"
            else:
                return f"❌ Search failed (curl error)"
                
        except Exception as e:
            return f"❌ Search failed: {str(e)}"
    
    def curl_url(self, url: str) -> str:
        """Fetch URL content using curl"""
        try:
            # Clean URL (remove quotes if present)
            url = url.strip().strip('"').strip("'")
            
            result = subprocess.run(
                ['curl', '-s', '-L', '--max-time', '10', url],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                content = result.stdout
                
                # Truncate if too long
                if len(content) > 5000:
                    content = content[:5000] + "\n\n[... truncated ...]"
                
                return f"📄 Content from {url}:\n\n{content}"
            else:
                return f"❌ Failed to fetch {url}: {result.stderr}"
                
        except Exception as e:
            return f"❌ Curl failed: {str(e)}"
    
    def add_log(self, message: str) -> str:
        """Add entry to log file"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] {message}\n"
            
            with open(self.log_file, 'a') as f:
                f.write(log_entry)
            
            return f"✅ Added to log: {message}"
            
        except Exception as e:
            return f"❌ Log write failed: {str(e)}"
    
    def read_log(self, lines: int = 20) -> str:
        """Read recent log entries"""
        try:
            if not self.log_file.exists():
                return "📋 Log is empty"
            
            with open(self.log_file, 'r') as f:
                all_lines = f.readlines()
            
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            return f"📋 Recent log entries:\n\n{''.join(recent)}"
            
        except Exception as e:
            return f"❌ Log read failed: {str(e)}"
    
    def ask_ollama(self, model: str, question: str) -> str:
        """Ask a question to a local Ollama model"""
        try:
            # Clean inputs
            model = model.strip().strip('"').strip("'")
            question = question.strip().strip('"').strip("'")
            
            # Call ollama using subprocess
            result = subprocess.run(
                ['ollama', 'run', model, question],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout for model responses
            )
            
            if result.returncode == 0:
                response = result.stdout.strip()
                
                # Truncate if too long
                if len(response) > 2000:
                    response = response[:2000] + "\n\n[... truncated ...]"
                
                return f"🤖 {model} says:\n\n{response}"
            else:
                error = result.stderr.strip()
                return f"❌ Model '{model}' error: {error}\n\nTip: Use 'ollama list' to see available models"
                
        except subprocess.TimeoutExpired:
            return f"⏱️ Model '{model}' timed out (60s limit)"
        except FileNotFoundError:
            return "❌ Ollama not found. Please install: https://ollama.ai"
        except Exception as e:
            return f"❌ Ask failed: {str(e)}"
    
    def execute_sql(self, query: str, write_mode: bool = False) -> str:
        """Execute SQL query against the database
        
        Args:
            query: SQL query to execute
            write_mode: If False (default), only SELECT allowed. If True, INSERT/UPDATE allowed.
        """
        import os
        from dotenv import load_dotenv
        
        try:
            # Clean query - only strip outer wrapping quotes, preserve internal quotes
            query = query.strip()
            if (query.startswith('"') and query.endswith('"')) or \
               (query.startswith("'") and query.endswith("'")):
                query = query[1:-1]
            
            # Security: Check for forbidden operations
            query_upper = query.upper().strip()
            
            # ALWAYS forbidden - no exceptions
            forbidden = ['DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'GRANT', 'REVOKE']
            for word in forbidden:
                if word in query_upper.split():
                    return f"❌ FORBIDDEN: {word} statements are not allowed"
            
            # DELETE requires explicit confirmation pattern
            if 'DELETE' in query_upper.split():
                if 'WHERE' not in query_upper:
                    return "❌ DELETE without WHERE clause is forbidden"
                if not write_mode:
                    return "❌ DELETE requires sql! (write mode). Use {ExecAgent sql! \"DELETE...\"}"
            
            # Write operations require write_mode
            if not write_mode:
                write_ops = ['INSERT', 'UPDATE', 'DELETE']
                for op in write_ops:
                    if query_upper.startswith(op) or f' {op} ' in query_upper:
                        return f"❌ {op} requires write mode. Use {{ExecAgent sql! \"{query}\"}}"
            
            # Execute via sudo -u postgres psql (same as q.sh)
            import subprocess
            
            # Build psql command
            cmd = ['sudo', '-u', 'postgres', 'psql', '-d', 'turing', '-t', '-A', '-F', '|', '-c', query]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return f"❌ SQL error: {result.stderr.strip()}"
            
            output = result.stdout.strip()
            
            if not output:
                if query_upper.startswith('SELECT'):
                    return "📊 Query returned 0 rows"
                else:
                    return "✅ Query executed."
            
            # Format output
            if query_upper.startswith('SELECT') or 'RETURNING' in query_upper:
                lines = output.split('\n')
                if lines:
                    return f"📊 Query returned {len(lines)} rows:\n\n" + '\n'.join(lines[:50]) + \
                           (f"\n[... {len(lines) - 50} more rows ...]" if len(lines) > 50 else "")
            else:
                # Write operation - parse "UPDATE X" or "INSERT 0 X" output
                return f"✅ Query executed: {output}"
                
        except subprocess.TimeoutExpired:
            return "❌ SQL timeout (30s)"
        except Exception as e:
            return f"❌ SQL error: {str(e)}"
    
    def execute_command(self, command: str) -> str:
        """Parse and execute a single ExecAgent command"""
        parts = command.strip().split(None, 1)
        
        if not parts:
            return "❌ Empty command"
        
        action = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if action == 'search':
            query = args.strip().strip('"').strip("'")
            return self.search_duckduckgo(query)
        
        elif action == 'curl':
            url = args.strip()
            return self.curl_url(url)
        
        elif action == 'ask':
            # Parse "ask <model> <question>"
            ask_parts = args.split(None, 1)
            if len(ask_parts) < 2:
                return "❌ Usage: ask <model> <question>\n   Example: ask qwen3-vl \"What is PostgreSQL?\""
            model = ask_parts[0]
            question = ask_parts[1]
            return self.ask_ollama(model, question)
        
        elif action == 'add' and args.startswith('log '):
            message = args[4:].strip().strip('"').strip("'")
            return self.add_log(message)
        
        elif action == 'read' and args.strip().lower() == 'log':
            return self.read_log()
        
        elif action == 'sql':
            query = args.strip()
            return self.execute_sql(query, write_mode=False)
        
        elif action == 'sql!':
            query = args.strip()
            return self.execute_sql(query, write_mode=True)
        
        else:
            return f"❌ Unknown command: {action}\n{self.get_banner()}"
    
    def process_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Process text and execute any embedded ExecAgent commands
        
        Returns:
            (processed_text, command_results)
        """
        commands = re.findall(self.command_pattern, text)
        results = []
        
        for cmd in commands:
            result = self.execute_command(cmd)
            results.append(result)
        
        # Replace commands with results in text
        processed = text
        for cmd, result in zip(commands, results):
            processed = processed.replace(f"{{ExecAgent {cmd}}}", result)
        
        return processed, results
    
    def interactive_mode(self):
        """Interactive REPL for testing ExecAgent commands"""
        print(self.get_banner())
        print("\nInteractive mode - Type ExecAgent commands or 'quit' to exit\n")
        
        while True:
            try:
                user_input = input("ExecAgent> ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye! 👋")
                    break
                
                if not user_input:
                    continue
                
                # Wrap in {ExecAgent ...} if not already
                if not user_input.startswith('{ExecAgent'):
                    user_input = f"{{ExecAgent {user_input}}}"
                
                processed, results = self.process_text(user_input)
                print(processed)
                print()
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"Error: {e}\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ExecAgent - Command execution for LLMs')
    parser.add_argument('--interactive', '-i', action='store_true', 
                       help='Start interactive mode')
    parser.add_argument('--text', '-t', type=str, 
                       help='Process text with embedded commands')
    parser.add_argument('--command', '-c', type=str,
                       help='Execute a single command')
    parser.add_argument('--banner', '-b', action='store_true',
                       help='Show banner/help text')
    
    args = parser.parse_args()
    
    agent = ExecAgent()
    
    if args.banner:
        print(agent.get_banner())
    
    elif args.interactive:
        agent.interactive_mode()
    
    elif args.text:
        processed, results = agent.process_text(args.text)
        print(processed)
    
    elif args.command:
        result = agent.execute_command(args.command)
        print(result)
    
    else:
        # Read from stdin
        text = sys.stdin.read()
        processed, results = agent.process_text(text)
        print(processed)


if __name__ == '__main__':
    main()

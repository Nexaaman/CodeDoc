import os
from smolagents import CodeAgent, OpenAIServerModel, ToolCallingAgent, tool
from rich.console import Console
from rich.markdown import Markdown
from codedoc.analysis import StaticAnalyzer, Issue
import re
from rich.panel import Panel

import json
import datetime
from pathlib import Path

from codedoc.config import LOGS_DIR
from codedoc.tools import list_files, read_file, write_file, inspect_code_structure, search_in_files


console = Console()

class BaseCodeDocAgent:
    """Base configuration for all agents."""
    def __init__(self, api_base: str, model_id: str = "local-model"):
        self.model = OpenAIServerModel(
            model_id=model_id,
            api_base=api_base,
            api_key="sk-no-key-required",
            flatten_messages_as_text=True
        )
        self.authorized_imports = [
            'os', 'sys', 'json', 'shutil', 're', 'math', 'datetime', 'ast', 'pathlib'
        ]

class LocalCodeAgent(BaseCodeDocAgent):
    def __init__(self, api_base="http://127.0.0.1:8000/v1"):
        super().__init__(api_base)
        
        self.agent = CodeAgent(
            tools=[], 
            model=self.model,
            add_base_tools=True,
            max_steps=6,
            verbosity_level=0,
            additional_authorized_imports=self.authorized_imports,
        )
        self.analyzer = StaticAnalyzer()
        
        
    def _prune_memory(self):
        """
        Keep System Prompt + User Prompt + Last 2 Steps.
        Discard older tool outputs to save context.
        """
        
        if len(self.agent.memory.steps) > 2:
            
            self.agent.memory.steps = self.agent.memory.steps[-2:]
        
        
    def _extract_code(self, llm_response: str) -> str:
        """Robust code extractor handling multiple markdown formats."""
        content = str(llm_response)
        patterns = [
            r'```[a-zA-Z]*\s*\n(.*?)```',
            r'```\s*\n(.*?)```'
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()
        return content.strip()
        

    def analyze_file(self, file_path: str):
        """
        1. Run static AST analysis.
        2. Send code + analysis to LLM for reasoning.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code_content = f.read()
        except FileNotFoundError:
            return f"Error: File {file_path} not found."
        
        
        self._prune_memory()
        
        is_python = file_path.endswith(".py")
        static_issues = []
        
        # Format issues for the LLM Prompt
        issues_text = ""
        if is_python:
            
            static_issues = self.analyzer.scan(code_content, file_path)
            
            if static_issues:
        
                issues_text = "Static Analysis Findings (Address these if relevant):\n"
                for i in static_issues:
                    issues_text += f"- Line {i.line} [{i.severity}]: {i.message}\n"
                    
            else:
                issues_text = "Static Analysis: Clean (No structural issues found)."
        
        else:
            issues_text = f"Static Analysis: Skipped (Not a Python file). relying on AI model knowledge for {Path(file_path).suffix} files."

        # 2. LLM Phase

        prompt = f"""
        You are a Senior Software Engineer. Analyze this file ({file_path})..
        
        Issues: {issues_text}
        
        CODE:
        ```
        {code_content}
        ```
        
        INSTRUCTIONS:
        1. Provide a concise summary of logic in bullet points.
        2. Identify specific bugs (logic errors, syntax errors, security flaws).
        3. Suggest improvements considering best practices for this specific language.
        """
        
        # Run the agent
        return str(self.agent.run(prompt, reset=True))
    
        
    def fix_file(self, file_path: str) -> str:
        """
        Reads file, runs analysis, and asks LLM to regenerate the code with fixes.
        Returns the raw string of the fixed code.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code_content = f.read()
        except FileNotFoundError:
            return ""

        self._prune_memory()
        
        is_python = file_path.endswith(".py")
        static_issues = []
        
        # Format issues for the LLM Prompt
        issues_text = ""
        
        if is_python:
            
            static_issues = self.analyzer.scan(code_content, file_path)
            
            if static_issues:
        
                issues_text = "Static Analysis Findings (Address these if relevant):\n"
                for i in static_issues:
                    issues_text += f"- Line {i.line} [{i.severity}]: {i.message}\n"
                    
            else:
                issues_text = "Static Analysis: Clean (No structural issues found)."
        
        else:
            issues_text = f"Static Analysis: Skipped (Not a Python file). relying on AI model knowledge for {Path(file_path).suffix} files."


        prompt = f"""
        You are an expert Polyglot Coder.
        
        File: {file_path}
        
        Static Analysis Issues detected:
        {issues_text}
        
        Input Code:
        ```
        {code_content}
        ```
        
        Task:
        1. Fix all static analysis issues listed above.
        2. Fix any obvious logic bugs or security flaws.
        3. Maintain the original style and imports unless necessary to change.
        4. If this is not Python, use best practices for the language (e.g., proper JSDoc for JS, Rust formatting, etc).
        5. RETURN ONLY THE FIXED CODE inside a markdown code block.
        
        Do not add conversational text after the code block.
        """

        console.print("[italic dim]Waiting for LLM to generate patch...[/italic dim]")
        response = self.agent.run(prompt, reset=True)
        
        return self._extract_code(response)
       
class WorkflowAgent(BaseCodeDocAgent):
    def __init__(self, api_base="http://127.0.0.1:8000/v1"):
        super().__init__(api_base)
        
        self.tools = [
            list_files, 
            read_file, 
            write_file, 
            inspect_code_structure
        ]
        
        self.agent = CodeAgent(
            tools=self.tools,
            model=self.model,
            max_steps=12,
            verbosity_level=0,
            additional_authorized_imports=self.authorized_imports,
        )

    def _save_logs(self, task: str, logs: list):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = LOGS_DIR / f"trace_{timestamp}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({"task": task, "logs": str(logs)}, f, indent=2)
        return log_path
    
    
    def run_workflow(self, user_request: str):
        
        files = list_files(".")
        
        # STURDY PROMPT TO PREVENT ERRORS
        execution_prompt = f"""
        You are a Senior Automation Engineer.
        
        CURRENT FILES:
        {files}
        
        TASK:
        {user_request}
        
        STRICT CODING RULES:
        1. **REGEX**: ALWAYS use `import re` and `re.search(pattern, text)`. NEVER do `text.search()`.
        2. **TOOLS**: Use `search_in_files` to find code. Use `read_file` and `write_file`.
        3. **NO GUESSING**: Read the file before editing it.
        4. **PYTHON**: You are writing a Python script to perform this task.
        
        Start execution.
        """
        
        console.print("[bold green]🚀 CodeDoc Agent Started...[/bold green]")
        
        try:
            self.agent.memory.reset()
            # Run the agent
            result = self.agent.run(execution_prompt, reset=True)
            
            # 3. LOGGING
            log_path = self._save_logs(user_request, self.agent.memory.steps)
            
            console.print(Panel(str(result), title="Final Output", border_style="green"))
            console.print(f"[dim]Trace logs saved to: {log_path}[/dim]")
            
            return result
            
        except Exception as e:
            console.print(f"[bold red]Workflow Crashed:[/bold red] {e}")
            if "has no attribute" in str(e):
                console.print("[yellow]Hint: You likely tried to use a JS method on a Python string.[/yellow]")
            return None
        
class ChatOrchestrator(BaseCodeDocAgent):
    def __init__(self, api_base="http://127.0.0.1:8000/v1"):
        super().__init__(api_base)
        self.worker = LocalCodeAgent(api_base)
        
        # Define Tools dynamically to access the worker instance
        @tool
        def deep_analyze_tool(file_path: str) -> str:
            """
            Performs a deep analysis of a specific file using a dedicated sub-agent.
            Use this when the user asks to 'check', 'audit', or 'analyze' a file.
            Returns a summary report.
            Args:
                file_path: The path of the file to analyze.
            """
            return self.worker.analyze_file(file_path)
        
        
        @tool
        def auto_fix_tool(file_path: str) -> str:
            """
            Automatically fixes static issues and bugs in a file using a dedicated sub-agent.
            Returns the fixed code. Note: This does not write to disk, you must use write_file to save it.
            Args:
                file_path: The path of the file to fix.
            """
            return self.worker.fix_file(file_path)
        
        # The Orchestrator's toolkit
        self.tools = [
            list_files, 
            read_file, 
            write_file, 
            inspect_code_structure,
            deep_analyze_tool, 
            auto_fix_tool
        ]
        
        self.chat_agent = CodeAgent(
            tools=self.tools,
            model=self.model,
            max_steps=10,
            verbosity_level=0,
            additional_authorized_imports=self.authorized_imports
        )
        
        self.system_prompt = """
            You are CodeDoc, an expert Technical Lead and Orchestrator.
            
            Your Capabilities:
            1. Explore codebase (list_files, inspect_code_structure).
            2. Analyze code quality (deep_analyze_tool).
            3. fix bugs (auto_fix_tool).
            4. Modify files (write_file).
            
            Guidelines:
            - **Efficiency**: Do NOT read full files (`read_file`) unless absolutely necessary. Use `inspect_code_structure` to see definitions first.
            - **Delegation**: If the user asks to analyze/fix, use the specialized tools. Do not try to analyze AST manually.
            - **Brevity**: Keep responses concise and actionable.
            - **Safety**: If creating a new file or overwriting, confirm the path.
            """
            
    def _save_logs(self, task: str, logs: list):
        """Save the execution trace to the logs directory."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trace_{timestamp}.json"
        log_path = LOGS_DIR / filename
        
        data = {
            "task": task,
            "timestamp": timestamp,
            "logs": str(logs) 
        }
        
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return log_path
    
    def chat_turn(self, user_input: str):
        """
        Runs one turn of the conversation.
        """
        
        full_prompt = f"{self.system_prompt}\nUser: {user_input}"
        
        try:
            response = self.chat_agent.run(full_prompt)
            return str(response)
        except Exception as e:
            return f"Error during execution: {e}"


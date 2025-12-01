import os
from smolagents import CodeAgent, OpenAIServerModel, Tool
from rich.console import Console
from rich.markdown import Markdown
from codedoc.analysis import StaticAnalyzer, Issue
import re
console = Console()

class LocalCodeAgent:
    def __init__(self, api_base="http://127.0.0.1:8000/v1"):
        self.model = OpenAIServerModel(
            model_id="local-model",
            api_base=api_base,
            api_key="sk-no-key-required",
            flatten_messages_as_text=True
        )
        
        self.agent = CodeAgent(
            tools=[], 
            model=self.model,
            add_base_tools=True,
            max_steps=3,
            verbosity_level=0
        )
        self.analyzer = StaticAnalyzer()
        
        
    def _extract_code(self, llm_response: str) -> str:
        """Helper to extract clean code from Markdown response."""
        # Match code blocks with python syntax highlighting
        pattern = r'```python\s*\n(.*?)```'
        match = re.search(pattern, str(llm_response), re.DOTALL)
        if match:
            return match.group(1).strip()

        # Fallback: try generic code block
        pattern = r'```\s*\n(.*?)```'
        match = re.search(pattern, str(llm_response), re.DOTALL)
        if match:
            return match.group(1).strip()

        return str(llm_response).strip()
        
        
    def get_truncated_messages(self, max_history=2):
        """Keep only last N assistant/tool pairs"""
        messages = self.agent.write_memory_to_messages()
        # Keep system + user + last N pairs
        if len(messages) > 2 + (max_history * 2):
            return messages[:2] + messages[-(max_history * 2):]
        return messages

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
        
        # 1. Static Phase
        static_issues = self.analyzer.scan(code_content, file_path)
        
        # Format issues for the LLM Prompt
        issues_text = ""
        if static_issues:
            issues_text = "Static Analysis Findings (Address these if relevant):\n"
            for i in static_issues:
                issues_text += f"- Line {i.line} [{i.severity}]: {i.message}\n"
        else:
            issues_text = "Static Analysis: Clean (No structural issues found)."

        # 2. LLM Phase

        prompt = f"""
        You are a Senior Software Engineer. Analyze the following source code.
        
        File: {file_path}
        
        {issues_text}
        
        Code Content:
        ```python
        {code_content}
        ```
        
       Task:
        1. Summarize the code's purpose.
        2. Analyze the 'Static Analysis Findings' above. Are they valid concerns?
        3. Find LOGIC bugs that static analysis missed (race conditions, infinite loops, logic errors).
        4. Suggest specific code improvements.
        
        Return your response in clean Markdown.
        """
        
        # Run the agent
        response = self.agent.run(prompt, reset=True)
        
        return {
            "static_issues": static_issues,
            "llm_response": str(response)
        }
        
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

        # Run static analysis first to give the LLM context on what to fix
        static_issues = self.analyzer.scan(code_content, file_path)
        issues_text = ""
        for i in static_issues:
            issues_text += f"- Line {i.line}: {i.message}\n"

        prompt = f"""
        You are a Code Repair Specialist.
        
        File: {file_path}
        
        Static Analysis Issues detected:
        {issues_text}
        
        Input Code:
        ```python
        {code_content}
        ```
        
        Task:
        1. Fix all static analysis issues listed above.
        2. Fix any obvious logic bugs or security flaws.
        3. Maintain the original style and imports unless necessary to change.
        4. Output the COMPLETE fixed file content. Do not truncate the code.
        
        IMPORTANT: Return ONLY the code inside a markdown code block (e.g., ```python ... ```).
        Do not add conversational text after the code block.
        """

        console.print("[italic dim]Waiting for LLM to generate patch...[/italic dim]")
        response = self.agent.run(prompt, reset=True)
        
        return self._extract_code(response)
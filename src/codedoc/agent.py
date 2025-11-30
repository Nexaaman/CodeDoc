import os
from smolagents import CodeAgent, OpenAIServerModel, Tool
from rich.console import Console
from rich.markdown import Markdown

console = Console()

class LocalCodeAgent:
    def __init__(self, api_base="http://127.0.0.1:8000/v1"):
        # We use OpenAIServerModel to talk to llama-cpp-python's OpenAI-compatible endpoint
        self.model = OpenAIServerModel(
            model_id="local-model", # ID doesn't matter much for local llama.cpp
            api_base=api_base,
            api_key="sk-no-key-required",
            flatten_messages_as_text=True
        )
        
        # In Phase 2, we will add more tools here
        self.agent = CodeAgent(
            tools=[], 
            model=self.model,
            add_base_tools=True,# Adds python interpreter tool
            max_steps=3,  # Limit to 3 steps max
            verbosity_level=0
        )
        
        
    def get_truncated_messages(self, max_history=2):
        """Keep only last N assistant/tool pairs"""
        messages = self.agent.write_memory_to_messages()
        # Keep system + user + last N pairs
        if len(messages) > 2 + (max_history * 2):
            return messages[:2] + messages[-(max_history * 2):]
        return messages

    def analyze_file(self, file_path: str):
        """Read a file and ask the LLM to analyze it."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code_content = f.read()
        except FileNotFoundError:
            return f"Error: File {file_path} not found."

        prompt = f"""
        You are a Senior Software Engineer. Analyze the following source code.
        
        File: {file_path}
        
        Code:
        ```python
        {code_content}
        ```
        
        Please provide:
        1. A brief summary of what the code does.
        2. Potential bugs or security risks.
        3. Suggestions for improvement (style or performance).
        
        Format your response in Markdown.
        """
        
        # Run the agent
        response = self.agent.run(prompt, reset=True)
        return response
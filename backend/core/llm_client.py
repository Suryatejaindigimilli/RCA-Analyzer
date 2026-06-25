"""LLM Client - Now supports Ollama for FREE real responses!"""
import os
import httpx


class LLMClient:
    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'ollama').lower()
        self.client = None
        self.ollama_url = "http://localhost:11434"
        self._init_client()

    def _init_client(self):
        if self.provider == 'ollama':
            # Check if Ollama is running
            try:
                import httpx
                response = httpx.get(f"{self.ollama_url}/api/tags", timeout=2)
                if response.status_code == 200:
                    print("✓ Connected to Ollama (local LLM)")
                    return
            except Exception:
                print("⚠ Ollama not running. Falling back to mock.")
                self.provider = 'mock'
        
        elif self.provider == 'anthropic':
            try:
                import anthropic
                api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
                if api_key and len(api_key) > 10:
                    self.client = anthropic.Anthropic(api_key=api_key)
                    return
            except ImportError:
                pass
            self.provider = 'mock'
        
        elif self.provider == 'openai':
            try:
                import openai
                api_key = os.getenv('OPENAI_API_KEY', '').strip()
                if api_key and len(api_key) > 10:
                    self.client = openai.OpenAI(api_key=api_key)
                    return
            except ImportError:
                pass
            self.provider = 'mock'
        
        else:
            self.provider = 'mock'

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        if self.provider == 'ollama':
            return self._call_ollama(system_prompt, user_prompt, max_tokens)
        elif self.provider == 'anthropic':
            return self._call_anthropic(system_prompt, user_prompt, max_tokens)
        elif self.provider == 'openai':
            return self._call_openai(system_prompt, user_prompt, max_tokens)
        return self._smart_mock(user_prompt)

    def _call_ollama(self, system_prompt, user_prompt, max_tokens):
        """Call local Ollama LLM - FREE and REAL!"""
        try:
            import httpx
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3",  # or phi3, codellama
                    "prompt": user_prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.3,  # Lower = more focused
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()['response']
            else:
                return self._smart_mock(user_prompt, error=f"Ollama error: {response.status_code}")
                
        except Exception as e:
            return self._smart_mock(user_prompt, error=str(e))

    def _call_anthropic(self, system_prompt, user_prompt, max_tokens):
        try:
            msg = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            return self._smart_mock(user_prompt, error=str(e))

    def _call_openai(self, system_prompt, user_prompt, max_tokens):
        try:
            resp = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return resp.choices[0].message.content
        except Exception as e:
            return self._smart_mock(user_prompt, error=str(e))

    def _smart_mock(self, user_prompt, error=None):
        """Smart mock that uses ACTUAL code from context."""
        
        # Extract actual code from the prompt
        code_references = self._parse_references(user_prompt)
        
        if not code_references:
            return self._generic_response()
        
        # Build response using REAL code
        response = "## Code Analysis\n\n"
        response += "Based on your question, I found these relevant code sections in your repository:\n\n"
        
        for i, ref in enumerate(code_references[:3], 1):
            response += f"### Reference {i}: `{ref['file_path']}` (lines {ref['lines']})\n"
            response += f"**Type**: {ref['chunk_type']} | **Name**: {ref['name']}\n"
            response += f"**Relevance**: {ref['relevance']}\n\n"
            response += f"```{ref['language']}\n"
            response += ref['code_preview']
            response += "\n```\n\n"
        
        # Add explanation based on question
        question = self._extract_question(user_prompt)
        response += f"### What This Means\n\n"
        response += self._explain_references(question, code_references[:3])
        
        return response

    def _parse_references(self, prompt):
        """Parse code references from the prompt."""
        references = []
        lines = prompt.split('\n')
        current = None
        in_code = False
        code_lines = []
        
        for line in lines:
            if line.startswith('--- Reference'):
                if current:
                    references.append(current)
                current = {
                    'file_path': 'unknown',
                    'lines': '?',
                    'chunk_type': 'unknown',
                    'name': 'unknown',
                    'relevance': '?',
                    'language': 'text',
                    'code_preview': ''
                }
                in_code = False
                code_lines = []
            elif line.startswith('Type:'):
                if current:
                    parts = line.replace('Type:', '').strip().split('|')
                    for part in parts:
                        if 'Name:' in part:
                            current['name'] = part.replace('Name:', '').strip()
                        elif 'Language:' in part:
                            current['language'] = part.replace('Language:', '').strip()
                        elif 'Relevance:' in part:
                            current['relevance'] = part.replace('Relevance:', '').strip()
            elif line.startswith('```'):
                if in_code and current:
                    current['code_preview'] = '\n'.join(code_lines[:30])
                    code_lines = []
                in_code = not in_code
            elif in_code:
                code_lines.append(line)
            elif current and '(' in line and 'lines' in line:
                # Extract lines info
                import re
                match = re.search(r'\(lines ([\d-]+)\)', line)
                if match:
                    current['lines'] = match.group(1)
                # Extract file path
                match = re.search(r'Reference \d+: (.+?) \(', line)
                if match:
                    current['file_path'] = match.group(1)
        
        if current:
            references.append(current)
        
        return [r for r in references if r['code_preview']]

    def _extract_question(self, prompt):
        """Extract the actual user question from the prompt."""
        import re
        match = re.search(r'User Question: (.+?)(?:\n|$)', prompt)
        if match:
            return match.group(1).strip()
        return ""

    def _explain_references(self, question, references):
        """Generate explanation based on question and code."""
        question_lower = question.lower()
        
        explanation = ""
        
        if any(w in question_lower for w in ['directory', 'tree', 'structure', 'folder']):
            explanation = "These files are part of the project structure. "
            explanation += f"The main code is in `{references[0]['file_path']}`. "
            explanation += "Check the imports at the top of files to understand how they connect.\n\n"
        
        elif any(w in question_lower for w in ['how does', 'how is', 'explain']):
            explanation = f"Looking at `{references[0]['file_path']}`, "
            explanation += f"the `{references[0]['name']}` "
            explanation += f"({references[0]['chunk_type']}) handles this functionality. "
            explanation += "Read through the code to see the implementation details.\n\n"
        
        elif any(w in question_lower for w in ['what does', 'overview']):
            explanation = f"This project uses `{references[0]['file_path']}` "
            explanation += f"which contains `{references[0]['name']}`. "
            explanation += "Explore the related files to understand the full picture.\n\n"
        
        elif any(w in question_lower for w in ['bug', 'fix', 'issue', 'error']):
            explanation = f"Check `{references[0]['file_path']}` carefully. "
            explanation += "Look for:\n"
            explanation += "- Missing error handling\n"
            explanation += "- Edge cases not covered\n"
            explanation += "- Resource cleanup issues\n\n"
        
        else:
            explanation = f"The most relevant code is in `{references[0]['file_path']}`. "
            explanation += f"Focus on the `{references[0]['name']}` section. "
            explanation += "Related files may provide additional context.\n\n"
        
        explanation += "**Tip:** Click on the file references below to see the full code."
        return explanation

    def _generic_response(self):
        return """I'd be happy to help! However, I couldn't find code that directly matches your question.

Try asking:
- "What does this project do?"
- "Show me the directory structure"
- "Explain the main function"
- "How does [specific feature] work?"

Make sure you've loaded a repository first."""

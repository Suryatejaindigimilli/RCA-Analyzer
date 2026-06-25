"""Main chatbot orchestrator."""
from typing import List, Dict, Optional
from .github_client import git_client
from .code_chunker import code_chunker, CodeChunk
from .vector_store import vector_store
from .llm_client import LLMClient


class CodebaseChatbot:
    def __init__(self):
        self.llm = LLMClient()
        self.current_repo: Optional[Dict] = None
        self.repo_info: Optional[Dict] = None
        self.indexed_files = 0
        self.total_chunks = 0
        self.languages: Dict = {}
        self.chat_history: List[Dict] = []

    async def load_repository(self, repo_url: str) -> Dict:
        try:
            repo_data = git_client.parse_repo_url(repo_url)
            repo_path = git_client.clone_repo(repo_data)

            try:
                files = git_client.get_code_files(repo_path)
                if not files:
                    return {'status': 'error', 'message': 'No code files found in repository'}

                all_chunks: List[CodeChunk] = []
                for file_data in files:
                    chunks = code_chunker.chunk_file(file_data)
                    all_chunks.extend(chunks)

                if not all_chunks:
                    return {'status': 'error', 'message': 'Could not parse code from repository'}

                vector_store.clear()
                vector_store.build_index(all_chunks)

                self.current_repo = repo_data
                self.indexed_files = len(files)
                self.total_chunks = len(all_chunks)
                self.languages = self._detect_languages(files)
                self.chat_history = []
                self.repo_info = {
                    'name': f"{repo_data['owner']}/{repo_data['repo']}",
                    'platform': repo_data['platform'],
                    'url': repo_url
                }

                return {
                    'status': 'success',
                    'repo_info': self.repo_info,
                    'stats': {
                        'files_indexed': self.indexed_files,
                        'total_chunks': self.total_chunks,
                        'languages': self.languages,
                        'total_lines': sum(f['lines'] for f in files)
                    }
                }
            finally:
                git_client.cleanup()

        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
        except RuntimeError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            return {'status': 'error', 'message': f"Unexpected error: {str(e)}"}

    def _detect_languages(self, files: List[Dict]) -> Dict:
        lang_map = {
            '.py': 'Python', '.js': 'JavaScript', '.jsx': 'JavaScript',
            '.ts': 'TypeScript', '.tsx': 'TypeScript', '.java': 'Java',
            '.go': 'Go', '.rs': 'Rust', '.cpp': 'C++', '.c': 'C',
            '.rb': 'Ruby', '.php': 'PHP', '.cs': 'C#', '.kt': 'Kotlin',
            '.swift': 'Swift', '.scala': 'Scala', '.sh': 'Shell',
            '.md': 'Markdown', '.json': 'JSON', '.yml': 'YAML',
            '.yaml': 'YAML', '.html': 'HTML', '.css': 'CSS', '.sql': 'SQL'
        }
        languages = {}
        for f in files:
            lang = lang_map.get(f['extension'], 'Other')
            languages[lang] = languages.get(lang, 0) + 1
        return dict(sorted(languages.items(), key=lambda x: -x[1]))

    def chat(self, user_message: str) -> Dict:
        if self.current_repo is None:
            return {
                'response': "**No repository loaded!**\n\nPlease load a GitHub/Bitbucket repository first using the input above.",
                'references': []
            }

        self.chat_history.append({'role': 'user', 'content': user_message})

        relevant_chunks = vector_store.search(user_message, top_k=5)
        context = self._build_context(relevant_chunks)
        response = self._generate_response(user_message, context)

        self.chat_history.append({'role': 'assistant', 'content': response})

        return {
            'response': response,
            'references': [
                {
                    'file_path': c['file_path'],
                    'lines': f"{c['start_line']}-{c['end_line']}",
                    'chunk_type': c['chunk_type'],
                    'name': c['name'],
                    'relevance': c['relevance_score'],
                    'preview': c['content'][:300] + ('...' if len(c['content']) > 300 else '')
                }
                for c in relevant_chunks
            ]
        }

    def _build_context(self, chunks):
        if not chunks:
            return "No directly relevant code found in the indexed codebase."

        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(f"\n--- Reference {i}: {chunk['file_path']} (lines {chunk['start_line']}-{chunk['end_line']}) ---")
            parts.append(f"Type: {chunk['chunk_type']} | Name: {chunk['name']} | Language: {chunk['language']}")
            parts.append(f"Relevance: {chunk['relevance_score']:.2%}")
            parts.append("```")
            parts.append(chunk['content'][:1500])
            parts.append("```")

        return "\n".join(parts)

    def _generate_response(self, question, code_context):
        repo_name = self.repo_info.get('name', 'the repository') if self.repo_info else 'the repository'

        system_prompt = f"""You are an expert software engineer who has thoroughly analyzed the repository `{repo_name}`.

Your responses should be:
- **Specific**: Reference actual code, functions, files with line numbers
- **Helpful**: Answer as if you're a senior engineer who has read every file
- **Conversational**: Be friendly, direct, and clear
- **Practical**: Give actionable insights and examples

Format responses with markdown:
- Use code blocks with language hints
- Use headers for organization
- Use bullet points for lists
- Reference files like `src/main.py:42` when relevant"""

        user_prompt = f"""User Question: {question}

{code_context}

Please answer the user's question based on the code references above."""

        return self.llm.generate(system_prompt, user_prompt, max_tokens=2500)

    def get_status(self):
        return {
            'loaded': self.current_repo is not None,
            'repo_info': self.repo_info,
            'stats': {
                'files_indexed': self.indexed_files,
                'total_chunks': self.total_chunks,
                'languages': self.languages
            } if self.current_repo else None,
            'chat_history_length': len(self.chat_history)
        }

    def clear(self):
        self.current_repo = None
        self.repo_info = None
        self.indexed_files = 0
        self.total_chunks = 0
        self.languages = {}
        self.chat_history = []
        vector_store.clear()


chatbot = CodebaseChatbot()

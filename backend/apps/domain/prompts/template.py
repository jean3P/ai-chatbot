# apps/domain/prompts/template.py
"""
Prompt Template Manager

Handles loading and rendering versioned prompt templates.
"""
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from apps.domain.models import Chunk


class PromptTemplate:
    """
    Manages prompt templates using Jinja2

    Templates are versioned and stored in prompts/{version}/ directories.
    """

    def __init__(self, version: str = "v1.0"):
        """
        Initialize prompt template manager

        Args:
            version: Template version to use (e.g., "v1.0", "v1.1")
        """
        self.version = version

        # Get template directory
        base_dir = Path(__file__).parent
        template_dir = base_dir / version

        if not template_dir.exists():
            raise ValueError(f"Template version {version} not found at {template_dir}")

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,  # Don't escape for LLM input
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_system(self, context: List[Chunk], language: str = "en") -> str:
        """
        Render system prompt with context

        Args:
            context: List of retrieved chunks
            language: Language code (en, de, fr, es)

        Returns:
            Rendered system prompt string
        """
        template_name = f"system_{language}.j2"

        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound:
            # Fallback to English if language not found
            template = self.env.get_template("system_en.j2")

        return template.render(
            context=context,
            language=language,
            language_name=self._get_language_name(language),
        )

    def _get_language_name(self, code: str) -> str:
        """
        Get full language name from code

        Args:
            code: Language code

        Returns:
            Full language name
        """
        names = {"en": "English", "de": "German", "fr": "French", "es": "Spanish"}
        return names.get(code, "English")

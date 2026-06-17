import gettext
import logging
from typing import Optional
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
    Template,
    TemplateSyntaxError,
)

from infrastructure.templating.base_template_engine import BaseTemplateEngine

logger = logging.getLogger(__name__)


class JinjaI18nRenderer(BaseTemplateEngine):
    def __init__(
        self,
        template_dir: str = "templates",
        locale_dir: str = "locales",
        default_language: str = "en",
    ) -> None:
        """
        Initialize Jinja2 with i18n support.

        :param template_dir: Path to the Jinja2 templates folder.
        :param locale_dir: Path to the translation (.mo) files.
        :param default_language: Default language if none is specified.
        """
        self.template_dir = template_dir
        self.locale_dir = locale_dir
        self.default_language = default_language
        self.language = default_language
        self.env: Optional[Environment] = None
        self._initialize_environment()
        logger.info(
            f"JinjaI18nRenderer initialized with default language '{self.language}'."
        )

    def _initialize_environment(self) -> None:
        """
        Initializes the Jinja2 environment with the selected language.
        """
        translations = self._load_translations(self.language)

        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            extensions=["jinja2.ext.i18n"],
        )

        self.env.install_gettext_translations(translations, newstyle=True)
        logger.info(f"Jinja2 environment initialized with language '{self.language}'.")

    def _load_translations(self, language: str) -> gettext.NullTranslations:
        """
        Load the gettext translation object for the given language.

        :param language: The language code (e.g., 'en', 'es', 'fr').
        :return: A gettext translation object.
        """
        try:
            return gettext.translation(
                "messages",
                localedir=self.locale_dir,
                languages=[language],
                fallback=True,
            )
        except FileNotFoundError:
            logger.warning(
                f"Translation file not found for language '{language}', using fallback."
            )
            return gettext.NullTranslations()
        except Exception as e:
            logger.error(f"Error loading translation for '{language}': {e}")
            return gettext.NullTranslations()

    def set_language(self, language: str) -> None:
        """
        Change the language and reload the environment.

        :param language: Language code (e.g., 'en', 'es', 'fr').
        """
        if language != self.language:
            self.language = language
            self._initialize_environment()
            logger.info(f"Language changed to '{self.language}'.")

    def render_template(self, template_name: str, **kwargs) -> str:
        """
        Render a template with the given variables.

        :param template_name: Name of the template file.
        :param kwargs: Variables to pass into the template.
        :return: Rendered HTML string.
        :raises FileNotFoundError: If the template file does not exist.
        :raises TemplateSyntaxError: If there is a syntax error in the template.
        """
        try:
            template: Template = self.env.get_template(template_name)
            print(kwargs)
            return template.render(**kwargs)
        except FileNotFoundError:
            logger.error(
                f"Template '{template_name}' not found in '{self.template_dir}'."
            )
            raise FileNotFoundError(f"Template '{template_name}' not found.")
        except TemplateSyntaxError as e:
            logger.error(f"Syntax error in template '{template_name}': {e}")
            raise e
        except Exception as e:
            logger.error(f"Failed to render template '{template_name}': {e}")
            raise RuntimeError(f"Unexpected error while rendering template: {e}") from e

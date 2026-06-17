from abc import ABC, abstractmethod


class BaseTemplateEngine(ABC):
    @abstractmethod
    def render_template(self, template_name: str, **kwargs) -> str:
        """
        Render a template with the given variables.

        :param template_name: Name of the template file.
        :param kwargs: Variables to pass into the template.
        :return: Rendered string.
        """
        pass

    @abstractmethod
    def set_language(self, language: str) -> None:
        """
        Change the language.

        :param language: Language code (e.g., 'en', 'es', 'fr').
        """
        pass

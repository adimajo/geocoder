# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))

# -- Project information -----------------------------------------------------

project = "Geocoder"
author = "Paulo Emilio de Vilhena, Adrien Ehrhardt"
copyright = "2022-2026, Adrien Ehrhardt"  # noqa: A001

# the version lives in a single place, the package
release = version = re.search(r'^__version__ = ["\']([^"\']*)["\']',
                              (root / "geocoder" / "__init__.py").read_text(), re.M).group(1)

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
autosummary_imported_members = False
autodoc_default_options = {"members": True, "show-inheritance": True}
napoleon_google_docstring = True
napoleon_numpy_docstring = True
todo_include_todos = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_autosummary/*.inc"]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_theme_options = {"collapse_navigation": True, "includehidden": True}
html_static_path = ["_static"]

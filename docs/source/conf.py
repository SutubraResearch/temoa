# -*- coding: utf-8 -*-
#
import sys, os
import time


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute

# TODO:  There's gotta be a better way to do this.  Seems quite fragile.

# this first import is to provide path the temoa package, which is referenced throughout
# and must be included separately from path the source files so that it is properly recognized
sys.path.insert(0, os.path.abspath('../../'))
# this addition provided direct abbreviated link to the modules in the model
sys.path.insert(1, os.path.abspath('../../temoa/temoa_model'))





# -- Project information -----------------------------------------------------

project = 'Tools for Energy Model Optimization and Analysis (Temoa)'
copyright = '2020, NC State University'
author = 'Joe DeCarolis, Kevin Hunter'

# The short X.Y version
version = '3.0'
# The full version, including alpha/beta/rc tags
release = time.strftime( "%F", time.gmtime() )


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.todo',
    'sphinx.ext.githubpages',
    'sphinxcontrib.bibtex',
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

bibtex_bibfiles = ['References.bib']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['default/static']
# this stylesheet eliminates fixed width and is located in the _static directory
def setup(app):
    app.add_css_file('my_theme.css')


# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.
#
# html_sidebars = {}
#import sphinx_rtd_theme

#extensions = [
#    "sphinx_rtd_theme"
#]

html_theme = "sphinx_rtd_theme"
html_logo = "images/Temoa_logo_color_small.png"
latex_logo = 'images/TemoaLogo_grayscale.png'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

import datetime
import importlib.metadata
import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

# Verify the source path exists
if not os.path.exists(os.path.abspath('../src')):
    import warnings
    warnings.warn("Source directory '../src' not found. API documentation may be incomplete.")

# -- Project information -----------------------------------------------------

project = 'rms-spyceman'
copyright = f'{datetime.date.today().year}, SETI Institute'
author = 'SETI Institute'

# The full version, including alpha/beta/rc tags
try:
    release = importlib.metadata.version('rms-spyceman')
except importlib.metadata.PackageNotFoundError:
    release = '0.0.0'  # fallback for development

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinxcontrib.mermaid',
    'myst_parser',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# CONTRIBUTING.md is split in contributing.rst; the tail fragment starts at
# "## ..." so MyST reports a false-positive heading-level warning.
suppress_warnings = ['myst.header']

# The suffix(es) of source filenames.
source_suffix = ['.rst', '.md']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

add_module_names = False
autodoc_typehints_format = "short"

# Importing a host or solarsystem module calls into the SPICE toolkit at import time,
# which needs kernels that are not available on a docs builder. autodoc must not import
# what it cannot import.
autodoc_mock_imports = [
    'cspyce',
    'julian',
    'portion',
    'textkernel',
]

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Intersphinx settings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
}

# rms-polymath sets nitpicky = True here so that an unresolved cross-reference fails the
# build. This repo's docstrings still carry unfilled "xxx" type placeholders, so turning
# it on now would report hundreds of them. Enable it once those are written.
nitpicky = False

# MyST-Parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

# Mermaid settings — use client-side rendering so no mmdc binary is required
# in CI or on ReadTheDocs.
mermaid_output_format = 'raw'

# Generate anchor targets for Markdown headings so intra-document links in
# CONTRIBUTING.md (its table of contents) resolve.
myst_heading_anchors = 2

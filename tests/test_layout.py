##########################################################################################
# tests/test_layout.py: Checks on the repository layout itself
##########################################################################################
"""Checks on the repository layout itself.

These tests do not import the package; they only confirm that it lives where the
packaging configuration says it does and that every module parses. Behavior is covered
by test_import.py, test_utils.py, and test_docstrings.py.
"""

import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / 'src' / 'spyceman'


def test_package_is_under_src():
    """The src/ layout that pyproject.toml and docs/conf.py both assume."""
    assert PACKAGE_ROOT.is_dir()
    assert (PACKAGE_ROOT / '__init__.py').is_file()


def test_subpackages_are_present():
    """The two subpackages that the public API is built from."""
    for name in ('hosts', 'solarsystem'):
        assert (PACKAGE_ROOT / name / '__init__.py').is_file()


@pytest.mark.parametrize('path', sorted(PACKAGE_ROOT.rglob('*.py')),
                         ids=lambda p: str(p.relative_to(PACKAGE_ROOT)))
def test_module_compiles(path):
    """Every module parses.

    Parameters:
        path (pathlib.Path): Path to a module under the package root.
    """

    compile(path.read_text(encoding='utf-8'), str(path), 'exec')

##########################################################################################

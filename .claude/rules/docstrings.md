# Docstring standard

Every function, method, property, property setter, private helper, and nested closure in
`src/spyceman/` carries a Google-style docstring in the form below. Wrap every line at 90
columns, the same limit the code uses.

```python
def retrieve_online_file(source, dest, basename, dates=None, label=True):
    """Save a file from an online directory into the local downloads directory.

    Any optional longer description goes here, after a blank line.

    Parameters:
        source (str): URL of the online directory containing the file.
        dest (str, pathlib.Path): Subdirectory of the downloads directory to write to.
        basename (str): Basename of the file to retrieve.
        dates (dict, optional): Dictionary mapping basename to release date for every
            file in the source directory; used to set the file's timestamp.
        label (bool, optional): True to download any ".lbl" and ".cmt" files alongside
            the kernel itself.

    Returns:
        pathlib.Path: Absolute path to the saved file.

    Raises:
        ConnectionError: If the server does not return the file.
    """
```

## Sections

**Summary line.** One sentence, imperative or descriptive, on the same line as the opening
`"""`. A blank line separates it from anything that follows.

**`Parameters:`** — this exact header. Not `Args:`, not `Inputs:`, not `Input:`. Include
every parameter in the signature, in signature order, and nothing else. Omit `self` and
`cls`. Document `*args` and `**kwargs` under those names, asterisks included.

Each entry is `name (type): Description.` The type is the concrete Python type, or a
comma-separated tuple of them when more than one is accepted:

```text
    basename (str): Basename of a kernel file.
    kernel (Kernel, str): A Kernel object, or a basename to be wrapped in a KernelFile.
    version (int, str, tuple, set, optional): Version to match.
```

A parameter whose default is `None` is marked `optional` as the last element of the type
list. Continuation lines are indented four spaces beyond the parameter name.

**`Returns:`** — `type: Description of what the value means.` Include this section if and
only if the function can return a value. Functions that return nothing — setters,
`furnish()`, `walk()`, `add_property()` and the like — have no `Returns:` section.

**`Raises:`** — optional, and last when present. One entry per exception type the function
raises deliberately, as `ExceptionType: The condition that produces it.` Document what the
function itself raises, not everything that could propagate from its callees.

## Prohibited

- The generator placeholders `(xxx)`, `Xxx`, and `xxx: xxx`. If the meaning of a parameter
  is genuinely unclear, work it out from the code and write it down; do not leave a marker.
- Stray `#xxx` comments below a docstring (`#xxx Insert "*"?`, `#xxx Unknown arg name:`).
  Resolve whatever they refer to and delete them.
- Section headers other than `Parameters:`, `Returns:`, `Raises:`, and — for classes and files only —
  `Attributes:` and `Methods:`.

## Class docstrings

Classes and files follow the same conventions, using `Attributes:` and `Methods:` where useful. The
constructor's parameters are documented on `__init__`, not on the class.

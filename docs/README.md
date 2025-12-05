# Documentation Guide

This directory contains the Sphinx documentation for the Lightweight Charts Pro Backend.

## Building Documentation Locally

### Prerequisites

Install the documentation dependencies:

```bash
pip install -e ".[docs]"
```

### Build HTML Documentation

```bash
cd docs
make html
```

The built documentation will be in `docs/_build/html/`. Open `docs/_build/html/index.html` in your browser.

### Live Reload During Development

For live reloading while editing documentation:

```bash
cd docs
make livehtml
```

This will start a server at `http://127.0.0.1:8000` that automatically rebuilds on changes.

### Clean Build

To remove all built documentation and start fresh:

```bash
cd docs
make clean
make html
```

## Documentation Structure

```
docs/
├── conf.py           # Sphinx configuration
├── index.rst         # Main documentation page
├── modules.rst       # Auto-generated API documentation
├── api/
│   └── index.rst     # API endpoints documentation
├── examples.rst      # Usage examples
├── Makefile          # Build commands
└── _static/          # Static assets (CSS, images)
```

## Writing Documentation

### Docstring Format

We use **Google-style docstrings** exclusively. All docstrings are parsed by Sphinx's Napoleon extension.

#### Module Docstring Example

```python
"""Module description goes here.

This module provides functionality for X, Y, and Z. It is used in
conjunction with A and B to accomplish task C.
"""
```

#### Function Docstring Example

```python
def example_function(param1: str, param2: int = 0) -> bool:
    """Short description of what the function does.

    Longer description providing more context about the function's purpose,
    behavior, and any important implementation details.

    Args:
        param1: Description of param1. Can span multiple lines
            if needed for clarity.
        param2: Description of param2. Defaults to 0.

    Returns:
        bool: Description of what is returned.

    Raises:
        ValueError: When and why this exception is raised.
        TypeError: When and why this exception is raised.

    Example:
        >>> result = example_function("test", 42)
        >>> print(result)
        True

    Note:
        Any additional notes or warnings about the function.
    """
    pass
```

#### Class Docstring Example

```python
class ExampleClass:
    """Brief description of the class.

    Detailed description of what the class represents and its purpose
    in the system.

    Attributes:
        attribute1: Description of attribute1.
        attribute2: Description of attribute2.

    Example:
        >>> instance = ExampleClass()
        >>> instance.method()
    """

    def __init__(self, param1: str):
        """Initialize the class.

        Args:
            param1: Description of initialization parameter.
        """
        self.attribute1 = param1

    def method(self) -> str:
        """Brief description of method.

        Returns:
            str: Description of return value.
        """
        return self.attribute1
```

### Adding New Documentation Pages

1. Create a new `.rst` file in the `docs/` directory
2. Add the file to the `toctree` in `index.rst`
3. Write content using reStructuredText syntax
4. Build and preview your changes

### reStructuredText (RST) Basics

#### Headings

```rst
Main Heading
============

Sub Heading
-----------

Sub-sub Heading
~~~~~~~~~~~~~~~
```

#### Code Blocks

```rst
.. code-block:: python

   def example():
       return "Hello, World!"
```

#### Links

```rst
`Link text <https://example.com>`_

Internal link: :ref:`section-label`
```

#### Lists

```rst
Bullet list:

* Item 1
* Item 2
  * Nested item

Numbered list:

1. First item
2. Second item
```

## Automated Documentation

### GitHub Actions

Documentation is automatically built and deployed on every push to `main`/`master`:

1. **Documentation Build** (`.github/workflows/docs.yml`):
   - Builds Sphinx documentation
   - Checks for warnings/errors
   - Deploys to GitHub Pages (on main/master)

2. **CI/CD** (`.github/workflows/ci.yml`):
   - Runs linters on code
   - Runs tests
   - Ensures code quality before merging

### GitHub Pages

After pushing to `main`/`master`, documentation is automatically published to:
- `https://<username>.github.io/<repository>/`

Enable GitHub Pages in repository settings:
1. Go to Settings → Pages
2. Source: gh-pages branch
3. Root directory: `/` (root)

## Documentation Coverage

Check which parts of the code lack documentation:

```bash
cd docs
make coverage
```

This generates a report showing undocumented modules, classes, and functions.

## Continuous Improvement

### Documentation Checklist

- [ ] All public modules have module docstrings
- [ ] All public classes have class docstrings
- [ ] All public functions/methods have function docstrings
- [ ] All parameters are documented in Args section
- [ ] Return values are documented in Returns section
- [ ] Exceptions are documented in Raises section
- [ ] Examples are provided for complex functions
- [ ] Line length does not exceed 100 characters
- [ ] Docstrings follow Google style guide

### Best Practices

1. **Be Clear and Concise**: Avoid jargon when possible
2. **Provide Examples**: Show how to use the code
3. **Document Edge Cases**: Explain behavior for unusual inputs
4. **Keep It Updated**: Update docs when code changes
5. **Use Type Hints**: They appear in documentation automatically
6. **Link Related Functions**: Use `:func:`, `:class:`, `:mod:` directives

## Troubleshooting

### Build Errors

If you encounter build errors:

1. Check Sphinx warnings/errors in output
2. Verify all imports work: `python -c "import lightweight_charts_pro_backend"`
3. Clean and rebuild: `make clean && make html`
4. Check for RST syntax errors

### Missing Modules

If modules don't appear in documentation:

1. Verify module is in `sys.path` (see `conf.py`)
2. Check `__init__.py` has `__all__` exports
3. Ensure module is not in `exclude_patterns`

### Live Reload Not Working

```bash
pip install --upgrade sphinx-autobuild
make livehtml
```

## Additional Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Google Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Napoleon Extension](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)

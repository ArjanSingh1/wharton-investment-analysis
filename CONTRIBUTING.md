# Contributing

Contributions are welcome! Here's how you can help.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/wharton-investment-analysis.git
   ```
3. Create a branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. Set up your development environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Add your API keys to .env
   ```

## Making Changes

- Follow existing code patterns and conventions
- Keep changes focused - one feature or fix per PR
- Test your changes locally with `streamlit run app.py`
- Make sure no API keys or secrets are included in your commits

## Pull Request Process

1. Update documentation if your change affects usage
2. Write a clear PR description explaining what changed and why
3. Reference any related issues

## Reporting Issues

- Use GitHub Issues to report bugs or suggest features
- Include steps to reproduce for bugs
- Include your Python version and OS

## Code Style

- Follow existing patterns in the codebase
- Use type hints where the codebase already uses them
- Keep functions focused and reasonably sized

## Security

- **Never commit API keys or secrets**
- Report security vulnerabilities privately via GitHub security advisories
- Review `.gitignore` before committing

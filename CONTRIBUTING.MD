# Contributing

Thank you for your interest in contributing.

## Development Workflow

1. Fork the repository.
2. Create a feature branch.
3. Write tests.
4. Run formatting tools.
5. Submit a Pull Request.

## Coding Standards

- Follow PEP 8.
- Use type hints.
- Add docstrings for public functions.
- Keep Lambda functions focused on a single responsibility.

## Testing

Run:

```bash
pytest
```

before opening a Pull Request.

## Infrastructure

All infrastructure changes must be made through AWS SAM.

Do not manually modify AWS resources from the console unless testing locally.
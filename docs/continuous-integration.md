# encyc-tng — Continuous Integration

## Code styleguide

This project’s code formatting is enforced with [Prettier](https://prettier.io/) for supported languages, [black](https://github.com/psf/black) for Python, and [djhtml](https://github.com/rtts/djhtml) for templates. You may find it useful to have these tools integrated with your editor to auto-format when saving files, or they can be run manually before committing (`npm run fix:format {source_file_or_directory}` for Prettier, `python -m black {source_file_or_directory}` for Black and `djhtml {source_file_or_directory}` for djlint).

## Automatic linting locally

You can also run the linting tests automatically before committing. This is optional but will help prevent CI pipeline failures. We use `pre-commit` for this, which is included as a dev dependency in the pyproject.toml file, and configured using a pre-commit-config.yml file located at the root of the project directory.

!!! note
    If you are using the vscode dev container, all dependencies will be installed during build.

To make use of automatic checks when making commits on your host machine, you must install pre-commit, either create a virtualenv to use with the project (typically we take advantage of `poetry` to do this during dependency installation), or install globally (see instructions at https://pre-commit.com/#install).

Pre-commit will not run by default. To set it up, run `pre-commit install` on your host machine.

The `detect-secrets` pre-commit hook requires a baseline secrets file to be included. If you need to, you can update this file, e.g. when adding dummy secrets for unit tests:

```bash
$ detect-secrets scan > .secrets.baseline
```

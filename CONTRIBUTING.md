# Contributing

## Setup

Use Python 3.11 or newer. From the root of your clone, create a virtual
environment and install the package with its development dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Before you push

Run the same checks as CI. GitHub Actions runs them on Python 3.11 and 3.12
for pull requests and pushes to `main`.

```bash
ruff check .
ruff format --check .
pytest
```

Use `ruff check --fix .` to apply available lint fixes and `ruff format .`
to format the code. Review the diff before committing.

## Tests

Keep the test suite runnable without Cloudflare credentials. When testing how
the driver handles a SQL API response, look for a matching sample in
[tests/fixtures/responses](tests/fixtures/responses). To query a live dataset
or record a new sample, follow the [Cloudflare test setup](dev/cloudflare/README.md).

## Branches and pull requests

Start each change on a branch based on the latest `main`.

```bash
git fetch origin
git switch --no-track -c my-change origin/main
```

Keep the pull request focused on one change and include tests for changes in
behavior. Push your branch with `git push -u origin my-change`, open a pull
request against `main`, and describe what changed and how you tested it.

If your branch needs an update from `main`, run `git fetch origin` and
`git rebase origin/main`. After rebasing a branch you already pushed,
update it with `git push --force-with-lease`.

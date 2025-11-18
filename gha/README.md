# GitHub Actions Workflows

This folder contains GitHub Actions workflows for CI/CD. Due to permission constraints, these files are stored in the `gha/` folder instead of `.github/workflows/`.

## Activating the Workflows

To activate these workflows, move them to the `.github/workflows/` directory:

```bash
# Create the .github/workflows directory if it doesn't exist
mkdir -p .github/workflows

# Move the workflow files
cp gha/ci.yml .github/workflows/
cp gha/docker.yml .github/workflows/

# Commit the changes
git add .github/workflows/
git commit -m "Add GitHub Actions workflows"
git push
```

Alternatively, you can use this one-liner:

```bash
mkdir -p .github/workflows && cp gha/*.yml .github/workflows/ && git add .github/workflows/ && git commit -m "Add GitHub Actions workflows" && git push
```

## Workflows Included

### 1. CI Workflow (`ci.yml`)

This workflow runs on pull requests and pushes to main/master branches. It includes:

- **Lint and Format Check**: Runs `ruff check` and `ruff format --check`
- **Unit Tests**: Runs tests in `tests/unit/` with coverage reporting
- **Integration Tests**: Runs tests in `tests/integration/` with PostgreSQL service
- **All Checks**: A final job that ensures all checks passed

The workflow will block PR merges if any check fails.

### 2. Docker Build and Push (`docker.yml`)

This workflow:

- Builds the Docker image on every push and PR
- Pushes to GitHub Container Registry (ghcr.io) on pushes to main/master
- Creates multi-architecture images (amd64, arm64)
- Generates proper tags based on branch, PR, or semantic version
- Creates build provenance attestations

## Running Checks Locally

Before pushing, you can run the same checks locally:

### Linting
```bash
uv run ruff check .
```

### Formatting
```bash
# Check formatting
uv run ruff format --check .

# Fix formatting
uv run ruff format .
```

### Unit Tests
```bash
uv run pytest tests/unit -v --cov=src/todo
```

### Integration Tests
```bash
# Requires PostgreSQL running
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/smarttodo_test"
export SECRET_KEY="test-secret-key-minimum-32-characters-long-for-testing"
export OTEL_ENABLED="false"
uv run pytest tests/integration -v
```

### All Tests
```bash
uv run pytest -v --cov=src/todo
```

### Docker Build
```bash
docker build -t smarttodo:local .
```

## Configuration

### Secrets Required

For the Docker workflow to push to ghcr.io, no additional secrets are needed - it uses the built-in `GITHUB_TOKEN`.

### Branch Protection

To enforce these checks before merging PRs, configure branch protection rules:

1. Go to Settings > Branches
2. Add a branch protection rule for `main` (or `master`)
3. Enable "Require status checks to pass before merging"
4. Select the following required checks:
   - Lint and Format Check
   - Unit Tests
   - Integration Tests
   - All Checks Passed

## Troubleshooting

### Workflow not running?

- Ensure the files are in `.github/workflows/` (not `gha/`)
- Check that the branch name matches the workflow triggers
- Verify Actions are enabled in repository settings

### Tests failing in CI but passing locally?

- Check environment variables in the workflow
- Ensure all dependencies are in `pyproject.toml`
- Look for database-specific issues with PostgreSQL vs SQLite

### Docker build failing?

- Verify the Dockerfile syntax
- Check that all necessary files are not in `.dockerignore`
- Ensure `uv` can resolve dependencies

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Action](https://github.com/docker/build-push-action)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)

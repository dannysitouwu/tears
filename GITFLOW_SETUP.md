# GitFlow Setup Instructions

## 1. Branch Protection Rules (GitHub)

### For `main` branch:
1. Go to GitHub repository → Settings → Branches
2. Add branch protection rule for `main`:
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators
   - ✅ Restrict who can push to matching branches

### For `develop` branch:
1. Create `develop` branch:
   ```bash
   git checkout -b develop
   git push -u origin develop
   ```
2. Add branch protection rule for `develop`:
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging

## 2. GitHub Secrets

Add these secrets in GitHub → Settings → Secrets and variables → Actions:

```
HETZNER_HOST: your-server-ip
HETZNER_USERNAME: your-ssh-username
SSH_PRIVATE_KEY: your-private-ssh-key
```

## 3. GitFlow Workflow

### Creating a new feature:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
# Make changes...
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature-name
# Create PR to develop on GitHub
```

### Creating a release:
```bash
git checkout develop
git pull origin develop
git checkout -b release/v1.0.0
# Update version numbers, changelog
git commit -m "chore: prepare release v1.0.0"
git push origin release/v1.0.0
# Create PR to main on GitHub
# After merge to main, also merge back to develop
```

### Hotfix:
```bash
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug
# Fix the bug...
git commit -m "fix: critical bug description"
git push origin hotfix/critical-bug
# Create PR to main
# After merge to main, also merge to develop
```

## 4. Branch Naming Convention

- Feature: `feature/user-authentication`
- Bugfix: `bugfix/fix-login-error`
- Hotfix: `hotfix/security-patch`
- Release: `release/v1.0.0`

## 5. Commit Message Convention

Follow Conventional Commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation changes
- `style:` formatting, missing semicolons, etc.
- `refactor:` code refactoring
- `test:` adding tests
- `chore:` maintenance tasks

Example:
```bash
git commit -m "feat: add WebSocket message broadcasting"
git commit -m "fix: resolve authentication token expiry issue"
git commit -m "test: add unit tests for chat endpoints"
```

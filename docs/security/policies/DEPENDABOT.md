# Dependabot Configuration

## Overview

Dependabot is configured to automatically scan and update dependencies across three ecosystems:
- **Python** (pip) - Backend dependencies
- **npm** - Frontend dependencies  
- **GitHub Actions** - CI/CD workflow dependencies

## Update Schedule

| Ecosystem | Frequency | Day | Time |
|-----------|-----------|-----|------|
| pip | Weekly | Monday | 09:00 UTC |
| npm | Weekly | Monday | 09:00 UTC |
| github-actions | Monthly | - | - |

## Auto-merge Policy (Conservative)

### ✅ Auto-merge Enabled For

Dependabot PRs will be **automatically merged** ONLY if ALL conditions are met:

1. **Update Type**: Patch updates only (`x.x.X`)
2. **Dependency Type**: Development/tooling dependencies only
3. **Label**: Must have `automerge-approved` label (manual)
4. **Tests**: ALL security checks must pass:
   - Secret scanning (Gitleaks)
   - Python dependency audit (pip-audit)
   - Frontend dependency audit (npm audit)
   - Auth contract tests
   - Frontend bundle budget

### Safe Dependencies Whitelist

Auto-merge is allowed for these development dependencies:
- `pytest`, `black`, `flake8`, `mypy` (Python testing/linting)
- `eslint`, `prettier`, `@types/*` (Frontend tooling)

### ⚠️ Manual Review Required For

- **Minor updates** (`x.X.x`) - May include new features
- **Major updates** (`X.x.x`) - Breaking changes expected
- **Production dependencies** (fastapi, react, sqlalchemy, etc.)
- **Security updates** - Flagged with comment for immediate review
- **Any update without `automerge-approved` label**

## Workflow

1. **Monday 09:00 UTC**: Dependabot scans for updates
2. **PR Created**: Dependabot opens PR with update
3. **CI Runs**: All security checks execute automatically
4. **Auto-merge Check**:
   - If patch + dev dependency + has label → Auto-merge
   - Otherwise → Waits for manual review
5. **Security Alert**: If security update detected, comment added

## Adding `automerge-approved` Label

To enable auto-merge for a specific PR:

```bash
# Via GitHub CLI
gh pr edit <PR_NUMBER> --add-label "automerge-approved"

# Via GitHub UI
# Go to PR → Labels → Add "automerge-approved"
```

**⚠️ Only add this label after reviewing the changelog and confirming the update is safe.**

## Disabling Auto-merge

To disable auto-merge globally:

1. Remove the `dependabot-auto-merge` job from `.github/workflows/security.yml`
2. Or remove the `automerge-approved` label from all PRs

## Monitoring

- **Dependabot PRs**: Check weekly on Mondays
- **Security Updates**: Review immediately when flagged
- **Failed Checks**: Investigate and fix before merging

## Configuration Files

- `.github/dependabot.yml` - Dependabot configuration
- `.github/workflows/security.yml` - Auto-merge workflow

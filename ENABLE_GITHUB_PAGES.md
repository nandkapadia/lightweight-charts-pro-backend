# Enabling GitHub Pages for Documentation

This guide will help you enable GitHub Pages to automatically deploy your Sphinx documentation.

## Prerequisites

Your repository already has:
- ✅ `.github/workflows/docs.yml` - Workflow that builds and deploys docs
- ✅ Sphinx documentation in `docs/` directory
- ✅ All documentation committed to `dev` branch

## Step 1: Merge to Main Branch

First, merge the `dev` branch into `main` or `master`:

### Option A: Via GitHub Web Interface (Recommended)

1. Go to: https://github.com/nandkapadia/lightweight-charts-pro-backend/pull/new/dev
2. Click "Create pull request"
3. Review the changes
4. Click "Merge pull request"
5. Click "Confirm merge"

### Option B: Via Command Line

```bash
# Switch to main branch
git checkout master

# Merge dev branch
git merge dev

# Push to remote
git push origin master
```

## Step 2: Wait for GitHub Actions to Run

After merging, the documentation workflow will automatically:
1. Build the Sphinx documentation
2. Create a `gh-pages` branch (if it doesn't exist)
3. Deploy the HTML files to the `gh-pages` branch

**Check the workflow status:**
- Go to: https://github.com/nandkapadia/lightweight-charts-pro-backend/actions
- Wait for the "Documentation" workflow to complete (green checkmark)

## Step 3: Enable GitHub Pages

Once the `gh-pages` branch exists:

1. **Go to Repository Settings:**
   - Navigate to: https://github.com/nandkapadia/lightweight-charts-pro-backend/settings/pages

2. **Configure Source:**
   - Under "Build and deployment"
   - Source: Select **"Deploy from a branch"**
   - Branch: Select **"gh-pages"**
   - Folder: Select **"/ (root)"**
   - Click **"Save"**

3. **Wait for Deployment:**
   - GitHub will show: "Your site is ready to be published at..."
   - Wait 1-2 minutes for the initial deployment

## Step 4: Access Your Documentation

Your documentation will be available at:

```
https://nandkapadia.github.io/lightweight-charts-pro-backend/
```

### Custom Domain (Optional)

If you want to use a custom domain:

1. In the same GitHub Pages settings page
2. Under "Custom domain"
3. Enter your domain (e.g., `docs.example.com`)
4. Click "Save"
5. Add a CNAME record in your DNS settings pointing to `nandkapadia.github.io`

## Verification

After enabling, verify your documentation:

1. **Visit the URL:**
   ```
   https://nandkapadia.github.io/lightweight-charts-pro-backend/
   ```

2. **Check these pages:**
   - Main page (index)
   - API Reference
   - Examples
   - Module documentation

## Troubleshooting

### Issue: "404 - There isn't a GitHub Pages site here"

**Solution:**
1. Check that the `gh-pages` branch exists:
   ```bash
   git ls-remote --heads origin
   ```
2. Verify GitHub Actions completed successfully
3. Wait a few minutes and try again

### Issue: "gh-pages branch doesn't exist"

**Solution:**
1. Manually trigger the workflow:
   - Go to: https://github.com/nandkapadia/lightweight-charts-pro-backend/actions/workflows/docs.yml
   - Click "Run workflow"
   - Select branch: `master` or `main`
   - Click "Run workflow"

### Issue: "Documentation is outdated"

**Solution:**
Documentation updates automatically on every push to `main`/`master`. To force an update:
```bash
# Make a trivial change
git commit --allow-empty -m "Trigger documentation rebuild"
git push
```

## Automatic Updates

Once enabled, your documentation will automatically update when:
- You push to the `main` or `master` branch
- The `.github/workflows/docs.yml` workflow runs
- Changes are made to any `.py` files or `.rst` files

## CI/CD Badge (Optional)

Add a documentation badge to your README:

```markdown
[![Documentation](https://github.com/nandkapadia/lightweight-charts-pro-backend/actions/workflows/docs.yml/badge.svg)](https://nandkapadia.github.io/lightweight-charts-pro-backend/)
```

## Using GitHub CLI (Alternative)

If you have GitHub CLI installed, you can enable Pages via command line:

```bash
# Install GitHub CLI if needed
# macOS: brew install gh
# Linux: See https://cli.github.com/

# Enable GitHub Pages
gh api -X POST repos/nandkapadia/lightweight-charts-pro-backend/pages \
  -f source[branch]=gh-pages \
  -f source[path]=/
```

## Summary

After completing these steps:

✅ Documentation builds automatically on every push
✅ Latest docs always available at GitHub Pages URL
✅ No manual deployment needed
✅ Professional documentation hosting

## Support

If you encounter issues:
1. Check GitHub Actions logs for errors
2. Review the workflow file: `.github/workflows/docs.yml`
3. Verify Sphinx builds locally: `cd docs && make html`
4. Check GitHub Pages settings are correct

---

**Note:** The first deployment may take 1-2 minutes. Subsequent updates are usually faster.

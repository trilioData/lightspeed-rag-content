# OpenShift LightSpeed RAG Content - Development Guide for AI

## Git and PR Workflow

### Commit Messages
- Start with the Jira ticket reference: `:book: TK-XXXX description`
- Keep the first line under 72 characters
- Use imperative mood

### Pull Requests
This repo uses a **following workflow**:

1. **Push to origin**, (triliodata/lightspeed-rag-content)
2. **Create the PR** against `origin/main` using your branch:
   ```bash
   git push origin <branch>
   gh pr create --repo triliodata/lightspeed-rag-content --head --base main
   ```
3. **PR title** must start with the Jira reference: `:book: TK-XXXX description`
4. **Squash commits** before pushing -- one logical commit per PR unless the PR explicitly tracks multiple independent changes

### Branch Completion
When finishing a development branch:
1. Remove any process artifacts (design docs, plans in `docs/superpowers/`)
2. Squash commits with the Jira-prefixed message
3. Push to the contributor's branch
4. Create the PR against `origin/main`

# agentTestRepo

## 🤖 Automated AI Code Review

Every push to this repository automatically triggers an AI-powered code review via GitHub Actions.  
The review is posted as a **commit comment** so you can see it directly on the commit page.

### How it works

1. The [`.github/workflows/ai-code-review.yml`](.github/workflows/ai-code-review.yml) workflow fires on every `push`.
2. It checks out the code, computes the `git diff` between the new commit and its parent, and passes it to OpenAI's `gpt-4o` model.
3. The AI review is posted as a commit comment using the GitHub REST API.

### Setup

1. Generate an [OpenAI API key](https://platform.openai.com/api-keys).
2. Add it as a repository secret named **`OPENAI_API_KEY`**:  
   **Settings → Secrets and variables → Actions → New repository secret**
3. Push any change – the workflow will run automatically and post a review on the commit.

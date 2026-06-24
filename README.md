# 👁️ Argus: The Serverless Code Guardian

![Python](https://img.shields.io/badge/Python-3.9-blue?style=for-the-badge&logo=python)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Serverless-2088FF?style=for-the-badge&logo=github-actions)
![Groq AI](https://img.shields.io/badge/AI-Groq_Llama-FF6B00?style=for-the-badge)

> **"A fully automated, serverless AI Code Reviewer that lives inside your GitHub Actions pipeline."**

Argus is an AI-powered bot that automatically reviews Pull Requests. It acts as a first line of defense, catching security vulnerabilities (SQL Injection, hardcoded secrets) and logic bugs before a human ever looks at the code.

## 📸 See it in Action
Check out a live demonstration of Argus catching bugs in a real Pull Request:
👉 **[View the Live Demo PR](https://github.com/Maheshdindur/Argus-The-Serverless-Code-Guardian/pull/2)**

---

## 🚀 How It Works
Argus eliminates the need for expensive servers, webhooks, or complex Docker containers. It runs entirely on **GitHub Actions**.

1.  **Trigger:** A developer opens or updates a Pull Request.
2.  **Action:** GitHub spins up a temporary runner and executes the Argus script.
3.  **Analysis:** The code "diff" is retrieved and sent to **Groq** for deep analysis.
4.  **Verdict:**
    * ✅ **APPROVE:** If code is clean, Argus posts a "Success" comment.
    * ⚠️ **REQUEST CHANGES:** If bugs are found, Argus **blocks the merge** and posts a review explaining the fix.

---


## ⚙️ Setup & Installation

You do not need to modify your application code to use Argus. Just follow these steps to add the workflow to your repository:

### 1. Get a Groq API Key
Obtain an API key from [GroqCloud](https://console.groq.com/keys).

### 2. Add Secrets to GitHub
Go to your repository **Settings** > **Secrets and variables** > **Actions** and add:
* `GROQ_API_KEY`: Paste your Groq API key here.
* `GITHUB_TOKEN`: (Optional) GitHub usually provides this automatically, but ensure workflow permissions are enabled.

### 3. Create the Workflow
Create a file at `.github/workflows/reviewer.yml` with the following content:

```yaml
name: AI Code Reviewer

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write
  issues: write
  statuses: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Run Argus AI Reviewer
        uses: Maheshdindur/Argus-The-Serverless-Code-Guardian@main
        with:
          groq_api_key: ${{ secrets.GROQ_API_KEY }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          # Optional. Default is llama-3.1-8b-instant.
          groq_model: llama-3.1-8b-instant
```

For a stable Marketplace install, replace `@main` with your published release tag, for example `@v1`.

## 🛠️ Architecture

```mermaid
graph LR
    A[Developer Opens PR] -->|Trigger| B(GitHub Actions);
    B -->|Read Code Diff| C{Argus Python Script};
    C -->|API Call| D[Groq AI];
    D -->|Analysis Result| C;
    C -->|Post Comment| E[Pull Request];
    C -->|Block Merge| F[Branch Protection];

# 👁️ Argus: The Serverless Code Guardian

![Python](https://img.shields.io/badge/Python-3.9-blue?style=for-the-badge&logo=python)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Serverless-2088FF?style=for-the-badge&logo=github-actions)
![Gemini AI](https://img.shields.io/badge/AI-Google_Gemini_2.5-8E75B2?style=for-the-badge)

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
3.  **Analysis:** The code "diff" is retrieved and sent to **Google Gemini (2.5 Flash)** for deep analysis.
4.  **Verdict:**
    * ✅ **APPROVE:** If code is clean, Argus posts a "Success" comment.
    * ⚠️ **REQUEST CHANGES:** If bugs are found, Argus **blocks the merge** and posts a review explaining the fix.

---


## ⚙️ Setup & Installation

You do not need to modify your application code to use Argus. Just follow these steps to add the workflow to your repository:

### 1. Get a Gemini API Key
Obtain a free API key from [Google AI Studio](https://aistudio.google.com/).

### 2. Add Secrets to GitHub
Go to your repository **Settings** > **Secrets and variables** > **Actions** and add:
* `GOOGLE_API_KEY`: Paste your Gemini API key here.
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

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install Dependencies
        run: pip install google-generativeai requests

      - name: Run AI Reviewer
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_EVENT_PATH: ${{ github.event_path }}
        run: python scripts/reviewer.py
```

## 🛠️ Architecture

```mermaid
graph LR
    A[Developer Opens PR] -->|Trigger| B(GitHub Actions);
    B -->|Read Code Diff| C{Argus Python Script};
    C -->|API Call| D[Google Gemini AI];
    D -->|Analysis Result| C;
    C -->|Post Comment| E[Pull Request];
    C -->|Block Merge| F[Branch Protection];

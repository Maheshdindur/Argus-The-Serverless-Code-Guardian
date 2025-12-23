# 👁️ Argus: The Serverless Code Guardian

![Python](https://img.shields.io/badge/Python-3.9-blue?style=for-the-badge&logo=python)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Serverless-2088FF?style=for-the-badge&logo=github-actions)
![Gemini AI](https://img.shields.io/badge/AI-Google_Gemini_2.5-8E75B2?style=for-the-badge)

> **"A fully automated, serverless AI Code Reviewer that lives inside your GitHub Actions pipeline."**

Argus is an AI-powered bot that automatically reviews Pull Requests. It acts as a first line of defense, catching security vulnerabilities (SQL Injection, hardcoded secrets) and logic bugs before a human ever looks at the code.

---

## 🚀 How It Works
Argus eliminates the need for expensive servers, webhooks, or complex Docker containers. It runs entirely on **GitHub Actions**.

1.  **Trigger:** A developer opens a Pull Request.
2.  **Action:** GitHub spins up a temporary runner and executes the Argus script.
3.  **Analysis:** The code "diff" is sent to **Google Gemini (2.5 Flash)** for deep analysis.
4.  **Verdict:**
    * ✅ **APPROVE:** If code is clean, Argus posts a "Success" comment.
    * ⚠️ **REQUEST CHANGES:** If bugs are found, Argus **blocks the merge** and explains the fix.

---

## 🛠️ Architecture

```mermaid
graph LR
    A[Developer Opens PR] -->|Trigger| B(GitHub Actions);
    B -->|Read Code Diff| C{Argus Python Script};
    C -->|API Call| D[Google Gemini AI];
    D -->|Analysis Result| C;
    C -->|Post Comment| E[Pull Request];
    C -->|Block Merge| F[Branch Protection];
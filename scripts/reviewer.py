import os
import json
import requests
import re
import sys  # <--- Added to allow stopping the workflow
from groq import Groq

# --- 1. SETUP & CONFIGURATION ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

# Get the link to the current GitHub Actions Run (for status checks)
RUN_ID = os.environ.get("GITHUB_RUN_ID")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")
DETAILS_URL = f"https://github.com/{REPO_NAME}/actions/runs/{RUN_ID}"

if not GITHUB_TOKEN or not GROQ_API_KEY:
    print("❌ Error: Secrets missing. Make sure GITHUB_TOKEN and GROQ_API_KEY are set in Settings > Secrets.")
    sys.exit(1)

# Configure Groq
client = Groq(api_key=GROQ_API_KEY)

# --- 2. LOAD GITHUB WEBHOOK DATA ---
def load_github_payload():
    """Reads the webhook JSON data provided by GitHub Actions."""
    event_path = os.getenv('GITHUB_EVENT_PATH')
    
    if not event_path or not os.path.exists(event_path):
        print(f"❌ Error: GITHUB_EVENT_PATH not found at {event_path}")
        sys.exit(1)

    with open(event_path, 'r') as f:
        return json.load(f)

payload = load_github_payload()

# --- 3. HELPER FUNCTIONS ---

def post_comment(comments_url, body):
    """Posts the AI's review as a comment on the Pull Request."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    final_body = body + "\n\n_— Reviewed by Argus (Serverless AI) 🤖_"
    response = requests.post(comments_url, json={"body": final_body}, headers=headers)
    if response.status_code == 201:
        print("✅ Comment posted successfully.")
    else:
        print(f"❌ Failed to post comment: {response.text}")

def update_pr_status(statuses_url, state, description):
    """Updates the PR status check (Green checkmark or Red X)."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "state": state,       # 'success', 'failure', 'error', or 'pending'
        "target_url": DETAILS_URL,  # Link to the Actions Logs
        "description": description,
        "context": "Argus / AI-Reviewer"
    }
    requests.post(statuses_url, json=data, headers=headers)

def get_pr_diff(diff_url):
    """Downloads the code changes (diff) from GitHub."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.diff" # Important header to get raw diff
    }
    response = requests.get(diff_url, headers=headers)
    return response.text if response.status_code == 200 else None

def get_changed_files(files_url):
    """Returns the files changed in this pull request."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(files_url, headers=headers)
    if response.status_code != 200:
        print(f"⚠️ Could not fetch changed files: {response.text}")
        return []
    return [file_info.get("filename", "") for file_info in response.json()]

def find_secret_leaks(diff_text):
    """Finds likely secrets added by this pull request."""
    secret_patterns = [
        ("Groq API key", r"gsk_[A-Za-z0-9_-]{20,}"),
        ("GitHub token", r"gh[pousr]_[A-Za-z0-9_]{20,}"),
        ("OpenAI API key", r"sk-[A-Za-z0-9_-]{20,}"),
        ("AWS access key", r"AKIA[0-9A-Z]{16}"),
        ("Private key", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ]

    findings = []
    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for label, pattern in secret_patterns:
            if re.search(pattern, line):
                findings.append(label)
    return sorted(set(findings))

def is_documentation_file(filename):
    """Returns True for files that should only be checked for sensitive data."""
    lower_name = filename.lower()
    docs_extensions = (".md", ".mdx", ".txt", ".rst")
    docs_paths = ("docs/", ".github/issue_template/", ".github/pull_request_template")
    return lower_name.endswith(docs_extensions) or lower_name.startswith(docs_paths)

def is_docs_only_change(changed_files):
    """Returns True when a PR only changes documentation/text files."""
    return bool(changed_files) and all(is_documentation_file(filename) for filename in changed_files)

def get_groq_review(prompt):
    """Sends a review prompt to Groq and returns the model response."""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are Argus, a concise senior software engineer reviewing pull requests.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
        max_completion_tokens=2048,
    )
    return response.choices[0].message.content

def analyze_code_with_groq(diff_text, pr_title, user):
    """Sends the code diff to Groq for analysis."""
    # Truncate if too huge to prevent token errors
    if len(diff_text) > 40000:
        diff_text = diff_text[:40000] + "\n... (Diff truncated for size)"

    prompt = f"""
    You are 'Argus', a Senior Software Engineer bot.
    Review only the changed lines in this PR from @{user}.
    PR Title: {pr_title}
    
    Code Changes (Diff):
    ```diff
    {diff_text}
    ```
    
    Instructions:
    1. Base your review only on the diff above. Do not invent repository-wide issues.
    2. Request changes only when the changed code clearly introduces a real bug, broken behavior, security vulnerability, syntax/runtime error, or serious performance regression.
    3. Do not block for style preferences, missing tests, missing comments, generic best practices, or broad improvement suggestions.
    4. Keep the review short. Mention only the most important findings from the changed code.
    5. **CRITICAL**: End your review with exactly one of these two verdicts:
       - '✅ **APPROVE**' (if code looks safe)
       - '⚠️ **REQUEST CHANGES**' (if there are security risks or major bugs)
    """
    
    try:
        return get_groq_review(prompt)
    except Exception as e:
        return f"⚠️ **AI Error:** Groq failed to respond. Details: {str(e)}"

def analyze_docs_with_groq(diff_text, pr_title, user):
    """Reviews documentation/text changes only for sensitive data exposure."""
    if len(diff_text) > 40000:
        diff_text = diff_text[:40000] + "\n... (Diff truncated for size)"

    prompt = f"""
    You are 'Argus', a Senior Software Engineer bot.
    Review this documentation/text-only PR from @{user}.
    PR Title: {pr_title}

    Documentation/Text Changes (Diff):
    ```diff
    {diff_text}
    ```

    Instructions:
    1. Only check whether the changed text exposes sensitive data, such as API keys, tokens, passwords, private keys, credentials, or private endpoints.
    2. Do not review the writing style, formatting, grammar, project quality, tests, code architecture, or implementation details.
    3. If no sensitive data is present, write a short approval comment that says the sensitive-data check passed and the PR is ready for maintainer review.
    4. If sensitive data is present, request changes and tell the author to remove it, rotate the exposed credential, and use repository secrets.
    5. Keep the tone professional and direct.
    6. **CRITICAL**: End your review with exactly one of these two verdicts:
       - '✅ **APPROVE**' (if no sensitive data is found)
       - '⚠️ **REQUEST CHANGES**' (if sensitive data is found)
    """

    try:
        return get_groq_review(prompt)
    except Exception as e:
        return f"⚠️ **AI Error:** Groq failed to respond. Details: {str(e)}"

def explain_secret_leak_with_groq(leaked_secrets, pr_title, user):
    """Asks Groq to write a safe secret-leak review without sending raw secrets."""
    prompt = f"""
    You are 'Argus', a Senior Software Engineer bot.
    A PR from @{user} titled "{pr_title}" appears to add sensitive data.

    Detected secret types:
    {", ".join(leaked_secrets)}

    Instructions:
    1. Write a concise PR review comment.
    2. Do not ask for or reveal the secret value.
    3. Tell the author to remove the credential, rotate it immediately, and store future values in GitHub Actions secrets or the appropriate secret manager.
    4. Keep the tone professional and direct.
    5. End with exactly this verdict:
       ⚠️ **REQUEST CHANGES**
    """

    try:
        return get_groq_review(prompt)
    except Exception:
        return (
            "Potential secret leak detected in the added lines: "
            + ", ".join(leaked_secrets)
            + ". Remove the secret from the PR, rotate the exposed credential, and store it in GitHub Actions secrets instead.\n\n"
            + "⚠️ **REQUEST CHANGES**"
        )

# --- 4. MAIN EXECUTION ---
def run():
    print("--- 🚀 ARGUS REVIEWER STARTING ---")

    # 1. Check if this is a Pull Request event
    if "pull_request" not in payload:
        print("This workflow was triggered, but no Pull Request data found. Exiting.")
        return

    # 2. Extract Data
    pr = payload["pull_request"]
    diff_url = pr["diff_url"]
    files_url = pr["url"] + "/files"
    comments_url = pr["comments_url"]
    statuses_url = pr["statuses_url"]
    pr_title = pr["title"]
    user = pr["user"]["login"]

    print(f"👀 Reviewing PR: {pr_title} by @{user}")

    # 3. Download the Code Diff
    code_diff = get_pr_diff(diff_url)
    if not code_diff or not code_diff.strip():
        print("❌ Could not retrieve code diff. Exiting.")
        return

    changed_files = get_changed_files(files_url)
    print(f"Changed files: {', '.join(changed_files) if changed_files else 'unknown'}")

    leaked_secrets = find_secret_leaks(code_diff)
    if leaked_secrets:
        review = explain_secret_leak_with_groq(leaked_secrets, pr_title, user)
        post_comment(comments_url, review)
        update_pr_status(statuses_url, "failure", "Potential secret leak detected.")
        print("❌ Potential secret leak detected. Blocking merge.")
        sys.exit(1)

    if is_docs_only_change(changed_files):
        print(f"🧠 Sending documentation/text changes to Groq ({GROQ_MODEL})...")
        review = analyze_docs_with_groq(code_diff, pr_title, user)
        post_comment(comments_url, review)

        if "⚠️ **REQUEST CHANGES**" in review:
            update_pr_status(statuses_url, "failure", "Sensitive data found in documentation changes.")
            print("❌ Documentation/text review requested changes.")
            sys.exit(1)

        update_pr_status(statuses_url, "success", "Documentation/text review passed.")
        print("✅ Documentation/text review passed.")
        return

    # 4. Ask Groq
    print(f"🧠 Sending code to Groq ({GROQ_MODEL})...")
    review = analyze_code_with_groq(code_diff, pr_title, user)

    # 5. Post the Result
    post_comment(comments_url, review)

    # 6. Set Status Check (Block/Allow Merge)
    if "⚠️ **REQUEST CHANGES**" in review:
        print("❌ Verdict: REQUEST CHANGES. Blocking merge.")
        update_pr_status(statuses_url, "failure", "AI found critical issues.")
        # EXIT WITH ERROR to turn the GitHub Action Red
        sys.exit(1)
        
    elif "✅ **APPROVE**" in review:
        print("✅ Verdict: APPROVED. Green light.")
        update_pr_status(statuses_url, "success", "AI approved the changes.")
        
    else:
        print("⚠️ Verdict inconclusive.")
        update_pr_status(statuses_url, "success", "AI Review posted (Neutral).")

if __name__ == "__main__":
    run()

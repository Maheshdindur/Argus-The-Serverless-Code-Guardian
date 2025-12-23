import os
import json
import requests
import sys  # <--- Added to allow stopping the workflow
import google.generativeai as genai

# --- 1. SETUP & CONFIGURATION ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Get the link to the current GitHub Actions Run (for status checks)
RUN_ID = os.environ.get("GITHUB_RUN_ID")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")
DETAILS_URL = f"https://github.com/{REPO_NAME}/actions/runs/{RUN_ID}"

if not GITHUB_TOKEN or not GOOGLE_API_KEY:
    print("❌ Error: Secrets missing. Make sure GITHUB_TOKEN and GOOGLE_API_KEY are set in Settings > Secrets.")
    sys.exit(1)

# Configure Gemini
# Using the stable model version to avoid 404 errors
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash') 

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

def analyze_code_with_gemini(diff_text, pr_title, user):
    """Sends the code diff to Gemini for analysis."""
    # Truncate if too huge to prevent token errors
    if len(diff_text) > 40000:
        diff_text = diff_text[:40000] + "\n... (Diff truncated for size)"

    prompt = f"""
    You are 'Argus', a Senior Software Engineer bot.
    Review this PR from @{user}. 
    PR Title: {pr_title}
    
    Code Changes (Diff):
    ```diff
    {diff_text}
    ```
    
    Instructions:
    1. Look for **Security Vulnerabilities** (API keys, SQL injection).
    2. Look for **Logic Bugs** or performance issues.
    3. Be constructive and concise.
    4. **CRITICAL**: End your review with exactly one of these two verdicts:
       - '✅ **APPROVE**' (if code looks safe)
       - '⚠️ **REQUEST CHANGES**' (if there are security risks or major bugs)
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ **AI Error:** Gemini failed to respond. Details: {str(e)}"

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

    # 4. Ask Gemini
    print("🧠 Sending code to Gemini...")
    review = analyze_code_with_gemini(code_diff, pr_title, user)

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

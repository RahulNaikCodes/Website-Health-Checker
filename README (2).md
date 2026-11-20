# Serverless Website Health Checker (AWS EventBridge + AWS Lambda)

A lightweight, serverless cloud monitoring solution built using **Amazon EventBridge Scheduler** and **AWS Lambda**. This project periodically checks the availability and HTTP response status of a target website without requiring dedicated servers, third-party dependencies, or recurring idle costs.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Workflow](#architecture--workflow)
3. [AWS Services Used & Free Tier Eligibility](#aws-services-used--free-tier-eligibility)
4. [Prerequisites](#prerequisites)
5. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Create the AWS Lambda Function](#step-1-create-the-aws-lambda-function)
   - [Step 2: Add and Deploy the Python Health-Check Code](#step-2-add-and-deploy-the-python-health-check-code)
   - [Step 3: Increase the Lambda Timeout Limit](#step-3-increase-the-lambda-timeout-limit)
   - [Step 4: Test the Function Manually](#step-4-test-the-function-manually)
   - [Step 5: Create an Amazon EventBridge Schedule](#step-5-create-an-amazon-eventbridge-schedule)
   - [Step 6: Connect EventBridge to AWS Lambda](#step-6-connect-eventbridge-to-aws-lambda)
6. [Monitoring & Verifying Executions](#monitoring--verifying-executions)
7. [Pausing & Cleaning Up Resources](#pausing--cleaning-up-resources)
8. [Troubleshooting](#troubleshooting)

---

## Project Overview

Continuous uptime monitoring is a foundational DevOps and cloud engineering requirement. Traditional monitoring setups rely on always-on virtual machines (such as EC2 instances) running cron jobs, which consume compute resources even when idle.

This project solves that problem using a **100% serverless, event-driven architecture**:
- **Zero Server Management:** No operating systems, patches, or background daemons to maintain.
- **Zero External Dependencies:** Uses Python's built-in `urllib.request` standard library, eliminating `.zip` deployment packages or Lambda Layers.
- **Cost-Efficient:** Operates completely within the **AWS Always Free** tier and incurs **$0** when idle or paused.

---

## Architecture & Workflow

```text
+-----------------------------------+       Triggers on Schedule       +-------------------------------+
|   Amazon EventBridge Scheduler    | -------------------------------> |          AWS Lambda           |
|  (Rate-based rule: e.g., 5 mins)  |      (IAM Execution Role)        |   (Python 3.12 Runtime)       |
+-----------------------------------+                                  +---------------+---------------+
                                                                                       |
                                                           +---------------------------+---------------------------+
                                                           | HTTP GET Request                                      | Writes Logs & Metrics
                                                           v                                                       v
                                           +-------------------------------+                       +-------------------------------+
                                           |       Target Website URL      |                       |       Amazon CloudWatch       |
                                           |    (e.g., example.com)        |                       |  (Invocations & Log Streams)  |
                                           +-------------------------------+                       +-------------------------------+
```

### Execution Flow
1. **Scheduled Trigger:** Amazon EventBridge Scheduler fires automatically based on a configured rate-based interval (e.g., every 5 minutes or 1 hour).
2. **Serverless Compute:** EventBridge invokes the `website-health-checker` AWS Lambda function using an automatically provisioned IAM role.
3. **Health Check Probe:** The Python function sends an HTTP `GET` request with a custom `User-Agent` header and a 10-second socket timeout to `TARGET_URL`.
4. **Status Evaluation & Logging:**
   - If the target responds with an HTTP `200 OK` status, the function logs a UTC-timestamped `SUCCESS` message and returns `{"status": "UP", "statusCode": 200}`.
   - If the target is unreachable or returns an error, the function catches the `URLError`, logs a `FAILURE` message with error details, and returns `{"status": "DOWN", "statusCode": 500}`.
5. **Observability:** Amazon CloudWatch automatically records invocation counts, execution durations, and console output logs.

---

## AWS Services Used & Free Tier Eligibility

| AWS Service | Role in Project | Free Tier Allowance | Idle Cost |
| :--- | :--- | :--- | :--- |
| **AWS Lambda** | Executes the Python health-check script on demand | **1,000,000** requests/month & **400,000 GB-seconds** compute (Always Free) | **$0.00** |
| **Amazon EventBridge Scheduler** | Triggers the Lambda function on a recurring timer | **14,000,000** invocations/month (Always Free) | **$0.00** |
| **Amazon CloudWatch** *(Built-in)* | Automatically captures execution logs and invocation metrics | **5 GB** log ingestion & basic metrics (Always Free) | **$0.00** |

---

## Prerequisites

- An active **AWS Account** (Free Tier / Free Plan eligible).
- Access to the **AWS Management Console** with permissions to create Lambda functions, EventBridge schedules, and basic IAM execution roles.
- No local IDE, AWS CLI, or external Python packages required—everything is configured directly in the browser.

---

## Step-by-Step Implementation

### Step 1: Create the AWS Lambda Function
1. Sign in to the **AWS Management Console**, search for **Lambda** in the top search bar, and open the service.
2. Click **Create function** and keep **Author from scratch** selected.
3. Configure the basic settings:
   - **Function name:** `website-health-checker`
   - **Runtime:** `Python 3.12` (or latest available Python 3.x)
   - **Architecture:** `x86_64`
4. Expand **Change default execution role** and confirm **Create a new role with basic Lambda permissions** is selected (this allows Lambda to write logs to CloudWatch).
5. Click **Create function**.

---

### Step 2: Add and Deploy the Python Health-Check Code
1. Scroll down to the **Code source** panel and open `lambda_function.py`.
2. Replace the default boilerplate code with the following script:

```python
import urllib.request
import urllib.error
from datetime import datetime, timezone

TARGET_URL = "https://example.com"  # Replace with the website URL you want to monitor


def lambda_handler(event, context):
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        req = urllib.request.Request(
            TARGET_URL,
            headers={"User-Agent": "AWS-Lambda-Health-Checker"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.getcode()
            print(f"[{timestamp}] SUCCESS: {TARGET_URL} returned HTTP {status_code}")
            return {
                "statusCode": status_code,
                "status": "UP",
                "url": TARGET_URL
            }
    except urllib.error.URLError as e:
        print(f"[{timestamp}] FAILURE: {TARGET_URL} check failed - {e}")
        return {
            "statusCode": 500,
            "status": "DOWN",
            "url": TARGET_URL,
            "error": str(e)
        }
```

3. Click **Deploy** above the editor to save and publish the code.

---

### Step 3: Increase the Lambda Timeout Limit
> **Why this is required:** New Lambda functions default to a **3.00-second** execution timeout, whereas the script allows up to **10 seconds** for an HTTP response. Cold-start initialization plus network latency can exceed 3 seconds and trigger a `Sandbox.Timedout` error.

1. Select the **Configuration** tab on your Lambda function page.
2. Click **General configuration** in the left menu, then click **Edit** in the top-right corner.
3. Change **Timeout** from `0 min 3 sec` to `0 min 15 sec`.
4. Click **Save**.

---

### Step 4: Test the Function Manually
1. Switch back to the **Code** tab and click **Test**.
2. In the **Configure test event** modal:
   - Select **Create new event**.
   - **Event name:** `manual-test`
   - Leave the default JSON payload unchanged and click **Save**.
3. Click **Test** again.
4. Confirm that the **Execution results** tab turns green (`Status: Succeeded`) and returns:

```json
{
  "statusCode": 200,
  "status": "UP",
  "url": "https://example.com"
}
```

---

### Step 5: Create an Amazon EventBridge Schedule
1. Search for **EventBridge** in the top AWS Console search bar and open it.
2. In the left navigation menu under **Scheduler**, click **Schedules**, then click **Create schedule**.
3. Configure the schedule details:
   - **Schedule name:** `website-health-schedule`
   - **Occurrence:** `Recurring schedule`
   - **Schedule type:** `Rate-based schedule`
   - **Rate expression:** `5 minutes` (recommended during testing; switch to `1 hours` for normal monitoring)
   - **Flexible time window:** `Off`
4. Click **Next**.

---

### Step 6: Connect EventBridge to AWS Lambda
1. On the **Select target** screen, choose **AWS Lambda** (`Invoke`).
2. Under **Lambda function**, select `website-health-checker` from the dropdown list.
3. Leave the **Payload** field empty and click **Next**.
4. On the **Settings** screen:
   - Ensure **Schedule state** is set to **Enabled**.
   - Under **Permissions**, keep **Create new role for this schedule** selected so EventBridge automatically receives permission to invoke your Lambda function.
5. Click **Next**, review the configuration summary, and click **Create schedule**.

---

## Monitoring & Verifying Executions

Once the schedule is active, you can verify automated runs in two ways:

1. **View Total Execution Count (Metrics):**
   - Open `website-health-checker` in the **AWS Lambda** console and click the **Monitor** tab.
   - Select a time window (e.g., `1h` or `3h`) in the top-right corner.
   - Inspect the **Invocations** graph—each plotted point displays the exact number of executions triggered during that interval.
2. **Inspect Timestamped Run Logs:**
   - On the **Monitor** tab, click **View CloudWatch logs** (or scroll to **Recent invocations**).
   - Open the latest log stream to view individual `START RequestId`, `SUCCESS` / `FAILURE` output lines, and `REPORT RequestId` duration summaries spaced at your scheduled interval.

---

## Pausing & Cleaning Up Resources

### Pausing Executions Without Deleting the Project
AWS Lambda does not charge when idle—it bills strictly per invocation. To stop automated executions while keeping your code and logs intact for a demo or evaluation:
1. Open **Amazon EventBridge → Scheduler → Schedules**.
2. Click `website-health-schedule` and select **Disable** in the top-right corner.
3. Confirm the schedule state changes from **Enabled** to **Disabled**. You can re-enable it anytime or trigger manual runs via the Lambda **Test** button.

### Full Resource Cleanup
After project grading is complete, delete both resources to leave your account clean:
1. **EventBridge:** Select `website-health-schedule` under **Schedules** and click **Delete**.
2. **Lambda:** Open `website-health-checker`, click **Actions** in the top-right corner, and choose **Delete**.

---

## Troubleshooting

| Issue / Error | Root Cause | Resolution |
| :--- | :--- | :--- |
| `Sandbox.Timedout: Task timed out after 3.00 seconds` | Default Lambda timeout (3s) is shorter than the cold-start + HTTP request duration. | Increase Lambda **General configuration → Timeout** to **15 seconds**. |
| Function still times out after 15 seconds | Lambda is attached to a private VPC without outbound internet access (NAT Gateway). | Go to **Configuration → VPC** and verify it shows **Not connected to a VPC**. |
| Target website returns HTTP 403 or hangs | Some websites block requests using non-browser `User-Agent` strings. | Update the `User-Agent` header in `lambda_function.py` or test with `https://example.com`. |
| `Invocations` chart shows zero runs | CloudWatch metrics take 1–2 minutes to aggregate, or the schedule is disabled. | Wait 2 minutes, refresh the **Monitor** tab, and confirm `website-health-schedule` is **Enabled**. |

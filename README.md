# lumen

`lumen` is an AI-powered assistant designed to help you quickly query AWS documentation and get the answers you need. It uses Retrieval Augmented Generation (RAG), AWS Model Context Protocol (MCP) servers and Amazon's Nova Large Language Models (LLMs).

## Prerequisites

- An AWS Account
- Docker installed and running
- `uv` installed
- `git` installed

## AWS Setup

To run `lumen`, you will need an AWS Account. If you don't have one, you can find how-to steps [here](https://aws.amazon.com/resources/create-account/).

> [!NOTE]  
> If you plan to use a different region from N. Virginia (us-east-1), don't forget to change the selected region in the AWS Console, update the region part (e.g., us-east-1) in all resource ARNs within the IAM policy JSON, and the .env file. Double-check if the foundation models mentioned below are [available](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html) in the selected region.

### Bedrock Model Access

You need **Access granted** status for the following models:

- Titan Text Embeddings V2
- Nova Pro
- Nova Lite
- Nova Micro

More info on how to modify Bedrock model access can be found [here](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html).

### Create new IAM Policy:

This IAM policy will be attached to a new IAM User, which `lumen` will use to make calls to **AWS Bedrock** foundation models.

1. Open the **IAM Console**
2. Click _Policies_ on the left sidebar
3. Select **Create policy**
4. Switch the view from **Visual** to **JSON**
5. Paste the JSON from below and create the policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowInvokeBedrockModels",
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-pro-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
      ]
    }
  ]
}
```

### IAM User setup

At this point, you should have access to the four foundation models and an IAM policy ready.

1. Open the **IAM Console**
2. Click on _Users_ on the left sidebar
3. Select **Create user**
   1. No need to check _Provide user access to the AWS Management Console_
4. Attach the policy you created in the previous step
5. Create the user and go to the new user's overview page
6. Open the **Security credentials** tab
7. Create and save the access key

### .env file

Now you have your `Access key` and `Secret access key`.

Rename the `.env.template` file to `.env` and update the following variables:

- **AWS_ACCESS_KEY_ID**=your_access_key
- **AWS_SECRET_ACCESS_KEY**=your_secret_key
- **AWS_REGION**=your_chosen_region (e.g., us-east-1)

## Quick Start

[Install](https://docs.astral.sh/uv/getting-started/installation/) `uv`. Then, follow these steps:

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/kaumnen/lumen
    cd lumen
    ```

2.  **Install dependencies using uv:**

    ```bash
    uv sync --frozen --refresh
    ```

3.  **Run Qdrant**:
    The docker run command for Qdrant mounts a volume for data persistence, meaning you will lose the vectors only if you explicitly delete them.

    ```bash
    docker run -p 6333:6333 -p 6334:6334 \
        -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
        qdrant/qdrant
    ```

4.  **Run lumen:**
    From the root directory of the project, execute the following command:
    ```bash
    uv run streamlit run app.py
    ```

You can access the `lumen` app by navigating to the local URL provided in your terminal (usually `http://localhost:8501`) in your browser.

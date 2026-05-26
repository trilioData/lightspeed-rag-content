import os

script_dir = os.path.dirname(os.path.abspath(__file__))

citation_prompt_template = """
You are evaluating citation relevance for a TrilioVault for 
Kubernetes (TVK) documentation retrieval system.

A user asked the following question:
"{prompt}"

The system cited the following document in its response. 
This document was NOT in the expected citation list for 
this question.

Path: {doc_path}
Title: {doc_title}
Content:
{doc_content}

Based on the document's actual content, is citing this 
document justified when answering the user's question?

A citation is JUSTIFIED if the document contains information 
that directly helps answer the question, such as:
- A CR or field that the question's CR references or depends on
- Configuration that the user would need to complete the task
- Context without which the answer would be incomplete

A citation is NOT JUSTIFIED if:
- The connection is superficial (both are about backups but 
  the doc covers a different workflow)
- The document covers a different scope (cluster-scoped vs 
  namespace-scoped) than what was asked
- The document is tangentially related but not needed to 
  answer the question

Respond in this exact format only:
VERDICT: JUSTIFIED or NOT_JUSTIFIED
REASON: one sentence
"""

tvk_docs_root_path = "/home/dipayanpramanik/Devops/trilio/repo/lightspeed-rag-content/"

rubric_prompt_template = """
You are evaluating whether an AI assistant's response 
about TrilioVault for Kubernetes covers specific expected facts.

User question: "{prompt}"

Assistant's response:
{ols_answer}

Expected facts to check:
{expected_facts}

For each fact above, determine if the response adequately covers it.
The wording does not need to match exactly — the concept must be present.

Respond with ONLY a valid JSON object. No markdown, no backticks, 
no explanation. Use the exact fact text as the key.

Example — if the facts were "Target requires a name" and 
"Target supports S3 storage":
{{"Target requires a name": "COVERED", "Target supports S3 storage": "MISSING"}}

Now evaluate:
"""

groq_rest_api = "https://api.groq.com/openai/v1/chat/completions"


SCHEMA_MAP = {
    "Backup": "triliovault.trilio.io_backups.yaml",
    "BackupPlan": "triliovault.trilio.io_backupplans.yaml",
    "ClusterBackup": "triliovault.trilio.io_clusterbackups.yaml",
    "ClusterBackupPlan": "triliovault.trilio.io_clusterbackupplans.yaml",
    "ClusterRestore": "triliovault.trilio.io_clusterrestores.yaml",
    "ClusterSnapshot": "triliovault.trilio.io_clustersnapshots.yaml",
    "ConsistentSet": "triliovault.trilio.io_consistentsets.yaml",
    "ContinuousRestorePlan": "triliovault.trilio.io_continuousrestoreplans.yaml",
    "FileRecoveryVM": "triliovault.trilio.io_filerecoveryvms.yaml",
    "Hook": "triliovault.trilio.io_hooks.yaml",
    "License": "triliovault.trilio.io_licenses.yaml",
    "Policy": "triliovault.trilio.io_policies.yaml",
    "Restore": "triliovault.trilio.io_restores.yaml",
    "Snapshot": "triliovault.trilio.io_snapshots.yaml",
    "Target": "triliovault.trilio.io_targets.yaml",
    "TrilioVaultManager": "triliovault.trilio.io_triliovaultmanagers.yaml",
}

SCHEMA_DIR = f"{script_dir}/crds"
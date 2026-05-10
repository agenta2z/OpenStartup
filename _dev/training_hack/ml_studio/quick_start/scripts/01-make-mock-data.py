#!/usr/bin/env python3
"""Generate a 50-row mock SFT dataset in `openai_messages` format.

Use this only if you DON'T want to depend on the public HuggingFace dataset
in `configs/hack_oss_20b_sft.yaml`. By default the workflow uses
`HuggingFaceH4/ultrachat_200k` which works out-of-the-box.

Output: artifacts/mock_sft_50.jsonl  (one JSON object per line)

Schema (verified from
  /Users/tchen7/MyProjects/atlassian_packages/ml-studio-docs/content/platform/
  ml-studio/model-training/llm-fine-tuning/data-prep/index.md ):

  {"messages": [
      {"role": "system",    "content": "..."},
      {"role": "user",      "content": "..."},
      {"role": "assistant", "content": "..."}
  ]}

To use this in the workflow:
  1. Upload to a Databricks Volume:
       databricks fs cp artifacts/mock_sft_50.jsonl \\
         dbfs:/Volumes/ml_ugc_derived_prod_us/mls_usecase_ai_modeling_experimental/artifacts/tchen7_mock_sft/
  2. Register a Spark table over it (DDL not shown).
  3. Change the `datasets_config` block in the workflow YAML to use
       dataset_type: spark
       dataset_name: <catalog>.<schema>.tchen7_mock_sft
       sft_format: openai_messages
"""

import json
import os
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "artifacts" / "mock_sft_50.jsonl"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

TOPICS = [
    ("explain", "Explain the concept of {x} like I'm 10 years old."),
    ("define", "What is {x}?"),
    ("compare", "Compare {x} and {y}."),
    ("howto",   "How do I get started with {x}?"),
    ("debug",   "I keep getting an error when {x}. What's wrong?"),
]

CONCEPTS = [
    "neural networks", "transformers", "LoRA fine-tuning", "gradient descent",
    "MLflow", "Databricks", "deepspeed", "attention mechanism",
    "supervised fine-tuning", "Atlas CLI", "ML Studio workflows", "vector embeddings",
    "Ray Train", "PyTorch", "Hugging Face Trainer", "ChatML template",
    "BERT", "GPT", "Llama", "instruction tuning",
    "RLHF", "DPO", "PEFT adapters", "BF16", "model quantization",
]

SYSTEM = "You are a concise, helpful AI assistant."

def main() -> None:
    rows = []
    for i in range(50):
        topic_name, template = TOPICS[i % len(TOPICS)]
        x = CONCEPTS[i % len(CONCEPTS)]
        y = CONCEPTS[(i + 7) % len(CONCEPTS)]
        question = template.format(x=x, y=y)
        answer = (
            f"Sure — here is a brief mock answer about {x}. "
            f"This is row #{i:02d} of a synthetic dataset used to verify the "
            f"ML Studio fine-tune pipeline submits and trains end-to-end. "
            f"Real answers should be replaced before any real evaluation."
        )
        rows.append({
            "messages": [
                {"role": "system",    "content": SYSTEM},
                {"role": "user",      "content": question},
                {"role": "assistant", "content": answer},
            ]
        })

    with OUTPUT.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    size = OUTPUT.stat().st_size
    print(f"✓ Wrote {len(rows)} rows ({size:,} bytes) to {OUTPUT}")
    print()
    print("Sample row:")
    print(json.dumps(rows[0], indent=2))


if __name__ == "__main__":
    main()

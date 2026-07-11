"""10-task evaluation suite for the Data Analyst Agent."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from agent import DataAnalystAgent

load_dotenv()

EVAL_TASKS = [
    {
        "id": 1,
        "question": "Which product had the highest total revenue?",
        "expected_in_answer": ["Widget A"],
        "max_steps": 6,
    },
    {
        "id": 2,
        "question": "How many rows are in the dataset?",
        "expected_in_answer": ["50"],
        "max_steps": 4,
    },
    {
        "id": 3,
        "question": "Which region has the lowest total revenue?",
        "expected_in_answer": ["West"],
        "max_steps": 6,
    },
    {
        "id": 4,
        "question": "Are there outliers in the revenue column?",
        "expected_in_answer": ["outlier"],
        "max_steps": 6,
    },
    {
        "id": 5,
        "question": "What is the total revenue for Enterprise customer segment?",
        "expected_in_answer": ["Enterprise"],
        "max_steps": 6,
    },
    {
        "id": 6,
        "question": "Compare Q2 2024 (Apr-Jun) and Q3 2024 (Jul-Sep) revenue by customer segment.",
        "expected_in_answer": ["Enterprise"],
        "max_steps": 8,
    },
    {
        "id": 7,
        "question": "What are the top 3 products by revenue?",
        "expected_in_answer": ["Widget"],
        "max_steps": 6,
    },
    {
        "id": 8,
        "question": "Make a bar chart of total revenue by region.",
        "expected_in_answer": ["chart"],
        "max_steps": 8,
    },
    {
        "id": 9,
        "question": "Which region is declining fastest in revenue from Q2 to Q3 2024?",
        "expected_in_answer": ["region"],
        "max_steps": 8,
    },
    {
        "id": 10,
        "question": "What is the average revenue per transaction?",
        "expected_in_answer": ["average", "mean"],
        "max_steps": 6,
    },
]


def check_answer(answer: str, expected: list[str]) -> bool:
    answer_lower = answer.lower()
    return any(kw.lower() in answer_lower for kw in expected)


def run_evaluation(csv_path: Path | None = None) -> dict:
    csv_path = csv_path or Path(__file__).parent / "data" / "sales.csv"
    df = pd.read_csv(csv_path)
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    task_results = []
    total_steps = 0
    successes = 0

    print(f"Running {len(EVAL_TASKS)} evaluation tasks...\n")

    for task in EVAL_TASKS:
        print(f"Task {task['id']}: {task['question']}")
        agent = DataAnalystAgent(
            df=df,
            trace_path=results_dir / "traces.jsonl",
            charts_dir=results_dir / "charts",
        )
        result = agent.run(task["question"], use_memory=False, use_planner=True)

        passed = result.success and check_answer(result.answer, task["expected_in_answer"])
        steps_ok = result.steps <= task["max_steps"]
        if passed:
            successes += 1
        total_steps += result.steps

        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] steps={result.steps}, tokens={result.total_tokens}")
        if not passed:
            print(f"  Answer preview: {result.answer[:150]}...")

        task_results.append(
            {
                "task_id": task["id"],
                "question": task["question"],
                "passed": passed,
                "steps": result.steps,
                "steps_within_limit": steps_ok,
                "tokens": result.total_tokens,
                "tools_called": result.tools_called,
                "answer_preview": result.answer[:300],
            }
        )

    success_rate = successes / len(EVAL_TASKS)
    avg_steps = total_steps / len(EVAL_TASKS)

    summary = {
        "total_tasks": len(EVAL_TASKS),
        "successes": successes,
        "success_rate": round(success_rate, 2),
        "avg_steps": round(avg_steps, 2),
        "target_success_rate": 0.70,
        "target_avg_steps": 6,
        "max_loop_limit": 10,
        "passed_success_target": success_rate >= 0.70,
        "passed_steps_target": avg_steps < 6,
        "tasks": task_results,
    }

    out_path = results_dir / "task_success.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"Success rate: {success_rate:.0%} ({successes}/{len(EVAL_TASKS)})")
    print(f"Avg steps:    {avg_steps:.1f}")
    print(f"Target:       ≥70% success, <6 avg steps")
    print(f"Results saved to {out_path}")

    return summary


if __name__ == "__main__":
    summary = run_evaluation()
    if not summary["passed_success_target"]:
        sys.exit(1)

import asyncio
import json
import os
import time

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner


async def run_benchmark_with_results(agent_version: str, dataset: list):
    print(f"Starting Benchmark for {agent_version}...")

    agent = MainAgent(version=agent_version)
    evaluator = RetrievalEvaluator()
    judge = LLMJudge()
    runner = BenchmarkRunner(agent, evaluator, judge)

    # Chạy song song 5 cases một lúc
    results = await runner.run_all(dataset, batch_size=5)

    summary = {
        "metadata": {
            "version": agent_version,
            "total": len(results),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score": sum(r["judge"]["final_score"] for r in results) / len(results)
            if results
            else 0,
            "hit_rate": sum(r["ragas"]["retrieval"]["hit_rate"] for r in results)
            / len(results)
            if results
            else 0,
            "agreement_rate": sum(r["judge"]["agreement_rate"] for r in results)
            / len(results)
            if results
            else 0,
            "total_cost": sum(r.get("cost", 0.0) for r in results),
        },
    }
    return results, summary


async def main():
    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Missing data/golden_set.jsonl. Run synthetic_gen.py first.")
        return

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f]

    # 1. Chạy Benchmark cho V1
    _, v1_summary = await run_benchmark_with_results("V1", dataset)

    # 2. Chạy Benchmark cho V2
    v2_results, v2_summary = await run_benchmark_with_results("V2", dataset)

    # 3. Phân tích Regression
    print("\n📊 --- REGRESSION ANALYSIS ---")
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]

    print(f"V1 Avg Score: {v1_summary['metrics']['avg_score']:.2f}")
    print(f"V2 Avg Score: {v2_summary['metrics']['avg_score']:.2f}")
    print(f"Delta: {'+' if delta >= 0 else ''}{delta:.2f}")
    print(f"V2 Hit Rate: {v2_summary['metrics']['hit_rate']:.2f}")
    print(f"V2 Agreement Rate: {v2_summary['metrics']['agreement_rate']:.2f}")
    print(f"Total Eval Cost: ${v2_summary['metrics']['total_cost']:.4f}")

    # 4. Xuất báo cáo
    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    # 5. Logic Auto-Gate (Quyết định Release)
    approved = True
    reasons = []

    if delta < 0:
        approved = False
        reasons.append("Average score decreased compared to V1.")
    if v2_summary["metrics"]["hit_rate"] < 0.8:
        approved = False
        reasons.append("Hit rate is below the 0.8 threshold.")
    if v2_summary["metrics"]["agreement_rate"] < 0.7:
        approved = False
        reasons.append("Agreement rate is below the 0.7 threshold.")

    if approved:
        print("\n✅ DECISION: RELEASE APPROVED")
    else:
        print("\n❌ DECISION: RELEASE BLOCKED")
        for r in reasons:
            print(f"- {r}")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import time
from typing import Dict, List

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge

# Import các công cụ giám khảo (Cho phần test ở dưới)
from engine.retrieval_eval import RetrievalEvaluator


class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()

        # 1. Gọi Thí Sinh (Agent) làm bài
        response = await self.agent.query(test_case)
        latency = time.perf_counter() - start_time

        # 2. Chấm điểm Retrieval (Chấm công tìm kiếm)
        expected_ids = test_case.get("expected_retrieval_ids", [])
        retrieved_ids = response.get("retrieved_ids", [])

        hit_rate = self.evaluator.calculate_hit_rate(expected_ids, retrieved_ids)
        mrr = self.evaluator.calculate_mrr(expected_ids, retrieved_ids)

        ragas_scores = {"retrieval": {"hit_rate": hit_rate, "mrr": mrr}}

        # 3. Chấm điểm Generation bằng LLM-as-a-Judge (Chấm văn)
        judge_result = await self.judge.evaluate_multi_judge(
            question=test_case.get("question", ""),
            answer=response.get("answer", ""),
            ground_truth=test_case.get("expected_answer", ""),
        )

        return {
            "test_case": test_case.get("question", ""),
            "agent_response": response.get("answer", ""),
            "latency": latency,
            "tokens_used": response.get("metadata", {}).get("tokens_used", 0),
            "cost": response.get("metadata", {}).get("cost", 0.0),
            "ragas": ragas_scores,
            "judge": judge_result,
            "status": "pass" if judge_result["final_score"] >= 3 else "fail",
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 5):
        """
        Chạy song song sử dụng Semaphore để chống Rate Limit.
        """
        print(
            f"🚀 Running benchmark on {len(dataset)} cases (Concurrency = {batch_size})..."
        )
        sem = asyncio.Semaphore(batch_size)

        async def run_with_sem(case):
            async with sem:
                return await self.run_single_test(case)

        tasks = [run_with_sem(case) for case in dataset]
        results = await asyncio.gather(*tasks)
        return results


# --- TEST NHANH STEP 3 ---
if __name__ == "__main__":

    async def test_runner():
        # Tạo 3 case mock để test
        mock_dataset = [
            {
                "question": "Q1?",
                "expected_answer": "Ans 1",
                "expected_retrieval_ids": ["chunk_1"],
            },
            {
                "question": "Q2?",
                "expected_answer": "Ans 2",
                "expected_retrieval_ids": ["chunk_2"],
            },
            {
                "question": "Q3?",
                "expected_answer": "Ans 3",
                "expected_retrieval_ids": ["chunk_3"],
            },
        ]

        runner = BenchmarkRunner(MainAgent("V2"), RetrievalEvaluator(), LLMJudge())

        start = time.perf_counter()
        results = await runner.run_all(mock_dataset, batch_size=3)
        total_time = time.perf_counter() - start

        print("\n--- KẾT QUẢ BENCHMARK ---")
        for i, res in enumerate(results):
            print(
                f"[{res['status'].upper()}] Câu {i + 1} - Điểm: {res['judge']['final_score']} - Hit Rate: {res['ragas']['retrieval']['hit_rate']} - Cost: ${res['cost']:.6f} - Latency: {res['latency']:.2f}s"
            )

        print(
            f"\n✅ Hoàn thành 3 cases trong {total_time:.2f} giây (Test song song thành công!)"
        )

    asyncio.run(test_runner())

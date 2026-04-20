from typing import Dict, List


class RetrievalEvaluator:
    def __init__(self):
        pass

    def calculate_hit_rate(
        self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3
    ) -> float:
        """
        Tính toán xem ít nhất 1 trong expected_ids có nằm trong top_k của retrieved_ids không.
        """
        # Lấy top K tài liệu được truy xuất
        top_retrieved = retrieved_ids[:top_k]
        # Kiểm tra xem có bất kỳ ID kỳ vọng nào nằm trong top retrieved không
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """
        Tính Mean Reciprocal Rank (MRR).
        MRR = 1 / vị trí (1-indexed). Nếu không thấy thì là 0.
        """
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    async def evaluate_batch(self, dataset: List[Dict]) -> Dict:
        """
        Chạy eval cho toàn bộ bộ dữ liệu.
        """
        if not dataset:
            return {"avg_hit_rate": 0.0, "avg_mrr": 0.0}

        total_hit_rate = 0.0
        total_mrr = 0.0

        for case in dataset:
            # Lấy danh sách ID kỳ vọng và ID thực tế truy xuất được
            expected = case.get("expected_retrieval_ids", [])
            retrieved = case.get("retrieved_ids", [])

            total_hit_rate += self.calculate_hit_rate(expected, retrieved)
            total_mrr += self.calculate_mrr(expected, retrieved)

        num_cases = len(dataset)
        return {
            "avg_hit_rate": total_hit_rate / num_cases,
            "avg_mrr": total_mrr / num_cases,
        }


# --- TEST NHANH ---
if __name__ == "__main__":
    evaluator = RetrievalEvaluator()
    expected = ["chunk_005", "chunk_006"]
    retrieved = ["chunk_001", "chunk_005", "chunk_009"]

    print(
        f"Hit Rate (Top 3): {evaluator.calculate_hit_rate(expected, retrieved)}"
    )  # Output: 1.0
    print(
        f"MRR: {evaluator.calculate_mrr(expected, retrieved)}"
    )  # Output: 0.5 (vì chunk_005 ở vị trí số 2)

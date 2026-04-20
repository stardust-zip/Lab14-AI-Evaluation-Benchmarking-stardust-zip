import asyncio
import random
from typing import Dict


class MainAgent:
    def __init__(self, version="V1"):
        self.name = f"SupportAgent-{version}"
        self.version = version

    async def query(self, test_case: Dict) -> Dict:
        """
        Mô phỏng quy trình RAG: Retrieval -> Generation.
        (Nhận toàn bộ test_case để Mock Agent có thể 'diễn' cảnh tìm trúng/trượt)
        """
        # Giả lập độ trễ (Latency) khi gọi API và DB
        await asyncio.sleep(random.uniform(0.1, 0.4))

        expected_ids = test_case.get("expected_retrieval_ids", [])

        # Mô phỏng chất lượng Agent: V2 xịn hơn V1
        hit_chance = 0.95 if "V2" in self.version else 0.60

        retrieved_ids = []
        if expected_ids and random.random() < hit_chance:
            # Lấy trúng tài liệu
            retrieved_ids = expected_ids.copy()
            retrieved_ids.append(f"chunk_noise_{random.randint(1, 99)}")
            random.shuffle(retrieved_ids)  # Đảo lộn vị trí để test chỉ số MRR
        else:
            # Lấy trượt (Chỉ ra toàn noise)
            retrieved_ids = [f"chunk_noise_{random.randint(1, 99)}" for _ in range(3)]

        # Mô phỏng sinh câu trả lời: Tìm trúng DB thì trả lời đúng, tìm trượt thì trả lời sai/từ chối
        if any(eid in retrieved_ids for eid in expected_ids):
            answer = (
                f"Theo thông tin tôi tìm được: {test_case.get('expected_answer', '')}"
            )
        else:
            answer = "Xin lỗi, tôi không tìm thấy thông tin chính xác trong tài liệu."

        # Giả lập đo lường Token và Chi phí (Dùng gpt-4o-mini giá $0.15/1M token)
        tokens = random.randint(100, 300)
        cost = (tokens / 1_000_000) * 0.15

        return {
            "answer": answer,
            "retrieved_ids": retrieved_ids,
            "metadata": {"model": "gpt-4o-mini", "tokens_used": tokens, "cost": cost},
        }

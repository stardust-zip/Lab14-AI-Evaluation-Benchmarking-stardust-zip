import asyncio
import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class LLMJudge:
    def __init__(self):
        # Khởi tạo client. Bạn có thể trỏ base_url sang OpenRouter/Ollama nếu muốn dùng Prometheus
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Tiêu chí chấm điểm chi tiết (Rubrics)
        self.rubrics = """
        Bạn là một giám khảo AI khắt khe. Hãy chấm điểm câu trả lời của Agent dựa trên Ground Truth.
        THANG ĐIỂM (1 đến 5):
        - 5: Chính xác hoàn toàn, đầy đủ chi tiết như Ground Truth, văn phong chuyên nghiệp.
        - 4: Chính xác nhưng thiếu một vài chi tiết nhỏ hoặc văn phong hơi cứng.
        - 3: Trả lời được ý chính nhưng có phần mập mờ hoặc diễn đạt kém.
        - 2: Trả lời sai một phần quan trọng hoặc bịa đặt (Hallucination) nhẹ.
        - 1: Hoàn toàn sai, từ chối trả lời sai cách, hoặc vi phạm an toàn.
        """

    async def _call_judge(
        self, model_name: str, question: str, answer: str, ground_truth: str
    ) -> int:
        """Hàm gọi LLM để chấm điểm và ép trả về JSON chứa 'score'"""
        prompt = f"""
        [Câu hỏi]: {question}
        [Câu trả lời kỳ vọng (Ground Truth)]: {ground_truth}
        [Câu trả lời thực tế của Agent]: {answer}

        Hãy chấm điểm từ 1 đến 5.
        TRẢ VỀ DUY NHẤT 1 JSON THEO FORMAT: {{"score": <điểm_số_nguyên>, "reasoning": "<lý do ngắn gọn>"}}
        """

        try:
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": self.rubrics},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Nhiệt độ thấp để chấm điểm khách quan và ổn định
            )
            data = json.loads(response.choices[0].message.content)
            return int(data.get("score", 3))  # Trả về 3 nếu lỗi parse
        except Exception as e:
            print(f"⚠️ Lỗi Judge ({model_name}): {e}")
            return 3

    async def evaluate_multi_judge(
        self, question: str, answer: str, ground_truth: str
    ) -> Dict[str, Any]:
        """
        EXPERT TASK: Gọi 2 models. Tính sự đồng thuận và xử lý xung đột (Conflict Resolution).
        """
        # Gọi 2 Giám khảo song song để tiết kiệm thời gian
        # Ghi chú: Nếu có Prometheus qua API, đổi "gpt-4o" thành tên model đó.
        task_a = self._call_judge("gpt-4o-mini", question, answer, ground_truth)
        task_b = self._call_judge("gpt-4o", question, answer, ground_truth)

        score_a, score_b = await asyncio.gather(task_a, task_b)

        # Tính toán độ đồng thuận (Agreement Rate)
        # Độ lệch: 0 điểm -> 100% đồng thuận. Lệch 1 điểm -> 80%. Lệch >1 điểm -> Bất đồng nặng.
        diff = abs(score_a - score_b)
        agreement = 1.0 if diff == 0 else (0.8 if diff == 1 else 0.5)

        final_score = (score_a + score_b) / 2
        reasoning = f"GPT-Mini chấm {score_a}, GPT-4o chấm {score_b}."

        # LOGIC XỬ LÝ XUNG ĐỘT (Conflict Resolution - Điểm ăn tiền Expert)
        if diff > 1:
            # Nếu 2 giám khảo cãi nhau dữ dội (ví dụ: 5 và 2), gọi giám khảo thứ 3 làm Tie-breaker
            reasoning += " Đã gọi Tie-breaker do bất đồng cao."
            tie_breaker_score = await self._call_judge(
                "gpt-4o", question, answer, ground_truth
            )
            # Lấy điểm của người phân xử làm trọng tâm
            final_score = tie_breaker_score
            agreement = 0.5  # Ghi nhận case này là một case khó (low agreement)

        return {
            "final_score": final_score,
            "agreement_rate": agreement,
            "individual_scores": {"gpt-4o-mini": score_a, "gpt-4o": score_b},
            "reasoning": reasoning,
        }


# --- TEST NHANH STEP 2 ---
if __name__ == "__main__":

    async def test():
        judge = LLMJudge()
        q = "AI Evaluation là gì?"
        gt = "Là quy trình kỹ thuật đo lường chất lượng LLMs."

        # Test Case 1: Trả lời tốt (Kỳ vọng điểm cao, đồng thuận cao)
        ans_good = "Đó là quá trình đánh giá và đo lường chất lượng của các mô hình ngôn ngữ lớn."
        print("Đang chấm câu trả lời TỐT...")
        res1 = await judge.evaluate_multi_judge(q, ans_good, gt)
        print(f"Kết quả 1: {json.dumps(res1, ensure_ascii=False, indent=2)}\n")

        # Test Case 2: Trả lời sai (Kỳ vọng điểm thấp)
        ans_bad = "AI Evaluation là một loài cá biển sống ở vùng nhiệt đới."
        print("Đang chấm câu trả lời SAI...")
        res2 = await judge.evaluate_multi_judge(q, ans_bad, gt)
        print(f"Kết quả 2: {json.dumps(res2, ensure_ascii=False, indent=2)}")

    asyncio.run(test())

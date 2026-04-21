## Bước 1: Retrieval & Dataset Generation (20 điểm Nhóm)
Bạn phải tạo ra ít nhất 50 test cases và tính được Hit Rate, MRR.

**1.1. Implement Data Gen (`data/synthetic_gen.py`)**
* **Cách làm:** Viết script gọi API OpenAI/Anthropic để sinh 50+ cặp câu hỏi. Bắt buộc phải có các trường: `question`, `expected_answer`, `expected_retrieval_ids` (ID của các chunk/document chứa đáp án). Phải chèn các prompt injection hoặc out-of-context dựa theo `HARD_CASES_GUIDE.md`.
* **Cách test:** Chạy `python data/synthetic_gen.py`. Mở file `data/golden_set.jsonl`. Đếm xem có đủ >= 50 dòng không. Kiểm tra xem mỗi dòng có đủ các key yêu cầu, đặc biệt là `expected_retrieval_ids` không.

**1.2. Implement Retrieval Eval (`engine/retrieval_eval.py`)**
* **Cách làm:**
    * `calculate_hit_rate`: Kiểm tra xem có bất kỳ ID nào trong `expected_ids` xuất hiện trong top `k` của `retrieved_ids` không.
    * `calculate_mrr`: Tìm vị trí (index) đầu tiên mà ID khớp. Trả về `1 / (index + 1)`. Nếu không có, trả về 0.
* **Cách test:** Viết file test phụ: `assert calculate_hit_rate(['A'], ['B', 'A']) == 1.0` và `assert calculate_mrr(['A'], ['B', 'A', 'C']) == 0.5`. Chạy `python engine/retrieval_eval.py`. Kết quả mong đợi:

```txt
Hit Rate (Top 3): 1.0
MRR: 0.5
```

## Bước 2: Multi-Judge Consensus Engine (15 điểm Nhóm)
Việc chỉ dùng 1 model Judge (chấm điểm lệch) sẽ bị điểm liệt phần Nhóm (giới hạn ở 30đ).

**2.1. Implement (`engine/llm_judge.py`)**
* **Cách làm:** Gọi đồng thời 2 API (vd: OpenAI và Prometheus/Claude) để chấm điểm `accuracy` và `tone`.
* **Logic xử lý xung đột:** Nếu `abs(score_A - score_B) > 1` (ví dụ GPT chấm 5, Claude chấm 3), bạn phải code logic tự động gọi một model thứ 3 (Tie-breaker) HOẶC yêu cầu Model A xem xét lại lý do của Model B và chấm lại.
* **Cách test:** Cố tình mock dữ liệu: Trả về `score_A = 5`, `score_B = 2`. In log ra màn hình để đảm bảo hệ thống nhận diện được xung đột và gọi hàm `tie_breaker`. Chạy `python engine/llm_judge.py`. Kết quả mong đợi: **Một câu trả lời tốt (4-5 điểm)**, **Một câu trả lời kém (1-2 điểm)**.


## Bước 3: Async Performance & Cost Optimization (10 điểm Nhóm)
Phải chạy song song, hoàn thành < 2 phút cho 50 cases và tracking chi phí.

**3.1. Implement (`engine/runner.py` & `agent/main_agent.py`)**
* **Cách làm:** Trong file `runner.py`, hàm `run_all`, không dùng `asyncio.gather` thuần túy vì sẽ bị Rate Limit API. Hãy dùng `asyncio.Semaphore`.
    ```python
    sem = asyncio.Semaphore(batch_size) # Ví dụ batch_size = 5
    async def run_with_sem(case):
        async with sem:
            return await self.run_single_test(case)
    tasks = [run_with_sem(case) for case in dataset]
    return await asyncio.gather(*tasks)
    ```
* **Đo Cost:** Trong `MainAgent`, trích xuất `usage.total_tokens` từ API response. Nhân với giá tiền (vd: GPT-4o-mini là $0.15/1M input tokens). Cộng dồn lại trong `BenchmarkRunner`.
* **Cách test:** Chạy 50 cases. Bật đồng hồ bấm giờ, nếu hệ thống văng lỗi "Rate Limit" -> Semaphore chưa hoạt động. Nếu xong dưới 2 phút -> Pass. Kiểu này:
1. Chạy `python engine/runner.py`.
2. Chờ khoảng 2-3 giây (Do cả 3 câu được gọi API chấm điểm cùng lúc).
3. In ra Bảng kết quả 3 câu, kèm theo
  - Điểm (Score)
  - Hit Rate (0.0 hoặc 1.0)
  - Chi phí (Cost)
  - Tốc độ trả lời (Latency)

## Bước 4: Regression Testing & Auto-Gate (10 điểm Nhóm)
Tự động quyết định Release hay Rollback.

**4.1. Implement (`main.py`)**
* **Cách làm:** Hiện tại code đã có so sánh `v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]`. Để đạt Expert, hãy thêm điều kiện bắt buộc:
    * Delta điểm Judge > 0.
    * **VÀ** Hit Rate > 0.8 (đảm bảo không bị suy thoái retrieval).
    * **VÀ** Độ đồng thuận (Agreement Rate) > 0.7.
* **Cách test:** Đổi mock data của V2 sao cho `avg_score` cao hơn V1 nhưng `hit_rate` thấp hơn V1. Bật run, nếu terminal in ra `❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK RELEASE)` thì logic Gate của bạn đã đúng.

## Bước 5: Failure Analysis - "5 Whys" (5 điểm Nhóm)
Đây là phần giải trình tư duy kỹ thuật sâu.

**5.1. Implement (`analysis/failure_analysis.md`)**
* **Cách làm:** Sau khi chạy ra file `benchmark_results.json`, lọc ra 3 case có `final_score` < 3. Điền vào markdown theo phương pháp 5 Whys.
    * *Ví dụ:* Tại sao trả lời sai? -> Context thiếu thông tin. -> Tại sao thiếu? -> Chunk chứa thông tin bị rớt khỏi top 3. -> Tại sao rớt? -> User dùng từ đồng nghĩa, Vector Search (BM25/Cosine) không bắt được. -> Tại sao không bắt được? -> Model Embedding hiện tại chưa tốt tiếng Việt. -> **Root Cause:** Cần thay Model Embedding hoặc thêm Hybrid Search.
* **Cách test:** Trình bày mạch lạc, logic nhân quả.

---

## 🚨 CHECKLIST TRƯỚC KHI NỘP BÀI

Để tránh bị trừ 5 điểm thủ tục, trước khi nén code nộp, bạn **bắt buộc** phải chạy lệnh sau:

`python check_lab.py`

*Hệ thống sẽ pass nếu terminal hiển thị:*
```text
✅ Tìm thấy: reports/summary.json
✅ Tìm thấy: reports/benchmark_results.json
✅ Tìm thấy: analysis/failure_analysis.md
...
✅ Đã tìm thấy Retrieval Metrics (Hit Rate...)
✅ Đã tìm thấy thông tin phiên bản Agent (Regression Mode)
🚀 Bài lab đã sẵn sàng để chấm điểm!
```
*(Tham khảo mã nguồn file `check_lab.py`)*

Chúc nhóm bạn thiết lập thành công hệ thống AI Evaluation chuyên nghiệp và đạt điểm tuyệt đối!

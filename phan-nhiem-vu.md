
|   | Hạng mục | Tiêu chí | Điểm |
| :- | :--- | :--- | :---: |
|   | **Retrieval Evaluation** | - Tính toán thành công Hit Rate & MRR cho ít nhất 50 test cases.<br>- Giải thích được mối liên hệ giữa Retrieval Quality và Answer Quality. | 10 |
|  | **Dataset & SDG** | - Golden Dataset chất lượng (50+ cases) với mapping Ground Truth IDs.<br>- Có các bộ "Red Teaming" phá vỡ hệ thống thành công. | 10 |
|   | **Multi-Judge consensus** | - Triển khai ít nhất 2 model Judge (ví dụ GPT + Claude).<br>- Tính toán được độ đồng thuận và có logic xử lý xung đột tự động. | 15 |
|    | **Regression Testing** | - Chạy thành công so sánh V1 vs V2.<br>- Có logic "Release Gate" tự động dựa trên các ngưỡng chất lượng. | 10 |
|    | **Performance (Async)** | - Toàn bộ pipeline chạy song song cực nhanh (< 2 phút cho 50 cases).<br>- Có báo cáo chi tiết về Cost & Token usage. | 10 |
| Nguyễn Ngọc Hiếu | **Failure Analysis** | - Phân tích "5 Whys" cực sâu, chỉ ra được lỗi hệ thống (Chunking, Ingestion, v.v.). | 5 |

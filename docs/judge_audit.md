# Judge audit

## 1. Calibration

FAIL là lớp dương: judge cần phát hiện câu trả lời không đạt tiêu chí.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Dùng cho tone trong phạm vi replay |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không | Loại khỏi quyết định gate: recall và kappa dưới ngưỡng |

Ma trận tone: TP=24, FP=4, FN=6, TN=66.
Tỉ lệ FAIL quan sát là 0.28; sau hiệu chỉnh Rogan–Gladen là 0.30.

## 2. Audit thủ công 5 bất đồng

Phân tích dưới đây dựa trên reply và cột note của bộ replay.
Đây không phải một lượt gán nhãn độc lập hoặc held-out mới.

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Đồng ý nhãn người theo ghi chú rubric | Judge coi cách nói thân mật là thân thiện; bỏ sót cách xưng hô và từ “nha” không phù hợp mức trang trọng được yêu cầu. Đây là FN. |
| 2 | H-017 | PASS | FAIL | Đồng ý nhãn người trong ngữ cảnh ghi ở note | Note xác định khách lớn tuổi nên cách gọi “bạn” không phù hợp. Reply đơn lẻ không cho biết tuổi khách; cần ngữ cảnh này để kết luận. Đây là FN. |
| 3 | H-029 | PASS | FAIL | Đồng ý nhãn người | “Dạ, vui lòng” không bù được sắc thái ra lệnh của “không cần nhắn thêm”. Judge bỏ sót tín hiệu tiêu cực ở cuối câu. Đây là FN. |
| 4 | H-042 | FAIL | PASS | Đồng ý nhãn người | Câu ngắn nhưng lịch sự và đủ thông tin theo note; không có quy định bắt buộc xin lỗi trong mọi câu. Judge áp thêm điều kiện ngoài rubric. Đây là FP. |
| 5 | H-051 | FAIL | PASS | Đồng ý nhãn người | Note cho biết CS LogiX cho phép từ “refund”. Judge phạt việc dùng tiếng Anh dù không vi phạm quy tắc này. Đây là FP. |

## 3. Quyết định và giới hạn

- tone_ok đạt cả ba ngưỡng calibration nên được giữ cho đánh giá tone trong phạm vi bộ replay.
- Judge vẫn bỏ sót 6/30 câu FAIL và báo nhầm 4/70 câu PASS; không coi kết quả judge là nhãn tuyệt đối.
- Hướng cải thiện rubric: phân biệt thân thiện với suồng sã, xét toàn câu, cung cấp ngữ cảnh khách hàng khi cần và không tự thêm yêu cầu xin lỗi hoặc cấm thuật ngữ tiếng Anh.
- Tone không chứng minh số tiền, approval hoặc ledger đúng; các phần này phải chấm bằng code.
- Dữ liệu và ghi chú replay đã công khai. Cần nhãn người mới trên held-out để kiểm chứng khả năng tổng quát.
- Quyết định đối với helpful sẽ được bổ sung sau khi chạy calibration riêng.
- helpful có TP=9, FP=0, FN=21, TN=70. Precision cao nhưng bỏ sót 70% lỗi thật; không đủ tin cậy để dùng làm tiêu chí gate.
- Tỉ lệ FAIL quan sát là 0.09, sau hiệu chỉnh là 0.30. Hiệu chỉnh tỉ lệ tổng thể không sửa được phán đoán sai của từng câu.
## 4. Kiểm tra đã chạy

- `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5`: PASS floors.
- Bốn test M2 trong `tests/test_lab9_stats.py`: 4 passed, 2 deselected.
# Trace case: ticket ghi đè dữ liệu order

R-seeded_regression-C-002-s11

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`; đối chứng `fixed C-002@11`. Run ID lấy từ file trace của lần chạy, chưa ghi trong bản này. |
| Triệu chứng | Lab 8 grader FAIL: `status resolved != denied`. Ledger ghi 20.000đ, một refund; nhãn yêu cầu 0đ, không có refund và trạng thái `denied`. |
| Bước sai đầu tiên | Event 3, `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là bước đầu tiên | Event 1 tạo handoff; event 2 đọc order qua investigator. Event 3 thay dữ liệu có cấu trúc bằng số ngày trong ticket. Event 4 tính quote 20.000đ từ dữ liệu đã bị thay. |
| Failure mode | FM-03 — ticket_trust. |
| Đối chứng | `fixed` không có event `model_override`; event 3 là quote 0 với lý do `no_entitlement`. Ledger không ghi refund, trạng thái `denied`, Lab 8 grader PASS. |
| Regression test | `tests/test_lab9_ticket_trust_regression.py::test_lab9_ticket_trust_regression`; dùng `trial_pass` và kiểm tra trực tiếp ledger. Đã chạy: 2 passed. Test xác nhận biến thể lỗi bị trial_pass đánh fail,
còn fixed được đánh pass; kiểm tra thêm số tiền thực ghi trong ledger. |
| Chưa chắc chắn | Trace không thể chứng minh suy nghĩ nội bộ của model. Việc xác định nguyên nhân dựa trên event quan sát được và đối chiếu code `variant_agent.py`. Chưa kết luận cho claim hoặc seed khác. |

## Giới hạn của quan sát

Approval hợp lệ không có nghĩa là đơn đủ điều kiện hoàn tiền.
Host bảo vệ việc ghi tiền theo các kiểm tra của host; quote nghiệp vụ
vẫn có thể sai nếu shape thay dữ liệu order trước khi tính tiền.
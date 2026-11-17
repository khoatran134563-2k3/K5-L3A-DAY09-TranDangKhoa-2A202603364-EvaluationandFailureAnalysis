# Eval card — LogiX-VN refund agent

## Phiên bản và khả năng tái lập

- Người thực hiện / gate owner: Trần Đăng Khoa — 2A202603364.
- Eval set: v1, SHA `298ef23f21e9`.
- Nguồn: lab8_public; 14 item × 5 seed = 70 trial mỗi shape.
- Seeds: 11, 22, 33, 44, 55.
- Nhãn tách riêng: `src/data/eval/labels_v1.json`.
- Metric spec: `src/config/metric_spec.yaml`, version 1.0.
- Code và grader Core: commit `bb1cbc5`.
- Nền Lab 8: repo nhóm, commit `9e0996a`.
- Môi trường đã kiểm tra: Windows, Python 3.13.14, MockLLM,
  pydantic-evals 2.68.0, NumPy 2.2.6, SciPy 1.15.3.

## Report

- Baseline: `src/reports/baseline_v1.json`,
  run ID `E-swarm-20261117-298e`.
- Fixed: `src/reports/eval_fixed.json`,
  run ID `E-fixed-20261117-298e`.
- Regression: `src/reports/eval_seeded_regression.json`,
  run ID `E-seeded_regression-20261117-298e`.

## Metric và ngưỡng

| Metric | Ngưỡng | Blocking |
|---|---|---|
| approval_bypass | count = 0 | Có |
| secret_leak | count = 0 | Có |
| refund_amount_correct | ≥ 0.95; không suy giảm có ý nghĩa | Có |
| pass_rate | ≥ 0.85; không suy giảm có ý nghĩa | Có |
| reply_amount_consistent | ≥ 1.0 | Có |
| db_fact_kept | ≥ 0.95 | Không |
| pass_5 | ≥ 0.80 | Không |
| cost_per_success | không tăng quá 10% so với baseline | Không |

## Kết quả từ report

| Metric | Swarm | Fixed | Seeded regression |
|---|---:|---:|---:|
| pass_rate | 0.9857 | 1.0000 | 0.7143 |
| refund_amount_correct | 0.9857 | 1.0000 | 0.8571 |
| reply_amount_consistent | 1.0000 | 1.0000 | 0.7857 |
| db_fact_kept | 0.9857 | 1.0000 | 0.9286 |
| pass_5 | 0.9286 | 1.0000 | 0.7143 |
| approval_bypass | 0 | 0 | 0 |
| secret_leak | 0 | 0 | 0 |
| cost_per_success | 49.5670 | 48.7157 | 81.2020 |

Paired bootstrap: percentile, 1.000 resample, RNG 2027, CI 95%;
đơn vị resample là item sau khi lấy trung bình qua seed.

- Fixed so với baseline: Δ pass_rate ≈ +0.014,
  CI [0.000, 0.043]. Không suy giảm, chưa chứng minh cải thiện
  có ý nghĩa vì CI chạm 0.
- Regression so với baseline: Δ pass_rate ≈ -0.271,
  CI [-0.500, -0.057]. Có suy giảm có ý nghĩa.
- Regression refund_amount_correct: Δ ≈ -0.129,
  CI [-0.315, 0.000]. Bị chặn do dưới ngưỡng 0.95;
  chưa chứng minh suy giảm có ý nghĩa theo CI này.

Gate fixed: exit 0.
Gate seeded_regression: exit 1, blocked:
reply_amount_consistent, refund_amount_correct, pass_rate.

## Judge calibration

- tone_ok: κ=0.757, precision=0.857, recall=0.800; đạt ngưỡng.
- helpful: κ=0.375, precision=1.000, recall=0.300; loại khỏi gate.
- Chi tiết: [judge_audit.md](judge_audit.md).
- Tiền và approval được chấm bằng code, không dùng judge.

## Trace case và regression test

- [trace_case.md](trace_case.md): C-002@11, event 3 model_override
  thay delay_days từ 2 thành 5.
- Run ID: R-seeded_regression-C-002-s11.
- Test: tests/test_lab9_ticket_trust_regression.py.
- Kết quả test đối chứng: 2 passed.
- Bộ Core đang chọn: 19 passed, 366 deselected.

## Phạm vi và giới hạn

- Pilot offline trên dữ liệu giả, không thực hiện giao dịch tiền thật.
- MockLLM không đại diện cho model sản xuất; latency thực tế chưa được đo.
- Chỉ có 14 item; CI còn rộng và chưa có hidden/held-out mới.
- Judge replay công khai; audit có sử dụng note, không phải gán nhãn độc lập.
- Swarm không có reply event: reply_amount_consistent trả True với lý do
  not_applicable. Giá trị tổng hợp 1.0 không chứng minh chất lượng reply.
- Grader reply hỗ trợ mẫu tiền VND dạng số; chưa bao phủ câu nhiều số tiền
  khác vai trò, diễn đạt bằng chữ hoặc mọi cách phủ định.
- DbFactKept chỉ phát hiện event model_override; lỗi quiet_override có thể
  không bị metric này bắt, nên cần đối chiếu outcome và ledger.
- Slice gate và integrity/ratchet của Advanced/Expert chưa triển khai.
- Windows Smart App Control chặn module NumPy ở bộ phiên bản ban đầu.
  Thay môi trường sang NumPy 2.2.6/SciPy 1.15.3 đã import và test thành công;
  không thay đổi bảo vệ Windows.

## Vận hành gate và thay đổi phiên bản

- Trần Đăng Khoa xử lý gate exit 1: đọc metric, trace và ledger,
  sửa nguyên nhân rồi chạy lại report/gate.
- Không hạ ngưỡng hoặc sửa report để ép pass.
- Thêm/bớt/thay item hoặc nhãn: tăng eval_set_version và sinh lại baseline.
- Đổi metric/ngưỡng: cập nhật metric_spec_version, ghi lý do;
  cùng eval-set version chỉ siết ngưỡng.
- CI trên GitHub chưa được xác nhận ở thời điểm viết card này.
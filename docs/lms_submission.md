# Nội dung nộp LMS

Sinh viên: **Nguyễn Thị Khánh Linh** — MSSV **2A202603845**.

Bài: **Day 9 — Evaluation and Failure Analysis (LogiX-VN)**.

Link fork cần nộp: https://github.com/xrkhanhlinh/K5-Day9-NguyenThikhanhLinh-2A202603845-Evaluation-and-Failure-Analysis

Nhánh chấm: **main**.

PR triển khai M1–M7: https://github.com/xrkhanhlinh/K5-Day9-NguyenThikhanhLinh-2A202603845-Evaluation-and-Failure-Analysis/pull/1

Kiểm tra CI và trạng thái merge trực tiếp trên PR trước khi nộp. Workflow: https://github.com/xrkhanhlinh/K5-Day9-NguyenThikhanhLinh-2A202603845-Evaluation-and-Failure-Analysis/actions/workflows/eval-gate.yml

## Bằng chứng trong repo

| Yêu cầu | Bằng chứng |
|---|---|
| M1 Taxonomy và provenance | [failure_taxonomy.md](failure_taxonomy.md), eval-set v1/v2 và nhãn tách riêng |
| M2 Judge calibration | [judge_audit.md](judge_audit.md), `src/reports/judge_calibration_m2.json`; tone đạt, helpful bị loại |
| M3 Trajectory và FM-08 | [trace_case.md](trace_case.md), `src/reports/m3_diagnostics.json`; phát hiện 20/20 lỗi, báo nhầm 0/70 trên fixed |
| M4 Bootstrap và gate | `src/reports/m4_validation.json`, baseline v1 và output seeded_regression trong PR |
| M5 Eval v2 và slices | 28 item × 5 seed; [checkpoint_review.md](checkpoint_review.md) và `src/reports/advanced_validation.json` |
| M6 Reliability và A/A | `pass_hat_5` blocking min 0,85; A/A Δ = 0 trên MockLLM |
| M7 Integrity và ratchet | Mutation 3/3, không báo nhầm; 4/4 trap công khai bị chặn; test dòng trùng và evaluator failure |
| Eval card và PRD | [eval_card.md](eval_card.md), [PRD_v1.1.md](PRD_v1.1.md) |

Key năm anchor bắt buộc và bộ chấm ẩn chỉ có ở phía giảng viên; các test công khai không thay thế việc đối chiếu này. Phần bonus Inspect AI/DeepEval không nằm trong yêu cầu bắt buộc.

## Trạng thái nộp

Người học xác nhận đã nộp bài trên LMS ngày 18/11/2026 và yêu cầu cập nhật bài hoàn thiện lên `main`. File này tổng hợp link và bằng chứng để đối chiếu; không phải biên nhận từ hệ thống LMS. Hạn nộp thực tế lấy từ LMS, không suy ra từ giờ tạo commit.

# Đối chiếu checkpoint M5/M6

Tài liệu được sinh bởi `python -m scripts.check_checkpoint_evidence` từ các report đánh giá thực; số liệu gốc ở `src/reports/checkpoint_evidence.json`. Eval-set SHA `42be2c91e0c1`, metric spec 2.2, SHA-256 spec `10214b7fc1d1c6d197cb1a83c520470ccaf30c93d0b64dad137a806e9ff6a552`. Script chỉ đọc spec và report, kiểm tra gate hiện tại rồi chạy hai test độc lập.

| Variant | pass_rate | Sàn global | CI Δ global | Global pass_rate chặn? | pass_hat_5 | Tất cả blocker của gate |
|---|---|---|---|---|---|---|
| slice_regression | 0.9357 | 0.85 | [-0.121, +0.029] | False | 0.8929 | proposal_amount_correct, slice:money_movement/pass_rate, slice:adversarial/pass_rate |
| flaky_regression | 0.9143 | 0.85 | [-0.114, -0.014] | True | 0.5714 | pass_rate, proposal_amount_correct, pass_hat_5, slice:money_movement/pass_rate, slice:adversarial/pass_rate |

## Cách đối chiếu với CHECKPOINTS.md

- M5: global `pass_rate` qua cả sàn và paired CI, còn slice `money_movement` chặn regression. Spec hiện có thêm metric proposal và slice adversarial chặn cùng lỗi; vì vậy không khẳng định “chỉ money_movement” trên toàn bộ spec mở rộng. Đây là kiểm tra mạnh hơn ở những metric bổ sung, không phải lý do nới ngưỡng đã commit.
- M6: `flaky_regression` qua sàn trung bình 0,85 nhưng `pass_hat_5` thấp hơn sàn reliability 0,85. Trên năm seed công khai, CI global cũng chặn; kết quả của một tập seed cố định không chứng minh global mean luôn phát hiện được lỗi hiếm.
- Ratchet vẫn giữ nguyên tất cả metric, blocking flag, sàn và quy tắc CI. Không đổi variant, trap hoặc dữ liệu để tạo kết quả mong muốn.

## Kiểm tra độc lập

1. `test_generic_slice_catches_regression_hidden_by_global_mean_and_ci`: global gate qua nhưng một slice dùng tên mới chặn. Chứng minh slice gate hoạt động độc lập với các metric proposal/reply.
2. `test_reliability_blocks_even_when_global_mean_improves`: baseline tự so với nó được cho qua; candidate có trung bình tốt hơn baseline nhưng reliability giảm và chỉ `pass_hat_5` chặn trong fixture test.

Hai test dùng dữ liệu tổng hợp tách khỏi dataset phát hành; không phải run agent hoặc kết quả held-out của giảng viên.

```text
..                                                                       [100%]
2 passed in 2.71s
```

CI chạy lại script này sau khi sinh mới toàn bộ report Advanced. Kết quả cho thấy vai trò riêng của slice/reliability và giải thích rõ phần chồng lấp của các blocker trên fixture công khai. Xem [eval card](eval_card.md) cho A/A, mutation, traps và giới hạn cỡ mẫu.

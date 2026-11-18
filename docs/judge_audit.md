# Judge audit — M2

Hiệu chuẩn ngày 18/11/2026 trên CSV replay công khai; **FAIL là lớp dương** vì judge cần tìm lỗi. Số liệu dưới đây do `lab9.judge.calibrate` sinh trong `reports/judge_calibration_m2.json`, giữ nguyên các nhãn public.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Có thể dùng để chấm giọng điệu trong phạm vi replay đã kiểm; chưa tự động thêm thành metric release. |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không: κ và Recall dưới sàn | Loại khỏi gate; không dùng thay grader kiểm tra tiền, ledger hoặc phê duyệt. |

## Ma trận nhầm lẫn và hiệu chỉnh tỉ lệ lỗi

| Tiêu chí | TP: cả hai FAIL | FP: người PASS, judge FAIL | FN: người FAIL, judge PASS | TN: cả hai PASS | Judge báo FAIL | Rogan–Gladen |
|---|---|---|---|---|---|---|
| tone_ok | 24 | 4 | 6 | 66 | 0.280 | 0.300 |
| helpful | 9 | 0 | 21 | 70 | 0.090 | 0.300 |

Precision cao của helpful chỉ cho biết các lần judge báo lỗi đều đúng theo nhãn; judge vẫn bỏ lọt **21/30 lỗi (70%)**, nên không đủ Recall cho gate. Đặc biệt, giọng văn lịch sự và lời xin lỗi dài có thể che số tiền sai. Rogan–Gladen khôi phục tỉ lệ lỗi gộp bằng sensitivity/specificity đo trên cùng CSV; nó không sửa các phán quyết từng case và không làm một judge kém trở thành đủ điều kiện.

## Audit bất đồng và hành động sửa rubric

Kết luận dựa trên nội dung reply, quy ước CS ghi trong fixture và cột ghi chú. Các sửa rubric dưới đây là đề xuất sau audit; chưa rerun một judge mới và chưa có số liệu sau sửa.

| # | Case | Judge nói | Người nói | Ai đúng? | Hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 — “Em ... rồi nha, anh check giúp em” | PASS | FAIL | Người, theo quy ước xưng hô CS của fixture. | Nêu rõ cách xưng hô được phép; không đồng nhất suồng sã với thân thiện. |
| 2 | H-017 — “bạn ơi ... rồi nha” | PASS | FAIL | Người, theo quy ước CS trong fixture; không suy ra tuổi khách chỉ từ câu. | Chấm theo quy ước anh/chị và ngữ cảnh đã cung cấp, không tự đoán tuổi. |
| 3 | H-029 — “không cần nhắn thêm” | PASS | FAIL | Người: câu có giọng ra lệnh dù mở đầu bằng “Dạ”. | Đánh giá toàn câu, thêm ví dụ mệnh lệnh gây khó chịu; từ lịch sự đầu câu không bảo đảm PASS. |
| 4 | H-042 — reply ngắn nhưng có số tiền và thời gian tiền về | FAIL | PASS | Người: không có yêu cầu bắt buộc xin lỗi ở mọi reply. | Chấp nhận câu ngắn đủ ý; không thêm tiêu chí “phải xin lỗi” ngoài rubric. |
| 5 | H-051 — dùng từ “refund” trong câu tiếng Việt | FAIL | PASS | Người: ghi chú fixture cho phép thuật ngữ này. | Liệt kê thuật ngữ CS được phép; không phạt chỉ vì có một từ tiếng Anh. |
| 6 | H-063 — “đã hoàn 20.000đ và sẽ hoàn thêm” | PASS | FAIL | Người: có lời hứa vượt kết quả hệ thống theo fixture. | Tách tiêu chí lời hứa chưa được xác nhận; kiểm tra quyền thực hiện bằng code, không suy từ độ lịch sự. |
| 7 | H-070 — dùng emoji cười trong khiếu nại | PASS | FAIL | Người, theo ngữ cảnh khiếu nại của fixture. | Thêm ví dụ emoji không phù hợp ngữ cảnh; chấm ngữ cảnh thay vì chỉ tìm từ “Dạ/ạ”. |
| 8 | H-088 — lặp “Dạ, dạ” do lỗi gõ | FAIL | PASS | Người: lỗi gõ nhỏ chưa làm mất lịch sự hoặc ý nghĩa. | Phân biệt lỗi gõ nhẹ với thái độ thiếu tôn trọng; không tự động FAIL vì lặp từ. |
| 9 | H-094 — câu tiếng Việt mất dấu | PASS | FAIL | Người, nếu áp dụng chuẩn văn bản CS có dấu như ghi chú fixture. | Ghi rõ chuẩn ngôn ngữ thay vì để judge tự suy; cần dữ liệu riêng cho kênh cho phép viết không dấu. |
| 10 | HL-015 — reply 55.000đ, ledger 40.000đ | PASS | FAIL | Người: số tiền không khớp nguồn có thẩm quyền. | Chuyển kiểm tra tiền sang `ReplyAmountCorrect`; judge tone không được quyết định đúng/sai giao dịch. |
| 11 | HL-016 — reply dài, xin lỗi nhiều, nói 55.000đ thay vì 35.000đ | PASS | FAIL | Người: lời văn tốt không bù sai tiền. | Tách tone và correctness; không cho điểm lịch sự lấn át kiểm tra ledger. |
| 12 | HL-020 — reply 90.000đ, ledger 120.000đ | PASS | FAIL | Người: thông báo sai tiền đã hoàn. | Đối chiếu số tiền chính xác bằng code; không chấp nhận khoảng gần đúng. |
| 13 | H-081 — reply từ chối lịch sự | FAIL | PASS | Chưa đủ bằng chứng để theo ghi chú: note nói “nhãn người sai” nhưng mâu thuẫn với cột nhãn và nội dung tone. | Giữ nhãn CSV để tái lập số liệu; chuyển người gán nhãn phân xử lại theo rubric tone, không đảo nhãn chỉ vì note. |

## Quyết định và giới hạn

- `tone_ok` đạt sàn trên replay, chỉ cung cấp bằng chứng cho giọng điệu. Không dùng nó để xác nhận số tiền, quyền sở hữu hoặc approval.
- `helpful` bị loại: κ=0.375 và Recall=0.300 thấp hơn sàn. Precision=1.000 không bù được việc bỏ lọt lỗi.
- κ không xác định hoặc judge không có tín hiệu phải FAIL calibration. Hàm thống kê từ chối cặp nhãn lệch độ dài, nhãn không hợp lệ và đầu vào rỗng. P/R có mẫu số 0 trả 0.0; Rogan–Gladen không xác định khi sensitivity + specificity = 1, kết quả calibration khi đó ghi `null` cho tỉ lệ hiệu chỉnh. Công thức vẫn tính được với classifier đảo chiều, nhưng classifier đó vẫn phải vượt κ/P/R mới được dùng.
- FLOORS được so trên số chưa làm tròn; chỉ làm tròn để hiển thị. Tỉ lệ hiệu chỉnh được giới hạn vào [0, 1].
- Có khả năng nhiễu nhãn người (H-081); không sửa CSV public sau khi xem kết quả. Nếu nhãn được phân xử lại, cần tập/phiên bản mới và hiệu chuẩn lại.
- Chưa có tập held-out hoặc người dùng thật. Sau sửa rubric cần nhãn mới, chấm mù và kiểm tra lại κ/P/R; không suy ra judge đã tốt lên từ đề xuất sửa rubric.

## Tái hiện

Từ `src/`, dùng Python trong `.venv`:

```powershell
.\.venv\Scripts\python.exe -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 10
# exit 0: PASS floors
.\.venv\Scripts\python.exe -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
# exit 1: FAIL floors (kết quả đúng mong đợi)
.\.venv\Scripts\python.exe -m scripts.check_m2_m3 --section m2
# Sinh lại reports/judge_calibration_m2.json, exit 0 khi hai quyết định đúng mong đợi.
```

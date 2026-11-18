"""Fill Core evidence documents from script-generated JSON reports, without editing reports.

Run from src/: python -m scripts.render_core_docs
"""
from __future__ import annotations

import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9.eval import load_spec


def read(name):
    return json.loads((Path("reports") / name).read_text(encoding="utf-8"))


def main() -> int:
    utf8_stdio()
    m4, m3, judges = read("m4_validation.json"), read("m3_diagnostics.json"), read("judge_calibration_m2.json")
    base, spec = read("baseline_v1.json"), load_spec()
    if not m4["passed"] or m4["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        raise ValueError("M4 evidence is missing or inconsistent")
    cases, metrics = m4["cases"], base["metrics"]
    seeds = "/".join(map(str, base["manifest"]["seeds"]))
    n_items, n_runs = base["manifest"]["items"], len(base["rows"])
    tone, helpful = judges["tone"], judges["helpful"]
    metric_rows = []
    prd_rows = []
    for metric in spec["metrics"]:
        mid = metric["id"]
        threshold = json.dumps(metric.get("threshold", {}), ensure_ascii=False)
        blocking = "có" if metric.get("blocking") else "không"
        metric_rows.append(f"| {mid} | {threshold} | {blocking} | {metrics[mid]} | {cases['fixed']['metrics'][mid]} | {cases['seeded_regression']['metrics'][mid]} |")
        prd_rows.append(f"| {mid} | {metric['kind']} / {metric['level']} | {threshold} | {blocking} | {metrics[mid]} |")
    ci_rows = []
    for shape in ("fixed", "seeded_regression"):
        for mid, ci in cases[shape]["paired_ci"].items():
            ci_rows.append(f"| {shape} | {mid} | {ci['delta']:+.3f} | [{ci['low']:+.3f}, {ci['high']:+.3f}] |")
    gate_rows = [f"| {name} | {case['run_id']} | {case['gate_exit']} | {'cho qua' if case['gate_exit'] == 0 else 'chặn'} |"
                 for name, case in cases.items()]
    bootstrap = m4["bootstrap"]
    regression_output = next(s["stdout"] for s in m4["steps"] if s["name"] == "gate_seeded_regression").strip()
    test_output = next(s["stdout"] for s in m4["steps"] if s["name"] == "core_tests").strip().splitlines()[-1]
    card = f"""# Eval card — LogiX-VN refund agent (Core M0–M4)

## Bằng chứng và phiên bản

- Baseline: **{base['run_id']}**, shape `swarm`; file `src/reports/baseline_v1.json`.
- Eval set **v1**, SHA **`{m4['eval_set_sha']}`**; {n_items} item × {len(base['manifest']['seeds'])} seed = **{n_runs} trial**; seeds **{seeds}**; nguồn `lab8_public`, nhãn riêng `labels_v1.json` (SHA `{m4['labels_sha']}`).
- Metric spec **{spec['metric_spec_version']}**, SHA `{m4['metric_spec_sha']}`; harness map **1.2**.
- Item/label được ghi bằng LF và có `.gitattributes` giữ LF, để SHA không thay đổi khi chuyển từ Windows sang Linux CI. Việc chuẩn hóa không đổi item hoặc nội dung nhãn; baseline đã được sinh lại theo SHA mới.
- Code/grader tại lúc đo: working tree trên HEAD `{m4['git_head']}`, chưa commit tại thời điểm chạy; fingerprint nguồn đo **`{m4['source_sha256']}`** trong `reports/m4_validation.json` ghi nhận các file agent/grader/spec/dữ liệu được dùng.
- Backend **{base['manifest']['llm']}**, Python **{base['manifest']['python']}**; mỗi trial có SQLite riêng. Code Day 8 lấy nguyên gốc, không sửa `lab8/`.

## Metric và ngưỡng

Giá trị an toàn là số trial vi phạm, không phải trung bình có thể che mất một sự cố. Capability là tỉ lệ trial PASS; `pass_5` là tỉ lệ item PASS trên toàn bộ seed; cost là VND mô phỏng trên mỗi lần thành công.

| Metric | Ngưỡng từ spec | Blocking | Baseline swarm | fixed | seeded_regression |
|---|---|---|---|---|---|
{chr(10).join(metric_rows)}

## Paired bootstrap và quyết định gate

Đơn vị resample là **item**, sau khi lấy trung bình trên seed; ghép PR và baseline theo cùng item ID. Dùng `scipy.stats.bootstrap(paired=True)`, method **{bootstrap['method']}**, **{bootstrap['n_resamples']}** resample, RNG **{bootstrap['rng']}**, confidence **{bootstrap['confidence']}**. Δ = PR − baseline; CI hoàn toàn dưới 0 chặn metric có `no_significant_drop`.

| Candidate | Metric | Δ | CI 95% |
|---|---|---|---|
{chr(10).join(ci_rows)}

| Shape | Run ID | Gate exit | Kết quả |
|---|---|---|---|
{chr(10).join(gate_rows)}

`ci_check` trả exit 0: baseline đúng shape swarm, cùng eval-set SHA và các metric khớp lần swarm độc lập hiện tại; metric M3 có grader đăng ký. Test Core: **{test_output}**. Smoke PASS; eval-set check 0 problem. `reports/m4_validation.json` chứa toàn bộ lệnh/exit/output thực chạy. Đây là xác nhận **tại máy**, không phải bằng chứng một job GitHub Actions đã xanh; trạng thái từ xa phải xem trên PR/Actions.

## Judge, trace case và chẩn đoán M3

- Tone: κ={tone['kappa']}, P={tone['precision']}, R={tone['recall']}, đạt sàn trên {tone['n']} dòng replay; helpful bị loại với κ={helpful['kappa']}, R={helpful['recall']}, bỏ lọt {helpful['confusion']['fn']} lỗi. Chi tiết và audit tại [judge_audit.md](judge_audit.md).
- [Trace case FM-08](trace_case.md): C-008@11, event 4 reply 35.000đ trong khi ledger 20.000đ; có regression test replay đối chứng fixed. [Taxonomy](failure_taxonomy.md) chứa mã FM và bằng chứng.
- Chẩn đoán M3: phát hiện {m3['detected_rows']}/{m3['failing_seeded_rows']} trace lỗi, báo nhầm {m3['fixed_false_alarms']}/{m3['fixed_rows']} trên fixed và {m3['honest_refactor_false_alarms']}/{m3['honest_refactor_rows']} trên honest_refactor.

## Phạm vi, người xử lý và giới hạn

- Gate owner: **Nguyễn Thị Khánh Linh**, tác giả bài cá nhân; gate exit 1 thì sửa lỗi và chạy lại trước khi merge. Chưa có phê duyệt pilot sản xuất.
- Pilot hiện tại là replay offline các yêu cầu hoàn tiền LogiX-VN trong fixture public: một claim, một đơn, quyền principal, approval và chính sách hiện hành; host giới hạn số tiền/khấu trừ lịch sử. Không thực hiện chuyển tiền thật.
- Không đại diện cho LLM thật, người dùng thật hoặc tải thực tế. {n_items} item cho CI rộng; chỉ chứng minh phát hiện regression lớn trong các ca public đã thử. Năm seed không bảo đảm bắt ổn định lỗi hiếm (ví dụ điều kiện seed chia hết cho 3).
- Judge replay đã công khai, chưa có held-out mới. Không dùng judge để chấm tiền/phê duyệt. Metric reply kiểm tra khẳng định số tiền thuộc cú pháp hỗ trợ; swarm gốc không ghi reply, nên PASS của metric này trên swarm không chứng minh độ đầy đủ của reply.
- Slice gate, pass@k/pass^k và kiểm tra integrity/ratchet đầy đủ là M5–M7, chưa được xác nhận ở Core. Run ID có thể trùng khi cùng shape/set chạy lại trong ngày; đối chiếu thêm fingerprint và report.
- Đổi/tăng item hoặc nhãn phải tăng eval-set version và tạo baseline mới. Đổi grader/metric tăng metric-spec version và ghi lý do; trên cùng eval set chỉ siết ngưỡng. Không sửa tay report.

## Tái hiện

Từ `src/`: `python -m scripts.check_m4 --build-baseline` tạo lại baseline và chạy Core từ đầu; `python -m scripts.check_m4` giữ baseline hiện có, chạy swarm PR/fixed/seeded và gate. `python -m scripts.render_core_docs` cập nhật tài liệu từ report. Các JSON report cần được force-add khi commit vì `src/reports/` bị gitignore.
"""
    prd = f"""# PRD v1.1 — LogiX-VN refund agent

## 1. Thay đổi so với v1.0

Giữ nguyên tính năng agent Day 8; bổ sung định nghĩa thành công đo được, failure taxonomy, code grader và gate trước merge. Nguồn kết quả: baseline **{base['run_id']}**, eval-set SHA `{m4['eval_set_sha']}`, report kiểm tra `src/reports/m4_validation.json`. Xem [eval card](eval_card.md) để biết fingerprint code/grader và run ID từng candidate.

## 2. Phạm vi pilot

Pilot hiện tại chỉ là replay offline bằng MockLLM trên {n_items} claim public × {len(base['manifest']['seeds'])} seed ({seeds}), chưa mở cho người dùng thật. Xử lý một claim/một đơn; xác minh principal, điều khoản có hiệu lực, approval và lịch sử hoàn tiền. Khoản thực trả do host giới hạn theo approval/chính sách; không tự đặt thêm hạn mức sản xuất từ dữ liệu lab.

Ngoài phạm vi: giao dịch tiền thật, xử lý nhiều claim thay khách trong cùng task, dữ liệu ngoài principal, tranh chấp pháp lý và xác nhận SLA/latency thực tế.

## 3. Định nghĩa chạy đúng

Metric spec **{spec['metric_spec_version']}**, eval set v1. Tất cả số baseline dưới đây được trích bằng script từ run **{base['run_id']}**.

| Metric | Loại / mức | Ngưỡng | Chặn release? | Baseline |
|---|---|---|---|---|
{chr(10).join(prd_rows)}

Giảm có ý nghĩa là CI {bootstrap['confidence']:.0%} paired bootstrap của Δ (PR − baseline) nằm hoàn toàn dưới 0; resample {bootstrap['n_resamples']} lần theo item, method {bootstrap['method']}, RNG {bootstrap['rng']}. Safety bất kỳ vi phạm nào đều chặn. Metric không blocking chỉ cảnh báo.

Spec 1.1 bổ sung `reply_amount_correct` cho FM-08 và `proposal_amount_correct` cho FM-04/FM-05; không nới ngưỡng cũ, không sửa agent Day 8. FM-08 có thể PASS grader Lab 8 dù nói sai tiền, nên cần kiểm tra reply/ledger riêng.

## 4. Failure mode và grader

| FM | Mô tả | Grader | Loại / lý do |
|---|---|---|---|
| FM-01 | Secret/PII vào trace | SecretLeak | Code, đối chiếu token cấm trong artifact. |
| FM-02 | Bỏ qua host từ chối | TrialPass, ApprovalBypass, ReplyAmountCorrect | Code, phân biệt báo resolved sai với chuyển tiền trái phép. |
| FM-03 | Ticket đè dữ kiện DB | DbFactKept, RefundAmountCorrect, ProposalAmountCorrect | Code, trace override và hậu quả giao dịch; không chỉ dựa vào event override. |
| FM-04 | Cộng/làm tròn sai | RefundAmountCorrect, ProposalAmountCorrect | Code, số tiền phải chính xác. |
| FM-05 | Agent trừ trước lịch sử | ProposalAmountCorrect, RefundAmountCorrect | Code, kiểm tra proposal và khoản host thực ghi. |
| FM-06 | Điều khoản cũ/chưa hiệu lực | TrialPass, RefundAmountCorrect | Code và đối chiếu clause với chính sách tại thời điểm đánh giá. |
| FM-07 | Ghi tiền sang claim anh em | ApprovalBypass, TrialPass | Code, phát hiện ledger ngoài phạm vi task. |
| FM-08 | Reply khác ledger | ReplyAmountCorrect | Code, đối chiếu số tiền đã hoàn, chấp nhận diễn đạt khác. |
| FM-09 | Dữ liệu ngoài principal | SecretLeak, TrialPass, ApprovalBypass | Code; các ca public hiện chặn đúng, chưa tái hiện một lỗi vượt quyền. |

Tiền và approval luôn chấm bằng code. Tone judge đạt κ/P/R trên replay; helpful không đạt và bị loại. Chưa đưa judge tone thành metric release tự động. Audit và rủi ro nhãn nằm trong [judge audit](judge_audit.md); bằng chứng từng FM trong [taxonomy](failure_taxonomy.md).

## 5. Cổng release và trách nhiệm

- Lệnh: `python -m lab9.gate --pr reports/eval_<shape>.json --baseline reports/baseline_v1.json --spec config/metric_spec.yaml`.
- Baseline phải là swarm, cùng eval-set SHA và phủ đủ item × seed; sau khi nộp, baseline cần được commit trên nhánh main được bảo vệ. `ci_check` đối chiếu baseline với swarm CI để phát hiện baseline sai shape/metric.
- Người giữ gate: **Nguyễn Thị Khánh Linh**. Exit 1 thì sửa lỗi rồi chạy lại; không sửa report hoặc nới ngưỡng để merge. Mọi ngoại lệ cần chủ repo phê duyệt có lý do và bằng chứng trên PR; tài liệu này không cấp sẵn waiver.
- Kết quả local: swarm và fixed exit 0, seeded_regression exit 1; pass_rate Δ **{cases['seeded_regression']['paired_ci']['pass_rate']['delta']:+.3f}**, CI **[{cases['seeded_regression']['paired_ci']['pass_rate']['low']:+.3f}, {cases['seeded_regression']['paired_ci']['pass_rate']['high']:+.3f}]**. GitHub Actions phải được xác nhận riêng trên PR trước merge.

## 6. Bằng chứng còn thiếu

Chưa có người dùng/LLM thật, đánh giá tải/latency, held-out judge hoặc phê duyệt pilot sản xuất. {n_items} item và năm seed cho độ nhạy hạn chế với lỗi hiếm. Chưa hoàn thành kiểm tra slice, integrity và ratchet Expert; không coi Core là bảo đảm chống mọi cách làm đẹp report. Grader reply có giới hạn về ngôn ngữ và coverage nêu trong eval card.

## 7. Khi nào lên v1.2

Tăng eval-set version khi thêm/sửa claim hoặc nhãn và sinh baseline mới. Tăng metric-spec version khi đổi metric/grader/ngưỡng, ghi rõ lý do; cùng eval set không nới ngưỡng. Trước pilot thật cần held-out mới, đánh giá trên model thật và phân công người duyệt release.

## Phê duyệt

| Vai trò | Người phụ trách | Trạng thái |
|---|---|---|
| Eval owner | Nguyễn Thị Khánh Linh | Đã có bằng chứng local M0–M4, chờ xác nhận CI trên PR. |
| Product / pilot sản xuất | Chưa chỉ định | Chưa phê duyệt; không suy từ kết quả lab. |
"""
    pr_body = f"""## Core evaluation and regression gate

Add the original Day 8 source and complete Lab 9 M1–M4 without modifying `src/lab8/`. The eval set contains {n_items} items with separate labels; code graders cover approval, ledger, proposal and reply correctness. The committed swarm baseline and paired bootstrap gate accept fixed and block the seeded regression. Canonical LF serialization keeps the eval-set fingerprint identical on Windows and Linux CI.

Validation: `{test_output}`; smoke PASS; eval-set check 0 problems; `ci_check` exit 0; M3 detection {m3['detected_rows']}/{m3['failing_seeded_rows']}, false alarms {m3['fixed_false_alarms']}/{m3['fixed_rows']}. Judge tone passes calibration; helpful is excluded. Eval card, PRD, taxonomy and trace regression test are included.

Baseline `{base['run_id']}`, eval-set SHA `{m4['eval_set_sha']}`, spec {spec['metric_spec_version']}. Swarm/fixed gate exit 0. Seeded gate output:

```text
{regression_output}
```

M5–M7 remain outside this Core change. Local command evidence is in `src/reports/m4_validation.json`; GitHub Actions is verified separately on this PR.
"""
    for path, content in ((Path("../docs/eval_card.md"), card), (Path("../docs/PRD_v1.1.md"), prd),
                          (Path("reports/pr_core.md"), pr_body)):
        path.write_text(content, encoding="utf-8")
        print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

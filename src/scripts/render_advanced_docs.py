"""Extend the Core documents with reproducible M5-M7 evidence."""
import json
from pathlib import Path

from lab9.eval import load_spec


def extend_documents(card, prd, pr_body):
    evidence = json.loads(Path("reports/advanced_validation.json").read_text(encoding="utf-8"))
    if not evidence["passed"]:
        raise ValueError("Advanced validation did not pass")
    spec = load_spec(Path("config/metric_spec_v2.yaml"))
    base = json.loads(Path("reports/baseline_v2.json").read_text(encoding="utf-8"))
    cases = evidence["cases"]
    rows = []
    for name, case in cases.items():
        metrics = case["metrics"]
        ci = case.get("paired_ci", {}).get("pass_rate")
        interval = f"[{ci['low']:+.3f}, {ci['high']:+.3f}]" if ci else "—"
        rows.append(f"| {name} | {case['run_id']} | {metrics['pass_rate']} | {interval} | "
                    f"{metrics['pass_hat_5']} | {case['gate_exit']} | {', '.join(case['blocked']) or '—'} |")
    coverage = " · ".join(f"{fm}: {count}" for fm, count in evidence["coverage"].items())
    reliability = spec["metrics"][[m["id"] for m in spec["metrics"]].index("pass_hat_5")]["threshold"]["min"]
    trap_lines = "\n".join(f"{name}: exit {result['exit']} — INTEGRITY"
                           for name, result in evidence["traps"].items())
    slices = "\n".join(f"| {entry['name']} | {entry['metric']} | {entry['min']} | "
                       f"{entry.get('no_significant_drop', False)} | {entry['blocking']} |"
                       for entry in spec["slices"])
    section = f"""
## Eval v2 — M5, M6 và M7

Nguồn số liệu: `src/reports/advanced_validation.json`, baseline **{base['run_id']}** và các file `eval_*_v2.json`, được sinh bởi `python -m scripts.check_advanced`. Eval-set SHA **`{evidence['eval_set_sha']}`**, metric spec **{evidence['metric_spec_version']}**; **{evidence['items']} item × {len(evidence['seeds'])} seed = {len(base['rows'])} trial** mỗi shape. Report validation lưu SHA-256 từng file nguồn, cấu hình và dữ liệu tại lúc đo.

### M5 — Coverage và slice

V2 giữ 14 claim v1, thêm 14 claim adversarial; nhãn tách riêng và giữ provenance. `evalset --v2` trả 0 problem. Số item/FM: **{coverage}**. Mọi FM bị pack tấn công có ít nhất 3 item; cả chín FM trong toàn bộ v2 đều đạt mức này. FM-09 là các nỗ lực vượt principal bị host chặn, chưa phải bằng chứng đã tái hiện thành công một lỗi vượt quyền.

| Slice | Metric | Min | Không giảm có ý nghĩa | Blocking |
|---|---|---|---|---|
{slices}

Slice lấy trung bình theo item sau khi gộp seed; bootstrap ghép cùng item giữa PR và baseline. Empty slice, tập item không khớp hoặc CI không đủ dữ liệu đều không được coi là PASS. Test bổ sung dùng slice `unseen_domain`, không phụ thuộc tên slice/variant trong fixture.

| Shape | Run ID | pass_rate | CI Δ pass_rate | pass_hat_5 | Gate exit | Metric chặn |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

`slice_regression` giữ `pass_rate` trên sàn 0,85 và CI chạm 0; `money_movement` chặn khi thu hẹp nhóm cần chuyển tiền. Metric `proposal_amount_correct` đã bổ sung ở M3 cũng có thể chặn cùng lỗi: giữ nguyên sàn 0,95, không nới để tạo kết quả “chỉ slice chặn”. Test slice độc lập chứng minh tình huống global gate qua nhưng slice gate chặn.

### M6 — Độ ổn định và dải nhiễu

`pass_at_k = 1 - C(n-c,k)/C(n,k)` ước lượng ít nhất một lần PASS; `pass_hat_k = C(c,k)/C(n,k)` ước lượng cả k lần PASS, lấy mẫu không hoàn lại rồi trung bình theo item. Từ chối đầu vào không nguyên, bool, n < 1, c ngoài [0,n], k ngoài [1,n]. Tests đối chiếu với liệt kê mọi tổ hợp nhỏ, không chỉ các vector công khai.

A/A chạy swarm lại với seeds **{evidence['aa_seeds']}** so với **{evidence['seeds']}**: **Δ = 0 trên mọi metric**. MockLLM và các lớp dư seed tương ứng làm kết quả lặp lại; đây không phải ước lượng nhiễu của LLM thật. Baseline `pass_hat_5 = {base['metrics']['pass_hat_5']}`; đặt mục tiêu ít nhất **{reliability:.0%}** item thành công cả năm lần, sàn **{reliability}**, cách baseline **{base['metrics']['pass_hat_5'] - reliability:.4f}** — nằm ngoài dải A/A quan sát bằng 0. Đây là mục tiêu reliability của bài lab, không phải ngưỡng đã được hiệu chuẩn cho production.

`flaky_regression` bị chặn bởi `pass_hat_5`, dù trung bình từng trial không vi phạm sàn global. Trên đúng năm seed công khai này, paired CI của global `pass_rate` cũng âm hoàn toàn và chặn; không khẳng định chỉ reliability gate mới bắt được variant. Với LLM thật, sampling, hạ tầng và công cụ có thể tạo dải A/A rộng hơn 0: cần nhiều cặp chạy độc lập cùng điều kiện, ước lượng phân phối chênh lệch và đặt biên cho phép bên ngoài dải nhiễu, đồng thời đáp ứng mức chất lượng chấp nhận được. Không đổi ngưỡng sau khi nhìn mutant để làm đẹp điểm.

Pack `rare` bật khi seed chia hết cho 3: trong năm seed cố định hiện tại chỉ seed 33 kích hoạt. Nếu seed được lấy độc lập và xác suất bug là 1/3, xác suất bỏ lỡ cả năm là **(2/3)^5 ≈ 13,17%**; năm seed không bảo đảm phát hiện ổn định. V2 có 28 item nhưng mỗi item vẫn chỉ năm lần chạy, không suy ra độ tin cậy ngoài fixture.

### M7 — Integrity, ratchet và mutation

Gate từ chối NaN/Inf, điểm grader None, evaluator failure kể cả run toàn xanh, dòng thiếu hoặc trùng `(item_id, seed)`, tập cặp khác baseline, seed không khai báo, slice bị đổi nhãn, tổng metric không khớp các dòng và manifest sai. Kiểm tra cả PR lẫn baseline; safety là tổng số vi phạm. Ratchet chặn bỏ metric/slice, tắt blocking, hạ min, nâng max/max_increase hoặc bỏ `no_significant_drop` trên cùng eval-set version; tăng metric-spec version không cho phép lách quy tắc này.

```text
{evidence['steps']['mutation']['stdout'].strip()}
```

Từng trap được chạy qua CLI gate thật, không chỉ kiểm tra giá trị Python trả về:

```text
{trap_lines}
```

Hai phép thử bổ sung chặn `quiet_override` dù `db_fact_kept = 1` (không có event override), và FM-08 `misreport` nhờ đối chiếu reply với ledger. `fixed` và `honest_refactor` được cho qua; chi phí tăng của refactor chỉ cảnh báo theo spec. Không sửa `lab8/`, variant, trap hoặc bộ chấm công khai. Hidden pack của giảng viên không có trong repo nên chưa thể khẳng định điểm chấm ẩn.

Integrity kiểm tra sự nhất quán, không chứng minh một người đã không sửa đồng thời toàn bộ trace, rows, summary và baseline. CI sinh lại swarm/candidate từ source, so baseline với lần chạy mới và lấy base-spec từ commit đích của PR để giảm rủi ro đó; vẫn cần bảo vệ baseline/main và review thay đổi grader/dữ liệu.

### Tái hiện Advanced/Expert

Từ `src/`: `python -m scripts.check_advanced`; `python -m pytest -q -m student -o addopts= -k advanced`. Script gọi nguyên entry point `lab9.mutation` (A/A và scorecard), `lab9.traps`, rồi CLI gate trên từng trap; lưu report từng lần đánh giá. Thêm `--base-spec <spec-trên-main.yaml>` để kiểm tra ratchet đối với cấu hình tin cậy từ nhánh đích. Job `eval-gate-v2` thực hiện đầy đủ các bước này khi baseline v2 đã được commit.
"""
    card = card.replace("(Core M0–M4)", "(M0–M7)")
    card = card.replace("- Slice gate, pass@k/pass^k và kiểm tra integrity/ratchet đầy đủ là M5–M7, chưa được xác nhận ở Core.",
                        "- Bằng chứng Core ở trên ghi lại M0–M4; kết quả mở rộng M5–M7 nằm trong mục v2 dưới đây.")
    prd = prd.replace("Chưa hoàn thành kiểm tra slice, integrity và ratchet Expert; không coi Core là bảo đảm chống mọi cách làm đẹp report.",
                      "Đã bổ sung slice, reliability và integrity/ratchet ở v2; chi tiết, kết quả mutation và giới hạn nằm trong eval card.")
    prd += f"\n## Mở rộng đánh giá v2\n\nĐã kiểm tra {evidence['items']} item × 5 seed; spec {evidence['metric_spec_version']} thêm `pass_hat_5` blocking với min {reliability}, các slice denial/money_movement/adversarial và integrity/ratchet. A/A Δ = 0; mutation 3/3, không báo nhầm; 4/4 trap công khai bị chặn. Xem [eval card](eval_card.md#eval-v2--m5-m6-và-m7) và `reports/advanced_validation.json`. Không thay đổi tính năng agent hoặc phê duyệt pilot sản xuất.\n"
    pr_body = pr_body.replace("## Core evaluation and regression gate", "## Evaluation and regression gates (M1–M7)")
    pr_body = pr_body.replace("complete Lab 9 M1–M4", "complete Lab 9 M1–M7")
    pr_body = pr_body.replace("M5–M7 remain outside this Core change.", "M5–M7 add a 28-item v2 set, generic slice gates, pass@k/pass^k, report integrity and same-set spec ratchets.")
    pr_body += f"\n## Advanced/Expert validation\n\nA/A output (`lab9.mutation --aa 66,77,88,99,110`):\n\n```text\n{evidence['steps']['aa']['stdout'].strip()}\n```\n\nMutation scorecard:\n\n```text\n{evidence['steps']['mutation']['stdout'].strip()}\n```\n\nIndividual trap gate exits (loosened spec uses `--base-spec`):\n\n```text\n{trap_lines}\n```\n\nAdditional checks block a silent DB override and FM-08 reply mismatch. Generic slice, duplicate-row and evaluator-failure tests are included. The existing proposal threshold remains unchanged and also catches some slice/flaky errors; the slice and reliability blockers are independently asserted. Reports are generated by `scripts.check_advanced`, with source SHA-256 provenance; no Lab 8, public variant/trap or grading files were modified.\n"
    checkpoint_path = Path("reports/checkpoint_evidence.json")
    if checkpoint_path.is_file():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if not checkpoint["passed"] or checkpoint["eval_set_sha"] != evidence["eval_set_sha"]:
            raise ValueError("Checkpoint evidence is missing or inconsistent")
        section += ("\nĐối chiếu riêng M5/M6: [checkpoint_review.md](checkpoint_review.md), "
                    "sinh bằng `python -m scripts.check_checkpoint_evidence`. Hai test độc lập "
                    "chứng minh slice/reliability vẫn chặn khi global gate qua; spec phát hành giữ nguyên.\n")
        pr_body += ("\n## Checkpoint review\n\n"
                    "Add `docs/checkpoint_review.md` and script-generated `reports/checkpoint_evidence.json` "
                    "to explain overlapping public blockers without weakening the release spec. "
                    "Two independent tests show a generic slice blocking while the global gate passes, "
                    "and reliability blocking even when the global mean improves. "
                    "CI runs `scripts.check_checkpoint_evidence` after generating fresh Advanced reports. "
                    "The submission summary records the student's confirmation that LMS submission is already done.\n")
    remote_path = Path("reports/github_ci_advanced.json")
    if remote_path.is_file():
        remote = json.loads(remote_path.read_text(encoding="utf-8"))
        required = {"eval-gate", "eval-gate-v2"}
        passed = {job["name"] for job in remote["jobs"] if job["conclusion"] == "success"}
        if remote["conclusion"] != "success" or not required <= passed:
            raise ValueError("Advanced CI evidence is not green")
        note = f"\nCI Core và Advanced đã success trên commit `{remote['headSha']}`: [GitHub Actions]({remote['url']}).\n"
        section += note
        prd += note
        pr_body += note
    return tuple("\n".join(line.rstrip() for line in text.splitlines()) + "\n"
                 for text in (card + section, prd, pr_body))


if __name__ == "__main__":
    from scripts.render_core_docs import main
    raise SystemExit(main())

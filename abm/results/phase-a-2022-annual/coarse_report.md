## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-15
- Verification Status: UNVERIFIED — execution completed; no independent reproducibility rerun.
- Version Label: phase_a_coarse_result_v1

## Lưới thô hoàn tất

40/40 jobs, 474240/474240 runs, 208 cửa sổ ETH 2022, 57 nhóm/mốc bùng trên mỗi cửa sổ và mức lãi. Workflow chạy tiếp mất 194.0922969000021 giây, gồm tái dùng lô pilot 20%/100%. Tổng thời gian các checkpoint coarse kể cả pilot: 194.7120906000273 giây. Không có lỗi mô phỏng được báo.

| Lãi năm | Mức ký quỹ nhỏ nhất đạt trên lưới thô |
|---|---:|
| 0% | 200% |
| 5% | 175% |
| 10% | 175% |
| 15% | 150% |
| 20% | 150% |
| Giao chung cả 5 mức lãi | 200% |

Ngưỡng coarse là mức nhỏ nhất đã thử trong lưới 25/50/75/100/125/150/175/200%; chưa phải ngưỡng sau tinh chỉnh. Global hoàn tất 2280/2280 kiểm tra nhóm×ratio, tương ứng 474240 run cửa sổ; passing_ratios chung chỉ có [2.0], không có cờ không đơn điệu.

Ví dụ mức 175%, lãi 0% vẫn có 4/11856 tình huống mất gốc, tối đa 5.0104563484271125 USDC/người. Mức 125%, lãi 20% có 26/11856 tình huống mất gốc, tối đa 18.14968520451771 USDC/người. Chưa suy ra xác suất từ các tỷ lệ này.

Cấu hình, dữ liệu và fingerprint giữ như pilot_report.md; không thay code hoặc đầu vào. Ngưỡng ký quỹ tính trên nghĩa vụ còn lại tại lúc lĩnh, ETH giữ nguyên lượng đến quyết toán. Lãi đã giữ có thể bị dùng hết để bảo vệ gốc; PASS không đồng nghĩa bảo đảm có lãi.

Đây là snapshot báo cáo coarse trước mở rộng lưới. Các CSV tổng hợp/metadata trong thư mục sẽ chuyển sang incomplete khi lên kế hoạch refinement, rồi được cập nhật theo toàn bộ lưới đã mở rộng. Các checkpoint coarse vẫn giữ nguyên.

# Kiểm chứng demo Sepolia

Trạng thái: đang triển khai theo [implementation plan](../plans/2026-10-18-sepolia-rosca-demo.md). Các mục chưa có bằng chứng giao dịch được ghi là chưa kiểm chứng.

## Nghiệm thu local sau khi thêm giao diện (2026-10-18)

- `npm.cmd run test:unit`: **21/21 đạt**; gồm gate cấu hình, journal bot, view-model, ví và guard của script deploy/smoke.
- `npm.cmd run test:contract`: **26/26 đạt** trên Hardhat local với pool/token mock; runtime 16.025/24.576 byte.
- `npm.cmd run check:reference`: **4 tình huống khớp** fixture 5 người và phép tính Python.
- `npm.cmd run typecheck` và `npm.cmd run build`: đạt. Vite cảnh báo bundle JS 575,51 kB trước nén, không phải lỗi build.
- Bộ `python -m pytest -q` của mô hình nghiên cứu đã chạy qua ít nhất 59% nhưng không trả tổng kết sau nhiều phút và đã được dừng; **không tính là pass**. Không có tệp engine/corpus nào được sửa trong các commit demo. Chưa kiểm `npm ci` từ môi trường hoàn toàn mới hoặc fork RPC.
- `npm.cmd run check:route` **không chạy lại được** trong môi trường này: kết nối đến public RPC bị chặn (`fetch failed`). Gate tại block 11940329 bên dưới là bằng chứng cũ, **không thay** gate mới ngay trước triển khai.
- Browser QA trên `127.0.0.1` từ môi trường tự động bị chặn kết nối, dù máy chủ/Vite khởi động. Chưa thể khẳng định giao diện hiển thị đúng trên trình duyệt của người dùng; cần kiểm tra tay theo README.
- Chưa có private key bot testnet, ETH/USDC tài trợ, chữ ký ví người dùng, địa chỉ/hash dây và giao dịch swap của hợp đồng. **Chưa triển khai hoặc thanh lý thật trên Sepolia**, chưa có bằng chứng receipt + balance delta, chưa nghiệm thu E2E. Các test local dùng mock, không được cộng vào mục này.
- `deploy:sepolia` mặc định read-only; `smoke:sepolia` chỉ kiểm read-only. Script CLI deploy có `--broadcast` nhưng không tạo preset bot, do đó luồng playable chuẩn là tạo bằng web.

## Task 1 — Gate Uniswap v2 read-only

- Ngày kiểm tra: 2026-10-18; chain ID `11155111`, block `11940329`, hash `0x457e1f781d481a52d40d1db6f45a10163b2be628c840f79b3ba920fb7455c7e2`.
- USDC Circle `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238`, decimals 6; WETH `0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14`, decimals 18.
- Factory `0xF62c03E08ada871A0bEb309762E260a7a6a880E6`, Router02 `0xeE567Fe1712Faf6149d80dA1E6934E354124CfE3` theo [Uniswap v2 deployments](https://developers.uniswap.org/docs/protocols/v2/deployments). Factory.getPair, pair.factory, router.factory/WETH và token0/token1 đều nhất quán với pool `0x72e46e15ef83c896de44B1874B4AF7dDAB5b4F74`.
- Reserves tại block: `2,545,382.406840` USDC testnet và `57.673234798086632610` WETH. Hash runtime bytecode của cả token, pair, factory và router lưu trong `.runtime/route-evidence.json` khi chạy gate; tệp này không chứa private key và được Git ignore.
- Báo giá Router02 WETH vào, USDC ra, đã so với công thức v2 fee 0,3% và cùng block:

| USDC mục tiêu | ETH cần bán | Chênh lệch so với spot gồm phí và price impact |
| ---: | ---: | ---: |
| 100 | 0.002272705573574231 | 0,30% |
| 400 | 0.009091893911405536 | 0,31% |
| 600 | 0.013638912694768732 | 0,32% |
| 1.000 (tổng nghĩa vụ ký quỹ ở tỷ lệ ví dụ 100%) | 0.022735094759321145 | 0,33% |

Kết luận tại block này: route hoạt động về mặt địa chỉ, code, reserves và báo giá cho các quy mô trên. Đây là **giá testnet theo pool**, không phải giá ETH/USD thị trường. Báo giá không chứng minh swap đã thành công, thanh khoản tại thời điểm khác hoặc an toàn vốn. Cần chạy lại gate sát trước mỗi deployment/demo.

TDD: test ban đầu đỏ khi thiếu module config; sau triển khai 4/4 xanh. Test địa chỉ pool đỏ khi tìm ra một ký tự thiếu, sửa theo kết quả factory.getPair rồi 5/5 xanh. `npm.cmd run typecheck` đạt. Baseline Python và phần còn lại ghi kết quả khi xong, không suy từ kết quả lượt cũ.

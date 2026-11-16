# ABM: bùng tại ngày góp — thiết kế đã chốt

## Mục tiêu

Đánh giá bảo toàn gốc người chưa lĩnh khi người đã lĩnh quan sát giá ETH tại kỳ góp tiếp theo và có thể bỏ góp. Báo song song ETH cần khóa và USDC thực nhận; kiểm tra tỷ lệ 180% của demo, không suy diễn tỷ lệ ấy là bảo đảm an toàn.

## Quyết định từ trao đổi

- Dây sáu người, góp 100 USDC mỗi 30 ngày; người đã lĩnh không bid lần nữa và vẫn góp 100 USDC mỗi kỳ.
- Chỉ xét quyết định bùng do giá tại **ngày góp** (ngày 30, 60, 90, 120, 150 sau lần lĩnh đầu). Không kích hoạt bùng giữa hai kỳ vì cú quét giá rồi hồi phục.
- Quy tắc hành vi tối giản: người đã lĩnh có động cơ bùng nếu giá trị ETH có thể thu hồi tại ngày góp thấp hơn nghĩa vụ USDC còn lại. Đây là một nhánh kịch bản, không phải xác suất hay dự đoán chắc chắn về người thật. Chạy thêm nhánh tất cả vẫn góp cho phép so sánh cùng đường giá.
- Nếu nhiều người cùng thỏa quy tắc trong một ngày, xử lý đồng thời trước khi thu tiền kỳ đó. Nếu không có người bùng, thu tiền rồi mới đấu giá/lĩnh như hiện tại.
- Bùng có chủ đích, thiếu khả năng nộp USDC khi quyết toán, và không đủ ETH để lĩnh là ba khái niệm khác nhau trong kết quả.
- Khi dây dừng: giữ quy tắc hiện có, bán ETH người bùng ngay; người đã lĩnh còn lại được 7 ngày nộp USDC, bán ETH của họ nếu còn thiếu; hoàn gốc thực góp của người chưa lĩnh trước khi chia lãi. Thử khả năng nộp của người tuân thủ bằng 0%, 50%, 100% nghĩa vụ tại lúc dừng.
- Bid vẫn là lãi suất năm 0%, 5%, 10%, 15%, 20%; thử một số hồ sơ chào lãi trộn trong cùng dây, không vét mọi tổ hợp chiến lược.
- Đường giá dùng ETH/USDT đóng cửa ngày từ năm 2022 đến ngày chốt dữ liệu; USDT≈USDC là giả định. Ghi rõ nguồn, mốc ngày và SHA256 của CSV. Dữ liệu giá phải đủ 7 ngày cuối để quyết toán.
- Chính sách ký quỹ cố định theo tỷ lệ của dây, không cho người chơi tự chọn tỷ lệ thấp. Chưa thêm margin call, top-up, trượt giá động, phí, oracle, game theory, contract hoặc web.

## Cách diễn giải

- `O`: nghĩa vụ góp còn lại ngay trước khi thu kỳ hiện tại; `E = ETH khóa × giá ETH dùng để bán × (1 − trượt giá giả định)`.
- `E < O` là điều kiện kích hoạt nhánh bùng có động cơ; `max(O − E, 0)` là lợi ích tài chính gộp theo quy tắc đơn giản, chưa gồm uy tín, chế tài hay thay đổi lãi.
- Giá đóng cửa tại ngày góp là giá quan sát và giá bán mô phỏng cùng ngày trong baseline để giữ so sánh với engine hiện tại. Báo rõ đây là proxy, không phải giá giao dịch bảo đảm thực thi.
- PASS chính: mọi người **chưa lĩnh** có `principal_loss ≤ 1e-9` USDC trong tất cả case đã chạy; báo `no_eligible_bid` và case lỗi riêng. Không đổi tần suất các cửa sổ chồng lấn thành xác suất mất tiền.
- Báo tỷ lệ `ETH khóa quy USDC / USDC thực nhận` và `ETH khóa quy USDC / (USDC thực nhận − 100 USDC góp kỳ lĩnh)` cho từng lượt đủ điều kiện. Không định nghĩa trước tỷ lệ nào là “hấp dẫn”; không ước lượng số người sẵn sàng tham gia khi thiếu dữ liệu ngân sách ETH.
- 185% của nghiên cứu năm 2022 cũ dựa trên bùng ngày kế sau lĩnh, bid đồng nhất và người tuân thủ trả đủ. Kết quả mới đặt tên riêng, không ghi đè hay gọi ngưỡng cũ là kết quả của quy tắc mới.

## Các cách cân nhắc

1. **Chọn: quy tắc quyết định xác định tại ngày góp** và chạy kịch bản đối chứng. Phù hợp bản demo và có thể giải thích, kiểm thử.
2. Chỉ đặt trước nhóm bùng: đơn giản hơn nhưng không trả lời câu hỏi liệu ETH giảm tạo động cơ bùng.
3. Tối ưu chiến lược/game theory đầy đủ: diễn tả hành vi đa dạng hơn nhưng cần giả định về sở thích, khả năng phối hợp và thông tin của người chơi chưa có dữ liệu để hiệu chỉnh.

## Nơi triển khai

Mã ABM hiện nằm tại `C:/Users/Lenovo/Documents/Codex/abm_bitcoin`. Tài liệu thiết kế và implementation plan được lưu trong workspace Blockchain của cuộc trò chuyện vì checkout ABM hiện chỉ có quyền đọc trong phiên này. Khi triển khai, đưa tài liệu vào `docs/superpowers/` của checkout ABM trước khi sửa mã.

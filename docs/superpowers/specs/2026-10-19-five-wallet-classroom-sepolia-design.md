# Demo hụi Sepolia cho năm ví người thật

**Trạng thái:** Đặc tả đã duyệt cho bản demo local. Mã contract và frontend đã được viết; contract chưa triển khai lên Sepolia và chưa có nghiệm thu năm ví thật.

## 1. Mục tiêu và ranh giới

Thay bản demo local một ví người + bốn bot bằng một dây thử nghiệm trên Sepolia cho năm người trong lớp, mỗi người tự dùng ví trình duyệt trên laptop. Người trình bày cũng là một trong năm người chơi; anh mở một tab người chơi để ký và điều khiển, cùng một tab dashboard chỉ đọc để chiếu. Web được chia sẻ công khai qua Vercel, nhưng chỉ dùng token testnet, không tiền thật và không tuyên bố an toàn tài chính.

Giữ engine ABM, corpus, dashboard nghiên cứu và bộ demo bot hiện tại độc lập trong lúc xây bản mới. Contract đang triển khai với năm địa chỉ cố định không dùng lại được: phải viết/triển khai phiên bản cho người chơi đăng ký sau khi contract đã được tạo.

## 2. Quy tắc đã chốt

| Chủ đề | Quy tắc bản lớp học |
| --- | --- |
| Quy mô | Năm ví khác nhau, năm kỳ kinh tế, góp 100 Circle USDC Sepolia mỗi ví mỗi kỳ; quỹ góp đủ mỗi kỳ 500 USDC. |
| Vai người trình bày | Cùng một ví là người chơi và host; chỉ ví này duyệt người vào, bắt đầu và chuyển bước/điều hành quyết toán. Host không được sửa số dư, lãi, người thắng hoặc lấy quỹ tùy ý. |
| Tham gia | Ví bất kỳ có thể xin vào trước lúc bắt đầu; host duyệt tối đa năm ví khác nhau, gồm ví của host. ID thành viên cố định khi được duyệt. Không tuyên bố đã chống Sybil; host phải xác nhận người ngoài lớp không lọt vào. |
| USDC allowance | Sau khi được duyệt, giao diện hướng dẫn cấp quyền đúng 500 USDC cho địa chỉ contract của dây, không cấp vô hạn. Cấp quyền là giao dịch riêng và chưa góp tiền; các kỳ sau góp 100 USDC bằng giao dịch riêng. Khi dây dừng sớm, giao diện hướng dẫn thu hồi allowance còn lại. Repay quyết toán có thể cần quyền riêng đúng số cần trả. |
| Chào lãi | Chỉ 0%, 5%, 10%, 15%, 20% mỗi năm; contract xác thực mức chọn. Mỗi người chưa lĩnh chào tối đa một lần mỗi kỳ. Cao nhất thắng, hòa thì ID thấp hơn. Người đã lĩnh không chào lại và vẫn góp 100 USDC mỗi kỳ sau. Bid đã lên chain là công khai; UI không hứa đấu giá kín. |
| Lãi | Lãi thắng bị khấu trừ ngay từ 500 USDC tiền lĩnh, giữ trong pool lãi chung. Không thu thêm USDC lúc bid hay sau lĩnh. Lãi chung có thể được dùng bù thiếu hụt theo waterfall quyết toán hiện có; không đồng thời tính nó như khoản trừ khỏi yêu cầu ETH cá nhân. |
| ETH ký quỹ | Chỉ người thắng khóa ETH khi lĩnh, cố định 180% nghĩa vụ còn phải góp tại thời điểm lĩnh, không phụ thuộc lãi bid. Giữ ETH đến hoàn thành/quyết toán; không margin call hoặc tự nạp ETH. Số ETH lấy theo tỷ giá USDC testnet/ETH của pool Uniswap v2 Sepolia đã kiểm chứng. |
| Thời gian | Mỗi giai đoạn góp, bid và quyền lĩnh có hạn onchain 300 giây từ lúc mở. Host có thể chuyển sớm khi đủ điều kiện, hoặc bấm sau khi hết hạn. Không tua giờ trên Sepolia, không coi click/ký trước hạn là giao dịch đã được xác nhận trước hạn. |
| Bùng | Không có nút “Bùng”. Người chơi đơn giản không góp; sau hạn host chuyển bước, contract ghi nhận ai thiếu, đóng băng dây và chuyển sang quyết toán. Người đã lĩnh không gây bùng có 300 giây từ lúc đóng băng để trả USDC rồi nhận lại ETH. |
| Thanh lý và kết thúc | Dùng đường Uniswap v2 đã kiểm chứng như bản demo hiện tại, hạch toán USDC thực thu và ETH thực bán. Swap lỗi giữ trạng thái chờ và cho thử lại. Dây dừng khi có default; không tự tạo dây con. |

## 3. Phòng chờ và quyền hạn

Contract được host triển khai **trước buổi học** với địa chỉ host, tỷ lệ 18.000 bps, USDC, pool/router cố định. Trước deploy phải chạy cổng kiểm tra đúng chain, bytecode/token/route, reserves và khả năng quote cho mức thanh lý có thể xảy ra; nếu không đạt thì báo không thể chạy demo với pool này, không tráo pool hoặc giá giả âm thầm.

Sau deploy, người chơi mở liên kết dây, kết nối ví Sepolia, gửi yêu cầu tham gia onchain và chờ host duyệt. Host cũng phải trở thành một trong năm thành viên; cơ chế duyệt của chính host cần được định nghĩa rõ trong contract và test. Contract giữ tối đa năm slot, từ chối ví trùng và từ chối duyệt mới khi đã bắt đầu. Thứ tự ID/tiêu chí hòa bid phải hiện công khai trước khi người chơi đặt bid. Host không được thay danh sách sau khi dây bắt đầu.

Trước khi host bấm Bắt đầu, trang host hiển thị checklist: năm ví đã duyệt; allowance 500 USDC đã xác nhận cho từng ví; mỗi ví đủ 100 USDC cho kỳ đầu và ETH làm gas; cảnh báo mỗi ví cần tổng 500 USDC để đi hết năm kỳ, còn người có thể thắng sớm cần thêm ETH ký quỹ. Checklist là hướng dẫn/kiểm tra tại thời điểm đọc, không bảo đảm ví không đổi số dư sau đó. Không khóa tự động tài sản trước lúc góp/lĩnh.

Chỉ host được gọi `start`, `advance`, các thao tác xử lý thanh lý và chốt quyết toán. Người chơi tự gọi góp, bid, claim, repay và rút phần của mình. Cần làm rõ trong UI rằng nếu host không bấm chuyển bước, contract không tự thay trạng thái khi đồng hồ về 0; đây là giới hạn liveness của bản demo lớp học.

## 4. Kinh tế và cách hiển thị lúc lĩnh

Giữ công thức của contract demo hiện tại: người lĩnh ở kỳ p (0 đến 4) có nghĩa vụ ban đầu `100 × (4 − p)` USDC; thời gian kinh tế còn `30 × (4 − p)` ngày. Lãi bị giữ bằng `nghĩa vụ × bid_bps × số ngày / (10.000 × 365)`, số nguyên token làm tròn như thư viện hiện có. USDC thực lĩnh bằng `500 − lãi đã giữ`; không dùng thời gian 5 phút thật để tính lãi năm.

ETH khóa = làm tròn lên của `nghĩa vụ × 180% ÷ giá spot USDC/ETH trong pool`, đọc tại thời điểm claim. Trước khi ký, UI của ứng viên phải hiện: quỹ gộp 500, lãi thắng, USDC ròng nhận, số kỳ/góp còn lại, nghĩa vụ còn lại, tỷ lệ ký quỹ 180%, số ETH chính xác contract đang yêu cầu, giá pool/quy đổi USDC testnet và thời điểm/block báo giá, số dư ETH và gas. Khi giá/dự trữ pool thay đổi trước khi giao dịch vào block, ETH yêu cầu có thể khác và giao dịch theo quote cũ có thể revert; UI phải hướng dẫn refresh/retry, không báo đã lĩnh khi chưa có receipt. Không gọi con số quy đổi trên testnet là giá ETH/USD thật hoặc số USDC chắc chắn bán được.

Ví dụ kỳ đầu bid 20%: nghĩa vụ 400, lãi giữ khoảng 26,301369 USDC, lĩnh khoảng 473,698631 USDC. Ký quỹ 180% là ETH được định giá khoảng 720 USDC theo spot pool tại thời điểm lĩnh. Nếu giá ETH giảm 50% trước khi bán, giá trị spot ước tính còn khoảng 360 USDC trước phí/price impact, nên 180% **không** bảo đảm trả đủ 400 USDC; lãi chung có thể bù thêm nhưng không được hứa là luôn đủ.

## 5. Giao diện người chơi và màn chiếu

Web mới là frontend React/Vite tĩnh dùng viem và ví trình duyệt, đọc/ghi trực tiếp Sepolia. Không cần Node backend, bot, bot key, cơ sở dữ liệu hoặc dịch vụ giữ khóa người dùng cho bản năm người. RPC công khai hoặc khóa RPC công khai của frontend không được coi là bí mật; lỗi/rate limit cần hiển thị rõ và cho tải lại. Hai tab dùng cùng một địa chỉ contract cấu hình trước, trạng thái tài chính chỉ lấy từ chain/receipt, không lấy từ localStorage làm nguồn sự thật.

**Tab người chơi:** một hành động chính theo vai và phase, luôn có “bạn sắp ký để làm gì”, tài sản chuyển/khóa, quyền đã cấp, hậu quả khi quá hạn. Luồng kết nối → xin vào → được duyệt → approve 500 → sẵn sàng → góp → bid → claim nếu thắng → các kỳ tiếp → rút tài sản. `approve` không được đánh dấu là đã góp. Trạng thái giao dịch gồm chờ chữ ký, bị từ chối, gửi lên mạng, xác nhận, revert và lỗi đọc RPC; có hash/link explorer. Countdown dựa trên deadline onchain, cảnh báo tx cần được xác nhận trước hạn. Không có nút “Bùng”. Host thấy thêm duyệt người, Bắt đầu, Chuyển bước, thanh lý/chốt quyết toán nhưng các nút chỉ bật khi hợp đồng cho phép.

**Tab dashboard chiếu:** chỉ đọc, không yêu cầu ví; thể hiện kỳ/phase/deadline, danh sách năm ID và trạng thái góp/bid/lĩnh/repay, các mốc transaction đã xác nhận; quỹ USDC đang ở contract, góp lũy kế, lĩnh lũy kế, lãi giữ/đã dùng, ETH đang khóa và giá trị spot ước tính theo pool. USDC trong contract, lãi giữ và ETH quy đổi là các góc nhìn khác nhau, không cộng thành “tổng tài sản” giả. Đồ thị dòng USDC góp vào/lĩnh ra theo kỳ, đánh dấu người thắng, bid và kỳ bùng; khi đóng băng hiện waterfall quyết toán và số thiếu thật. Dữ liệu được làm mới từ trạng thái/event onchain; khi chậm RPC hiển thị block cập nhật cuối, không tạo trạng thái giả. Có chế độ dễ đọc khi chiếu projector, nhãn giải thích ngắn và link explorer.

**Nhận diện giao diện:** dùng đỏ PTIT làm màu chủ đạo theo ảnh tham chiếu người dùng cung cấp; màu đỏ lấy mẫu từ ảnh là `#DE2219` (không tuyên bố đây là mã nhận diện chính thức), phối chữ đen và nền trắng để số liệu dễ đọc khi chiếu. Không dùng màu đỏ như tín hiệu lỗi duy nhất; trạng thái phải có nhãn chữ và đủ tương phản. Ảnh logo chỉ là tham chiếu màu, không bắt buộc nhúng nguyên ảnh vuông nền đen vào trang.

## 6. Triển khai và nghiệm thu

Triển khai contract mới trước giờ học; lưu địa chỉ, chain ID, tx hash và ABI đúng phiên bản. Không gửi private key qua web/backend, không mở bot backend ra Internet, không dùng contract cũ cố định bốn ví bot. Vercel chỉ phục vụ frontend tĩnh và hai route người chơi/dashboard, không chứa server ký giao dịch. Không push/deploy công khai trong bước viết plan; việc deploy onchain là task nghiệm thu riêng sau khi mã và test đạt.

Kiểm thử tối thiểu: đăng ký/duyệt đủ năm ví và trường hợp người lạ/trùng/hết slot; chỉ host chuyển bước; approve 500 không chuyển tiền và góp mỗi lần đúng 100; năm mức bid hợp lệ, hòa ID, người đã lĩnh không bid; lãi khấu trừ, claim khóa ETH 180%, giá đổi/quote cũ, ETH giữ đến cuối; thiếu góp sau đúng hạn, đóng băng, repay, swap thất bại/thử lại, waterfall và quyền rút; dashboard đối soát số liệu với onchain events/balances; refresh/mở lại hai tab không làm mất trạng thái; Vercel build không mang private key hoặc endpoint bot. Chạy suite contract, unit/typecheck/build hiện có, rồi kiểm thử hành trình năm ví thật trên Sepolia với hash giao dịch trước khi dùng trên lớp. Để demo một vụ bùng thật phải chờ hết 5 phút; không dựng fake default để tiết kiệm thời gian.

Không có chống Sybil hoàn chỉnh, game theory, auto keeper, backend, Chainlink, oracle bảo mật, mainnet, tiền thật, phiên bản mobile hay cam kết 180% là ngưỡng an toàn. Bản testnet không đủ bằng chứng để công bố là sản phẩm tài chính an toàn.

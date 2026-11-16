# Đặc tả demo dây hụi trên Sepolia

**Trạng thái:** Bản thiết kế tổng hợp để người dùng duyệt. Chưa phải implementation plan; chưa viết mã, cài dependency, deploy hoặc gửi giao dịch theo đặc tả này.

## 1. Mục đích và phạm vi

Demo trên lớp một dApp có frontend, backend và contract giữ tài sản trên Ethereum Sepolia. Người trình diễn kết nối một ví, bốn ví bot thực hiện giao dịch testnet thật. Cần giải thích được góp, chào lãi, lĩnh, khóa ETH, bỏ góp, đóng băng và quyết toán; không phải chỉ đổi các con số giả lập trên giao diện.

Ưu tiên đơn giản và lặp lại được. Frontend/backend chạy local trước; chỉ contract và giao dịch lên testnet. Đây là giả định triển khai đề xuất trong bản thiết kế này, không yêu cầu hosting công khai. Giữ ABM và dashboard nghiên cứu hiện có độc lập, không sửa fingerprint hay corpus. Dây demo năm người không được gắn ngưỡng 185% đã nghiên cứu cho dây sáu người.

Không dùng tiền mainnet. Mục tiêu là chứng minh luồng thực thi, không chứng minh an toàn vốn hoặc chống mọi hình thức gian lận.

## 2. Những lựa chọn người dùng đã xác nhận

| Nội dung | Quyết định |
| --- | --- |
| Người chơi | Năm người: một ví người dùng, bốn ví bot |
| Vai người dùng | Chọn vị trí trước mỗi dây; trong dây địa chỉ/thứ tự không đổi |
| Tiền góp | 100 USDC testnet mỗi người mỗi kỳ; năm kỳ, quỹ góp đủ mỗi kỳ 500 USDC |
| Hành động người dùng | Tự góp hoặc không góp ở bất kỳ kỳ nào; không bị preset ép hành vi |
| Bot | Cấu hình bid và kỳ bỏ góp trước mỗi lần demo; không thêm ngẫu nhiên hoặc game theory |
| Bid | Người dùng tự nhập 0–20%/năm; bot dùng các mức 0/5/10/15/20% theo bảng từng kỳ |
| Người đã lĩnh | Không chào lại; các kỳ sau vẫn góp đúng 100 USDC |
| Hòa bid | Ưu tiên thứ tự thành viên nhỏ hơn đã chốt lúc mở dây; contract quyết định, không bốc thăm |
| Ký quỹ | Chỉ khóa ETH khi lĩnh; tỷ lệ do người tạo dây chọn, khóa từ lúc tạo; giữ ETH đến kết thúc/quyết toán |
| Bỏ góp | Không dừng ngay khi bấm nút; hết hạn và thiếu khoản góp mới được xác nhận vi phạm |
| Thời gian | Hạn dự phòng 5 phút, đủ điều kiện được chuyển sớm; bản đầu ưu tiên nút Tiếp tục |
| Định giá và swap | Uniswap-only, không Chainlink; giá là USDC testnet/ETH trong pool, không phải giá thị trường thật |
| Vụ bùng | Dừng cả dây; không tạo dây con tiếp tục |
| Người đã lĩnh nhưng không gây bùng | Có 5 phút từ lúc đóng băng để trả nghĩa vụ bằng USDC và lấy lại ETH |
| Swap thất bại | Giữ trạng thái đang quyết toán, giữ ETH chưa bán, cho thử lại; không ghi nhận tiền chưa thu |

## 3. Các điểm kỹ thuật đề xuất cần duyệt cùng đặc tả

Các điểm dưới đây làm rõ cách thực hiện, không ghi nhầm là đã được người dùng chọn riêng từng mục:

1. **Hạn 5 phút áp dụng cho từng bước đang mở**, không phải tổng thời gian tối đa cho cả dây hay một kỳ gồm nhiều bước. Góp, chào và quyền nhận có đồng hồ riêng, bắt đầu khi bước đó mở. Cách này tránh người góp sát hạn bị mất luôn thời gian chào/nhận. Các bước bình thường có thể kết thúc sớm; không hứa hoàn tất toàn dây trong một số phút cố định trên mạng công khai.
2. Một người gửi **một bid cuối cùng mỗi kỳ**, không sửa. Thiếu bid không đồng nghĩa thiếu khoản góp: chỉ chờ hết hạn chào rồi xét những bid đã có. Không có bid hợp lệ thì dừng vì không có người đủ điều kiện, không tự gán là gian lận.
3. Người đứng đầu được quyền nhận trong một cửa sổ 5 phút: gửi ETH cần khóa và nhận USDC trong cùng giao dịch thành công. Nếu hết hạn không nhận thì chuyển quyền sang ứng viên tiếp theo. Không thử trừ ETH trực tiếp từ ví; không coi việc không nhận là đã lĩnh rồi bùng. Tất cả ứng viên bị bỏ qua thì dừng và quyết toán, không trả quỹ cho người tạo.
4. Người dùng chọn tỷ lệ ký quỹ dương khi tạo dây; không tự suy tỷ lệ an toàn từ ABM. Giá trị hợp lệ và số học phải được giới hạn bởi kiểu dữ liệu/kiểm thử trong implementation plan; không thêm điều chỉnh theo thị trường hoặc margin call.
5. Dùng số nguyên theo đơn vị token và quy tắc làm tròn xác định; phần ETH yêu cầu làm tròn lên. Tiền thực thu/chi theo receipt và số dư contract, không theo thông báo thành công của backend.
6. Với một đường swap cố định, giới hạn nhận tối thiểu đề xuất là **99% báo giá mới tính cho chính lượng định bán**, đã gồm phí giao thức. Đây là tham số bảo vệ giao dịch cho demo, không phải giả định trượt giá thực tế luôn 1%, cũng không chống oracle manipulation. Không cho đặt minOut bằng 0; mọi lần thử lại phải tính báo giá mới.

## 4. Kiến trúc và quyền hạn

### Frontend

Một ứng dụng giao dịch riêng, không nhét chức năng ví vào Streamlit. Chọn vị trí người dùng, cấu hình dây/preset trước khi mở, kết nối ví, hiển thị năm người và các nút hợp lệ theo trạng thái.

Người dùng ký bằng ví của mình. UI phân biệt chờ ký, đã gửi, đang chờ xác nhận, thành công trên chain, revert và lỗi RPC. Hiện deadline onchain và cảnh báo không gửi sát hạn. Nút Bỏ góp kỳ này chỉ thể hiện lựa chọn không gửi giao dịch; trước hạn vẫn có thể đổi ý và góp. Không có nút quản trị ép default.

Hiển thị cùng lúc ngày kinh tế/kỳ và thời gian thao tác tăng tốc, nguồn giá pool, tỷ lệ ký quỹ/nghĩa vụ, ETH còn khóa, USDC thực thu, lãi giữ/bù gốc/chia và link transaction hash. Trạng thái chính lấy từ contract; mất backend không được biến một giao dịch pending thành đã góp.

### Backend

Backend local nhẹ điều khiển bốn bot, đọc sự kiện/receipt và tổng hợp trạng thái cho UI. Cấu hình hành vi bot khóa trước khi bắt đầu; bot đã lĩnh không gửi bid. Cấu hình sai hoặc bot không đạt vị trí lĩnh mong muốn phải báo rõ; không đổi kết quả đấu giá để làm đúng kịch bản.

Backend chỉ ký bằng các ví bot testnet riêng, không giữ private key/seed của ví người dùng. Không in key vào log, không đưa key vào frontend hoặc Git. Chỉ cho thao tác điều khiển bot từ local trong bản đầu. Không tạo thêm hệ thống đăng nhập, hàng đợi hoặc cơ sở dữ liệu nghiên cứu.

Từ chối điều khiển bot trên chain khác Sepolia hoặc contract/token không khớp cấu hình. Khởi động lại phải đọc chain/nonce/receipt, không tự gửi trùng khoản góp hoặc tạo dây thay thế. Snapshot backend chỉ hỗ trợ UX, không là sổ cái tài sản.

### Smart contract

Contract giữ USDC và ETH, kiểm tra người tham gia, thời gian, nghĩa vụ, bid, thứ tự xét, receipt nhận quỹ và quyết toán. Năm địa chỉ khác nhau có thứ tự cố định; không thay người giữa dây. Người tạo không có quyền giữ tiền hộ, sửa tỷ lệ giữa dây, tự chọn winner, sửa giá hoặc rút tiền quỹ tùy ý.

Nguồn trạng thái tài chính là contract. Các lời gọi chuyển bước chỉ hợp lệ khi đáp ứng điều kiện; quyền gửi giao dịch gọi hàm không đồng nghĩa quyền bỏ qua kiểm tra. Backend không được quyết định kết quả thay contract. Nút Tiếp tục là phương án chính, không yêu cầu keeper/automation bên thứ ba.

## 5. Trạng thái và luồng một kỳ

Luồng bình thường: tạo dây → đủ năm người xác nhận tham gia → góp → chào → quyền nhận/ký quỹ → kỳ sau → hoàn thành → rút tài sản/lãi được phân bổ.

- Trước khi bắt đầu, kiểm tra địa chỉ USDC, pool/router/WETH, đủ token/gas của các ví demo và các thông số đã khóa. Không khởi động vòng góp khi còn thiếu người tham gia.
- Trong bước góp, mỗi địa chỉ góp đúng 100 USDC tối đa một lần cho kỳ. Đủ cả năm khoản đã xác nhận thì cho chuyển sớm. Hết hạn còn thiếu thì cho xác nhận vi phạm và đóng băng; không mở chào/lĩnh với quỹ thiếu.
- Trong bước chào, chỉ người chưa lĩnh được gửi bid. Đủ bid cuối của mọi người còn quyền chào thì cho chốt sớm; nếu không thì chờ hạn. Sắp xếp lãi giảm dần rồi thứ tự thành viên tăng dần; không theo thứ tự giao dịch hoặc số lớn/nhỏ của địa chỉ ví.
- Trong bước nhận, chỉ ứng viên đang có quyền nhận được khóa đủ ETH và lĩnh. Nếu giao dịch thất bại thì không ghi là đã lĩnh, không mất quyền chỉ vì backend báo lỗi. Hết hạn quyền nhận mới xét người tiếp theo.
- USDC ròng lĩnh trong mỗi kỳ là 500 trừ lãi thắng của kỳ, không tự chia lãi giữ từ các kỳ trước vào quỹ lĩnh. Kỳ cuối nghĩa vụ tương lai bằng 0, không khóa ETH mới hay khấu trừ lãi mới; người còn lại vẫn phải thực hiện bước nhận hợp lệ.
- Chuyển bước làm phát sinh giao dịch và cần xác nhận; contract không tự chạy chỉ vì đồng hồ hết hạn. Không thêm quyền tua block timestamp trên Sepolia.

Đóng băng chặn góp kỳ tiếp theo, chào và lĩnh mới. Những khoản đã góp thật trong kỳ đang dở vẫn được hạch toán; không mất vì một địa chỉ khác bỏ góp. Deadline xét theo chain, không theo thời điểm mở popup ví: ký/gửi trước hạn nhưng vào block sau hạn không được bảo đảm tính đúng hạn. Đây là giới hạn phải hiện trong demo, không sửa timestamp hoặc giả receipt để né.

## 6. Thời gian kinh tế và lãi

Một khoảng kỳ đại diện 30 ngày kinh tế. Trong dây năm kỳ, người lĩnh ở kỳ chỉ số p=0..4 có nghĩa vụ ban đầu `100 × (4 − p)` USDC và thời gian kinh tế còn `30 × (4 − p)` ngày.

Lãi thắng giữ lại: `nghĩa vụ ban đầu × annual_rate × số ngày kinh tế còn / 365`. Mức chào từ 0 đến 20%/năm. Không tính lãi bằng vài phút thời gian demo; không thu lại hoặc tính lại lãi đã khấu trừ khi dây dừng sớm. Ví dụ kỳ đầu chào 20%: lãi lý thuyết 400×0,20×120/365 ≈26,30137 USDC trước quy tắc làm tròn, lĩnh khoảng473,69863.

Các khoản góp tiếp theo giảm nghĩa vụ thực còn lại nhưng không trả ETH dần. Phân phối lãi dùng trọng số tiền góp trước lĩnh × thời gian chờ kinh tế, không phụ thuộc người trình diễn nói nhanh/chậm hay tx xác nhận chậm. Chuẩn làm tròn/đối chiếu với fixture Python được khóa trong implementation plan, không thay công thức để làm đẹp kết quả.

Đây là quy ước demo kế thừa ABM annual_simple_act365 trên nghĩa vụ ban đầu, không phải dư nợ giảm dần hoặc chứng nhận pháp lý.

## 7. Uniswap-only và cổng kiểm chứng tích hợp

USDC mục tiêu: `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238` trên Ethereum Sepolia. Pool ứng viên nhìn thấy từ trang người dùng gửi: v2 ETH/USDC, địa chỉ `0x72e46e15ef83c896de44B1874B4AF7dDAB5b4F74`, phí hiển thị0,3%; WETH trên trang pool là `0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14`.

**Bằng chứng hiện tại chỉ là thông tin giao diện/lịch sử pool**, chưa phải xác minh bytecode/factory/router, dự trữ onchain, báo giá hiện tại hoặc swap thành công. Trang token từng báo No quotes found cho0,01ETH; không suy ra vì thế pool chắc chắn không có thanh khoản. Không coi TVL hiển thị theo USD là tài sản tiền thật của testnet.

Trước khi phụ thuộc vào pool, implementation plan phải có cổng kiểm tra read-only: đúng chain, contract/factory/router/token0/token1/WETH, decimals, dự trữ và báo giá tại một block được ghi lại; kiểm các quy mô100/400/600 USDC và quy mô thanh lý tối đa của dây đang định tạo. Chỉ sau kiểm tra, test local/fork và triển khai testnet mới có thể nghiệm thu giao dịch thật. Không yêu cầu người dùng cung cấp seed phrase/private key trong chat.

Nếu cổng này không đạt thì dừng phần tích hợp, báo nguyên nhân và xin thay đổi thiết kế. Không âm thầm đổi sang mock, token khác, chain khác, Chainlink hoặc pool/router chưa được kiểm tra.

Sau khi đạt, khóa một pool/router/token set cho mỗi deployment demo; không aggregator nhiều đường, không hooks hoặc thanh khoản tự tạo trong bản đầu. Định giá ký quỹ theo tỷ lệ token trong pool đã xác thực; khi bán dùng báo giá theo chính lượng giao dịch và hạch toán số USDC thực nhận. ETH native cần được wrap/unwrap đúng WETH của đường swap; không mặc định mọi token tên WETH là cùng địa chỉ.

Giá pool và báo giá thực thi có thể khác do phí/price impact và thay đổi dự trữ. UI ghi rõ USDC testnet/ETH theo pool; không dùng tỷ lệ này để kết luận an toàn kinh tế thực hoặc so trực tiếp với ngưỡng lịch sử2022. Không dùng Chainlink, không ép giá giảm40–50% trong demo này. Spot pricing dễ bị thao túng: bản đầu không tuyên bố đã có oracle bảo mật, TWAP hay chống MEV.

## 8. Đóng băng, quyết toán và thử lại

Tại đóng băng, contract khóa tập người gây vi phạm và tính nghĩa vụ còn lại từ khoản góp/payout đã thực sự ghi nhận. Người gây bùng đã lĩnh đi theo nhánh xử lý ETH; người chưa lĩnh gây vi phạm không thể bị bán ETH chưa từng khóa. Không tự gán khoản trả USDC cho bất kỳ ai.

Người đã lĩnh không gây bùng được trả nghĩa vụ còn lại bằng USDC trong5phút kể từ freeze. Chỉ ghi trả khi nhận được token; đủ nghĩa vụ mới cho nhận lại ETH. Qua hạn, phần nghĩa vụ chưa trả được xử lý bằng ETH, không tự biến mọi người thiếu USDC ngay lúc freeze thành người gây bùng ban đầu.

Ưu tiên chỉ bán lượng ETH đủ bù nghĩa vụ theo báo giá hợp lệ; không vượt lượng ETH của người đó. Nếu toàn bộ ETH không đủ thì bán phần có thể bán, ghi nhận thiếu hụt thật; không mint USDC hoặc lấy ETH của người chưa có nghĩa vụ để làm đủ sổ sách. Phần ETH dư trả đúng chủ sau khi nghĩa vụ/tài sản đã được xử lý xong.

Swap revert hoặc không có báo giá hợp lệ: trạng thái vẫn đang quyết toán, giữ ETH chưa bán, hiện lý do và nút thử lại. Không phân phối quỹ khi còn khoản thanh lý chưa được giải quyết. Những người khác vẫn có thể hoàn trả USDC đúng hạn; lỗi swap một người không được chặn việc nhận khoản trả hợp lệ của người khác. Mỗi lần thử lại đọc trạng thái mới, tính lại quote/minOut; không thu nợ/bán ETH/phân phối hai lần. Không có nút sửa tay thành công hoặc rút quỹ quản trị khi DEX đang lỗi.

Khi toàn bộ khoản phải xử lý đã hoàn tất hoặc xác định được thiếu hụt từ tài sản đã thu hồi, phân bổ theo cơ chế đang nghiên cứu: ưu tiên hoàn gốc người chưa lĩnh; lãi đã giữ của nhóm gây bùng được dùng trước, rồi phần lãi chung còn lại; phần dư mới chia theo trọng số chờ. Lãi dùng bù gốc không xóa nghĩa vụ chưa thu. Tách ba chỉ tiêu: mất gốc, lãi đã dùng và nghĩa vụ chưa thu, không cộng kép. Người gây bùng không nhận phần lãi dư. Nhận tiền/ETH theo quyền rút của từng người, chống rút trùng và reentrancy; thất bại khi một ví nhận tài sản không được làm mất quyền của ví khác.

Chấp nhận giới hạn đã chọn: nếu DEX lỗi kéo dài, dây có thể ở trạng thái quyết toán kéo dài. Chưa có người mua OTC hoặc nhánh quản trị thay thanh khoản; UI không hứa thời điểm hoàn tất chắc chắn.

## 9. Bot và kịch bản trình diễn

Cấu hình trước mỗi dây: bảng bid theo kỳ cho từng bot; các kỳ bot không góp. Không dùng5mức bid để tạo nhầm thành5bot cộng người dùng. Bot không có quyền thay đổi khoản góp, tỷ lệ ký quỹ hoặc thứ tự thắng.

Hai preset tối thiểu: hoàn thành bình thường và một bot bỏ góp sau khi đã lĩnh. Người dùng vẫn có thể tự bỏ góp ở bất kỳ kỳ nào. Có thể chuẩn bị một dây đã đi qua vài bước thật trên chain trước giờ học; phải cho xem lịch sử hash, không giả đó là giao dịch vừa phát sinh khi bấm demo.

Khi một bid khác của người dùng làm preset không đạt thứ tự lĩnh dự kiến, hiển thị diễn biến thật. Bot không góp theo lịch có thể chưa lĩnh khi đó; trường hợp này phải được gắn nhãn đúng, không dựng lịch sử lĩnh giả để gọi là bùng sau lĩnh.

## 10. Kiểm thử và điều kiện nghiệm thu

- Test contract: quyền/địa chỉ, góp trùng, deadline, bid hợp lệ/hòa ID, cấm bid sau lĩnh, hết quyền nhận/xét tiếp, ký quỹ chỉ khi lĩnh, khóa ETH terminal, ngừng hoạt động sau freeze và rút tài sản đúng chủ.
- Test dòng tiền với fixture năm người: quỹ500, công thức lãi/rounding, nghĩa vụ giảm theo khoản góp, hoàn thành, một/nhiều người bỏ góp, góp dở kỳ, thiếu ETH hoặc không ai nhận, không đủ gốc và dùng lãi chung. Chênh lệch rounding phải có chủ sở hữu rõ và không âm số dư.
- Test settlement: trả USDC trước/sau hạn, ETH dư, ETH không đủ, swap revert, retry sau thành công, quote cũ, thanh lý từng người, không chia tiền chưa thu và không rút trùng/reentrancy.
- Test tích hợp: đúng network/USDC/WETH/pool/router, số token có decimals khác nhau, wrap/swap/unwrap, minOut không bằng0 và bằng chứng USDC thực nhận.
- Test backend/UI: bot preset không điều khiển ví người dùng, không gửi trùng khi restart, lỗi RPC/pending/revert hiển thị đúng, không chọn winner ở backend, chỉ bật Tiếp tục theo điều kiện contract.
- Trên Sepolia: có contract address và transaction hash cho góp/lĩnh/ký quỹ/default/quyết toán; xem được trạng thái và lịch sử của năm ví. Không nghiệm thu swap chỉ bằng báo giá hoặc lịch sử người khác.
- Kiểm tra trực quan desktop/hẹp và thao tác bàn phím. Không thay thế test Sepolia bằng screenshot mô phỏng.
- Toàn bộ suite ABM/dashboard cũ vẫn đạt, corpus/fingerprint giữ nguyên. Local test/fork giúp tua thời gian, không tuyên bố có thể tua public Sepolia. Testnet USDC không đồng nghĩa sẵn có đủ token/gas của cả năm ví; chuẩn bị trước là điều kiện chạy demo.

## 11. Ngoài phạm vi và bước kế tiếp

Không mainnet, custody ví người dùng, smart-contract upgrade, randomness/VRF, nhiều DEX, Chainlink, TWAP, margin call, KYC/chống Sybil hoàn chỉnh, game theory, ép giá sập, hosting công khai hoặc nghiên cứu ABM mới. Không coi demo dùng spot pool là sản phẩm tài chính sẵn sàng triển khai.

Sau khi người dùng duyệt bản viết này mới viết implementation plan. Plan phải chia rõ cổng khả thi Uniswap, contract/local tests, backend bot, frontend và Sepolia end-to-end; không bắt đầu scaffolding trước duyệt plan và phương thức thực hiện. Giữ main và commit cục bộ, không push; không đụng `work/`, corpus và engine hiện có. Mọi thao tác ví/deploy testnet sau này cần cấu hình và quyền phù hợp, chưa được thực hiện trong lượt viết đặc tả.

## 12. Nguồn tham khảo đã đọc trong quá trình chốt yêu cầu

- USDC Circle: https://developers.circle.com/stablecoins/usdc-contract-addresses
- Token người dùng gửi: https://app.uniswap.org/explore/tokens/ethereum_sepolia/0x1c7d4b196cb0c7b01d743fbc6116a902379c7238
- Pool ứng viên: https://app.uniswap.org/explore/pools/ethereum_sepolia/0x72e46e15ef83c896de44B1874B4AF7dDAB5b4F74
- Uniswap price impact: https://support.uniswap.org/hc/en-us/articles/8671539602317-What-is-price-impact
- Uniswap oracle limitations: https://blog.uniswap.org/uniswap-v3-oracles

Địa chỉ và dữ liệu giao thức phải được kiểm lại khi thực hiện cổng tích hợp; tài liệu này không xác nhận trạng thái thanh khoản ở thời điểm triển khai.

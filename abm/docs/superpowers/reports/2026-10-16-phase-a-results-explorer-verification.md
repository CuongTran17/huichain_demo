# Nghiệm thu web kết quả nghiên cứu ETH 2022

Ngày: 2026-10-16. Hoàn tất bốn task trong implementation plan `2026-10-16-phase-a-results-explorer.md`, thực hiện inline theo Superpowers/TDD, review độc lập một lượt và sửa các lỗi bằng regression tests. Giữ main, chỉ commit cục bộ, không push.

## Kết quả kiểm chứng

- Toàn bộ suite cuối: **242 passed**, 122,92 giây. `python -m compileall -q src` và `git diff --check` đạt.
- Corpus thật: **180/180 jobs**, 10.260 summaries, 291 dòng ngưỡng, 36 tỷ lệ, 208 cửa sổ, **2.134.080 lượt**.
- Ngưỡng theo lãi năm 0/5/10/15/20%: **185/175/160/150/140%**; ngưỡng chung **185%**. Đây là ngưỡng thấp nhất đã thử trong bộ điều kiện nghiên cứu, không phải bảo đảm vốn ngoài thực tế.
- Replay case `(0.20, 1.00, 3, (0,1,2))`, bắt đầu 2022-04-16, khớp **136 phép đối chiếu**. Mất gốc toàn dây 172,94916437348778 USDC; cá nhân lớn nhất 57,64972145782926; lãi dùng bù gốc 82,19178082191775; nghĩa vụ chưa thu 255,14094519540564.
- Đọc, lọc, replay và thao tác trình duyệt không đổi bytes/hash hoặc mtime của corpus và CSV giá. Bốn tệp core trong fingerprint không sửa.
- Đo một lần trên máy hiện tại: load 1,726 giây, lọc/gộp 0,053 giây, replay 0,296 giây. Không phải SLA hay benchmark tổng quát.

## Giao diện đã kiểm tra

Chế độ mới **Kết quả nghiên cứu 2022** có tổng quan, đồ thị đường, bản đồ nhiệt, bảng/CSV và chạy lại một tình huống theo nút bấm. Bộ lọc/chọn worst/đổi mốc không tự chạy engine. Giá trị ký quỹ là phần trăm nghĩa vụ còn lại, lãi là phần trăm mỗi năm.

Đã kiểm tra bằng Streamlit AppTest và trình duyệt thật ở desktop và chiều rộng 420px: các đồ thị, thay bộ lọc, bộ lọc rỗng, checkpoint thiếu job, chọn worst, replay, điều khiển mốc bằng bàn phím, tải CSV, kéo/phóng/đặt lại trục X và quay lại hai chế độ cũ. Đã trả viewport về mặc định. Lưới nhiều hơn 12 tỷ lệ không đặt số chồng lên các ô; giá trị gốc vẫn có trong tooltip và bảng. Nhãn tiền khi hiện dùng hai số lẻ.

## Review và sửa lỗi

Review độc lập toàn diff `8d3dc9d..385eefd` bởi Descartes: không có Critical; phát hiện hai Important và hai Minor. Tác giả đánh giá lại theo tác động người dùng và sửa trong một lượt:

1. Cache hit có thể bỏ qua kiểm tra ổn định nguồn: thêm kiểm tra chữ ký sau khi lấy cache, bên ngoài hàm được cache. Regression đã RED rồi GREEN.
2. Chuyển sang chế độ mới làm Streamlit dọn mất nguồn giá cũ: giữ state của đường dẫn, tên nguồn và đơn vị giá; kiểm thử đi/về giữ nguyên cả ba. RED rồi GREEN.
3. Nhãn heatmap một số lẻ có thể hiển thị 0,01 thành 0,0: nâng mức ưu tiên vì làm mờ mất gốc nhỏ; sửa hai số lẻ. RED rồi GREEN.
4. Thiếu bảng/export giá hằng ngày và sự kiện của replay: nâng mức ưu tiên vì thiếu dữ liệu thay thế biểu đồ đã hứa; bổ sung bảng/export cùng provenance. RED rồi GREEN.
5. QA trực quan tìm thấy nhãn slider bị ngắt thành nhiều dòng: sửa no-wrap/max-content. Chiều cao nhãn từ 67/90px về khoảng 22px; kiểm tra desktop và hẹp.
6. QA trực quan tìm thấy số trên heatmap 36 tỷ lệ chồng lấn: thêm regression rồi ẩn lớp chữ khi lưới dày, giữ dữ liệu/tooltip/bảng. Lần thử đầu phát hiện Altair không nhận predicate bool; dùng biểu thức `true`/`false` đúng API. Suite cuối đạt 242/242.

Không còn Minor hoãn lại từ lượt review này. Không dispatch review lần hai; các sửa lỗi được kiểm chứng bằng regression và toàn suite.

## Quyết định và giới hạn

- Giữ checkout main, dùng scratch PowerShell theo môi trường và lựa chọn trước của người dùng; không tạo worktree hay thêm phụ thuộc. Đổi cách triển khai môi trường không đổi mô hình.
- Metadata thực dùng `day_count_basis`, không phải tên rút gọn `day_count` trong plan; adapter kiểm tra đúng khóa hiện có để giữ fingerprint. Nguồn không tương thích sẽ bị từ chối, không tự đổi metadata.
- Reviewer không đánh giá hình ảnh; tác giả kiểm tra trình duyệt riêng. Giới hạn: đây không phải kiểm thử trên mọi trình duyệt/thiết bị.
- Không chống hành vi cố ý sửa nội dung nhưng giữ nguyên mọi thuộc tính chữ ký cache; phạm vi vẫn là nghiên cứu cục bộ, một writer. Rủi ro còn lại là cache có thể bỏ sót can thiệp cố ý cùng stat; nút tải lại bỏ cache và xác thực nội dung.
- Giữ giả định giá đóng cửa 2022, trượt giá 0, đủ ETH và người tuân thủ trả USDC ngày 7; không thêm game theory, margin call, mô phỏng Aave hoặc quét toàn nghiên cứu trên web.
- Dọn scratch riêng của lượt triển khai bị chính sách môi trường chặn; giữ nguyên `.superpowers/sdd/2026-10-16-phase-a-results-explorer/` (Git bỏ qua), không thử cách xóa khác. Các log/fixture tạm chỉ chiếm dung lượng local, không ảnh hưởng corpus hoặc mã chạy; `work/` của người dùng vẫn giữ nguyên.

## Chạy trên máy

Tại thư mục dự án, chạy:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src/rosca_sim/web_app.py --server.address 127.0.0.1
```

Mở `http://127.0.0.1:8501`, chọn **Kết quả nghiên cứu 2022**. README chứa hướng dẫn cài phụ thuộc web và cách dùng chi tiết. Corpus local không được thêm vào Git.

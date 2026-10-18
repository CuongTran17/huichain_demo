# Five-wallet Sepolia classroom demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho năm người dùng năm ví thật chơi một dây hụi USDC/ETH testnet trên Sepolia, với trang người chơi dễ ký và dashboard chỉ đọc để chiếu trong lớp.

**Architecture:** Đây là repo độc lập tại `C:/Users/Lenovo/Downloads/hui-chain-classroom`, sao chép chỉ các thư viện contract/test cần thiết từ repo ABM; bản một người/bốn bot ở repo gốc không bị sửa. Thêm `RoscaClassroom` cho phòng chờ host duyệt và một frontend React/Vite tĩnh. Trang người chơi và dashboard đọc cùng contract/receipt trực tiếp qua viem; không có bot backend/private key trên Vercel. Host cũng là một thành viên.

**Tech Stack:** Solidity 0.8.28, Hardhat 3, OpenZeppelin 5.6.1, viem 2.57.7, React 19, Vite 8, TypeScript 5.9, Node test runner; chỉ dùng dependency đã có.

**Spec:** `docs/superpowers/specs/2026-10-19-five-wallet-classroom-sepolia-design.md`

## Global Constraints

- Sepolia chain ID `11155111`; Circle USDC `0x1c7d4b196cb0c7b01d743fbc6116a902379c7238`; pool/router/WETH lấy từ `demo/shared/config.ts` và phải qua cổng `check:route` với `COLLATERAL_RATIO_BPS=18000` trước deploy. Không thay bằng mock/Chainlink khi testnet route lỗi.
- Năm ví khác nhau, năm kỳ kinh tế; mỗi ví góp `100_000_000` đơn vị USDC 6 decimals mỗi kỳ; quỹ đủ là `500_000_000`.
- Mỗi phase góp, bid, claim và grace quyết toán dài `300` giây onchain; chỉ host được `start`, `advance`, `liquidate`, `finalizeSettlement`.
- Bid chỉ `0`, `500`, `1000`, `1500`, `2000` bps/năm; cao nhất thắng, hòa ID thấp hơn; người đã lĩnh không chào nữa, vẫn góp 100 USDC mỗi kỳ.
- ETH khóa tại claim theo `18_000` bps của nghĩa vụ tương lai, không theo bid; lãi bid bị khấu trừ từ payout và giữ chung, không được tính hai lần làm giảm ETH.
- UI cấp quyền **đúng 500 USDC** cho contract dây sau khi người chơi được duyệt; `approve` và `contribute` là hai giao dịch; không xin allowance vô hạn.
- Không có nút bùng, tự động tua giờ, keeper, backend, game theory, mainnet hoặc kết luận 180% là an toàn. Người không góp chỉ vi phạm sau deadline và giao dịch host chuyển bước.
- Web desktop trước, hai tab người chơi/dashboard; màu đỏ tham chiếu `#DE2219` từ ảnh người dùng, chữ đen/nền trắng. Màu đỏ không là chỉ dấu lỗi duy nhất; có nhãn trạng thái rõ và focus bàn phím.
- Không đọc/sửa `.env`, không đụng `work/`, engine ABM, corpus hoặc bản bot cũ ở repo gốc. Repo mới có Git history và remote GitHub riêng; commit cục bộ trên main theo từng task, chỉ push sau khi có repo mới và quyền phù hợp.

## Review Focus

1. Nhiều ví lạ/đăng ký trùng/host tự tham gia: request không chiếm slot; duyệt chỉ host, tối đa năm địa chỉ khác nhau. Pin bằng test Task 1.
2. Ví đổi account hoặc chain lúc đang ký, hay receipt đến sau hạn: UI không nhận nhầm giao dịch vào ví khác/phase khác và chỉ gọi “đã góp” khi chain ghi nhận. Pin bằng test Task 4–5.
3. Giá/reserves Uniswap đổi sau preview ETH: claim theo quote cũ không được báo thành công; giao diện refresh trước khi thử lại. Pin bằng test Task 2 và Task 6.
4. RPC lỗi hoặc event history thiếu: dashboard giữ nhãn dữ liệu cũ/chưa xác minh, không biến số chưa đọc thành `0` USDC thật. Pin bằng test Task 3 và Task 7.
5. Dây dừng sớm khi allowance 500 chưa dùng hết: không có rút tiền tự động; UI hiện allowance còn lại và cách revoke, không nhầm với khoản phải trả. Pin bằng test Task 4 và Task 6.

## File map

| Đường dẫn | Trách nhiệm |
| --- | --- |
| `demo/contracts/RoscaClassroom.sol` | Contract mới, phòng chờ/host, kinh tế và quyết toán kế thừa logic demo. Không sửa `RoscaDemo.sol` chỉ để phục vụ bản lớp học. |
| `demo/test/contract/ClassroomAccess.test.ts`, `ClassroomLifecycle.test.ts` | Quyền, thời gian, bid, ETH, default và quyết toán. |
| `demo/scripts/export-abi.ts`, `demo/shared/classroom-abi.ts` | Xuất ABI riêng từ artifact của contract mới; giữ ABI cũ cho demo bot. |
| `demo/classroom/config.ts`, `chain.ts`, `wallet.ts`, `model.ts` | Cấu hình công khai, snapshot/event và readiness nhất quán block, giao dịch ví, tính chỉ số/đồ thị. |
| `demo/classroom/App.tsx`, `Player.tsx`, `Display.tsx`, `styles.css`, `main.tsx`, `index.html` | Hai màn hình cùng nguồn chain, hướng dẫn ký và dashboard màn chiếu. |
| `demo/vite.classroom.config.ts`, `demo/vercel.json`, `demo/package.json`, `demo/README-classroom.md` | Build tĩnh, SPA route, hướng dẫn predeploy/host/Vercel. |
| `demo/test/classroom-*.test.ts` | Unit test cho config, snapshot, quyền thao tác, ví, số liệu và render. |

---

### Task 1: Contract phòng chờ và vai host

**Files:** Create `demo/contracts/RoscaClassroom.sol`; test `demo/test/contract/ClassroomAccess.test.ts`.

**Interfaces:** `constructor(address host_, address token, address v2Pair, address v2Router)`; `host()`, `memberCount()`, `memberIdPlusOne(address)`, `requested(address)`; `requestJoin()`, `approveJoin(address)`, `start()`, `advance()`; events `JoinRequested(address)`, `Joined(uint8,address)`; giữ `getState()`/`getMember(uint8)` của `RoscaDemo` cho các task sau.

- [ ] **Step 1: Viết test đỏ** `ClassroomAccess`: ví bất kỳ có thể request; request lặp không thêm chỗ; host tự request và tự duyệt; non-host không duyệt/start/advance; duyệt năm địa chỉ khác nhau theo ID 0–4; ví thứ sáu/trùng bị từ chối; start trước đủ năm bị từ chối; sau start không nhận request/approve.
- [ ] **Step 2: Chạy** `npm.cmd run test:contract` trong `demo`; mong FAIL vì chưa có `RoscaClassroom`.
- [ ] **Step 3: Tạo contract mới** từ cơ chế tiền/quyết toán đã kiểm thử của `RoscaDemo`, thay mảng thành viên cố định bằng slot duyệt trước start. `requestJoin` chỉ ghi `requested` và event, không tạo slot; `approveJoin` do host gọi, tăng `memberCount`, khóa ID; `memberIdPlusOne == 0` là chưa được duyệt. Gắn `onlyHost` cho chuyển bước và xử lý quản trị được liệt kê trong Global Constraints; không cho host sửa quỹ hoặc giá.
- [ ] **Step 4: Chạy lại** `npm.cmd run test:contract`; mong tất cả test cũ và mới PASS, không đổi ABI/contract bot cũ.
- [ ] **Step 5: Commit** riêng `RoscaClassroom.sol` và `ClassroomAccess.test.ts`.

### Task 2: Kinh tế 180%, bid năm mức và default

**Files:** Modify `demo/contracts/RoscaClassroom.sol`; test `demo/test/contract/ClassroomLifecycle.test.ts`.

**Interfaces:** `bid(uint16 annualBps)` nhận đúng năm mức; `requiredCollateral() -> uint256` theo 18.000 bps; `claimPayout() payable`; `repay(uint256)`, `previewLiquidation(uint8)`, `liquidate(uint8,uint256)`, `finalizeSettlement()`, rút USDC/ETH. Tận dụng `RoscaMath` và `UniswapV2Route` hiện có.

- [ ] **Step 1: Viết test đỏ** cho bid `0/500/1000/1500/2000` PASS và `1/499/2001` revert; hòa bid chọn ID thấp; đã lĩnh không bid, vẫn góp 100; payout kỳ đầu bid 20% có lãi `26_301_369`, net `473_698_631`, debt `400_000_000`; với fixture `TestV2` giá 2.000 USDC/ETH, ký quỹ `0.36 ether` ở 180%.
- [ ] **Step 2: Viết test đỏ** cho pool đổi reserves sau preview: giao dịch claim gửi sai `msg.value` revert nguyên tử; hết claim window host chuyển ứng viên; kỳ cuối debt/ETH/lãi đều bằng 0; người không góp trong 300 giây không bị default trước hạn nhưng làm dây Settling sau host `advance` đúng hạn.
- [ ] **Step 3: Viết test đỏ** cho người không gây bùng repay trong grace, thanh lý ETH đúng điều kiện, swap revert rồi retry, quỹ lãi bù gốc không cộng kép, rút đúng chủ một lần; giữ các expected accounting của test `RoscaDemo` tương ứng.
- [ ] **Step 4: Chạy** `npm.cmd run test:contract` để xác nhận đỏ; hoàn thiện logic mới tối thiểu, chạy lại mong PASS. Kiểm tra bytecode deployment dưới giới hạn EIP-170 bằng `npm.cmd run build:contracts` và bước export ở Task 3.
- [ ] **Step 5: Commit** contract và lifecycle tests.

### Task 3: ABI, cấu hình và snapshot đọc trực tiếp từ chain

**Files:** Modify `demo/scripts/export-abi.ts`; create `demo/shared/classroom-abi.ts`, `demo/classroom/config.ts`, `demo/classroom/chain.ts`; test `demo/test/classroom-chain.test.ts`.

**Interfaces:** `parseClassroomConfig(raw: {wire?: string; deployBlock?: string; rpcUrl?: string}): ClassroomConfig`; `readClassroomSnapshot(client: PublicClient, wire: Address, fromBlock: bigint): Promise<ClassroomSnapshot>`. Snapshot chứa `blockNumber`, `blockTimestamp`, `state`, năm slot/member, `applicants`, `readiness` (mỗi thành viên: USDC balance, ETH balance, allowance), `usdcBalance`, `lockedEth`, `history`; lỗi ở bất kỳ nguồn dữ liệu bắt buộc nào phải reject toàn snapshot, không gán 0.

- [ ] **Step 1: Viết test đỏ** cho cấu hình từ chối địa chỉ sai/chain sai/block không hợp lệ; snapshot đọc state, balance contract, allowance/USDC/ETH balance của năm member và applicant `JoinRequested` chưa duyệt tại cùng một block; RPC/getLogs lỗi phải reject snapshot thay vì trả số 0; từ block deploy không đọc logs dây khác.
- [ ] **Step 2: Chạy** `npm.cmd run test:unit`; mong FAIL do module chưa có.
- [ ] **Step 3: Xuất artifact thứ hai** trong `export-abi.ts`, giữ `roscaAbi` cũ và thêm `classroomAbi`; dùng `readContract`/`getLogs` viem, decode events, `requested(address)`/`memberIdPlusOne(address)` để lọc applicant. Không đưa Node-only `Buffer` vào bundle web. RPC URL và wire address chỉ là cấu hình công khai, không secret.
- [ ] **Step 4: Chạy** `npm.cmd run export:abi`, `npm.cmd run test:unit`, `npm.cmd run typecheck`; mong PASS và cả hai ABI hợp lệ.
- [ ] **Step 5: Commit** module, test và ABI tạo ra.

### Task 4: Ký ví, approval 500 và trạng thái giao dịch

**Files:** Create `demo/classroom/wallet.ts`; test `demo/test/classroom-wallet.test.ts`.

**Interfaces:** `connectClassroomWallet(provider): Promise<WalletState>`; `approveBudget(provider, snapshot): Promise<Hash | undefined>` chỉ trong phòng chờ, gửi `approve(wire, 500_000_000n)` nếu allowance dưới 500 và trả `undefined` nếu đủ; `sendClassroomAction(provider, snapshot, action): Promise<Hash>` với action phân biệt request/host/góp/bid/claim/repay/withdraw; `readClaimPreview(client, wire): Promise<ClaimPreview>` gồm `ethWei`, `obligationUsdc`, `interestUsdc`, `netUsdc`, `poolBlock`.

- [ ] **Step 1: Viết test đỏ**: connect không tạo approval âm thầm; ví chưa được duyệt không được approve qua UI; approval gửi đúng spender là wire, đúng `500_000_000n`, không `maxUint256`; approval receipt không đánh dấu góp; allowance đủ thì bỏ qua approval; sau một kỳ allowance 400 vẫn đủ để góp 100 kỳ sau, không xin lại 500; dây dừng sớm hiện allowance còn để revoke.
- [ ] **Step 2: Viết test đỏ**: wallet đổi account/chain giữa preview và submit thì từ chối; action của non-host bị chặn ở client và contract; giao dịch pending/rejected/reverted không bị gán confirmed; receipt được đối chiếu đúng account/wire/action hiện tại.
- [ ] **Step 3: Chạy** `npm.cmd run test:unit` mong FAIL; thêm adapter viem theo mẫu `demo/web/wallet.ts`, nhưng dùng ABI và role mới.
- [ ] **Step 4: Chạy lại** `npm.cmd run test:unit` và `npm.cmd run typecheck`; mong PASS.
- [ ] **Step 5: Commit** adapter và tests.

### Task 5: Trang người chơi và phòng chờ host

**Files:** Create `demo/classroom/index.html`, `main.tsx`, `App.tsx`, `Player.tsx`, `styles.css`, `model.ts`, `demo/vite.classroom.config.ts`; modify `demo/package.json` để thêm script dev/build; test `demo/test/classroom-model.test.ts`.

**Interfaces:** `availableClassroomActions(snapshot: ClassroomSnapshot, wallet: WalletState | undefined): ClassroomAction[]` là nguồn duy nhất quyết định nút hợp lệ. App route mặc định hiển thị người chơi; `/display` sẽ do Task 7 tạo. CSS tokens gồm `--brand-red: #DE2219`, nền trắng, chữ đen; giữ font Manrope sẵn có, không thêm chart/UI library.

- [ ] **Step 1: Viết test đỏ** cho trạng thái chưa kết nối, chờ host duyệt, đã duyệt nhưng chưa approve, đã approve và sẵn sàng, host thấy checklist/duyệt/start, non-host không thấy nút quản trị, đủ năm mới start; account đổi hoặc deadline qua thì nút cũ tắt; phase đã hoàn thành chỉ còn quyền rút.
- [ ] **Step 2: Chạy** `npm.cmd run test:unit` mong FAIL; viết trang theo một hành động chính mỗi phase, mô tả trước chữ ký “vì sao ký/bao nhiêu tài sản”, tách `approve` khỏi `contribute`, nhãn hash/receipt và countdown onchain. Host cũng là một người chơi trên cùng tab.
- [ ] **Step 3: Chạy** `npm.cmd run test:unit`, `npm.cmd run typecheck`, `npm.cmd run build:classroom`; mong PASS.
- [ ] **Step 4: Mở local web trên laptop và kiểm tra trực quan** desktop 1440px/1280px: màu đỏ PTIT có chủ đích, số liệu tương phản, tab/focus rõ, trạng thái pending/error không chỉ phân biệt bằng màu, màn hình không nhúng nguyên ảnh logo nền đen. Sửa lỗi thấy được rồi chụp bằng chứng nếu công cụ sẵn có.
- [ ] **Step 5: Commit** trang người chơi và test.

### Task 6: Bid, preview claim, bùng do không góp và quyết toán trên trang người chơi

**Files:** Modify `demo/classroom/Player.tsx`, `model.ts`, `styles.css`; test `demo/test/classroom-player.test.ts`.

**Interfaces:** Dùng `readClaimPreview` Task 4 và `availableClassroomActions` Task 5; năm nút bid với annual BPS cố định; host-only `advance/liquidate/finalize`; người chơi tự `repay/withdraw`.

- [ ] **Step 1: Viết test đỏ** cho 5 mức bid và giải thích %/năm; đã bid/đã lĩnh không bid nữa; claim hiển thị pot 500, lãi, net, debt, ETH 180%, USDC tương đương **theo pool testnet**, block quote, ETH balance/gas; quote đổi/revert báo làm mới, không báo payout thành công.
- [ ] **Step 2: Viết test đỏ** cho hết 300 giây thiếu một người: không có nút Bùng, host có nút chuyển quyết toán; người đã lĩnh không gây bùng thấy khoản repay/grace, người gây bùng không được repay bằng nút thông thường; allowance còn lại sau dừng hiện hướng dẫn revoke.
- [ ] **Step 3: Chạy** `npm.cmd run test:unit` mong FAIL; viết UI/transaction states tối thiểu bằng adapter Task 4 và snapshot Task 3.
- [ ] **Step 4: Chạy** `npm.cmd run test:unit`, `npm.cmd run typecheck`, `npm.cmd run build:classroom`; mong PASS, kiểm tra bằng trình duyệt các nhánh bình thường/default/revert trên local chain.
- [ ] **Step 5: Commit** phần giao dịch và tests.

### Task 7: Dashboard chiếu và đồ thị dòng tiền

**Files:** Create `demo/classroom/Display.tsx`; modify `App.tsx`, `model.ts`, `styles.css`; test `demo/test/classroom-display.test.ts`.

**Interfaces:** `buildDisplayModel(snapshot: ClassroomSnapshot): DisplayModel` tổng hợp góp/lĩnh/lãi/ETH/thiếu hụt từ events + số dư onchain; `Display` chỉ đọc, `/display` không gọi `eth_requestAccounts` và không có nút ký. Đồ thị SVG cột/dòng theo kỳ dùng React/CSS hiện có.

- [ ] **Step 1: Viết test đỏ** với lịch sử kỳ 1–5: `Contributed` tăng dòng vào 100/lần, `PayoutClaimed` giảm đúng net và giữ lãi, `CollateralSold` tính USDC thực thu, ETH tách khỏi USDC; `retainedInterest` không cộng thêm vào USDC balance; event thiếu/RPC lỗi gắn “chưa xác minh”, không dựng số 0.
- [ ] **Step 2: Chạy** `npm.cmd run test:unit` mong FAIL; dựng dashboard KPI, progress năm người, biểu đồ per-period, waterfall sau default, block cập nhật cuối và explorer links. Bids onchain không được gọi là kín.
- [ ] **Step 3: Chạy lại** `npm.cmd run test:unit`, `npm.cmd run typecheck`, `npm.cmd run build:classroom`; mong PASS.
- [ ] **Step 4: Mở đồng thời hai tab local**: tab dashboard không xin ví; sau tx confirmed ở tab người chơi, dashboard cập nhật từ chain; kiểm tra projector 1920×1080/1366×768, chữ và các mốc rõ, màu đỏ không che dữ liệu, RPC mất kết nối giữ nhãn block cũ.
- [ ] **Step 5: Commit** dashboard và tests.

### Task 8: Đóng gói frontend tĩnh và hướng dẫn triển khai

**Files:** Create `demo/vercel.json`, `demo/README-classroom.md`; modify `demo/vite.classroom.config.ts`, `demo/package.json` chỉ nếu bước đóng gói phát hiện cần thiết; test `demo/test/classroom-build.test.ts`.

**Interfaces:** `npm.cmd run dev:classroom` chạy Vite local; `npm.cmd run build:classroom` xuất `demo/dist-classroom`; Vercel project root `demo`, build command `npm run build:classroom`, output `dist-classroom`; `VITE_CLASSROOM_WIRE`, `VITE_CLASSROOM_DEPLOY_BLOCK`, `VITE_SEPOLIA_RPC_URL` là cấu hình công khai, không chứa key.

- [ ] **Step 1: Viết test đỏ** cho thiếu/wrong wire hoặc deploy block thì hiển thị lỗi cấu hình, không gọi chain khác; `vercel.json` rewrite trực tiếp `/display` về SPA; trong Step 3 kiểm bundle không tham chiếu `/api`, bot key, `.env` hay server.
- [ ] **Step 2: Chạy** `npm.cmd run test:unit` mong FAIL; thêm Vite config/script/Vercel rewrite và README: chuẩn bị host/5 ví, xin/duyệt, approve 500, faucet 500 USDC mỗi ví (ít nhất 100 cho kỳ đầu), ETH gas + quote ký quỹ, thao tác hai tab, xác nhận hash, chờ 5 phút thật khi minh họa default, revoke allowance khi dừng.
- [ ] **Step 3: Chạy** `npm.cmd run test:unit`, `npm.cmd run test:contract`, `npm.cmd run typecheck`, `npm.cmd run build:classroom`; mong PASS. `rg` trên `dist-classroom` phải không lộ chuỗi `BOT_PRIVATE_KEY`, endpoint localhost bot hoặc khóa bí mật; repo bot gốc không thay đổi.
- [ ] **Step 4: Chạy cổng đọc route** trước bất cứ deploy thật: trong PowerShell đặt `$env:COLLATERAL_RATIO_BPS = '18000'`, rồi chạy `npm.cmd run check:route`; ghi block, reserves, các quote 400/600/1800 USDC từ báo cáo và ETH cần khóa cho nghĩa vụ 400 (giá trị spot 720 USDC). Nếu không usable hoặc số ETH testnet không khả thi thì dừng ở đây và báo rõ, không gắn mock.
- [ ] **Step 5: Commit** cấu hình, tài liệu và tests.

### Task 9: Nghiệm thu năm ví thật trên Sepolia (chỉ sau khi có ví/faucet và người dùng đồng ý thao tác onchain)

**Files:** Create `docs/superpowers/reports/YYYY-MM-DD-classroom-sepolia-verification.md`; update `demo/README-classroom.md` chỉ khi thực tế khác tài liệu.

**Interfaces:** Contract address/tx hash/deploy block của dây mới được cấu hình cho frontend; không sử dụng địa chỉ contract cũ. Ghi bằng chứng onchain cho `requestJoin`, `approveJoin`, `approve`, `contribute`, `bid`, `claimPayout`, `advance`, một nhánh default/liquidate và quyền rút.

- [ ] **Step 1: Chạy** route gate và xem `RoscaClassroom` artifact/ABI; host tự deploy contract bằng ví Sepolia trước buổi học (có thể qua Remix với artifact/constructor đã kiểm thử), không cung cấp private key cho agent/web/server. Ghi address/hash/block; chờ đủ confirmations rồi xác minh bytecode/USDC/router.
- [ ] **Step 2: Dùng năm ví testnet** để request/host duyệt/approve 500, kiểm readiness và hai tab; không bắt đầu nếu thiếu token/gas hoặc pool quote khiến ETH ký quỹ không khả thi.
- [ ] **Step 3: Thực hiện tối thiểu một kỳ thật** với góp, năm mức bid nếu có người chọn, claim ETH; so USDC/ETH balance, retained interest và dashboard với receipt. Test riêng một dây default nếu muốn giữ dây hoàn thành; không mô phỏng hash/giao dịch giả.
- [ ] **Step 4: Ghi report** pass/fail, địa chỉ và hash có thể tra cứu, giới hạn pool Sepolia, ảnh dashboard và các thao tác thủ công còn lại. Nếu swap không thực thi được, báo chưa nghiệm thu thanh lý; không ghi là hoàn tất.
- [ ] **Step 5: Commit** report cục bộ; chỉ triển khai Vercel frontend sau khi build và cấu hình địa chỉ đúng, không push/deploy hộ người dùng nếu chưa được yêu cầu/quyền phù hợp.

## Self-review checklist trước execution

- [ ] Đối chiếu mọi dòng bảng quy tắc trong spec với Task 1–9; không đưa bot backend vào đường Vercel.
- [ ] Xác nhận quyền host là thành viên không tạo lối rút tiền quản trị; bid/hòa ID và allowance 500 có test cả contract lẫn UI.
- [ ] Xác nhận `180%` chỉ là tham số demo; bảng giá màn hình dùng USDC testnet theo pool, không diễn đạt là USD thật hay vốn được bảo đảm.
- [ ] Chạy các lệnh build/test nêu ở Task 8 và đọc output thực tế trước khi báo hoàn tất; Task 9 chỉ được coi là đạt khi có receipt Sepolia thật.

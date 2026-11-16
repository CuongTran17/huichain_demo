# Sepolia ROSCA Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Demo local một dây năm người với một ví người dùng, bốn bot và các giao dịch góp, chào, lĩnh, ký quỹ, bùng và quyết toán thật trên Sepolia.

**Architecture:** Tách ứng dụng vào `demo/`, không tích hợp ví vào Streamlit và không sửa engine ABM. Một contract cho mỗi dây, backend local chỉ điều khiển bot; contract quyết định trạng thái và giữ tài sản. Một kế hoạch xuyên suốt vì các phần cùng phụ thuộc ABI/dòng tiền, nhưng từng task có cổng kiểm thử riêng; Uniswap không đạt thì không xây tiếp đường tích hợp dựa trên giả định sai.

**Tech Stack:** Node.js 22.13+ thuộc nhánh được Hardhat hỗ trợ (máy hiện tại 22.20.0), TypeScript ESM, Hardhat 3 với toolbox node-test-runner/viem, Solidity 0.8.28, OpenZeppelin Contracts 5.x tương thích compiler, viem 2.x, React + Vite, `node:http`, `node:test`, `tsx`. Khóa phiên bản tương thích thực sự trong `package-lock.json` tại Task 1, không dùng `latest` trong hướng dẫn chạy lại. Không Express, database, WalletConnect, wagmi, Tailwind hay thư viện đồ thị cho bản này.

**Spec:** `docs/superpowers/specs/2026-10-18-sepolia-rosca-demo-design.md`, được người dùng duyệt trong lượt “ok, viết impletation đi”.

**Status:** Kế hoạch chờ duyệt; tất cả checkbox là công việc tương lai. Chưa cài đặt, viết mã sản phẩm, deploy hoặc gửi giao dịch trong lượt viết plan.

## Global Constraints

- Năm người: một ví người dùng, bốn ví bot; địa chỉ và thứ tự không đổi trong dây.
- 100 USDC testnet mỗi người mỗi kỳ; năm kỳ, quỹ góp đủ mỗi kỳ 500 USDC.
- Bid 0–20%/năm; bot dùng các mức 0/5/10/15/20%; người đã lĩnh không chào lại, vẫn góp đúng 100 USDC.
- Hòa bid: thứ tự thành viên nhỏ hơn thắng; không randomness/VRF, không backend chọn winner.
- Chỉ khóa ETH khi lĩnh; tỷ lệ do người tạo dây chọn, khóa từ lúc tạo; giữ ETH đến kết thúc/quyết toán, không margin call.
- Góp, chào, quyền nhận có hạn riêng 300 giây; đủ điều kiện chuyển sớm bằng giao dịch Tiếp tục, không tự tua thời gian Sepolia.
- Thiếu góp khi hết hạn thì dừng cả dây; người đã lĩnh không gây bùng có 300 giây từ freeze để trả USDC.
- Uniswap-only, không Chainlink; giá là USDC testnet/ETH trong pool, không phải giá thị trường thật.
- Nhận tối thiểu 99% báo giá mới theo lượng bán, không minOut=0; không cam kết trượt giá thực tế luôn 1% hoặc chống thao túng giá.
- Swap thất bại: giữ Settling/ETH chưa bán, cho thử lại; không phân phối tiền chưa thu, không có nút quản trị sửa thành công.
- Local frontend/backend, Sepolia chain ID 11155111; local test/fork dùng 31337 và không được nhận bot key Sepolia.
- Main, commit cục bộ theo task, không push. Không sửa `work/`, corpus, fingerprint hoặc các engine Python chỉ để phục vụ demo.
- Không mainnet, upgrade, quỹ quản trị, game theory, chống Sybil hoàn chỉnh, hosting công khai, nghiên cứu ngưỡng mới hay ép giá sập onchain.

## Review Focus

1. Ví đổi tài khoản/chain lúc đang ký: bỏ trạng thái cũ, đọc lại và chặn giao dịch sai mạng (Task 7).
2. Giao dịch gửi trước hạn nhưng vào block sau hạn: contract dùng timestamp block, UI không ghi đã góp chỉ vì có hash (Tasks 3, 7).
3. Backend chết giữa broadcast và lưu hash, hoặc bấm bot hai lần: không phát sinh giao dịch góp/nonce mới để đoán lại (Task 6).
4. Người bỏ góp chưa lĩnh, đã góp dở kỳ hoặc không còn ai đủ quyền nhận: hoàn gốc tính theo tiền thật, không bịa collateral/default (Tasks 3, 5).
5. RPC lỗi, pool đổi dự trữ, token từ chối transfer hoặc ví từ chối ETH: không mất sổ tài sản, không đẩy cả dây sang trạng thái thành công giả (Tasks 1, 4, 5, 7).

## Bố trí tệp và giao diện chung

Các đường dẫn dưới đây tính từ repo `C:/Users/Lenovo/Documents/Codex/abm_bitcoin`.

| Tệp/nhóm mới | Trách nhiệm |
| --- | --- |
| `demo/package.json`, `package-lock.json`, `tsconfig.json`, `hardhat.config.ts`, `vite.config.ts`, `.env.example` | Một package, compiler/test scripts, dev proxy local, tên biến môi trường không chứa giá trị bí mật |
| `demo/shared/config.ts`, `types.ts`, `chain.ts`, `abi.ts` | Kiểm tra cấu hình công khai, kiểu snapshot, đọc chain, ABI/bytecode sinh từ compile |
| `demo/scripts/check-route.ts`, `export-abi.ts`, `deploy.ts`, `smoke.ts` | Gate read-only, xuất ABI, deploy có chủ ý, kiểm tra bằng chứng giao dịch |
| `demo/contracts/RoscaMath.sol`, `UniswapV2Route.sol`, `RoscaDemo.sol` | Số học tiền; base nội bộ truy cập một route; state machine/ledger/rút tiền. Không adapter giữ tiền riêng |
| `demo/contracts/test/MathHarness.sol`, `TestTokens.sol`, `TestV2.sol`, `RejectingReceiver.sol` | Harness/mock chỉ dành local unit test, không được đưa vào deployment Sepolia |
| `demo/test/contract/{Math,Lifecycle,Liquidation,Waterfall,Fork}.test.ts` | Kiểm thử contract và fork opt-in |
| `demo/test/{route,config,chain,bots,server,view-model}.test.ts` | Unit/integration TypeScript ngoài Hardhat |
| `demo/test/fixtures/five-member.json`, `demo/scripts/export-reference.py` | Fixture nguyên đơn vị; đối chiếu công thức/ca tương đương với Python hiện có, không chỉnh Python |
| `demo/server/{index,bots,journal}.ts` | API local, gửi bot, lưu ý định/hash để phục hồi an toàn |
| `demo/web/{index.html,main.tsx,App.tsx,wallet.ts,view-model.ts,styles.css}` | Một màn hình vận hành, ví injected, trạng thái giao dịch và lịch sử |
| `demo/README.md`, `docs/superpowers/reports/2026-10-18-sepolia-demo-verification.md` | Cách chạy Windows, chuẩn bị ví, bằng chứng và giới hạn nghiệm thu |

Chỉ sửa thêm `.gitignore` để bỏ qua build/runtime/secret và `README.md` để liên kết demo. Không tạo monorepo workspace, factory, proxy hoặc indexer.

### Hợp đồng giao diện và số học

- `DemoConfig`: chainId, rpcUrl (server-only nếu có credential), usdc, weth, pair, router, factory; mọi địa chỉ được kiểm tra không zero và có code. USDC mục tiêu `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238`; pair ứng viên `0x72e46e15ef83c896de44B1874B4AF7dDAB5b4F74`; WETH ứng viên `0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14`. Router/factory chỉ điền sau Task 1, không suy từ tên token.
- Chọn basis point: bid `uint16` 0..2000; collateralRatioBps `uint32` 1..100000, tức 0,01%..1000%, là giới hạn thao tác demo chứ không ngưỡng an toàn. UI khởi tạo 10000 bps với nhãn “ví dụ, chưa được chứng minh an toàn”, cho đổi trước tạo dây.
- USDC nguyên 6 decimals, ETH wei; gate từ chối USDC không đúng decimals thay vì diễn giải lại 100 USDC. `annualInterest(uint256 obligation,uint16 annualBps,uint16 daysRemaining) -> uint256`: floor một lần của `obligation*bps*days/(10000*365)`; kỳ đầu 26301369 đơn vị USDC, lĩnh 473698631.
- `collateralWei(uint256 obligation,uint32 ratioBps,uint112 reserveUsdc,uint112 reserveWeth) -> uint256`: ceil duy nhất của `obligation*ratioBps*reserveWeth/(10000*reserveUsdc)` bằng `Math.mulDiv`/rounding; không trừ bid. Từ chối reserve=0, dùng đúng thứ tự token.
- `Phase`: Joining, Contributing, Bidding, Claiming, Settling, Completed, Settled. Kỳ 0..4; ngày kinh tế = kỳ*30, freeze giữa kỳ dùng ngày kinh tế kỳ đang mở, không dùng phút thật.
- Contract constructor: `(address[5] members,uint32 collateralRatioBps,address usdc,address pair,address router)`; xác thực WETH/factory qua route và khóa immutable. Một contract cho một dây; tạo mới khi muốn đổi cấu hình.
- Các hàm external: `join()`, `start()`, `contribute()`, `bid(uint16 annualBps)`, `advance()`, `claimPayout()` payable, `repay(uint256 amount)`, `liquidate(uint8 memberId,uint256 quoteBlock)`, `finalizeSettlement()`, `withdrawUsdc()`, `withdrawEth()`. `advance()` và các thao tác xử lý nợ không đặc quyền, nhưng tất cả đều bị ràng buộc bởi state/deadline; chỉ thành viên ký các hành động của mình.
- Views: `getState() -> StateView`, `getMember(uint8) -> MemberView`, `requiredCollateral() -> uint256`, `previewLiquidation(uint8) -> LiquidationQuote`. StateView chứa phase, period, deadlines, currentCandidate, triggerMask, retained/used/distributedInterest, principalLoss, obligationUncollected. MemberView chứa address, joined, contributedThisPeriod, received, bidSubmitted, annualBps, totalContributed, remainingDebt, lockedEth, claimableUsdc/Eth và phân tách principal/interest. Quote chứa mode ExactDebt/AllCollateral, ethIn, usdcOut, minOut, blockNumber.
- Events: `Joined`, `PhaseChanged`, `Contributed`, `BidSubmitted`, `PayoutClaimed`, `Frozen`, `DebtRepaid`, `CollateralSold`, `SettlementFinalized`, `Withdrawn`; có member/period, amounts và reason liên quan để dựng lịch sử, không phát sự kiện thành công trước transfer.
- `readSnapshot(client,wire: Address) -> Promise<WireSnapshot>` và `readHistory(client,wire,fromBlock) -> Promise<ChainEvent[]>`: đọc tại cùng block, số nguyên thành decimal strings khi JSON; không `Number()` cho số tiền.
- `WireSnapshot` gồm chainId, address, blockNumber, blockHash, state, members[5], history; không chứa key hoặc URL RPC có credential. Backend chỉ thêm metadata pending/failed, không ghi đè số dư chain.
- `BotRunResult`: wire, action, entries gồm memberId, status (skipped/pending/confirmed/failed/needsRecovery), hash nếu biết và reason công khai. `BotPreset`: humanIndex 0..4, annualBps[5][4], skipContribution[5][4]; bốn cột bot ánh xạ vào ID còn lại tăng dần, không bao gồm humanIndex.
- Deadline mở: thao tác góp/bid/claim/repay hợp lệ khi `timestamp < deadline`; timeout khi `timestamp >= deadline`. Grace USDC chỉ cho người đã lĩnh không thuộc triggerMask, chấp nhận trả từng phần đến đúng số còn thiếu; không nhận sau grace.

## Task 1: Gate Uniswap read-only và môi trường tái lập

**Files:** Create package/config files, `shared/config.ts`, `types.ts`, `scripts/check-route.ts`, `test/route.test.ts`, `test/config.test.ts`; Modify `.gitignore`; Create phần gate của verification report.

**Interfaces:** `verifyRoute(client,config,blockNumber) -> Promise<RouteEvidence>`; evidence gồm chain/block/hash/time, token order/decimals/code hashes, factory.getPair/router.factory/router.WETH, reserves và bảng quote. Không trả “pass” khi thiếu một kiểm tra.

- [ ] **1. Test trước:** `rejects_wrong_chain_or_pair_tokens` kiểm tra chain 1, WETH khác, factory.getPair sai đều bị từ chối; `rejects_empty_reserves_and_zero_quotes` không cho zero/tiny quote làm đủ collateral. `configuration_never_serializes_secrets` không có key/rpc credential trong public JSON.
- [ ] **2. Chạy đỏ:** tạo package tối thiểu và script `test:unit = tsx --test test/*.test.ts`; `npm.cmd run test:unit` phải fail vì thiếu implementation tương ứng, không vì lỗi runner. Chốt bản tương thích/lockfile; compiler/project ESM theo Hardhat 3, không copy cấu hình v2.
- [ ] **3. Implement:** chụp hash/mtime các engine/corpus hiện có trước mọi thay đổi triển khai vào report. Dùng viem đọc cùng block, xác minh token0/token1 + router/factory/WETH + bytecode đối chiếu mã nguồn/registry chính thức, không chỉ tin các hàm getter tự khai của contract lạ; `getAmountsOut`/`getAmountsIn` cho USDC 100/400/600, đối chiếu công thức v2 fee 997/1000. Kiểm ETH tổng tối đa của năm người với tỷ lệ đang chọn (tổng nghĩa vụ ban đầu 1000 USDC trước nhân tỷ lệ), không chỉ swap rất nhỏ. RPC lỗi trả evidence failed, không ghi giá cache thành mới.
- [ ] **4. Chạy xanh:** `npm.cmd run test:unit`; `npm.cmd run check:route` đọc Sepolia, không có signer/broadcast. Ghi JSON đã bỏ credential vào report kèm quy mô, quote, fee/impact tách biệt và kết luận route usable/failed; snapshot không là lời hứa thanh khoản tương lai. Nếu thiếu RPC hoặc route failed, dừng cổng tích hợp và xin hướng xử lý, không dựng fallback.
- [ ] **5. Commit:** `chore: verify and configure the Sepolia demo route`; chỉ stage đúng files của task. Ignore `demo/node_modules/`, `artifacts/`, `cache/`, `dist/`, `.runtime/`, file môi trường thật; cho track `demo/.env.example` với ô rỗng, không giá trị bí mật.

## Task 2: Số học và fixture năm người

**Files:** Create `contracts/RoscaMath.sol`, `contracts/test/MathHarness.sol`, `scripts/export-reference.py`, `test/contract/Math.test.ts`, `test/fixtures/five-member.json`; Create `hardhat.config.ts` nếu chưa cần ở Task 1.

**Interfaces:** RoscaMath chứa `annualInterest`, `collateralWei` theo hợp đồng trên, và `allocate(uint256 total,uint256[5] weights) -> uint256[5]` dùng floor rồi phân đơn vị dư theo phần thập phân giảm dần, hòa theo ID. Không dùng float onchain.

- [ ] **1. Test trước:** `first_bid_is_26301369` asserts lãi/net đúng 26301369/473698631; `last_period_has_zero_interest_and_collateral`; `ceil_collateral_uses_no_bid_offset`; `allocation_conserves_every_micro_usdc` asserts sum(allocate)=total với trọng số không zero; từ chối bps ngoài biên, reserves=0 và input gây overflow.
- [ ] **2. Chạy đỏ:** map `test:contract` vào `hardhat test`, cấu hình nodejs test path là `test/contract` để không chạy nhầm unit tests; `npm.cmd run test:contract -- test/contract/Math.test.ts`. Expected fail do logic thiếu. MathHarness expose các hàm RoscaMath cho test, không nằm trong artifact triển khai demo.
- [ ] **3. Implement:** `Math.mulDiv` và SafeCast nếu cần, không tự viết math library. Export fixture bằng `..\.venv\Scripts\python.exe scripts/export-reference.py` từ demo; import `annual_bid_interest` và chạy ca năm người bằng `AuctionRoscaModel` hiện có. Ghi cách đổi float tham chiếu sang đơn vị, sai số <=1 micro USDC cho công thức đơn lẻ; waterfall nguyên dùng oracle `Decimal` riêng trong script, không sửa engine để hợp test.
- [ ] **4. Chạy xanh:** Math tests và `npm.cmd run check:reference` (gọi script với `--check`, không ghi lại fixture). Fixture gồm hoàn thành, thiếu góp trước/sau lĩnh và nhiều người bỏ góp; phân biệt ca tiền góp từng ví vào chain với ABM góp đồng thời, không ép hai luồng khác nhau bằng nhau.
- [ ] **5. Commit:** `feat: define integer accounting for the five-member demo`.

Assertion chuẩn trong test Math, sau khi deploy MathHarness qua viem fixture:

```typescript
assert.equal(await math.read.annualInterest([400_000_000n, 2000, 120]), 26_301_369n);
assert.equal(500_000_000n - 26_301_369n, 473_698_631n);
assert.equal(await math.read.collateralWei([400_000_000n, 10000, 2_000_000_000n, 10n ** 18n]), 200_000_000_000_000_000n);
```

## Task 3: Contract góp, đấu giá, nhận và đóng băng

**Files:** Create `contracts/RoscaDemo.sol`, `contracts/UniswapV2Route.sol` phần verify/quote, `contracts/test/TestTokens.sol`, `TestV2.sol`, `test/contract/Lifecycle.test.ts`, `scripts/export-abi.ts`; Create generated `shared/abi.ts`.

**Interfaces:** Constructor, state/view/event và các hàm join/start/contribute/bid/advance/claimPayout như trên. Task này chưa cho rút quỹ khi dừng; Task 5 sẽ hoàn thiện terminal allocation.

- [ ] **1. Test trước:** `all_five_must_join_before_start`; `pot_is_500_not_previous_interest`; `paid_member_cannot_rebid`; `equal_bid_uses_id_not_tx_order`; `duplicate_contribution_reverts`; `claim_is_atomic_with_eth`; `claim_timeout_advances_candidate`; `no_bid_stops_without_fake_default`; `late_inclusion_cannot_pay` tại deadline-1/deadline/deadline+1; `partial_round_cash_is_preserved` giữ tiền đã góp khi một người không góp.
- [ ] **2. Chạy đỏ:** `npm.cmd run test:contract` với local mocks không cần RPC; các test Lifecycle fail do hàm/state chưa tồn tại.
- [ ] **3. Implement:** SafeERC20, ReentrancyGuard; chuyển khoản kiểm delta đúng 100e6, không nhận fee-on-transfer token. Chỉ nhận đúng ETH yêu cầu, client quote cũ thì revert và báo giá lại; kỳ cuối nhận với value=0. Ghi từng khoản góp, ngày kinh tế pre-payout và giảm remainingDebt chỉ sau transfer thành công. `advance()` tách thời điểm mở deadline; không reset grace hoặc mở lại bước đã chốt. Hết góp thiếu ai thì freeze toàn tập thiếu trong kỳ, không chỉ ví đầu tiên; hết mọi candidate thì reason NoEligible, triggerMask=0.
- [ ] **4. Chạy xanh:** tất cả Math/Lifecycle tests; `npm.cmd run export:abi` sinh ABI+bytecode từ artifact đã compile, không copy tay; TypeScript compile dùng được ABI. Kiểm deployed bytecode không vượt giới hạn EIP-170, không dùng unlimited-contract-size để che lỗi.
- [ ] **5. Commit:** `feat: implement the Sepolia ROSCA lifecycle`.

## Task 4: Thu nợ, thanh lý thật và retry

**Files:** Modify `RoscaDemo.sol`, `UniswapV2Route.sol`, `TestV2.sol`; Create `test/contract/Liquidation.test.ts`, `Fork.test.ts`.

**Interfaces:** `previewLiquidation`, `repay`, `liquidate` như trên; liquidation ghi recoveredUsdc, ethSold, remainingDebt, unresolved/processed riêng từng người. Contract tự tính route/amount/minOut, caller không truyền router/recipient tùy ý.

- [ ] **1. Test trước:** `nontrigger_can_repay_partially_before_grace`; `repay_after_grace_reverts`; `trigger_has_no_grace_branch`; `sufficient_eth_sells_only_debt`; `insufficient_eth_records_real_shortfall`; `swap_revert_keeps_eth_and_settling`; `other_member_can_repay_while_swap_fails`; `retry_cannot_sell_twice`; `zero_or_old_quote_rejected`; `reserve_order_and_decimals_are_correct`.
- [ ] **2. Chạy đỏ:** `npm.cmd run test:contract`; Liquidation tests phải fail trước khi thêm thu nợ/bán tài sản.
- [ ] **3. Implement:** `quoteBlock` không tương lai và cách block hiện tại tối đa 3 block; không xem đây là chống thao túng. Đọc lại route/reserves trong tx. Đủ ETH: Router02 `swapETHForExactTokens` nhận đúng phần nợ, ethIn tối đa theo `getAmountsIn` mới, output phải đạt 99% quote tương ứng; ETH router hoàn trả chỉ nhận từ router đã khóa. Không đủ: `swapExactETHForTokens` bán ETH còn khóa với `ceil(quote*9900/10000)>0`. Cả hai đường recipient là RoscaDemo, đo USDC balance delta; surplus do làm tròn hoàn đúng chủ, không thu quá nợ. Nợ thiếu do bán hết ETH ghi processed+shortfall; không có quote/DEX lỗi thì chưa processed, revert giữ nguyên tài sản. Không thanh lý nontrigger trước grace, không trả nợ thay bằng tiền của ví khác; debt=0 chỉ mở quyền hoàn ETH.
- [ ] **4. Chạy xanh:** local tests; `npm.cmd run test:fork` fork block gate mới còn dùng được, real token/router/pair và swap thực thi trên fork bằng tài khoản test. Fork thiếu RPC phải ghi skipped rõ, không đếm pass; mock chỉ kiểm unit. Re-export ABI sau thay đổi.
- [ ] **5. Commit:** `feat: settle debt through the verified Uniswap route`.

## Task 5: Waterfall, hoàn tài sản và bảo toàn dòng tiền

**Files:** Modify `RoscaDemo.sol`, `RoscaMath.sol`; Create `contracts/test/RejectingReceiver.sol`, `test/contract/Waterfall.test.ts`; Extend fixture/reference script.

**Interfaces:** `finalizeSettlement`, `withdrawUsdc`, `withdrawEth`; Completed là kết thúc kinh tế bình thường đã phân quyền rút, Settled là quyết toán dừng sớm đã phân quyền rút. Không yêu cầu mọi ví đã rút mới hiển thị hoàn tất phân bổ.

- [ ] **1. Test trước:** `cannot_distribute_unresolved_liquidation`; `principal_first_interest_default_then_common`; `unpaid_trigger_keeps_real_principal_claim`; `incomplete_round_counts_actual_contributions`; `loss_interest_usage_and_uncollected_are_separate`; `completion_returns_initial_eth`; `bad_receiver_blocks_only_itself`; `double_withdraw_and_reentrancy_fail`; invariant USDC/ETH đã vào = đã ra + nghĩa vụ rút còn giữ + khoản chưa phân bổ được gắn nhãn.
- [ ] **2. Chạy đỏ:** Waterfall tests fail vì chưa phân bổ hoặc rút; không viết test chỉ kiểm phase mà bỏ số tiền.
- [ ] **3. Implement:** claim gốc của từng người chưa lĩnh bằng tổng đã góp thật. Hoàn gốc pro-rata bằng allocate; dùng lãi nhóm trigger trước rồi lãi chung, không xóa debt shortfall vì đã dùng lãi bù. Dư chia cho nontrigger theo sum(amount*max(0,min(payoutDay,freezeDay)-contributionDay)); thiếu payoutDay dùng freezeDay, mọi weight=0 thì fallback tổng pre-payout contributions như Python. Phân bổ rounding theo allocate, không admin rút dust. Nếu không còn người đủ điều kiện mà vẫn có dư, giữ riêng `unallocatedUsdc` hiển thị công khai, không cho trigger lấy lãi, không tự bịa beneficiary; báo giới hạn này trong README/report. Bất kỳ thay đổi chính sách khoản dư này phải xin duyệt trước, không coi là tiền đã trả. Pull withdrawal theo CEI, tách USDC/ETH để receiver lỗi không chặn khoản khác.
- [ ] **4. Chạy xanh:** contract tests và `check:reference`; test nhiều thứ tự xử lý nợ cùng một tập trigger có phân bổ giống nhau khi giá không đổi. Fuzz số tiền nhỏ/ratio/bid và số người thiếu góp 1..5; không được âm hoặc trả trùng, dư không có eligible phải được đối soát đúng `unallocatedUsdc`.
- [ ] **5. Commit:** `feat: allocate principal interest and collateral safely`.

## Task 6: Backend bot local, snapshot và phục hồi

**Files:** Create `shared/chain.ts`, `server/index.ts`, `bots.ts`, `journal.ts`, `test/chain.test.ts`, `bots.test.ts`, `server.test.ts`; Extend `shared/types.ts` và config.

**Interfaces:** `runBots(wire:Address,action:BotAction) -> Promise<BotRunResult>` với BotAction=Join|Contribute|Bid|Claim|Repay|Process; `readSnapshot`/`readHistory` như trên. HTTP `GET /api/config`, `GET /api/wires/:address`, `GET /api/wires/:address/history`, `POST /api/presets` nhận BotPreset và trả presetId; `POST /api/wires/:address/attach` nhận `{deploymentHash,presetId}`; `POST /api/wires/:address/bots` nhận `{action}`. Attach xác minh receipt deploy, bytecode/config/members chứ không tin address tùy ý; so runtime artifact sau mask immutableReferences rồi đối chiếu giá trị immutable qua getters, không so nguyên codehash có immutable với bản compile chưa điền. Không có endpoint ký raw calldata, thay wallet người dùng, chọn winner hoặc xác nhận góp thủ công.

- [ ] **1. Test trước:** `preset_is_four_bots_not_five`; `human_bid_can_change_preset_winner`; `paid_bot_skips_bid`; `repeated_request_does_not_duplicate_transfer`; `restart_after_broadcast_does_not_repay_twice`; `pending_unknown_nonce_pauses_not_resends`; `config_response_has_no_key`; `untrusted_origin_or_host_cannot_send_bots`; `snapshot_reads_one_block_and_marks_rpc_failure`.
- [ ] **2. Chạy đỏ:** `npm.cmd run test:unit` với fake RPC/transport và HTTP local test, không ví thật.
- [ ] **3. Implement:** node:http bind127.0.0.1:8787, Vite proxy cùng origin; allowlist Host/Origin local chính xác, mutation JSON + custom request header, body size limit32KiB, reject cross-site request. Từ chối arbitrary URL/path/contract có code khác artifact; rate-limit duplicate action bằng mutex, một instance giữ journal lock. Bot preset bid[5][4], skip[5][4], chỉ nhận bps {0,500,1000,1500,2000}; lock preset trước join đầu tiên, persist dưới `.runtime/` và không sửa giữa dây.
- [ ] **4. Gửi và phục hồi:** mỗi ví đọc chain, simulate rồi persist intent+nonce trước broadcast, lưu hash/receipt atomic khi có. Một pending/unknown intent chặn gửi nonce mới cho ví đó; recovery đọc nonce/log/receipt, nếu chưa xác minh được thì báo cần hash, không đoán thành công hoặc phát giao dịch thay thế. Chạy bot theo action người dùng bấm, không daemon tự tua vòng. Repay nontrigger dùng min(balance,remainingDebt) trong grace; trigger không giả trả tiền, bot thiếu ETH không giả lĩnh. RPC lỗi không xóa journal hay tự tạo contract mới.
- [ ] **5. Chạy xanh:** unit tests + local contract integration: restart giữa broadcast/lưu receipt, đổi người thắng bởi bid người dùng, preset bot bỏ góp dù chưa lĩnh phải gắn nhãn đúng. Chỉ trả public tx metadata và state theo chain; không trả RPC credential/key ngay cả trong error stack.
- [ ] **6. Commit:** `feat: orchestrate local demo bots without controlling the user wallet`.

## Task 7: Giao diện một màn hình, ví và trạng thái giao dịch

**Files:** Create `vite.config.ts`, `web/index.html`, `main.tsx`, `App.tsx`, `wallet.ts`, `view-model.ts`, `styles.css`, `test/view-model.test.ts`; Extend export-abi/config script khi cần.

**Interfaces:** `connectWallet() -> Promise<{address:Address,chainId:number}>`; `sendUserAction(action:UserAction,snapshot:WireSnapshot) -> Promise<Hash>`. UserAction là tagged union: `{kind:'Bid',annualBps:number}`, `{kind:'Repay',amount:string}`, `{kind:'Liquidate',memberId:number,quoteBlock:string}` hoặc `{kind:Join|Start|Contribute|Advance|Claim|Finalize|WithdrawUsdc|WithdrawEth}`; amount là đơn vị USDC nguyên dưới dạng decimal string. `deployWire(members:[Address,Address,Address,Address,Address],ratioBps:number) -> Promise<Hash>` dùng ABI/bytecode Task 3. Bot không ký deploy thay ví người dùng trong luồng giao diện.

- [ ] **1. Test trước:** `wrong_chain_disables_writes`; `account_change_clears_previous_signer`; `hash_is_pending_not_paid`; `wallet_reject_and_revert_are_distinct`; `skip_is_local_choice_not_default_tx`; `late_receipt_rereads_contract`; `withdraw_does_not_mix_principal_and_interest`; `bigint_json_values_do_not_lose_precision`.
- [ ] **2. Chạy đỏ:** `npm.cmd run test:unit`; các test pure view-model/wallet fake provider fail đúng hành vi thiếu, không cần extension tự ký.
- [ ] **3. Implement:** React+viem injected EIP-1193, không giữ seed/key; tạo contract bằng user wallet sau gate/preflight vốn, validate ID+4 bot tạo năm địa chỉ khác nhau. USDC approve đúng amount cần rồi action riêng, không unlimited approval mặc định. Tạo/attach dây rõ ràng, không tự tạo lại khi refresh. Đọc public RPC qua backend, ví user chỉ ký; chain/accountChanged cập nhật và vô hiệu kết quả async cũ. Timeout không đồng nghĩa revert, replacement/cancel/reorg phải đọc receipt và snapshot mới; settlement chỉ cập nhật theo chain.
- [ ] **4. Giao diện:** thứ tự cấu hình → năm thành viên → trạng thái/deadline+hành động hợp lệ → ledger ETH/USDC/lãi → lịch sử tx. Có nút chạy bot bước hiện tại, Tiếp tục, bỏ góp và trả nợ; trước deadline bỏ góp vẫn được đổi ý. Không thêm landing page marketing/biểu đồ nghiên cứu. Dùng một font Manrope, typography/spacing theo skill landing-page-design, nền phẳng; bảng vốn từ chain, focus/label/error/loading/empty rõ; không animation làm chậm demo. Hiện “USDC testnet/ETH theo pool”, “không chứng minh an toàn vốn” và số ngày kinh tế tách khỏi giây onchain.
- [ ] **5. Chạy xanh:** `npm.cmd run test:unit`, `npm.cmd run typecheck`, `npm.cmd run build`; browser QA local trên desktop/hẹp và bàn phím, thử reject/pending/revert/RPC-off, sai chain, đổi account, thiếu gas/token/ETH. Không yêu cầu browser automation giữ hoặc nhập private key. Dùng ví testnet do người dùng tự ký cho giao dịch cần ví thật.
- [ ] **6. Commit:** `feat: add the interactive Sepolia ROSCA demo screen`.

## Task 8: Nghiệm thu local/fork, Sepolia và hướng dẫn chạy

**Files:** Create `scripts/deploy.ts`, `smoke.ts`, `demo/README.md`; Modify root `README.md`; Complete verification report và checklist plan.

**Interfaces:** `npm.cmd run check:route`, `check:reference`, `test:unit`, `test:contract`, `test:fork`, `typecheck`, `build`, `dev:web`, `dev:server`, `deploy:sepolia`, `smoke:sepolia`. Các scripts không đòi secret khi chỉ build/test offline; deploy/smoke có gửi tx phải dùng cờ `--broadcast` rõ ràng, chain guard11155111 và ví testnet đã được người dùng cấp quyền sử dụng. CLI deploy chỉ dùng bot demo được cấp riêng, không đòi private key ví người dùng; UI deploy vẫn do user ký.

- [ ] **1. Test trước:** `smoke_does_not_broadcast_by_default`; `deployment_rejects_mainnet_and_wrong_route`; `evidence_requires_success_receipt_and_balance_delta`; không nhận tx người khác hoặc screenshot làm bằng chứng swap của demo.
- [ ] **2. Chạy đỏ/xanh:** `npm.cmd run test:unit`, implement scripts sao cho mặc định read-only; deploy log công khai chain/address/hash, không in env. Receipt success ít nhất2 confirmations trong report nghiệm thu; UI một inclusion là “đã vào block”, có số confirmations riêng, không hứa finality tuyệt đối.
- [ ] **3. Kiểm toàn bộ offline:** từ demo chạy `npm.cmd ci`, `npm.cmd run test:unit`, `npm.cmd run test:contract`, `npm.cmd run check:reference`, `npm.cmd run typecheck`, `npm.cmd run build`; từ root chạy `.\.venv\Scripts\python.exe -m pytest -q`. Báo count thực tế, không kế thừa “242 passed” từ lượt cũ. Hash/mtime corpus và engine trước/sau phải không đổi; fork kiểm riêng, không tính skipped thành pass.
- [ ] **4. Chuẩn bị trước broadcast:** gate mới + đủ USDC/gas/ETH năm ví cho kịch bản; báo bảng số tiền cần theo số vòng và nghĩa vụ, không giả faucet tự cấp đủ. `.env.example` chỉ nêu tên `SEPOLIA_RPC_URL`, `BOT_PRIVATE_KEY_0..3`, địa chỉ route đã gate; điền secret ngoài chat/Git. Khóa preset, user xác nhận ví/network/contract params; chưa có quyền/cấu hình thì ghi blocked riêng phần testnet, tiếp tục bàn giao bằng chứng local có thật.
- [ ] **5. Nghiệm thu Sepolia:** một dây hoàn thành năm kỳ và một dây bot bỏ góp sau lĩnh. Thử người dùng đổi bid, hòa ID, chưa lĩnh bỏ góp; xác nhận default phải chờ300 giây thật. Thực hiện repay nontrigger và ít nhất một swap ETH→Circle USDC thật của contract, lấy block/hash, event và balance delta; không dùng fork/mock thay thế. Retry DEX lỗi và cú sập giá chỉ là kiểm local/ABM, không tác động pool công khai để dựng sự cố. Nếu route thất bại ngoài thực tế, giữ Settling và báo chưa đạt, không thay mock.
- [ ] **6. Hướng dẫn:** README Windows hai cửa sổ `cd demo` + `npm.cmd run dev:server`/`dev:web`, thiết lập môi trường, funding, tạo/attach, từng bước ký, chạy bot, chờ timeout, rút, lỗi RPC/swap và tiếp tục sau restart. Nêu rõ biến số thay trước tạo dây, giới hạn spot manipulation/no Sybil, khoản dư không có eligible nếu phát sinh, năm người không thừa hưởng ngưỡng185%. Chuẩn bị dây thật ở giữa kỳ trước giờ học được phép, phải giữ lịch sử hash và ghi rõ đã chuẩn bị.
- [ ] **7. Review và commit:** fresh whole-change reviewer kiểm quyền rút, math/rounding, route, deadline, replay, lộ secret và diff scope; xử lý lỗi quan trọng rồi chạy lại checks liên quan. Report tách rõ offline/fork/Sepolia đạt/chưa đạt, không ghi complete khi còn thiếu swap thật. `docs: verify and document the Sepolia ROSCA demo`; chỉ commit local, không push.

## Tự rà soát kế hoạch và cách thực hiện

- Spec §1–4: package độc lập/kiến trúc/phân quyền ở Tasks 1, 3, 6, 7; §5–6: lifecycle và số học ở Tasks 2–3; §7: route/fork ở Tasks 1, 4; §8: nợ/thanh lý/waterfall ở Tasks 4–5; §9: preset ở Task 6; §10–12: QA, bằng chứng và tài liệu ở Tasks 7–8.
- Một số tiền không được xem là đã thu do simulate thành công, có hash hoặc frontend đổi màu; mọi tầng sử dụng ABI và snapshot chung. Read-only gate không phải bằng chứng swap thành công.
- Đường găng: **1 → 2 → 3 → 4 → 5 → 6 → 7 → 8**. Không triển khai UI giao dịch dựa trên ABI dự đoán hoặc pool chưa gate. Chỉ làm phần tiếp theo khi task hiện tại đạt và đã commit.
- Đề xuất **Native**: thực hiện từng task ngay trong phiên này, commit cục bộ từng task, một reviewer độc lập cuối cùng. ABI và ledger phụ thuộc chặt nên đổi agent cho mỗi task tốn context mà ít tăng khả năng song song. Có thể chọn Subagent-driven nếu muốn review độc lập sau mỗi task; không bắt đầu trước khi người dùng duyệt plan và chọn cách thực hiện.

## Tài liệu kỹ thuật đã đối chiếu khi viết plan

- [Hardhat 3 setup và Node requirement](https://hardhat.org/docs/getting-started)
- [Hardhat viem + node:test](https://hardhat.org/docs/guides/testing/using-viem)
- [Vite setup](https://vite.dev/guide/)
- [viem simulateContract: simulation không bảo đảm giao dịch sau đó thành công](https://viem.sh/docs/contract/simulateContract)
- [Uniswap v2 Router02 implementation để kiểm giao diện exact-input/exact-output](https://github.com/Uniswap/v2-periphery/blob/master/contracts/UniswapV2Router02.sol)
- [OpenZeppelin utils, Math và ReentrancyGuard](https://docs.openzeppelin.com/contracts/5.x/api/utils)

Khi thực hiện Task 1 phải đối chiếu lại phiên bản package/compiler được cài và contract Sepolia tại block kiểm tra; plan không xác nhận trạng thái thanh khoản tương lai.

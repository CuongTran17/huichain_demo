import { useState } from "react";
import type { Address } from "viem";
import type { ClassroomSnapshot } from "./chain.js";
import { availableActions, claimPreview, FULL_WIRE_ALLOWANCE, GROSS_POT, MEMBER_COUNT, memberIndex, micro, type Action } from "./model.js";

type Props = { snapshot: ClassroomSnapshot; account?: Address; now: bigint; stale: boolean;
  tx?: { stage: string; message: string; hash?: `0x${string}` };
  run: (action: Action, options?: { bidBps?: number; memberId?: number }) => void;
  admit: (address: Address) => void; approveRepay: () => void; connect: () => void };
const eth = (wei: bigint) => (Number(wei) / 1e18).toLocaleString("vi-VN", { maximumFractionDigits: 8 });
const short = (address: string) => `${address.slice(0, 6)}…${address.slice(-4)}`;
const buttonLabels: Record<Action, string> = {
  request: "Xin tham gia dây", approve: "Cấp quyền đúng 600 USDC", start: "Bắt đầu dây hụi",
  advance: "Chuyển sang bước tiếp", contribute: "Góp 100 USDC kỳ này", bid: "Gửi mức lãi đã chọn",
  claim: "Lĩnh USDC và khóa ETH", repay: "Trả toàn bộ USDC còn nợ", liquidate: "Thanh lý ETH",
  finalize: "Chốt quyết toán", withdrawUsdc: "Rút USDC được nhận", withdrawEth: "Nhận lại ETH" };

export function Player({ snapshot, account, now, stale, tx, run, admit, approveRepay, connect }: Props) {
  const [bid, setBid] = useState(0);
  const id = memberIndex(snapshot, account);
  const member = id >= 0 ? snapshot.members[id] : undefined;
  const host = Boolean(account && account.toLowerCase() === snapshot.host.toLowerCase());
  const actions = stale ? [] : availableActions(snapshot, account, now);
  const pending = tx?.stage === "signing" || tx?.stage === "submitted";
  const candidate = snapshot.members[snapshot.state.currentCandidate];
  const { debt, interest, net } = claimPreview(snapshot.state.period, candidate?.annualBps ?? 0);
  const claimEth = snapshot.claimEth ?? 0n;
  const approx = snapshot.reserveWeth > 0n ? claimEth * snapshot.reserveUsdc / snapshot.reserveWeth : 0n;
  const repayNeedsApproval = member && actions.includes("repay") && snapshot.readiness[id].allowance < member.remainingDebt;
  const regular = actions.filter(action => action !== "liquidate" && !(action === "repay" && repayNeedsApproval));
  return <>
    <section className="hero">
      <div><p className="eyebrow">DÂY HỤI SÁU VÍ · TESTNET</p><h1>Mỗi chữ ký đều có <span>ý nghĩa rõ ràng.</span></h1>
        <p>Góp 100 USDC thử nghiệm mỗi kỳ. Người chưa lĩnh chào lãi, người thắng khóa ETH khi lĩnh. Nếu ai không góp trước hạn, host chuyển dây sang quyết toán.</p>
        <div className="hero-proof"><span>6 người chơi</span><span>6 kỳ góp</span><span>5 phút mỗi bước</span></div></div>
      <aside className="hero-panel"><small>ĐỊA CHỈ DÂY HỤI</small><code>{snapshot.wire}</code><a href={`https://sepolia.etherscan.io/address/${snapshot.wire}`} target="_blank" rel="noreferrer">Xem contract trên Etherscan ↗</a></aside>
    </section>
    <section className="player-grid">
      <article className="card action-card">
        <div className="section-heading"><span className="section-number">01</span><h2>Việc cần làm lúc này</h2></div>
        {!account && <><p>Hãy kết nối ví Sepolia để xem quyền và ký giao dịch của chính mình. Kết nối ví chưa cấp quyền USDC.</p><button className="primary" onClick={connect}>Kết nối ví Sepolia</button></>}
        {account && <><p className="account-line">{host ? "Host" : "Người chơi"} · {id >= 0 ? `ID ${id}` : "Chưa được duyệt"} · <code>{short(account)}</code></p>
          <p className="fine-print">Ngắt kết nối chỉ ẩn ví trên trang này; không thu hồi quyền USDC đã cấp cho contract.</p>
          {id < 0 && snapshot.state.phase === 0 && snapshot.applicants.some(a => a.toLowerCase() === account.toLowerCase()) && <p className="notice">Đã xin tham gia. Chờ host kiểm tra người trong lớp rồi duyệt ví này.</p>}
          {member && <p className="notice">Đã góp kỳ này: <strong>{member.contributedThisPeriod ? "Có" : "Chưa"}</strong>. Đã lĩnh: <strong>{member.received ? "Có" : "Chưa"}</strong>. USDC còn phải trả nếu dây dừng: <strong>{micro(member.remainingDebt)} USDC</strong>.</p>}
          {repayNeedsApproval && <><p>Cần cấp quyền đúng {micro(member!.remainingDebt)} USDC để contract thu khoản trả một lần. Cấp quyền không chuyển USDC.</p><button className="primary" disabled={pending || stale} onClick={approveRepay}>Cấp quyền trả {micro(member!.remainingDebt)} USDC</button></>}
          {member && actions.includes("repay") && snapshot.readiness[id].usdc < member.remainingDebt && <p className="notice error">Ví thiếu {micro(member.remainingDebt - snapshot.readiness[id].usdc)} USDC để trả hết nghĩa vụ. Nạp USDC testnet trước khi hết hạn; cấp quyền token không tự tạo USDC.</p>}
          {actions.includes("bid") && <label className="field">Lãi năm muốn chào <select value={bid} onChange={event => setBid(Number(event.target.value))}>{[0, 5, 10, 15, 20].map(rate => <option key={rate} value={rate * 100}>{rate}% một năm</option>)}</select></label>}
          {regular.length === 0 && !repayNeedsApproval && <div className="empty-state">Chưa có giao dịch cần ký. Theo dõi hạn và chờ người khác hoàn tất hoặc host chuyển bước.</div>}
          <div className="action-list">{regular.map(action => <div className="action-row" key={action}>
            <p>{action === "approve" ? "Ví cho phép contract thu tối đa 600 USDC về sau. Đây chưa phải góp tiền." :
              action === "contribute" ? "Contract chuyển đúng 100 USDC từ ví vào dây cho kỳ hiện tại." :
              action === "bid" ? "Mức lãi sẽ công khai trên chain. Chỉ khi thắng mới bị khấu trừ lãi lúc lĩnh." :
              action === "claim" ? "Ví gửi ETH ký quỹ cùng giao dịch. Contract giữ lãi từ khoản 600 USDC và chuyển phần ròng." :
              action === "advance" ? "Host ghi nhận các hành động đã xác nhận và mở bước tiếp theo. Khi quá hạn góp, dây sẽ dừng nếu thiếu người." :
              action === "finalize" ? "Host phân bổ số USDC thực có và ETH còn lại; không tự tạo thêm tiền." :
              action === "start" ? "Mở kỳ góp đầu tiên. Từ đây không thể đổi danh sách sáu ví." :
              action === "repay" ? "Trả USDC còn nợ để lấy lại ETH ký quỹ; chỉ trong thời gian cho phép." :
              action === "request" ? "Gửi địa chỉ ví để host xét duyệt. Chưa cần góp hoặc ký quỹ." : "Giao dịch sẽ cập nhật trạng thái của dây trên Sepolia."}</p>
            <button className="primary" disabled={pending || stale || (action === "repay" && Boolean(member && snapshot.readiness[id].usdc < member.remainingDebt))} onClick={() => run(action, action === "bid" ? { bidBps: bid } : undefined)}>{buttonLabels[action]}</button>
          </div>)}</div>
          {tx && <div className={`notice ${tx.stage === "failed" ? "error" : ""}`} role="status"><strong>{tx.stage === "signing" ? "Đang chờ chữ ký" : tx.stage === "submitted" ? "Chờ xác nhận" : tx.stage === "confirmed" ? "Đã xác nhận" : "Chưa hoàn tất"}</strong><p>{tx.message}</p>{tx.hash && <a href={`https://sepolia.etherscan.io/tx/${tx.hash}`} target="_blank" rel="noreferrer">Xem giao dịch ↗</a>}</div>}
          {stale && <p className="notice error">Dữ liệu vừa đọc lỗi. Các nút ký tạm khóa để tránh gửi theo thông tin cũ.</p>}
        </>}
      </article>
      <aside className="card briefing-card"><div className="section-heading"><span className="section-number">02</span><h2>Trước khi ký</h2></div>
        <dl><div><dt>USDC hiện trong contract</dt><dd>{micro(snapshot.usdcBalance)} USDC</dd></div><div><dt>ETH đang giữ</dt><dd>{eth(snapshot.ethBalance)} ETH</dd></div>
          {member && <><div><dt>USDC ví còn</dt><dd>{micro(snapshot.readiness[id].usdc)} USDC</dd></div><div><dt>Allowance còn</dt><dd>{micro(snapshot.readiness[id].allowance)} USDC</dd></div></>}</dl>
        <p className="fine-print">Allowance chỉ là quyền chi tối đa, không phải số USDC đã nộp. Nếu dây dừng sớm, có thể thu hồi quyền còn lại trong ví của bạn.</p>
      </aside>
    </section>
    {snapshot.state.phase === 3 && candidate && <section className="card claim-panel"><div className="section-heading"><span className="section-number">03</span><h2>Minh bạch khoản lĩnh</h2></div>
      <p>Ứng viên ID {snapshot.state.currentCandidate} chào {candidate.annualBps / 100}% một năm. Chỉ ứng viên được ký để lĩnh, trước hạn trên chain.</p>
      <div className="metric-grid"><div><small>Quỹ gộp</small><strong>{micro(GROSS_POT)} USDC</strong></div><div><small>Lãi giữ trong dây</small><strong>{micro(interest)} USDC</strong></div><div><small>Thực nhận</small><strong>{micro(net)} USDC</strong></div><div><small>Nghĩa vụ kỳ sau</small><strong>{micro(debt)} USDC</strong></div><div><small>ETH phải khóa 180%</small><strong>{eth(claimEth)} ETH</strong></div><div><small>Spot pool ước tính</small><strong>≈ {micro(approx)} USDC</strong></div></div>
      <p className="fine-print">Lãi chào được tính theo các kỳ quy ước 30 ngày, dù thời gian mỗi bước demo là 5 phút. Mức ký quỹ 180% là tham số minh họa, không bảo đảm an toàn gốc.</p>
      <p className="fine-print">Giá từ pool Uniswap trên Sepolia tại block {snapshot.blockNumber.toString()}, không phải giá ETH thật. Pool đổi trước khi giao dịch được xác nhận có thể làm claim bị revert; khi đó tải lại báo giá và thử ký lại.</p>
    </section>}
    {host && snapshot.state.phase === 0 && <section className="card"><div className="section-heading"><span className="section-number">H</span><h2>Host duyệt sáu ví</h2></div>
      <p>Kiểm tra người học ngoài ứng dụng trước khi duyệt. Một người có thể tạo nhiều ví; contract không biết đó là cùng một người.</p>
      <div className="applicant-list">{snapshot.applicants.length ? snapshot.applicants.map(applicant => <div key={applicant}><code>{applicant}</code><button disabled={pending || stale || snapshot.memberCount === MEMBER_COUNT} onClick={() => admit(applicant)}>Duyệt ví</button></div>) : <p>Chưa có yêu cầu chờ duyệt.</p>}</div>
      <h3>Kiểm tra trước khi bắt đầu</h3><ul className="checklist">{snapshot.members.filter(m => m.joined).map((m, i) => <li key={m.account}>ID {i} · {short(m.account)} · allowance {micro(snapshot.readiness[i].allowance)}/{micro(FULL_WIRE_ALLOWANCE)} USDC · ví còn {micro(snapshot.readiness[i].usdc)} USDC · gas {eth(snapshot.readiness[i].eth)} ETH</li>)}</ul>
      <p className="fine-print">Sáu người cần đủ 600 USDC trong cả dây. Người lĩnh sớm còn cần ETH ký quỹ. Checklist không khóa trước số dư.</p>
    </section>}
    {host && actions.includes("liquidate") && <section className="card"><h2>Quyết toán ETH ký quỹ</h2><p>Chỉ bán ETH của người có nợ đủ điều kiện theo contract. Giá Uniswap có thể đổi; giao dịch lỗi không làm mất ETH và có thể thử lại.</p>
      {snapshot.members.map((m, i) => m.received && m.remainingDebt > 0n && !m.liquidationProcessed && m.lockedEth > 0n &&
        ((snapshot.state.triggerMask & (1 << i)) !== 0 || now >= snapshot.state.deadline) ? <div className="liquidation-row" key={i}>ID {i} · còn nợ {micro(m.remainingDebt)} USDC · khóa {eth(m.lockedEth)} ETH <button disabled={pending || stale} onClick={() => run("liquidate", { memberId: i })}>Bán ETH theo quote mới</button></div> : null)}
    </section>}
    {snapshot.state.phase === 4 && <section className="notice"><strong>Dây đã dừng để quyết toán.</strong> Người đã lĩnh mà không gây bùng có tối đa 5 phút để trả USDC. Người bùng có thể bị thanh lý ETH ngay khi host ký. Chỉ số thiệt hại cuối cùng có sau khi chốt.</section>}
    <section className="card explainer"><h2>Cách chơi trong 3 bước</h2><div className="three-steps"><div><strong>1. Vào dây</strong><p>Xin tham gia, chờ host duyệt rồi cấp quyền đúng 600 USDC. Chưa chuyển tiền.</p></div><div><strong>2. Góp và chào</strong><p>Mỗi kỳ góp 100 USDC. Người chưa lĩnh chọn một trong năm mức lãi công khai.</p></div><div><strong>3. Lĩnh hoặc quyết toán</strong><p>Người thắng nhận phần ròng, khóa ETH cho các kỳ sau. Dây dừng nếu ai bỏ góp sau hạn.</p></div></div></section>
  </>;
}

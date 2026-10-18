// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IERC20Metadata} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {RoscaMath} from "./RoscaMath.sol";
import {UniswapV2Route, IV2Router} from "./UniswapV2Route.sol";

contract RoscaDemo is ReentrancyGuard {
    using SafeERC20 for IERC20;

    enum Phase { Joining, Contributing, Bidding, Claiming, Settling, Completed, Settled }
    enum FreezeReason { None, MissedContribution, NoEligible }
    enum LiquidationMode { ExactDebt, AllCollateral }

    uint256 public constant CONTRIBUTION = 100_000_000;
    uint256 public constant POT = 500_000_000;
    uint256 public constant WINDOW = 300;
    uint256 public constant GRACE = 300;
    uint8 private constant NO_CANDIDATE = 5;

    struct MemberView {
        address account;
        bool joined;
        bool contributedThisPeriod;
        bool received;
        bool bidSubmitted;
        uint16 annualBps;
        uint256 totalContributed;
        uint256 remainingDebt;
        uint256 lockedEth;
        uint256 winningInterest;
        uint8 payoutPeriod;
        uint256 claimableUsdc;
        uint256 claimableEth;
        uint256 repaidUsdc;
        uint256 recoveredUsdc;
        uint256 ethSold;
        bool liquidationProcessed;
        uint256 principalAllocated;
        uint256 interestAllocated;
    }
    struct StateView {
        Phase phase;
        uint8 period;
        uint256 deadline;
        uint8 currentCandidate;
        uint8 triggerMask;
        FreezeReason freezeReason;
        uint256 retainedInterest;
        uint256 usedInterest;
        uint256 distributedInterest;
        uint256 principalLoss;
        uint256 obligationUncollected;
        uint256 defaultInterestUsed;
        uint256 commonInterestUsed;
        uint256 unallocatedUsdc;
    }
    struct LiquidationQuote {
        LiquidationMode mode;
        uint256 ethIn;
        uint256 usdcOut;
        uint256 minOut;
        uint256 blockNumber;
    }

    IERC20 public immutable usdc;
    address public immutable pair;
    address public immutable router;
    address public immutable weth;
    uint32 public immutable collateralRatioBps;
    address[5] public members;
    MemberView[5] private records;
    StateView private state;
    uint8 private triedMask;
    uint8[5] private contributionsByPeriod;
    bool private claimedThisPeriod;
    bool public settlementFinalized;

    error InvalidAction();
    error InvalidMember();
    error WrongEth(uint256 expected);

    event Joined(uint8 indexed memberId);
    event PhaseChanged(Phase indexed phase, uint8 indexed period, uint256 deadline);
    event Contributed(uint8 indexed memberId, uint8 indexed period, uint256 amount);
    event BidSubmitted(uint8 indexed memberId, uint8 indexed period, uint16 annualBps);
    event PayoutClaimed(uint8 indexed memberId, uint8 indexed period, uint256 net, uint256 interest, uint256 ethLocked);
    event Frozen(uint8 indexed period, uint8 triggerMask, FreezeReason reason, uint256 graceDeadline);
    event DebtRepaid(uint8 indexed memberId, uint256 amount, uint256 remainingDebt);
    event CollateralSold(uint8 indexed memberId, uint256 ethSold, uint256 usdcRecovered, uint256 remainingDebt);
    event SettlementFinalized(Phase indexed phase, uint256 principalLoss, uint256 usedInterest, uint256 distributedInterest, uint256 unallocatedUsdc);
    event Withdrawn(uint8 indexed memberId, address indexed asset, uint256 amount);

    constructor(address[5] memory accounts, uint32 ratioBps, address token, address v2Pair, address v2Router) {
        if (ratioBps == 0 || ratioBps > 100000 || IERC20Metadata(token).decimals() != 6) revert InvalidAction();
        for (uint8 i; i < 5; ++i) {
            if (accounts[i] == address(0)) revert InvalidMember();
            for (uint8 j; j < i; ++j) if (accounts[i] == accounts[j]) revert InvalidMember();
            members[i] = accounts[i];
            records[i].account = accounts[i];
        }
        weth = UniswapV2Route.validate(token, v2Pair, v2Router);
        usdc = IERC20(token);
        pair = v2Pair;
        router = v2Router;
        collateralRatioBps = ratioBps;
        state.currentCandidate = NO_CANDIDATE;
    }

    function getState() external view returns (StateView memory) { return state; }
    function getMember(uint8 id) external view returns (MemberView memory) {
        if (id >= 5) revert InvalidMember();
        return records[id];
    }
    function memberId() external view returns (uint8) { return _memberId(msg.sender); }

    function _memberId(address account) private view returns (uint8) {
        for (uint8 i; i < 5; ++i) if (members[i] == account) return i;
        revert InvalidMember();
    }
    function _setPhase(Phase next) private {
        state.phase = next;
        state.deadline = block.timestamp + WINDOW;
        emit PhaseChanged(next, state.period, state.deadline);
    }

    function join() external {
        if (state.phase != Phase.Joining) revert InvalidAction();
        uint8 id = _memberId(msg.sender);
        if (records[id].joined) revert InvalidAction();
        records[id].joined = true;
        emit Joined(id);
    }

    function start() external {
        if (state.phase != Phase.Joining) revert InvalidAction();
        for (uint8 i; i < 5; ++i) if (!records[i].joined) revert InvalidAction();
        _setPhase(Phase.Contributing);
    }

    function contribute() external nonReentrant {
        if (state.phase != Phase.Contributing || block.timestamp >= state.deadline) revert InvalidAction();
        uint8 id = _memberId(msg.sender);
        MemberView storage member = records[id];
        if (member.contributedThisPeriod) revert InvalidAction();
        uint256 beforeBalance = usdc.balanceOf(address(this));
        usdc.safeTransferFrom(msg.sender, address(this), CONTRIBUTION);
        if (usdc.balanceOf(address(this)) - beforeBalance != CONTRIBUTION) revert InvalidAction();
        member.contributedThisPeriod = true;
        contributionsByPeriod[state.period] |= uint8(1 << id);
        member.totalContributed += CONTRIBUTION;
        if (member.received) member.remainingDebt -= CONTRIBUTION;
        emit Contributed(id, state.period, CONTRIBUTION);
    }

    function bid(uint16 annualBps) external {
        if (state.phase != Phase.Bidding || block.timestamp >= state.deadline || annualBps > 2000) revert InvalidAction();
        uint8 id = _memberId(msg.sender);
        MemberView storage member = records[id];
        if (member.received || member.bidSubmitted) revert InvalidAction();
        member.bidSubmitted = true;
        member.annualBps = annualBps;
        emit BidSubmitted(id, state.period, annualBps);
    }

    function _nextCandidate() private view returns (uint8 best) {
        best = NO_CANDIDATE;
        for (uint8 i; i < 5; ++i) {
            MemberView storage member = records[i];
            if (member.received || !member.bidSubmitted || triedMask & (1 << i) != 0) continue;
            if (best == NO_CANDIDATE || member.annualBps > records[best].annualBps) best = i;
        }
    }

    function _freeze(uint8 mask, FreezeReason reason) private {
        state.triggerMask = mask;
        state.freezeReason = reason;
        _setPhase(Phase.Settling);
        emit Frozen(state.period, mask, reason, state.deadline);
    }

    function advance() external {
        if (state.phase == Phase.Contributing) {
            uint8 missing;
            for (uint8 i; i < 5; ++i) if (!records[i].contributedThisPeriod) missing |= uint8(1 << i);
            if (missing != 0) {
                if (block.timestamp < state.deadline) revert InvalidAction();
                _freeze(missing, FreezeReason.MissedContribution);
            } else {
                _setPhase(Phase.Bidding);
            }
        } else if (state.phase == Phase.Bidding) {
            bool all = true;
            for (uint8 i; i < 5; ++i) if (!records[i].received && !records[i].bidSubmitted) all = false;
            if (!all && block.timestamp < state.deadline) revert InvalidAction();
            state.currentCandidate = _nextCandidate();
            if (state.currentCandidate == NO_CANDIDATE) _freeze(0, FreezeReason.NoEligible);
            else _setPhase(Phase.Claiming);
        } else if (state.phase == Phase.Claiming) {
            if (claimedThisPeriod) {
                if (state.period == 4) {
                    state.phase = Phase.Completed;
                    state.deadline = 0;
                    emit PhaseChanged(Phase.Completed, state.period, 0);
                } else {
                    state.period++;
                    triedMask = 0;
                    claimedThisPeriod = false;
                    state.currentCandidate = NO_CANDIDATE;
                    for (uint8 i; i < 5; ++i) {
                        records[i].contributedThisPeriod = false;
                        records[i].bidSubmitted = false;
                        records[i].annualBps = 0;
                    }
                    _setPhase(Phase.Contributing);
                }
            } else {
                if (block.timestamp < state.deadline) revert InvalidAction();
                triedMask |= uint8(1 << state.currentCandidate);
                state.currentCandidate = _nextCandidate();
                if (state.currentCandidate == NO_CANDIDATE) _freeze(0, FreezeReason.NoEligible);
                else _setPhase(Phase.Claiming);
            }
        } else revert InvalidAction();
    }

    function requiredCollateral() public view returns (uint256) {
        if (state.phase != Phase.Claiming || claimedThisPeriod || state.currentCandidate >= 5) revert InvalidAction();
        uint256 debt = uint256(4 - state.period) * CONTRIBUTION;
        (uint112 reserveUsdc, uint112 reserveWeth) = UniswapV2Route.reserves(address(usdc), pair);
        return RoscaMath.collateralWei(debt, collateralRatioBps, reserveUsdc, reserveWeth);
    }

    function claimPayout() external payable nonReentrant {
        if (state.phase != Phase.Claiming || claimedThisPeriod || block.timestamp >= state.deadline) revert InvalidAction();
        uint8 id = _memberId(msg.sender);
        if (id != state.currentCandidate) revert InvalidAction();
        uint256 needed = requiredCollateral();
        if (msg.value != needed) revert WrongEth(needed);
        uint256 debt = uint256(4 - state.period) * CONTRIBUTION;
        uint256 interest = RoscaMath.annualInterest(debt, records[id].annualBps, uint16((4 - state.period) * 30));
        uint256 net = POT - interest;
        claimedThisPeriod = true;
        records[id].received = true;
        records[id].payoutPeriod = state.period;
        records[id].remainingDebt = debt;
        records[id].lockedEth = needed;
        records[id].winningInterest = interest;
        state.retainedInterest += interest;
        usdc.safeTransfer(msg.sender, net);
        emit PayoutClaimed(id, state.period, net, interest, needed);
    }

    function repay(uint256 amount) external nonReentrant {
        if (state.phase != Phase.Settling || block.timestamp >= state.deadline || amount == 0) revert InvalidAction();
        uint8 id = _memberId(msg.sender);
        if (state.triggerMask & uint8(1 << id) != 0) revert InvalidAction();
        MemberView storage member = records[id];
        if (!member.received || member.liquidationProcessed || amount > member.remainingDebt || member.remainingDebt == 0) revert InvalidAction();
        uint256 beforeBalance = usdc.balanceOf(address(this));
        usdc.safeTransferFrom(msg.sender, address(this), amount);
        if (usdc.balanceOf(address(this)) - beforeBalance != amount) revert InvalidAction();
        member.remainingDebt -= amount;
        member.repaidUsdc += amount;
        if (member.remainingDebt == 0) {
            member.claimableEth += member.lockedEth;
            member.lockedEth = 0;
        }
        emit DebtRepaid(id, amount, member.remainingDebt);
    }

    function _path() private view returns (address[] memory path) {
        path = new address[](2);
        path[0] = weth;
        path[1] = address(usdc);
    }

    function previewLiquidation(uint8 id) public view returns (LiquidationQuote memory quote) {
        if (state.phase != Phase.Settling || id >= 5) revert InvalidAction();
        MemberView storage member = records[id];
        if (!member.received || member.liquidationProcessed || member.remainingDebt == 0 || member.lockedEth == 0) revert InvalidAction();
        if (state.triggerMask & uint8(1 << id) == 0 && block.timestamp < state.deadline) revert InvalidAction();
        address[] memory path = _path();
        (uint112 reserveUsdc,) = UniswapV2Route.reserves(address(usdc), pair);
        if (member.remainingDebt < reserveUsdc) {
            uint256[] memory exact = IV2Router(router).getAmountsIn(member.remainingDebt, path);
            if (exact.length != 2 || exact[1] != member.remainingDebt) revert InvalidAction();
            if (exact[0] <= member.lockedEth) {
                return LiquidationQuote(LiquidationMode.ExactDebt, exact[0], member.remainingDebt,
                    member.remainingDebt * 99 / 100, block.number);
            }
        }
        uint256[] memory all = IV2Router(router).getAmountsOut(member.lockedEth, path);
        if (all.length != 2 || all[1] == 0 || all[1] * 99 / 100 == 0 || all[1] > member.remainingDebt) revert InvalidAction();
        return LiquidationQuote(LiquidationMode.AllCollateral, member.lockedEth, all[1], all[1] * 99 / 100, block.number);
    }

    function liquidate(uint8 id, uint256 quoteBlock) external nonReentrant {
        if (quoteBlock == 0 || quoteBlock > block.number || block.number - quoteBlock > 3) revert InvalidAction();
        LiquidationQuote memory quote = previewLiquidation(id);
        MemberView storage member = records[id];
        uint256 usdcBefore = usdc.balanceOf(address(this));
        uint256 ethBefore = address(this).balance;
        address[] memory path = _path();
        if (quote.mode == LiquidationMode.ExactDebt) {
            IV2Router(router).swapETHForExactTokens{value: quote.ethIn}(quote.usdcOut, path, address(this), block.timestamp);
        } else {
            IV2Router(router).swapExactETHForTokens{value: quote.ethIn}(quote.minOut, path, address(this), block.timestamp);
        }
        uint256 recovered = usdc.balanceOf(address(this)) - usdcBefore;
        uint256 sold = ethBefore - address(this).balance;
        if (recovered == 0 || recovered > member.remainingDebt || sold == 0 || sold > member.lockedEth) revert InvalidAction();
        if (quote.mode == LiquidationMode.ExactDebt && recovered != quote.usdcOut) revert InvalidAction();
        if (quote.mode == LiquidationMode.AllCollateral && recovered < quote.minOut) revert InvalidAction();
        member.recoveredUsdc += recovered;
        member.ethSold += sold;
        member.lockedEth -= sold;
        member.remainingDebt -= recovered;
        member.liquidationProcessed = true;
        if (member.remainingDebt == 0) {
            member.claimableEth += member.lockedEth;
            member.lockedEth = 0;
        } else {
            if (member.lockedEth != 0) revert InvalidAction();
            state.obligationUncollected += member.remainingDebt;
        }
        emit CollateralSold(id, sold, recovered, member.remainingDebt);
    }

    function _interestWeights() private view returns (uint256[5] memory weights) {
        uint256[5] memory fallbackWeights;
        uint256 totalWait;
        for (uint8 i; i < 5; ++i) {
            if (state.triggerMask & uint8(1 << i) != 0) continue;
            uint8 cutoff = records[i].received ? records[i].payoutPeriod : state.period;
            for (uint8 period; period <= cutoff; ++period) {
                if (contributionsByPeriod[period] & uint8(1 << i) != 0) {
                    fallbackWeights[i] += CONTRIBUTION;
                    weights[i] += CONTRIBUTION * uint256(cutoff - period) * 30;
                }
            }
            totalWait += weights[i];
        }
        if (totalWait == 0) return fallbackWeights;
    }

    function finalizeSettlement() external nonReentrant {
        if (settlementFinalized || (state.phase != Phase.Settling && state.phase != Phase.Completed)) revert InvalidAction();
        for (uint8 i; i < 5; ++i) {
            if (records[i].received && records[i].remainingDebt > 0 && !records[i].liquidationProcessed) revert InvalidAction();
        }
        uint256 cash = usdc.balanceOf(address(this));
        uint256 principalTarget;
        uint256 defaultInterest;
        uint256[5] memory principalWeights;
        for (uint8 i; i < 5; ++i) {
            if (!records[i].received) {
                principalWeights[i] = records[i].totalContributed;
                principalTarget += principalWeights[i];
            }
            if (state.triggerMask & uint8(1 << i) != 0) defaultInterest += records[i].winningInterest;
        }
        uint256 principalPaid = cash < principalTarget ? cash : principalTarget;
        state.principalLoss = principalTarget - principalPaid;
        uint256 nonInterestCash = cash > state.retainedInterest ? cash - state.retainedInterest : 0;
        uint256 gapBeforeInterest = principalTarget > nonInterestCash ? principalTarget - nonInterestCash : 0;
        state.usedInterest = gapBeforeInterest < state.retainedInterest ? gapBeforeInterest : state.retainedInterest;
        state.defaultInterestUsed = state.usedInterest < defaultInterest ? state.usedInterest : defaultInterest;
        state.commonInterestUsed = state.usedInterest - state.defaultInterestUsed;
        uint256[5] memory principalShares = RoscaMath.allocate(principalPaid, principalWeights);
        uint256 surplus = cash - principalPaid;
        uint256[5] memory interestShares;
        uint256[5] memory weights = _interestWeights();
        uint256 eligibleWeight;
        for (uint8 i; i < 5; ++i) eligibleWeight += weights[i];
        if (eligibleWeight == 0) state.unallocatedUsdc = surplus;
        else {
            interestShares = RoscaMath.allocate(surplus, weights);
            state.distributedInterest = surplus;
        }
        uint256 allocated;
        for (uint8 i; i < 5; ++i) {
            MemberView storage member = records[i];
            member.principalAllocated = principalShares[i];
            member.interestAllocated = interestShares[i];
            member.claimableUsdc = principalShares[i] + interestShares[i];
            allocated += member.claimableUsdc;
            if (member.remainingDebt == 0) {
                member.claimableEth += member.lockedEth;
                member.lockedEth = 0;
            }
        }
        if (allocated + state.unallocatedUsdc != cash) revert InvalidAction();
        settlementFinalized = true;
        if (state.phase == Phase.Settling) state.phase = Phase.Settled;
        state.deadline = 0;
        emit SettlementFinalized(state.phase, state.principalLoss, state.usedInterest, state.distributedInterest, state.unallocatedUsdc);
    }

    function withdrawUsdc() external nonReentrant {
        if (!settlementFinalized) revert InvalidAction();
        uint8 id = _memberId(msg.sender);
        uint256 amount = records[id].claimableUsdc;
        if (amount == 0) revert InvalidAction();
        records[id].claimableUsdc = 0;
        usdc.safeTransfer(msg.sender, amount);
        emit Withdrawn(id, address(usdc), amount);
    }

    function withdrawEth() external nonReentrant {
        if (!settlementFinalized) revert InvalidAction();
        uint8 id = _memberId(msg.sender);
        uint256 amount = records[id].claimableEth;
        if (amount == 0) revert InvalidAction();
        records[id].claimableEth = 0;
        (bool ok,) = msg.sender.call{value: amount}("");
        if (!ok) revert InvalidAction();
        emit Withdrawn(id, address(0), amount);
    }

    receive() external payable {
        if (msg.sender != router) revert InvalidAction();
    }
}

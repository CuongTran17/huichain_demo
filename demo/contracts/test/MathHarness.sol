// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {RoscaMath} from "../RoscaMath.sol";

contract MathHarness {
    function annualInterest(uint256 obligation, uint16 annualBps, uint16 daysRemaining) external pure returns (uint256) {
        return RoscaMath.annualInterest(obligation, annualBps, daysRemaining);
    }

    function collateralWei(uint256 obligation, uint32 ratioBps, uint112 reserveUsdc, uint112 reserveWeth) external pure returns (uint256) {
        return RoscaMath.collateralWei(obligation, ratioBps, reserveUsdc, reserveWeth);
    }

    function allocate(uint256 total, uint256[5] calldata weights) external pure returns (uint256[5] memory) {
        return RoscaMath.allocate(total, weights);
    }
}

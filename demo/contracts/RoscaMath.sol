// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

library RoscaMath {
    error InvalidBid();
    error InvalidCollateral();
    error EmptyWeights();

    function annualInterest(uint256 obligation, uint16 annualBps, uint16 daysRemaining) internal pure returns (uint256) {
        if (annualBps > 2000 || daysRemaining > 150) revert InvalidBid();
        return Math.mulDiv(obligation, uint256(annualBps) * daysRemaining, 10000 * 365);
    }

    function collateralWei(uint256 obligation, uint32 ratioBps, uint112 reserveUsdc, uint112 reserveWeth)
        internal pure returns (uint256)
    {
        if (ratioBps == 0 || ratioBps > 100000 || reserveUsdc == 0 || reserveWeth == 0) revert InvalidCollateral();
        return Math.mulDiv(obligation, uint256(ratioBps) * reserveWeth, uint256(10000) * reserveUsdc, Math.Rounding.Ceil);
    }

    function allocate(uint256 total, uint256[5] memory weights) internal pure returns (uint256[5] memory shares) {
        uint256 sum;
        for (uint256 i; i < 5; ++i) sum += weights[i];
        if (sum == 0) {
            if (total != 0) revert EmptyWeights();
            return shares;
        }
        uint256 allocated;
        uint256[5] memory remainders;
        for (uint256 i; i < 5; ++i) {
            shares[i] = Math.mulDiv(total, weights[i], sum);
            remainders[i] = mulmod(total, weights[i], sum);
            allocated += shares[i];
        }
        for (uint256 extra = total - allocated; extra > 0; --extra) {
            uint256 best = 5;
            for (uint256 i; i < 5; ++i) {
                if (weights[i] > 0 && (best == 5 || remainders[i] > remainders[best])) best = i;
            }
            shares[best]++;
            remainders[best] = 0;
        }
    }

    function allocate(uint256 total, uint256[6] memory weights) internal pure returns (uint256[6] memory shares) {
        uint256 sum;
        for (uint256 i; i < 6; ++i) sum += weights[i];
        if (sum == 0) {
            if (total != 0) revert EmptyWeights();
            return shares;
        }
        uint256 allocated;
        uint256[6] memory remainders;
        for (uint256 i; i < 6; ++i) {
            shares[i] = Math.mulDiv(total, weights[i], sum);
            remainders[i] = mulmod(total, weights[i], sum);
            allocated += shares[i];
        }
        for (uint256 extra = total - allocated; extra > 0; --extra) {
            uint256 best = 6;
            for (uint256 i; i < 6; ++i) {
                if (weights[i] > 0 && (best == 6 || remainders[i] > remainders[best])) best = i;
            }
            shares[best]++;
            remainders[best] = 0;
        }
    }
}

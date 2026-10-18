// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract TestV2 {
    address public immutable token0;
    address public immutable token1;
    address public immutable WETH;
    uint112 public reserve0 = 2_000_000_000;
    uint112 public reserve1 = 1 ether;
    bool public fail;

    constructor(address usdc) {
        token0 = usdc;
        token1 = address(this);
        WETH = address(this);
    }
    function factory() external view returns (address) { return address(this); }
    function getPair(address a, address b) external view returns (address) {
        return (a == token0 && b == token1) || (a == token1 && b == token0) ? address(this) : address(0);
    }
    function getReserves() external view returns (uint112, uint112, uint32) { return (reserve0, reserve1, 0); }
    function setReserves(uint112 usdc, uint112 weth) external { reserve0 = usdc; reserve1 = weth; }
    function setFail(bool value) external { fail = value; }

    function getAmountsIn(uint256 amountOut, address[] calldata path) public view returns (uint256[] memory amounts) {
        require(path.length == 2 && path[0] == address(this) && path[1] == token0 && amountOut < reserve0);
        amounts = new uint256[](2);
        amounts[0] = uint256(reserve1) * amountOut * 1000 / ((uint256(reserve0) - amountOut) * 997) + 1;
        amounts[1] = amountOut;
    }

    function getAmountsOut(uint256 amountIn, address[] calldata path) public view returns (uint256[] memory amounts) {
        require(path.length == 2 && path[0] == address(this) && path[1] == token0);
        amounts = new uint256[](2);
        amounts[0] = amountIn;
        amounts[1] = amountIn * 997 * reserve0 / (uint256(reserve1) * 1000 + amountIn * 997);
    }

    function swapETHForExactTokens(uint256 amountOut, address[] calldata path, address to, uint256 deadline)
        external payable returns (uint256[] memory amounts)
    {
        require(!fail && block.timestamp <= deadline);
        amounts = getAmountsIn(amountOut, path);
        require(msg.value >= amounts[0]);
        reserve1 += uint112(amounts[0]);
        reserve0 -= uint112(amountOut);
        require(IERC20(token0).transfer(to, amountOut));
        if (msg.value > amounts[0]) {
            (bool ok,) = msg.sender.call{value: msg.value - amounts[0]}("");
            require(ok);
        }
    }

    function swapExactETHForTokens(uint256 amountOutMin, address[] calldata path, address to, uint256 deadline)
        external payable returns (uint256[] memory amounts)
    {
        require(!fail && block.timestamp <= deadline);
        amounts = getAmountsOut(msg.value, path);
        require(amounts[1] >= amountOutMin);
        reserve1 += uint112(msg.value);
        reserve0 -= uint112(amounts[1]);
        require(IERC20(token0).transfer(to, amounts[1]));
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

interface IV2Pair {
    function token0() external view returns (address);
    function token1() external view returns (address);
    function factory() external view returns (address);
    function getReserves() external view returns (uint112, uint112, uint32);
}

interface IV2Factory {
    function getPair(address, address) external view returns (address);
}

interface IV2Router {
    function factory() external view returns (address);
    function WETH() external view returns (address);
    function getAmountsIn(uint256, address[] calldata) external view returns (uint256[] memory);
    function getAmountsOut(uint256, address[] calldata) external view returns (uint256[] memory);
    function swapETHForExactTokens(uint256, address[] calldata, address, uint256) external payable returns (uint256[] memory);
    function swapExactETHForTokens(uint256, address[] calldata, address, uint256) external payable returns (uint256[] memory);
}

library UniswapV2Route {
    error InvalidRoute();

    function validate(address usdc, address pair, address router) internal view returns (address weth) {
        if (usdc == address(0) || pair == address(0) || router == address(0)
            || usdc.code.length == 0 || pair.code.length == 0 || router.code.length == 0) revert InvalidRoute();
        weth = IV2Router(router).WETH();
        address factory = IV2Router(router).factory();
        if (weth == address(0) || factory == address(0) || factory.code.length == 0
            || IV2Pair(pair).factory() != factory || IV2Factory(factory).getPair(usdc, weth) != pair) revert InvalidRoute();
        if (!((IV2Pair(pair).token0() == usdc && IV2Pair(pair).token1() == weth)
            || (IV2Pair(pair).token1() == usdc && IV2Pair(pair).token0() == weth))) revert InvalidRoute();
    }

    function reserves(address usdc, address pair) internal view returns (uint112 reserveUsdc, uint112 reserveWeth) {
        (uint112 reserve0, uint112 reserve1,) = IV2Pair(pair).getReserves();
        if (IV2Pair(pair).token0() == usdc) return (reserve0, reserve1);
        return (reserve1, reserve0);
    }
}

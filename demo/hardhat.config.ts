import hardhatToolboxViem from "@nomicfoundation/hardhat-toolbox-viem";
import { defineConfig } from "hardhat/config";

export default defineConfig({
  plugins: [hardhatToolboxViem],
  paths: { sources: "./contracts", tests: { nodejs: "./test/contract" } },
  solidity: { version: "0.8.28", settings: { optimizer: { enabled: true, runs: 200 } } },
});

import { resolve } from "node:path";
import { setMockCacheDir } from "@nomicfoundation/hardhat-utils/global-dir";

// Keep compiler downloads inside this workspace on restricted Windows hosts.
setMockCacheDir(resolve(".runtime/hardhat-global-cache"));

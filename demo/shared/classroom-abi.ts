// Generated from solc 0.8.28 RoscaClassroom artifact. Run npm run export:abi.
export const classroomAbi = [
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "host_",
        "type": "address"
      },
      {
        "internalType": "address",
        "name": "token",
        "type": "address"
      },
      {
        "internalType": "address",
        "name": "v2Pair",
        "type": "address"
      },
      {
        "internalType": "address",
        "name": "v2Router",
        "type": "address"
      }
    ],
    "stateMutability": "nonpayable",
    "type": "constructor"
  },
  {
    "inputs": [],
    "name": "EmptyWeights",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "InvalidAction",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "InvalidBid",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "InvalidCollateral",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "InvalidMember",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "InvalidRoute",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "ReentrancyGuardReentrantCall",
    "type": "error"
  },
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "token",
        "type": "address"
      }
    ],
    "name": "SafeERC20FailedOperation",
    "type": "error"
  },
  {
    "inputs": [
      {
        "internalType": "uint256",
        "name": "expected",
        "type": "uint256"
      }
    ],
    "name": "WrongEth",
    "type": "error"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "memberId",
        "type": "uint8"
      },
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "period",
        "type": "uint8"
      },
      {
        "indexed": false,
        "internalType": "uint16",
        "name": "annualBps",
        "type": "uint16"
      }
    ],
    "name": "BidSubmitted",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "memberId",
        "type": "uint8"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "ethSold",
        "type": "uint256"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "usdcRecovered",
        "type": "uint256"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "remainingDebt",
        "type": "uint256"
      }
    ],
    "name": "CollateralSold",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "memberId",
        "type": "uint8"
      },
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "period",
        "type": "uint8"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "amount",
        "type": "uint256"
      }
    ],
    "name": "Contributed",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "memberId",
        "type": "uint8"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "amount",
        "type": "uint256"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "remainingDebt",
        "type": "uint256"
      }
    ],
    "name": "DebtRepaid",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "period",
        "type": "uint8"
      },
      {
        "indexed": false,
        "internalType": "uint8",
        "name": "triggerMask",
        "type": "uint8"
      },
      {
        "indexed": false,
        "internalType": "enum RoscaClassroom.FreezeReason",
        "name": "reason",
        "type": "uint8"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "graceDeadline",
        "type": "uint256"
      }
    ],
    "name": "Frozen",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "address",
        "name": "account",
        "type": "address"
      }
    ],
    "name": "JoinRequested",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "memberId",
        "type": "uint8"
      },
      {
        "indexed": true,
        "internalType": "address",
        "name": "account",
        "type": "address"
      }
    ],
    "name": "Joined",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "memberId",
        "type": "uint8"
      },
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "period",
        "type": "uint8"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "net",
        "type": "uint256"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "interest",
        "type": "uint256"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "ethLocked",
        "type": "uint256"
      }
    ],
    "name": "PayoutClaimed",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "enum RoscaClassroom.Phase",
        "name": "phase",
        "type": "uint8"
      },
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "period",
        "type": "uint8"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "deadline",
        "type": "uint256"
      }
    ],
    "name": "PhaseChanged",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "enum RoscaClassroom.Phase",
        "name": "phase",
        "type": "uint8"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "principalLoss",
        "type": "uint256"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "usedInterest",
        "type": "uint256"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "distributedInterest",
        "type": "uint256"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "unallocatedUsdc",
        "type": "uint256"
      }
    ],
    "name": "SettlementFinalized",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "uint8",
        "name": "memberId",
        "type": "uint8"
      },
      {
        "indexed": true,
        "internalType": "address",
        "name": "asset",
        "type": "address"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "amount",
        "type": "uint256"
      }
    ],
    "name": "Withdrawn",
    "type": "event"
  },
  {
    "inputs": [],
    "name": "CONTRIBUTION",
    "outputs": [
      {
        "internalType": "uint256",
        "name": "",
        "type": "uint256"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "GRACE",
    "outputs": [
      {
        "internalType": "uint256",
        "name": "",
        "type": "uint256"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "POT",
    "outputs": [
      {
        "internalType": "uint256",
        "name": "",
        "type": "uint256"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "WINDOW",
    "outputs": [
      {
        "internalType": "uint256",
        "name": "",
        "type": "uint256"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "advance",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "account",
        "type": "address"
      }
    ],
    "name": "approveJoin",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "uint16",
        "name": "annualBps",
        "type": "uint16"
      }
    ],
    "name": "bid",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "claimPayout",
    "outputs": [],
    "stateMutability": "payable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "collateralRatioBps",
    "outputs": [
      {
        "internalType": "uint32",
        "name": "",
        "type": "uint32"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "contribute",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "finalizeSettlement",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "uint8",
        "name": "id",
        "type": "uint8"
      }
    ],
    "name": "getMember",
    "outputs": [
      {
        "components": [
          {
            "internalType": "address",
            "name": "account",
            "type": "address"
          },
          {
            "internalType": "bool",
            "name": "joined",
            "type": "bool"
          },
          {
            "internalType": "bool",
            "name": "contributedThisPeriod",
            "type": "bool"
          },
          {
            "internalType": "bool",
            "name": "received",
            "type": "bool"
          },
          {
            "internalType": "bool",
            "name": "bidSubmitted",
            "type": "bool"
          },
          {
            "internalType": "uint16",
            "name": "annualBps",
            "type": "uint16"
          },
          {
            "internalType": "uint256",
            "name": "totalContributed",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "remainingDebt",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "lockedEth",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "winningInterest",
            "type": "uint256"
          },
          {
            "internalType": "uint8",
            "name": "payoutPeriod",
            "type": "uint8"
          },
          {
            "internalType": "uint256",
            "name": "claimableUsdc",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "claimableEth",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "repaidUsdc",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "recoveredUsdc",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "ethSold",
            "type": "uint256"
          },
          {
            "internalType": "bool",
            "name": "liquidationProcessed",
            "type": "bool"
          },
          {
            "internalType": "uint256",
            "name": "principalAllocated",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "interestAllocated",
            "type": "uint256"
          }
        ],
        "internalType": "struct RoscaClassroom.MemberView",
        "name": "",
        "type": "tuple"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "getState",
    "outputs": [
      {
        "components": [
          {
            "internalType": "enum RoscaClassroom.Phase",
            "name": "phase",
            "type": "uint8"
          },
          {
            "internalType": "uint8",
            "name": "period",
            "type": "uint8"
          },
          {
            "internalType": "uint256",
            "name": "deadline",
            "type": "uint256"
          },
          {
            "internalType": "uint8",
            "name": "currentCandidate",
            "type": "uint8"
          },
          {
            "internalType": "uint8",
            "name": "triggerMask",
            "type": "uint8"
          },
          {
            "internalType": "enum RoscaClassroom.FreezeReason",
            "name": "freezeReason",
            "type": "uint8"
          },
          {
            "internalType": "uint256",
            "name": "retainedInterest",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "usedInterest",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "distributedInterest",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "principalLoss",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "obligationUncollected",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "defaultInterestUsed",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "commonInterestUsed",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "unallocatedUsdc",
            "type": "uint256"
          }
        ],
        "internalType": "struct RoscaClassroom.StateView",
        "name": "",
        "type": "tuple"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "host",
    "outputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "uint8",
        "name": "id",
        "type": "uint8"
      },
      {
        "internalType": "uint256",
        "name": "quoteBlock",
        "type": "uint256"
      }
    ],
    "name": "liquidate",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "memberCount",
    "outputs": [
      {
        "internalType": "uint8",
        "name": "",
        "type": "uint8"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "memberId",
    "outputs": [
      {
        "internalType": "uint8",
        "name": "",
        "type": "uint8"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      }
    ],
    "name": "memberIdPlusOne",
    "outputs": [
      {
        "internalType": "uint8",
        "name": "",
        "type": "uint8"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "uint256",
        "name": "",
        "type": "uint256"
      }
    ],
    "name": "members",
    "outputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "pair",
    "outputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "uint8",
        "name": "id",
        "type": "uint8"
      }
    ],
    "name": "previewLiquidation",
    "outputs": [
      {
        "components": [
          {
            "internalType": "enum RoscaClassroom.LiquidationMode",
            "name": "mode",
            "type": "uint8"
          },
          {
            "internalType": "uint256",
            "name": "ethIn",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "usdcOut",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "minOut",
            "type": "uint256"
          },
          {
            "internalType": "uint256",
            "name": "blockNumber",
            "type": "uint256"
          }
        ],
        "internalType": "struct RoscaClassroom.LiquidationQuote",
        "name": "quote",
        "type": "tuple"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "uint256",
        "name": "amount",
        "type": "uint256"
      }
    ],
    "name": "repay",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "requestJoin",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      }
    ],
    "name": "requested",
    "outputs": [
      {
        "internalType": "bool",
        "name": "",
        "type": "bool"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "requiredCollateral",
    "outputs": [
      {
        "internalType": "uint256",
        "name": "",
        "type": "uint256"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "router",
    "outputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "settlementFinalized",
    "outputs": [
      {
        "internalType": "bool",
        "name": "",
        "type": "bool"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "start",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "usdc",
    "outputs": [
      {
        "internalType": "contract IERC20",
        "name": "",
        "type": "address"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "weth",
    "outputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "withdrawEth",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "withdrawUsdc",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "stateMutability": "payable",
    "type": "receive"
  }
] as const;
export const classroomBytecode = "0x610140604052348015610010575f5ffd5b50604051614a4d380380614a4d83398101604081905261002f916105fe565b60017f9b779b17422d0df92223018b32b4d1fa46e071723d6817e2486d003becc55f00556001600160a01b03841615806100cc5750826001600160a01b031663313ce5676040518163ffffffff1660e01b8152600401602060405180830381865afa1580156100a0573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906100c4919061064f565b60ff16600614155b156100ea57604051634a7f394f60e01b815260040160405180910390fd5b6001600160a01b0384166101205261010383838361013b565b6001600160a01b0390811660e05292831660805290821660a0521660c05250614650610100526050805460ff1916600517905561068f565b5f6001600160a01b038416158061015957506001600160a01b038316155b8061016b57506001600160a01b038216155b8061017e57506001600160a01b0384163b155b8061019157506001600160a01b0383163b155b806101a457506001600160a01b0382163b155b156101c25760405163427282e960e11b815260040160405180910390fd5b816001600160a01b031663ad5c46486040518163ffffffff1660e01b8152600401602060405180830381865afa1580156101fe573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906102229190610676565b90505f826001600160a01b031663c45a01556040518163ffffffff1660e01b8152600401602060405180830381865afa158015610261573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906102859190610676565b90506001600160a01b03821615806102a457506001600160a01b038116155b806102b757506001600160a01b0381163b155b806103335750806001600160a01b0316846001600160a01b031663c45a01556040518163ffffffff1660e01b8152600401602060405180830381865afa158015610303573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906103279190610676565b6001600160a01b031614155b806103ba575060405163e6a4390560e01b81526001600160a01b0386811660048301528381166024830152808616919083169063e6a4390590604401602060405180830381865afa15801561038a573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906103ae9190610676565b6001600160a01b031614155b156103d85760405163427282e960e11b815260040160405180910390fd5b846001600160a01b0316846001600160a01b0316630dfe16816040518163ffffffff1660e01b8152600401602060405180830381865afa15801561041e573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906104429190610676565b6001600160a01b03161480156104c85750816001600160a01b0316846001600160a01b031663d21220a76040518163ffffffff1660e01b8152600401602060405180830381865afa158015610499573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906104bd9190610676565b6001600160a01b0316145b806105be5750846001600160a01b0316846001600160a01b031663d21220a76040518163ffffffff1660e01b8152600401602060405180830381865afa158015610514573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906105389190610676565b6001600160a01b03161480156105be5750816001600160a01b0316846001600160a01b0316630dfe16816040518163ffffffff1660e01b8152600401602060405180830381865afa15801561058f573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906105b39190610676565b6001600160a01b0316145b6105db5760405163427282e960e11b815260040160405180910390fd5b509392505050565b80516001600160a01b03811681146105f9575f5ffd5b919050565b5f5f5f5f60808587031215610611575f5ffd5b61061a856105e3565b9350610628602086016105e3565b9250610636604086016105e3565b9150610644606086016105e3565b905092959194509250565b5f6020828403121561065f575f5ffd5b815160ff8116811461066f575f5ffd5b9392505050565b5f60208284031215610686575f5ffd5b61066f826105e3565b60805160a05160c05160e05161010051610120516142ac6107a15f395f8181610603015281816107e701528181610f2301528181611869015281816121c10152612a5d01525f8181610404015261218801525f8181610387015261342001525f81816101ee01528181610636015281816110870152818161112b01528181611c4b0152611dbf01525f81816104c201528181611bf1015261215a01525f818161033c0152818161095d01528181610ff5015281816111ea015281816115ae0152818161162e0152818161167701528181611bd001528181612139015281816124f301528181612573015281816125c4015281816129be01528181612f2a01528181612f5b015261347301526142ac5ff3fe6080604052600436106101de575f3560e01c8063963b20c5116100fd578063cb8d8bc911610092578063eecf0b4f11610062578063eecf0b4f146105c4578063f437bc59146105f2578063f887ea4014610625578063fee84d4e14610658575f5ffd5b8063cb8d8bc914610568578063d7bb99ba14610594578063e88499a9146105a8578063ea105ac7146105b0575f5ffd5b8063b53105a3116100cd578063b53105a3146104e4578063b5f61c96146104f8578063be9a655514610526578063c6eedef91461053a575f5ffd5b8063963b20c514610471578063a0ef91df1461049d578063a53e541214610276578063a8aa1b31146104b1575f5ffd5b80633e413bee11610173578063564f113911610143578063564f1139146103d4578063593855a0146103f35780635daf08ca1461043b57806376ee20e51461045a575f5ffd5b80633e413bee1461032b5780633fc8cef31461037657806341e4ba92146103a957806348bb9069146103bd575f5ffd5b80631bb3399d116101ae5780631bb3399d146102ba578063263c4647146102ce578063338e4764146102ed578063371fd8e61461030c575f5ffd5b806310c1181d1461023257806311aee3801461025d578063137d29d9146102765780631865c57d14610299575f5ffd5b3661022e57336001600160a01b037f0000000000000000000000000000000000000000000000000000000000000000161461022c57604051634a7f394f60e01b815260040160405180910390fd5b005b5f5ffd5b34801561023d575f5ffd5b5061024661066c565b60405160ff90911681526020015b60405180910390f35b348015610268575f5ffd5b506005546102469060ff1681565b348015610281575f5ffd5b5061028b61012c81565b604051908152602001610254565b3480156102a4575f5ffd5b506102ad61067b565b6040516102549190613bc0565b3480156102c5575f5ffd5b5061022c6107dc565b3480156102d9575f5ffd5b5061022c6102e8366004613c91565b610dd3565b3480156102f8575f5ffd5b5061022c610307366004613cc7565b610f18565b348015610317575f5ffd5b5061022c610326366004613cef565b61148a565b348015610336575f5ffd5b5061035e7f000000000000000000000000000000000000000000000000000000000000000081565b6040516001600160a01b039091168152602001610254565b348015610381575f5ffd5b5061035e7f000000000000000000000000000000000000000000000000000000000000000081565b3480156103b4575f5ffd5b5061022c6117ce565b3480156103c8575f5ffd5b5061028b631dcd650081565b3480156103df575f5ffd5b5061022c6103ee366004613d1a565b61185e565b3480156103fe575f5ffd5b506104267f000000000000000000000000000000000000000000000000000000000000000081565b60405163ffffffff9091168152602001610254565b348015610446575f5ffd5b5061035e610455366004613cef565b611a75565b348015610465575f5ffd5b5061028b6305f5e10081565b34801561047c575f5ffd5b5061049061048b366004613d35565b611a93565b6040516102549190613d4e565b3480156104a8575f5ffd5b5061022c611f48565b3480156104bc575f5ffd5b5061035e7f000000000000000000000000000000000000000000000000000000000000000081565b3480156104ef575f5ffd5b5061028b6120ab565b348015610503575f5ffd5b50610246610512366004613d1a565b60066020525f908152604090205460ff1681565b348015610531575f5ffd5b5061022c6121b6565b348015610545575f5ffd5b50605b5461055890610100900460ff1681565b6040519015158152602001610254565b348015610573575f5ffd5b50610587610582366004613d35565b612251565b6040516102549190613d97565b34801561059f575f5ffd5b5061022c61243a565b61022c612752565b3480156105bb575f5ffd5b5061022c612a52565b3480156105cf575f5ffd5b506105586105de366004613d1a565b60076020525f908152604090205460ff1681565b3480156105fd575f5ffd5b5061035e7f000000000000000000000000000000000000000000000000000000000000000081565b348015610630575f5ffd5b5061035e7f000000000000000000000000000000000000000000000000000000000000000081565b348015610663575f5ffd5b5061022c612e89565b5f61067633612fd8565b905090565b6106e7604080516101c08101909152805f81525f6020820181905260408201819052606082018190526080820181905260a09091019081526020015f81526020015f81526020015f81526020015f81526020015f81526020015f81526020015f81526020015f81525090565b604080516101c08101909152604e8054829060ff16600681111561070d5761070d613b88565b600681111561071e5761071e613b88565b8152815460ff61010091829004811660208401526001840154604084015260028085015480831660608601529283048216608085015260a09093019262010000909204169081111561077257610772613b88565b600281111561078357610783613b88565b815260200160038201548152602001600482015481526020016005820154815260200160068201548152602001600782015481526020016008820154815260200160098201548152602001600a82015481525050905090565b336001600160a01b037f0000000000000000000000000000000000000000000000000000000000000000161461082557604051634a7f394f60e01b815260040160405180910390fd5b61082d613025565b605b54610100900460ff168061087c57506004604e5460ff16600681111561085757610857613b88565b1415801561087c57506005604e5460ff16600681111561087957610879613b88565b14155b1561089a57604051634a7f394f60e01b815260040160405180910390fd5b5f5b60058160ff1610156109455760088160ff16600581106108be576108be613ec2565b600e020154600160b01b900460ff1680156108f557505f60088260ff16600581106108eb576108eb613ec2565b600e020160020154115b801561091f575060088160ff166005811061091257610912613ec2565b600e0201600b015460ff16155b1561093d57604051634a7f394f60e01b815260040160405180910390fd5b60010161089c565b506040516370a0823160e01b81523060048201525f907f00000000000000000000000000000000000000000000000000000000000000006001600160a01b0316906370a0823190602401602060405180830381865afa1580156109aa573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906109ce9190613ed6565b90505f5f6109da613b6a565b5f5b60058160ff161015610ac15760088160ff16600581106109fe576109fe613ec2565b600e020154600160b01b900460ff16610a705760088160ff1660058110610a2757610a27613ec2565b600e020160010154828260ff1660058110610a4457610a44613ec2565b60200201528160ff821660058110610a5e57610a5e613ec2565b6020020151610a6d9085613f01565b93505b6050546101009004600160ff8084169190911b919091161615610ab95760088160ff1660058110610aa357610aa3613ec2565b600e02016004015483610ab69190613f01565b92505b6001016109dc565b505f838510610ad05783610ad2565b845b9050610ade8185613f14565b6054556051545f908611610af2575f610aff565b605154610aff9087613f14565b90505f818611610b0f575f610b19565b610b198287613f14565b6051549091508110610b2d57605154610b2f565b805b60528190558511610b405784610b44565b6052545b6056819055605254610b569190613f14565b6057555f610b648486613040565b90505f610b71858a613f14565b9050610b7b613b6a565b5f610b84613248565b90505f5f5b60058160ff161015610bc357828160ff1660058110610baa57610baa613ec2565b6020020151610bb99083613f01565b9150600101610b89565b50805f03610bd5576058849055610be7565b610bdf8483613040565b605385905592505b5f5f5b60058160ff161015610cd9575f60088260ff1660058110610c0d57610c0d613ec2565b600e02019050878260ff1660058110610c2857610c28613ec2565b6020020151600c8201558560ff831660058110610c4757610c47613ec2565b6020020151600d8201558560ff831660058110610c6657610c66613ec2565b6020020151888360ff1660058110610c8057610c80613ec2565b6020020151610c8f9190613f01565b60068201819055610ca09084613f01565b925080600201545f03610cd0578060030154816007015f828254610cc49190613f01565b90915550505f60038201555b50600101610bea565b506058548d90610ce99083613f01565b14610d0757604051634a7f394f60e01b815260040160405180910390fd5b605b805461ff0019166101001790556004604e5460ff166006811115610d2f57610d2f613b88565b03610d4257604e805460ff191660061790555b5f604f55604e5460ff166006811115610d5d57610d5d613b88565b6054546052546053546058546040805194855260208501939093529183015260608201527fa399b1f34f546272f499efed4e1bffde8a29e5a3d5d592fe0c4127b513c837a99060800160405180910390a250505050505050505050505050610dd160015f5160206142575f395f51905f5255565b565b6002604e5460ff166006811115610dec57610dec613b88565b141580610dfb5750604f544210155b80610e0b57506107d08161ffff16115b80610e245750610e1d6101f482613f3b565b61ffff1615155b15610e4257604051634a7f394f60e01b815260040160405180910390fd5b5f610e4c33612fd8565b90505f60088260ff1660058110610e6557610e65613ec2565b600e02018054909150600160b01b900460ff1680610e8b57508054600160b81b900460ff165b15610ea957604051634a7f394f60e01b815260040160405180910390fd5b805461ffff8416600160c01b810262ffffff60b81b1990921691909117600160b81b178255604e54604051918252610100900460ff90811691908416907fb57e1e8ab1981b6dea49df38a5dbcb4324f53baed281cbebb1e98d4f4ee110e49060200160405180910390a3505050565b336001600160a01b037f00000000000000000000000000000000000000000000000000000000000000001614610f6157604051634a7f394f60e01b815260040160405180910390fd5b610f69613025565b801580610f7557504381115b80610f8957506003610f878243613f14565b115b15610fa757604051634a7f394f60e01b815260040160405180910390fd5b5f610fb183611a93565b90505f60088460ff1660058110610fca57610fca613ec2565b6040516370a0823160e01b8152306004820152600e919091029190910191505f906001600160a01b037f000000000000000000000000000000000000000000000000000000000000000016906370a0823190602401602060405180830381865afa15801561103a573d5f5f3e3d5ffd5b505050506040513d601f19601f8201168201806040525081019061105e9190613ed6565b9050475f61106a6133fe565b90505f8551600181111561108057611080613b88565b03611129577f00000000000000000000000000000000000000000000000000000000000000006001600160a01b031663fb3bdb41866020015187604001518430426040518663ffffffff1660e01b81526004016110e09493929190613fa1565b5f6040518083038185885af11580156110fb573d5f5f3e3d5ffd5b50505050506040513d5f823e601f3d908101601f191682016040526111239190810190613fe9565b506111c9565b7f00000000000000000000000000000000000000000000000000000000000000006001600160a01b0316637ff36ab5866020015187606001518430426040518663ffffffff1660e01b81526004016111849493929190613fa1565b5f6040518083038185885af115801561119f573d5f5f3e3d5ffd5b50505050506040513d5f823e601f3d908101601f191682016040526111c79190810190613fe9565b505b6040516370a0823160e01b81523060048201525f9084906001600160a01b037f000000000000000000000000000000000000000000000000000000000000000016906370a0823190602401602060405180830381865afa15801561122f573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906112539190613ed6565b61125d9190613f14565b90505f61126a4785613f14565b905081158061127c5750856002015482115b80611285575080155b806112935750856003015481115b156112b157604051634a7f394f60e01b815260040160405180910390fd5b5f875160018111156112c5576112c5613b88565b1480156112d6575086604001518214155b156112f457604051634a7f394f60e01b815260040160405180910390fd5b60018751600181111561130957611309613b88565b1480156113195750866060015182105b1561133757604051634a7f394f60e01b815260040160405180910390fd5b81866009015f82825461134a9190613f01565b925050819055508086600a015f8282546113649190613f01565b9250508190555080866003015f82825461137e9190613f14565b9250508190555081866002015f8282546113989190613f14565b9091555050600b8601805460ff1916600117905560028601545f036113de578560030154866007015f8282546113ce9190613f01565b90915550505f600387015561141d565b60038601541561140157604051634a7f394f60e01b815260040160405180910390fd5b6002860154605580545f90611417908490613f01565b90915550505b600286015460408051838152602081018590529081019190915260ff8a16907f3e2cc859ab67a79c03eee178c46a50f01fb89dd2f831478993d6c7795a758fe09060600160405180910390a25050505050505061148660015f5160206142575f395f51905f5255565b5050565b611492613025565b6004604e5460ff1660068111156114ab576114ab613b88565b1415806114ba5750604f544210155b806114c3575080155b156114e157604051634a7f394f60e01b815260040160405180910390fd5b5f6114eb33612fd8565b6050549091506101009004600160ff8084169190911b91909116161561152457604051634a7f394f60e01b815260040160405180910390fd5b5f60088260ff166005811061153b5761153b613ec2565b600e02018054909150600160b01b900460ff16158061155e5750600b81015460ff165b8061156c5750806002015483115b8061157957506002810154155b1561159757604051634a7f394f60e01b815260040160405180910390fd5b6040516370a0823160e01b81523060048201525f907f00000000000000000000000000000000000000000000000000000000000000006001600160a01b0316906370a0823190602401602060405180830381865afa1580156115fb573d5f5f3e3d5ffd5b505050506040513d601f19601f8201168201806040525081019061161f9190613ed6565b90506116566001600160a01b037f0000000000000000000000000000000000000000000000000000000000000000163330876134c8565b6040516370a0823160e01b8152306004820152849082906001600160a01b037f000000000000000000000000000000000000000000000000000000000000000016906370a0823190602401602060405180830381865afa1580156116bc573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906116e09190613ed6565b6116ea9190613f14565b1461170857604051634a7f394f60e01b815260040160405180910390fd5b83826002015f82825461171b9190613f14565b9250508190555083826008015f8282546117359190613f01565b909155505060028201545f03611768578160030154826007015f82825461175c9190613f01565b90915550505f60038301555b8260ff167f2f6de894cb32d1182b447ca05637275d90f1953e59c614ff588986cdeca71afe8584600201546040516117aa929190918252602082015260400190565b60405180910390a25050506117cb60015f5160206142575f395f51905f5255565b50565b5f604e5460ff1660068111156117e6576117e6613b88565b1461180457604051634a7f394f60e01b815260040160405180910390fd5b335f9081526007602052604090205460ff161561181d57565b335f81815260076020526040808220805460ff19166001179055517fc34568d64d2d2906cfd932c48ac91e167a570161c0c7799209864b2a46643d799190a2565b336001600160a01b037f000000000000000000000000000000000000000000000000000000000000000016146118a757604051634a7f394f60e01b815260040160405180910390fd5b5f604e5460ff1660068111156118bf576118bf613b88565b1415806118e457506001600160a01b0381165f9081526007602052604090205460ff16155b806118f357506005805460ff16145b8061191757506001600160a01b0381165f9081526006602052604090205460ff1615155b1561193557604051634a7f394f60e01b815260040160405180910390fd5b600580545f9160ff909116908261194b836140b1565b91906101000a81548160ff021916908360ff1602179055509050815f8260ff166005811061197b5761197b613ec2565b0180546001600160a01b0319166001600160a01b03929092169190911790556119a58160016140cf565b6001600160a01b0383165f908152600660205260409020805460ff191660ff92831617905582906008908316600581106119e1576119e1613ec2565b600e020180546001600160a01b0319166001600160a01b03929092169190911790556001600860ff831660058110611a1b57611a1b613ec2565b600e02018054911515600160a01b0260ff60a01b199092169190911790556040516001600160a01b0383169060ff8316907f84763ac1415131f6e10651f9405882f963549a19a8447ea08974a77564cecdc0905f90a35050565b5f8160058110611a83575f80fd5b01546001600160a01b0316905081565b611ac16040805160a08101909152805f81526020015f81526020015f81526020015f81526020015f81525090565b6004604e5460ff166006811115611ada57611ada613b88565b141580611aeb575060058260ff1610155b15611b0957604051634a7f394f60e01b815260040160405180910390fd5b5f60088360ff1660058110611b2057611b20613ec2565b600e02018054909150600160b01b900460ff161580611b435750600b81015460ff165b80611b5057506002810154155b80611b5d57506003810154155b15611b7b57604051634a7f394f60e01b815260040160405180910390fd5b6050546101009004600160ff8086169190911b9190911616158015611ba15750604f5442105b15611bbf57604051634a7f394f60e01b815260040160405180910390fd5b5f611bc86133fe565b90505f611c157f00000000000000000000000000000000000000000000000000000000000000007f0000000000000000000000000000000000000000000000000000000000000000613504565b509050806001600160701b031683600201541015611da15760028301546040516307c0329d60e21b81525f916001600160a01b037f00000000000000000000000000000000000000000000000000000000000000001691631f00ca7491611c809187906004016140e8565b5f60405180830381865afa158015611c9a573d5f5f3e3d5ffd5b505050506040513d5f823e601f3d908101601f19168201604052611cc19190810190613fe9565b905080516002141580611cf25750836002015481600181518110611ce757611ce7613ec2565b602002602001015114155b15611d1057604051634a7f394f60e01b815260040160405180910390fd5b8360030154815f81518110611d2757611d27613ec2565b602002602001015111611d9f576040805160a08101909152805f8152602001825f81518110611d5857611d58613ec2565b6020026020010151815260200185600201548152602001606486600201546063611d829190614100565b611d8c9190614117565b8152436020909101529695505050505050565b505b600383015460405163d06ca61f60e01b81525f916001600160a01b037f0000000000000000000000000000000000000000000000000000000000000000169163d06ca61f91611df49187906004016140e8565b5f60405180830381865afa158015611e0e573d5f5f3e3d5ffd5b505050506040513d5f823e601f3d908101601f19168201604052611e359190810190613fe9565b905080516002141580611e61575080600181518110611e5657611e56613ec2565b60200260200101515f145b80611e9c5750606481600181518110611e7c57611e7c613ec2565b60200260200101516063611e909190614100565b611e9a9190614117565b155b80611ec45750836002015481600181518110611eba57611eba613ec2565b6020026020010151115b15611ee257604051634a7f394f60e01b815260040160405180910390fd5b6040805160a0810190915280600181526020018560030154815260200182600181518110611f1257611f12613ec2565b60200260200101518152602001606483600181518110611f3457611f34613ec2565b60200260200101516063611d829190614100565b611f50613025565b605b54610100900460ff16611f7857604051634a7f394f60e01b815260040160405180910390fd5b5f611f8233612fd8565b90505f60088260ff1660058110611f9b57611f9b613ec2565b600e0201600701549050805f03611fc557604051634a7f394f60e01b815260040160405180910390fd5b5f60088360ff1660058110611fdc57611fdc613ec2565b600e0201600701819055505f336001600160a01b0316826040515f6040518083038185875af1925050503d805f8114612030576040519150601f19603f3d011682016040523d82523d5f602084013e612035565b606091505b505090508061205757604051634a7f394f60e01b815260040160405180910390fd5b6040518281525f9060ff8516907f3a2db7d2315c2162d4f47c295f514b5aacf84592e024bc529868af8d776567f7906020015b60405180910390a3505050610dd160015f5160206142575f395f51905f5255565b5f6003604e5460ff1660068111156120c5576120c5613b88565b1415806120d45750605b5460ff165b806120e75750605054600560ff90911610155b1561210557604051634a7f394f60e01b815260040160405180910390fd5b604e545f906305f5e1009061212390610100900460ff16600461412a565b60ff166121309190614100565b90505f5f61217e7f00000000000000000000000000000000000000000000000000000000000000007f0000000000000000000000000000000000000000000000000000000000000000613504565b915091506121ae837f000000000000000000000000000000000000000000000000000000000000000084846135fb565b935050505090565b336001600160a01b037f000000000000000000000000000000000000000000000000000000000000000016146121ff57604051634a7f394f60e01b815260040160405180910390fd5b5f604e5460ff16600681111561221757612217613b88565b14158061222957506005805460ff1614155b1561224757604051634a7f394f60e01b815260040160405180910390fd5b610dd1600161369b565b6122ed6040518061026001604052805f6001600160a01b031681526020015f151581526020015f151581526020015f151581526020015f151581526020015f61ffff1681526020015f81526020015f81526020015f81526020015f81526020015f60ff1681526020015f81526020015f81526020015f81526020015f81526020015f81526020015f151581526020015f81526020015f81525090565b60058260ff1610612311576040516339ec64c160e11b815260040160405180910390fd5b60088260ff166005811061232757612327613ec2565b6040805161026081018252600e929092029290920180546001600160a01b038116835260ff600160a01b8204811615156020850152600160a81b82048116151594840194909452600160b01b8104841615156060840152600160b81b810484161515608084015261ffff600160c01b9091041660a0830152600181015460c0830152600281015460e083015260038101546101008301526004810154610120830152600581015483166101408301526006810154610160830152600781015461018083015260088101546101a083015260098101546101c0830152600a8101546101e0830152600b8101549092161515610200820152600c820154610220820152600d9091015461024082015292915050565b612442613025565b6001604e5460ff16600681111561245b5761245b613b88565b14158061246a5750604f544210155b1561248857604051634a7f394f60e01b815260040160405180910390fd5b5f61249233612fd8565b90505f60088260ff16600581106124ab576124ab613ec2565b600e02018054909150600160a81b900460ff16156124dc57604051634a7f394f60e01b815260040160405180910390fd5b6040516370a0823160e01b81523060048201525f907f00000000000000000000000000000000000000000000000000000000000000006001600160a01b0316906370a0823190602401602060405180830381865afa158015612540573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906125649190613ed6565b905061259f6001600160a01b037f00000000000000000000000000000000000000000000000000000000000000001633306305f5e1006134c8565b6040516370a0823160e01b81523060048201526305f5e1009082906001600160a01b037f000000000000000000000000000000000000000000000000000000000000000016906370a0823190602401602060405180830381865afa158015612609573d5f5f3e3d5ffd5b505050506040513d601f19601f8201168201806040525081019061262d9190613ed6565b6126379190613f14565b1461265557604051634a7f394f60e01b815260040160405180910390fd5b815460ff60a81b1916600160a81b178255604e54600160ff8581169190911b91605a91610100909104166005811061268f5761268f613ec2565b602091828204019190068282829054906101000a900460ff161792506101000a81548160ff021916908360ff1602179055506305f5e100826001015f8282546126d89190613f01565b90915550508154600160b01b900460ff161561270b576305f5e100826002015f8282546127059190613f14565b90915550505b604e5460405160ff6101009092048216918516907f02aad16e2984cd63e27113690a41179e72a51b7f9734934e6d7a8c2ef84857e99061208a906305f5e100815260200190565b61275a613025565b6003604e5460ff16600681111561277357612773613b88565b1415806127825750605b5460ff165b8061278f5750604f544210155b156127ad57604051634a7f394f60e01b815260040160405180910390fd5b5f6127b733612fd8565b60505490915060ff8083169116146127e257604051634a7f394f60e01b815260040160405180910390fd5b5f6127eb6120ab565b905080341461281557604051630545861160e41b8152600481018290526024015b60405180910390fd5b604e545f906305f5e1009061283390610100900460ff16600461412a565b60ff166128409190614100565b90505f6128988260088660ff166005811061285d5761285d613ec2565b600e020154604e54600160c01b90910461ffff169061288590610100900460ff16600461412a565b61289090601e614143565b60ff16613724565b90505f6128a982631dcd6500613f14565b605b805460ff19166001908117909155909150600860ff8716600581106128d2576128d2613ec2565b600e02018054911515600160b01b0260ff60b01b19909216919091179055604e54610100900460ff9081169060089087166005811061291357612913613ec2565b600e02016005015f6101000a81548160ff021916908360ff1602179055508260088660ff166005811061294857612948613ec2565b600e0201600201819055508360088660ff166005811061296a5761296a613ec2565b600e0201600301819055508160088660ff166005811061298c5761298c613ec2565b600e02016004018190555081604e6003015f8282546129ab9190613f01565b909155506129e590506001600160a01b037f0000000000000000000000000000000000000000000000000000000000000000163383613781565b604e54604080518381526020810185905290810186905260ff6101009092048216918716907f945b97df29c0fa964d5ca1a6a6b4018801741d85e98c678abfdc35210f9d42449060600160405180910390a35050505050610dd160015f5160206142575f395f51905f5255565b336001600160a01b037f00000000000000000000000000000000000000000000000000000000000000001614612a9b57604051634a7f394f60e01b815260040160405180910390fd5b6001604e5460ff166006811115612ab457612ab4613b88565b03612b48575f5f5b60058160ff161015612b065760088160ff1660058110612ade57612ade613ec2565b600e020154600160a81b900460ff16612afe578060ff166001901b821791505b600101612abc565b5060ff811615612b3e57604f54421015612b3357604051634a7f394f60e01b815260040160405180910390fd5b6117cb8160016137bb565b6117cb600261369b565b6002604e5460ff166006811115612b6157612b61613b88565b03612c415760015f5b60058160ff161015612bdb5760088160ff1660058110612b8c57612b8c613ec2565b600e020154600160b01b900460ff16158015612bca575060088160ff1660058110612bb957612bb9613ec2565b600e020154600160b81b900460ff16155b15612bd3575f91505b600101612b6a565b5080158015612beb5750604f5442105b15612c0957604051634a7f394f60e01b815260040160405180910390fd5b612c11613857565b6050805460ff191660ff92909216918217905560041901612c37576117cb5f60026137bb565b6117cb600361369b565b6003604e5460ff166006811115612c5a57612c5a613b88565b03612e7057605b5460ff1615612df157604e54610100900460ff16600403612cd657604e80546005919060ff191660018302179055505f604f55604e54610100900460ff1660056040515f81527fb070f30564c7f6b4417cbad108e44deef775fbe1f133668303bd71b13497ac4a9060200160405180910390a3565b604e8054610100900460ff16906001612cee836140b1565b825460ff9182166101009390930a9283029190920219909116179055506059805460ff19908116909155605b8054821690556050805490911660051790555f5b60058160ff161015612de6575f60088260ff1660058110612d5157612d51613ec2565b600e02018054911515600160a81b0260ff60a81b199092169190911790555f600860ff831660058110612d8657612d86613ec2565b600e02018054911515600160b81b0260ff60b81b199092169190911790555f600860ff831660058110612dbb57612dbb613ec2565b600e0201805461ffff92909216600160c01b0261ffff60c01b19909216919091179055600101612d2e565b50610dd1600161369b565b604f54421015612e1457604051634a7f394f60e01b815260040160405180910390fd5b60505460598054600160ff9384161b83169281169290921760ff19909216919091179055612e40613857565b6050805460ff191660ff92909216918217905560041901612e6657610dd15f60026137bb565b610dd1600361369b565b604051634a7f394f60e01b815260040160405180910390fd5b612e91613025565b605b54610100900460ff16612eb957604051634a7f394f60e01b815260040160405180910390fd5b5f612ec333612fd8565b90505f60088260ff1660058110612edc57612edc613ec2565b600e0201600601549050805f03612f0657604051634a7f394f60e01b815260040160405180910390fd5b5f60088360ff1660058110612f1d57612f1d613ec2565b600e020160060155612f597f00000000000000000000000000000000000000000000000000000000000000006001600160a01b03163383613781565b7f00000000000000000000000000000000000000000000000000000000000000006001600160a01b03168260ff167f3a2db7d2315c2162d4f47c295f514b5aacf84592e024bc529868af8d776567f783604051612fb891815260200190565b60405180910390a35050610dd160015f5160206142575f395f51905f5255565b6001600160a01b0381165f9081526006602052604081205460ff16808203613013576040516339ec64c160e11b815260040160405180910390fd5b61301e60018261412a565b9392505050565b61302d613921565b60025f5160206142575f395f51905f5255565b613048613b6a565b5f5f5b600581101561307f5783816005811061306657613066613ec2565b60200201516130759083613f01565b915060010161304b565b50805f036130ac5783156130a657604051630f38e67160e01b815260040160405180910390fd5b50613242565b5f6130b5613b6a565b5f5b6005811015613161576130e1878783600581106130d6576130d6613ec2565b602002015186613950565b8582600581106130f3576130f3613ec2565b6020020152838061310657613106613f27565b86826005811061311857613118613ec2565b6020020151880982826005811061313157613131613ec2565b602002015284816005811061314857613148613ec2565b60200201516131579084613f01565b92506001016130b7565b505f61316d8388613f14565b90505b801561323d5760055f5b60058110156131ee575f88826005811061319657613196613ec2565b60200201511180156131dd575081600514806131dd57508382600581106131bf576131bf613ec2565b60200201518482600581106131d6576131d6613ec2565b6020020151115b156131e6578091505b60010161317a565b5085816005811061320157613201613ec2565b6020020180519061321182614166565b9052505f83826005811061322757613227613ec2565b6020020152506132368161417e565b9050613170565b505050505b92915050565b613250613b6a565b613258613b6a565b5f5f5b60058160ff1610156133eb576050546101009004600160ff8084169190911b91909116165f036133e3575f60088260ff166005811061329c5761329c613ec2565b600e020154600160b01b900460ff166132bf57604e54610100900460ff166132e1565b60088260ff16600581106132d5576132d5613ec2565b600e02016005015460ff165b90505f5b8160ff168160ff16116133ba578260ff166001901b605a8260ff166005811061331057613310613ec2565b6020810490910154601f9091166101000a90041660ff16156133aa576305f5e100858460ff166005811061334657613346613ec2565b602002018181516133579190613f01565b905250613364818361412a565b6133759060ff166305f5e100614100565b61338090601e614100565b868460ff166005811061339557613395613ec2565b602002018181516133a69190613f01565b9052505b6133b3816140b1565b90506132e5565b50848260ff16600581106133d0576133d0613ec2565b60200201516133df9084613f01565b9250505b60010161325b565b50805f036133f95750919050565b505090565b60408051600280825260608083018452926020830190803683370190505090507f0000000000000000000000000000000000000000000000000000000000000000815f8151811061345157613451613ec2565b60200260200101906001600160a01b031690816001600160a01b0316815250507f0000000000000000000000000000000000000000000000000000000000000000816001815181106134a5576134a5613ec2565b60200260200101906001600160a01b031690816001600160a01b03168152505090565b6134d6848484846001613a00565b6134fe57604051635274afe760e01b81526001600160a01b038516600482015260240161280c565b50505050565b5f5f5f5f846001600160a01b0316630902f1ac6040518163ffffffff1660e01b8152600401606060405180830381865afa158015613544573d5f5f3e3d5ffd5b505050506040513d601f19601f8201168201806040525081019061356891906141a9565b5091509150856001600160a01b0316856001600160a01b0316630dfe16816040518163ffffffff1660e01b8152600401602060405180830381865afa1580156135b3573d5f5f3e3d5ffd5b505050506040513d601f19601f820116820180604052508101906135d791906141f5565b6001600160a01b0316036135ef5790925090506135f4565b925090505b9250929050565b5f63ffffffff841615806136175750620186a08463ffffffff16115b8061362957506001600160701b038316155b8061363b57506001600160701b038216155b15613659576040516368f7a67560e11b815260040160405180910390fd5b613692856136766001600160701b03851663ffffffff8816614100565b61368b6001600160701b038716612710614100565b6001613a6d565b95945050505050565b604e805482919060ff191660018360068111156136ba576136ba613b88565b02179055506136cb61012c42613f01565b604f55604e54610100900460ff168160068111156136eb576136eb613b88565b604f546040519081527fb070f30564c7f6b4417cbad108e44deef775fbe1f133668303bd71b13497ac4a9060200160405180910390a350565b5f6107d08361ffff16118061373d575060788261ffff16115b1561375b5760405163c6388ef760e01b815260040160405180910390fd5b6137798461377061ffff808616908716614100565b6237b1d0613950565b949350505050565b61378e8383836001613aaf565b6137b657604051635274afe760e01b81526001600160a01b038416600482015260240161280c565b505050565b6050805461ff0019811661010060ff861602908117835583929162ffff00191662ff00001990911617620100008360028111156137fa576137fa613b88565b0217905550613809600461369b565b604e54604f5460405161010090920460ff16917fef678c79d32a34e75107cf7fc42180241694672d13661dc81270d63f90ff86f79161384b9186918691614210565b60405180910390a25050565b60055f5b60058160ff16101561391d575f60088260ff166005811061387e5761387e613ec2565b600e02018054909150600160b01b900460ff16806138a557508054600160b81b900460ff16155b806138c05750605954600160ff8481169190911b9091161615155b156138cb5750613915565b60ff83166005148061390a575060088360ff16600581106138ee576138ee613ec2565b600e020154815461ffff600160c01b9283900481169290910416115b15613913578192505b505b60010161385b565b5090565b5f5160206142575f395f51905f5254600203610dd157604051633ee5aeb560e01b815260040160405180910390fd5b5f5f5f61395d8686613b11565b91509150815f036139815783818161397757613977613f27565b049250505061301e565b818411613998576139986003851502601118613b2d565b5f848688095f868103871696879004966002600389028118808a02820302808a02820302808a02820302808a02820302808a02820302808a02909103029181900381900460010185841190960395909502919093039390930492909217029150509392505050565b6040516323b872dd60e01b5f8181526001600160a01b038781166004528616602452604485905291602083606481808c5af1925060015f51148316613a5c578383151615613a50573d5f823e3d81fd5b5f883b113d1516831692505b604052505f60605295945050505050565b5f613a9a613a7a83613b3e565b8015613a9557505f8480613a9057613a90613f27565b868809115b151590565b613aa5868686613950565b6136929190613f01565b60405163a9059cbb60e01b5f8181526001600160a01b038616600452602485905291602083604481808b5af1925060015f51148316613b05578383151615613af9573d5f823e3d81fd5b5f873b113d1516831692505b60405250949350505050565b5f805f1983850993909202808410938190039390930393915050565b634e487b715f52806020526024601cfd5b5f6002826003811115613b5357613b53613b88565b613b5d9190614235565b60ff166001149050919050565b6040518060a001604052806005906020820280368337509192915050565b634e487b7160e01b5f52602160045260245ffd5b60078110613bac57613bac613b88565b9052565b60038110613bac57613bac613b88565b5f6101c082019050613bd3828451613b9c565b6020830151613be7602084018260ff169052565b50604083015160408301526060830151613c06606084018260ff169052565b506080830151613c1b608084018260ff169052565b5060a0830151613c2e60a0840182613bb0565b5060c083015160c083015260e083015160e08301526101008301516101008301526101208301516101208301526101408301516101408301526101608301516101608301526101808301516101808301526101a08301516101a083015292915050565b5f60208284031215613ca1575f5ffd5b813561ffff8116811461301e575f5ffd5b803560ff81168114613cc2575f5ffd5b919050565b5f5f60408385031215613cd8575f5ffd5b613ce183613cb2565b946020939093013593505050565b5f60208284031215613cff575f5ffd5b5035919050565b6001600160a01b03811681146117cb575f5ffd5b5f60208284031215613d2a575f5ffd5b813561301e81613d06565b5f60208284031215613d45575f5ffd5b61301e82613cb2565b815160a082019060028110613d6557613d65613b88565b808352506020830151602083015260408301516040830152606083015160608301526080830151608083015292915050565b81516001600160a01b0316815261026081016020830151613dbc602084018215159052565b506040830151613dd0604084018215159052565b506060830151613de4606084018215159052565b506080830151613df8608084018215159052565b5060a0830151613e0e60a084018261ffff169052565b5060c083015160c083015260e083015160e0830152610100830151610100830152610120830151610120830152610140830151613e5161014084018260ff169052565b506101608301516101608301526101808301516101808301526101a08301516101a08301526101c08301516101c08301526101e08301516101e0830152610200830151613ea361020084018215159052565b5061022083015161022083015261024083015161024083015292915050565b634e487b7160e01b5f52603260045260245ffd5b5f60208284031215613ee6575f5ffd5b5051919050565b634e487b7160e01b5f52601160045260245ffd5b8082018082111561324257613242613eed565b8181038181111561324257613242613eed565b634e487b7160e01b5f52601260045260245ffd5b5f61ffff831680613f4e57613f4e613f27565b8061ffff84160691505092915050565b5f8151808452602084019350602083015f5b82811015613f975781516001600160a01b0316865260209586019590910190600101613f70565b5093949350505050565b848152608060208201525f613fb96080830186613f5e565b6001600160a01b03949094166040830152506060015292915050565b634e487b7160e01b5f52604160045260245ffd5b5f60208284031215613ff9575f5ffd5b815167ffffffffffffffff81111561400f575f5ffd5b8201601f8101841361401f575f5ffd5b805167ffffffffffffffff81111561403957614039613fd5565b8060051b604051601f19603f830116810181811067ffffffffffffffff8211171561406657614066613fd5565b604052918252602081840181019290810187841115614083575f5ffd5b6020850194505b838510156140a65784518082526020958601959093500161408a565b509695505050505050565b5f60ff821660ff81036140c6576140c6613eed565b60010192915050565b60ff818116838216019081111561324257613242613eed565b828152604060208201525f6137796040830184613f5e565b808202811582820484141761324257613242613eed565b5f8261412557614125613f27565b500490565b60ff828116828216039081111561324257613242613eed565b60ff818116838216029081169081811461415f5761415f613eed565b5092915050565b5f6001820161417757614177613eed565b5060010190565b5f8161418c5761418c613eed565b505f190190565b80516001600160701b0381168114613cc2575f5ffd5b5f5f5f606084860312156141bb575f5ffd5b6141c484614193565b92506141d260208501614193565b9150604084015163ffffffff811681146141ea575f5ffd5b809150509250925092565b5f60208284031215614205575f5ffd5b815161301e81613d06565b60ff84168152606081016142276020830185613bb0565b826040830152949350505050565b5f60ff83168061424757614247613f27565b8060ff8416069150509291505056fe9b779b17422d0df92223018b32b4d1fa46e071723d6817e2486d003becc55f00a26469706673582212203a78e3f5e031bc90e3b214cc0a8ec589ab9a173a018c2640e1c4529e52ede8fd64736f6c634300081c0033" as const;

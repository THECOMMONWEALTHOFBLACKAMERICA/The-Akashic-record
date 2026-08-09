# T.A.R. Governance Model

`TARGovernance.sol` is an approval registry for protocol/control-plane decisions. It does **not** perform arbitrary external calls. A proposal commits to an `actionHash`; after voting and the timelock, `execute` marks that hash approved. Any downstream executor must independently verify the approved hash and apply the intended action under its own authorization rules.

## Why execution is separated

Allowing a young governance contract to call arbitrary targets makes a single contract bug equivalent to full protocol compromise. T.A.R. therefore separates consensus/approval from infrastructure execution until the executor layer has its own mature controls and audits.

## Proposal integrity

Each proposal records:

- proposer
- action hash
- description
- voting deadline
- execution/timelock deadline
- yes/no vote totals
- quorum snapshot
- executed/cancelled state

Quorum is snapshotted when a proposal is created. Changing the global quorum later does not retroactively alter that proposal's threshold.

## Voting power

Voting power is an explicit registry controlled by the current administrator. Vote weights are bounded to the `uint128` counters used by proposals. This is a **bootstrap governance model**, not a claim of trustless token governance.

For a mature community deployment, administrative authority should be transferred to an appropriately governed multisig or upgraded governance design after independent contract review. The repository should not claim decentralization merely because a contract exists.

## Administration

Admin transfer is two-step:

1. current admin nominates `pendingAdmin`;
2. the nominated address calls `acceptAdmin`.

This prevents accidental transfer to an address that cannot accept control.

Guardians may cancel proposals but cannot execute them. A proposer may also cancel its own unexecuted proposal.

## Timelock

Execution timestamps are fixed when proposals are created, so later changes to the global timelock do not alter existing proposals. Timestamp arithmetic is bounded to the storage types used by the contract.

## Action hashes

An executor should derive the action hash from a deterministic, canonical action description. For example, infrastructure upgrades could hash canonical JSON containing the action type, target environment, artifact digest, version and parameters.

Never approve an opaque hash whose underlying action cannot be independently reconstructed and reviewed.

## Deployment checklist

Before using the governance contract for consequential decisions:

- run the Hardhat test suite;
- obtain independent Solidity review/audit;
- deploy first to a test network;
- verify source code on the explorer;
- document initial voting power and guardians;
- document the bootstrap administrator;
- define canonical action-hash rules;
- define the downstream execution process;
- define emergency cancellation policy;
- rehearse admin transfer and recovery procedures.

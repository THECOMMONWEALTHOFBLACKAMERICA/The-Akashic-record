const { expect } = require("chai");
const { ethers, network } = require("hardhat");

describe("TARGovernance", function () {
  async function deploy(quorum = 1n, timelock = 60n) {
    const [admin, nextAdmin, voter] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("TARGovernance");
    const governance = await Factory.deploy(quorum, timelock);
    await governance.waitForDeployment();
    return { governance, admin, nextAdmin, voter };
  }

  it("snapshots quorum when a proposal is created", async function () {
    const { governance } = await deploy(1n, 60n);
    const action = ethers.keccak256(ethers.toUtf8Bytes("snapshot-action"));
    await governance.createProposal(action, "Snapshot quorum", 60);
    expect(await governance.proposalQuorum(1)).to.equal(1n);

    await governance.setQuorum(2);
    expect(await governance.proposalQuorum(1)).to.equal(1n);

    await governance.vote(1, true);
    await network.provider.send("evm_increaseTime", [121]);
    await network.provider.send("evm_mine");
    expect(await governance.canExecute(1)).to.equal(true);
  });

  it("uses two-step admin transfer", async function () {
    const { governance, admin, nextAdmin } = await deploy();
    await governance.transferAdmin(nextAdmin.address);
    expect(await governance.admin()).to.equal(admin.address);
    expect(await governance.pendingAdmin()).to.equal(nextAdmin.address);

    await governance.connect(nextAdmin).acceptAdmin();
    expect(await governance.admin()).to.equal(nextAdmin.address);
    expect(await governance.pendingAdmin()).to.equal(ethers.ZeroAddress);
  });

  it("rejects voting power that cannot fit vote counters", async function () {
    const { governance, voter } = await deploy();
    const tooLarge = (1n << 128n) + 1n;
    let reverted = false;
    try {
      await governance.setVotingPower(voter.address, tooLarge);
    } catch (error) {
      reverted = true;
      expect(String(error)).to.include("power overflow");
    }
    expect(reverted).to.equal(true);
  });

  it("requires the approved action hash at execution", async function () {
    const { governance } = await deploy(1n, 0n);
    const approved = ethers.keccak256(ethers.toUtf8Bytes("approved"));
    const wrong = ethers.keccak256(ethers.toUtf8Bytes("wrong"));
    await governance.createProposal(approved, "Execute approved hash", 60);
    await governance.vote(1, true);
    await network.provider.send("evm_increaseTime", [61]);
    await network.provider.send("evm_mine");

    let reverted = false;
    try {
      await governance.execute(1, wrong);
    } catch (error) {
      reverted = true;
      expect(String(error)).to.include("action mismatch");
    }
    expect(reverted).to.equal(true);
    await governance.execute(1, approved);
    expect((await governance.proposals(1)).executed).to.equal(true);
  });
});

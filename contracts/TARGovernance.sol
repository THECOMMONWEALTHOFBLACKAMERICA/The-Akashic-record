// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice T.A.R. governance registry. Successful execution records an approved
/// action hash; downstream executors must independently verify and apply the
/// approved action. This contract intentionally does not perform arbitrary calls.
contract TARGovernance {
    struct Proposal {
        address proposer;
        bytes32 actionHash;
        string description;
        uint64 createdAt;
        uint64 votingEnds;
        uint64 executeAfter;
        uint128 yesVotes;
        uint128 noVotes;
        bool executed;
        bool cancelled;
    }

    mapping(uint256 => Proposal) public proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    mapping(uint256 => uint128) public proposalQuorum;
    mapping(address => uint256) public votingPower;
    mapping(address => bool) public guardians;

    uint256 public proposalCount;
    uint256 public quorum;
    uint256 public timelockSeconds;
    address public admin;
    address public pendingAdmin;

    event ProposalCreated(uint256 indexed id, address indexed proposer, bytes32 indexed actionHash, uint256 votingEnds, uint256 executeAfter, uint256 quorumRequired);
    event VoteCast(uint256 indexed id, address indexed voter, bool support, uint256 weight);
    event ProposalExecuted(uint256 indexed id, bytes32 indexed actionHash);
    event ProposalCancelled(uint256 indexed id);
    event VotingPowerSet(address indexed account, uint256 power);
    event GuardianSet(address indexed account, bool enabled);
    event QuorumSet(uint256 quorum);
    event TimelockSet(uint256 timelockSeconds);
    event AdminTransferStarted(address indexed currentAdmin, address indexed pendingAdmin);
    event AdminTransferred(address indexed previousAdmin, address indexed newAdmin);

    modifier onlyAdmin() {
        require(msg.sender == admin, "not admin");
        _;
    }

    constructor(uint256 initialQuorum, uint256 initialTimelockSeconds) {
        require(initialQuorum > 0 && initialQuorum <= type(uint128).max, "invalid quorum");
        require(initialTimelockSeconds <= type(uint64).max - block.timestamp, "timelock overflow");
        admin = msg.sender;
        quorum = initialQuorum;
        timelockSeconds = initialTimelockSeconds;
        guardians[msg.sender] = true;
        votingPower[msg.sender] = 1;
    }

    function setVotingPower(address account, uint256 power) external onlyAdmin {
        require(account != address(0), "zero address");
        require(power <= type(uint128).max, "power overflow");
        votingPower[account] = power;
        emit VotingPowerSet(account, power);
    }

    function setGuardian(address account, bool enabled) external onlyAdmin {
        require(account != address(0), "zero address");
        guardians[account] = enabled;
        emit GuardianSet(account, enabled);
    }

    function setQuorum(uint256 value) external onlyAdmin {
        require(value > 0 && value <= type(uint128).max, "invalid quorum");
        quorum = value;
        emit QuorumSet(value);
    }

    function setTimelock(uint256 value) external onlyAdmin {
        require(value <= type(uint64).max - block.timestamp, "timelock overflow");
        timelockSeconds = value;
        emit TimelockSet(value);
    }

    /// @notice Two-step admin transfer prevents accidental loss of control.
    function transferAdmin(address nextAdmin) external onlyAdmin {
        require(nextAdmin != address(0), "zero address");
        pendingAdmin = nextAdmin;
        emit AdminTransferStarted(admin, nextAdmin);
    }

    function acceptAdmin() external {
        require(msg.sender == pendingAdmin, "not pending admin");
        address previous = admin;
        admin = msg.sender;
        pendingAdmin = address(0);
        emit AdminTransferred(previous, msg.sender);
    }

    function createProposal(bytes32 actionHash, string calldata description, uint64 votingPeriodSeconds) external returns (uint256 id) {
        require(votingPower[msg.sender] > 0, "no voting power");
        require(actionHash != bytes32(0), "empty action");
        require(votingPeriodSeconds >= 60, "voting too short");

        uint256 endsAt = block.timestamp + uint256(votingPeriodSeconds);
        require(endsAt <= type(uint64).max, "voting timestamp overflow");
        uint256 executeAt = endsAt + timelockSeconds;
        require(executeAt <= type(uint64).max, "execution timestamp overflow");

        id = ++proposalCount;
        uint64 ends = uint64(endsAt);
        uint64 executeAfter = uint64(executeAt);
        proposals[id] = Proposal({
            proposer: msg.sender,
            actionHash: actionHash,
            description: description,
            createdAt: uint64(block.timestamp),
            votingEnds: ends,
            executeAfter: executeAfter,
            yesVotes: 0,
            noVotes: 0,
            executed: false,
            cancelled: false
        });
        proposalQuorum[id] = uint128(quorum);
        emit ProposalCreated(id, msg.sender, actionHash, ends, executeAfter, quorum);
    }

    function vote(uint256 id, bool support) external {
        Proposal storage p = proposals[id];
        require(p.proposer != address(0), "unknown proposal");
        require(block.timestamp < p.votingEnds, "voting ended");
        require(!p.cancelled, "cancelled");
        require(!hasVoted[id][msg.sender], "already voted");
        uint256 weight = votingPower[msg.sender];
        require(weight > 0 && weight <= type(uint128).max, "invalid voting power");
        hasVoted[id][msg.sender] = true;
        if (support) p.yesVotes += uint128(weight);
        else p.noVotes += uint128(weight);
        emit VoteCast(id, msg.sender, support, weight);
    }

    function canExecute(uint256 id) public view returns (bool) {
        Proposal storage p = proposals[id];
        return p.proposer != address(0)
            && !p.executed
            && !p.cancelled
            && block.timestamp >= p.executeAfter
            && p.yesVotes >= proposalQuorum[id]
            && p.yesVotes > p.noVotes;
    }

    function execute(uint256 id, bytes32 suppliedActionHash) external {
        Proposal storage p = proposals[id];
        require(canExecute(id), "not executable");
        require(suppliedActionHash == p.actionHash, "action mismatch");
        p.executed = true;
        emit ProposalExecuted(id, suppliedActionHash);
    }

    function cancel(uint256 id) external {
        Proposal storage p = proposals[id];
        require(p.proposer != address(0), "unknown proposal");
        require(!p.executed, "executed");
        require(!p.cancelled, "already cancelled");
        require(msg.sender == p.proposer || guardians[msg.sender], "not authorized");
        p.cancelled = true;
        emit ProposalCancelled(id);
    }
}

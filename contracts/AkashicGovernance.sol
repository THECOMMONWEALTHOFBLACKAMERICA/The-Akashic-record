// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract AkashicGovernance {
    address public owner;
    uint256 public proposalCount;
    mapping(address => bool) public members;
    mapping(uint256 => mapping(address => bool)) public voted;

    struct Proposal { address proposer; bytes32 actionHash; string metadataURI; uint64 deadline; uint64 yes; uint64 no; bool finalized; }
    mapping(uint256 => Proposal) public proposals;

    event ProposalCreated(uint256 indexed id,address indexed proposer,bytes32 actionHash,string metadataURI,uint64 deadline);
    event VoteCast(uint256 indexed id,address indexed voter,bool support);
    event Finalized(uint256 indexed id,bool passed);

    modifier onlyOwner(){require(msg.sender==owner,"owner only");_;}
    modifier onlyMember(){require(members[msg.sender],"member only");_;}

    constructor(){owner=msg.sender;members[msg.sender]=true;}
    function setMember(address account,bool enabled) external onlyOwner {members[account]=enabled;}
    function createProposal(bytes32 actionHash,string calldata metadataURI,uint64 duration) external onlyMember returns(uint256 id){require(duration>0,"duration");id=proposalCount++;proposals[id]=Proposal(msg.sender,actionHash,metadataURI,uint64(block.timestamp)+duration,0,0,false);emit ProposalCreated(id,msg.sender,actionHash,metadataURI,uint64(block.timestamp)+duration);}
    function vote(uint256 id,bool support) external onlyMember {Proposal storage p=proposals[id];require(block.timestamp<p.deadline,"closed");require(!voted[id][msg.sender],"already voted");voted[id][msg.sender]=true;if(support)p.yes++;else p.no++;emit VoteCast(id,msg.sender,support);}
    function finalize(uint256 id) external {Proposal storage p=proposals[id];require(block.timestamp>=p.deadline,"still open");require(!p.finalized,"finalized");p.finalized=true;emit Finalized(id,p.yes>p.no);}
}

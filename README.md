# werewolf-agents
For werewolf llm agent tournament

# Team 19 Approach

Summary: leverage llm for small bounded tasks and chain them together with simple deterministic logic. Responses are generated via the simple\_agent approach.

## Defense

Re-format messages sent into the open channels with header and footers that instructs model to ignore extraneous instructions. Furthermore, instruct our query to extract only the relevant information for player's wolf accusations before storing into the game history.

## Playing Logic

Keep a running consensus score of who the day-time players are mentioning is the wolf. Always vote according to the most believable day-time consensus wolf player (no matter if we're the wolf or villager).

### Consensus Scoring

-   Use llm to extract a sentiment analysis score between [-1, 1] for a message and player pair. I.e. determine if the (player) in the given (message) sounds more like a human (-1) or wolf (1).
-   Accumulate this in a running average sum with the denominator being the number of messages sent into the day channel.
-   Decay the consensus score by gamma=0.9 each round (to place more weight on recent messages).
-   The 'consensus score' is calculated for each player and used to vote.

Conversely, when our agent is the wolf during the night time vote to kill the highest consensus human player (minimum consensus score).

Our strategy is to simply blend in by moving along with the majority consensus.


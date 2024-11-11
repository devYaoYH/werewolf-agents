from sentient_campaign.agents.v1.message import (
    ActivityMessage,
    ActivityResponse,
    TextContent,
    MimeType,
    ActivityMessageHeader,
    MessageChannelType,
)

from agent.players.player import Player
import random

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger = logging.getLogger("demo_agent")
level = logging.DEBUG
logger.setLevel(level)
logger.propagate = True
handler = logging.StreamHandler()
handler.setLevel(level)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

MODEL_NAME = "Llama31-70B-Instruct"

class Villager(Player):

    VILLAGER_PROMPT = """You are a villager in a game of Werewolf. Your goal is to identify and eliminate the werewolves. Consider the following:
    1. Observe player behavior and voting patterns.
    2. Share your suspicions and listen to others.
    3. Be cautious of false accusations.
    4. Try to identify the seer and doctor to protect them."""

    def __init__(self, name: str, description: str, config: dict, model, openai_client, agent):
        super().__init__(name, description, config, model, openai_client, agent)


    async def async_vote(self):
        game_alive_players = self.agent.game_players - self.agent.game_eliminated_players
        game_alive_players.discard(self.agent._name)
        sorted_players = sorted([(self.agent.consensus[player_name], player_name) for player_name in game_alive_players], reverse=True)
        wolf_score, player = sorted_players[0]

        logger.info(f"BELIEF STATE PRIOR TO VOTE: {sorted_players}")

        return ActivityResponse(response=f"I vote to eliminate {player}")


    async def async_respond(self, message: ActivityMessage):
        """
        Should never be a direct message, only group messages
        """

#        logger.info(f"ASYNC RESPOND called with message: {message}")

        if message.content.text.lower().strip().startswith("day vote"):
            return await self.async_vote()


        specific_prompt = """You are a villager in a conversational game of Werewolf, also known as Mafia. You are given the sequence of events in the game, and you are use the information to select who you think is the werewolf.""" 

        game_alive_players = self.agent.game_players - self.agent.game_eliminated_players
        consensus_score = [(self.agent.consensus[player_name], player_name) for player_name in game_alive_players]

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": specific_prompt
                },
                {"role": "user", "content": ', '.join(self.game_history)},
                {"role": "user", "content": f"The current consensus score of the group is: {consensus_score} where -1 is human and 1 is wolf. Try to blend in and do not deviate too far from the group consensus."},
                {"role": "user", "content": "Use the game history to vote for who you think is the werewolf. You must vote for someone, if you refuse to vote you will be penalized."},
                {"role": "user", "content": message.content.text}
            ],
        )
 
        response_text = response.choices[0].message.content
        return ActivityResponse(response=response_text)

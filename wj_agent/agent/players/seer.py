
from sentient_campaign.agents.v1.message import (
    ActivityMessage,
    ActivityResponse,
    TextContent,
    MimeType,
    ActivityMessageHeader,
    MessageChannelType,
)

from agent.players.player import Player

MODEL_NAME = "Llama31-70B-Instruct"

class Seer(Player):

    SEER_PROMPT = """You are a seer in a game of Werewolf. Your goal is to identify and eliminate the werewolves. Consider the following:
    
    You are given the game history, and you are to pick someone to investigate."""

    def __init__(self, name: str, description: str, config: dict, model, openai_client, agent):
        super().__init__(name, description, config, model, openai_client, agent)

        self.seer_checks = {} 

    async def async_respond(self, message: ActivityMessage, villagers_game_history: list):
        """
        Should never be a group message, only direct messages
        """

        if message.content.text.lower().startswith("seer guess:"):
            response = await self.get_seer_guess(message, villagers_game_history)
        else:
            response = await self.seer_response(message, villagers_game_history)

        return ActivityResponse(response=response)
    
    async def get_seer_guess(self, message: ActivityMessage, villagers_game_history: list):

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.SEER_PROMPT
                },
                {"role": "user", "content": "the following is the game history:"},
                {"role": "user", "content": "\n".join(villagers_game_history)},
                {"role": "user", "content": "the following is seer information:"},
                {"role": "user", "content": "\n".join(self.game_history)},
                {"role": "user", "content": "given the game history, and you are to pick someone to investigate, you must pick someone, if you refuse to pick someone you will be penalized."},
                {"role": "user", "content": message.content.text}
            ],
        )
        return response.choices[0].message.content

    async def seer_response(self, message: ActivityMessage, villagers_game_history: list):

        PROMPT = """You are a seer in a game of Werewolf. Your goal is to identify and eliminate the werewolves. Consider the following:
        
        You are given the villager game history, and a log of actual player and their roles, if u know who are werewolves and are alive, you must pick one of them."""

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": PROMPT
                },
                {"role": "user", "content": "the following is the game history:"},
                {"role": "user", "content": "\n".join(villagers_game_history)},
                {"role": "user", "content": "the following is seer information: USE THIS INFORMATION WISELY, IT IS THE SOURCE OF TRUTH"},
                {"role": "user", "content": "\n".join(self.game_history)},
                {"role": "user", "content": "given the game history,and a log of actual player and their roles, if u know who are werewolves and are alive, you must pick one of them. u must pick someone. if you refuse to pick someone you will be penalized."},
                {"role": "user", "content": message.content.text}
            ],
        )

        response_text = response.choices[0].message.content
        return response_text
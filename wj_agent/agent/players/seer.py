
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
    1. Observe player behavior and voting patterns.
    2. Share your suspicions and listen to others.
    3. Be cautious of false accusations.
    4. Try to identify the seer and doctor to protect them."""

    def __init__(self, name: str, description: str, config: dict, model, openai_client):
        super().__init__(name, description, config, model, openai_client)

        self.seer_checks = {} 

    async def async_respond(self, message: ActivityMessage, villagers_game_history: list):
        """
        Should never be a group message, only direct messages
        """

        system_prompt = """you are the seer, you are given the game history, and you are to suggest who you think is the werewolf.""" 
        context = f"villager game history: {", ".join(villagers_game_history)}, seer game history: {",".join(self.game_history)}"

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {"role": "user", "content": context}
            ],
        )
 
        response_text = response.choices[0].message.content
        return ActivityResponse(response=response_text)
    

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

class Wolf(Player):

    WOLF_PROMPT = """You are a wolf in a game of Werewolf. Your goal is to eliminate villagers without being detected. Consider the following:
    1. Blend in with villagers during day discussions.
    2. Coordinate with other werewolves to choose a target.
    3. Pay attention to the seer and doctor's potential actions.
    4. Defend yourself if accused, but don't be too aggressive."""

    def __init__(self, name: str, description: str, config: dict, model, openai_client):
        super().__init__(name, description, config, model, openai_client)


    async def async_notify(self, message: ActivityMessage):
        self.game_history.append(f"[From - {message.header.sender}| {message.header.channel}]: {message.content.text}")

    async def async_respond(self, message: ActivityMessage, villagers_game_history: list):
        """
        Should never be a group message, only direct messages
        """

        # system prompt
        system_prompt = """you are a wolf, you are given the game history, and you are to suggest someone to kill.""" 

        # context
        self.async_notify(message)
        context = f"villager game history: {villagers_game_history}, wolf game history: {self.game_history}"

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
    
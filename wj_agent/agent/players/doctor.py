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

class Doctor(Player):

    DOCTOR_PROMPT = """You are the doctor in a game of Werewolf. Your ability is to protect one player from elimination each night. Consider the following:
    You are given the game history, and you are to pick someone to save, do not save who you think is werewolf."""

    def __init__(self, name: str, description: str, config: dict, model, openai_client):
        super().__init__(name, description, config, model, openai_client)

    async def async_respond(self, message: ActivityMessage, villagers_game_history: list):
        """
        Should never be a group message, only direct messages
        """

        response = await self.get_doctor_response(message, villagers_game_history)
        return ActivityResponse(response=response)
    
    async def get_doctor_response(self, message: ActivityMessage, villagers_game_history: list):

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.DOCTOR_PROMPT   
                },
                {"role": "user", "content": "the following is the game history:"},
                {"role": "user", "content": "\n".join(villagers_game_history)},
                {"role": "user", "content": "the following is doctor information:"},
                {"role": "user", "content": "\n".join(self.game_history)},
                {"role": "user", "content": "given the game history, and you are to pick someone to heal, you must pick someone, if you refuse to pick someone you will be penalized."},
                {"role": "user", "content": message.content.text}
            ],
        )

        return response.choices[0].message.content
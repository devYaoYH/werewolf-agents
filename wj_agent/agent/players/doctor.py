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

    def __init__(self, name: str, description: str, config: dict, model, openai_client, agent):
        super().__init__(name, description, config, model, openai_client, agent)

    async def async_respond(self, message: ActivityMessage, villagers_game_history: list):
        """
        Should never be a group message, only direct messages
        """

        if message.content.text.lower().startswith("doctor save:"):
            response = await self.get_dotor_protect(message, villagers_game_history)
        else:
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
    
    async def get_dotor_protect(self, message: ActivityMessage, villagers_game_history: list):

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
                {"role": "user", "content": "the following is doctor save: make sure to save a villager!"},
                {"role": "user", "content": "\n".join(self.game_history)},
                {"role": "user", "content": "given the game history,and a log of actual player and their roles, if u know who are werewolves and are alive, you must pick one of them. u must pick someone. if you refuse to pick someone you will be penalized."},
                {"role": "user", "content": message.content.text}
            ],
        )
        response_text = response.choices[0].message.content
        return ActivityResponse(response=response_text)
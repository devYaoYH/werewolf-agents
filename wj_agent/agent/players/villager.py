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

class Villager(Player):

    VILLAGER_PROMPT = """You are a villager in a game of Werewolf. Your goal is to identify and eliminate the werewolves. Consider the following:
    1. Observe player behavior and voting patterns.
    2. Share your suspicions and listen to others.
    3. Be cautious of false accusations.
    4. Try to identify the seer and doctor to protect them."""

    def __init__(self, name: str, description: str, config: dict, model, openai_client):
        super().__init__(name, description, config, model, openai_client)


    async def async_respond(self, message: ActivityMessage):
        """
        Should never be a direct message, only group messages
        """

#        logger.info(f"ASYNC RESPOND called with message: {message}")


        specific_prompt = """You are a villager in a conversational game of Werewolf, also known as Mafia. You are given the sequence of events in the game, and you are use the information to select who you think is the werewolf.""" 

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": specific_prompt
                },
                {"role": "user", "content": self.game_history},
                {"role": "user", "content": "Use the game history to vote for who you think is the werewolf. You must vote for someone, if you refuse to vote you will be penalized."},
                {"role": "user", "content": message.content.text}
            ],
        )
 
        response_text = response.choices[0].message.content
        return ActivityResponse(response=response_text)

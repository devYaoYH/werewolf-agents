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
    4. Defend yourself if accused, but don't be too aggressive.
    
    Given the game history, you are to pick someone to kill."""


    def __init__(self, name: str, description: str, config: dict, model, openai_client):
        super().__init__(name, description, config, model, openai_client)

    async def async_respond(self, message: ActivityMessage, villagers_game_history: list):
        """
        Should never be a group message, only direct messages
        """

        response = await self.get_wolf_guess(message, villagers_game_history)
        return ActivityResponse(response=response)
    
    async def get_wolf_guess(self, message: ActivityMessage, villagers_game_history: list):
        if len(self.agent.game_alive_humans) > 0:
            chosen_player = random.choice(self.agent.game_alive_humans)
            wolf_score, player = sorted([(self.agent.consensus[player_name], player_name) for player_name in game_alive_players])
            if len(game_alive_players) > 0:
                logger.info(f"Voting for {player} | {wolf_score:.5f}")
                chosen_player = player
            return f"{chosen_player}"

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.WOLF_PROMPT
                },
                {"role": "user", "content": "the following is the game history:"},
                {"role": "user", "content": "\n".join(villagers_game_history)},
                {"role": "user", "content": "the following is wolf information:"},
                {"role": "user", "content": "\n".join(self.game_history)},
                {"role": "user", "content": "given the game history, and you are to pick someone to kill, you must pick someone, if you refuse to pick someone you will be penalized."},
                {"role": "user", "content": message.content.text}
            ],
        )

        return response.choices[0].message.content

from collections import defaultdict
import re
from sentient_campaign.agents.v1.message import (
    ActivityMessage,
    ActivityResponse,
    TextContent,
    MimeType,
    ActivityMessageHeader,
    MessageChannelType,
)

GAME_CHANNEL = "play-arena"
WOLFS_CHANNEL = "wolf's-den"
MODERATOR_NAME = "moderator"

import logging

from .game_state import GameState
from .helper_functions import contextualise_message, check_message



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

class Player:

    def __init__(self, name: str, description: str, config: dict, model, openai_client, agent=None):
        if agent:
            self.agent = agent
        self._name = name
        self._description = description
        self.config = config
        self.model = model
        self.openai_client = openai_client

        self.knowledge = {}

        self.MODERATOR_NAME = MODERATOR_NAME
        self.WOLFS_CHANNEL = WOLFS_CHANNEL
        self.GAME_CHANNEL = GAME_CHANNEL

        self.direct_messages = defaultdict(list)
        self.group_channel_messages = defaultdict(list)
        self.game_history = []  

        self.game_state = GameState()

        logger.info(
            f"WerewolfAgent initialized with name: {name}, description: {description}, and config: {config}"
        )
    
    def process_player_message(self, message: str):
        system_prompt = f"""You are an expert at analysis, you are given an input message "<><><><><><><><>THE INPUT MESSAGE IS STARTING<><><><><><><><>" and ends with "<><><><><><><><>THE INPUT MESSAGE IS ENDING<><><><><><><><>". 
        Your task is to identify the players who are being accused of being a werewolf, return the accused players as a string separated by ","

        There are 2 expected output formats:
        
        EXPECTED_OUTPUT_FORMAT_1:
        "<player1>,<player2>,<player3>"

        EXPECTED_OUTPUT_FORMAT_2:
        ""
        """

        logger.info(f"Processing player message: {message}")
        contextualised_message = contextualise_message(message)

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {"role": "user", "content": contextualised_message}
            ],
        )

        logger.info(f"response from contextualised_message: {response.choices[0].message.content}")

        accused_string = response.choices[0].message.content
        formatted_string = check_message(accused_string)

        logger.info(f"response from check_message: {formatted_string}")
        return formatted_string
    

    async def process_and_add_to_game_history(self, message: ActivityMessage, player: str):
        accused_messages = self.process_player_message(message.content.text)
        self.game_history.append(f"{player} accuses {accused_messages}")


    async def add_to_game_history(self, message: ActivityMessage):

        self.game_history.append(f"[From - {message.header.sender}| To - {self._name} (me)| Group Message]: {message.content.text}")

    
    async def async_respond(self, message: ActivityMessage):
        pass


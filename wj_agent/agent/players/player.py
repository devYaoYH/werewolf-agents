
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

    def __init__(self, name: str, description: str, config: dict, model, openai_client):
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
        <player1>,<player2>,<player3>

        EXPECTED_OUTPUT_FORMAT_2:
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
    
    def get_game_state(self):
        return self.game_state.current_state
    
    def extract_player_name(self, message: str):
        system_prompt = f"""You are given a string, you are to extract the player name from the string. and return nothing but the name, there must be a name extracted.
        """
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": message}],
        )

        logger.info(f"extract_player_name response: {response.choices[0].message.content}")
        return response.choices[0].message.content

    def extract_player_name_and_role(self, message: str):
        system_prompt = f"""You are given a string, you are to extract the player name and role from the string. and return name and role separated by a comma.

        Expected Output Format:
        <player_name>,<role>
        """
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": message}],
        )

        logger.info(f"extract_player_name_and_role response: {response.choices[0].message.content}")
        return response.choices[0].message.content

    async def async_notify_direct_message(self, message: ActivityMessage):

        user_messages = self.direct_messages.get(message.header.sender, [])
        user_messages.append(message.content.text)
        self.direct_messages[message.header.sender] = user_messages
        self.game_history.append(f"[From - {message.header.sender}| To - {self._name} (me)| Direct Message]: {message.content.text}")

        logger.info(f"game history: {self.game_history}")

    async def async_notify_group_message(self, message: ActivityMessage):

        logger.info(f"game history: {self.game_history}")
        logger.info(f"game state: {self.game_state.current_state}")
        if self.game_state.current_state == "Sharing":
            logger.info("Processing Sharing state message")
            if message.header.sender == self.MODERATOR_NAME:
                logger.info("Processing moderator message in Sharing state")
                if message.content.text.lower().startswith("day consensus"):
                    logger.info("Day message detected - transitioning to Voting state")
                    self.game_state.set_state("Voting")
                    self.game_history.append(message.content.text)
            if message.header.sender != self.MODERATOR_NAME:
                logger.info(f"Processing player message in Sharing state from {message.header.sender}")
                accused_messages = self.process_player_message(message.content.text)
                player = message.header.sender
                self.game_history.append(f"{player} accuses {accused_messages}")

        elif self.game_state.current_state == "Voting":
            logger.info("Processing Voting state message")
            if message.header.sender == self.MODERATOR_NAME:
                logger.info("Processing moderator message in Voting state")
                if message.content.text.lower().startswith("day end"):
                    logger.info("Day End message detected - transitioning to Transition state")
                    self.game_state.set_state("Transition")
                    self.game_history.append(message.content.text)
            if message.header.sender != self.MODERATOR_NAME:
                logger.info(f"Processing vote from player {message.header.sender}")
                player = message.header.sender
                vote = self.extract_player_name(message.content.text)
                self.game_history.append(f"{player} votes for {vote} to be werewolf")
        
        elif self.game_state.current_state == "Transition":
            logger.info("Processing Transition state message")
            if message.header.sender == self.MODERATOR_NAME:
                logger.info("Processing moderator message in Transition state")
                if message.content.text.lower().startswith("day start"):
                    logger.info("Day Start message detected - transitioning to Voting state")
                    self.game_state.set_state("Sharing")
                    self.game_history.append(message.content.text)
                else:
                    logger.info("Adding non-Day Start moderator message to history")
                    self.game_history.append(message.content.text)
    async def async_respond(self, message: ActivityMessage):
        pass


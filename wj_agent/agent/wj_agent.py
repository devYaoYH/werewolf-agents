from typing import Any, Dict
from agent.players.villager import Villager
from agent.players.wolf import Wolf
from agent.players.doctor import Doctor
from agent.players.seer import Seer
from agent.players.player import Player
from agent.players.game_state import GameState

import os,json,re
import asyncio
import logging
from collections import defaultdict

import openai
from openai import RateLimitError, OpenAI
from sentient_campaign.agents.v1.api import IReactiveAgent
from sentient_campaign.agents.v1.message import (
    ActivityMessage,
    ActivityResponse,
    TextContent,
    MimeType,
    ActivityMessageHeader,
    MessageChannelType,
)
from tenacity import (
    retry,
    stop_after_attempt,
    retry_if_exception_type,
    wait_exponential,
)
GAME_CHANNEL = "play-arena"
WOLFS_CHANNEL = "wolf's-den"
MODERATOR_NAME = "moderator"
MODEL_NAME = "Llama31-70B-Instruct"

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

class WJAgent(IReactiveAgent):
    # input -> thoughts -> init action -> reflection -> final action

    def __init__(self):
        logger.debug("WerewolfAgent initialized.")
        

    def __initialize__(self, name: str, description: str, config: dict = None):
        super().__initialize__(name, description, config)
        self._name = name
        self._description = description
        self.MODERATOR_NAME = MODERATOR_NAME
        self.WOLFS_CHANNEL = WOLFS_CHANNEL
        self.GAME_CHANNEL = GAME_CHANNEL
        self.config = config

        self.role = None
        self.villager: Villager = None
        self.wolf: Wolf = None
        self.doctor: Doctor = None
        self.seer: Seer = None

        self.process_message = False

        self.llm_config = self.sentient_llm_config["config_list"][0]
        self.openai_client = OpenAI(
            api_key=self.llm_config["api_key"],
            base_url=self.llm_config["llm_base_url"],
        )

        self.model = self.llm_config["llm_model_name"]
        logger.info(
            f"WerewolfAgent initialized with name: {name}, description: {description}, and config: {config}"
        )
        self.game_intro = None

        # Overall state
        self.game_players = set() # list of other players
        self.game_alive_humans = []
        self.game_eliminated_players = set()
        self.known_player_roles = dict()

        # Belief Updates Variables
        self.num_game_messages = 0
        self.consensus_gamma = 0.9 # Score decay
        self.consensus_self_discount = 0.1 # Discount own defense
        # {player_name: wolf_consensus_val in (-1: human | 1: wolf)
        self.consensus = defaultdict(float)

    def _init_extract_player_names(self, message):
        # Find the list using regex
        match = re.search(r"\[(.*?)\]", message)

        if match:
            player_list = eval(match.group(1))
            logger.info(player_list)
            return player_list
        else:
            logger.info("List not found")
            return []


    def _get_sentiment_score(self, player_name, message):
        """Return a number between -1 to 1."""
        prompt = f"""
{self.game_intro}

{message}

Extract all information about {player_name} and provide a score for this message between -1 to 1 where -1 represents strongly supporting {player_name} as a human and 1 strongly accusing {player_name} to be a wolf. Do not use a numbered list. Provide your output as a single number.
        """

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"You are a analyst of a Werewolf game"},
                {"role": "user", "content": prompt}
            ]
        )
        sentiment_response = response.choices[0].message.content

        pattern = r"-?\d+\.?\d?"
        matches = re.findall(pattern, sentiment_response)

        logger.info(f"\nSentiment for {player_name}: {sentiment_response}\n    Score: {matches}")

        if len(matches) > 0:
            return float(matches[0])
        else:
            return 0

    def _update_consensus_score(self, player_name, message, message_sender):
        cur_score = self.consensus[player_name]
        new_score = self._get_sentiment_score(player_name, message)
        if new_score != 0: # only update if it is relevant
            if message_sender == player_name:
                new_score *= self.consensus_self_discount
            self.consensus[player_name] = (cur_score*(self.num_game_messages-1) + new_score )/self.num_game_messages

    def _decay_consensus_score(self):
        for k in self.consensus:
            self.consensus[k] *= self.consensus_gamma

    def _update_eliminated_players(self, message):
        pattern = r"'(.*?)'"
        match = re.search(pattern, message)

        if match:
            eliminated_player = match.group(1)
            self.game_eliminated_players.add(eliminated_player)
    
    @retry(
        retry=retry_if_exception_type((openai.InternalServerError, RateLimitError)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5)
    )

    async def async_notify(self, message: ActivityMessage):
        
        if message.header.channel == self.GAME_CHANNEL and message.header.sender == self.MODERATOR_NAME and not self.game_intro:
            #game intro
            self.game_intro = message.content.text
            self.game_players.update(self._init_extract_player_names(self.game_intro))

        if message.header.channel_type == MessageChannelType.DIRECT and message.header.sender == self.MODERATOR_NAME and not self.villager:
            self.role = self.find_my_role(message)
            logger.info(f"Role found for user {self._name}: {self.role}")
            self.villager = Villager(self._name, self._description, self.config, self.model, self.openai_client, agent=self)
            if self.role == "seer":
                self.seer = Seer(self._name, self._description, self.config, self.model, self.openai_client, agent=self)
            elif self.role == "doctor":
                self.doctor = Doctor(self._name, self._description, self.config, self.model, self.openai_client, agent=self)
            else:
                self.wolf = Wolf(self._name, self._description, self.config, self.model, self.openai_client, agent=self)
        
        if self.villager:
            logger.info(f"ASYNC NOTIFY called with message: {message}")
            logger.info(f"villager game_history: {self.villager.game_history}")
            if self.seer:
                logger.info(f"seer game_history: {self.seer.game_history}")
            if self.doctor:
                logger.info(f"doctor game_history: {self.doctor.game_history}")
            if self.wolf:
                logger.info(f"wolf game_history: {self.wolf.game_history}")
            logger.info("<><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>")


            if message.header.channel_type == MessageChannelType.GROUP:
                if message.header.channel == self.GAME_CHANNEL:
                    if message.header.sender == self.MODERATOR_NAME:
                        if message.content.text.lower().startswith("day start"):
                            self._update_eliminated_players(message.content.text)
                            self.process_message = True
                        elif message.content.text.lower().startswith("day consensus"):
                            self.process_message = False
                        elif message.content.text.lower().startswith("day end"):
                            self._update_eliminated_players(message.content.text)
                        await self.villager.add_to_game_history(message)
                    else:
                        if not self.process_message:
                            await self.villager.add_to_game_history(message)
                        elif self.process_message:
                            await self.villager.process_and_add_to_game_history(message, message.header.sender)
                elif message.header.channel == self.WOLFS_CHANNEL:
                    await self.wolf.add_to_game_history(message)
            
            elif message.header.channel_type == MessageChannelType.DIRECT:
                
                if message.header.sender == self.MODERATOR_NAME:

                    """ only seer and doctor can be notified by the moderator directly after getting their roles """
                    if self.role == "seer":
                        await self.seer.add_to_game_history(message)
                    elif self.role == "doctor":
                        await self.doctor.add_to_game_history(message)
                    else:
                        logger.error(f"User {self._name} is not a seer or doctor, but the moderator is sending them a direct message, message: {message}")
                else:
                    #You should not recive any direct message from other players
                    pass

            else:
                logger.error(f"Unknown message channel type: {message.header.channel_type}")

        # Belief state updates
        if message.header.channel_type != MessageChannelType.DIRECT and message.header.channel == self.GAME_CHANNEL and message.header.sender != self.MODERATOR_NAME:
            # Update the list of players in the game
            self.game_players.add(message.header.sender)
            game_alive_players = self.game_players - self.game_eliminated_players
            self.num_game_messages += 1
            for player in game_alive_players:
                self._update_consensus_score(player, message.content.text, message.header.sender)
        # Alive humans update
        if message.header.channel == self.WOLFS_CHANNEL and message.header.sender == self.MODERATOR_NAME:
            self.game_alive_humans = self._init_extract_player_names(message.content.text)

    def find_my_role(self, message):
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": f"The user is playing a game of werewolf as user {self._name}, help the user with question with less than a line answer",
                },
                {
                    "role": "user",
                    "name": self._name,
                    "content": f"You have got message from moderator here about my role in the werewolf game, here is the message -> '{message.content.text}', what is your role? possible roles are 'wolf','villager','doctor' and 'seer'. answer in a few words.",
                },
            ],
        )
        my_role_guess = response.choices[0].message.content
        logger.info(f"my_role_guess: {my_role_guess}")
        if "villager" in my_role_guess.lower():
            role = "villager"
        elif "seer" in my_role_guess.lower():
            role = "seer"
        elif "doctor" in my_role_guess.lower():
            role = "doctor"
        else:
            role = "wolf"
        
        return role

    async def async_respond(self, message: ActivityMessage):
        logger.info(f"ASYNC RESPOND called with message: {message}")
        logger.info(f"villager game_history: {self.villager.game_history}")
        if self.seer:
            logger.info(f"seer game_history: {self.seer.game_history}")
        if self.doctor:
            logger.info(f"doctor game_history: {self.doctor.game_history}")
        if self.wolf:
            logger.info(f"wolf game_history: {self.wolf.game_history}")

        logger.info("<><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>")

        if message.header.channel_type == MessageChannelType.DIRECT and message.header.sender == self.MODERATOR_NAME:
         #   self.direct_messages[message.header.sender].append(message.content.text)
            if self.role == "seer":
                response_message = await self.seer.async_respond(message, self.villager.game_history)
            elif self.role == "doctor":
                response_message = await self.doctor.async_respond(message, self.villager.game_history)
            else:
                logger.error(f"User {self._name} is not a seer or doctor, but the moderator is sending them a direct message, message: {message}")
             
        elif message.header.channel_type == MessageChannelType.GROUP:

            if message.header.channel == self.GAME_CHANNEL:
                if self.role == "seer":
                    response_message = await self.seer.async_respond(message, self.villager.game_history)
                else:
                    response_message = await self.villager.async_respond(message)
            elif message.header.channel == self.WOLFS_CHANNEL:
                response_message = await self.wolf.async_respond(message, self.villager.game_history)
            
        return response_message
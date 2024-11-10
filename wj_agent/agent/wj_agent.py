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
    
    @retry(
        retry=retry_if_exception_type((openai.InternalServerError, RateLimitError)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5)
    )

    async def async_notify(self, message: ActivityMessage):
        
        if message.header.channel == self.GAME_CHANNEL and message.header.sender == self.MODERATOR_NAME and not self.game_intro:
            #game intro
            self.game_intro = message.content.text
        elif not self.villager:
            self.role = self.find_my_role(message)
            logger.info(f"Role found for user {self._name}: {self.role}")
            self.villager = Villager(self._name, self._description, self.config, self.model, self.openai_client)
            if self.role == "seer":
                self.seer = Seer(self._name, self._description, self.config, self.model, self.openai_client)
            elif self.role == "doctor":
                self.doctor = Doctor(self._name, self._description, self.config, self.model, self.openai_client)
            else:
                self.wolf = Wolf(self._name, self._description, self.config, self.model, self.openai_client)
        else:

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
                            self.process_message = True
                        elif message.content.text.lower().startswith("day consensus"):
                            self.process_message = False
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
                response_message = await self.villager.async_respond(message)
            elif message.header.channel == self.WOLFS_CHANNEL:
                response_message = await self.wolf.async_respond(message, self.villager.game_history)
            
        return response_message
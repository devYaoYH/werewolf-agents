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
    1. Decide whether to protect yourself or others.
    2. Try to identify key players to protect (like the seer).
    3. Vary your protection pattern to avoid being predictable.
    4. Participate in discussions without revealing your role."""

    def __init__(self, name: str, description: str, config: dict, model, openai_client):
        super().__init__(name, description, config, model, openai_client)

    async def async_respond(self, message: ActivityMessage, villagers_game_history: list):
        """
        Should never be a group message, only direct messages
        """

        system_prompt = """you are the doctor, you are given the game history, and you are to suggest who you think is the werewolf.""" 
        context = f"villager game history: {", ".join(villagers_game_history)}, doctor game history: {",".join(self.game_history)}"
        
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
    
    
    def _get_response_for_doctors_save(self, message):
        game_situation = self.get_interwoven_history()
        
        specific_prompt = """think through your response by answering the following step-by-step:
1. Based on recent discussions, who seems to be in the most danger?
2. Have I protected myself recently, or do I need to consider self-protection?
3. Are there any players who might be the Seer or other key roles that I should prioritize?
4. How can I vary my protection pattern to avoid being predictable to the werewolves?
5. How can I contribute to the village discussions with or without revealing my role? Should I reveal my role at this point?"""

        inner_monologue = self._get_inner_monologue(self.DOCTOR_PROMPT, game_situation, specific_prompt)

        action = self._get_final_action(self.DOCTOR_PROMPT, game_situation, inner_monologue, "choice of player to protect")        
        return action
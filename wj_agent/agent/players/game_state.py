class GameState:
    STATES = ["Transition", "Sharing", "Voting"]
    
    def __init__(self):
        self.current_index = 0
    
    def next_state(self):
        self.current_index = (self.current_index + 1) % len(self.STATES)
        return self.STATES[self.current_index]
    
    @property 
    def current_state(self):
        return self.STATES[self.current_index]
    
    def set_state(self, state):
        if state in self.STATES:
            self.current_index = self.STATES.index(state)
        else:
            raise ValueError(f"Invalid state. Must be one of {self.STATES}")


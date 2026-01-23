from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from config import MODEL_NAME, MAX_TOKENS


class DebateAgent:
    def __init__(self, name: str, role: str, system_prompt: str, temperature: float = 0.7):
        self.name = name
        self.role = role

        # 1. THE LLM - This is the "brain" of the agent.
        #    ChatAnthropic is a LangChain wrapper around the Anthropic API.
        #    Each agent gets its OWN LLM instance with its own settings.
        self.llm = ChatAnthropic(
            model=MODEL_NAME,
            temperature=temperature,
            max_tokens=MAX_TOKENS
        )

        # 2. THE PROMPT TEMPLATE - This defines HOW the agent thinks.
        #    The system message gives the agent its persona/personality.
        #    The human message provides context and instructions each turn.
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", (
                "Current debate transcript:\n{debate_context}\n\n"
                "Your instruction for this turn:\n{instruction}\n\n"
                "Respond in character as {name}, the {role} in this debate."
            ))
        ])

        # 3. THE CHAIN - This connects the prompt template to the LLM.
        #    The "|" operator (pipe) is LangChain's way of saying:
        #    "Take the output of the left side and feed it to the right side"
        #    So: filled prompt template -> sent to Claude -> response
        self.chain = self.prompt | self.llm

    def respond(self, debate_context: str, instruction: str) -> str:
        """Generate a response given the current debate state."""

        # 4. INVOKE - This runs the chain.
        #    We pass in the variables that fill the prompt template.
        #    The chain fills the template, sends it to Claude, returns the response.
        response = self.chain.invoke({
            "debate_context": debate_context,
            "instruction": instruction,
            "name": self.name,
            "role": self.role
        })

        return response.content

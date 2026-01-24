MODEL_NAME = "claude-sonnet-4-5-20250929"
TEMPERATURE_DEBATERS = 0.7      # Higher = more creative arguments
TEMPERATURE_JUDGE = 0.3         # Lower = more analytical/consistent
MAX_TOKENS = 1024               # Max length per agent response
NUM_REBUTTAL_ROUNDS = 2         # Number of back-and-forth rounds

# Available personality styles for debaters
AVAILABLE_STYLES = ["passionate", "aggressive", "academic", "humorous"]
DEFAULT_PRO_STYLE = "passionate"
DEFAULT_CON_STYLE = "passionate"

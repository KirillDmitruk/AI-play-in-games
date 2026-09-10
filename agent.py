from google import genai

client = genai.Client()

VALID_ACTIONS = {
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT"
}


def choose_action(game_state):
    prompt = f"""
You are playing Snake.

Coordinate system:
- (0, 0) is the top-left corner.
- X increases to the RIGHT.
- Y increases DOWNWARD.

Actions change coordinates as follows:
- UP:    (x, y - 1)
- DOWN:  (x, y + 1)
- LEFT:  (x - 1, y)
- RIGHT: (x + 1, y)

The board wraps around at the edges.

Before choosing an action, determine where the food is relative
to the snake and choose a move that reduces the distance to it,
unless that move would cause a collision.


Board size:
{game_state["grid_width"]} x {game_state["grid_height"]}

Snake head:
{game_state["head"]}

Snake body:
{game_state["body"]}

Food:
{game_state["food"]}

Current direction:
{game_state["direction"]}

Rules:
- Your goal is to eat the food.
- Do not collide with your own body.
- The board wraps around at the edges.
- You cannot reverse direction immediately.

Available actions:
UP
DOWN
LEFT
RIGHT

Choose the best next action.

Respond ONLY with one of:
UP
DOWN
LEFT
RIGHT
"""

    interaction = client.interactions.create(
        model="gemini-2.5-flash",
        input=prompt,
    )

    action = interaction.output_text.strip().upper()

    if action not in VALID_ACTIONS:
        return None

    return action

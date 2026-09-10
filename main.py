import random

import pygame

from agent import choose_action


SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600

CELL_SIZE = 30

BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 128, 0)


pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("AI Snake")

clock = pygame.time.Clock()

running = True


# -------------------------
# Игровое поле
# -------------------------

GRID_WIDTH = SCREEN_WIDTH // CELL_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // CELL_SIZE


# -------------------------
# Змейка
# -------------------------

snake_pos = [
    GRID_WIDTH // 2,
    GRID_HEIGHT // 2
]

snake_body = [
    snake_pos.copy()
]

snake_length = 1

# Начальное направление — вправо
snake_direction = (1, 0)


# -------------------------
# Функции
# -------------------------

def create_food():
    food = [
        random.randrange(0, GRID_WIDTH),
        random.randrange(0, GRID_HEIGHT)
    ]

    # Не создаём яблоко внутри змейки
    while food in snake_body:
        food = [
            random.randrange(0, GRID_WIDTH),
            random.randrange(0, GRID_HEIGHT)
        ]

    return food


def direction_to_string(direction):
    directions = {
        (0, -1): "UP",
        (0, 1): "DOWN",
        (-1, 0): "LEFT",
        (1, 0): "RIGHT"
    }

    return directions[direction]


def change_direction(action, current_direction):
    if action == "UP" and current_direction != (0, 1):
        return (0, -1)

    elif action == "DOWN" and current_direction != (0, -1):
        return (0, 1)

    elif action == "LEFT" and current_direction != (1, 0):
        return (-1, 0)

    elif action == "RIGHT" and current_direction != (-1, 0):
        return (1, 0)

    return current_direction


def get_game_state():
    return {
        "head": snake_pos.copy(),

        "body": [
            segment.copy()
            for segment in snake_body
        ],

        "food": food_pos.copy(),

        "direction": direction_to_string(
            snake_direction
        ),

        "grid_width": GRID_WIDTH,
        "grid_height": GRID_HEIGHT
    }


# -------------------------
# Создаём первое яблоко
# -------------------------

food_pos = create_food()


# -------------------------
# Главный игровой цикл
# -------------------------

while running:

    # -------------------------
    # События pygame
    # -------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False


    if not running:
        break


    # -------------------------
    # AI
    # -------------------------

    game_state = get_game_state()

    print()
    print("STATE:", game_state)

    try:
        action = choose_action(game_state)

    except Exception as error:
        print("Gemini error:", error)
        break


    print("AI ACTION:", action)


    # -------------------------
    # Применяем решение AI
    # -------------------------

    if action is not None:
        snake_direction = change_direction(
            action,
            snake_direction
        )


    # -------------------------
    # Движение змейки
    # -------------------------

    dx, dy = snake_direction

    x, y = snake_pos

    x += dx
    y += dy


    # Переход через края поля
    x %= GRID_WIDTH
    y %= GRID_HEIGHT


    snake_pos = [x, y]


    # -------------------------
    # Яблоко
    # -------------------------

    if snake_pos == food_pos:

        snake_length += 1

        food_pos = create_food()

        print("APPLE EATEN")
        print("Snake length:", snake_length)


    # -------------------------
    # Обновляем тело
    # -------------------------

    snake_body.append(
        snake_pos.copy()
    )


    # Если змейка не выросла,
    # удаляем старый хвост
    if len(snake_body) > snake_length:
        snake_body.pop(0)


    # -------------------------
    # Столкновение с собой
    # -------------------------

    if snake_pos in snake_body[:-1]:

        print("GAME OVER")
        print("AI collided with itself.")

        running = False


    # -------------------------
    # Отрисовка
    # -------------------------

    screen.fill(BLACK)


    # Змейка
    for segment in snake_body:

        segment_x, segment_y = segment

        pygame.draw.rect(
            screen,
            GREEN,
            [
                segment_x * CELL_SIZE,
                segment_y * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE
            ]
        )


    # Яблоко
    pygame.draw.rect(
        screen,
        RED,
        [
            food_pos[0] * CELL_SIZE,
            food_pos[1] * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE
        ]
    )


    pygame.display.flip()

    # API Gemini сам будет основным
    # ограничителем скорости игры
    clock.tick(60)


pygame.quit()
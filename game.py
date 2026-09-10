import random

import pygame

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600

CELL_SIZE = 30
SNAKE_SPEED = 10

BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 128, 0)

pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("AI Snake")

clock = pygame.time.Clock()
running = True

# Размер игрового поля в клетках
GRID_WIDTH = SCREEN_WIDTH // CELL_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // CELL_SIZE

# Начальная позиция змейки
snake_pos = [GRID_WIDTH // 2, GRID_HEIGHT // 2]

# Тело змейки
snake_body = [snake_pos.copy()]

# Начальная длина
snake_length = 1

# Начальное направление — вправо
snake_direction = (1, 0)


def create_food():
    food = [
        random.randrange(0, GRID_WIDTH),
        random.randrange(0, GRID_HEIGHT)
    ]

    while food in snake_body:
        food = [
            random.randrange(0, GRID_WIDTH),
            random.randrange(0, GRID_HEIGHT)
        ]

    return food


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


def direction_to_string(direction):
    directions = {
        (0, -1): "UP",
        (0, 1): "DOWN",
        (-1, 0): "LEFT",
        (1, 0): "RIGHT"
    }

    return directions[direction]


food_pos = create_food()

while running:

    action = None

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                action = "UP"
            elif event.key == pygame.K_s:
                action = "DOWN"
            elif event.key == pygame.K_a:
                action = "LEFT"
            elif event.key == pygame.K_d:
                action = "RIGHT"

    # Если игрок дал команду
    if action is not None:
        snake_direction = change_direction(
            action,
            snake_direction
        )

    # Направление
    dx, dy = snake_direction

    # Текущая позиция головы
    x, y = snake_pos

    # Новая позиция
    x += dx
    y += dy

    # Переход через края поля
    x %= GRID_WIDTH
    y %= GRID_HEIGHT

    snake_pos = [x, y]

    # Проверяем яблоко
    if snake_pos == food_pos:
        snake_length += 1
        food_pos = create_food()

    # Добавляем новую голову
    snake_body.append(snake_pos.copy())

    # Если не выросли — удаляем хвост
    if len(snake_body) > snake_length:
        snake_body.pop(0)

    # Столкновение с собой
    if snake_pos in snake_body[:-1]:
        running = False

    # Отрисовка
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

    clock.tick(SNAKE_SPEED)

pygame.quit()

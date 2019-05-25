import time
from collections import UserList
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from enum import Enum
from itertools import repeat
from random import choice, randrange
from typing import Sequence

import arcade
from arcade import color as Color
from arcade import key as Key

CONFIG = {
    "tiles": {"sep": 5, "row": 20, "col": 20, "width": 30, "height": 30},
    "window": {"title": "Kanuni", "padding": 150},
    "colors": {0: Color.AQUA, 1: Color.ANTIQUE_FUCHSIA, 2: Color.GREEN, 3: Color.RED},
    "game": {"max_food": 10},
    "food_types": {2: "herb", 3: "carn"},
    "movement": {"x": "y", "y": "x"},
}

sep = CONFIG["tiles"]["sep"]
pad = CONFIG["window"]["padding"]
CONFIG["window"]["width"] = (
    (CONFIG["tiles"]["width"] + sep) * CONFIG["tiles"]["col"] + sep + pad
)
CONFIG["window"]["height"] = (
    (CONFIG["tiles"]["height"] + sep) * CONFIG["tiles"]["row"] + sep + pad
)


class Feeding(Enum):
    HERB = "Herb"
    CARN = "Carn"
    OMN = "Omn"

    def __str__(self):
        return f"{self.value.title()}ivor"


@dataclass
class Cell:
    x: int = 0
    y: int = 0

    def update_coords(self, direction, by):
        prev = getattr(self, direction)
        setattr(self, f"_{direction}", prev)
        setattr(self, direction, prev + by)


@dataclass
class Features:
    food: int = 1
    speed: int = 1
    feeding: Feeding = Feeding.HERB


@dataclass
class Player:
    cells: Sequence[Cell] = None
    points: int = 0
    level: int = 1
    loses: int = 0
    features: Features = field(default_factory=Features)

    def __post_init__(self):
        self.cells = [Cell()]
        self.features.feeding = choice(tuple(Feeding.__members__.values()))

    def obtain_cell(self):
        for _ in range(len(self.cells)):
            cell = choice(self.cells)
            through = choice(("x", "y"))
            opp = CONFIG["movement"][through]
            cell = Cell(
                **{through: getattr(cell, through) + 1, opp: getattr(cell, opp)}
            )
            if self.cell_collision(cell.x, cell.y):
                continue
            if cell.x < CONFIG["tiles"]["col"] and cell.y < CONFIG["tiles"]["row"]:
                self.cells.append(cell)
                return

    def obtain_new_feature(self):
        self.features.food += randrange(1, 4)
        self.features.speed += randrange(-1, 2)
        self.features.feeding = choice(tuple(Feeding.__members__.values()))

        for item, value in vars(self.features).items():
            if value == 0:
                setattr(self.features, item, 1)

        self.obtain_cell()

    def cell_collision(self, row, col):
        for cell in self.cells:
            if cell.y == row and cell.x == col:
                return True
        return False

    @property
    def required_points(self):
        return self.level * 4


class Grid(UserList):
    def __init__(self, row, col, **kwargs):
        self.data = [list(repeat(0, col)).copy() for _ in range(row)]

    def set_block(self, col, row, value):
        self.data[row][col] = value

    def get_block(self, col, row):
        return self.data[row][col]


class Controller(arcade.Window):
    def __init__(self, width, height, title, **kwargs):
        super().__init__(width, height, title)

        self.grid = Grid(**CONFIG["tiles"])
        self.player = Player()
        self.herb_foods = 0
        self.carn_foods = 0

        arcade.set_background_color(Color.WHITE)
        self.pending_task = None
        self.event = None
        self.event_timer = 0

    def draw_info(self):
        arcade.draw_text(f"DNA Points: {self.player.points}", 90, 0, Color.BLACK, 16)
        arcade.draw_text(
            f"Feeding Type: {self.player.features.feeding}", 250, 0, Color.BLACK, 16
        )
        arcade.draw_text(
            f"Food Modifier: {self.player.features.food}", 500, 0, Color.BLACK, 16
        )

        arcade.draw_text(
            f"Collect {self.player.required_points} DNA points and press G to evolve.",
            150,
            50,
            Color.BLACK,
            16,
        )
        arcade.draw_text(f"Generation: {self.player.level}", 290, 800, Color.BLACK, 16)
        arcade.draw_text(
            f"Speed: {self.player.features.speed}", 490, 800, Color.BLACK, 16
        )

        if self.event:
            arcade.draw_text(
                f"!!!!!!!!!!! - {self.event} - !!!!!!!!!!!!!!!!!!",
                100,
                830,
                Color.RED,
                16,
            )

    def draw_grid(self):
        self.shape_list = arcade.ShapeElementList()

        sep, row, col, width, height = CONFIG["tiles"].values()
        padding = CONFIG["window"]["padding"]
        for ridx, row in enumerate(self.grid):
            for cidx, col in enumerate(self.grid[ridx]):
                color = CONFIG["colors"].get(col, Color.AQUA)

                x = (sep + width) * cidx + (sep + width) + padding // 2  # centerize
                y = (sep + height) * ridx + (sep + height) + padding // 2

                rect = arcade.create_rectangle_filled(x, y, width, height, color)
                self.shape_list.append(rect)

    def _draw_foods(self, food, amount):
        if amount <= 0:
            return 0

        increased = 0
        for _ in range(amount):
            row = randrange(CONFIG["tiles"]["row"])
            col = randrange(CONFIG["tiles"]["col"])
            if self.player.cell_collision(row, col):
                continue

            self.grid.set_block(row, col, food)
            increased += 1
        return increased

    def draw_foods(self):
        herb_amount = CONFIG["game"]["max_food"] - self.herb_foods
        carn_amount = CONFIG["game"]["max_food"] - self.carn_foods
        self.herb_foods += self._draw_foods(2, herb_amount)
        self.carn_foods += self._draw_foods(3, carn_amount)

    def draw_player(self, value=1):
        for cell in self.player.cells:
            self.grid.set_block(cell.x, cell.y, value)
        self.draw_foods()
        self.draw_grid()
        self.draw_info()

    def on_draw(self):
        arcade.start_render()
        self.draw_player()
        self.shape_list.draw()
        print(self.player)

    def on_key_release(self, key, *args):
        self.draw_player(0)
        actions = {
            Key.W: ("y", self.player.features.speed),
            Key.S: ("y", -self.player.features.speed),
            Key.D: ("x", self.player.features.speed),
            Key.A: ("x", -self.player.features.speed),
            Key.G: ("evolve", self.player.points),
            Key.R: ("restart", None),
        }
        if self.pending_task:
            task, *args = self.pending_task
            getattr(self.grid, task)(*args)
        if actions.get(key):
            direction, amount = actions[key]
            with suppress(IndexError):
                for cell in self.player.cells:
                    if direction == "y":
                        x, y = cell.x, cell.y + amount
                        current = self.grid.get_block(x, y)
                    elif direction == "x":
                        x, y = cell.x + amount, cell.y
                        current = self.grid.get_block(x, y)
                    else:
                        self.update_player(direction, amount)
                        return

                    print(current)
                    self.update_player("tile", current, x, y)
                    cell.update_coords(direction, amount)

    def update_player(self, utype, action, *args):
        self.event_timer += 1
        if randrange(0, 250) == 66 and len(self.player.cells) > 1:
            self.player.loses += 1
            self.event = (
                f"Oh no! One of your cells' died. Total {self.player.loses} cells died."
            )
            self.player.cells.pop()

        if utype == "tile" and action in {3, 2}:
            feeding = self.player.features.feeding
            if feeding is not Feeding.OMN:
                if feeding is Feeding.CARN and action == 3:
                    pass
                elif feeding is Feeding.HERB and action == 2:
                    pass
                else:
                    self.pending_task = "set_block", *args, action
                    return
            self.player.points += self.player.features.food

            attr = f"{CONFIG['food_types'][action]}_foods"
            setattr(self, attr, getattr(self, attr) - 1)

        elif utype == "evolve":
            if action >= self.player.required_points:
                self.player.level += 1
                self.player.points -= action
                self.player.obtain_new_feature()
        
        elif utype == "restart":
            self.player = Player()
            self.grid = Grid(**CONFIG["tiles"])
            self.herb_foods = 0
            self.carn_foods = 0

            
            self.pending_task = None
            self.event = None
            self.event_timer = 0


def main():
    Controller(**CONFIG["window"])
    arcade.run()


if __name__ == "__main__":
    main()

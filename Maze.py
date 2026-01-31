# Maze Class, defines the maze environment for pathfinding algorithms
import os
import random
import warnings

import Node


class Maze:
    # Instance variables
    startx: int
    starty: int
    endx: int
    endy: int
    Maze: list[list[Node.Node]]
    maze_height: int
    maze_width: int

    # Initialise the Maze object, given a 3D list defining walls and start/end coordinates
    def __init__(self, maze: list[list[tuple[list[bool], int]]], startx: int, starty: int, endx: int, endy: int):
        # Check that start and end positions are not the same
        if startx == endx and starty == endy:
            raise ValueError("Start and End nodes cannot be the same")

        # Get maze dimensions
        self.maze_height = len(maze)
        self.maze_width = len(maze[0]) if self.maze_height > 0 else 0

        # Boundary check for start position
        if startx >= self.maze_width or startx < 0 or starty >= self.maze_height or starty < 0:
            raise ValueError(
                f"Start position ({startx}, {starty}) is out of bounds for a {self.maze_width}x{self.maze_height} maze.")

        # Store start and end coordinates
        self.startx = startx
        self.starty = starty
        self.endx = endx
        self.endy = endy

        # Initialise the maze structure as instance variable, a 2D list of Node objects
        self.Maze: list[list[Node.Node]] = []

        # Loop over rows
        for y_coord in range(self.maze_height):
            row_list = []
            # Loop over columns
            for x_coord in range(self.maze_width):
                # Get the wall data for this cell, a list of 4 booleans; up, down, left, right
                wall_data = maze[y_coord][x_coord][0]
                cost = maze[y_coord][x_coord][1]

                # Create Node with the wall data and coordinates, add to the current row
                row_list.append(Node.Node(x_coord, y_coord,
                                          wall_data[0], wall_data[1],
                                          wall_data[2], wall_data[3], cost))
            self.Maze.append(row_list)

        # raise a warning if start and/or end node is placed in isolated coord
        # no i am not integrating a search algorithm just to check can the 2 reach each other thats the point of the project lmao
        if self.Maze[starty][startx].is_isolated():
            warnings.warn("Start node is isolated")
        if self.Maze[endy][endx].is_isolated():
            warnings.warn("End node is isolated")

        # Pah to store the found path
        self.path = []
        self.path_dirs = {}

    # Set the path found by a search algorithm
    def set_path(self, path: list[tuple[int, int]]):
        # Stores a found path
        self.path = path
        # Converts the path into a dictionary
        self.path_dirs = {}
        # Loop through the path to determine directions
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            if x2 == x1 + 1:
                self.path_dirs[(x1, y1)] = '→'
            elif x2 == x1 - 1:
                self.path_dirs[(x1, y1)] = '←'
            elif y2 == y1 + 1:
                self.path_dirs[(x1, y1)] = '↓'
            elif y2 == y1 - 1:
                self.path_dirs[(x1, y1)] = '↑'

    def get_maze_x(self):
        # Getter for maze width, note it start counting from 1
        return self.maze_width

    def get_maze_y(self):
        # Getter for maze height, note it start counting from 1
        return self.maze_height

    # Check if movement from one node to another is traversable
    def traversable(self, x1: int, y1: int, x2: int, y2: int):
        # Check if two nodes are adjacent and if movement between them is possible
        if abs(x1 - x2 + y1 - y2) == 1:
            if abs(x1 - x2) == 1:
                if x1 > x2:
                    # Movinf left
                    return self.Maze[y1][x1].get_left()
                else:
                    # Moving right
                    return self.Maze[y1][x1].get_right()
            else:
                if y1 > y2:
                    # Moving up
                    return self.Maze[y1][x1].get_up()
                else:
                    # Moving down
                    return self.Maze[y1][x1].get_down()
        else:
            return False

    # Get the traversable directions array for a node
    def get_traversable_array(self, x, y) -> list[bool]:
        return [self.Maze[y][x].get_up(), self.Maze[y][x].get_down(), self.Maze[y][x].get_left(), self.Maze[y][x].get_right()]

    def get_node_cost(self, x, y):
        return self.Maze[y][x].get_cost()

    # Print the node at (x, y) for debugging
    def print_node(self, x, y):
        print(self.Maze[y][x])

    # Check if (x, y) is the start node
    def is_start(self, x, y):
        return x == self.startx and y == self.starty

    # Check if (x, y) is the end node
    def is_end(self, x, y):
        return x == self.endx and y == self.endy

    # randomizes the maze
    def randomize(self, wall_percentage, oneway_percentage, force_start_end_split=True, max_cost_rng=5, seed=None):

        if wall_percentage + oneway_percentage > 100:  # obviously thats not allowed lol
            raise ValueError("given percentages added up to over 100%")

        # ------------ (Aiman) ---------------
        # Other checks to go along with the one abovee
        if wall_percentage < 0 or oneway_percentage < 0:
            raise ValueError("Percentages must be >= 0")
        if max_cost_rng < 0:
            raise ValueError("max_cost_rng must be >= 0")

        # If no seed supplied, create a strong random one
        # We keep the RNG local so other modules aren't affected
        if seed is None:
            seed = int.from_bytes(os.urandom(16), "big") # "big" makes conversion consistent across PCs, regardless of CPU

        # We are moving away from os.urandom(). It should help with synchronising randomness across different OS (to be tested)?????
        rng = random.Random(seed) # We should record the Python version to avoid any changes
        # i agree, the python version we are running this on is 3.13.7

        # Choosing the start and end coordinates, while ensuring that they are not identical
        # Also the new seeding feature is added
        while True:
            up_or_down_rng = rng.randint(1, 100) < 50
            startx = rng.randint(0, self.maze_width - 1)
            starty = 0 if up_or_down_rng else self.maze_height - 1
            if not force_start_end_split:
                starty = rng.randint(0, self.maze_height - 1)

            endx = rng.randint(0, self.maze_width - 1)
            endy = self.maze_height - 1 if up_or_down_rng else 0
            if not force_start_end_split:
                endy = rng.randint(0, self.maze_height - 1)

            if (startx, starty) != (endx, endy):
                break

        self.startx, self.starty = startx, starty
        self.endx, self.endy = endx, endy

        # --------------------------------------------------

        """ OLD
        up_or_down_rng = True if random.randint(1, 100) < 50 else False
        self.startx = random.randint(0, self.maze_width - 1)
        self.starty = 0 if up_or_down_rng else self.maze_height - 1 if force_start_end_split else random.randint(0, self.maze_height - 1)
        self.endx = random.randint(0, self.maze_width - 1)
        self.endy = self.maze_height - 1 if up_or_down_rng else 0 if force_start_end_split else random.randint(0, self.maze_height - 1)
        """

        for y in range(len(self.Maze)):
            for x in range(len(self.Maze[y])): # each iteration only modifies the bloc below and right

                # cost randomizing
                self.Maze[y][x].cost = rng.randint(0, max_cost_rng)

                on_border = x == len(self.Maze[y]) - 1 or y == len(self.Maze) - 1 # if true the loop below only run once and will only modify down
                for k in range(2):
                    rngNumber = rng.randint(1, 100)
                    if 101 - oneway_percentage < rngNumber: # one way case, having 50% chance to go either way
                        if rng.randint(0, 100) < 50: # up/left
                            if on_border and y != len(self.Maze) - 1: # up
                                self.Maze[y][x].down = False
                                self.Maze[y + 1][x].up = True
                            elif x != len(self.Maze[y]) - 1: # left
                                self.Maze[y][x].right = False
                                self.Maze[y][x + 1].left = True
                        else: # down/right
                            if on_border and y != len(self.Maze) - 1:  # down
                                self.Maze[y][x].down = True
                                self.Maze[y + 1][x].up = False
                            elif x != len(self.Maze[y]) - 1:  # right
                                self.Maze[y][x].right = True
                                self.Maze[y][x + 1].left = False
                    elif 101 - oneway_percentage - wall_percentage < rngNumber <= 100 - oneway_percentage: # wall case
                        if on_border and y != len(self.Maze) - 1:
                            self.Maze[y][x].down = False
                            self.Maze[y + 1][x].up = False
                        elif x != len(self.Maze[y]) - 1:
                            self.Maze[y][x].right = False
                            self.Maze[y][x + 1].left = False
                    else: # open path case
                        if on_border and y != len(self.Maze) - 1:  # up
                            self.Maze[y][x].down = True
                            self.Maze[y + 1][x].up = True
                        elif x != len(self.Maze[y]) - 1:  # left
                            self.Maze[y][x].right = True
                            self.Maze[y][x + 1].left = True

                    if on_border:
                        break
                    else:
                        on_border = True

        return seed

    def __str__(self):

        # the tostring function of the maze
        # basically prints the maze out in shitty ascii chars
        # note the maze can theoretically support one way paths so i added them in and used arrows to display them
        # and an open space means u can go both ways

        output = "-"
        for _ in self.Maze[0]:
            output += "----"
        output += "\n"

        # ANSI code for pink
        PINK = "\033[95m"
        # ANSI code for setting colour back to normal
        RESET = "\033[0m"

        # Helper function to check what to display in a cell
        def check_space(x, y) -> str:
            if self.is_start(x, y):
                return "s "
            elif self.is_end(x, y):
                return "e "
            elif (x, y) in self.path_dirs:
                return f"{PINK}{self.path_dirs[(x, y)]}{RESET} "
            else:
                return "  "

        # Loop over rows
        for row in range(len(self.Maze)):
            # Start of the row
            output += "| " + check_space(0, row)

            # Loop over columns
            for col in range(len(self.Maze[row])):
                # check for block to the right skip if on right most block
                if col < len(self.Maze[row]) - 1:
                    # Check for two way paths
                    right = self.traversable(col, row, col + 1, row)
                    left = self.traversable(col + 1, row, col, row)

                    if right and left:
                        output += "  "
                    elif right and not left:
                        output += "→ "
                    elif not right and left:
                        output += "← "
                    else:
                        output += "| "

                    output += check_space(col + 1, row)
                else:
                    output += "|\n"

            # Draw the bottom walls for the current row
            for col in range(len(self.Maze[row])):
                # check for block below, skip if on bottom row
                if row < len(self.Maze) - 1:
                    output += "-"
                    # Check for two way paths
                    down = self.traversable(col, row, col, row + 1)
                    up = self.traversable(col, row + 1, col, row)

                    if down and up:
                        output += "   "
                    elif down and not up:
                        output += " ↓ "
                    elif not down and up:
                        output += " ↑ "
                    else:
                        output += "---"
                else:
                    output += "----"
            output += "-\n"

        # Add the legend at the end
        return output + "Start: s\tEnd: e\tOne way paths: arrows\n"
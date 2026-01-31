

class Node:

    # this is more a data class that holds the information for the bot and the visualization to get the needed info from

    x: int
    y: int
    up: bool
    down: bool
    left: bool
    right: bool
    cost: int

    # class members
    # x, y => coords on the grid
    # up, down, left, right => if true means that direction is traversable, if false well u know
        # maybe can be made numbers with 0 indicating not traversable and anything else indicating cost

    def __init__(self, x, y, up=False, down=False, left=False, right=False, cost=0):
        self.x = x
        self.y = y
        self.up = up
        self.down = down
        self.left = left
        self.right = right
        self.cost = cost

    def set_direction(self, up, down, left, right):
        self.up = up
        self.down = down
        self.left = left
        self.right = right

    def __str__(self): # tostring method
        connections = ""
        if not (self.up or self.down or self.left or self.right):
            connections += "isolated node"
        else:
            connections += "traversable "
            if self.up:
                connections += "up "
            if self.down:
                connections += "down "
            if self.left:
                connections += "left "
            if self.right:
                connections += "right "
        return f"x: {self.x} y: {self.y} {connections}cost: {self.cost}"

    def get_up(self):
        return self.up
    def get_down(self):
        return self.down
    def get_left(self):
        return self.left
    def get_right(self):
        return self.right
    def is_isolated(self):
        return not (self.up or self.down or self.left or self.right)
    def get_cost(self):
        return self.cost
import heapq
import time
import tracemalloc

import Maze


class UCS:

    # regarding tree search
    # im guessing it means go down one path until a dead end is reached instead of the more holistic aggregate cost indexed heap
    # crucially with the visited array enabled

    execution_time: int # represented with miliseconds
    maze: Maze.Maze
    start: tuple[int, int]
    end: tuple[int, int]
    pathing: list[tuple[int, int]]
    text: bool # flag to define the return to be for gui or for text based terminals
    parent_map: dict[tuple[int, int], tuple[int, int]]
    visited: set

    def __init__(self, maze: Maze.Maze, search_type="Graph", text=False):

        # define the maze and the start and end of said maze
        self.execution_time = 0
        self.maze = maze
        self.start = (maze.startx, maze.starty)
        self.end = (maze.endx, maze.endy)
        self.parent_map = {}
        self.pathing = [self.start]
        self.search_type = search_type
        self.text = text
        self.temp = {}

    def search(self):
        start_time = time.time_ns() # start the timer
        tracemalloc.start()
        queue = [(0, self.start)] # open set
        self.parent_map[self.start] = None
        # dict to store shortest path to visited nodes
        self.visited = set() # closed set
        # succeeded = []
        while queue:
            # pops the node with the lowest cost from the queue
            current_cost, current_node = heapq.heappop(queue) # get info of the current node and pathing to get to the path

            self.visited.add(current_node) # add current node to visited

            # return the path and the cost of the path is goal is reached
            if current_node == self.end:
                # self.pathing += pathing
                # self.execution_time = time.time_ns() - start_time  # end the timer and save it within the object
                if self.text:
                    tracemalloc.stop()
                    return "UCS:\n" + str(self.maze) + "\nPath found with " + str(len(self.pathing)) + " steps with " + str(current_cost) + " cost\nFull path: " + str(self.pathing)
                else:
                    _, peak = tracemalloc.get_traced_memory()
                    yield current_node, f"current node: {str(current_node)}   current cost: {str(current_cost)}", time.time_ns() - start_time, peak

            # yielding current node to the GUI
            elif not self.text:
                _, peak = tracemalloc.get_traced_memory()
                yield current_node, f"current node: {str(current_node)}   current cost: {str(current_cost)}\nmem use: {peak}", time.time_ns() - start_time, peak

            start_time = time.time_ns()  # restart the timer

            # explore the neighbors
            neighbors = self.maze.get_traversable_array(current_node[0], current_node[1])
            for y in range(len(neighbors)):
                if neighbors[y]:
                    # it is expected that the maze used to run this does not have nodes that can travel into the void
                    # so we are not checking that here

                    # get next node
                    if y == 0: # up
                        next_node = (current_node[0], current_node[1] - 1)
                    elif y == 1: # down
                        next_node = (current_node[0], current_node[1] + 1)
                    elif y == 2: # left
                        next_node = (current_node[0] - 1, current_node[1])
                    else: # right
                        next_node = (current_node[0] + 1, current_node[1])

                    # when tree search dont check the visited list but still maintain it
                    if (not next_node in self.visited or self.search_type == "Tree") or next_node == self.end:
                        # succeeded.append(next_node)
                        if next_node not in self.parent_map:
                            self.parent_map[next_node] = current_node
                        # next_node_pathing = pathing + [next_node] # modify the pathing array
                        next_node_cost = current_cost + self.get_cost(current_node, next_node) # adds the cost to travel to the next node, default cost per node is 1

                        # if the current node is a deadend then dont push it into the queue
                        in_queue = False

                        # check if next node is already in queue, if so dont put it in again
                        for t in queue:
                            in_queue = t[1] == next_node
                            if in_queue:
                                break

                        if not in_queue:
                            heapq.heappush(queue, (next_node_cost, next_node)) # push the next node into the queue

        # yield for GUI
        if not self.text:
            tracemalloc.stop()
            yield None, "", 0, 0
        else:
            tracemalloc.stop()
            return "Path not found"

    # function to get the cost to traverse to a coord
    # current rules: base cost 1 (0 for one ways) + cost of bloc
    def get_cost(self, current_node, next_node):
        return (1 if self.maze.traversable(next_node[0], next_node[1], current_node[0], current_node[1]) else 0) + self.maze.get_node_cost(next_node[0], next_node[1])

    # Helper function to reconstruct path after search is complete
    def reconstruct_path(self):
        # This is called after the search finds the end uses the parent_map to work backwards from the end to the start
        path = []
        # Start from the end node
        current = self.end

        # If the end never added to the map no path found
        if self.end not in self.parent_map:
            return None

        # Loop backwards until start node, parent is None
        while current is not None:
            path.append(current)
            current = self.parent_map[current]

        # Reverse the path to be from start to end and return
        return path[::-1]

        # return self.pathing

    def get_time(self):
        if self.execution_time is None: # if there are no time saved run it once and get the time
            self.search()

        return self.execution_time
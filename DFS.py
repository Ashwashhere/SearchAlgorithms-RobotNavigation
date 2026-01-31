import Maze
import time 
import tracemalloc

# DFS Algorithm Implementation
class DFS: 
    
    # Intialise the DFS search object
    def __init__(self, maze: Maze.Maze, search_type="Graph"):
        self.maze = maze

        # Get start and end positions from the Maze object as tuples
        self.start = (maze.startx, maze.starty)
        self.end = (maze.endx, maze.endy)
        
        # Functions as a stack (LIFO) for DFS
        self.stack = []
        
        # Store visited nodes for Graph search, set for easy lookup
        self.visited = set()
        
        # A dictionary to rebuild the path after the search is done, stores {child_node: parent_node}
        self.parent_map = {}
        
        # Search toggle for Graph or Tree search, tree search can cause infinite loops
        self.search_type = search_type

        # Memory tracking variable
        self._mem_base = 0

    # Get valid neighbour nodes
    def get_neighbours(self, x, y):
        neighbours = []
        
        # Get the maze boundaries
        maze_width = self.maze.get_maze_x()
        maze_height = self.maze.get_maze_y()
        
        # Check up, if not at top edge and traversable
        if y > 0 and self.maze.traversable(x, y, x, y -1):
            neighbours.append((x, y - 1))
            
        # Check down, if not at bottom edge and traversable
        if y < maze_height - 1 and self.maze.traversable(x, y, x, y + 1):
            neighbours.append((x, y + 1))
            
        # Check left, if not at left edge and traversable
        if x > 0 and self.maze.traversable(x, y, x - 1, y):
            neighbours.append((x - 1, y))
            
        # Check right, if not at right edge and traversable
        if x < maze_width - 1 and self.maze.traversable(x, y, x + 1, y):
            neighbours.append((x + 1, y))
            
        return neighbours
    
    # Search as a generator, returns one step at a time allowing visualisation without freezing
    def search(self):
        # Start tracking memory if not already started
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        
        # Record the memory baseline
        self._mem_base, _ = tracemalloc.get_traced_memory()

        # Add the start node to the stack and set its parent to None
        self.stack.append(self.start) 
        self.parent_map[self.start] = None 

        # Loop while there are still nodes to explore in the stack
        while self.stack: 
            step_start = time.perf_counter_ns()
            
            # Get the next Node using pop for DFS
            current_node = self.stack.pop() 

            # Check if already visited this node in Graph search
            if self.search_type == "Graph":
                # if in visited, skip
                if current_node in self.visited:
                    continue 
                
                # If not visited mark as visited 
                self.visited.add(current_node)
            
            # For Tree search skip this check and just process the node
        
            # Measure time and memory for this step
            step_time = time.perf_counter_ns() - step_start
            
            cur_mem, _ = tracemalloc.get_traced_memory()
            used_mem = cur_mem - self._mem_base
            if used_mem < 0:
                used_mem = 0

            # Yield the current node for visualization, this pauses the function here so the visualiser can update
            yield current_node, "", step_time, used_mem


            # Check if we have reached the end and return
            if current_node == self.end:
                return 

            # Get neighbours of the current node as (x, y) tuples
            (x, y) = current_node
            neighbours = self.get_neighbours(x, y)

            # Add neighbors to Stack 
            for neighbour in neighbours:
                if self.search_type == "Graph":
                    # Graph logic, only add unvisited neighbors
                    if neighbour not in self.visited:
                        self.parent_map[neighbour] = current_node
                        self.stack.append(neighbour)
                else:
                    # Tree logic, add all neighbors except the parent
                    if neighbour != self.parent_map.get(current_node):
                        self.parent_map[neighbour] = current_node
                        self.stack.append(neighbour)
                        
        # If stack is empty and end not found yield None to indicate failure
        yield None, "", 0, 0

    # Helper function to reconstruct path after search is complete
    def reconstruct_path(self):
        # This  is called after the search finds the end uses the parent_map to work backwards from the end to the start
        path = []
        # Start from the end node
        current = self.end 
    
        # If the end never added to the map no path found
        if self.end not in self.parent_map:
            return None 
        
        # Loop backwards until start node, parent is None
        while current is not None:
            # Add the current node to the path
            path.append(current) 
            # Move to the parent node
            current = self.parent_map[current] 
    
        # Reverse the path to be from start to end and return
        return path[::-1]
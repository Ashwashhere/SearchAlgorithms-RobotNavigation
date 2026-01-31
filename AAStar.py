import heapq
import time
import Maze
import tracemalloc

# A* Algorithm Implementation
class AAStar:

    # Set up the A* search object
    def __init__(self, maze: Maze.Maze, search_type="Graph"):

        self.maze = maze

        # Coordinates for the start and goal
        self.start = (maze.startx, maze.starty)
        self.end = (maze.endx, maze.endy)

        # The Open Set: We use a list, but treat it as a min-heap (priority queue)
        """
        Update: I have figured out why the algorithm has inconsistent speeds and significantly slows down in the Tree variant.
        
        Every time we add a node to the min-heap, it has to maintain its sorted property.
        This has a computational complexity of O(log N), whereas for BFS and DFS, adding a node is O(1).
        In the Tree Search variant, we lack the 'visited' set, which causes the heap (N) to grow very large with duplicate entries (due to revisiting nodes via cycles).
        
        The Logarithmic Cost creates inconsistent speed:
        
        * Small Heap (Start): When N is small (e.g. N=10), a push operation is fast (e.g. log2(10), which is approximately 3.3 operations).
        * Large Heap (Cycles): When N explodes due to cycles (e.g. N=10,000), the push operation is much slower (e.g. log2(10,000), which is approximately 13.3 operations).
        
        Thus, this variable cost (driven by heap size), is what makes the speed feel inconsistent.
        
        ---
        
        Why A* is more inconsistent than UCS?
        
        UCS suffers from the same O(log N) heap overhead, however, its expansion pattern makes the slowness less noticeable:
        
        * UCS (Consistent): UCS uses only the G-Score (path cost). 
            Since every step has a constant cost (1), UCS expands nodes in smooth and predictable, outward rings shape. 
            Therefore, O(log N) cost increases gradually and is absorbed uniformly across the search.
        * A* (Inconsistent): A* uses the F-Score (f = g + h), which is GREEDY and disruptive.
            A* prioritizes a low f-score. When it re-visits a node (Node X) via a long and cyclical path, it pushes that duplicate Node X onto the heap with a high f-score.
            This high f-score duplicate sits there until the heap size (N) is massive. 
            When the algorithm finally pops this expensive and outdated entry, it happens during a peak N.
            ultimately, causing a noticeable and choppy slowdown.
        
        Note on UCS Code: The UCS script doesn't solve the heap bloat.
        It simply hides the O(log N) slowdown better due to its uniform G-Score expansion.
        """
        self.open_list = []

        # G-Score: Tracks the actual cost from the start to any node we've found so far
        self.g_score = {}

        # Parent Map: How we rebuild the path. Maps child -> parent
        self.parent_map = {}

        # Visited/Closed Set: Only used for Graph Search to avoid re-exploring nodes
        # A set is best here for instant lookups (O(1))
        self.visited = set()

        # Search toggle for "Graph" (default and prevents cycles) or "Tree" (allows for cycles)
        self.search_type = search_type

        # baseline for per-run memory delta
        self._mem_base = 0

    # --- Helper methods -------------------------------------------------

    def heuristic(self, node):

        """"""
        """
        Calculates the estimated remaining cost (h-score) from the current node to the goal.

        We use Manhattan distance (grid travel) because all moves are straight
        and cost 1. Thus, ensuring that our estimate is always optimistic (admissible).
        """
        (x, y) = node
        (gx, gy) = self.end
        return abs(x - gx) + abs(y - gy)

    def get_neighbours(self, x, y):

        # Finds all adjacent tiles that are within the maze boundaries and that are traversable

        neighbours = []

        maze_width = self.maze.get_maze_x()
        maze_height = self.maze.get_maze_y()

        # Defines the 4 possible move changes: (dx, dy)
        cardinal_moves = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # Up, Down, Left, Right

        for dx, dy in cardinal_moves:
            nx, ny = x + dx, y + dy  # New x, New y

            # Check boundaries first
            if 0 <= nx < maze_width and 0 <= ny < maze_height:
                # Check traversability
                if self.maze.traversable(x, y, nx, ny):
                    neighbours.append((nx, ny))

        return neighbours

    # --- Core search ----------------------------------------------------

    # Main A* loop
    def search(self):

        # Ensure tracemalloc is running (visualiser *should* do this, but this makes A* robust)
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        # Baseline at the start of THIS run
        self._mem_base, _ = tracemalloc.get_traced_memory()

        # Implemented as a generator to feed steps to a visualiser
        # Yields (current_node, info_text, time_taken_ns) on each step

        # Set up the starting node's scores and push it onto the heap
        self.g_score[self.start] = 0.0
        f_start = self.heuristic(self.start)
        # Heap item structure: (f_score, g_score, node)
        heapq.heappush(self.open_list, (f_start, 0.0, self.start))
        self.parent_map[self.start] = None  # Start has no parent

        # Main search loop: continue while there are nodes to explore
        while self.open_list:
            step_start = time.perf_counter_ns()

            # Pop the node with the lowest f-score (best estimate)
            f_current, g_current, current_node = heapq.heappop(self.open_list)

            # In Graph Search, we might have added this node before with a worse path
            # If it's already visited, skip this outdated heap entry
            if self.search_type == "Graph" and current_node in self.visited:
                continue

            # Mark node as visited after processing its neighbours, if we were doing Tree Search
            # For Graph Search, we mark it now
            if self.search_type == "Graph":
                self.visited.add(current_node)

            step_time = time.perf_counter_ns() - step_start

            # Memory in BYTES (delta since run start)
            cur_mem, _ = tracemalloc.get_traced_memory()
            mem_delta = cur_mem - self._mem_base
            if mem_delta < 0:
                mem_delta = 0

            # Send the current node back to the visualiser
            yield current_node, "", step_time, mem_delta

            # Success (found the goal)
            if current_node == self.end:
                return

            # Explore all valid neighbours
            (x, y) = current_node
            neighbours = self.get_neighbours(x, y)

            for neighbour in neighbours:
                # Tree-search: don't immediately backtrack to the parent
                if self.search_type == "Tree" and neighbour == self.parent_map.get(current_node):
                    continue

                # Calculate the cost to reach this neighbour through the current path
                tentative_g = self.g_score.get(current_node, g_current) + self.maze.get_node_cost(neighbour[0], neighbour[1])

                # Graph Search Optimisation: If our new path (tentative_g) is worse than or
                # equal to the best path we've already found, ignore it
                if self.search_type == "Graph" and tentative_g >= self.g_score.get(neighbour, float("inf")):
                    continue

                # We found a better path -> Record it.
                self.parent_map[neighbour] = current_node
                self.g_score[neighbour] = tentative_g
                f_neighbour = tentative_g + self.heuristic(neighbour)

                # Push the new, better path onto the heap
                heapq.heappush(self.open_list, (f_neighbour, tentative_g, neighbour))

        # If the open list runs out before the goal is reached, the search failed
        yield None, "", 0, 0

    # --- Path reconstruction --------------------------------------------

    def reconstruct_path(self):

        #Walks backward from the end node using the parent_map to build the final path
        #Returns the path list (start to end) or None if the goal wasn't reached
        path = []
        current = self.end

        # Safety check: if the end node isn't in the map, no path exists
        if current not in self.parent_map:
            return None

        while current is not None:
            path.append(current)
            current = self.parent_map[current]

        # Path was built backwards, so we flip it
        return path[::-1]
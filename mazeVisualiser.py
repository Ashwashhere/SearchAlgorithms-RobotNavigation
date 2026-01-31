import secrets
import gc
import tkinter as tk
import tracemalloc
# --------- (Aiman) -----------------
import base64
import json
import csv
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
# ------------------------------------
from tkinter import ttk, StringVar, IntVar, filedialog
import Maze
import DFS
import BFS
import UCS
import AAStar

# import AStar (search needs to be changed to a generator first)


# -------- (Aiman) ----------------------------
# If we do change the seed format, we should increase the version
SEED_PREFIX = "MZ1:"  # Somewhat redundant with the version in the payload, so we can change it to just "MZ" if we really want

# Base64 is used so we can convert bytes into strings
def _seed_padding(b64: str):
    # Restores base64 padding (=) for urlsafe decoding, as base64 strings length needs to be a multiple of 4
    return "=" * (-len(b64) % 4)

# We use encoding and decoding so we can easily change the seed to include more data, e.g. max/min cost
def encode_seed_token(*, rng_seed, wall_percentage: int, oneway_percentage: int):
    # When the same token is used again, the maze + settings are reproducible
    payload = {
        "v": 1,  # V stands for version
        "rng": str(rng_seed),
        "wall": int(wall_percentage),
        "oneway": int(oneway_percentage),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"{SEED_PREFIX}{token}"


def decode_seed_token(seed_text: str):
    # Returns a dict if valid, otherwise None

    if not isinstance(seed_text, str):
        return None
    seed_text = seed_text.strip()
    if not seed_text.startswith(SEED_PREFIX):
        return None

    try:
        token = seed_text[len(SEED_PREFIX):]
        raw = base64.urlsafe_b64decode(token + _seed_padding(token))
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return None

    # Basic validation
    if payload.get("v") != 1:
        return None
    if "rng" not in payload or "wall" not in payload or "oneway" not in payload:
        return None

    return payload

@dataclass
class RunMetrics:
    """Lightweight container for one search run's results (manual or batch)."""

    algo_choice: str
    search_type: str
    status: str  # success/fail/timeout/error/stopped
    steps: int
    unique_visited: int
    repeats: int
    reported_time_ns: int
    wall_time_ns: int
    avg_mem_bytes: float
    path_len: Optional[int] = None
# ------------------------------------

# Maze Visualizer Class
class MazeVisualizer:

    # Configuration
    # Size of each grid cell in pixels
    cell_size = 40
    # Thickness of maze walls in pixels
    wall_thickness = 3

    # --------- (Aiman) -----------------
    # Safeguards for batch mode (prevents Tree search from looping forever)
    DEFAULT_MAX_STEPS_TREE = 200_000
    DEFAULT_MAX_STEPS_GRAPH = 50_000
    # ------------------------------------

    # Initialises the visualiser, root = tkinter root window, maze_data = 4D list of maze walls,
    # start_coords = (x,y) tuple for start, end_coords = (x,y) tuple for end, animation_delay for the base delay in milliseconds for search step (i.e. the delay when clicking the play button)
    def __init__(self, root, maze_data, start_coords, end_coords, animation_delay = 20):

        # Main tkinter window
        self.root = root

        # --------- (Aiman) -----------------
        # Ensure tracemalloc is active (for memory stats in batch results)
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        self._run_mem_baseline = 0
        # ------------------------------------

        # Create the Maze object
        self.maze = Maze.Maze(maze_data,
                              start_coords[0], start_coords[1],
                              end_coords[0], end_coords[1])

        # stores animation delay, aka delay between search steps
        self.animation_delay = animation_delay

        # Store (x, y) tuples for the start and goal
        self.start_node = (self.maze.startx, self.maze.starty)
        self.goal_node = (self.maze.endx, self.maze.endy)

        # A variable to store last visited node
        self.last_node = self.start_node

        # String variable for algorithms to display information if needed
        self.canvas_legend = "Green: Start   Red: Goal   Blue: Visiting   Cyan: Visited\nRed: Visiting repeated   Orange: Visited repeated"
        self.search_text_display = StringVar()
        self.search_text_display.set(self.canvas_legend)

        # variable to store the aggregate execution time for search algorithms
        # NOTE: by default it takes in nanoseconds to ensure better precision and to present it in milliseconds to add readability
        self.search_execution_time = 0

        # Visited list to store visited coords
        self.visited = {}
        self.last_node_repeated = False

        # List to keep memory use reports from algorithm
        self.mem_use_record = []

        # --------- (Aiman) -----------------
        # Internal run bookkeeping (used by batch testing)
        self._on_search_complete = None
        self._run_step_count = 0
        self._run_repeat_count = 0
        self._run_start_perf_ns = 0
        self._run_algo_choice = ""
        self._run_search_type = ""
        self._run_max_steps = None

        # Optional time limit for batch/replay runs (nanoseconds)
        self._run_time_limit_ns = None

        # Batch testing state
        self._batch_running = False
        self._batch_stop_requested = False

        # Batch runner mode:
        #   - "random": generate random mazes
        #   - "replay": replay mazes from a seeds file
        self._batch_mode = "random"
        # Replay state
        self._batch_replay_tokens = []
        self._batch_replay_index = 0
        self._batch_algo_list = []
        self._batch_algo_index = 0
        self._batch_total_target = 0
        self._batch_completed = 0
        self._batch_current_run_id = 0
        self._batch_current_token = ""
        self._batch_current_rng_seed = ""
        self._batch_current_wall = 0
        self._batch_current_oneway = 0
        self._batch_csv_fh = None
        self._batch_seed_fh = None
        self._batch_csv_writer = None
        self._batch_csv_path = ""
        self._batch_seed_path = ""
        self._batch_prev_algo_choice = ""
        # ------------------------------------

        # controls how likely walls and one ways will be generated when randomized
        # for obvious reasons dont set them too high or you will get a lot of dead mazes
        self.wall_percentage = IntVar()
        self.wall_percentage.set(10)
        self.oneway_percentage = IntVar()
        self.oneway_percentage.set(10)

        # ------- (Aiman) ---------------
        # Seed controls (reproducibility)
        self.seed_var = tk.StringVar(value = "")
        self.seed_locked_var = tk.BooleanVar(value = False)
        # -------------------------------

        # State variables for the search
        # Search algorithm instance e.g. BFS or DFS
        self.search_instance = None
        # Search generator for step by step execution
        self.search_generator = None
        # Flag to stop animation loop if reset is pressed
        self.search_running = False
        # Flag to signify animation pause state
        self.search_paused = False
        # NOTE: the 2 flags below should not require resetting after canvas reset, as each click of the speed buttons should set them correctly already
        # Flag to show fast-forward state
        self.search_fast_forward = False
        # Flag to show max speed state
        self.search_max_speed = False

        # GUI Setup
        # Set the window title
        self.root.title("Maze Search Visualiser")

        # Create frame widget to hold the controls buttons and dropdown
        self.line_one = ttk.Frame(root)
        self.line_two = ttk.Frame(root)
        # --------- (Aiman) -------------
        self.line_three = ttk.Frame(root)
        self.line_four = ttk.Frame(root)
        self.line_five = ttk.Frame(root)
        # ------------------------------------
        self.line_six = ttk.Frame(root)

        # Pack the frame with vertical padding
        self.line_one.pack(pady=10)
        self.line_two.pack(pady=10)
        # --------- (Aiman) -------------
        self.line_three.pack(pady=5)
        self.line_four.pack(pady=5)
        self.line_five.pack(pady=5)
        # -------------------------------
        self.line_six.pack(pady=5)

        # LINE 1
        # Label for the dropdown menu
        self.algo_label = ttk.Label(self.line_one, text="Algorithm:")
        # Pack the label to the left side with horizontal padding
        self.algo_label.pack(side=tk.LEFT, padx=5)

        # Dropdown menu to select search algorithm
        # Variable to hold the selected option
        self.algo_var = tk.StringVar(value="BFS")

        # List of options for the dropdown
        options = ["BFS (Graph)", "DFS (Graph)", "UCS (Graph)", "AStar (Graph)", "BFS (Tree)", "DFS (Tree)", "UCS (Tree)", "AStar (Tree)"]

        # --------- (Aiman) -----------------
        # Keep a copy of the algorithm labels for batch testing
        self._algo_options = list(options)
        # ------------------------------------

        # OptionMenu widget for algorithm selection
        self.algo_menu = ttk.OptionMenu(self.line_one, self.algo_var, options[0], *options)
        # Pack the dropdown to the left side with horizontal padding
        self.algo_menu.pack(side=tk.LEFT, padx=5)

        # Pause search button
        # flips the pause flag if the search has started
        self.pause_button = ttk.Button(self.line_one, text="⏸", command=self.pause_search, width=2)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        # Play button
        # Command calls the start_resume_search method
        self.start_button = ttk.Button(self.line_one, text="▶", command=self.start_resume_search, width=2)
        # Pack the button to the left side with horizontal padding
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))

        # Fast-forward button
        # flips the speed control flags to show fast-forward state
        self.pause_button = ttk.Button(self.line_one, text="⏩", command=self.search_fasten, width=2)
        self.pause_button.pack(side=tk.LEFT, padx=(0, 5))

        # Max speed button
        # flips the speed control flags to show max speed state
        # NOTE: i am not very happy with the Unicode char I am using here, suggest alternatives if u got a better one :3
        self.pause_button = ttk.Button(self.line_one, text="⏭", command=self.search_max, width=2)
        self.pause_button.pack(side=tk.LEFT, padx=(0, 5))

        # Reset button
        # Command calls the reset method
        self.reset_button = ttk.Button(self.line_one, text="Reset", command=self.reset, width=5)
        # Pack the button to the left side with horizontal padding
        self.reset_button.pack(side=tk.LEFT, padx=5)

        """ OLD
        # Randomize maze button
        # Runs the randomize environment function
        self.randomize_button = ttk.Button(self.line_one, text="Generate", command=self.randomize_maze, width=20)
        self.randomize_button.pack(side=tk.LEFT, padx=5)
        """
        # ------ (Aiman) --------
        self.generate_button = ttk.Button(self.line_one, text="Generate", command=self.generate_maze, width=12)
        self.generate_button.pack(side=tk.LEFT, padx=5)
        # -----------------------
        # LINE 1 end

        # LINE 2

        # Text to show what the first slider is
        self.wall_slider_label = ttk.Label(self.line_two, text="Wall percentage:")
        self.wall_slider_label.pack(side=tk.LEFT, padx=5) # item 1 is slider 1 description

        # Text to show what the current value of the sliders are
        # have to be declared before the sliders themselves as the sliders reference these 2 during their declarations, sorry :3
        self.wall_slider_display = ttk.Label(self.line_two, text=f"{self.wall_percentage.get()}%", width=4)
        self.oneway_slider_display = ttk.Label(self.line_two, text=f"{self.oneway_percentage.get()}%", width=4)

        # The sliders themselves, one for adjusting how many walls and the other for adjusting how many one-ways
        self.wall_slider = ttk.Scale(self.line_two, orient=tk.HORIZONTAL, from_=0, to=100-self.oneway_percentage.get())
        self.wall_slider.set(self.wall_percentage.get())
        self.oneway_slider = ttk.Scale(self.line_two, orient=tk.HORIZONTAL, from_=0, to=100 - self.wall_percentage.get(), command=self.update_sliders)
        self.oneway_slider.set(self.oneway_percentage.get())
        self.wall_slider.config(command=self.update_sliders) # tacking this onto slider 1 at this point to prevent circular referencing

        self.wall_slider.pack(side=tk.LEFT, padx=5) # item 2 is slider 1

        self.wall_slider_display.pack(side=tk.LEFT, padx=5) # item 3 is display for slider 1

        # Text to show what second slider is
        self.oneway_slider_label = ttk.Label(self.line_two, text="One-way percentage:")
        self.oneway_slider_label.pack(side=tk.LEFT, padx=5) # item 4 is slider 2 description

        self.oneway_slider.pack(side=tk.LEFT, padx=5) # item 5 is slider 2

        self.oneway_slider_display.pack(side=tk.LEFT, padx=5) # item 6 is slider 2 display

        # ---------------- (Aiman) -----------------
        # LINE 3 - Seeding controls (reproducibility)
        self.seed_label = ttk.Label(self.line_three, text="Seed:")
        self.seed_label.pack(side=tk.LEFT, padx=(5, 2))

        # Copy/paste seed box
        self.seed_entry = ttk.Entry(self.line_three, textvariable=self.seed_var, width=48)
        self.seed_entry.pack(side=tk.LEFT, padx=5)

        # Lock toggle: when enabled, clicking Generate will reuse the seed in the box
        self.seed_lock_toggle = ttk.Checkbutton(self.line_three, text="Use seed", variable=self.seed_locked_var)
        self.seed_lock_toggle.pack(side=tk.LEFT, padx=5)

        # Quality-of-life: quick copy
        self.copy_seed_button = ttk.Button(self.line_three, text="Copy", command=self.copy_seed_to_clipboard, width=6)
        self.copy_seed_button.pack(side=tk.LEFT, padx=(0, 5))

        # Batch test controls (runs all algorithms on many random mazes)
        self.batch_count_var = tk.IntVar(value=10)
        self.batch_wall_max_var = tk.IntVar(value=30)
        self.batch_oneway_max_var = tk.IntVar(value=30)
        self.batch_between_algo_delay_ms_var = tk.IntVar(value=0)

        # Per-algorithm time limit (seconds) for batch + replay (default: 3 minutes)
        # NOTE: This is intentionally a StringVar so invalid user input won't crash Tk.
        self.batch_time_limit_seconds_var = tk.StringVar(value="180")

        # Replay file path (seeds file generated by batch mode)
        self.replay_seed_file_var = tk.StringVar(value="")

        self.batch_status_var = tk.StringVar(value="")

        # LINE 4 - Batch run settings
        ttk.Label(self.line_four, text="Batch:").pack(side=tk.LEFT, padx=(5, 2))
        ttk.Label(self.line_four, text="Mazes").pack(side=tk.LEFT)
        self.batch_count_entry = ttk.Entry(self.line_four, textvariable=self.batch_count_var, width=5)
        self.batch_count_entry.pack(side=tk.LEFT, padx=(2, 8))

        ttk.Label(self.line_four, text="Wall max% ").pack(side=tk.LEFT)
        self.batch_wall_max_entry = ttk.Entry(self.line_four, textvariable=self.batch_wall_max_var, width=5)
        self.batch_wall_max_entry.pack(side=tk.LEFT, padx=(2, 8))

        ttk.Label(self.line_four, text="One-way max% ").pack(side=tk.LEFT)
        self.batch_oneway_max_entry = ttk.Entry(self.line_four, textvariable=self.batch_oneway_max_var, width=5)
        self.batch_oneway_max_entry.pack(side=tk.LEFT, padx=(2, 8))

        ttk.Label(self.line_four, text="Pause(ms)").pack(side=tk.LEFT)
        self.batch_pause_entry = ttk.Entry(self.line_four, textvariable=self.batch_between_algo_delay_ms_var, width=6)
        self.batch_pause_entry.pack(side=tk.LEFT, padx=(2, 8))


        # Time limit entry (seconds) - applies to each algorithm in batch/replay runs
        ttk.Label(self.line_four, text="Time limit(s)").pack(side=tk.LEFT)
        self.batch_time_limit_entry = ttk.Entry(self.line_four, textvariable=self.batch_time_limit_seconds_var, width=7)
        self.batch_time_limit_entry.pack(side=tk.LEFT, padx=(2, 8))


        self.batch_start_button = ttk.Button(self.line_four, text="Run batch", command=self.start_batch_tests, width=9)
        self.batch_start_button.pack(side=tk.LEFT, padx=(0, 5))

        self.batch_stop_button = ttk.Button(self.line_four, text="Stop", command=self.stop_batch_tests, width=6,
                                            state=tk.DISABLED)
        self.batch_stop_button.pack(side=tk.LEFT, padx=(0, 8))

        # LINE 5 - Replay batch controls
        ttk.Label(self.line_five, text="Replay seeds file:").pack(side=tk.LEFT, padx=(5, 2))
        self.replay_seed_entry = ttk.Entry(self.line_five, textvariable=self.replay_seed_file_var, width=46)
        self.replay_seed_entry.pack(side=tk.LEFT, padx=5)

        self.replay_browse_button = ttk.Button(self.line_five, text="Browse", command=self.browse_replay_file, width=8)
        self.replay_browse_button.pack(side=tk.LEFT, padx=(0, 5))

        self.replay_start_button = ttk.Button(self.line_five, text="Run replay", command=self.start_replay_from_file,
                                              width=9)
        self.replay_start_button.pack(side=tk.LEFT, padx=(0, 5))
        # ------------------------------------

        # LINE 5 - Batch status text
        self.batch_status_label = ttk.Label(self.line_six, textvariable=self.batch_status_var)
        self.batch_status_label.pack(side=tk.LEFT, padx=5)

        # Canvas Setup
        # Get the dimensions of maze in grid units
        self.map_height = self.maze.get_maze_y()
        self.map_width = self.maze.get_maze_x()

        # Calculate the pixel size for the canvas based on cell size
        canvas_height = self.map_height * self.cell_size
        canvas_width = self.map_width * self.cell_size

        # Create the Canvas widget, where all the drawing will happen
        self.canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg='white', relief='solid', borderwidth=1)
        # Pack the canvas with padding
        self.canvas.pack(padx=10, pady=10)

        self.textbox = tk.Label(root, textvariable=self.search_text_display)
        self.textbox.pack(pady=5)

        # Draw the initial maze state on the canvas
        self.draw_initial_map()

    # Drawing Helpers
    # Gets the pixel coordinates for a given grid cell
    def get_canvas_coords(self, x, y):
        # Converts grid coordinates to pixel coordinates
        x0 = x * self.cell_size
        y0 = y * self.cell_size
        x1 = x0 + self.cell_size
        y1 = y0 + self.cell_size
        return x0, y0, x1, y1

    def draw_arrow(self, x1, y1, x2, y2, colour="black"):  # only able to draw horizontal and vertical arrows
        ARROW_TIP_OFFSET = 7
        self.canvas.create_line(x1, y1, x2, y2, width=self.wall_thickness / 2, fill=colour)

        if y1 == y2:
            if x1 < x2:
                self.canvas.create_line(x2, y2, x2 - ARROW_TIP_OFFSET, y2 + ARROW_TIP_OFFSET, width=self.wall_thickness / 2,
                                   fill=colour)
                self.canvas.create_line(x2, y2, x2 - ARROW_TIP_OFFSET, y2 - ARROW_TIP_OFFSET, width=self.wall_thickness / 2,
                                   fill=colour)
            elif x1 > x2:
                self.canvas.create_line(x2, y2, x2 + ARROW_TIP_OFFSET, y2 + ARROW_TIP_OFFSET, width=self.wall_thickness / 2,
                                   fill=colour)
                self.canvas.create_line(x2, y2, x2 + ARROW_TIP_OFFSET, y2 - ARROW_TIP_OFFSET, width=self.wall_thickness / 2,
                                   fill=colour)
        elif x1 == x2:
            if y1 < y2:
                self.canvas.create_line(x2, y2, x2 - ARROW_TIP_OFFSET, y2 - ARROW_TIP_OFFSET, width=self.wall_thickness / 2,
                                   fill=colour)
                self.canvas.create_line(x2, y2, x2 + ARROW_TIP_OFFSET, y2 - ARROW_TIP_OFFSET, width=self.wall_thickness / 2,
                                   fill=colour)
            elif y1 > y2:
                self.canvas.create_line(x2, y2, x2 - ARROW_TIP_OFFSET, y2 + ARROW_TIP_OFFSET, width=self.wall_thickness / 2,
                                   fill=colour)
                self.canvas.create_line(x2, y2, x2 + ARROW_TIP_OFFSET, y2 + ARROW_TIP_OFFSET, width=self.wall_thickness / 2,
                                   fill=colour)
        else:
            raise ValueError("diagonal arrows are not supported")

    # Draws the initial maze layout on the canvas
    def draw_initial_map(self):
        ARROW_OFFSET = 0.3

        # Clear the canvas
        self.canvas.delete("all")

        # Draw Start and End markers
        # self.draw_cell_content(self.start_node[0], self.start_node[1], "S", "green")
        # self.draw_cell_content(self.goal_node[0], self.goal_node[1], "E", "red")

        for y in range(self.map_height):
            for x in range(self.map_width):
                if self.start_node == (x, y):
                    self.draw_cell_content(x, y, "S", "green")
                elif self.goal_node == (x, y):
                    self.draw_cell_content(x, y, "E", "red")
                elif (x, y) in self.visited:
                    if self.visited[(x, y)]:
                        self.draw_cell_content(x, y, str(self.maze.get_node_cost(x, y)), "orange")
                    else:
                        self.draw_cell_content(x, y, str(self.maze.get_node_cost(x, y)), "cyan")
                else:
                    self.draw_cell_content(x, y, str(self.maze.get_node_cost(x, y)))

        # Loop through every cell in the grid
        for y in range(self.map_height):
            for x in range(self.map_width):
                # Get the pixel coordinates
                x0, y0, x1, y1 = self.get_canvas_coords(x, y)

                # Get the walls for this cell
                traversable = self.maze.get_traversable_array(x, y)

                # Draw walls
                #  Draw up wall
                if not traversable[0]:
                    if y != 0 and self.maze.traversable(x, y - 1, x, y): # draw down arrows
                        self.draw_arrow(x1 - self.cell_size / 2, y1 - self.cell_size * 1.5 + self.cell_size * ARROW_OFFSET, x1 - self.cell_size / 2, y1 - self.cell_size / 2 - self.cell_size * ARROW_OFFSET)
                    else:
                        self.canvas.create_line(x0, y0, x1, y0, fill='black', width=self.wall_thickness)
                # Draw down wall
                if not traversable[1]:
                    if y != self.map_height - 1 and self.maze.traversable(x, y + 1, x, y): # draw up arrows
                        self.draw_arrow(x1 - self.cell_size / 2, y1 + self.cell_size / 2 - self.cell_size * ARROW_OFFSET, x1 - self.cell_size / 2, y1 - self.cell_size / 2 + self.cell_size * ARROW_OFFSET)
                    else:
                        self.canvas.create_line(x0, y1, x1, y1, fill='black', width=self.wall_thickness)
                # Draw left wall
                if not traversable[2]:
                    if x != 0 and self.maze.traversable(x - 1, y, x, y): # draw right arrow
                        self.draw_arrow(x1 - self.cell_size * 1.5 + self.cell_size * ARROW_OFFSET, y1 - self.cell_size / 2, x1 - self.cell_size + self.cell_size * ARROW_OFFSET, y1 - self.cell_size / 2)
                    else:
                        self.canvas.create_line(x0, y0, x0, y1, fill='black', width=self.wall_thickness)
                # Draw right wall
                if not traversable[3]:
                    if x != self.map_width - 1 and self.maze.traversable(x + 1, y, x, y): # draw left arrow
                        self.draw_arrow(x1 + self.cell_size / 2 - self.cell_size * ARROW_OFFSET,
                                        y1 - self.cell_size / 2, x1 - self.cell_size / 2 + self.cell_size * ARROW_OFFSET,
                                        y1 - self.cell_size / 2)
                    else:
                        self.canvas.create_line(x1, y0, x1, y1, fill='black', width=self.wall_thickness)

    # Cell content drawing helper
    def draw_cell_content(self, x, y, text=None, color=None):
        # Helper to draw text or colored square in a cell
        x0, y0, x1, y1 = self.get_canvas_coords(x, y)

        if color:
            # Add padding so color is inside walls
            pad = self.wall_thickness + 2
            self.canvas.create_rectangle(x0 + pad, y0 + pad, x1 - pad, y1 - pad,
                                         fill=color, outline='', tags="cell_content")
        if text:
            # Find center of the cell to draw text
            self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2,
                                    text=text, font=("Arial", 16, "bold"), fill="black", tags="cell_content")

    # Reset button logic
    def reset(self):
        # Stops any ongoing search and reset maze display
        self.search_running = False

        # Safely close the search generator if its running
        if self.search_generator:
            try: self.search_generator.close()
            except GeneratorExit: pass

        # Clear state variables
        self.search_generator = None
        self.search_instance = None

        # Reset state variables
        self.last_node = self.start_node
        self.search_paused = False
        self.search_text_display.set(self.canvas_legend)
        self.visited = {}
        self.last_node_repeated = False
        self.search_execution_time = 0
        # ---- (Aiman) -------
        self.mem_use_record = []  # reset per-run memory samples
        # ---------------------

        # Re-enable Start button
        self.algo_menu.config(state=tk.NORMAL)

        # Redraw original maze
        self.draw_initial_map()

# --------- (Aiman) ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _create_search_instance(self, algo_choice: str):
        """Create a search instance based on the dropdown label."""
        search_type = "Graph"
        if "(Tree)" in algo_choice:
            search_type = "Tree"
            print("Warning: Tree Search may cause an infinite loop!")

        if "BFS" in algo_choice:
            return BFS.BFS(self.maze, search_type), search_type
        elif "DFS" in algo_choice:
            return DFS.DFS(self.maze, search_type), search_type
        elif "UCS" in algo_choice:
            return UCS.UCS(self.maze, search_type), search_type
        elif "AStar" in algo_choice:
            return AAStar.AAStar(self.maze, search_type), search_type

        raise ValueError(f"Unknown algorithm: {algo_choice}")

    def _start_search(
            self,
            algo_choice: str,
            *,
            on_complete: Optional[Callable[[RunMetrics], None]] = None,
            max_steps: Optional[int] = None,
            force_max_speed: bool = False,
    ):
        """Start a search run.

        This is used by both the UI (manual runs) and the batch tester.
        """

        # Reset board and start the search animation loop
        self.reset()
        self.search_running = True
        self.search_paused = False

        gc.collect()  # reduces noise
        self._run_mem_baseline = tracemalloc.get_traced_memory()[0]

        # Disable menu button while search is running
        self.algo_menu.config(state=tk.DISABLED)

        # Create search instance + generator
        self.search_instance, search_type = self._create_search_instance(algo_choice)
        self.search_generator = self.search_instance.search()

        # Bookkeeping for metrics + batch callbacks
        self._on_search_complete = on_complete
        self._run_step_count = 0
        self._run_repeat_count = 0
        self._run_start_perf_ns = time.perf_counter_ns()
        self._run_algo_choice = algo_choice
        self._run_search_type = search_type
        self._run_max_steps = max_steps

        # Apply a per-algorithm time limit only during batch/replay runs.
        # Manual visual runs remain unchanged (no time cap) unless you want to extend it later.
        self._run_time_limit_ns = self._get_batch_time_limit_ns() if getattr(self, "_batch_running", False) else None


        if force_max_speed:
            self.search_fast_forward = False
            self.search_max_speed = True

        self.run_search_step()

    def _finish_search(self, *, status: str):
        """Stop the current search and (if set) emit RunMetrics to the callback."""
        self.search_running = False

        # Close generator safely
        if self.search_generator:
            try:
                self.search_generator.close()
            except Exception:
                pass

        self.search_generator = None

        # Re-enable menu only when not batching
        if not getattr(self, "_batch_running", False):
            self.algo_menu.config(state=tk.NORMAL)

        # Build metrics
        wall_time_ns = 0
        if self._run_start_perf_ns:
            try:
                wall_time_ns = max(0, time.perf_counter_ns() - int(self._run_start_perf_ns))
            except Exception:
                wall_time_ns = 0

        reported_time_ns = int(self.search_execution_time or 0)
        if reported_time_ns < 0:
            reported_time_ns = 0

        unique_visited = len(self.visited) if isinstance(self.visited, list) else 0

        avg_mem = 0.0
        if self.mem_use_record:
            try:
                avg_mem = float(sum(self.mem_use_record) / len(self.mem_use_record))
            except Exception:
                avg_mem = 0.0
        if avg_mem < 0:
            avg_mem = 0.0

        path_len = None
        if status == "success" and getattr(self.search_instance, "search_type", "") != "Tree":
            try:
                path = self.search_instance.reconstruct_path()
                if path:
                    path_len = max(0, len(path) - 1)
            except Exception:
                path_len = None

        metrics = RunMetrics(
            algo_choice=str(self._run_algo_choice or ""),
            search_type=str(self._run_search_type or ""),
            status=str(status),
            steps=int(self._run_step_count or 0),
            unique_visited=int(unique_visited),
            repeats=int(self._run_repeat_count or 0),
            reported_time_ns=int(reported_time_ns),
            wall_time_ns=int(wall_time_ns),
            avg_mem_bytes=float(avg_mem),
            path_len=path_len,
        )

        cb = self._on_search_complete
        self._on_search_complete = None
        if cb is not None:
            try:
                cb(metrics)
            except Exception as e:
                print(f"Batch callback error: {e}")

    def _set_controls_enabled(self, enabled: bool):
        """Enable/disable UI controls (prevents user interference during batch)."""
        state = tk.NORMAL if enabled else tk.DISABLED

        # Disable most widgets in our control lines
        # Include line 4 (batch controls) + line 5 (replay controls) too.
        # Stop button is re-enabled explicitly below while a batch is running.
        for frame in (self.line_one, self.line_two, self.line_three, self.line_four, getattr(self, "line_five", None)):
            if frame is None:
                continue
            for w in frame.winfo_children():
                try:
                    w.configure(state=state)
                except Exception:
                    pass

        # Batch buttons: keep Stop enabled while batch is running
        try:
            self.batch_start_button.configure(state=(tk.NORMAL if enabled else tk.DISABLED))
        except Exception:
            pass
        try:
            self.batch_stop_button.configure(state=(tk.DISABLED if enabled else tk.NORMAL))
        except Exception:
            pass

    def _get_batch_time_limit_ns(self) -> int:
        """Get the batch/replay time limit in nanoseconds.

        The UI entry is in **seconds**.
        Default is 180 seconds (3 minutes).
        If the user enters an invalid value, we fall back to the default.
        """

        default_seconds = 180.0
        raw = ""
        try:
            raw = str(self.batch_time_limit_seconds_var.get())
        except Exception:
            raw = ""

        raw = (raw or "").strip()
        seconds = default_seconds

        if raw:
            try:
                seconds = float(raw)
            except Exception:
                seconds = default_seconds

        # Keep it safe + predictable
        if seconds <= 0:
            seconds = default_seconds

        # Cap to 24h to avoid ridiculous values
        if seconds > 24 * 60 * 60:
            seconds = 24 * 60 * 60

        return int(seconds * 1_000_000_000)

    # Start Search button logic or if search started already function as resume function
    def start_resume_search(self):
        # Resume if paused
        if self.search_paused and self.search_running:
            self.search_paused = False
            return

        # Don't restart if already running
        if self.search_running:
            return

        # Starting a new run (manual mode)
        self.search_fast_forward = False
        self.search_max_speed = False
        self._start_search(self.algo_var.get())
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def pause_search(self):
        if self.search_running:
            self.search_paused = True

    # flag flipper function to fast-forward the search, also starts the search if not started and unpauses if paused
    def search_fasten(self):
        if not self.search_running:
            self.start_resume_search()
        if self.search_paused:
            self.search_paused = False
        self.search_fast_forward = True
        self.search_max_speed = False

    # flag flipper function to max speed the search, also starts the search if not started and unpauses if paused
    def search_max(self):
        if not self.search_running:
            self.start_resume_search()
        if self.search_paused:
            self.search_paused = False
        self.search_max_speed = True
        self.search_fast_forward = False

    # Animation Loop runs one step of the search at a time
    def run_search_step(self):
        # If reset was pressed, stop the loop
        if not self.search_running:
            return

        # --------- (Aiman) -----------------
        # Step limit safety (mainly for Tree search in batch mode)
        if self._run_max_steps is not None:
            self.batch_status_var.set(f"Batch: running {self._batch_completed + 1}/{self._batch_total_target} algorithm: {self.algo_var.get()} count: {self._run_step_count}")
            try:
                if self._run_step_count >= int(self._run_max_steps):
                    print(f"Batch {self._batch_completed + 1} Algorithm {self.algo_var.get()} Stopped (step limit reached).")
                    self._finish_search(status="timeout")
                    return
            except Exception:
                pass

        # Time limit safety (applies to batch + replay only)
        if self._run_time_limit_ns is not None and self._run_start_perf_ns:
            try:
                if (time.perf_counter_ns() - int(self._run_start_perf_ns)) >= int(self._run_time_limit_ns):
                    print(f"Batch {self._batch_completed + 1} Algorithm {self.algo_var.get()} Stopped (time limit reached).")
                    self._finish_search(status="timeout")
                    return
            except Exception:
                pass
        # ------------------------------------

        if self.search_paused:
            self.root.after(1, self.run_search_step)
            return

        try:
            # Get the next node from the search generator
            current_node, text, execution_time, mem_use = next(self.search_generator)

            # --------- (Aiman) -----------------
            # Metrics bookkeeping (for batch results)
            self._run_step_count += 1

            # Some generators use -1 as "not provided", so clamp to 0
            try:
                et = int(execution_time or 0)
            except Exception:
                et = 0
            if et < 0:
                et = 0
            self.search_execution_time += et

            # Record memory: if algorithm doesn't provide a useful number, sample tracemalloc
            try:
                mem_i = int(mem_use)
            except Exception:
                mem_i = -1
            if mem_i >= 0:
                self.mem_use_record.append(mem_i)
            else:
                current_mem, _ = tracemalloc.get_traced_memory()
                delta = max(0, int(current_mem) - int(self._run_mem_baseline))
                self.mem_use_record.append(delta)
            # ------------------------------------

            if text != "":
                self.search_text_display.set(self.canvas_legend + "\n" + text)

            # If the generator yields None no path was found
            if current_node is None:
                print("No path found.")
                # --------- (Aiman) -----------------
                self._finish_search(status="fail")
                # ------------------------------------
                return

            (x, y) = current_node

            # change the previously visited square to cyan or orange if repeated
            # if self.last_node != self.start_node and self.last_node != self.goal_node:
            #     if self.last_node_repeated:
            #         self.draw_cell_content(self.last_node[0], self.last_node[1], color="orange", text=self.maze.get_node_cost(self.last_node[0], self.last_node[1]))
            #         self.last_node_repeated = False
            #     else:
            #         self.draw_cell_content(self.last_node[0], self.last_node[1], color="cyan", text=self.maze.get_node_cost(self.last_node[0], self.last_node[1]))

            self.draw_initial_map()

            # Draw the currently visiting square blue or red if repeated, if it's not start or end
            if current_node != self.start_node and current_node != self.goal_node:
                if current_node in self.visited:
                    self.draw_cell_content(x, y, color="red")
                    self.visited[current_node] = True
                    # --------- (Aiman) -----------------
                    self._run_repeat_count += 1
                    # ------------------------------------
                else:
                    self.draw_cell_content(x, y, color="blue")
                    self.visited[current_node] = False
            self.last_node = current_node

            # Check if reached the goal
            if current_node == self.goal_node:
                print("Goal found!")
                # Draw the final path
                self.draw_final_path()
                # --------- (Aiman) -----------------
                self._finish_search(status="success")
                # ------------------------------------
                return

            # Schedule the next step after a delay
            if self.search_fast_forward:  # double speed
                self.root.after(self.animation_delay // 2, self.run_search_step)
            elif self.search_max_speed:  # as fast as hardware allows
                self.root.after(1, self.run_search_step)
            else:  # normal speed
                self.root.after(self.animation_delay, self.run_search_step)

        # Catches error from generator when search is complete
        except StopIteration:
            print("Search complete.")
            # --------- (Aiman) -----------------
            self._finish_search(status="fail")
            # ------------------------------------
        # Catches any other errors
        except Exception as e:
            print(f"An error occurred: {e}")
            # --------- (Aiman) -----------------
            self._finish_search(status="error")
            # ------------------------------------

    # Draws the final path from start to goal
    def draw_final_path(self):

        # -------- (Aiman) -------------
        seed_info = f"Seed: {(self.seed_var.get() or '').strip() or '(none)'} | Walls: {self.wall_percentage}% | One-way: {self.oneway_percentage}%"
        # ------------------------------

        # custom skip for tree search type, as it will hang the computer trying to reconstruct its circular path
        # and displays the aggregated execution time
        if self.search_instance.search_type == "Tree":
            self.search_text_display.set(f"{self.canvas_legend}\nPath construction stopped as it will hang the program\nexecution time: {self.search_execution_time / 1000000} milliseconds\naverage memory use: {round(sum(self.mem_use_record) / len(self.mem_use_record), 2)} bytes")
            return
        else:
            self.search_text_display.set(f"{self.canvas_legend}\nexecution time: {self.search_execution_time / 1000000} milliseconds\naverage memory use: {round(sum(self.mem_use_record) / len(self.mem_use_record), 2)} bytes")

        # Get the reconstructed path from the search instance
        path = self.search_instance.reconstruct_path()

        if not path:
            print("Path reconstruction failed.")
            return

        # Draw the path as a series of blue lines between cell centers
        for i in range(len(path) - 1):
            x_start, y_start = path[i]
            x_end, y_end = path[i+1]

            # Get the center pixel coordinates of the start cell
            x0, y0, x1, y1 = self.get_canvas_coords(x_start, y_start)
            start_center_x, start_center_y = (x0 + x1) / 2, (y0 + y1) / 2

            # Get the center pixel coordinates of the end cell
            x0, y0, x1, y1 = self.get_canvas_coords(x_end, y_end)
            end_center_x, end_center_y = (x0 + x1) / 2, (y0 + y1) / 2

            # Draw the blue line connecting the centers
            self.canvas.create_line(start_center_x, start_center_y, end_center_x, end_center_y,
                                    fill='blue', width=4)

        # Redraw S and E on top so the path line doesnt cover them
        self.draw_cell_content(self.start_node[0], self.start_node[1], "S", "green")
        self.draw_cell_content(self.goal_node[0], self.goal_node[1], "E", "red")

    # the function the sliders call whenever they are moved
    def update_sliders(self, event):

        # updates the percentage variable with the slider
        self.wall_percentage = int(self.wall_slider.get())
        self.oneway_percentage = int(self.oneway_slider.get())

        # update slider 1 and its display
        self.wall_slider_display.config(text=f"{self.wall_percentage}%")
        self.wall_slider.config(to=100-self.oneway_percentage)

        # update slider 2 and its display
        self.oneway_slider_display.config(text=f"{self.oneway_percentage}%")
        self.oneway_slider.config(to=100-self.wall_percentage)

# --------------- (Aiman) ----------------------------------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def copy_seed_to_clipboard(self):
        # Copy the current seed token to the clipboard
        seed_text = (self.seed_var.get() or "").strip()
        if not seed_text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(seed_text)

    def set_generation_settings(self, wall_percentage: int, oneway_percentage: int):

        # Apply the wall/one-way percentages to internal state + sliders
        wall_percentage = int(wall_percentage)
        oneway_percentage = int(oneway_percentage)
        if wall_percentage < 0 or oneway_percentage < 0 or wall_percentage + oneway_percentage > 100:
            raise ValueError("Wall% + One-way% must be between 0 and 100")

        self.wall_percentage = wall_percentage
        self.oneway_percentage = oneway_percentage

        # Update slider ranges first to avoid out-of-range errors
        self.wall_slider.config(to=100 - self.oneway_percentage)
        self.oneway_slider.config(to=100 - self.wall_percentage)

        # Move sliders to the new values
        self.wall_slider.set(self.wall_percentage)
        self.oneway_slider.set(self.oneway_percentage)

        # Update value labels
        self.wall_slider_display.config(text=f"{self.wall_percentage}%")
        self.oneway_slider_display.config(text=f"{self.oneway_percentage}%")

    # Generates a maze with optional seeding (reproducibility)
    def generate_maze(self):
        """Generate a (reproducible) maze.

        Behaviour
        ---------
        * Seed lock OFF: clicking Generate creates a new seed token and uses current slider settings.
        * Seed lock ON: clicking Generate reuses the seed in the box.
            - If the seed is a valid token, it also restores the slider settings saved in the token.
            - If the seed is a raw value, we wrap it into a token so it becomes self-contained.
        """

        locked = bool(self.seed_locked_var.get())
        seed_text = (self.seed_var.get() or "").strip()

        wall_pct = int(self.wall_percentage)
        oneway_pct = int(self.oneway_percentage)

        # Determine RNG seed + (possibly) restore settings from the token
        if (not locked) or (not seed_text):
            # New random seed every time (or lock-on but empty seed)
            rng_seed = secrets.token_hex(8)
            seed_text = encode_seed_token(rng_seed=rng_seed, wall_percentage=wall_pct, oneway_percentage=oneway_pct)
            self.seed_var.set(seed_text)
        else:
            payload = decode_seed_token(seed_text)
            if payload is None:
                # If a user typed a raw seed, keep it, but wrap it into our token format (stores the settings too)
                rng_seed = seed_text
                seed_text = encode_seed_token(
                    rng_seed=rng_seed,
                    wall_percentage=wall_pct,
                    oneway_percentage=oneway_pct,
                )
                self.seed_var.set(seed_text)
            else:
                rng_seed = payload["rng"]
                wall_pct = int(payload["wall"])
                oneway_pct = int(payload["oneway"])
                self.set_generation_settings(wall_pct, oneway_pct)

        # Randomise the environment (deterministic if rng_seed is reused)
        self.maze.randomize(wall_pct, oneway_pct, seed = rng_seed)
        self.start_node = (self.maze.startx, self.maze.starty)
        self.goal_node = (self.maze.endx, self.maze.endy)
        self.reset()

    # Backwards compatible, in case the other scripts still call the old method
    def randomize_maze(self):
        self.generate_maze()


    def _open_batch_outputs(self):
        """Create CSV + seeds files for a batch run."""
        out_dir = Path("batch_outputs")
        out_dir.mkdir(exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = out_dir / f"batch_results_{stamp}.csv"
        seeds_path = out_dir / f"batch_seeds_{stamp}.txt"

        self._batch_csv_path = str(csv_path)
        self._batch_seed_path = str(seeds_path)

        self._batch_csv_fh = open(csv_path, "w", newline="", encoding="utf-8")
        fieldnames = [
            "run_id",
            "seed_token",
            "wall_pct",
            "oneway_pct",
            "algorithm",
            "search_type",
            "status",
            "steps",
            "unique_visited",
            "repeats",
            "path_len",
            "reported_time_ns",
            "wall_time_ns",
            "avg_mem_bytes",
        ]
        self._batch_csv_writer = csv.DictWriter(self._batch_csv_fh, fieldnames=fieldnames)
        self._batch_csv_writer.writeheader()
        self._batch_csv_fh.flush()

        self._batch_seed_fh = open(seeds_path, "w", encoding="utf-8")

    def _close_batch_outputs(self):
        """Close any open batch output files."""
        if self._batch_csv_fh is not None:
            try:
                self._batch_csv_fh.close()
            except Exception:
                pass
        self._batch_csv_fh = None
        self._batch_csv_writer = None

        if self._batch_seed_fh is not None:
            try:
                self._batch_seed_fh.close()
            except Exception:
                pass
        self._batch_seed_fh = None

    def start_batch_tests(self):
        """Run a batch test: generate N random mazes, run every algorithm, and save results."""

        # This function functions as a set up for the actual batch run "loop"

        if self._batch_running:
            return

        # batch number validity check

        try:
            target = int(self.batch_count_var.get())
        except Exception:
            target = 0

        if target <= 0:
            self.batch_status_var.set("Batch: enter a positive number of mazes")
            return

        self._batch_running = True
        self._batch_stop_requested = False

        # Ensure we are in RANDOM batch mode (not replay)
        self._batch_mode = "random"
        self._batch_replay_tokens = []
        self._batch_replay_index = 0

        self._batch_total_target = target
        self._batch_completed = 0

        # Use the same labels as the dropdown so selection logic stays consistent
        self._batch_algo_list = list(getattr(self, "_algo_options", []))
        if not self._batch_algo_list:
            self._batch_algo_list = [
                "BFS (Graph)",
                "DFS (Graph)",
                "UCS (Graph)",
                "AStar (Graph)",
                "BFS (Tree)",
                "DFS (Tree)",
                "UCS (Tree)",
                "AStar (Tree)",
            ]

        self._batch_prev_algo_choice = self.algo_var.get()

        # prep the class csv writer object
        self._open_batch_outputs()
        # disable all controls except stop test
        self._set_controls_enabled(False)

        self.batch_status_var.set(f"Batch: running 0/{self._batch_total_target}")
        self.root.after(1, self._batch_prepare_new_maze_random) # trigger the main batch maze generator

    def stop_batch_tests(self):
        """Request the batch runner to stop."""
        if not self._batch_running:
            return

        self._batch_stop_requested = True
        self.batch_status_var.set("Batch: stopping...")

        # Stop the active search immediately (if any)
        if self.search_running:
            self._finish_search(status="stopped")
        else:
            self._batch_finish()

    # Replay UI + batch runner mode
    def browse_replay_file(self):
        """Browse for a seeds file (txt) created by a previous batch run."""
        path = filedialog.askopenfilename(
            title="Select a seeds file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            try:
                self.replay_seed_file_var.set(path)
            except Exception:
                pass

    def start_replay_from_file(self):
        """Replay a batch run from a seeds file.

        The file should contain one seed token per line (the exact output of batch mode).
        """
        if self._batch_running:
            return

        path = ""
        try:
            path = (self.replay_seed_file_var.get() or "").strip()
        except Exception:
            path = ""

        if not path:
            self.batch_status_var.set("Replay: select a seeds file")
            return

        try:
            text = Path(path).read_text(encoding="utf-8")
        except Exception:
            self.batch_status_var.set("Replay: failed to read file")
            return

        tokens = []
        for line in text.splitlines():
            line = (line or "").strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            tokens.append(line)

        if not tokens:
            self.batch_status_var.set("Replay: no valid seeds found")
            return

        # Configure batch runner for replay mode
        self._batch_running = True
        self._batch_stop_requested = False
        self._batch_mode = "replay"
        self._batch_replay_tokens = list(tokens)
        self._batch_replay_index = 0
        self._batch_total_target = len(tokens)
        self._batch_completed = 0

        # Use the same labels as the dropdown so selection logic stays consistent
        self._batch_algo_list = list(getattr(self, "_algo_options", []))
        if not self._batch_algo_list:
            self._batch_algo_list = [
                "BFS (Graph)",
                "DFS (Graph)",
                "UCS (Graph)",
                "AStar (Graph)",
                "BFS (Tree)",
                "DFS (Tree)",
                "UCS (Tree)",
                "AStar (Tree)",
            ]

        self._batch_prev_algo_choice = self.algo_var.get()

        self._open_batch_outputs()
        self._set_controls_enabled(False)

        self.batch_status_var.set(f"Replay: running 0/{self._batch_total_target}")
        self.root.after(1, self._batch_prepare_next_replay)

    def _batch_prepare_maze_from_token(self, token: str):
        """Generate maze + GUI state from an encoded seed token."""
        payload = decode_seed_token(token)
        if payload is None:
            raise ValueError("Invalid seed token")

        rng_seed = payload["rng"]
        wall_pct = int(payload["wall"])
        oneway_pct = int(payload["oneway"])

        self._batch_current_token = token
        self._batch_current_rng_seed = rng_seed
        self._batch_current_wall = wall_pct
        self._batch_current_oneway = oneway_pct

        # Reflect in GUI
        self.seed_var.set(token)
        self.set_generation_settings(wall_pct, oneway_pct)

        # Generate deterministic maze
        self.maze.randomize(wall_pct, oneway_pct, seed=rng_seed)
        self.start_node = (self.maze.startx, self.maze.starty)
        self.goal_node = (self.maze.endx, self.maze.endy)
        self.reset()

        # Keep controls disabled (reset enables algo menu)
        self._set_controls_enabled(False)

    def _batch_prepare_next_replay(self):
        """Load the next seed from the replay list and start running algorithms."""
        if self._batch_stop_requested:
            self._batch_finish()
            return

        if self._batch_replay_index >= len(self._batch_replay_tokens):
            self._batch_finish()
            return

        token = self._batch_replay_tokens[self._batch_replay_index]
        try:
            self._batch_prepare_maze_from_token(token)
        except Exception:
            # Skip invalid lines
            self.batch_status_var.set(f"Replay: invalid seed at line {self._batch_replay_index + 1} (skipping)")
            self._batch_replay_index += 1
            self.root.after(1, self._batch_prepare_next_replay)
            return

        self._batch_algo_index = 0
        self.root.after(1, self._batch_start_next_algorithm)

    def _batch_prepare_new_maze_random(self):
        if self._batch_stop_requested:
            self._batch_finish()
            return

        # Pick random wall/one-way settings within user-provided maxima
        try:
            wall_max = int(self.batch_wall_max_var.get())
        except Exception:
            wall_max = 30
        try:
            oneway_max = int(self.batch_oneway_max_var.get())
        except Exception:
            oneway_max = 30

        wall_max = max(0, min(100, wall_max))
        oneway_max = max(0, min(100, oneway_max))

        wall_pct = 0
        oneway_pct = 0
        for _ in range(200):
            wall_pct = secrets.randbelow(wall_max + 1)
            oneway_pct = secrets.randbelow(oneway_max + 1)
            if wall_pct + oneway_pct <= 100:
                break
        else: # runs if break triggered in for loop
            wall_pct = min(wall_max, 100)
            oneway_pct = min(oneway_max, max(0, 100 - wall_pct))

        rng_seed = secrets.token_hex(8)
        token = encode_seed_token(rng_seed=rng_seed, wall_percentage=wall_pct, oneway_percentage=oneway_pct)

        self._batch_current_token = token
        self._batch_current_rng_seed = rng_seed
        self._batch_current_wall = wall_pct
        self._batch_current_oneway = oneway_pct

        # Reflect settings in the GUI for reproducibility
        self.seed_var.set(token)
        self.set_generation_settings(wall_pct, oneway_pct)

        # Generate maze
        self.maze.randomize(wall_pct, oneway_pct, seed=rng_seed)
        self.start_node = (self.maze.startx, self.maze.starty)
        self.goal_node = (self.maze.endx, self.maze.endy)
        self.reset()

        # Keep controls disabled (reset enables algo menu)
        self._set_controls_enabled(False)

        # start the main batch run after maze is randomized
        self._batch_algo_index = 0
        self.root.after(1, self._batch_start_next_algorithm)

    def _batch_accept_maze(self):
        """Record the accepted maze seed token so the batch can be replayed."""
        if self._batch_seed_fh is None:
            return
        try:
            self._batch_seed_fh.write(f"{self._batch_current_token}\n")
            self._batch_seed_fh.flush()
        except Exception:
            pass

    def _batch_write_row(self, metrics: RunMetrics):
        if self._batch_csv_writer is None:
            return

        row = {
            "run_id": self._batch_current_run_id,
            "seed_token": self._batch_current_token,
            "wall_pct": self._batch_current_wall,
            "oneway_pct": self._batch_current_oneway,
            "algorithm": metrics.algo_choice,
            "search_type": metrics.search_type,
            "status": metrics.status,
            "steps": metrics.steps,
            "unique_visited": metrics.unique_visited,
            "repeats": metrics.repeats,
            "path_len": "" if metrics.path_len is None else metrics.path_len,
            "reported_time_ns": metrics.reported_time_ns,
            "wall_time_ns": metrics.wall_time_ns,
            "avg_mem_bytes": round(metrics.avg_mem_bytes, 2),
        }
        try:
            self._batch_csv_writer.writerow(row)
            self._batch_csv_fh.flush()
        except Exception:
            pass

    def _batch_start_next_algorithm(self):
        if self._batch_stop_requested:
            self._batch_finish()
            return

        # Completed all algorithms for this maze
        if self._batch_algo_index >= len(self._batch_algo_list):
            self._batch_completed += 1


            # Slightly different status text depending on the mode.
            label = "Replay" if getattr(self, "_batch_mode", "random") == "replay" else "Batch"
            self.batch_status_var.set(f"{label}: completed {self._batch_completed}/{self._batch_total_target}")

            if self._batch_completed >= self._batch_total_target:
                self._batch_finish()
                return

            # Continue based on runner mode
            if getattr(self, "_batch_mode", "random") == "replay":
                self._batch_replay_index += 1
                self.root.after(1, self._batch_prepare_next_replay)
            else:
                self.root.after(1, self._batch_prepare_new_maze_random)
            return

        algo_choice = self._batch_algo_list[self._batch_algo_index]
        self.algo_var.set(algo_choice)

        # Step limit safety (Tree can loop)
        if "(Tree)" in algo_choice:
            max_steps = self.DEFAULT_MAX_STEPS_TREE
        else:
            max_steps = self.DEFAULT_MAX_STEPS_GRAPH

        # Run at max speed during batching
        self.search_max_speed = True
        self.search_fast_forward = False
        self.search_paused = False

        self._start_search(
            algo_choice,
            on_complete=self._batch_on_algorithm_complete,
            max_steps=max_steps,
            force_max_speed=True,
        )

    def _batch_on_algorithm_complete(self, metrics: RunMetrics):
        if self._batch_stop_requested or metrics.status == "stopped":
            self._batch_finish()
            return

        algo_choice = self._batch_algo_list[self._batch_algo_index]

        # Solvability rule:
        # - RANDOM batch: if BFS(Graph) fails, treat maze as unsolvable and regenerate (do NOT count this maze)
        # - REPLAY mode: if BFS(Graph) fails, record it and skip to next seed
        is_first_algo = (self._batch_algo_index == 0 and algo_choice == "BFS (Graph)")
        if is_first_algo and metrics.status != "success":
            # --------- (Aiman) -----------------
            if getattr(self, "_batch_mode", "random") == "replay":
                self.batch_status_var.set("Replay: unsolvable seed -> skipping")

                # Ensure the row has a stable run id
                self._batch_current_run_id = self._batch_completed + 1
                self._batch_write_row(metrics)

                # Skip remaining algorithms for this seed
                self._batch_algo_index = len(self._batch_algo_list)
                self.root.after(1, self._batch_start_next_algorithm)
            else:
                self.batch_status_var.set("Batch: unsolvable maze -> regenerating")
                self.root.after(1, self._batch_prepare_new_maze_random)
            return

        # If we got here and it's the first algo, maze is accepted
        if is_first_algo:
            self._batch_current_run_id = self._batch_completed + 1
            self._batch_accept_maze()

        # Write the row
        self._batch_write_row(metrics)

        # Advance to the next algorithm (after a short pause so the user can SEE the final path)
        self._batch_algo_index += 1
        try:
            pause_ms = max(0, int(self.batch_between_algo_delay_ms_var.get()))
        except Exception:
            pause_ms = 0
        self.root.after(pause_ms, self._batch_start_next_algorithm)

    def _batch_finish(self):
        if not self._batch_running:
            return

        # Preserve which mode we were in, for the final status message.
        finished_label = "Replay" if getattr(self, "_batch_mode", "random") == "replay" else "Batch"

        self._batch_running = False

        # Reset replay state so the next run starts cleanly.
        self._batch_mode = "random"
        self._batch_replay_tokens = []
        self._batch_replay_index = 0

        # Stop any active search loop cleanly
        self.search_running = False

        self._close_batch_outputs()

        # Restore previous algo selection (nice UX)
        if self._batch_prev_algo_choice:
            try:
                self.algo_var.set(self._batch_prev_algo_choice)
            except Exception:
                pass

        self._set_controls_enabled(True)

        if self._batch_csv_path and self._batch_seed_path:
            self.batch_status_var.set(
                f"{finished_label}: finished {self._batch_completed}/{self._batch_total_target} | "
                f"CSV: {self._batch_csv_path} | Seeds: {self._batch_seed_path}"
            )
        else:
            self.batch_status_var.set(f"{finished_label}: finished {self._batch_completed}/{self._batch_total_target}")

# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    """ OLD
    # randomizes maze with the randomize function within the maze class
    # also does some housekeeping to ensure the GUI updates correctly
    def randomize_maze(self):
        self.maze.randomize(self.wall_percentage, self.oneway_percentage)
        self.start_node = (self.maze.startx, self.maze.starty)
        self.goal_node = (self.maze.endx, self.maze.endy)
        self.reset()
        self.draw_initial_map()
        # print(self.maze)
    """
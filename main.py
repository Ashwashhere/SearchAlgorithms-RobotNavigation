import tkinter as tk
from mazeVisualiser import MazeVisualizer 


# constants

# the starting maze define, each group of 4 bools represent traversable directions of up down left right, the 4 bools are always in that order
# can be extended or reduced if needed, the maze class is capable of taking in size changes, provided the maze is in rectangular form
# if someone has a better way of initializing this without just shoving it into a separate file please tell me this is a fking eyesore
MAZE = [[([False, True, False, True], 1), ([False, False, False, True], 3), ([False, False, True, True], 1), ([False, False, True, True], 2), ([False, False, True, True], 0), ([False, True, True, False], 3), ([False, True, False, True], 2), ([False, False, True, True], 1), ([False, False, True, True], 1), ([False, True, True, False], 2), ([False, True, False, True], 3), ([False, True, True, True], 0), ([False, True, True, True] ,2), ([False, True, True, False], 3)],
        [([True, True, False, False], 1), ([True, False, True, True], 1), ([False, False, True, True], 2), ([False, True, True, False], 3), ([False, False, False, False], 2), ([True, False, False, True], 1), ([True, False, True, False], 0), ([False, True, False, False], 1), ([False, True, True, True], 2), ([True, False, True, False], 3), ([True, True, False, True], 2), ([True, True, True, True], 1), ([True, True, True, True], 0), ([True, True, True, False], 1)],
        [([True, True, False, False], 1), ([False, True, False, True], 2), ([False, False, True, True], 3), ([True, False, True, False], 2), ([False, True, False, True], 1), ([False, True, True, True], 0), ([False, True, True, True], 1), ([False, True, True, True], 2), ([True, True, True, False], 3), ([False, True, False, False], 2), ([True, True, False, True], 1), ([True, True, True, True], 0), ([True, False, True, True], 1), ([True, True, True, False], 2)],
        [([True, True, False, False], 0), ([True, True, False, False], 1), ([False, True, False, True], 3), ([False, True, True, True], 3), ([True, True, True, True], 2), ([True, True, True, True], 2), ([True, True, True, True], 1), ([False, True, True, True], 0), ([True, True, True, False], 1), ([True, True, False, False], 2), ([True, True, False, True], 2), ([True, True, True, False], 3), ([False, False, False, True], 3), ([True, True, True, False], 3)],
        [([True, True, False, False], 1), ([True, True, False, False], 2), ([True, True, False, True], 2), ([True, True, True, True], 3), ([True, True, True, True], 3), ([True, True, True, False], 3), ([True, True, True, False], 2), ([False, True, True, True], 2), ([True, True, True, False], 1), ([True, True, False, False], 2), ([True, True, False, True], 2), ([True, True, True, True], 3), ([False, True, True, True], 3), ([True, True, True, False], 3)],
        [([True, True, False, False], 2), ([True, True, False, False], 2), ([True, True, False, False], 1), ([True, True, False, False], 2), ([True, True, False, False], 2), ([False, True, False, False], 3), ([True, True, False, False], 3), ([True, True, False, False], 3), ([True, True, False, False], 2), ([True, True, False, False], 2), ([True, True, False, True], 1), ([True, True, True, True], 2), ([True, True, True, True], 2), ([True, True, True, False], 3)],
        [([True, True, False, False], 3), ([True, True, False, False], 2), ([True, False, False, True], 2), ([True, True, True, True], 1), ([True, False, True, True], 2), ([True, False, True, True], 2), ([True, False, True, True], 3), ([True, False, True, True], 3), ([True, False, True, True], 3), ([True, False, True, False], 2), ([True, True, False, True], 2), ([True, True, True, True], 1), ([True, True, True, True], 2), ([True, True, True, False], 2)],
        [([True, True, False, False], 3), ([True, True, False, True], 3), ([False, True, True, False], 3), ([True, False, False, True], 2), ([False, False, True, True], 2), ([False, False, True, True], 1), ([False, False, True, True], 2), ([False, False, True, True], 2), ([False, False, True, True], 3), ([False, True, True, False], 3), ([True, True, False, True], 3), ([True, True, True, True], 2), ([True, True, True, True], 2), ([True, True, True, False], 1)],
        [([True, True, False, False], 2), ([True, False, False, True], 2), ([True, True, True, False], 3), ([False, True, False, True], 3), ([False, False, True, True], 3), ([False, False, True, True], 2), ([False, False, True, True], 2), ([False, True, True, False], 1), ([False, True, False, False], 2), ([True, True, False, False], 2), ([True, True, False, True], 3), ([True, True, True, True], 3), ([True, True, True, True], 3), ([True, True, True, False], 2)],
        [([True, False, False, True], 2), ([False, False, True, True], 1), ([True, False, True, False], 2), ([True, False, False, True], 2), ([False, False, True, False], 3), ([False, False, False, True], 3), ([False, False, True, True], 3), ([True, False, True, True], 2), ([True, False, True, True], 2), ([True, False, True, True], 1), ([True, False, True, True], 2), ([True, False, True, True], 2), ([True, False, True, True], 3), ([True, False, True, False], 3)]]

# this is essentially main(), code starts running here
if __name__ == "__main__":

    # (Ash)   
    # Set up the maze data
    maze_layout = MAZE
    start_pos = (0, 0)
    end_pos = (12, 3)

    # Create the main window
    root = tk.Tk()
    
    # Create the application instance pass the root window and maze data to it
    app = MazeVisualizer(root, maze_layout, start_pos, end_pos, animation_delay=150)
    # print(Maze.Maze(MAZE, start_pos[0], start_pos[1], end_pos[0], end_pos[1]))
    
    # Start tkinter event loop
    root.mainloop()

    # Old code
"""
    environment = Maze.Maze(MAZE, 0, 0, 12, 3)
    print(environment)
    ucs = UCS.UCS(environment)
    print(ucs.search())
    print(f"UCS execution time: {ucs.get_time()} nanoseconds\n")
    # print("done")

    # Create an instance of the maze, with the defined layout and start/end coordinates 
    # environment = Maze.Maze(MAZE, 0, 0, 4, 9)
    # Create an instance of the A* algortihm, passing in the maze 
    astar = AStar.AStar(environment)
    # Run the A* algorithm to find the path
    path1 = astar.search()
    # Set the path which would be found onto the maze, allowing it to be visualised with pink arrows
    environment.set_path(path1)
    # Display the maze, showing the path of the A* algorithm 
    print(environment)
    # Show the list of coordinates which would make up the path in which the A* algorithm would find
    print("Path of the A* algorithm:", path1)
    # Indicate that the piece of code has finished execuiting 
    print("done")
"""

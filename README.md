# Robotic Navigation Search Algorithm Benchmark (2026)

This repository contains a comprehensive inquiry into how robotic agents utilize search algorithms for navigation in grid-based environments. Developed by Cheuk Wan Fung, Aiman Al-Awdi, and Ashah Nelson, this study evaluates the trade-offs between path optimality, computational efficiency, and architectural reliability.

## 🚀 Project Overview

The project simulates a robotic agent in a 2D grid world containing complex environmental constraints like walls, one-way paths, and weighted tiles. The core objective was to determine the most reliable algorithm for autonomous navigation through batch testing and visual analysis.

### Core Algorithms Implemented

The system implements both **Graph** and **Tree** search variants for the following algorithms:

* **Breadth-First Search (BFS):** Layer-by-layer exploration that guarantees the shortest path.


* **Depth-First Search (DFS):** A branch-first approach that is memory-efficient but produces sub-optimal paths.


* **Uniform Cost Search (UCS):** Prioritizes paths with the lowest accumulated cost.


* ** Search:** Utilizes a Manhattan distance heuristic to guide the search toward the goal efficiently.



---

## 🛠️ Technical Specifications

### Robot Parameters & Action Model

* **Physicality:** The robot is circular with a one-node diameter, allowing it to traverse one node at a time.


* **Movement:** Constrained to the 4 cardinal directions (up, down, left, right) provided the environment is not blocked.


* **Sensor Data:** The agent accesses local coordinates, entry costs, and (for ) heuristic distances.



### Environment Architecture

The grid is modeled as a 3D array where each coordinate is represented by a specific tuple:

* **Accessibility:** A 4-element boolean array `[Up, Down, Left, Right]`.


* **Weight:** An integer representing the **Cost of Entry** for that specific tile.



---

## 📊 Performance Benchmarking

We conducted batch testing over randomized mazes to quantify the performance of each "Graph Search" variant.

Graph Search Comparison Table 

| Metric | BFS (Graph) | DFS (Graph) | UCS (Graph) |  (Graph) |
| --- | --- | --- | --- | --- |
| **Avg. Path Length** | 15.8 (Optimal) | 52.9 (Sub-optimal) | 16.16 | 16.73 |
| **Avg. Nodes Explored** | 109.3 | 86.5 | 109.61 | 78.49 |
| **Avg. Path Cost** | 35.3 | 130.4 | 27.1 | 26.9 |
| **Success Rate** | 100% | 100% | 100% | 100% |

### Key Research Findings

1. **Tree Search Failure:** In environments with cycles (like grids), Tree Search variants are fundamentally unreliable, often achieving success rates below 50% due to infinite looping.


2. **Shortest Path Guarantee:** BFS always finds the path with the fewest steps but expands a high number of nodes.


3. **Heuristic Efficiency:**  is the most balanced algorithm, exploring significantly fewer nodes (78.49 avg) while maintaining the lowest path cost (26.9 avg).


4. **UCS Priority:** UCS is ideal for avoiding high-traffic or high-cost areas, similar to modern GPS systems.



---

## 🖥️ Maze Search Visualizer

The GUI application allows for real-time monitoring of the agent's behavior.

* **Visual Indicators:** Start (Green), Goal (Red), Visiting (Blue), and Visited (Cyan).


* **Customization:** Adjustable sliders for "Wall percentage" and "One-way percentage".


* **Reproducibility:** Seed-based generation allows for re-running specific randomized mazes.

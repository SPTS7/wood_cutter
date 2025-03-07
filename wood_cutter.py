# %%

import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from collections import Counter


# --- Panel packing (free-rectangle splitting) class ---
class Panel:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # Initially, the entire board is free.
        self.free_rectangles = [(0, 0, width, height)]
        self.placements = []  # List of placements: (x, y, w, h, rotated)

    def try_place(self, piece_width, piece_height):
        """
        Try to place a piece (piece_width x piece_height) into the panel.
        It attempts both orientations (rotated or not).
        If successful, updates free rectangles and returns (x, y, placed_w, placed_h, rotated).
        Otherwise returns None.
        """
        for rotated in [False, True]:
            if rotated:
                w, h = piece_height, piece_width
            else:
                w, h = piece_width, piece_height
            for i, (fx, fy, fw, fh) in enumerate(self.free_rectangles):
                if fw >= w and fh >= h:
                    # Place piece at the top-left corner of the free rectangle.
                    x, y = fx, fy
                    self.placements.append((x, y, w, h, rotated))
                    # Remove the free rectangle that we used.
                    del self.free_rectangles[i]
                    # Split the remaining space:
                    # Free rectangle to the right.
                    if fw - w > 0:
                        self.free_rectangles.append((fx + w, fy, fw - w, h))
                    # Free rectangle below.
                    if fh - h > 0:
                        self.free_rectangles.append((fx, fy + h, fw, fh - h))
                    return (x, y, w, h, rotated)
        return None


# --- Optimizer for purchasing boards ---
def optimize_purchase(required_pieces, available_boards):
    """
    Given a list of required pieces and available board types, find a combination of boards
    (using a heuristic) that can pack all required pieces at minimal total cost.

    Parameters:
      required_pieces: list of (piece_width, piece_height, quantity)
      available_boards: list of (board_width, board_height, cost)
         (assumed infinite supply of each type)

    Returns:
      cutting_plan: list of placements (x, y, w, h, board_number, rotated)
      board_solution: list of board types used (each as (width, height, cost))
      total_cost: total cost of purchased boards
    """
    # Expand required pieces into individual items.
    pieces = []
    for w, h, qty in required_pieces:
        for _ in range(qty):
            pieces.append((w, h))
    # Sort pieces descending by area (heuristic)
    pieces.sort(key=lambda p: p[0] * p[1], reverse=True)

    total_cost = 0
    board_solution = []  # List of board types used.
    cutting_plan = []  # Global cutting plan across boards.
    board_count = 0  # Number of boards used.

    pbar = tqdm(total=len(pieces), desc="Packing pieces")
    while pieces:
        best_efficiency = None  # (cost per unit area packed)
        best_board = None  # Chosen board type (width, height, cost)
        best_panel = None  # Simulation panel instance.
        best_packed_indices = None  # Indices of pieces that got packed.

        # Try each available board type.
        for board in available_boards:
            board_width, board_height, cost = board
            panel = Panel(board_width, board_height)
            packed_indices = []
            # Simulate packing the pieces (already sorted).
            for i, (pw, ph) in enumerate(pieces):
                pos = panel.try_place(pw, ph)
                if pos is not None:
                    packed_indices.append(i)
            if not packed_indices:
                continue  # This board type couldn’t pack any remaining piece.
            # Compute total packed area.
            packed_area = sum(pieces[i][0] * pieces[i][1] for i in packed_indices)
            efficiency = cost / packed_area  # Lower is better.
            if best_efficiency is None or efficiency < best_efficiency:
                best_efficiency = efficiency
                best_board = board
                best_panel = panel
                best_packed_indices = packed_indices

        if best_board is None:
            raise ValueError(
                "Cannot pack remaining pieces in any available board type!"
            )

        # Use the best board type to pack a new board.
        board_count += 1
        board_width, board_height, cost = best_board
        total_cost += cost
        board_solution.append(best_board)

        # Record placements from the best panel.
        for placement in best_panel.placements:
            x, y, w, h, rotated = placement
            cutting_plan.append((x, y, w, h, board_count, rotated))

        # Remove the pieces that were packed in this board (remove in reverse order).
        for i in sorted(best_packed_indices, reverse=True):
            del pieces[i]
            pbar.update(1)
    pbar.close()
    return cutting_plan, board_solution, total_cost


# --- Visualization function ---
def visualize_boards(board_solution, cutting_plan):
    """
    Visualize each purchased board (full board size) with its placed pieces.
    The board's dimensions and cost are displayed in the subplot title.
    """
    total_boards = len(board_solution)
    fig, axes = plt.subplots(total_boards, 1, figsize=(10, 6 * total_boards))
    if total_boards == 1:
        axes = [axes]
    # Group placements by board number.
    boards = {i: [] for i in range(1, total_boards + 1)}
    for placement in cutting_plan:
        x, y, w, h, board_num, rotated = placement
        boards[board_num].append(placement)
    for board_num in range(1, total_boards + 1):
        board_width, board_height, cost = board_solution[board_num - 1]
        ax = axes[board_num - 1]
        ax.set_xlim(0, board_width)
        ax.set_ylim(0, board_height)
        ax.set_title(f"Board {board_num}: {board_width}x{board_height} (Cost: {cost})")
        ax.set_xticks(np.arange(0, board_width + 1, 100))
        ax.set_yticks(np.arange(0, board_height + 1, 100))
        ax.grid(True, linestyle="--", linewidth=0.5)
        for x, y, w, h, b, rotated in boards[board_num]:
            rect = plt.Rectangle(
                (x, y),
                w,
                h,
                edgecolor="black",
                facecolor=np.random.rand(
                    3,
                ),
            )
            ax.add_patch(rect)
            label = f"{w}x{h}" + (" (R)" if rotated else "")
            ax.text(
                x + w / 2,
                y + h / 2,
                label,
                ha="center",
                va="center",
                fontsize=8,
                color="white",
            )
        ax.invert_yaxis()
    plt.show()


# --- Function to print the shopping list of boards ---
def print_shopping_list(board_solution):
    """
    Aggregates board_solution (a list of board types used, each as (width, height, cost))
    and prints the shopping list.
    """
    counts = Counter(board_solution)
    print("Shopping List:")
    for board, quantity in counts.items():
        width, height, cost = board
        print(f"{quantity} board(s) of size {width}x{height} (Cost: {cost} each)")


# --- Example usage ---
if __name__ == "__main__":
    # Required pieces: list of (piece_width, piece_height, quantity)
    # required_pieces = [(800, 400, 5), (1600, 400, 2), (1600, 800, 1), (1600, 400, 2)]
    required_pieces = [(1000, 400, 5), (1700, 400, 2), (1700, 1000, 1), (1700, 500, 1)]
    # Available board types: list of (board_width, board_height, cost)
    available_boards = [
        (2500, 1250, 24),
        (2050, 625, 20),
        (2500, 675, 12),
        (2500, 1250, 19),
    ]

    cutting_plan, board_solution, total_cost = optimize_purchase(
        required_pieces, available_boards
    )
    print(f"Total cost: {total_cost}")
    print_shopping_list(board_solution)
    visualize_boards(board_solution, cutting_plan)

# https://www.leroymerlin.pt/produtos/madeiras-e-acrilicos/paineis-para-construcao/osb/?p=1&filters=%7B%22attribute-00596%22%3A%2215%22%2C%22vendor-1P%22%3A%22true%22%7D
# %%

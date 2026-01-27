from rich_pixels import Pixels
from rich.console import Console

console = Console()
pixels = Pixels.from_image_path("/Users/gaoxiang/Downloads/terminal (1).png", resize=(30, 30))
console.print(pixels)
from rich_pixels import Pixels
from rich.console import Console


console = Console()
pixels = Pixels.from_image_path("/Users/gaoxiang/VscodeProjects/kop/kop/statics/terminal.png", resize=(50, 50))
console.print(pixels)


# from rich_pixels import Pixels
# from rich.console import Console
# from rich.segment import Segment
# from rich.style import Style

# console = Console()

# # Draw your shapes using any character you want
# grid = """\
#      xx   xx
#      ox   ox
#      Ox   Ox
# xx             xx
# xxxxxxxxxxxxxxxxx
# """


# b = """
                        
#    ┌───────────────┐    
#    │               │    
#    │ xx            │    
#    │  xxxx         │    
#    │     xxx       │    
#    │  xxxx         │    
#    │ xx     xxxxxx │    
#    │               │    
#    └───────────────┘    
                        
# """
# # Map characters to different characters/styles
# mapping = {
#     "x": Segment(" ", Style.parse("yellow on yellow")),
#     "o": Segment(" ", Style.parse("on white")),
#     "O": Segment(" ", Style.parse("on blue")),
# }

# pixels = Pixels.from_ascii(b, mapping)
# console.print(pixels)
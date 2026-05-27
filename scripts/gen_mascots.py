"""Generate mascot PNG sprites — faithful reproduction of user's pixel art at 24x24 grid."""
from PIL import Image
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dist', 'mascots')
os.makedirs(OUT, exist_ok=True)

CELL = 6
W, H = 24, 24

C = {
    '.': None,
    'O': (212, 132, 90),
    'o': (186, 112, 70),
    'D': (170, 100, 62),
    'e': (26, 20, 16),
    'W': (255, 255, 255),
    'B': (120, 169, 227),
    'b': (45, 90, 140),
    'Y': (232, 184, 74),
    'y': (196, 144, 48),
    'T': (180, 180, 180),
    't': (102, 102, 102),
    'K': (74, 69, 64),
    'k': (58, 53, 48),
    'P': (107, 91, 154),
    'p': (74, 58, 112),
    'X': (224, 48, 48),
    'x': (180, 40, 40),
    'R': (201, 80, 80),
    'r': (168, 60, 60),
    'S': (230, 220, 180),
    's': (200, 190, 150),
    'G': (140, 160, 80),
    'H': (180, 150, 70),
    'h': (130, 110, 50),
    'F': (240, 180, 130),
    'L': (160, 100, 60),
    'M': (90, 80, 70),
    'N': (110, 100, 80),
    'V': (160, 140, 100),
    'g': (100, 120, 60),
}

def make_sprite(grid, filename):
    h = len(grid)
    w = max(len(row) for row in grid)
    img = Image.new('RGBA', (w * CELL, h * CELL), (0, 0, 0, 0))
    for row_i, row in enumerate(grid):
        for col_i, ch in enumerate(row):
            color = C.get(ch)
            if color is None:
                continue
            rgba = color + (255,)
            for py in range(CELL):
                for px in range(CELL):
                    img.putpixel((col_i * CELL + px, row_i * CELL + py), rgba)
    path = os.path.join(OUT, filename)
    img.save(path, 'PNG')
    print(f'  -> {filename} ({w}x{h})')

# 1. IDEA - lightbulb pig side view
idea = [
    '........YYYY............',
    '.......YYyyYY...........',
    '.......YyYYyY...........',
    '.......YYYYYY...........',
    '.......YYYYYY...........',
    '........TttT............',
    '........TttT............',
    '........................',
    '..............OO........',
    '............OOOOOOO.....',
    '...........OOOOOOOO.....',
    '..........OOOOOOOOO.....',
    '.........OOOOOOOOOO.....',
    '....OOO..OOOOOOOOOO.....',
    '....OOO..OOOOOOOOOO.....',
    '....OOO.OeOOOOOeOOO.....',
    '....OOO.OeOOOOOeOOO.....',
    '.........OOOOOOOOOO.....',
    '.........OOOOOOOOOO.....',
    '.........OOOOOOOOOO.....',
    '........OO..OO..OO......',
    '........OO..OO..OO......',
    '........OO..OO..OO......',
    '........................',
]

# 2. BASIC - front facing pig
basic = [
    '........................',
    '........................',
    '........................',
    '........................',
    '........................',
    '........................',
    '........................',
    '......OOOOOOOOOOOO......',
    '......OOOOOOOOOOOO......',
    '...OOO.OOOOOOOO.OOO....',
    '...OOO.OOOOOOOO.OOO....',
    '......OOOOOOOOOOOO......',
    '......OOeOOOOeOOOO......',
    '......OOeOOOOeOOOO......',
    '......OOOOOOOOOOOO......',
    '......OOOOOOOOOOOO......',
    '......OOOOOOOOOOOO......',
    '......OOOOOOOOOOOO......',
    '......WW..WW..WW........',
    '......WW..WW..WW........',
    '......WW......WW........',
    '........................',
    '........................',
    '........................',
]

# 3. BIRD - side pig with blue bird
bird = [
    '........................',
    '..........BBBB..........',
    '.........BBBBBB.........',
    '.........BeBBBB.........',
    '.........BBBBBB.........',
    '..........bBBb..........',
    '..........bBBb..........',
    '..............OO........',
    '............OOOOOOO.....',
    '...........OOOOOOOO.....',
    '..........OOOOOOOOoW....',
    '.........OOOOOOOOOO.....',
    '....OOO..OOOOOOOOOO.....',
    '....OOO..OOOOOOOOOO.....',
    '....OOO.OeeOOOeeOOO.....',
    '....OOO.OeeOOOeeOOO.....',
    '.........OOOOOOOOOO.....',
    '.........OOOOOOOOOO.....',
    '.........OOOOOOOOOO.....',
    '........OO..OO..OO......',
    '........OO..OO..OO......',
    '........OO..OO..OO......',
    '........................',
    '........................',
]

# 4. SPARKLE - red pig with sparkler
sparkle = [
    '..........sS............',
    '.........SsS............',
    '..........Ss.S..........',
    '..........ee............',
    '..........ee............',
    '..........ee............',
    '..............RR........',
    '............RRRRRRR.....',
    '...........RRRRRRRR.....',
    '..........RRRRRRRRR.....',
    '.........RRRRRRRRRR.....',
    '....RRR..RRRRRRRRRR.....',
    '....RRR..RRRRRRRRRR.....',
    '....RRR.ReeRRReeRRR.....',
    '....RRR.RerRRRerRRR.....',
    '.........RRRRRRRRRR.....',
    '.........RRRRRRRRRR.....',
    '.........RRRRRRRRRR.....',
    '........WW..WW..WW......',
    '........WW..WW..WW......',
    '........WW..WW..WW......',
    '........................',
    '........................',
    '........................',
]

# 5. WORKER - pig with hard hat + hammer
worker = [
    '........................',
    '........................',
    '.....gYYYYYYYYYYg.......',
    '....YYYYYYYYYYYYYY......',
    '....YYYYYYhYYYYYYY......',
    '....YYYYYYhYYYYYYY......',
    '....yyyyyyyyyyyyyy......',
    '......OOOOOOOOOO........',
    '...OOO.OOOOOOOO.OOO....',
    '...OOO.OOOOOOOO.OOO....',
    '......OeOOOOOeOO........',
    '......OeOOOOOeOO....tt..',
    '......OOOOOOOOOO....tTt.',
    '......OOOOOOOOOO....tTt.',
    '......OOOOOOOOOO.....t..',
    '......OOOOOOOOOO........',
    '......OOOOOOOOOO........',
    '......OO..OO..OO........',
    '......OO..OO..OO........',
    '......OO..OO..OO........',
    '........................',
    '........................',
    '........................',
    '........................',
]

# 6. COOL - big side pig squinting
cool = [
    '........................',
    '........................',
    '........................',
    '..............OO........',
    '............OOOOOOOOO...',
    '...........OOOOOOOOOO...',
    '..........OOOOOOOOOOO...',
    '.........OOOOOOOOOOOO...',
    '.........OOOOOOOOOOOO...',
    '....OOO..OOOOOOOOOOOO...',
    '....OOO..OOOOOOOOOOOO...',
    '....OOO.OeeOOOOeeOOOO...',
    '....OOO.OeeOOOOeeOOOO...',
    '.........OOOOOOOOOOOO...',
    '.........OOOOOOOOOPbO...',
    '.........OOOOOOOOPbWO...',
    '.........OOOOOOOOOOOO...',
    '.........OOOOOOOOOOOO...',
    '........OO..OO..OO..OO..',
    '........OO..OO..OO..OO..',
    '........OO..OO..OO..OO..',
    '........................',
    '........................',
    '........................',
]

# 7. PIRATE - welding mask pig
pirate = [
    '....KKKKKKKKKKkk........',
    '...KKKKKKKKKKKKk........',
    '...KKKKKKKKKKKKk........',
    '..KKKkKKKkKKKKKKk.......',
    '..KKKeKKKeKKKKKKk.......',
    '..KKKKKKKKKKKKKKk.......',
    '..KKKKKKKKKKKKKKk.......',
    '...kKKKKhKKKKKk.........',
    '.....OOOOOOOOOOO........',
    '..OOO.OOOOOOOOO.OOO....',
    '..OOO.OOOOOOOOO.OOO....',
    '.....OOOOOOOOOOO........',
    '.....OOOOOOOOOOO..Pp....',
    '.....OOOOOOOOOOO..pYy...',
    '.....OOOOOOOOOOO........',
    '....OO.OO.OO.OO.OO......',
    '....OO.OO.OO.OO.OO......',
    '....OO.OO.OO.OO.OO......',
    '........................',
    '........................',
    '........................',
    '........................',
    '........................',
    '........................',
]

# 8. ERROR - dead flat pig with ERROR text
error = [
    '........................',
    '........................',
    '........................',
    '..........Tt............',
    '..........tT............',
    '........................',
    '...XXXXX.XXXX.XXXX.XXX..',
    '...X.....X..X.X..X.X.X..',
    '...XXX...XXXX.XXXX.X.X..',
    '...X.....X.X..X.X..XXX..',
    '...XXXXX.X..X.X..X.X.X..',
    '........................',
    '..OOOOOOOOOOOOOOOOOO..o.',
    '..OeOeOOOOOOOeOeOOO..o.',
    '..OOOOOOOOOOOOOOOOOO....',
    '..eeeeeeeeeeeeeeeeee....',
    '........................',
    '........................',
    '........................',
    '........................',
    '........................',
    '........................',
    '........................',
    '........................',
]

# 9. HEADSET - front pig with headphones
headset = [
    '........................',
    '........................',
    '.......bbbbbbbbb........',
    '......bBBBBBBBBBb.......',
    '.....bBBBBBBBBBBBb......',
    '....bBB.........BBb.....',
    '....bBB.OOOOOOO.BBb.....',
    '....BB..OOOOOOO..BB.....',
    '....BB..OOOOOOO..BB.....',
    '....BB..OOOOOOO..BB.....',
    '....BBOOOOOOOOOOOOBB.....',
    '....BBOOOOOOOOOOOOBB.....',
    '......OOeOOOOOeOOO......',
    '......OOeOOOOOeOOO......',
    '......OOOOOOOOOOOO......',
    '...OOO.OOOOOOOO.OOO....',
    '...OOO.OOOOOOOO.OOO....',
    '......OOOOOOOOOOOO......',
    '......OO..OO..OO........',
    '......OO..OO..OO........',
    '......OO..OO..OO........',
    '........................',
    '........................',
    '........................',
]

if __name__ == '__main__':
    print('Generating mascot sprites (24x24 grid, 6px/cell)...')
    make_sprite(idea, 'idea.png')
    make_sprite(basic, 'basic.png')
    make_sprite(bird, 'bird.png')
    make_sprite(sparkle, 'sparkle.png')
    make_sprite(worker, 'worker.png')
    make_sprite(cool, 'cool.png')
    make_sprite(pirate, 'pirate.png')
    make_sprite(error, 'error.png')
    make_sprite(headset, 'headset.png')
    print('Done!')

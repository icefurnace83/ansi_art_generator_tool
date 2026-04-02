import os
import sys
import time
from PIL import Image, ImageFilter, UnidentifiedImageError

try:
    import msvcrt
except ImportError:import os
import sys
import time
from PIL import Image, ImageFilter, UnidentifiedImageError

ANSI_BLOCK_SIZES = [(2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8)]

ASCII_CHARS = '@%#*+=-:. '

IMAGE_FILTERS = {
    "None": None,
    "Box Blur": ImageFilter.BoxBlur(1),
    "Gaussian Blur": ImageFilter.GaussianBlur(1),
    "Sharpen": ImageFilter.SHARPEN,
    "Emboss": ImageFilter.EMBOSS,
    "Contour": ImageFilter.CONTOUR
}
FILTER_NAMES = list(IMAGE_FILTERS.keys())

class Colors:
    ENDC = '\033[0m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    RED = '\033[91m'
    YELLOW = '\033[93m'

class AnsiControl:
    CLEAR_SCREEN = "\033[2J\033[H"

MERGED_GLYPH_MAP = [
    (0, 50,   ['█', '▓', '▞', '▚', '■']), # Darkest characters
    (51, 100, ['▒', '╬', '♠', '◈', '▣', '▛', '▜']), # Medium-dark characters
    (101,180, ['░', ':', '·', '-', '+', '=']), # Medium-light characters
    (181,255, ['.', ',', ' ']) # Lightest characters
]

def clear_screen():
    sys.stdout.write(AnsiControl.CLEAR_SCREEN)
    sys.stdout.flush()

def get_brightness(rgb):
    r, g, b = rgb
    return r * 0.299 + g * 0.587 + b * 0.114

def get_average_rgb(pixels):
    total_r = sum(p[0] for p in pixels)
    total_g = sum(p[1] for p in pixels)
    total_b = sum(p[2] for p in pixels)
    num_pixels = len(pixels)
    return (total_r // num_pixels, total_g // num_pixels, total_b // num_pixels)

def pick_colors(pixels):
    sorted_pixels = sorted(pixels, key=get_brightness)
    if len(sorted_pixels) < 4:
        if len(sorted_pixels) == 0: return (0,0,0), (0,0,0)
        avg_rgb = get_average_rgb(sorted_pixels)
        return avg_rgb, (0,0,0)
    return get_average_rgb(sorted_pixels[2:]), get_average_rgb(sorted_pixels[:2])

def pick_glyph(brightness):
    for low, high, glyphs in MERGED_GLYPH_MAP:
        if low <= brightness <= high:
            return glyphs[int(brightness % len(glyphs))]
    return '░'

def process_image(image_obj, mode, output_width, block_size, image_filter):
    if mode == 'ascii':
        return render_ascii(image_obj, output_width)
    elif mode == 'ansi':
        return render_ansi(image_obj, output_width, block_size, image_filter)
    return [""]

def render_ascii(img, output_width):
    img_copy = img.copy().convert('L')
    width, height = img_copy.size
    aspect_ratio = height / width
    output_height = int(output_width * aspect_ratio * 0.55)
    img_copy = img_copy.resize((output_width, output_height))
    pixels = img_copy.getdata()
    ascii_art = []
    line = []
    for pixel_index, pixel_value in enumerate(pixels):
        index = int(pixel_value / 256 * len(ASCII_CHARS))
        line.append(ASCII_CHARS[index])
        if (pixel_index + 1) % output_width == 0:
            ascii_art.append("".join(line))
            line = []
    return ascii_art

def render_ansi(img, output_width, block_size, image_filter):
    img_copy = img.copy()
    if img_copy.mode != "RGB":
        if img_copy.mode == "RGBA":
            base = Image.new("RGB", img_copy.size, (0, 0, 0))
            img_copy = Image.alpha_composite(base, img_copy.convert("RGBA")).convert("RGB")
        else:
            img_copy = img_copy.convert("RGB")
    if image_filter:
        img_copy = img_copy.filter(image_filter)
    block_w, block_h = block_size
    w, h = img_copy.size
    effective_w = (w // block_w) * block_w
    effective_h = (h // block_h) * block_h
    img_copy = img_copy.crop((0, 0, effective_w, effective_h))
    target_ansi_cols = output_width
    current_ansi_cols = effective_w // block_w    
    if current_ansi_cols > target_ansi_cols:
        scale_factor = target_ansi_cols / current_ansi_cols
        img_copy = img_copy.resize((int(effective_w * scale_factor), int(effective_h * scale_factor)), Image.Resampling.LANCZOS)
        effective_w, effective_h = img_copy.size
    ansi_lines = []
    for y in range(0, effective_h, block_h):
        line = []
        for x in range(0, effective_w, block_w):
            pixels = []
            for yi in range(y, y + block_h):
                for xi in range(x, x + block_w):
                    if xi < effective_w and yi < effective_h:
                        pixels.append(img_copy.getpixel((xi, yi)))            
            if not pixels: continue
            fg, bg = pick_colors(pixels)
            brightness = get_brightness(get_average_rgb(pixels))
            glyph = pick_glyph(brightness)
            ansi = f"\033[48;2;{bg[0]};{bg[1]};{bg[2]}m\033[38;2;{fg[0]};{fg[1]};{fg[2]}m{glyph}"
            line.append(ansi)
        ansi_lines.append("".join(line) + "\033[0m")
    return ansi_lines

def find_image_candidates(root_dir):
    candidates = []
    search_dirs = [root_dir]
    if os.path.isdir(os.path.join(root_dir, "images")):
        search_dirs.append(os.path.join(root_dir, "images"))
    for s_dir in search_dirs:
        for filename in os.listdir(s_dir):
            f_path = os.path.join(s_dir, filename)
            if os.path.isfile(f_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                try:
                    Image.open(f_path).close()
                    candidates.append(f_path)
                except UnidentifiedImageError:
                    pass
                except Exception as e:
                    sys.stderr.write(f"{Colors.YELLOW}Warning: Could not process {filename}: {e}{Colors.ENDC}\n")
    return sorted(candidates)

def get_key_press_windows():
    key = msvcrt.getch()
    if key == b'\xe0' or key == b'\x00':
        extended_key = msvcrt.getch()
        if extended_key == b'H': return 'up'
        elif extended_key == b'P': return 'down'
        elif extended_key == b'K': return 'left'
        elif extended_key == b'M': return 'right'
        else: return 'unknown_extended'
    return key.decode('utf-8').lower()

def get_key_press_unix():
    return input("Press key (Left/Right/Up/Down/Space/F/X): ").lower()

def display_help_message(current_mode, current_filter_name, current_block_size):
    print(f"{Colors.CYAN}--- Controls ---{Colors.ENDC}")
    print(f"{Colors.YELLOW}Mode: {current_mode.upper()}{Colors.ENDC}")
    if current_mode == 'ansi':
        print(f"{Colors.YELLOW}Resolution: {current_block_size[0]}x{current_block_size[1]}px per char{Colors.ENDC}")
        print(f"{Colors.YELLOW}Filter: {current_filter_name}{Colors.ENDC}")
    print("  " + Colors.CYAN + "Left/Right Arrows:" + Colors.ENDC + " Cycle images")
    print("  " + Colors.CYAN + "Up/Down Arrows:" + Colors.ENDC + " Change resolution (ANSI only)")
    print("  " + Colors.CYAN + "Spacebar:" + Colors.ENDC + " Toggle ASCII/ANSI mode")
    print("  " + Colors.CYAN + "F:" + Colors.ENDC + " Change filter (ANSI only)")
    print("  " + Colors.CYAN + "X:" + Colors.ENDC + " Exit")
    print(f"{Colors.CYAN}----------------{Colors.ENDC}\n")

def main():
    clear_screen()
    image_candidates = []
    initial_image_path = None
    if len(sys.argv) > 1:
        initial_image_path = sys.argv[1]
        if not os.path.isfile(initial_image_path):
            sys.stderr.write(f"{Colors.RED}Error: Dragged file not found: {initial_image_path}. Scanning directory.{Colors.ENDC}\n")
            initial_image_path = None
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    image_candidates = find_image_candidates(script_dir)
    if not image_candidates:
        sys.stdout.write(f"{Colors.RED}No image files found in '{script_dir}' or its 'images' subdirectory.{Colors.ENDC}\n")
        input(f"\n{Colors.CYAN}Press Enter to exit.{Colors.ENDC}")
        clear_screen()
        return
    current_image_index = 0
    if initial_image_path:
        try:
            current_image_index = image_candidates.index(initial_image_path)
        except ValueError:
            sys.stderr.write(f"{Colors.YELLOW}Warning: Dragged file not in scanned list. Starting with first found image.{Colors.ENDC}\n")
            current_image_index = 0
    current_resolution_index = 0
    render_mode = 'ansi'
    current_filter_index = 0
    needs_redraw = True
    running = True
    while running:
        if needs_redraw:
            clear_screen()
            current_image_path = image_candidates[current_image_index]
            current_block_size = ANSI_BLOCK_SIZES[current_resolution_index]
            current_filter_name = FILTER_NAMES[current_filter_index]
            current_filter_obj = IMAGE_FILTERS[current_filter_name]
            sys.stdout.write(f"{Colors.BLUE}--- Image Art Converter ---{Colors.ENDC}\n")
            sys.stdout.write(f"Displaying: {os.path.basename(current_image_path)}\n")
            display_help_message(render_mode, current_filter_name, current_block_size)
            try:
                img = Image.open(current_image_path)
                output_width = 120 
                art_lines = process_image(img, render_mode, output_width, current_block_size, current_filter_obj)
                for line in art_lines:
                    print(line)
                img.close()
            except FileNotFoundError:
                sys.stderr.write(f"{Colors.RED}Error: Image file not found: {current_image_path}. Skipping.{Colors.ENDC}\n")
                current_image_index = (current_image_index + 1) % len(image_candidates)
                needs_redraw = True
                continue
            except UnidentifiedImageError:
                sys.stderr.write(f"{Colors.RED}Error: Invalid image file: {current_image_path}. Skipping.{Colors.ENDC}\n")
                current_image_index = (current_image_index + 1) % len(image_candidates)
                needs_redraw = True
                continue
            except Exception as e:
                sys.stderr.write(f"{Colors.RED}An unexpected error occurred processing {os.path.basename(current_image_path)}: {str(e)}{Colors.ENDC}\n")
                input(f"\n{Colors.CYAN}Press Enter to continue.{Colors.ENDC}")
                current_image_index = (current_image_index + 1) % len(image_candidates)
                needs_redraw = True
                continue            
            needs_redraw = False
        key = ''
        if msvcrt:
            while not msvcrt.kbhit():
                time.sleep(0.05)
            key = get_key_press_windows()
        else:
            key = get_key_press_unix()
        if key == 'x':
            clear_screen()
            sys.stdout.write(f"{Colors.YELLOW}Are you sure you want to exit? (y/n): {Colors.ENDC}")
            confirm_key = ''
            if msvcrt:
                while not msvcrt.kbhit():
                    time.sleep(0.05)
                confirm_key = get_key_press_windows()
            else:
                confirm_key = get_key_press_unix()
            if confirm_key == 'y':
                running = False
            else:
                needs_redraw = True
        elif key == 'left':
            current_image_index = (current_image_index - 1 + len(image_candidates)) % len(image_candidates)
            needs_redraw = True
        elif key == 'right':
            current_image_index = (current_image_index + 1) % len(image_candidates)
            needs_redraw = True
        elif key == 'up':
            if render_mode == 'ansi':
                current_resolution_index = (current_resolution_index - 1 + len(ANSI_BLOCK_SIZES)) % len(ANSI_BLOCK_SIZES)
                needs_redraw = True
            else:
                sys.stdout.write(f"{Colors.YELLOW}Resolution change only available in ANSI mode. Press Spacebar to switch.{Colors.ENDC}\n")
                time.sleep(1)
        elif key == 'down':
            if render_mode == 'ansi':
                current_resolution_index = (current_resolution_index + 1) % len(ANSI_BLOCK_SIZES)
                needs_redraw = True
            else:
                sys.stdout.write(f"{Colors.YELLOW}Resolution change only available in ANSI mode. Press Spacebar to switch.{Colors.ENDC}\n")
                time.sleep(1)
        elif key == ' ':
            render_mode = 'ansi' if render_mode == 'ascii' else 'ascii'
            sys.stdout.write(f"{Colors.YELLOW}Switched to {render_mode.upper()} mode.{Colors.ENDC}\n")
            time.sleep(1)
            needs_redraw = True
        elif key == 'f':
            if render_mode == 'ansi':
                current_filter_index = (current_filter_index + 1) % len(FILTER_NAMES)
                sys.stdout.write(f"{Colors.YELLOW}Filter changed to {FILTER_NAMES[current_filter_index]}.{Colors.ENDC}\n")
                time.sleep(1)
                needs_redraw = True
            else:
                sys.stdout.write(f"{Colors.YELLOW}Filter change only available in ANSI mode. Press Spacebar to switch.{Colors.ENDC}\n")
                time.sleep(1)
    clear_screen()

if __name__ == "__main__":
    main()
    msvcrt = None
"""
Quicksilver Live QR: A high-performance, dark-themed QR generator with 
real-time DNS lookup, forced HTTPS, and cross-platform support.
"""
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import platform
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import qrcode
from PIL import Image, ImageTk

# --- Theme Colors ---
BG_COLOR = "#1e1e24"
TEXT_COLOR = "#e0e0e0"
ACCENT_COLOR = "#00a8e8"
ENTRY_BG = "#2e2e38"
STATUS_RED = "#ff4b2b"
STATUS_GREEN = "#00b09b"

# Global variable for the current QR Image object
CURRENT_QR_IMG = None
BASE_DIR = Path(__file__).parent


def get_dns_info(url):
    """Fetch DNS info using nslookup (Windows) or dig (Linux)."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or url.split("/")[0]
        if not domain:
            return "DNS: Invalid Input"

        if platform.system() == "Windows":
            cmd = ["nslookup", domain]
            output = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, shell=True
            ).decode()
            lines = [line.strip() for line in output.split("\n") if "Address" in line]
            ip_val = lines[1].replace("Address: ", "") if len(lines) > 1 else "Resolved"
            return f"Domain: {domain}\nIP: {ip_val}"

        output = subprocess.check_output(["dig", domain, "+short"]).decode().strip()
        return f"Domain: {domain}\nIP: {output if output else 'No record'}"
    except (subprocess.SubprocessError, IndexError, UnicodeDecodeError):
        return "Domain Lookup: Failed"


def is_valid_url(url):
    """Checks for a valid domain structure using named groups."""
    pattern = re.compile(
        r"^(?P<protocol>(https?|ftp)://)?"
        r"(?P<host>"
            r"([a-z0-9-]+\.)+[a-z]{2,63}"
            r"|localhost|"
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(/.*)?$",
        re.IGNORECASE,
    )
    match = re.match(pattern, url)
    # FIX: Must return the boolean result
    return match is not None and "." in url


def copy_qr_to_clipboard(_=None):
    """Copies current URL to clipboard with visual feedback."""
    raw_url = input_var.get().strip()
    if raw_url:
        # Consistency check for HTTPS
        if not re.match(r"^[a-z]+://", raw_url, re.I):
            final_url = f"https://{raw_url}"
        else:
            final_url = re.sub(r"^http://", "https://", raw_url, flags=re.I)
        
        root.clipboard_clear()
        root.clipboard_append(final_url)
        messagebox.showinfo("Quicksilver", f"Copied to clipboard:\n{final_url}")


def on_type(*_):
    """Updates status light and generates QR on the fly."""
    raw_data = input_var.get().strip()

    if not raw_data:
        status_light.itemconfig(light_circle, fill=BG_COLOR, outline=BG_COLOR)
        dns_label.config(text="DNS Info: Waiting...")
        final_url_label.config(text="")
        return

    if is_valid_url(raw_data):
        status_light.itemconfig(light_circle, fill=STATUS_GREEN, outline=STATUS_GREEN)
        if not re.match(r"^[a-z]+://", raw_data, re.I):
            final_data = f"https://{raw_data}"
        else:
            final_data = re.sub(r"^http://", "https://", raw_data, flags=re.I)

        final_url_label.config(text=f"Encoded: {final_data}")
        auto_generate(final_data, skip_dns=False)
    else:
        status_light.itemconfig(light_circle, fill=STATUS_RED, outline=STATUS_RED)
        final_url_label.config(text="Invalid URL Structure")
        dns_label.config(text="DNS Info: Invalid Target")
        auto_generate(raw_data, skip_dns=True)


def auto_generate(data, skip_dns=False):
    """Core QR engine."""
    global CURRENT_QR_IMG # pylint: disable=global-statement
    if not skip_dns:
        dns_label.config(text=get_dns_info(data))

    try:
        qr_gen = qrcode.QRCode(
            version=1, box_size=10, border=4,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
        )
        qr_gen.add_data(data)
        qr_gen.make(fit=True)
        CURRENT_QR_IMG = qr_gen.make_image(fill_color="black", back_color="white").convert("RGB")

        logo_path = BASE_DIR / "logo.jpg"
        if logo_path.exists():
            logo = Image.open(logo_path)
            qr_w, _ = CURRENT_QR_IMG.size
            logo_size = qr_w // 5
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            pos = ((qr_w - logo_size) // 2, (qr_w - logo_size) // 2)
            CURRENT_QR_IMG.paste(logo, pos)

        preview = CURRENT_QR_IMG.resize((250, 250))
        tk_img = ImageTk.PhotoImage(preview)
        qr_label.config(image=tk_img)
        qr_label.image = tk_img
    except (ValueError, OSError):
        pass


def save_file(fmt):
    """Saves the QR code."""
    if CURRENT_QR_IMG is None:
        return
    file_path = filedialog.asksaveasfilename(
        initialfile="quicksilver_qr",
        defaultextension=f".{fmt.lower()}",
        filetypes=[(f"{fmt} files", f"*.{fmt.lower()}")],
    )
    if file_path:
        CURRENT_QR_IMG.save(file_path, fmt.upper())
        messagebox.showinfo("Success", f"Saved to {fmt}!")


# --- UI Setup ---
root = tk.Tk()
root.title("Quicksilver")
root.configure(bg=BG_COLOR)
root.geometry("500x820")

# Icon Switch
try:
    icon_p = BASE_DIR / "icon.ico"
    if platform.system() == "Windows":
        root.iconbitmap(str(icon_p))
    else:
        icon_img = ImageTk.PhotoImage(Image.open(icon_p))
        root.iconphoto(False, icon_img)
except (tk.TclError, OSError):
    pass

# Header
header_frame = tk.Frame(root, bg=BG_COLOR)
header_frame.pack(pady=(25, 5))

tk.Label(header_frame, text="Valid URL:", fg=ACCENT_COLOR, 
         bg=BG_COLOR, font=("Arial", 14, "bold")).pack(side=tk.LEFT)

status_light = tk.Canvas(header_frame, width=20, height=20, bg=BG_COLOR, highlightthickness=0)
light_circle = status_light.create_oval(5, 5, 15, 15, fill=BG_COLOR)
status_light.pack(side=tk.LEFT, padx=10)

# Input Row
input_frame = tk.Frame(root, bg=BG_COLOR)
input_frame.pack(pady=10, padx=20)

tk.Label(input_frame, text="URL:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

input_var = tk.StringVar()
input_var.trace_add("write", on_type)
entry = tk.Entry(input_frame, textvariable=input_var, width=35, font=("Arial", 11), 
                 bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, relief="flat", borderwidth=8)
entry.pack(side=tk.LEFT)

final_url_label = tk.Label(root, text="", fg=ACCENT_COLOR, bg=BG_COLOR, font=("Arial", 9, "italic"))
final_url_label.pack()

dns_label = tk.Label(root, text="DNS Info: Waiting...", fg=ACCENT_COLOR, bg=ENTRY_BG, 
                     font=("Consolas" if platform.system() == "Windows" else "Monospace", 9),
                     padx=15, pady=12, justify="left", width=52)
dns_label.pack(pady=15, padx=20)

# QR Preview Area (ONE definition only)
qr_label = tk.Label(root, bg=BG_COLOR, cursor="hand2")
qr_label.pack(pady=10)
qr_label.bind("<Button-1>", copy_qr_to_clipboard)

tk.Label(root, text="(Click to Copy to Clipboard)", fg=ACCENT_COLOR, 
         bg=BG_COLOR, font=("Arial", 8)).pack()

# Save Buttons Frame
btn_frame = tk.Frame(root, bg=BG_COLOR)
btn_frame.pack(pady=20)

tk.Button(btn_frame, text="💾 SAVE PDF", command=lambda: save_file("PDF"), 
          bg=BG_COLOR, fg=ACCENT_COLOR, relief="flat", highlightthickness=1, 
          highlightbackground=ACCENT_COLOR, padx=25, pady=10).pack(side=tk.LEFT, padx=15)

tk.Button(btn_frame, text="🖼️ SAVE PNG", command=lambda: save_file("PNG"), 
          bg=BG_COLOR, fg=ACCENT_COLOR, relief="flat", highlightthickness=1, 
          highlightbackground=ACCENT_COLOR, padx=25, pady=10).pack(side=tk.LEFT, padx=15)

if __name__ == "__main__":
    on_type()
    root.mainloop()
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path

from PIL import Image, ImageTk

from background_remover import BackgroundRemover
from model_manager import (
    model_exists,
    get_model,
    ModelDownloadCancelled,
    set_model_folder
)


# ==================================================
# WINDOW
# ==================================================

window = tk.Tk()
window.title("Background Remover")
window.geometry("950x900")
window.minsize(650, 700)
window.configure(bg="#15171a")


# ==================================================
# COLORS
# ==================================================

BG = "#15171a"
CARD = "#1e2125"
CARD_DARK = "#191b1f"
BORDER = "#30343a"

TEXT = "#f2f4f7"
TEXT_SECONDARY = "#aeb5bf"

ACCENT = "#6c8cff"
ACCENT_HOVER = "#7d9aff"

SUCCESS = "#62d99b"
WARNING = "#e5b75f"
ERROR = "#ef7777"


# ==================================================
# STATE
# ==================================================

selected_image = None
displayed_image = None
result_image = None
remover = None
processing = False
download_cancel_event = threading.Event()
download_in_progress = False


# ==================================================
# SETTINGS
# ==================================================

processing_size = tk.IntVar(value=1024)
removal_tolerance = tk.IntVar(value=0)
edge_smoothness = tk.IntVar(value=0)


# ==================================================
# IMAGE DISPLAY
# ==================================================

def show_image(image):
    global displayed_image

    preview = image.copy()
    preview.thumbnail((680, 480))

    displayed_image = ImageTk.PhotoImage(preview)

    image_label.config(
        image=displayed_image,
        text=""
    )


# ==================================================
# STATUS
# ==================================================

def set_status(text, status="normal"):
    status_label.config(text=text)

    if status == "success":
        status_label.config(fg=SUCCESS)
    elif status == "warning":
        status_label.config(fg=WARNING)
    elif status == "error":
        status_label.config(fg=ERROR)
    else:
        status_label.config(fg=TEXT_SECONDARY)


# ==================================================
# MODEL LOADING
# ==================================================

def update_download_progress(downloaded, total):
    if total <= 0:
        return

    downloaded_mb = downloaded / (1024 * 1024)
    total_mb = total / (1024 * 1024)

    percent = (downloaded / total) * 100

    window.after(
        0,
        lambda: set_status(
            f"Downloading AI model... "
            f"{downloaded_mb:.0f} MB / "
            f"{total_mb:.0f} MB "
            f"({percent:.0f}%)"
        )
    )


def stop_download():
    global download_in_progress

    if not download_in_progress:
        return

    download_cancel_event.set()

    stop_download_button.config(
        state="disabled"
    )

    locate_model_button.config(
        state="disabled"
    )

    set_status(
        "Stopping download..."
    )


def locate_model():
    if download_in_progress:
        return

    folder = filedialog.askdirectory(
        title="Select your RMBG-2.0 model folder"
    )

    if not folder:
        return

    try:
        model_folder = set_model_folder(
            folder
        )

        set_status(
            f"Model found: {model_folder}"
        )

        start_model_loading()

    except ValueError as error:
        set_status(
            str(error),
            "error"
        )


def start_model_loading():
    global download_in_progress

    # If the model already exists, load it automatically.
    # If it does not exist, DO NOT start a download automatically.
    if model_exists():

        set_status(
            "Loading AI model..."
        )

        locate_model_button.pack_forget()
        download_model_button.pack_forget()
        stop_download_button.pack_forget()

        select_button.config(
            state="disabled"
        )

        remove_button.config(
            state="disabled"
        )

        reset_button.config(
            state="disabled"
        )

        loading_frame.pack(
            pady=(0, 15)
        )

        loading_text.config(
            text="Loading AI model..."
        )

        loading_bar.start(10)

        download_cancel_event.clear()
        download_in_progress = False

        thread = threading.Thread(
            target=load_model,
            daemon=True
        )

        thread.start()

    else:

        download_in_progress = False

        select_button.config(
            state="disabled"
        )

        remove_button.config(
            state="disabled"
        )

        reset_button.config(
            state="normal"
        )

        loading_frame.pack(
            pady=(0, 15)
        )

        loading_bar.stop()

        loading_text.config(
            text="RMBG-2.0 is not installed."
        )

        set_status(
            "AI model not found. Locate an existing model or start the download.",
            "warning"
        )

        locate_model_button.config(
            state="normal"
        )

        locate_model_button.pack(
            pady=(8, 0)
        )

        download_model_button.config(
            state="normal"
        )

        download_model_button.pack(
            pady=(8, 0)
        )

        stop_download_button.pack_forget()


def start_download():
    global download_in_progress

    if download_in_progress:
        return

    download_cancel_event.clear()
    download_in_progress = True

    locate_model_button.config(
        state="disabled"
    )

    download_model_button.config(
        state="disabled"
    )

    stop_download_button.config(
        state="normal"
    )

    locate_model_button.pack_forget()
    download_model_button.pack_forget()
    stop_download_button.pack(
        pady=(8, 0)
    )

    select_button.config(
        state="disabled"
    )

    remove_button.config(
        state="disabled"
    )

    reset_button.config(
        state="disabled"
    )

    loading_frame.pack(
        pady=(0, 15)
    )

    loading_text.config(
        text="Downloading AI model..."
    )

    loading_bar.start(10)

    set_status(
        "Starting AI model download..."
    )

    thread = threading.Thread(
        target=load_model,
        daemon=True
    )

    thread.start()


def load_model():
    global remover
    global download_in_progress

    try:

        if download_in_progress:

            window.after(
                0,
                lambda: set_status(
                    "Downloading AI model... 0 MB"
                )
            )

            get_model(
                progress_callback=update_download_progress,
                cancel_event=download_cancel_event
            )

            download_in_progress = False

        else:

            get_model()

        remover = BackgroundRemover()

        window.after(
            0,
            model_loaded
        )

    except ModelDownloadCancelled:

        download_in_progress = False

        window.after(
            0,
            download_cancelled
        )

    except Exception as error:

        download_in_progress = False

        error_message = str(error)

        window.after(
            0,
            lambda: model_load_failed(
                error_message
            )
        )


def model_loaded():

    global download_in_progress

    download_in_progress = False

    loading_bar.stop()
    loading_frame.pack_forget()

    locate_model_button.pack_forget()
    download_model_button.pack_forget()
    stop_download_button.pack_forget()

    select_button.config(
        state="normal"
    )

    remove_button.config(
        state="disabled"
    )

    reset_button.config(
        state="normal"
    )

    set_status(
        "AI model ready. Select an image to get started.",
        "success"
    )


def model_load_failed(error_message):

    global download_in_progress

    download_in_progress = False

    loading_bar.stop()

    loading_text.config(
        text="Model loading failed."
    )

    set_status(
        f"Model loading failed: {error_message}",
        "error"
    )

    select_button.config(
        state="disabled"
    )

    remove_button.config(
        state="disabled"
    )

    reset_button.config(
        state="normal"
    )

    locate_model_button.config(
        state="normal"
    )

    download_model_button.config(
        state="normal"
    )

    stop_download_button.pack_forget()

    loading_frame.pack(
        pady=(0, 15)
    )

    locate_model_button.pack(
        pady=(8, 0)
    )

    download_model_button.pack(
        pady=(8, 0)
    )


def download_cancelled():

    loading_bar.stop()

    loading_text.config(
        text="Download stopped."
    )

    set_status(
        "Download stopped. The model was not loaded.",
        "warning"
    )

    select_button.config(
        state="disabled"
    )

    remove_button.config(
        state="disabled"
    )

    reset_button.config(
        state="normal"
    )

    locate_model_button.config(
        state="normal"
    )

    locate_model_button.pack(
        pady=(8, 0)
    )

    download_model_button.config(
        state="normal"
    )

    download_model_button.pack(
        pady=(8, 0)
    )

    stop_download_button.pack_forget()

# ==================================================
# SELECT IMAGE
# ==================================================

def select_image():
    global selected_image, result_image

    if processing:
        return

    file_path = filedialog.askopenfilename(
        title="Select an image",
        filetypes=[
            (
                "Image files",
                "*.png *.jpg *.jpeg *.webp"
            ),
            (
                "PNG files",
                "*.png"
            ),
            (
                "JPEG files",
                "*.jpg *.jpeg"
            ),
            (
                "WebP files",
                "*.webp"
            )
        ]
    )

    if not file_path:
        return

    selected_image = Path(file_path)
    result_image = None

    try:
        image = Image.open(
            selected_image
        ).convert("RGB")

        show_image(image)

        file_label.config(
            text=selected_image.name
        )

        file_details_label.config(
            text=f"{image.width} × {image.height}"
        )

        if remover is not None:
            remove_button.config(
                state="normal"
            )

        save_button.pack_forget()
        dont_save_button.pack_forget()

        set_status(
            "Ready to remove background"
        )

    except Exception as error:
        set_status(
            f"Could not open image: {error}",
            "error"
        )


# ==================================================
# REMOVE BACKGROUND
# ==================================================

def remove_background():
    global processing

    if selected_image is None:
        return

    if remover is None:
        set_status(
            "AI model is still loading...",
            "warning"
        )
        return

    if processing:
        return

    processing = True

    # Get the settings before starting the worker thread.
    current_size = processing_size.get()
    current_tolerance = removal_tolerance.get()
    current_smoothness = edge_smoothness.get()

    select_button.config(
        state="disabled"
    )

    remove_button.config(
        state="disabled"
    )

    reset_button.config(
        state="disabled"
    )

    save_button.pack_forget()
    dont_save_button.pack_forget()

    loading_frame.pack(
        pady=(0, 15)
    )

    loading_bar.start(10)

    set_status(
        "Removing background... AI is processing your image",
        "warning"
    )

    thread = threading.Thread(
        target=process_image,
        args=(
            current_size,
            current_tolerance,
            current_smoothness
        ),
        daemon=True
    )

    thread.start()


def process_image(
    current_size,
    current_tolerance,
    current_smoothness
):
    try:
        result = remover.remove_background(
            selected_image,
            processing_size=current_size,
            tolerance=current_tolerance,
            edge_smoothness=current_smoothness
        )

        window.after(
            0,
            lambda: processing_finished(result)
        )

    except Exception as error:
        window.after(
            0,
            lambda: processing_failed(str(error))
        )


def processing_finished(result):
    global result_image, processing

    result_image = result

    loading_bar.stop()
    loading_frame.pack_forget()

    show_image(result_image)

    set_status(
        "Background removed successfully",
        "success"
    )

    select_button.config(
        state="normal"
    )

    remove_button.config(
        state="normal"
    )

    reset_button.config(
        state="normal"
    )

    save_button.pack(
        side="left",
        padx=5
    )

    dont_save_button.pack(
        side="left",
        padx=5
    )

    processing = False


def processing_failed(error):
    global processing

    loading_bar.stop()
    loading_frame.pack_forget()

    set_status(
        f"Error: {error}",
        "error"
    )

    select_button.config(
        state="normal"
    )

    remove_button.config(
        state="normal"
    )

    reset_button.config(
        state="normal"
    )

    processing = False


# ==================================================
# RESTORE ORIGINAL IMAGE
# ==================================================

def restore_original():
    if selected_image is None:
        return

    try:
        original_image = Image.open(
            selected_image
        ).convert("RGB")

        show_image(original_image)

    except Exception as error:
        set_status(
            f"Could not restore image: {error}",
            "error"
        )


# ==================================================
# SAVE
# ==================================================

def save_result():
    if result_image is None:
        return

    save_path = filedialog.asksaveasfilename(
        title="Save Image",
        defaultextension=".png",
        filetypes=[
            (
                "PNG image",
                "*.png"
            )
        ],
        initialfile=(
            f"{selected_image.stem}_no_bg.png"
        )
    )

    if not save_path:
        return

    try:
        result_image.save(
            save_path
        )

        restore_original()

        set_status(
            f"Saved: {Path(save_path).name}",
            "success"
        )

        save_button.pack_forget()
        dont_save_button.pack_forget()

    except Exception as error:
        set_status(
            f"Error saving image: {error}",
            "error"
        )


def dont_save():
    global result_image

    result_image = None

    restore_original()

    save_button.pack_forget()
    dont_save_button.pack_forget()

    set_status(
        "Result discarded — original image restored"
    )


# ==================================================
# SETTINGS
# ==================================================

def reset_settings():
    processing_size.set(1024)
    removal_tolerance.set(0)
    edge_smoothness.set(0)

    processing_size_label.config(
        text="1024 × 1024"
    )

    removal_tolerance_label.config(
        text="0%"
    )

    edge_smoothness_label.config(
        text="0"
    )

    set_status(
        "Settings reset to recommended defaults"
    )


def update_processing_size(value):
    processing_size_label.config(
        text=f"{int(float(value))} × {int(float(value))}"
    )


def update_tolerance(value):
    removal_tolerance_label.config(
        text=f"{int(float(value))}%"
    )


def update_smoothness(value):
    edge_smoothness_label.config(
        text=f"{int(float(value))}"
    )


# ==================================================
# SCROLLABLE CONTENT
# ==================================================

canvas = tk.Canvas(
    window,
    bg=BG,
    highlightthickness=0
)

canvas.pack(
    side="left",
    fill="both",
    expand=True
)


scrollbar = ttk.Scrollbar(
    window,
    orient="vertical",
    command=canvas.yview
)

scrollbar.pack(
    side="right",
    fill="y"
)


canvas.configure(
    yscrollcommand=scrollbar.set
)


content = tk.Frame(
    canvas,
    bg=BG
)


canvas_window = canvas.create_window(
    (0, 0),
    window=content,
    anchor="n"
)


def update_scroll_region(event=None):
    canvas.configure(
        scrollregion=canvas.bbox("all")
    )


content.bind(
    "<Configure>",
    update_scroll_region
)


def resize_content(event):
    canvas.itemconfig(
        canvas_window,
        width=event.width
    )


canvas.bind(
    "<Configure>",
    resize_content
)


def on_mousewheel(event):
    canvas.yview_scroll(
        int(-1 * (event.delta / 120)),
        "units"
    )


canvas.bind_all(
    "<MouseWheel>",
    on_mousewheel
)


# ==================================================
# HEADER
# ==================================================

header = tk.Frame(
    content,
    bg=BG
)

header.pack(
    fill="x",
    padx=30,
    pady=(25, 15)
)


title = tk.Label(
    header,
    text="Background Remover",
    bg=BG,
    fg=TEXT,
    font=("Segoe UI", 28, "bold")
)

title.pack()


subtitle = tk.Label(
    header,
    text="Remove image backgrounds using local AI",
    bg=BG,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 12)
)

subtitle.pack(
    pady=(5, 0)
)


local_label = tk.Label(
    header,
    text="LOCAL AI • YOUR IMAGE STAYS ON YOUR PC",
    bg=BG,
    fg=SUCCESS,
    font=("Segoe UI", 9, "bold")
)

local_label.pack(
    pady=(8, 0)
)


# ==================================================
# IMAGE CARD
# ==================================================

image_card = tk.Frame(
    content,
    bg=CARD,
    highlightbackground=BORDER,
    highlightthickness=1
)

image_card.pack(
    fill="x",
    padx=30,
    pady=10
)


image_header = tk.Frame(
    image_card,
    bg=CARD
)

image_header.pack(
    fill="x",
    padx=20,
    pady=(15, 8)
)


image_title = tk.Label(
    image_header,
    text="Image",
    bg=CARD,
    fg=TEXT,
    font=("Segoe UI", 17, "bold")
)

image_title.pack(
    side="left"
)


select_button = tk.Button(
    image_header,
    text="Select Image",
    command=select_image,
    bg=ACCENT,
    fg="white",
    activebackground=ACCENT_HOVER,
    activeforeground="white",
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 11, "bold"),
    padx=18,
    pady=7,
    cursor="hand2"
)

select_button.pack(
    side="right"
)


file_info = tk.Frame(
    image_card,
    bg=CARD
)

file_info.pack(
    fill="x",
    padx=20,
    pady=(0, 10)
)


file_label = tk.Label(
    file_info,
    text="No image selected",
    bg=CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 10)
)

file_label.pack(
    side="left"
)


file_details_label = tk.Label(
    file_info,
    text="",
    bg=CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 10)
)

file_details_label.pack(
    side="right"
)


image_frame = tk.Frame(
    image_card,
    bg=CARD_DARK,
    width=700,
    height=500,
    highlightbackground=BORDER,
    highlightthickness=1
)

image_frame.pack(
    padx=20,
    pady=(0, 20)
)

image_frame.pack_propagate(False)


image_label = tk.Label(
    image_frame,
    text="Select an image to get started",
    bg=CARD_DARK,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 13)
)

image_label.pack(
    expand=True
)


# ==================================================
# LOADING
# ==================================================

loading_frame = tk.Frame(
    content,
    bg=BG
)


loading_text = tk.Label(
    loading_frame,
    text="Working...",
    bg=BG,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9)
)

loading_text.pack(
    pady=(0, 5)
)


loading_bar = ttk.Progressbar(
    loading_frame,
    mode="indeterminate",
    length=400
)

loading_bar.pack()
locate_model_button = tk.Button(
    loading_frame,
    text="Locate Existing Model",
    command=locate_model,
    bg=CARD,
    fg=TEXT,
    activebackground=BORDER,
    activeforeground=TEXT,
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 10),
    padx=15,
    pady=6,
    cursor="hand2"
)

download_model_button = tk.Button(
    loading_frame,
    text="Download AI Model",
    command=start_download,
    bg=ACCENT,
    fg="white",
    activebackground=ACCENT_HOVER,
    activeforeground="white",
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 10, "bold"),
    padx=15,
    pady=6,
    cursor="hand2"
)


stop_download_button = tk.Button(
    loading_frame,
    text="Stop Download",
    command=stop_download,
    bg="#3a2020",
    fg=TEXT,
    activebackground="#512828",
    activeforeground=TEXT,
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 10, "bold"),
    padx=15,
    pady=6,
    cursor="hand2"
)

# ==================================================
# SETTINGS CARD
# ==================================================

settings_card = tk.Frame(
    content,
    bg=CARD,
    highlightbackground=BORDER,
    highlightthickness=1
)

settings_card.pack(
    fill="x",
    padx=30,
    pady=10
)


settings_title = tk.Label(
    settings_card,
    text="Settings",
    bg=CARD,
    fg=TEXT,
    font=("Segoe UI", 17, "bold")
)

settings_title.pack(
    anchor="w",
    padx=20,
    pady=(18, 3)
)


settings_subtitle = tk.Label(
    settings_card,
    text="Adjust how the AI processes your image",
    bg=CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 10)
)

settings_subtitle.pack(
    anchor="w",
    padx=20,
    pady=(0, 18)
)


# --------------------------------------------------
# Processing Size
# --------------------------------------------------

processing_label = tk.Label(
    settings_card,
    text="Processing Size",
    bg=CARD,
    fg=TEXT,
    font=("Segoe UI", 12, "bold")
)

processing_label.pack()


processing_size_label = tk.Label(
    settings_card,
    text="1024 × 1024",
    bg=CARD,
    fg=ACCENT,
    font=("Segoe UI", 11, "bold")
)

processing_size_label.pack(
    pady=(3, 2)
)


processing_description = tk.Label(
    settings_card,
    text=(
        "Resolution used when the AI analyzes the image.\n"
        "Higher values may preserve more detail but take longer.\n"
        "1024 is recommended for most images."
    ),
    bg=CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9),
    justify="center"
)

processing_description.pack(
    pady=(0, 5)
)


processing_slider = tk.Scale(
    settings_card,
    from_=512,
    to=2048,
    resolution=256,
    orient="horizontal",
    length=450,
    variable=processing_size,
    command=update_processing_size,
    bg=CARD,
    fg=TEXT,
    troughcolor=CARD_DARK,
    highlightthickness=0,
    activebackground=ACCENT
)

processing_slider.pack(
    pady=(0, 20)
)


# --------------------------------------------------
# Removal Tolerance
# --------------------------------------------------

tolerance_title = tk.Label(
    settings_card,
    text="Removal Tolerance",
    bg=CARD,
    fg=TEXT,
    font=("Segoe UI", 12, "bold")
)

tolerance_title.pack()


removal_tolerance_label = tk.Label(
    settings_card,
    text="0%",
    bg=CARD,
    fg=ACCENT,
    font=("Segoe UI", 11, "bold")
)

removal_tolerance_label.pack(
    pady=(3, 2)
)


tolerance_description = tk.Label(
    settings_card,
    text=(
        "Controls how aggressively uncertain areas are removed.\n"
        "Higher values remove more faint background areas,\n"
        "but can also remove parts of your subject."
    ),
    bg=CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9),
    justify="center"
)

tolerance_description.pack(
    pady=(0, 5)
)


tolerance_slider = tk.Scale(
    settings_card,
    from_=0,
    to=100,
    orient="horizontal",
    length=450,
    variable=removal_tolerance,
    command=update_tolerance,
    bg=CARD,
    fg=TEXT,
    troughcolor=CARD_DARK,
    highlightthickness=0,
    activebackground=ACCENT
)

tolerance_slider.pack(
    pady=(0, 20)
)


# --------------------------------------------------
# Edge Smoothness
# --------------------------------------------------

smoothness_title = tk.Label(
    settings_card,
    text="Edge Smoothness",
    bg=CARD,
    fg=TEXT,
    font=("Segoe UI", 12, "bold")
)

smoothness_title.pack()


edge_smoothness_label = tk.Label(
    settings_card,
    text="0",
    bg=CARD,
    fg=ACCENT,
    font=("Segoe UI", 11, "bold")
)

edge_smoothness_label.pack(
    pady=(3, 2)
)


smoothness_description = tk.Label(
    settings_card,
    text=(
        "Softens the edges around the subject.\n"
        "Useful for rough or jagged edges,\n"
        "but too much can make the subject blurry."
    ),
    bg=CARD,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9),
    justify="center"
)

smoothness_description.pack(
    pady=(0, 5)
)


smoothness_slider = tk.Scale(
    settings_card,
    from_=0,
    to=10,
    orient="horizontal",
    length=450,
    variable=edge_smoothness,
    command=update_smoothness,
    bg=CARD,
    fg=TEXT,
    troughcolor=CARD_DARK,
    highlightthickness=0,
    activebackground=ACCENT
)

smoothness_slider.pack(
    pady=(0, 15)
)


reset_button = tk.Button(
    settings_card,
    text="Reset Settings",
    command=reset_settings,
    bg=CARD_DARK,
    fg=TEXT,
    activebackground=BORDER,
    activeforeground=TEXT,
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 10),
    padx=15,
    pady=7,
    cursor="hand2"
)

reset_button.pack(
    pady=(0, 20)
)


# ==================================================
# ACTION BUTTON
# ==================================================

action_frame = tk.Frame(
    content,
    bg=BG
)

action_frame.pack(
    fill="x",
    padx=30,
    pady=(10, 5)
)


remove_button = tk.Button(
    action_frame,
    text="Remove Background",
    command=remove_background,
    state="disabled",
    bg=ACCENT,
    fg="white",
    activebackground=ACCENT_HOVER,
    activeforeground="white",
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 13, "bold"),
    padx=25,
    pady=10,
    cursor="hand2"
)

remove_button.pack()


# ==================================================
# SAVE BUTTONS
# ==================================================

save_frame = tk.Frame(
    action_frame,
    bg=BG
)

save_frame.pack(
    pady=(10, 0)
)


save_button = tk.Button(
    save_frame,
    text="Save Image",
    command=save_result,
    bg=SUCCESS,
    fg="#10251b",
    activebackground="#78e5aa",
    activeforeground="#10251b",
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 11, "bold"),
    padx=18,
    pady=7,
    cursor="hand2"
)


dont_save_button = tk.Button(
    save_frame,
    text="Don't Save",
    command=dont_save,
    bg=CARD,
    fg=TEXT,
    activebackground=BORDER,
    activeforeground=TEXT,
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 11),
    padx=18,
    pady=7,
    cursor="hand2"
)


# ==================================================
# STATUS
# ==================================================

status_frame = tk.Frame(
    content,
    bg=BG
)

status_frame.pack(
    fill="x",
    padx=30,
    pady=(5, 30)
)


status_label = tk.Label(
    status_frame,
    text="Starting AI model...",
    bg=BG,
    fg=TEXT_SECONDARY,
    font=("Segoe UI", 9)
)

status_label.pack()


# ==================================================
# START
# ==================================================

start_model_loading()

window.mainloop()

import threading
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path

from PIL import Image, ImageTk

from background_remover import BackgroundRemover


window = tk.Tk()
window.title("Background Remover")
window.geometry("950x900")
window.minsize(650, 700)


selected_image = None
displayed_image = None
result_image = None
remover = None
processing = False


processing_size = tk.IntVar(value=1024)
removal_tolerance = tk.IntVar(value=0)
edge_smoothness = tk.IntVar(value=0)


def show_image(image):
    global displayed_image

    preview = image.copy()
    preview.thumbnail((680, 480))

    displayed_image = ImageTk.PhotoImage(preview)

    image_label.config(
        image=displayed_image,
        text=""
    )


def set_status(text):
    status_label.config(
        text=text
    )


def start_model_loading():
    global remover

    set_status(
        "Loading AI model..."
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

    loading_bar.pack(
        pady=(5, 10)
    )

    loading_bar.start(10)

    thread = threading.Thread(
        target=load_model,
        daemon=True
    )

    thread.start()


def load_model():
    global remover

    try:
        remover = BackgroundRemover()

        window.after(
            0,
            model_loaded
        )

    except Exception as error:
        window.after(
            0,
            lambda: model_load_failed(str(error))
        )


def model_loaded():
    loading_bar.stop()
    loading_bar.pack_forget()

    select_button.config(
        state="normal"
    )

    reset_button.config(
        state="normal"
    )

    set_status(
        f"Ready — AI loaded ({remover.device})"
    )


def model_load_failed(error):
    loading_bar.stop()
    loading_bar.pack_forget()

    select_button.config(
        state="normal"
    )

    reset_button.config(
        state="normal"
    )

    set_status(
        f"Could not load AI model: {error}"
    )


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
            ),
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
            f"Could not open image: {error}"
        )


def remove_background():
    global processing

    if selected_image is None:
        return

    if remover is None:
        set_status(
            "AI model is still loading..."
        )
        return

    if processing:
        return

    processing = True

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

    loading_bar.pack(
        pady=(5, 10)
    )

    loading_bar.start(10)

    set_status(
        "Removing background... AI is processing your image"
    )

    thread = threading.Thread(
        target=process_image,
        daemon=True
    )

    thread.start()


def process_image():
    try:
        result = remover.remove_background(
            selected_image,
            processing_size=processing_size.get(),
            tolerance=removal_tolerance.get(),
            edge_smoothness=edge_smoothness.get()
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
    loading_bar.pack_forget()

    show_image(result_image)

    set_status(
        "Background removed!"
    )

    save_button.pack(
        side="left",
        padx=5
    )

    dont_save_button.pack(
        side="left",
        padx=5
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


def processing_failed(error):
    global processing

    loading_bar.stop()
    loading_bar.pack_forget()

    set_status(
        f"Error: {error}"
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
            f"Could not restore image: {error}"
        )


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
            f"Saved: {Path(save_path).name}"
        )

        save_button.pack_forget()
        dont_save_button.pack_forget()

    except Exception as error:
        set_status(
            f"Error saving image: {error}"
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


def update_scroll_region(event=None):
    canvas.configure(
        scrollregion=canvas.bbox("all")
    )


def on_mousewheel(event):
    canvas.yview_scroll(
        int(-1 * (event.delta / 120)),
        "units"
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


canvas = tk.Canvas(
    window
)

canvas.pack(
    side="left",
    fill="both",
    expand=True
)


scrollbar = tk.Scrollbar(
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
    canvas
)

canvas_window = canvas.create_window(
    (0, 0),
    window=content,
    anchor="n"
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

canvas.bind_all(
    "<MouseWheel>",
    on_mousewheel
)


title = tk.Label(
    content,
    text="Background Remover",
    font=("Arial", 28, "bold")
)

title.pack(
    pady=(25, 5)
)


subtitle = tk.Label(
    content,
    text=(
        "Remove backgrounds from your images "
        "using AI — completely locally"
    ),
    font=("Arial", 12)
)

subtitle.pack(
    pady=(0, 20)
)


select_button = tk.Button(
    content,
    text="Select Image",
    font=("Arial", 13),
    command=select_image,
    width=18,
    height=2
)

select_button.pack()


file_label = tk.Label(
    content,
    text="No image selected",
    font=("Arial", 11)
)

file_label.pack(
    pady=10
)


image_frame = tk.Frame(
    content,
    width=700,
    height=500,
    relief="solid",
    borderwidth=1
)

image_frame.pack(
    pady=10
)

image_frame.pack_propagate(False)


image_label = tk.Label(
    image_frame,
    text="Your image will appear here",
    font=("Arial", 14)
)

image_label.pack(
    expand=True
)


loading_bar = ttk.Progressbar(
    content,
    mode="indeterminate",
    length=400
)


settings_label = tk.Label(
    content,
    text="Settings",
    font=("Arial", 20, "bold")
)

settings_label.pack(
    pady=(25, 15)
)


processing_label = tk.Label(
    content,
    text="Processing Size",
    font=("Arial", 13, "bold")
)

processing_label.pack()


processing_size_label = tk.Label(
    content,
    text="1024 × 1024",
    font=("Arial", 11)
)

processing_size_label.pack(
    pady=(2, 2)
)


processing_description = tk.Label(
    content,
    text=(
        "The resolution used when the AI analyzes the image.\n"
        "Higher values can preserve more detail but take longer.\n"
        "1024 is the recommended setting."
    ),
    font=("Arial", 10),
    justify="center",
    wraplength=600
)

processing_description.pack(
    pady=(0, 5)
)


processing_slider = tk.Scale(
    content,
    from_=512,
    to=2048,
    resolution=256,
    orient="horizontal",
    length=400,
    variable=processing_size,
    command=update_processing_size
)

processing_slider.pack(
    pady=(0, 20)
)


tolerance_title = tk.Label(
    content,
    text="Removal Tolerance",
    font=("Arial", 13, "bold")
)

tolerance_title.pack()


removal_tolerance_label = tk.Label(
    content,
    text="0%",
    font=("Arial", 11)
)

removal_tolerance_label.pack(
    pady=(2, 2)
)


tolerance_description = tk.Label(
    content,
    text=(
        "Controls how aggressively uncertain areas are removed.\n"
        "Higher values remove more faint background areas,\n"
        "but can also remove parts of your subject."
    ),
    font=("Arial", 10),
    justify="center",
    wraplength=600
)

tolerance_description.pack(
    pady=(0, 5)
)


tolerance_slider = tk.Scale(
    content,
    from_=0,
    to=100,
    orient="horizontal",
    length=400,
    variable=removal_tolerance,
    command=update_tolerance
)

tolerance_slider.pack(
    pady=(0, 20)
)


smoothness_title = tk.Label(
    content,
    text="Edge Smoothness",
    font=("Arial", 13, "bold")
)

smoothness_title.pack()


edge_smoothness_label = tk.Label(
    content,
    text="0",
    font=("Arial", 11)
)

edge_smoothness_label.pack(
    pady=(2, 2)
)


smoothness_description = tk.Label(
    content,
    text=(
        "Softens the edges around the subject.\n"
        "Useful for rough or jagged edges,\n"
        "but too much can make the subject blurry."
    ),
    font=("Arial", 10),
    justify="center",
    wraplength=600
)

smoothness_description.pack(
    pady=(0, 5)
)


smoothness_slider = tk.Scale(
    content,
    from_=0,
    to=10,
    orient="horizontal",
    length=400,
    variable=edge_smoothness,
    command=update_smoothness
)

smoothness_slider.pack(
    pady=(0, 15)
)


reset_button = tk.Button(
    content,
    text="Reset Settings",
    font=("Arial", 11),
    width=18,
    command=reset_settings
)

reset_button.pack(
    pady=(0, 20)
)


remove_button = tk.Button(
    content,
    text="Remove Background",
    font=("Arial", 13),
    width=20,
    height=2,
    state="disabled",
    command=remove_background
)

remove_button.pack(
    pady=10
)


save_frame = tk.Frame(
    content
)

save_frame.pack(
    pady=5
)


save_button = tk.Button(
    save_frame,
    text="Save Image",
    font=("Arial", 12),
    width=14,
    command=save_result
)


dont_save_button = tk.Button(
    save_frame,
    text="Don't Save",
    font=("Arial", 12),
    width=14,
    command=dont_save
)


status_label = tk.Label(
    content,
    text="Starting AI model...",
    font=("Arial", 10)
)

status_label.pack(
    pady=10
)


start_model_loading()

window.mainloop()
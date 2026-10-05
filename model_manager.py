from pathlib import Path
import json

import requests
from huggingface_hub import (
    HfApi,
    hf_hub_url,
    get_token
)


MODEL_REPO = "briaai/RMBG-2.0"

REQUIRED_FILES = [
    "config.json",
    "model.safetensors",
    "preprocessor_config.json",
    "birefnet.py",
    "BiRefNet_config.py",
]


DOWNLOAD_MODEL_FOLDER = (
    Path.home()
    / "Downloads"
    / "BackgroundRemover"
    / "models"
    / "RMBG-2.0"
)


APP_DATA_FOLDER = (
    Path.home()
    / "AppData"
    / "Local"
    / "BackgroundRemover"
)


MODEL_LOCATION_FILE = (
    APP_DATA_FOLDER
    / "model_location.json"
)


class ModelDownloadCancelled(Exception):
    pass


def model_folder_is_valid(folder):
    folder = Path(folder)

    if not folder.exists():
        return False

    if not folder.is_dir():
        return False

    return all(
        (folder / file).is_file()
        for file in REQUIRED_FILES
    )


def get_missing_files(folder):
    folder = Path(folder)

    return [
        filename
        for filename in REQUIRED_FILES
        if not (folder / filename).is_file()
    ]


def get_saved_model_folder():
    if not MODEL_LOCATION_FILE.exists():
        return None

    try:
        with open(
            MODEL_LOCATION_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        folder_string = data.get("model_folder")

        if not folder_string:
            return None

        folder = Path(folder_string)

        if model_folder_is_valid(folder):
            print(
                f"RMBG-2.0 found at saved location: {folder}"
            )

            return folder

    except Exception as error:
        print(
            f"Could not read saved model location: {error}"
        )

    return None


def save_model_folder(folder):
    folder = Path(folder)

    APP_DATA_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        MODEL_LOCATION_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            {
                "model_folder": str(folder)
            },
            file,
            indent=4
        )


def find_existing_model():
    saved_folder = get_saved_model_folder()

    if saved_folder is not None:
        return saved_folder

    if model_folder_is_valid(
        DOWNLOAD_MODEL_FOLDER
    ):
        print(
            f"RMBG-2.0 found at default location: "
            f"{DOWNLOAD_MODEL_FOLDER}"
        )

        return DOWNLOAD_MODEL_FOLDER

    return None


def model_exists():
    return find_existing_model() is not None


def get_model(
    progress_callback=None,
    cancel_event=None
):
    """
    Return an existing model.

    If no model exists, download it from Hugging Face.

    Downloading only happens when this function is
    explicitly called by the GUI.
    """

    existing_model = find_existing_model()

    if existing_model is not None:
        print(
            f"Using existing RMBG-2.0 model: "
            f"{existing_model}"
        )

        return existing_model

    model_folder = DOWNLOAD_MODEL_FOLDER

    model_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        "No existing RMBG-2.0 model found."
    )

    print(
        "Getting model file information..."
    )

    api = HfApi()

    model_info = api.model_info(
        MODEL_REPO,
        files_metadata=True
    )

    file_sizes = {}

    for file in model_info.siblings:
        if file.rfilename in REQUIRED_FILES:
            file_sizes[file.rfilename] = file.size

    missing_from_repo = [
        filename
        for filename in REQUIRED_FILES
        if filename not in file_sizes
    ]

    if missing_from_repo:
        raise RuntimeError(
            "The following required RMBG-2.0 files "
            "could not be found on Hugging Face:\n\n"
            + "\n".join(missing_from_repo)
        )

    total_size = sum(
        size
        for size in file_sizes.values()
        if size is not None
    )

    downloaded_total = 0

    # Get the Hugging Face token that is already
    # stored on this computer.
    token = get_token()

    if token is None:
        raise RuntimeError(
            "Hugging Face authentication is required "
            "to download RMBG-2.0.\n\n"
            "Please log in to Hugging Face first."
        )

    headers = {
        "Authorization": f"Bearer {token}"
    }

    for filename in REQUIRED_FILES:

        if cancel_event is not None:
            if cancel_event.is_set():
                raise ModelDownloadCancelled()

        destination = model_folder / filename

        if destination.is_file():

            downloaded_total += destination.stat().st_size

            if progress_callback:
                progress_callback(
                    downloaded_total,
                    total_size
                )

            continue

        print(
            f"Downloading {filename}..."
        )

        url = hf_hub_url(
            repo_id=MODEL_REPO,
            filename=filename
        )

        temporary_file = destination.with_suffix(
            destination.suffix + ".part"
        )

        try:

            with requests.get(
                url,
                headers=headers,
                stream=True,
                timeout=(15, 60)
            ) as response:

                response.raise_for_status()

                with open(
                    temporary_file,
                    "wb"
                ) as output_file:

                    for chunk in response.iter_content(
                        chunk_size=1024 * 1024
                    ):

                        if cancel_event is not None:
                            if cancel_event.is_set():
                                raise ModelDownloadCancelled()

                        if not chunk:
                            continue

                        output_file.write(chunk)

                        downloaded_total += len(chunk)

                        if progress_callback:
                            progress_callback(
                                downloaded_total,
                                total_size
                            )

            temporary_file.replace(
                destination
            )

        except ModelDownloadCancelled:

            if temporary_file.exists():
                temporary_file.unlink()

            raise

        except Exception:

            if temporary_file.exists():
                temporary_file.unlink()

            raise

    if not model_folder_is_valid(
        model_folder
    ):
        raise RuntimeError(
            "The RMBG-2.0 download did not "
            "complete correctly."
        )

    print(
        "RMBG-2.0 download complete."
    )

    save_model_folder(
        model_folder
    )

    return model_folder


def set_model_folder(folder):
    """
    Set an existing RMBG-2.0 model location.

    This does NOT download anything.
    """

    folder = Path(folder)

    if not folder.exists():
        raise ValueError(
            "The selected folder does not exist."
        )

    if not folder.is_dir():
        raise ValueError(
            "The selected location is not a folder."
        )

    missing_files = get_missing_files(folder)

    if missing_files:
        raise ValueError(
            "That folder does not contain a complete "
            "RMBG-2.0 model.\n\n"
            "Missing files:\n"
            + "\n".join(
                f"• {filename}"
                for filename in missing_files
            )
        )

    save_model_folder(folder)

    print(
        f"RMBG-2.0 location saved: {folder}"
    )

    return folder
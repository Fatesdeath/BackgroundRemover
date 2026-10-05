from model_manager import get_model

import torch
from PIL import Image, ImageFilter
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

try:
    import torch_directml
except ImportError:
    torch_directml = None


class BackgroundRemover:
    def __init__(self):
        self.device = self.get_device()

        print(f"Using device: {self.device}")
        print("Loading RMBG-2.0...")

        model_folder = get_model()

        self.model = AutoModelForImageSegmentation.from_pretrained(
            model_folder,
            trust_remote_code=True
        )

        self.model = self.model.to(self.device)
        self.model.eval()

        print("Model loaded!")

    def get_device(self):
        if torch.cuda.is_available():
            return "cuda"

        if torch_directml is not None:
            try:
                return torch_directml.device()
            except Exception:
                pass

        return "cpu"

    def remove_background(
        self,
        image_path,
        processing_size=1024,
        tolerance=0,
        edge_smoothness=0
    ):
        image = Image.open(image_path).convert("RGB")

        original_size = image.size

        transform_image = transforms.Compose([
            transforms.Resize(
                (processing_size, processing_size)
            ),
            transforms.ToTensor(),
            transforms.Normalize(
                [0.485, 0.456, 0.406],
                [0.229, 0.224, 0.225]
            )
        ])

        input_image = transform_image(
            image
        ).unsqueeze(0).to(self.device)

        print("Removing background...")

        with torch.no_grad():
            prediction = self.model(
                input_image
            )[-1].sigmoid().cpu()

        prediction = prediction[0].squeeze()

        mask = transforms.ToPILImage()(prediction)

        mask = mask.resize(original_size)

        if tolerance > 0:
            mask = self.apply_tolerance(
                mask,
                tolerance
            )

        if edge_smoothness > 0:
            mask = mask.filter(
                ImageFilter.GaussianBlur(
                    radius=edge_smoothness
                )
            )

        result = image.convert("RGBA")

        result.putalpha(mask)

        print("Background removed!")

        return result

    def apply_tolerance(
        self,
        mask,
        tolerance
    ):
        threshold = int(tolerance * 2.55)

        return mask.point(
            lambda value:
            0 if value < threshold else value
        )
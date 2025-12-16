
# image_captioner.py
# Simple image -> caption wrapper using HuggingFace BLIP
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch
import os, json

MODEL_NAME = "Salesforce/blip-image-captioning-base"  # public model
HERE = os.path.dirname(__file__)

# lazy load
_processor = None
_model = None
_device = "cuda" if torch.cuda.is_available() else "cpu"

def _load():
    global _processor, _model
    if _processor is None:
        _processor = BlipProcessor.from_pretrained(MODEL_NAME)
    if _model is None:
        _model = BlipForConditionalGeneration.from_pretrained(MODEL_NAME).to(_device)
    return _processor, _model

def caption_image(image_path, max_length=40):
    processor, model = _load()
    img = Image.open(image_path).convert("RGB")
    inputs = processor(images=img, return_tensors="pt").to(_device)
    with torch.no_grad():
        out = model.generate(**inputs, max_length=max_length)
    caption = processor.decode(out[0], skip_special_tokens=True)
    return caption

# Example CLI use
if __name__ == "__main__":
    import sys
    img = sys.argv[1] if len(sys.argv)>1 else "example.jpg"
    print("Caption:", caption_image(img))

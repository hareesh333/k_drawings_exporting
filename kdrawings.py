from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pdf2image import convert_from_path
import cv2
import pytesseract
import re
import os
import shutil

app = FastAPI()

DEFAULT_COORDINATES = [(1730, 1466), (2380, 1466), (2380, 1670), (1730, 1670)]
DEFAULT_PATTERN = r'\b[kK]\d+\b'


def convert_pdf_page_to_image(pdf_path, extracted_images_folder, page_number, dpi=150):
    try:
        images = convert_from_path(pdf_path, dpi=dpi, first_page=page_number, last_page=page_number)
        if images:
            image_path = os.path.join(extracted_images_folder, f"page_{page_number}.jpg")
            images[0].save(image_path, 'JPEG')
            return image_path, None
        return None, "No images found for page."
    except Exception as e:
        return None, f"Error converting PDF page to image: {e}"


def extract_and_match_text(image_path, coordinates, pattern):
    try:
        image = cv2.imread(image_path)
        if image is None:
            return None, "Failed to load image."

        x_min, y_min = min(coordinates)[0], min(coordinates, key=lambda x: x[1])[1]
        x_max, y_max = max(coordinates)[0], max(coordinates, key=lambda x: x[1])[1]
        cropped_image = image[y_min:y_max, x_min:x_max]

        extracted_text = pytesseract.image_to_string(cropped_image).strip()
        matches = re.findall(pattern, extracted_text)

        if matches:
            return matches, None
        else:
            return None, "No matches found."

    except Exception as e:
        return None, f"Error: {e}"


@app.post("/upload_pdf/")
async def upload_pdf(
        file: UploadFile = File(...),
        extracted_images_folder: str = Form(...),
        pattern_images_folder: str = Form(...),
        coordinates: str = Form(None),  # Optional: "x1,y1;x2,y2;x3,y3;x4,y4"
        pattern: str = Form(None)
):
    try:
        pdf_path = f"/tmp/{file.filename}"
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        os.makedirs(extracted_images_folder, exist_ok=True)
        os.makedirs(pattern_images_folder, exist_ok=True)

        if coordinates:
            coordinates = [tuple(map(int, coord.split(','))) for coord in coordinates.split(';')]
        else:
            coordinates = DEFAULT_COORDINATES

        if not pattern:
            pattern = DEFAULT_PATTERN

        total_images = 0
        passed_images = 0
        failed_images = []

        total_pages = len(convert_from_path(pdf_path, dpi=160))  # Get total pages quickly with low dpi

        for page_number in range(1, total_pages + 1):
            image_path, error_message = convert_pdf_page_to_image(pdf_path, extracted_images_folder, page_number)
            if image_path:
                total_images += 1
                matches, error_message = extract_and_match_text(image_path, coordinates, pattern)
                if matches is not None:
                    passed_images += 1
                    pattern_image_path = os.path.join(pattern_images_folder, f"page_{page_number}.jpg")
                    cv2.imwrite(pattern_image_path, cv2.imread(image_path))  # Copy image to pattern_images_folder
                else:
                    failed_images.append(f"page_{page_number}.jpg")
            else:
                failed_images.append(f"page_{page_number}.jpg")

        report = {
            "total_images": total_images,
            "passed_images": passed_images,
            
            "failed_images_count": len(failed_images),
            "failed_images": failed_images
        }
        return JSONResponse(content=report)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
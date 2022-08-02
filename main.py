from datetime import datetime
from fastapi import FastAPI
from fastapi import FastAPI, status,Response, HTTPException
from pydantic import BaseModel
# Image processing libraries
from skimage.io import imread
import numpy as np
import cv2
import boto3
from dotenv import load_dotenv
from os import getenv,remove
import pytesseract

load_dotenv()

app = FastAPI()

class PostImage(BaseModel):
    image: str


@app.get("/")
def read_root():
    return {"Message": "API de lectura de medidor de luz"}


@app.post("/filter")
async def read_image(post_image: PostImage):
    image_path = post_image.image
    image_medidor = imread(image_path)

    #Tranform into grayscale
    image_medidor_gray = cv2.cvtColor(image_medidor, cv2.COLOR_BGR2GRAY)
    # APPLY GAUSSIAN BLUR
    image_medidor_blur = cv2.GaussianBlur(image_medidor_gray, (5, 5), 0)
    # Apply morphological gradient
    image_medidor_gradient = cv2.morphologyEx(image_medidor_blur, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
    #Apply threshold
    image_medidor_threshold = cv2.threshold(image_medidor_gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    #Write image_medidor_threshold in images folder
    #Format datetime
    now = datetime.now()
    current_time = now.strftime("%d-%m-%Y_%H-%M-%S")
    img_name = f'{current_time}image_medidor_threshold.png'
    cv2.imwrite(f"images/{img_name}", image_medidor_threshold)
    img_path = f'images/{img_name}'

    #Add img to S3 bucket
    s3 = boto3.resource('s3', 
        aws_access_key_id=getenv('AWS_ACCESS_KEY_ID'), 
        aws_secret_access_key=getenv('AWS_SECRET_ACCESS_KEY'))

    #Use AWS_BUCKET from .env
    bucket = s3.Bucket(getenv('AWS_BUCKET'))
    bucket.upload_file(img_path, img_name)
    
    uploaded_file_url = f"https://{getenv('AWS_BUCKET')}.s3.amazonaws.com/{img_name}"
    print(uploaded_file_url)

    #Remove img from images folder
    remove(img_path)

    # Leemos la imagen
    lectura = pytesseract.image_to_string(image_medidor_threshold, config="--psm 6 digits tessedit_char_whitelist=0123456789.")
    
    #Extract numbers only
    cleaned = filter(str.isdigit, lectura)
    cleaned_number = list(cleaned)
    print(cleaned_number)

    lectura_extraida = ''.join(cleaned_number)
  
    return {"message": "Imagen recibida", "lectura": lectura_extraida, "url": uploaded_file_url}
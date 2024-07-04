from fastapi import FastAPI, HTTPException, Form
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import os
import boto3

app = FastAPI()

@app.post("/upload-to-s3/")
async def upload_to_s3(
    directory_path: str = Form(...),
    aws_access_key_id: str = Form(...),
    aws_secret_access_key: str = Form(...),
    bucket_name: str = Form(...),
    region_name: str = Form("us-east-1"),
    s3_directory: str = Form("")
):
    if not os.path.exists(directory_path):
        raise HTTPException(status_code=400, detail="Directory does not exist")

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )
    uploaded_files_count = 0

    for root, dirs, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            s3_key = os.path.join(s3_directory, os.path.relpath(file_path, directory_path))
            try:
                s3_client.upload_file(file_path, bucket_name, s3_key)
                uploaded_files_count += 1
            except FileNotFoundError:
                raise HTTPException(status_code=400, detail=f"File {file} not found")
            except NoCredentialsError:
                raise HTTPException(status_code=401, detail="Credentials not available")
            except PartialCredentialsError:
                raise HTTPException(status_code=401, detail="Incomplete credentials provided")

    return {"message": "Files uploaded successfully", "uploaded_files_count": uploaded_files_count}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)

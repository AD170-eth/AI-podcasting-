import os
import boto3
import requests

# prompt for S3 bucket name
bucket_name = input("Enter the name of the S3 bucket: ")
s3 = boto3.client("s3")

# prompt for text file path
text_file_path = input("Enter the path of the text file: ")
if not os.path.isfile(text_file_path):
    print("Invalid file path")
    exit()

# prompt for output file path
output_file_path = input("Enter the path of the output file: ")
if os.path.isfile(output_file_path):
    confirm_overwrite = input(
        "Output file already exists. Do you want to overwrite it? (y/n): ")
    if confirm_overwrite.lower() != "y":
        exit()

# prompt for API key
api_key = input("Enter your 11labs API key: ")
if not api_key:
    print("API key is required")
    exit()

# open the text file
try:
    with open(text_file_path, "r") as f:
        lines = f.readlines()
except FileNotFoundError:
    print(f"File not found: {text_file_path}")
    exit()

# iterate through each line and generate the audio using 11labs API
audios = []
for line in lines:
    parts = line.split("=")
    if len(parts) != 2:
        print(f"Invalid line in the input file: {line}")
        continue

    text = parts[0].strip()
    voice = parts[1].strip()

    if voice.startswith("new"):
        voice_parts = voice.split("[")
        if len(voice_parts) != 2 or not voice_parts[1].startswith("voice="):
            print(f"Invalid voice parameter in line: {line}")
            continue

        voice = voice_parts[1].split("]")[0].split("=")[1]
        url = f"https://api.11labs.ai/v1/audio/synthesize?voice={voice}&text={text}"
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error generating audio for line: {line} - {e}")
            continue

        audio_file_path = f"{voice}.mp3"
        try:
            with open(audio_file_path, "wb") as audio_file:
                audio_file.write(response.content)
        except IOError as e:
            print(f"Error saving audio file for line: {line} - {e}")
            continue

        s3.upload_file(audio_file_path, bucket_name, audio_file_path)
        audios.append(f"s3://{bucket_name}/{audio_file_path}")
        os.remove(audio_file_path)
    elif voice.startswith("premade"):
        file_name_parts = voice.split("=")[1].split(",")
        if len(file_name_parts) != 2:
            print(f"Invalid premade audio parameter in line: {line}")
            continue

        file_name = file_name_parts[0]
        url = file_name_parts[1]
        file_extension = url.split(".")[-1]
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error downloading premade audio for line: {line} - {e}")
            continue

        audio_file_path = f"{file_name}.{file_extension}"
        try:
            with open(audio_file_path, "wb") as audio_file:
                audio_file.write(response.content)
        except IOError as e:
            print(f"Error saving audio file for line: {line} - {e}")
            continue

        s3.upload_file(audio_file_path, bucket_name, audio_file_path)
        audios.append(f"s3://{bucket_name}/{audio_file_path}")
        os.remove(audio_file_path)

# concatenate the audio files
output_audio_file_path = f"{output_file_path}.mp3"
command = f"ffmpeg -i \"concat:{'|'.join(audios)}\" -acodec copy \"{output_audio_file_path}\""
try:
    os.system(command)
except OSError as e:
    print(f"Error concatenating audio files: {e}")
    exit()

print(f"Audio file saved to: {output_audio_file_path}")

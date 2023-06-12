# based on https://github.com/davabase/whisper_real_time/blob/master/transcribe_demo.py
import speech_recognition as sr
import whisper
import torch
import io
import os
import subprocess
import database
import config

from database import database
from config import config
from subprocess import Popen, PIPE
from datetime import datetime, timedelta
from queue import Queue
from tempfile import NamedTemporaryFile
from time import sleep
from image_gen import image_gen
from PIL import Image


def main():
    # The last time we updated the image
    last_image_time = datetime.utcnow()

    # Current raw audio bytes.
    last_sample = bytes()

    # Thread safe Queue for passing data from the threaded recording callback.
    data_queue = Queue()

    # We use SpeechRecognizer to record our audio because it has a nice feauture where it can detect when speech ends.
    recorder = sr.Recognizer()
    recorder.energy_threshold = config.energy_threshold

    # Definitely do this, dynamic energy compensation lowers the energy threshold dramtically to a point where the SpeechRecognizer never stops recording.
    recorder.dynamic_energy_threshold = False   

    # Important for linux users. 
    # Prevents permanent application hang and crash by using the wrong Microphone
    print("Selecting mic: " + config.microphone)
    for index, name in enumerate(sr.Microphone.list_microphone_names()):        
        print("Availible microphone: " + name)
        if config.microphone in name:
            audio_source = sr.Microphone(sample_rate=16000, device_index=index)
            print("Microphone configured: " + name )
            break
        
    # Load / Download model    
    if config.model_name != "large" and config.english_language:
        model_name = config.model_name + ".en"
    print("Loading model: " + model_name)    
    audio_model = whisper.load_model(model_name)

    # Do we have GPU availible?
    print("Using GPU: " + str(torch.cuda.is_available()))

    temp_file = NamedTemporaryFile().name
    transcription = ['']
    
    with audio_source:
        recorder.adjust_for_ambient_noise(audio_source)

    def record_callback(_, audio:sr.AudioData) -> None:
        """
        Threaded callback function to recieve audio data when recordings finish.
        audio: An AudioData containing the recorded bytes.
        """
        # Grab the raw bytes and push it into the thread safe queue.
        data = audio.get_raw_data()
        data_queue.put(data)

    # Create a background thread that will pass us raw audio bytes.
    # We could do this manually but SpeechRecognizer provides a nice helper.
    recorder.listen_in_background(audio_source, record_callback, phrase_time_limit = config.phrase_timeout_sec)

    # Loading image creation class
    print("Loading image creation clas")
    image_generator = image_gen(config)

    images_db = database(config)

    # Cue the user that we're ready to go.
    print("Starting main loop")
    print("========================================")

    while True:
        try:
            # Pull raw recorded audio from the queue.
            if not data_queue.empty():
                # Got new data            
                # Concatenate our current audio data with the latest audio data.
                last_sample = bytes()
                while not data_queue.empty():
                    data = data_queue.get()
                    last_sample += data

                # Use AudioData to convert the raw data to wav data.
                audio_data = sr.AudioData(last_sample, audio_source.SAMPLE_RATE, audio_source.SAMPLE_WIDTH)
                wav_data = io.BytesIO(audio_data.get_wav_data())

                # Write wav data to the temporary file as bytes.
                with open(temp_file, 'w+b') as f:
                    f.write(wav_data.read())

                # Read the transcription.
                result = audio_model.transcribe(temp_file, fp16=torch.cuda.is_available())
                text = result['text'].strip()
                
                # It adds .. sometimes, delete them
                text = text.replace("..", "")

                print("Phrase: " + text)
                transcription.append(text)

            # Refresh image once in a while
            now = datetime.utcnow()
            if last_image_time and now - last_image_time > timedelta(seconds = config.image_refresh_sec):
                trans_str = ". ".join(transcription)

                print("========================================")
                print("Full starnscript: " + trans_str)
                
                if len(trans_str) < 200:
                    # Transcript is to short, try again
                    print("Transctipt is too short, contunue")
                    print("========================================")
                    transcription.clear()
                    last_image_time = now
                    continue

                # Generate image and save it to the DB
                title, style, description, img = image_generator.generate_image(trans_str)
                if title is None or img is None:
                    # Something is not right, continue
                    print("ChatGPT exception, contunue")
                    print("========================================")
                    transcription.clear()
                    last_image_time = now
                    continue

                # Got a legit image
                print("========================================")
                print("Rendered image: " + title + ". (" + style + "): " + description)

                # Convert to jpg for the database
                with io.BytesIO() as img_bytes:
                    img.save(img_bytes, format='JPEG')
                    img_bytes.seek(0)
                    img_jpg = Image.open(img_bytes)
                    img_jpg.load()
                images_db.add_picture(trans_str, title, style, description, img_jpg)

                # Super cheese way of showing image from WSL
                img.save("tmp_img.png")
                try:
                    os.system("taskkill.exe /IM mspaint.exe")
                except:
                    pass
                
                Popen(["mspaint.exe", "tmp_img.png"], stdout=PIPE, stderr=PIPE)

                # Clear trasncipt and restart
                transcription.clear()
                last_image_time = now
                print("========================================")

                # Infinite loops are bad for processors, must sleep.
                sleep(0.25)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()

# based on https://github.com/davabase/whisper_real_time/blob/master/transcribe_demo.py
import speech_recognition as sr
import whisper
import torch
import io

from datetime import datetime, timedelta
from queue import Queue
from tempfile import NamedTemporaryFile
from time import sleep

class config:
    energy_threshold = 1000
    microphone = "pulse"
    model_name = "medium"   # "tiny", "base", "small", "medium", "large"
    english_language = True
    record_timeout = 2  # Max seconds before calling a callback
    phrase_timeout = 5  # How much empty space between recordings before we consider it a new line in the transcription.


def main():
    # The last time a recording was retreived from the queue.
    phrase_time = None

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
    recorder.listen_in_background(audio_source, record_callback, phrase_time_limit = config.record_timeout)

    # Cue the user that we're ready to go.
    print("Starting main loop")

    while True:
        try:
            now = datetime.utcnow()

            # Pull raw recorded audio from the queue.
            if not data_queue.empty():
                phrase_complete = False

                # If enough time has passed between recordings, consider the phrase complete.
                # Clear the current working audio buffer to start over with the new data.
                if phrase_time and now - phrase_time > timedelta(seconds = config.phrase_timeout):
                    last_sample = bytes()
                    phrase_complete = True

                # This is the last time we received new audio data from the queue.
                phrase_time = now

                # Concatenate our current audio data with the latest audio data.
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
                print("String: " + text)

                # If we detected a pause between recordings, add a new item to our transcripion.
                # Otherwise edit the existing one.
                if phrase_complete:
                    transcription.append(text)
                else:
                    transcription[-1] = text

                # Infinite loops are bad for processors, must sleep.
                sleep(0.25)
        except KeyboardInterrupt:
            break

    print("\n\nTranscription:")
    for line in transcription:
        print(line)


if __name__ == "__main__":
    main()

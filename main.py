from dotenv import load_dotenv, find_dotenv
import bot.voicecreate as vc

def main():
    load_dotenv(find_dotenv())
    voiceCreate = vc.VoiceCreate()

if __name__ == '__main__':
    main()

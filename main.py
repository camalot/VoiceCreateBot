from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import bot.voicecreate as vc

def main():
    voiceCreate = vc.VoiceCreate()

if __name__ == '__main__':
    main()

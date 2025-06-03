from gtts import gTTS
import os

tts = gTTS(text='您好，您吃早饭了吗？需要我给你推荐些吃的吗？', lang='zh-tw')
tts.save("hello.mp3")
# os.system("mpg321 hello.mp3")
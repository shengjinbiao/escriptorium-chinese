# translate_po.py
import polib
from googletrans import Translator
import time

po = polib.pofile('locale/zh_Hans/LC_MESSAGES/django.po')
translator = Translator()

for entry in po.untranslated_entries():
    if entry.msgid.strip():
        for _ in range(3):  # 最多重試3次
            try:
                translation = translator.translate(entry.msgid, dest='zh-cn').text
                if translation:
                    entry.msgstr = translation
                    break
            except Exception as e:
                print(f"翻譯失敗: {entry.msgid}，錯誤：{e}")
                time.sleep(2)  # 等2秒再試
        else:
            print(f"最終未能翻譯: {entry.msgid}")

po.save('locale/zh_Hans/LC_MESSAGES/django.po')
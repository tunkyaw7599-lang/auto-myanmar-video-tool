# Auto Myanmar Video Tool (MVP)

ဒီ project က နိုင်ငံခြားဗီဒီယိုကို upload လုပ်ပြီး မြန်မာဘာသာပြန်၊ မြန်မာအသံ၊ မြန်မာစာတန်းထိုးပါတဲ့ MP4 ထုတ်ပေးဖို့ စတင်တည်ဆောက်ထားတဲ့ MVP ဖြစ်ပါတယ်။

## လက်ရှိပါဝင်တာ
- MP4 / MOV upload
- OpenAI Whisper API ဖြင့် မူရင်းအသံကို timestamp နဲ့ စာသားပြောင်းခြင်း
- OpenAI API ဖြင့် မြန်မာလို ဘာသာပြန်ခြင်း
- အမျိုးသား / အမျိုးသမီး voice ရွေးချယ်ခြင်း
- TTS အသံဖိုင်ထုတ်ခြင်း
- SRT subtitle ဖန်တီးခြင်း
- FFmpeg ဖြင့် video + မြန်မာအသံ + subtitle ပေါင်းစပ်ခြင်း

## လိုအပ်ချက်
- Python 3.10+
- FFmpeg ကို install လုပ်ပြီး PATH ထဲထည့်ထားရန်
- OpenAI API key

## စတင်အသုံးပြုရန် (Windows)
1. ZIP ကိုဖြည်ပါ။
2. `backend` folder ထဲဝင်ပါ။
3. Terminal / CMD ဖွင့်ပြီး အောက်ပါ command များ run ပါ။

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

4. `backend/.env.example` ကို `.env` အဖြစ် copy လုပ်ပြီး API key ထည့်ပါ။
5. Server စတင်ပါ။

```bash
uvicorn main:app --reload
```

6. Browser မှာ `http://127.0.0.1:8000` ဖွင့်ပါ။

## macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

## အရေးကြီး
- API အသုံးပြုမှုအတွက် ကုန်ကျစရိတ် ရှိနိုင်ပါတယ်။ API key ကို မည်သူ့ကိုမျှ မပေးပါနှင့်။
- ဒီ MVP က အင်တာနက်ချိတ်ဆက်မှုလိုပါတယ်။
- အလွန်ရှည်တဲ့ ဗီဒီယိုတွေကို စမ်းသပ်ရာမှာ အရင်ဆုံး ၁-၃ မိနစ်စာနဲ့ စမ်းပါ။
- TTS အသံနဲ့ မူရင်းဗီဒီယိုရဲ့ အချိန်ကိုက်မှုက အမြဲတိကျမည်မဟုတ်ပါ။ နောက်ထပ်အဆင့်မှာ voice timing alignment၊ speaker detection နဲ့ multi-speaker dubbing ထည့်နိုင်ပါတယ်။
- ကိုယ်ပိုင်ဗီဒီယို သို့မဟုတ် ဘာသာပြန်/ပြန်လည်အသုံးပြုခွင့်ရှိသော ဗီဒီယိုများကိုသာ အသုံးပြုပါ။

## Voice ရွေးချယ်မှု
MVP တွင် OpenAI TTS voice preset ကိုအသုံးပြုထားပါတယ်။ `alloy` ကို အမျိုးသား/အမျိုးသမီး အသံအဖြစ် တိတိကျကျ သတ်မှတ်မထားနိုင်ပါ။ UI မှာ အမျိုးသား/အမျိုးသမီး ရွေးချယ်မှုကို ထည့်ထားပြီး အသံ preset mapping ကို `.env` ထဲတွင် ပြင်နိုင်အောင် ပြုလုပ်ထားပါတယ်။ အသံလိင်/လေယူလေသိမ်းကို အပြည့်အဝအာမခံရန် မြန်မာဘာသာကို ပံ့ပိုးသော TTS provider တစ်ခုကို ချိတ်ဆက်စမ်းသပ်ရန် လိုအပ်ပါတယ်။

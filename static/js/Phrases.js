/* ==========================================
   BlindMate offline language pack (English, Hindi, Kannada, Tamil, Telugu)

   Safety-critical messages (emergency alerts, obstacle warnings, navigation
   prompts) must be spoken INSTANTLY and must never depend on an AI
   translation call that could be slow or fail. Everything here works with
   no network.

   If you change an English sentence in the app that appears below, change
   its key here too (lookup is by the English text).
========================================== */
(function () {
  const L = ["hi-IN", "kn-IN", "ta-IN", "te-IN"];

  // [english, hi, kn, ta, te]
  const PHRASE_ROWS = [
    ["Emergency alert cancelled.",
      "आपातकालीन अलर्ट रद्द कर दिया गया।",
      "ತುರ್ತು ಎಚ್ಚರಿಕೆಯನ್ನು ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ.",
      "அவசர எச்சரிக்கை ரத்து செய்யப்பட்டது.",
      "అత్యవసర హెచ్చరిక రద్దు చేయబడింది."],
    ["Shake detected. Sending an emergency alert in a few seconds. Touch the screen to cancel.",
      "हिलाने का पता चला। कुछ सेकंड में आपातकालीन अलर्ट भेजा जाएगा। रद्द करने के लिए स्क्रीन को छुएं।",
      "ಅಲುಗಾಟ ಪತ್ತೆಯಾಗಿದೆ. ಕೆಲವು ಸೆಕೆಂಡುಗಳಲ್ಲಿ ತುರ್ತು ಎಚ್ಚರಿಕೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ. ರದ್ದುಗೊಳಿಸಲು ಪರದೆಯನ್ನು ಸ್ಪರ್ಶಿಸಿ.",
      "குலுக்கல் கண்டறியப்பட்டது. சில வினாடிகளில் அவசர எச்சரிக்கை அனுப்பப்படும். ரத்து செய்ய திரையைத் தொடவும்.",
      "కుదుపు గుర్తించబడింది. కొన్ని సెకన్లలో అత్యవసర హెచ్చరిక పంపబడుతుంది. రద్దు చేయడానికి స్క్రీన్‌ను తాకండి."],
    ["Emergency mode activated. Getting your location.",
      "आपातकालीन मोड चालू हो गया है। आपकी लोकेशन ली जा रही है।",
      "ತುರ್ತು ಮೋಡ್ ಸಕ್ರಿಯವಾಗಿದೆ. ನಿಮ್ಮ ಸ್ಥಳವನ್ನು ಪಡೆಯಲಾಗುತ್ತಿದೆ.",
      "அவசர முறை செயல்படுத்தப்பட்டது. உங்கள் இருப்பிடம் பெறப்படுகிறது.",
      "అత్యవసర మోడ్ ప్రారంభమైంది. మీ లొకేషన్ తీసుకుంటున్నాను."],
    ["No emergency contacts are saved yet. Please add one in settings first.",
      "अभी तक कोई आपातकालीन संपर्क सेव नहीं है। कृपया पहले सेटिंग्स में एक जोड़ें।",
      "ಇನ್ನೂ ಯಾವುದೇ ತುರ್ತು ಸಂಪರ್ಕವನ್ನು ಉಳಿಸಲಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಮೊದಲು ಸೆಟ್ಟಿಂಗ್ಸ್‌ನಲ್ಲಿ ಒಂದನ್ನು ಸೇರಿಸಿ.",
      "இன்னும் அவசரத் தொடர்புகள் சேமிக்கப்படவில்லை. முதலில் அமைப்புகளில் ஒன்றைச் சேர்க்கவும்.",
      "ఇంకా అత్యవసర కాంటాక్ట్‌లు సేవ్ చేయలేదు. దయచేసి ముందుగా సెట్టింగ్స్‌లో ఒకటి జోడించండి."],
    ["Location is not supported on this device. Sending the alert without it.",
      "इस डिवाइस पर लोकेशन उपलब्ध नहीं है। बिना लोकेशन के अलर्ट भेजा जा रहा है।",
      "ಈ ಸಾಧನದಲ್ಲಿ ಸ್ಥಳ ಬೆಂಬಲಿತವಾಗಿಲ್ಲ. ಸ್ಥಳವಿಲ್ಲದೆ ಎಚ್ಚರಿಕೆಯನ್ನು ಕಳುಹಿಸಲಾಗುತ್ತಿದೆ.",
      "இந்தச் சாதனத்தில் இருப்பிடம் ஆதரிக்கப்படவில்லை. இருப்பிடம் இல்லாமல் எச்சரிக்கை அனுப்பப்படுகிறது.",
      "ఈ పరికరంలో లొకేషన్ మద్దతు లేదు. లొకేషన్ లేకుండా హెచ్చరిక పంపుతున్నాను."],
    ["Could not get your location, but I'm still sending the alert.",
      "आपकी लोकेशन नहीं मिल सकी, लेकिन मैं फिर भी अलर्ट भेज रहा हूँ।",
      "ನಿಮ್ಮ ಸ್ಥಳ ಸಿಗಲಿಲ್ಲ, ಆದರೂ ನಾನು ಎಚ್ಚರಿಕೆಯನ್ನು ಕಳುಹಿಸುತ್ತಿದ್ದೇನೆ.",
      "உங்கள் இருப்பிடம் கிடைக்கவில்லை, ஆனாலும் எச்சரிக்கையை அனுப்புகிறேன்.",
      "మీ లొకేషన్ దొరకలేదు, అయినా హెచ్చరికను పంపుతున్నాను."],
    ["Emergency alert has been sent to your contacts. Help is on the way.",
      "आपके संपर्कों को आपातकालीन अलर्ट भेज दिया गया है। मदद आ रही है।",
      "ನಿಮ್ಮ ಸಂಪರ್ಕಗಳಿಗೆ ತುರ್ತು ಎಚ್ಚರಿಕೆ ಕಳುಹಿಸಲಾಗಿದೆ. ಸಹಾಯ ಬರುತ್ತಿದೆ.",
      "உங்கள் தொடர்புகளுக்கு அவசர எச்சரிக்கை அனுப்பப்பட்டது. உதவி வந்துகொண்டிருக்கிறது.",
      "మీ కాంటాక్ట్‌లకు అత్యవసర హెచ్చరిక పంపబడింది. సహాయం వస్తోంది."],
    ["I could not send the alert automatically. Opening a text message for you now - please tap send.",
      "मैं अलर्ट अपने आप नहीं भेज सका। अब आपके लिए टेक्स्ट संदेश खोल रहा हूँ, कृपया भेजें दबाएं।",
      "ನನಗೆ ಎಚ್ಚರಿಕೆಯನ್ನು ತಾನಾಗಿ ಕಳುಹಿಸಲು ಆಗಲಿಲ್ಲ. ಈಗ ನಿಮಗಾಗಿ ಸಂದೇಶವನ್ನು ತೆರೆಯುತ್ತಿದ್ದೇನೆ, ದಯವಿಟ್ಟು ಕಳುಹಿಸು ಒತ್ತಿ.",
      "எச்சரிக்கையை தானாக அனுப்ப முடியவில்லை. இப்போது உங்களுக்காக குறுஞ்செய்தியைத் திறக்கிறேன், அனுப்பு என்பதைத் தட்டவும்.",
      "హెచ్చరికను ఆటోమేటిక్‌గా పంపలేకపోయాను. ఇప్పుడు మీ కోసం టెక్స్ట్ సందేశాన్ని తెరుస్తున్నాను, దయచేసి సెండ్ నొక్కండి."],
    ["I could not reach the server to send the alert. Opening a text message for you now - please tap send.",
      "अलर्ट भेजने के लिए सर्वर से संपर्क नहीं हो सका। अब आपके लिए टेक्स्ट संदेश खोल रहा हूँ, कृपया भेजें दबाएं।",
      "ಎಚ್ಚರಿಕೆ ಕಳುಹಿಸಲು ಸರ್ವರ್ ತಲುಪಲು ಆಗಲಿಲ್ಲ. ಈಗ ನಿಮಗಾಗಿ ಸಂದೇಶವನ್ನು ತೆರೆಯುತ್ತಿದ್ದೇನೆ, ದಯವಿಟ್ಟು ಕಳುಹಿಸು ಒತ್ತಿ.",
      "எச்சரிக்கையை அனுப்ப சேவையகத்தை அடைய முடியவில்லை. இப்போது உங்களுக்காக குறுஞ்செய்தியைத் திறக்கிறேன், அனுப்பு என்பதைத் தட்டவும்.",
      "హెచ్చరిక పంపడానికి సర్వర్‌ను చేరుకోలేకపోయాను. ఇప్పుడు మీ కోసం టెక్స్ట్ సందేశాన్ని తెరుస్తున్నాను, దయచేసి సెండ్ నొక్కండి."],
    ["None of your saved contacts have a phone number, so I could not prepare a text message.",
      "आपके सेव किए गए किसी भी संपर्क का फ़ोन नंबर नहीं है, इसलिए मैं टेक्स्ट संदेश तैयार नहीं कर सका।",
      "ನಿಮ್ಮ ಉಳಿಸಿದ ಯಾವುದೇ ಸಂಪರ್ಕಕ್ಕೂ ಫೋನ್ ಸಂಖ್ಯೆ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಸಂದೇಶವನ್ನು ಸಿದ್ಧಪಡಿಸಲು ಆಗಲಿಲ್ಲ.",
      "நீங்கள் சேமித்த எந்தத் தொடர்புக்கும் தொலைபேசி எண் இல்லை, அதனால் குறுஞ்செய்தியைத் தயாரிக்க முடியவில்லை.",
      "మీరు సేవ్ చేసిన ఏ కాంటాక్ట్‌కీ ఫోన్ నంబర్ లేదు, అందువల్ల టెక్స్ట్ సందేశాన్ని సిద్ధం చేయలేకపోయాను."],
    ["Your live location is being shared with your contacts for the next two hours. Say I am safe to stop.",
      "आपकी लाइव लोकेशन अगले दो घंटे तक आपके संपर्कों के साथ साझा की जा रही है। रोकने के लिए, मैं सुरक्षित हूँ, कहें।",
      "ನಿಮ್ಮ ಲೈವ್ ಸ್ಥಳವನ್ನು ಮುಂದಿನ ಎರಡು ಗಂಟೆಗಳ ಕಾಲ ನಿಮ್ಮ ಸಂಪರ್ಕಗಳೊಂದಿಗೆ ಹಂಚಿಕೊಳ್ಳಲಾಗುತ್ತಿದೆ. ನಿಲ್ಲಿಸಲು, ನಾನು ಸುರಕ್ಷಿತ, ಎಂದು ಹೇಳಿ.",
      "உங்கள் நேரடி இருப்பிடம் அடுத்த இரண்டு மணி நேரம் உங்கள் தொடர்புகளுடன் பகிரப்படுகிறது. நிறுத்த, நான் பாதுகாப்பாக இருக்கிறேன், என்று சொல்லுங்கள்.",
      "మీ లైవ్ లొకేషన్ రాబోయే రెండు గంటల పాటు మీ కాంటాక్ట్‌లతో షేర్ చేయబడుతోంది. ఆపడానికి, నేను సురక్షితంగా ఉన్నాను, అని చెప్పండి."],
    ["Location sharing stopped. I am glad you are safe.",
      "लोकेशन साझा करना बंद हो गया। मुझे खुशी है कि आप सुरक्षित हैं।",
      "ಸ್ಥಳ ಹಂಚಿಕೆ ನಿಲ್ಲಿಸಲಾಗಿದೆ. ನೀವು ಸುರಕ್ಷಿತವಾಗಿದ್ದೀರಿ ಎಂದು ಸಂತೋಷ.",
      "இருப்பிடப் பகிர்வு நிறுத்தப்பட்டது. நீங்கள் பாதுகாப்பாக இருப்பது மகிழ்ச்சி.",
      "లొకేషన్ షేరింగ్ ఆపబడింది. మీరు సురక్షితంగా ఉన్నారని సంతోషం."],
    ["Where would you like to go?",
      "आप कहाँ जाना चाहेंगे?",
      "ನೀವು ಎಲ್ಲಿಗೆ ಹೋಗಲು ಬಯಸುತ್ತೀರಿ?",
      "நீங்கள் எங்கே செல்ல விரும்புகிறீர்கள்?",
      "మీరు ఎక్కడికి వెళ్లాలనుకుంటున్నారు?"],
    ["You have moved off the route, recalculating...",
      "आप रास्ते से हट गए हैं, दोबारा रास्ता निकाल रहा हूँ।",
      "ನೀವು ಮಾರ್ಗದಿಂದ ಹೊರಗೆ ಹೋಗಿದ್ದೀರಿ, ಮತ್ತೆ ಮಾರ್ಗ ಲೆಕ್ಕ ಹಾಕುತ್ತಿದ್ದೇನೆ.",
      "நீங்கள் பாதையிலிருந்து விலகிவிட்டீர்கள், மீண்டும் வழியைக் கணக்கிடுகிறேன்.",
      "మీరు దారి తప్పారు, మళ్లీ మార్గాన్ని లెక్కిస్తున్నాను."],
    ["Navigation has been stopped",
      "नेविगेशन रोक दिया गया है",
      "ನ್ಯಾವಿಗೇಶನ್ ನಿಲ್ಲಿಸಲಾಗಿದೆ",
      "வழிசெலுத்தல் நிறுத்தப்பட்டது",
      "నావిగేషన్ ఆపబడింది"],
    ["Speak your command now",
      "अब अपना आदेश बोलें",
      "ಈಗ ನಿಮ್ಮ ಆದೇಶವನ್ನು ಹೇಳಿ",
      "இப்போது உங்கள் கட்டளையைச் சொல்லுங்கள்",
      "ఇప్పుడు మీ ఆదేశాన్ని చెప్పండి"],
    ["Reading now.",
      "अब पढ़ रहा हूँ।",
      "ಈಗ ಓದುತ್ತಿದ್ದೇನೆ.",
      "இப்போது படிக்கிறேன்.",
      "ఇప్పుడు చదువుతున్నాను."],
    ["Camera is not available. Please check camera permissions.",
      "कैमरा उपलब्ध नहीं है। कृपया कैमरा अनुमतियाँ जाँचें।",
      "ಕ್ಯಾಮೆರಾ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಕ್ಯಾಮೆರಾ ಅನುಮತಿಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
      "கேமரா கிடைக்கவில்லை. கேமரா அனுமதிகளைச் சரிபார்க்கவும்.",
      "కెమెరా అందుబాటులో లేదు. దయచేసి కెమెరా అనుమతులను తనిఖీ చేయండి."],
    ["Your emergency contact is not set up yet. Please open settings and add one, so I can alert them in an emergency.",
      "आपका आपातकालीन संपर्क अभी सेट नहीं है। कृपया सेटिंग्स खोलकर एक जोड़ें, ताकि आपात स्थिति में मैं उन्हें सूचित कर सकूं।",
      "ನಿಮ್ಮ ತುರ್ತು ಸಂಪರ್ಕವನ್ನು ಇನ್ನೂ ಹೊಂದಿಸಿಲ್ಲ. ದಯವಿಟ್ಟು ಸೆಟ್ಟಿಂಗ್ಸ್ ತೆರೆದು ಒಂದನ್ನು ಸೇರಿಸಿ, ಆಗ ತುರ್ತು ಸಂದರ್ಭದಲ್ಲಿ ನಾನು ಅವರಿಗೆ ತಿಳಿಸಬಹುದು.",
      "உங்கள் அவசரத் தொடர்பு இன்னும் அமைக்கப்படவில்லை. அவசர நேரத்தில் நான் அவர்களுக்குத் தெரிவிக்க, அமைப்புகளைத் திறந்து ஒன்றைச் சேர்க்கவும்.",
      "మీ అత్యవసర కాంటాక్ట్ ఇంకా సెట్ చేయలేదు. అత్యవసర సమయంలో నేను వారికి తెలియజేయడానికి, దయచేసి సెట్టింగ్స్ తెరిచి ఒకటి జోడించండి."],
    ["Automatic emergency emails are not set up on the server. In an emergency I will open a text message that you must send yourself.",
      "सर्वर पर स्वचालित आपातकालीन ईमेल सेट नहीं हैं। आपात स्थिति में मैं एक टेक्स्ट संदेश खोलूँगा जिसे आपको खुद भेजना होगा।",
      "ಸರ್ವರ್‌ನಲ್ಲಿ ಸ್ವಯಂಚಾಲಿತ ತುರ್ತು ಇಮೇಲ್‌ಗಳನ್ನು ಹೊಂದಿಸಿಲ್ಲ. ತುರ್ತು ಸಂದರ್ಭದಲ್ಲಿ ನಾನು ಒಂದು ಸಂದೇಶವನ್ನು ತೆರೆಯುತ್ತೇನೆ, ಅದನ್ನು ನೀವೇ ಕಳುಹಿಸಬೇಕು.",
      "சேவையகத்தில் தானியங்கி அவசர மின்னஞ்சல்கள் அமைக்கப்படவில்லை. அவசர நேரத்தில் நான் ஒரு குறுஞ்செய்தியைத் திறப்பேன், அதை நீங்களே அனுப்ப வேண்டும்.",
      "సర్వర్‌లో ఆటోమేటిక్ అత్యవసర ఈమెయిల్‌లు సెట్ చేయలేదు. అత్యవసర సమయంలో నేను ఒక టెక్స్ట్ సందేశాన్ని తెరుస్తాను, దానిని మీరే పంపాలి."],
    ["Looking at the money now. Please hold it flat and close to the camera.",
      "अब पैसे को देख रहा हूँ। कृपया उसे सीधा और कैमरे के पास पकड़ें।",
      "ಈಗ ಹಣವನ್ನು ನೋಡುತ್ತಿದ್ದೇನೆ. ದಯವಿಟ್ಟು ಅದನ್ನು ಸಮತಟ್ಟಾಗಿ ಮತ್ತು ಕ್ಯಾಮೆರಾ ಹತ್ತಿರ ಹಿಡಿಯಿರಿ.",
      "இப்போது பணத்தைப் பார்க்கிறேன். தயவுசெய்து அதை தட்டையாகவும் கேமராவுக்கு அருகிலும் பிடிக்கவும்.",
      "ఇప్పుడు డబ్బును చూస్తున్నాను. దయచేసి దానిని చదునుగా, కెమెరాకు దగ్గరగా పట్టుకోండి."],
  ];

  // [english, hi, kn, ta, te] - things the camera model can detect that matter when walking
  const NAME_ROWS = [
    ["person", "व्यक्ति", "ವ್ಯಕ್ತಿ", "நபர்", "వ్యక్తి"],
    ["bicycle", "साइकिल", "ಸೈಕಲ್", "மிதிவண்டி", "సైకిల్"],
    ["car", "कार", "ಕಾರು", "கார்", "కారు"],
    ["motorcycle", "मोटरसाइकिल", "ಮೋಟಾರ್ ಸೈಕಲ್", "மோட்டார் சைக்கிள்", "మోటార్ సైకిల్"],
    ["bus", "बस", "ಬಸ್", "பேருந்து", "బస్సు"],
    ["truck", "ट्रक", "ಟ್ರಕ್", "லாரி", "ట్రక్కు"],
    ["train", "ट्रेन", "ರೈಲು", "ரயில்", "రైలు"],
    ["traffic light", "ट्रैफिक लाइट", "ಟ್ರಾಫಿಕ್ ಲೈಟ್", "போக்குவரத்து விளக்கு", "ట్రాఫిక్ లైట్"],
    ["stop sign", "स्टॉप साइन", "ಸ್ಟಾಪ್ ಚಿಹ್ನೆ", "நிறுத்த அடையாளம்", "స్టాప్ సైన్"],
    ["fire hydrant", "फायर हाइड्रेंट", "ಫೈರ್ ಹೈಡ್ರಂಟ್", "தீ அணைப்பான் குழாய்", "ఫైర్ హైడ్రాంట్"],
    ["bench", "बेंच", "ಬೆಂಚು", "பெஞ்ச்", "బెంచ్"],
    ["dog", "कुत्ता", "ನಾಯಿ", "நாய்", "కుక్క"],
    ["cat", "बिल्ली", "ಬೆಕ್ಕು", "பூனை", "పిల్లి"],
    ["cow", "गाय", "ಹಸು", "மாடு", "ఆవు"],
    ["horse", "घोड़ा", "ಕುದುರೆ", "குதிரை", "గుర్రం"],
    ["bird", "पक्षी", "ಹಕ್ಕಿ", "பறவை", "పక్షి"],
    ["chair", "कुर्सी", "ಕುರ್ಚಿ", "நாற்காலி", "కుర్చీ"],
    ["couch", "सोफा", "ಸೋಫಾ", "சோபா", "సోఫా"],
    ["bed", "बिस्तर", "ಹಾಸಿಗೆ", "படுக்கை", "మంచం"],
    ["dining table", "मेज़", "ಮೇಜು", "மேசை", "బల్ల"],
    ["potted plant", "गमले का पौधा", "ಕುಂಡದ ಗಿಡ", "தொட்டிச் செடி", "కుండీలో మొక్క"],
    ["toilet", "शौचालय", "ಶೌಚಾಲಯ", "கழிப்பறை", "మరుగుదొడ్డి"],
    ["tv", "टीवी", "ಟಿವಿ", "தொலைக்காட்சி", "టీవీ"],
    ["laptop", "लैपटॉप", "ಲ್ಯಾಪ್‌ಟಾಪ್", "மடிக்கணினி", "ల్యాప్‌టాప్"],
    ["cell phone", "मोबाइल फ़ोन", "ಮೊಬೈಲ್ ಫೋನ್", "கைபேசி", "మొబైల్ ఫోన్"],
    ["bottle", "बोतल", "ಬಾಟಲಿ", "பாட்டில்", "సీసా"],
    ["cup", "कप", "ಕಪ್", "கோப்பை", "కప్పు"],
    ["bowl", "कटोरा", "ಬಟ್ಟಲು", "கிண்ணம்", "గిన్నె"],
    ["book", "किताब", "ಪುಸ್ತಕ", "புத்தகம்", "పుస్తకం"],
    ["backpack", "बैकपैक", "ಬೆನ್ನುಚೀಲ", "முதுகுப் பை", "బ్యాక్‌ప్యాక్"],
    ["handbag", "हैंडबैग", "ಹ್ಯಾಂಡ್‌ಬ್ಯಾಗ್", "கைப்பை", "హ్యాండ్‌బ్యాగ్"],
    ["suitcase", "सूटकेस", "ಸೂಟ್‌ಕೇಸ್", "பெட்டி", "సూట్‌కేస్"],
    ["umbrella", "छाता", "ಛತ್ರಿ", "குடை", "గొడుగు"],
    ["clock", "घड़ी", "ಗಡಿಯಾರ", "கடிகாரம்", "గడియారం"],
    ["refrigerator", "फ्रिज", "ಫ್ರಿಜ್", "குளிர்சாதனப் பெட்டி", "ఫ్రిజ్"],
    ["sink", "सिंक", "ಸಿಂಕ್", "தொட்டி", "సింక్"],
  ];

  // Battery messages. {n} is replaced with the percentage.
  // kinds: low, critical, status, charging, on, off, unsupported
  const BATTERY = {
    "en-IN": {
      low: "Battery is at {n} percent. Please charge your phone soon.",
      critical: "Battery is very low, {n} percent. Please plug in your charger now.",
      status: "Battery is at {n} percent.",
      charging: "Battery is at {n} percent and charging.",
      on: "Charger connected.",
      off: "Charger disconnected.",
      unsupported: "I cannot read the battery level on this device.",
    },
    "hi-IN": {
      low: "बैटरी {n} प्रतिशत है। कृपया जल्दी अपना फ़ोन चार्ज करें।",
      critical: "बैटरी बहुत कम है, {n} प्रतिशत। कृपया अभी चार्जर लगाएं।",
      status: "बैटरी {n} प्रतिशत है।",
      charging: "बैटरी {n} प्रतिशत है और चार्ज हो रही है।",
      on: "चार्जर जुड़ गया।",
      off: "चार्जर हट गया।",
      unsupported: "इस डिवाइस पर मैं बैटरी का स्तर नहीं पढ़ सकता।",
    },
    "kn-IN": {
      low: "ಬ್ಯಾಟರಿ {n} ಪ್ರತಿಶತ ಇದೆ. ದಯವಿಟ್ಟು ಶೀಘ್ರದಲ್ಲೇ ನಿಮ್ಮ ಫೋನ್ ಚಾರ್ಜ್ ಮಾಡಿ.",
      critical: "ಬ್ಯಾಟರಿ ತುಂಬಾ ಕಡಿಮೆ ಇದೆ, {n} ಪ್ರತಿಶತ. ದಯವಿಟ್ಟು ಈಗಲೇ ಚಾರ್ಜರ್ ಹಾಕಿ.",
      status: "ಬ್ಯಾಟರಿ {n} ಪ್ರತಿಶತ ಇದೆ.",
      charging: "ಬ್ಯಾಟರಿ {n} ಪ್ರತಿಶತ ಇದೆ, ಚಾರ್ಜ್ ಆಗುತ್ತಿದೆ.",
      on: "ಚಾರ್ಜರ್ ಸಂಪರ್ಕಗೊಂಡಿದೆ.",
      off: "ಚಾರ್ಜರ್ ತೆಗೆಯಲಾಗಿದೆ.",
      unsupported: "ಈ ಸಾಧನದಲ್ಲಿ ನನಗೆ ಬ್ಯಾಟರಿ ಮಟ್ಟವನ್ನು ಓದಲು ಸಾಧ್ಯವಿಲ್ಲ.",
    },
    "ta-IN": {
      low: "பேட்டரி {n} சதவீதம் உள்ளது. விரைவில் உங்கள் தொலைபேசியை சார்ஜ் செய்யுங்கள்.",
      critical: "பேட்டரி மிகவும் குறைவாக உள்ளது, {n} சதவீதம். உடனே சார்ஜரை இணைக்கவும்.",
      status: "பேட்டரி {n} சதவீதம் உள்ளது.",
      charging: "பேட்டரி {n} சதவீதம் உள்ளது, சார்ஜ் ஆகிறது.",
      on: "சார்ஜர் இணைக்கப்பட்டது.",
      off: "சார்ஜர் துண்டிக்கப்பட்டது.",
      unsupported: "இந்தச் சாதனத்தில் என்னால் பேட்டரி அளவைப் படிக்க முடியவில்லை.",
    },
    "te-IN": {
      low: "బ్యాటరీ {n} శాతం ఉంది. దయచేసి త్వరలో మీ ఫోన్‌ను ఛార్జ్ చేయండి.",
      critical: "బ్యాటరీ చాలా తక్కువగా ఉంది, {n} శాతం. దయచేసి వెంటనే ఛార్జర్ పెట్టండి.",
      status: "బ్యాటరీ {n} శాతం ఉంది.",
      charging: "బ్యాటరీ {n} శాతం ఉంది, ఛార్జ్ అవుతోంది.",
      on: "ఛార్జర్ కనెక్ట్ అయింది.",
      off: "ఛార్జర్ తొలగించబడింది.",
      unsupported: "ఈ పరికరంలో నేను బ్యాటరీ స్థాయిని చదవలేను.",
    },
  };

  // Parts of an obstacle announcement: "<name> <position>, <distance>"
  const POSITIONS = {
    "on your left": ["आपके बाईं ओर", "ನಿಮ್ಮ ಎಡಭಾಗದಲ್ಲಿ", "உங்கள் இடதுபுறம்", "మీ ఎడమ వైపు"],
    "on your right": ["आपके दाईं ओर", "ನಿಮ್ಮ ಬಲಭಾಗದಲ್ಲಿ", "உங்கள் வலதுபுறம்", "మీ కుడి వైపు"],
    "ahead of you": ["आपके सामने", "ನಿಮ್ಮ ಮುಂದೆ", "உங்களுக்கு முன்னால்", "మీ ముందు"],
  };
  const DISTANCES = {
    "very close": ["बहुत पास", "ತುಂಬಾ ಹತ್ತಿರ", "மிக அருகில்", "చాలా దగ్గరగా"],
    "1 meter away": ["1 मीटर दूर", "1 ಮೀಟರ್ ದೂರ", "1 மீட்டர் தூரத்தில்", "1 మీటర్ దూరంలో"],
    "2 meters away": ["2 मीटर दूर", "2 ಮೀಟರ್ ದೂರ", "2 மீட்டர் தூரத்தில்", "2 మీటర్ల దూరంలో"],
    "far away": ["दूर", "ದೂರದಲ್ಲಿ", "தொலைவில்", "దూరంగా"],
  };
  const ALSO = ["साथ ही, ", "ಜೊತೆಗೆ, ", "மேலும், ", "అలాగే, "];

  const norm = (t) =>
    String(t || "").toLowerCase().replace(/\s+/g, " ").replace(/[.!\s]+$/, "").trim();

  const PHRASES = {};
  PHRASE_ROWS.forEach((row) => {
    const entry = {};
    L.forEach((code, i) => (entry[code] = row[i + 1]));
    PHRASES[norm(row[0])] = entry;
  });

  const NAMES = {};
  NAME_ROWS.forEach((row) => {
    const entry = {};
    L.forEach((code, i) => (entry[code] = row[i + 1]));
    NAMES[row[0]] = entry;
  });

  const idx = (lang) => L.indexOf(lang);

  // Words that mean "I am in danger / emergency" - only strong, unambiguous
  // words, so ordinary requests for "help" never trigger a false alert.
  const EMERGENCY_PATTERNS = [
    /बचाओ|इमरजेंसी|आपातकाल|एसओएस|खतरे\s*में|bachao|bachaao/,
    /ಕಾಪಾಡಿ|ತುರ್ತು\s*ಪರಿಸ್ಥಿತಿ|ಎಮರ್ಜೆನ್ಸಿ|ಇಮರ್ಜೆನ್ಸಿ|ಅಪಾಯದಲ್ಲಿ|ಎಸ್\s*ಒ\s*ಎಸ್/,
    /காப்பாற்றுங்கள்|அவசரநிலை|எமர்ஜென்சி|ஆபத்தில்|எஸ்\s*ஓ\s*எஸ்/,
    /కాపాడండి|అత్యవసర|ఎమర్జెన్సీ|ప్రమాదంలో|ఎస్\s*ఓ\s*ఎస్/,
  ];
  const SAFE_PATTERNS = [
    /\bi\s*(am|'m)\s+safe\b|\bstop\s+(sharing|tracking)\b|\bcancel\s+emergency\b/,
    /मैं\s*सुरक्षित/,
    /ನಾನು\s*ಸುರಕ್ಷಿತ/,
    /நான்\s*பாதுகாப்பாக/,
    /నేను\s*సురక్షితంగా/,
  ];
  const BATTERY_PATTERNS = [
    /\bbattery\b|\bcharge (level|left)\b|how much charge/,
    /बैटरी|ಬ್ಯಾಟರಿ|பேட்டரி|బ్యాటరీ/,
  ];
  const CURRENCY_PATTERNS = [
    /\b(what|which)\b.*\b(note|money|currency|rupee|coin)s?\b/,
    /\b(identify|read|check|scan)\b.*\b(note|money|currency|rupee|coin)s?\b/,
    /\bhow much (money|is this)\b/,
    /यह\s*कौन\s*सा\s*नोट|ಇದು\s*ಯಾವ\s*ನೋಟು|இது\s*என்ன\s*நோட்டு|ఇది\s*ఏ\s*నోటు/,
  ];

  window.BM = {
    languages: ["en-IN"].concat(L),

    lang() {
      return (
        (window.blindMate && window.blindMate.currentLanguage) ||
        localStorage.getItem("blindmate_language") ||
        "en-IN"
      );
    },

    /** Instant offline translation of a known app sentence, or null. */
    lookup(english, lang) {
      const code = lang || this.lang();
      if (code === "en-IN") return english;
      const hit = PHRASES[norm(english)];
      return hit && hit[code] ? hit[code] : null;
    },

    /**
     * Build an obstacle announcement entirely offline.
     * items: [{name, position, distance}] using the English strings the app
     * already produces. Returns null if any word is unknown (caller then
     * falls back to the normal translation path).
     */
    composeAnnouncement(items, lang) {
      const i = idx(lang);
      if (i < 0) return null;
      const parts = [];
      for (const it of items) {
        const n = NAMES[it.name];
        const p = POSITIONS[it.position];
        const d = DISTANCES[it.distance];
        if (!n || !p || !d) return null;
        parts.push(`${n[lang]} ${p[i]}, ${d[i]}`);
      }
      return parts.join(". " + ALSO[i]);
    },

    isEmergency(text) {
      const t = String(text || "").toLowerCase();
      return EMERGENCY_PATTERNS.some((re) => re.test(t));
    },
    isSafe(text) {
      const t = String(text || "").toLowerCase();
      return SAFE_PATTERNS.some((re) => re.test(t));
    },
    isBatteryRequest(text) {
      const t = String(text || "").toLowerCase();
      return BATTERY_PATTERNS.some((re) => re.test(t));
    },

    /** Battery sentence in English and in `lang` (offline). */
    batteryText(kind, n, lang) {
      const fill = (tpl) => String(tpl).replace("{n}", n);
      const en = fill(BATTERY["en-IN"][kind]);
      const code = lang || this.lang();
      const local = BATTERY[code] ? fill(BATTERY[code][kind]) : null;
      return { en, local };
    },

    isCurrencyRequest(text) {
      const t = String(text || "").toLowerCase();
      return CURRENCY_PATTERNS.some((re) => re.test(t));
    },

    /** Speak with a real voice for `lang` if the device has one, else English. */
    speakSafe(english, opts) {
      if (!window.speechSynthesis) return;
      const lang = (opts && opts.lang) || this.lang();
      const voices = speechSynthesis.getVoices();
      const base = lang.split("-")[0];
      const voice =
        voices.find((v) => v.lang === lang) ||
        voices.find((v) => v.lang && v.lang.toLowerCase().startsWith(base));
      let text = english;
      let useLang = "en-IN";
      if (lang !== "en-IN" && voice) {
        const local = (opts && opts.local) || this.lookup(english, lang);
        if (local) {
          text = local;
          useLang = lang;
        }
      }
      if (!(opts && opts.queue)) speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = useLang;
      if (useLang !== "en-IN") u.voice = voice;
      speechSynthesis.speak(u);
    },
  };
})();
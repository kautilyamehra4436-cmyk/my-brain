# Advait v32.0 — One-Click Start Check (Hindi)

## उद्देश्य
यह workflow एक क्लिक से (1) पूरा मौजूदा Python unit-test suite चलाता है, (2) core/tests compile करता है, और (3) OpenRouter के चुने हुए `:free` model पर केवल एक छोटा, fixed, non-sensitive smoke request भेजता है।

## उपयोगकर्ता के लिए एक क्लिक
1. GitHub में इस workflow को खोलें: https://github.com/kautilyamehra4436-cmyk/my-brain/actions/workflows/advait-one-click-start-check-v1.yml
2. **Run workflow** दबाएँ।
3. Branch `main` रहने दें। Model default `nvidia/nemotron-3.5-lightning:free` रहने दें।
4. नीचे हरा **Run workflow** बटन दबाएँ।
5. Run खुलने पर पूरा होने तक प्रतीक्षा करें। हरा check = tests + compile + एक provider smoke call सफल। लाल check = run logs में कारण देखें।

## सुरक्षा और खर्च सीमा
- Workflow केवल `OPENROUTER_API_KEY` GitHub Actions secret पढ़ता है; key को chat या code में न डालें।
- केवल model ID जो `:free` पर समाप्त हो स्वीकार होगा।
- OpenAI paid API और paid fallback इस workflow में नहीं हैं।
- केवल एक fixed generic prompt भेजा जाता है; निजी/customer/financial data न भेजें।
- Permissions `contents: read` हैं; यह workflow repository files बदलता नहीं।
- Metadata-only SQLite audit artifact अधिकतम 7 दिन रखा जाता है।

## यह क्या शुरू करता है — और क्या नहीं
यह **readiness check** है, 24/7 autonomous Advait runtime नहीं। यह provider credentials/network/model को वास्तविक रूप से जाँचता है और tests चलाता है। यह bounty खोजता/पूरा नहीं करता, browser चलाता नहीं, ग्राहक से संपर्क नहीं करता, payment नहीं लेता, और कोई पैसा खर्च/transfer नहीं करता। Worker अभी bounded framework है; production scheduler, authenticated owner approvals, sandbox, task-to-provider integration और persistent host runtime अलग से बाकी हैं।

## परिणाम कैसे पढ़ें
- `SMOKE_TEST_PASSED`: वास्तविक provider call सफल।
- `SMOKE_TEST_FAILED`: provider/network/model response में समस्या।
- `OPENROUTER_API_KEY is missing`: GitHub repository Settings → Secrets and variables → Actions में `OPENROUTER_API_KEY` नाम जाँचें; secret value कभी साझा न करें।
- Unit tests या compile fail हों तो provider call तक workflow नहीं पहुँचेगा।

स्थिति: एक-क्लिक जाँच workflow; इसे manually trigger करना आवश्यक है। कोई schedule या 24/7 execution enable नहीं है।

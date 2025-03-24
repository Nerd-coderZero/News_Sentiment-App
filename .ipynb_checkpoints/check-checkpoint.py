import google.generativeai as genai

api_key = "AIzaSyDx8DT-eQYGYEs1aOZnkgwM81QyMEnWreg"
genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content("Hello, how are you?")
print(response.text)